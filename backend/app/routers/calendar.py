import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends, HTTPException
from googleapiclient.discovery import build, build_from_document
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_db
from app.database.crud_users import get_user_by_email
from app.dependencies.auth import get_current_user
from app.schemas.calendar import CalendarEventResponse, CreateEventRequest
from app.achievements import check_and_grant_achievements

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar", tags=["Calendario"])

# Discovery doc cacheado en memoria — se obtiene una sola vez por proceso
_discovery_doc: Optional[str] = None
_discovery_lock = threading.Lock()


def _get_discovery_doc() -> str:
    global _discovery_doc
    if _discovery_doc is None:
        with _discovery_lock:
            if _discovery_doc is None:
                import urllib.request
                url = "https://www.googleapis.com/discovery/v1/apis/calendar/v3/rest"
                with urllib.request.urlopen(url) as r:
                    _discovery_doc = r.read().decode()
    return _discovery_doc


def build_calendar_service(google_token: str):
    credentials = Credentials(token=google_token)
    try:
        return build_from_document(doc=_get_discovery_doc(), credentials=credentials)
    except Exception:
        # Fallback a build normal si el cache falla
        return build("calendar", "v3", credentials=credentials)


def _fetch_single_calendar(google_token: str, cal_id: str, max_results: int, time_min: str, time_max: Optional[str]) -> list:
    # Cada hilo necesita su propio service — httplib2 no es thread-safe
    service = build_calendar_service(google_token)
    params = {
        "calendarId": cal_id,
        "timeMin": time_min,
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_max:
        params["timeMax"] = time_max
    return service.events().list(**params).execute().get("items", [])


def _fetch_events_sync(google_token: str, max_results: int, time_min: str, time_max: Optional[str]) -> list:
    service = build_calendar_service(google_token)
    cal_list = service.calendarList().list().execute()
    active_calendars = [c["id"] for c in cal_list.get("items", []) if c.get("selected", False)]

    if not active_calendars:
        return []

    # Fetch de todos los calendarios en paralelo
    with ThreadPoolExecutor(max_workers=min(len(active_calendars), 5)) as pool:
        futures = {
            pool.submit(_fetch_single_calendar, google_token, cal_id, max_results, time_min, time_max): cal_id
            for cal_id in active_calendars
        }
        all_items = []
        for future in as_completed(futures):
            try:
                all_items.extend(future.result())
            except Exception as e:
                logger.warning("Error fetching calendar %s: %s", futures[future], e)

    return all_items


def _create_event_sync(google_token: str, event_body: dict) -> dict:
    service = build_calendar_service(google_token)
    return service.events().insert(calendarId="primary", body=event_body).execute()


@router.get("/events", response_model=list[CalendarEventResponse])
async def get_events(
    current_user: dict = Depends(get_current_user),
    max_results: int = 50,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
):
    """
    Retorna eventos del Google Calendar del usuario.
    time_min / time_max: RFC3339. Si no se pasan, time_min = inicio del mes actual.
    """
    try:
        if not time_min:
            now = datetime.now(timezone.utc)
            time_min = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(
            None, _fetch_events_sync, current_user["google_token"], max_results, time_min, time_max
        )

        events = []
        for item in items:
            start = item["start"].get("dateTime", item["start"].get("date"))
            end = item["end"].get("dateTime", item["end"].get("date"))
            if not start:
                logger.warning("Evento sin start, omitido: %s", item.get("id"))
                continue
            events.append(
                CalendarEventResponse(
                    id=item["id"],
                    title=item.get("summary", "Sin título"),
                    start=start,
                    end=end,
                    description=item.get("description"),
                    location=item.get("location"),
                )
            )
        return events

    except HttpError as e:
        logger.error("Google Calendar error fetching events: %s %s", e.status_code, e.reason)
        raise HTTPException(status_code=e.status_code, detail=f"Error de Google Calendar: {e.reason}")
    except Exception as e:
        logger.error("Unexpected error fetching events: %s", e)
        raise HTTPException(status_code=500, detail="Error interno al obtener eventos")


@router.post("/events", response_model=CalendarEventResponse, status_code=201)
async def create_event(
    body: CreateEventRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        event_body = {
            "summary": body.title,
            "start": {
                "dateTime": body.start.isoformat(),
                "timeZone": "America/Mexico_City",
            },
            "end": {
                "dateTime": body.end.isoformat(),
                "timeZone": "America/Mexico_City",
            },
        }
        if body.description:
            event_body["description"] = body.description
        if body.location:
            event_body["location"] = body.location

        loop = asyncio.get_running_loop()
        created = await loop.run_in_executor(
            None, _create_event_sync, current_user["google_token"], event_body
        )

        start = created["start"].get("dateTime", created["start"].get("date"))
        end = created["end"].get("dateTime", created["end"].get("date"))
        if not start:
            logger.error("Evento creado sin start en respuesta de Google: %s", created.get("id"))
            raise HTTPException(status_code=502, detail="Respuesta inválida de Google Calendar")

        try:
            user = await get_user_by_email(db, current_user["email"])
            if user:
                await check_and_grant_achievements(db, str(user.id), "event_created")
        except Exception:
            pass

        return CalendarEventResponse(
            id=created["id"],
            title=created.get("summary", "Sin título"),
            start=start,
            end=end,
            description=created.get("description"),
            location=created.get("location"),
        )

    except HttpError as e:
        logger.error("Google Calendar error creating event: %s %s", e.status_code, e.reason)
        raise HTTPException(status_code=e.status_code, detail=f"Error de Google Calendar: {e.reason}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error creating event: %s", e)
        raise HTTPException(status_code=500, detail="Error interno al crear evento")

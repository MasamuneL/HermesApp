from fastapi import APIRouter, Depends, HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone

from app.dependencies.auth import get_current_user
from app.schemas.calendar import CalendarEventResponse, CreateEventRequest

router = APIRouter(prefix="/api/calendar", tags=["Calendario"])


def build_calendar_service(google_token: str):
    """
    Crea el cliente de Google Calendar usando el access token OAuth del usuario.
    El mismo token que se usa para autenticación también tiene scope de calendar.
    """
    credentials = Credentials(token=google_token)
    return build("calendar", "v3", credentials=credentials)


@router.get("/events", response_model=list[CalendarEventResponse])
async def get_events(
    current_user: dict = Depends(get_current_user),
    max_results: int = 20,
):
    """
    Retorna los próximos eventos del Google Calendar del usuario autenticado.

    Headers requeridos:
    - Authorization: Bearer <google_oauth_access_token>

    El mismo token de auth se usa para acceder a Google Calendar API.
    """
    try:
        service = build_calendar_service(current_user["google_token"])
        now = datetime.now(timezone.utc).isoformat()

        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = []
        for item in result.get("items", []):
            start = item["start"].get("dateTime", item["start"].get("date"))
            end = item["end"].get("dateTime", item["end"].get("date"))
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
        raise HTTPException(status_code=e.status_code, detail=f"Error de Google Calendar: {e.reason}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener eventos: {str(e)}")


@router.post("/events", response_model=CalendarEventResponse, status_code=201)
async def create_event(
    body: CreateEventRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Crea un nuevo evento en el Google Calendar del usuario autenticado.

    Headers requeridos:
    - Authorization: Bearer <google_oauth_access_token>

    Body ejemplo:
        {
            "title": "Cálculo II",
            "start": "2026-03-25T10:00:00",
            "end": "2026-03-25T12:00:00",
            "description": "Examen parcial",
            "location": "Salón 301"
        }
    """
    try:
        service = build_calendar_service(current_user["google_token"])

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

        created = service.events().insert(calendarId="primary", body=event_body).execute()

        return CalendarEventResponse(
            id=created["id"],
            title=created.get("summary", "Sin título"),
            start=created["start"].get("dateTime", created["start"].get("date")),
            end=created["end"].get("dateTime", created["end"].get("date")),
            description=created.get("description"),
            location=created.get("location"),
        )

    except HttpError as e:
        raise HTTPException(status_code=e.status_code, detail=f"Error de Google Calendar: {e.reason}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear evento: {str(e)}")

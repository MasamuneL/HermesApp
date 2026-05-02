"""
action_tools.py — Funciones de Google Calendar que el orquestador puede ejecutar.

Cada función recibe un google_token (OAuth access token del usuario) y realiza
la operación correspondiente en el Google Calendar primario del usuario.
"""

from datetime import datetime, timezone
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def _build_service(google_token: str):
    """Crea el cliente de Google Calendar a partir del OAuth access token."""
    credentials = Credentials(token=google_token)
    return build("calendar", "v3", credentials=credentials)


def create_calendar_event(
    google_token: str,
    title: str,
    start: str,
    end: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    recurrence: Optional[list] = None,
) -> dict:
    """
    Crea un evento en Google Calendar.

    Args:
        google_token: OAuth access token del usuario.
        title: Título del evento.
        start: Fecha/hora de inicio en formato ISO 8601 (YYYY-MM-DDTHH:MM:SS).
        end: Fecha/hora de fin en formato ISO 8601.
        description: Descripción opcional.
        location: Ubicación opcional (ej: "Salón H202").
        recurrence: Lista de reglas RRULE para eventos recurrentes.
                    Ej: ["RRULE:FREQ=WEEKLY;UNTIL=20260630T000000Z"]

    Returns:
        Dict con los datos del evento creado.
    """
    service = _build_service(google_token)
    event_body = {
        "summary": title,
        "start": {"dateTime": start, "timeZone": "America/Mexico_City"},
        "end": {"dateTime": end, "timeZone": "America/Mexico_City"},
    }
    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location
    if recurrence:
        event_body["recurrence"] = recurrence

    created = service.events().insert(calendarId="primary", body=event_body).execute()
    return {
        "id": created["id"],
        "title": created.get("summary"),
        "start": created["start"].get("dateTime", created["start"].get("date")),
        "end": created["end"].get("dateTime", created["end"].get("date")),
        "description": created.get("description"),
        "location": created.get("location"),
    }


def get_calendar_events(
    google_token: str,
    max_results: int = 20,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
) -> list[dict]:
    """
    Retorna los próximos eventos del calendario del usuario.

    Args:
        google_token: OAuth access token del usuario.
        max_results: Número máximo de eventos a retornar.
        time_min: Límite inferior de tiempo en ISO 8601. Defaults a ahora.
        time_max: Límite superior de tiempo en ISO 8601 (opcional).

    Returns:
        Lista de dicts con los datos de cada evento.
    """
    service = _build_service(google_token)
    if time_min is None:
        time_min = datetime.now(timezone.utc).isoformat()

    params = {
        "calendarId": "primary",
        "timeMin": time_min,
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_max:
        params["timeMax"] = time_max

    result = service.events().list(**params).execute()
    events = []
    for item in result.get("items", []):
        events.append({
            "id": item["id"],
            "title": item.get("summary", "Sin título"),
            "start": item["start"].get("dateTime", item["start"].get("date")),
            "end": item["end"].get("dateTime", item["end"].get("date")),
            "description": item.get("description"),
            "location": item.get("location"),
        })
    return events


def update_calendar_event(
    google_token: str,
    event_id: str,
    title: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
) -> dict:
    """
    Actualiza un evento existente en Google Calendar.
    Solo modifica los campos que se pasen (parcial).

    Args:
        google_token: OAuth access token del usuario.
        event_id: ID del evento a actualizar.
        title, start, end, description, location: Campos a actualizar (todos opcionales).

    Returns:
        Dict con los datos del evento actualizado.
    """
    service = _build_service(google_token)
    event = service.events().get(calendarId="primary", eventId=event_id).execute()

    if title:
        event["summary"] = title
    if start:
        event["start"] = {"dateTime": start, "timeZone": "America/Mexico_City"}
    if end:
        event["end"] = {"dateTime": end, "timeZone": "America/Mexico_City"}
    if description is not None:
        event["description"] = description
    if location is not None:
        event["location"] = location

    updated = service.events().update(
        calendarId="primary", eventId=event_id, body=event
    ).execute()
    return {
        "id": updated["id"],
        "title": updated.get("summary"),
        "start": updated["start"].get("dateTime", updated["start"].get("date")),
        "end": updated["end"].get("dateTime", updated["end"].get("date")),
        "description": updated.get("description"),
        "location": updated.get("location"),
    }


def delete_calendar_event(google_token: str, event_id: str) -> dict:
    """
    Elimina un evento de Google Calendar.

    Args:
        google_token: OAuth access token del usuario.
        event_id: ID del evento a eliminar.

    Returns:
        Dict confirmando la eliminación.
    """
    service = _build_service(google_token)
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    return {"deleted": True, "event_id": event_id}


def search_calendar_events(
    google_token: str,
    query: str,
    max_results: int = 10,
) -> list[dict]:
    """
    Busca eventos en Google Calendar por texto libre.

    Args:
        google_token: OAuth access token del usuario.
        query: Texto a buscar (título, descripción, ubicación, etc.).
        max_results: Número máximo de resultados.

    Returns:
        Lista de dicts con los eventos que coinciden.
    """
    service = _build_service(google_token)
    result = service.events().list(
        calendarId="primary",
        q=query,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for item in result.get("items", []):
        events.append({
            "id": item["id"],
            "title": item.get("summary", "Sin título"),
            "start": item["start"].get("dateTime", item["start"].get("date")),
            "end": item["end"].get("dateTime", item["end"].get("date")),
            "description": item.get("description"),
            "location": item.get("location"),
        })
    return events

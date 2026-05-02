from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CalendarEventResponse(BaseModel):
    id: str
    title: str
    start: str
    end: Optional[str]
    description: Optional[str]
    location: Optional[str]


class CreateEventRequest(BaseModel):
    title: str
    start: datetime  # ISO 8601 — ej: "2026-03-25T10:00:00"
    end: datetime    # ISO 8601 — ej: "2026-03-25T11:00:00"
    description: Optional[str] = None
    location: Optional[str] = None

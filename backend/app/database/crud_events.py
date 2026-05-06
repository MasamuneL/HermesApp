# app/crud/crud_events.py
"""
CRUD de Eventos del Calendario
Funciones para crear, leer, actualizar y borrar eventos
"""
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.event import CalendarEvent
from datetime import datetime, timedelta
from typing import Optional, List
import uuid

# ==========================================
# CREATE - Crear evento
# ==========================================

async def create_event(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str,
    start_time: datetime,
    end_time: datetime,
    event_type: str = None,
    description: str = None,
    classroom: str = None,
    professor: str = None,
    recurrence: str = None
) -> CalendarEvent:
    """
    Crea un nuevo evento en el calendario
    
    Parámetros:
        user_id: ID del usuario
        title: Nombre del evento (ej: "Cálculo Diferencial")
        start_time: Cuándo empieza
        end_time: Cuándo termina
        event_type: Tipo (clase, examen, tarea, estudio)
        classroom: Salón (ej: "Aula 301")
        professor: Nombre del profesor
        recurrence: Si se repite (weekly, daily, monthly)
    
    Ejemplo:
        event = await create_event(
            db,
            user_id=user.id,
            title="Cálculo Diferencial",
            start_time=datetime(2026, 3, 10, 8, 0),
            end_time=datetime(2026, 3, 10, 10, 0),
            event_type="clase",
            classroom="Aula 301",
            professor="Dr. García"
        )
    """
    event = CalendarEvent(
        user_id=user_id,
        title=title,
        start_time=start_time,
        end_time=end_time,
        event_type=event_type,
        description=description,
        classroom=classroom,
        professor=professor,
        recurrence=recurrence
    )
    db.add(event)
    await db.flush()
    return event

async def create_events_from_ocr(
    db: AsyncSession,
    user_id: uuid.UUID,
    events_data: List[dict]
) -> List[CalendarEvent]:
    """
    Crea múltiples eventos desde OCR (cuando el usuario sube foto del horario)
    
    Parámetros:
        user_id: ID del usuario
        events_data: Lista de diccionarios con info de eventos
    
    Ejemplo de events_data:
        [
            {
                "title": "Cálculo",
                "day": "Lunes",
                "start_time": "08:00",
                "end_time": "10:00",
                "classroom": "301"
            },
            {
                "title": "Física",
                "day": "Martes",
                "start_time": "10:00",
                "end_time": "12:00",
                "classroom": "Lab 2"
            }
        ]
    
    Víctor te pasará esta lista después de que Gemini procese la imagen.
    """
    events = []
    for data in events_data:
        event = CalendarEvent(
            user_id=user_id,
            title=data.get("title"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            event_type=data.get("event_type", "clase"),
            classroom=data.get("classroom"),
            professor=data.get("professor"),
            recurrence=data.get("recurrence", "weekly")  # Por defecto semanal
        )
        events.append(event)
        db.add(event)

    await db.flush()

    return events

# ==========================================
# READ - Leer eventos
# ==========================================

async def get_event_by_id(db: AsyncSession, event_id: uuid.UUID) -> Optional[CalendarEvent]:
    """
    Obtiene un evento por su ID
    """
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    return result.scalar_one_or_none()

async def get_user_events(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100
) -> List[CalendarEvent]:
    """
    Obtiene todos los eventos de un usuario
    
    Ejemplo:
        events = await get_user_events(db, user_id)
        for event in events:
            print(f"{event.title} - {event.start_time}")
    """
    result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.user_id == user_id)
        .order_by(CalendarEvent.start_time.asc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_events_by_date(
    db: AsyncSession,
    user_id: uuid.UUID,
    date: datetime
) -> List[CalendarEvent]:
    """
    Obtiene eventos de un día específico
    
    Ejemplo:
        hoy = datetime.now()
        events_today = await get_events_by_date(db, user_id, hoy)
    """
    start_of_day = date.replace(hour=0, minute=0, second=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    result = await db.execute(
        select(CalendarEvent)
        .where(
            and_(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_time >= start_of_day,
                CalendarEvent.start_time < end_of_day
            )
        )
        .order_by(CalendarEvent.start_time.asc())
    )
    return result.scalars().all()

async def get_upcoming_events(
    db: AsyncSession,
    user_id: uuid.UUID,
    days: int = 7
) -> List[CalendarEvent]:
    """
    Obtiene eventos próximos (próximos N días)
    
    Ejemplo:
        # Eventos de la próxima semana
        upcoming = await get_upcoming_events(db, user_id, days=7)
    """
    now = datetime.now()
    future_date = now + timedelta(days=days)
    
    result = await db.execute(
        select(CalendarEvent)
        .where(
            and_(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_time >= now,
                CalendarEvent.start_time <= future_date
            )
        )
        .order_by(CalendarEvent.start_time.asc())
    )
    return result.scalars().all()

async def get_events_by_type(
    db: AsyncSession,
    user_id: uuid.UUID,
    event_type: str
) -> List[CalendarEvent]:
    """
    Obtiene eventos de un tipo específico
    
    Ejemplo:
        exams = await get_events_by_type(db, user_id, "examen")
    """
    result = await db.execute(
        select(CalendarEvent)
        .where(
            and_(
                CalendarEvent.user_id == user_id,
                CalendarEvent.event_type == event_type
            )
        )
        .order_by(CalendarEvent.start_time.asc())
    )
    return result.scalars().all()

# ==========================================
# UPDATE - Actualizar evento
# ==========================================

async def update_event(
    db: AsyncSession,
    event_id: uuid.UUID,
    title: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    description: str = None,
    classroom: str = None,
    professor: str = None
) -> Optional[CalendarEvent]:
    """
    Actualiza un evento
    
    Ejemplo:
        event = await update_event(
            db,
            event_id=event.id,
            title="Cálculo Integral",
            classroom="Aula 405"
        )
    """
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if start_time is not None:
        update_data["start_time"] = start_time
    if end_time is not None:
        update_data["end_time"] = end_time
    if description is not None:
        update_data["description"] = description
    if classroom is not None:
        update_data["classroom"] = classroom
    if professor is not None:
        update_data["professor"] = professor
    
    if not update_data:
        return await get_event_by_id(db, event_id)
    
    await db.execute(
        update(CalendarEvent)
        .where(CalendarEvent.id == event_id)
        .values(**update_data)
    )
    await db.flush()

    return await get_event_by_id(db, event_id)

# ==========================================
# DELETE - Borrar evento
# ==========================================

async def delete_event(db: AsyncSession, event_id: uuid.UUID) -> bool:
    """
    Elimina un evento
    
    Ejemplo:
        deleted = await delete_event(db, event.id)
    """
    result = await db.execute(
        delete(CalendarEvent).where(CalendarEvent.id == event_id)
    )
    await db.flush()
    return result.rowcount > 0

async def delete_all_user_events(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Elimina TODOS los eventos de un usuario
    
    Ejemplo:
        count = await delete_all_user_events(db, user_id)
        print(f"Se eliminaron {count} eventos")
    """
    result = await db.execute(
        delete(CalendarEvent).where(CalendarEvent.user_id == user_id)
    )
    await db.flush()
    return result.rowcount

# ==========================================
# SEARCH - Buscar eventos
# ==========================================

async def search_events(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    limit: int = 20
) -> List[CalendarEvent]:
    """
    Busca eventos por título o descripción
    
    Ejemplo:
        events = await search_events(db, user_id, "cálculo")
        # Encuentra "Cálculo Diferencial", "Cálculo Integral", etc.
    """
    result = await db.execute(
        select(CalendarEvent)
        .where(
            and_(
                CalendarEvent.user_id == user_id,
                CalendarEvent.title.ilike(f"%{query}%")
            )
        )
        .order_by(CalendarEvent.start_time.desc())
        .limit(limit)
    )
    return result.scalars().all()
# backend/app/database/event.py
"""
Modelo de CalendarEvent (Evento del Calendario) - ACTUALIZADO
Tabla: calendar_events
Agregado: location
"""
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database.postgres import Base

class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    
    id = Column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(String)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    event_type = Column(String(50))
    classroom = Column(String(100))
    professor = Column(String(255))
    location = Column(String(255))      # NUEVO: Ubicación
    recurrence = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
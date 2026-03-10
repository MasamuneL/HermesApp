# app/models/event.py
"""
Modelo de Evento del Calendario
Define cómo se ven los eventos (clases, tareas, exámenes)
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.postgres import Base
import uuid

class CalendarEvent(Base):
    """
    Tabla: calendar_events
    
    Campos:
    - id: Identificador único del evento
    - user_id: A quién pertenece el evento
    - title: Nombre del evento (ej: "Cálculo Diferencial")
    - description: Detalles adicionales
    - start_time: Cuándo empieza
    - end_time: Cuándo termina
    - event_type: Tipo (clase, examen, tarea, etc)
    - classroom: Salón (ej: "Aula 301")
    - professor: Nombre del profesor
    - recurrence: Si se repite (ej: "weekly")
    """
    __tablename__ = "calendar_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Información del evento
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    # Fechas y horarios
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    
    # Metadata
    event_type = Column(String(50))  # clase, examen, tarea, estudio
    classroom = Column(String(100))
    professor = Column(String(255))
    recurrence = Column(String(50))  # daily, weekly, monthly
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relación con User
    user = relationship("User", back_populates="events")
    
    def __repr__(self):
        return f"<Event {self.title} at {self.start_time}>"
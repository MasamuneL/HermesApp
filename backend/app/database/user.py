# app/models/user.py
"""
Modelo de Usuario
Define cómo se ve un usuario en la base de datos
"""
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.postgres import Base
import uuid

class User(Base):
    """
    Tabla: users
    
    Campos:
    - id: Identificador único
    - email: Email del usuario (único)
    - full_name: Nombre completo
    - password_hash: Contraseña encriptada
    - google_id: ID de Google (si usa OAuth)
    - created_at: Fecha de registro
    - is_active: Si el usuario está activo
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    password_hash = Column(String(255))
    google_id = Column(String(255), unique=True, index=True)  # Para OAuth
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relaciones con otras tablas
    events = relationship("CalendarEvent", back_populates="user", cascade="all, delete-orphan")
    ranking = relationship("Ranking", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"
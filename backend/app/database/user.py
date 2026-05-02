# backend/app/database/user.py
"""
Modelo de User (Usuario) - ACTUALIZADO
Tabla: users
Agregados: u_degree, semester
"""
import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    password_hash = Column(String(255))
    google_id = Column(String(255), unique=True)
    u_degree = Column(String(255))
    semester = Column(Integer)
    universidad = Column(String(255))
    birth_date = Column(Date)
    photo_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    ranking = relationship("Ranking", back_populates="user", uselist=False)
# backend/app/database/user.py
"""
Modelo de User (Usuario) - ACTUALIZADO
Tabla: users
Agregados: u_degree, semester
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.sql import func
from app.database.postgres import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    password_hash = Column(String(255))
    google_id = Column(String(255), unique=True)
    u_degree = Column(String(255))      # NUEVO: Carrera
    semester = Column(Integer)           # NUEVO: Semestre
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
# backend/app/database/achievement.py
"""
Modelo de Achievement (Logro)
Tabla: achievements
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database.postgres import Base

class Achievement(Base):
    __tablename__ = "achievements"
    
    ach_id = Column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    usr_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ach_title = Column(String(255), nullable=False)
    ach_desc = Column(String)
    ach_points = Column(Integer, nullable=False)
    ach_rank = Column(Integer)
    fecha_objetivo = Column(Integer)  # Timestamp Unix
    status_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
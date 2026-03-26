# backend/app/database/ranking.py
"""
Modelo de Ranking y Puntos
Define los puntos y logros de cada usuario
CORREGIDO: Quitado back_populates que causaba error
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database.postgres import Base

class Ranking(Base):
    """
    Tabla: rankings
    
    Campos:
    - id: Identificador único
    - user_id: Usuario al que pertenece
    - points: Puntos totales acumulados
    - level: Nivel basado en puntos
    - achievements: Logros desbloqueados (JSON)
    - daily_streak: Racha de días consecutivos
    """
    __tablename__ = "rankings"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Puntuación
    points = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=1)
    
    # Logros (almacenados como JSON)
    # Ejemplo: {"first_scan": true, "week_streak": true, "top_10": false}
    achievements = Column(JSONB, default={})
    
    # Racha diaria
    daily_streak = Column(Integer, default=0)
    last_activity = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # NOTA: relationship con back_populates removido para evitar error
    # Si necesitas acceder al usuario: user = db.query(User).filter_by(id=ranking.user_id).first()
    
    def __repr__(self):
        return f"<Ranking user={self.user_id} points={self.points}>"
# backend/app/database/crud_achievements.py
"""
CRUD para achievements (logros)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.achievement import Achievement
from typing import List, Optional

async def create_achievement(
    db: AsyncSession,
    usr_id: str,
    ach_title: str,
    ach_desc: str,
    ach_points: int,
    ach_rank: int = None,
    fecha_objetivo: int = None
) -> Achievement:
    """Crear un nuevo logro para un usuario"""
    achievement = Achievement(
        usr_id=usr_id,
        ach_title=ach_title,
        ach_desc=ach_desc,
        ach_points=ach_points,
        ach_rank=ach_rank,
        fecha_objetivo=fecha_objetivo,
        status_completed=False
    )
    
    db.add(achievement)
    await db.commit()
    await db.refresh(achievement)
    return achievement


async def get_user_achievements(
    db: AsyncSession,
    usr_id: str
) -> List[Achievement]:
    """Obtener todos los logros de un usuario"""
    result = await db.execute(
        select(Achievement).where(Achievement.usr_id == usr_id)
    )
    return result.scalars().all()


async def get_completed_achievements(
    db: AsyncSession,
    usr_id: str
) -> List[Achievement]:
    """Obtener logros completados de un usuario"""
    result = await db.execute(
        select(Achievement).where(
            Achievement.usr_id == usr_id,
            Achievement.status_completed == True
        )
    )
    return result.scalars().all()


async def mark_achievement_completed(
    db: AsyncSession,
    ach_id: str
) -> Optional[Achievement]:
    """Marcar un logro como completado"""
    result = await db.execute(
        select(Achievement).where(Achievement.ach_id == ach_id)
    )
    achievement = result.scalar_one_or_none()
    
    if achievement:
        achievement.status_completed = True
        await db.commit()
        await db.refresh(achievement)
    
    return achievement


async def delete_achievement(
    db: AsyncSession,
    ach_id: str
) -> bool:
    """Eliminar un logro"""
    result = await db.execute(
        select(Achievement).where(Achievement.ach_id == ach_id)
    )
    achievement = result.scalar_one_or_none()
    
    if achievement:
        await db.delete(achievement)
        await db.commit()
        return True
    
    return False
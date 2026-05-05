# backend/app/achievements/achievement_service.py
"""
Servicio de logros
Maneja la lógica de otorgamiento y verificación de achievements
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.crud_achievements import (
    create_achievement,
    get_user_achievements,
    mark_achievement_completed
)
from app.database.redis_operations import update_user_ranking
from app.achievements.achievements_config import get_achievement_by_key, ACHIEVEMENTS


async def grant_achievement(
    db: AsyncSession,
    user_id: str,
    achievement_key: str
) -> dict:
    """
    Otorga un logro al usuario
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        achievement_key: Clave del logro (ej: "primera_tarea")
    
    Returns:
        dict con el logro creado o None si ya lo tenía
    """
    # Obtener configuración del logro
    achievement_config = get_achievement_by_key(achievement_key)
    if not achievement_config:
        return None
    
    # Verificar si ya tiene el logro
    user_achievements = await get_user_achievements(db, user_id)
    for ach in user_achievements:
        if ach.ach_title == achievement_config["title"]:
            return None  # Ya lo tiene
    
    # Crear el logro
    new_achievement = await create_achievement(
        db=db,
        usr_id=user_id,
        ach_title=achievement_config["title"],
        ach_desc=achievement_config["description"],
        ach_points=achievement_config["points"],
        ach_rank=achievement_config["rank"],
        fecha_objetivo=achievement_config.get("fecha_objetivo")
    )
    
    # Marcar como completado inmediatamente
    await mark_achievement_completed(db, str(new_achievement.ach_id))
    
    # Sumar puntos al ranking en Redis
    if achievement_config["points"] > 0:
        await update_user_ranking(user_id, achievement_config["points"])
    
    return {
        "achievement_key": achievement_key,
        "title": achievement_config["title"],
        "points": achievement_config["points"],
        "unlocked": True
    }


async def check_and_grant_achievements(
    db: AsyncSession,
    user_id: str,
    event_type: str,
    **kwargs
) -> list:
    """
    Verifica y otorga logros según el evento que ocurrió
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        event_type: Tipo de evento ("task_completed", "event_created", "chat_sent", etc.)
        **kwargs: Datos adicionales del evento
    
    Returns:
        Lista de logros desbloqueados
    """
    unlocked = []
    
    # Mapeo de eventos a logros
    event_achievement_map = {
        "task_completed": ["primera_tarea", "10_tareas", "50_tareas"],
        "event_created": ["primer_evento"],
        "chat_sent": ["primer_chat"],
        "friend_added": ["primer_amigo"],
        "daily_login": ["racha_3_dias", "racha_7_dias", "racha_30_dias"],
        "level_up": ["nivel_5", "nivel_10"]
    }
    
    # Obtener logros potenciales
    potential_achievements = event_achievement_map.get(event_type, [])
    
    for achievement_key in potential_achievements:
        # Verificar si cumple requisitos
        if await _check_requirements(db, user_id, achievement_key, **kwargs):
            result = await grant_achievement(db, user_id, achievement_key)
            if result:
                unlocked.append(result)
    
    return unlocked


async def _check_requirements(
    db: AsyncSession,
    user_id: str,
    achievement_key: str,
    **kwargs
) -> bool:
    """
    Verifica si el usuario cumple los requisitos para un logro
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        achievement_key: Clave del logro
        **kwargs: Datos del evento
    
    Returns:
        True si cumple requisitos, False si no
    """
    # Lógica de verificación según el logro
    if achievement_key == "primera_tarea":
        # Solo verificar si es la primera tarea
        task_count = kwargs.get("task_count", 0)
        return task_count == 1
    
    elif achievement_key == "10_tareas":
        task_count = kwargs.get("task_count", 0)
        return task_count == 10
    
    elif achievement_key == "50_tareas":
        task_count = kwargs.get("task_count", 0)
        return task_count == 50
    
    elif achievement_key == "racha_3_dias":
        streak = kwargs.get("daily_streak", 0)
        return streak == 3
    
    elif achievement_key == "racha_7_dias":
        streak = kwargs.get("daily_streak", 0)
        return streak == 7
    
    elif achievement_key == "racha_30_dias":
        streak = kwargs.get("daily_streak", 0)
        return streak == 30
    
    elif achievement_key == "nivel_5":
        level = kwargs.get("level", 0)
        return level == 5
    
    elif achievement_key == "nivel_10":
        level = kwargs.get("level", 0)
        return level == 10
    
    elif achievement_key in ["primer_evento", "primer_chat", "primer_amigo"]:
        # Estos se otorgan en el primer evento
        return True
    
    return False


async def get_user_achievement_progress(
    db: AsyncSession,
    user_id: str
) -> dict:
    """
    Obtiene el progreso del usuario en todos los logros
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
    
    Returns:
        dict con logros completados y pendientes
    """
    user_achievements = await get_user_achievements(db, user_id)
    completed_titles = {ach.ach_title for ach in user_achievements if ach.status_completed}
    
    progress = {
        "completed": [],
        "pending": []
    }
    
    for key, config in ACHIEVEMENTS.items():
        if config["title"] in completed_titles:
            progress["completed"].append({
                "key": key,
                "title": config["title"],
                "description": config["description"],
                "points": config["points"]
            })
        else:
            progress["pending"].append({
                "key": key,
                "title": config["title"],
                "description": config["description"],
                "points": config["points"]
            })
    
    return progress

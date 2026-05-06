# backend/app/achievements/__init__.py
"""
Módulo de logros (achievements)
Sistema de gamificación para Hermes
"""
from .achievements_config import ACHIEVEMENTS, get_achievement_by_key, get_all_achievements
from .achievement_service import (
    grant_achievement,
    check_and_grant_achievements,
    get_user_achievement_progress
)

__all__ = [
    "ACHIEVEMENTS",
    "get_achievement_by_key",
    "get_all_achievements",
    "grant_achievement",
    "check_and_grant_achievements",
    "get_user_achievement_progress"
]

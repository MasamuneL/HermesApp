# backend/app/achievements/achievements_config.py
"""
Configuración de logros del sistema Hermes
Define los 9 logros aprobados para el MVP
"""

ACHIEVEMENTS = {
    # ══════════════════════════════════════════════════════════
    # LOGROS DE INICIO (25 pts total)
    # ══════════════════════════════════════════════════════════
    "primera_tarea": {
        "title": "Primera Tarea",
        "description": "Completa tu primera tarea en Hermes",
        "points": 10,
        "rank": 1,
        "fecha_objetivo": None
    },
    
    "primer_evento": {
        "title": "Primer Evento",
        "description": "Agrega tu primer evento al calendario",
        "points": 10,
        "rank": 1,
        "fecha_objetivo": None
    },
    
    "primer_chat": {
        "title": "Primera Conversación",
        "description": "Chatea con Hermes por primera vez",
        "points": 5,
        "rank": 1,
        "fecha_objetivo": None
    },
    
    # ══════════════════════════════════════════════════════════
    # LOGROS DE RACHA (220 pts total)
    # ══════════════════════════════════════════════════════════
    "racha_3_dias": {
        "title": "3 Días Seguidos",
        "description": "Abre Hermes 3 días consecutivos",
        "points": 20,
        "rank": 2,
        "fecha_objetivo": None
    },
    
    "racha_7_dias": {
        "title": "Semana Completa",
        "description": "Abre Hermes 7 días consecutivos",
        "points": 50,
        "rank": 3,
        "fecha_objetivo": None
    },
    
    "racha_30_dias": {
        "title": "Mes Completo",
        "description": "Abre Hermes 30 días consecutivos",
        "points": 150,
        "rank": 4,
        "fecha_objetivo": None
    },
    
    # ══════════════════════════════════════════════════════════
    # LOGROS DE PRODUCTIVIDAD (130 pts total)
    # ══════════════════════════════════════════════════════════
    "10_tareas": {
        "title": "Productivo",
        "description": "Completa 10 tareas",
        "points": 30,
        "rank": 2,
        "fecha_objetivo": None
    },
    
    "50_tareas": {
        "title": "Súper Productivo",
        "description": "Completa 50 tareas",
        "points": 100,
        "rank": 3,
        "fecha_objetivo": None
    },
    
    # ══════════════════════════════════════════════════════════
    # LOGROS SOCIALES (15 pts total)
    # ══════════════════════════════════════════════════════════
    "primer_amigo": {
        "title": "Primer Amigo",
        "description": "Agrega tu primer amigo en Hermes",
        "points": 15,
        "rank": 2,
        "fecha_objetivo": None
    }
}


def get_achievement_by_key(key: str) -> dict:
    """Obtiene un logro por su clave"""
    return ACHIEVEMENTS.get(key)


def get_all_achievements() -> dict:
    """Retorna todos los logros disponibles"""
    return ACHIEVEMENTS


def get_total_possible_points() -> int:
    """Calcula el total de puntos posibles"""
    return sum(ach["points"] for ach in ACHIEVEMENTS.values())

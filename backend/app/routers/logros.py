from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/logros", tags=["Logros"])


@router.get("/me")
async def get_my_achievements(
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna los logros desbloqueados del usuario autenticado.

    Pendiente: Martin creará la tabla de achievements en la DB.
    Cuando esté lista, este endpoint:
    1. Busca al usuario por email en PostgreSQL
    2. Consulta sus logros en la nueva tabla de achievements
    3. Retorna la lista con AchievementsResponse
    """
    # TODO: implementar cuando Martin entregue la tabla de achievements
    raise HTTPException(
        status_code=501,
        detail="Módulo de logros aún no implementado — esperando tabla de Martin",
    )

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from firebase_admin import auth as firebase_auth

from app.database.postgres import get_db
from app.database.crud_users import get_user_by_email
from app.database.redis_operations import (
    get_top_ranking,
    get_user_rank,
    get_user_points_from_redis,
)
from app.schemas.ranking import RankingResponse

router = APIRouter(prefix="/api/ranking", tags=["Ranking"])


async def get_current_user(authorization: str = Header()):
    """
    Dependency de Firebase Auth.
    Verifica el token Bearer y retorna el payload decodificado.
    """
    try:
        token = authorization.replace("Bearer ", "")
        return firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


@router.get("/top")
async def get_global_top(limit: int = 10):
    """
    Retorna el top N del ranking global.
    Lee desde Redis (Sorted Set 'ranking:global') — no toca PostgreSQL.
    No requiere autenticación, cualquiera puede ver el leaderboard.
    """
    top = await get_top_ranking(limit)
    return {"success": True, "data": top}


@router.get("/me")
async def get_my_ranking(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna la posición y puntos del usuario autenticado en el ranking global.
    Combina Redis (posición + puntos en tiempo real) con el user_id de PostgreSQL.
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user_id_str = str(user.id)

    # Redis tiene los puntos en tiempo real (más rápido que PostgreSQL)
    rank = await get_user_rank(user_id_str)
    points = await get_user_points_from_redis(user_id_str)

    return {
        "success": True,
        "data": {
            "user_id": user_id_str,
            "rank": rank,           # Posición en el leaderboard (1 = primero)
            "points": points or 0,  # 0 si el usuario aún no tiene puntos en Redis
        },
    }

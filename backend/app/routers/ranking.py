import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_db
from app.database.crud_users import get_user_by_email, get_users_by_ids
from app.database.redis_operations import (
    get_top_ranking,
    get_user_rank,
    get_user_points_from_redis,
)
from app.dependencies.auth import get_current_user
from app.schemas.ranking import RankingResponse

router = APIRouter(prefix="/api/ranking", tags=["Ranking"])


@router.get("/top")
async def get_global_top(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna el top N del ranking global con nombre y foto de cada usuario.
    """
    top = await get_top_ranking(limit)

    valid_ids = []
    for entry in top:
        try:
            valid_ids.append(uuid.UUID(entry["user_id"]))
        except (ValueError, KeyError):
            pass

    users = await get_users_by_ids(db, valid_ids)
    user_map = {str(u.id): u for u in users}

    enriched = []
    for entry in top:
        u = user_map.get(entry["user_id"])
        enriched.append({
            "user_id": entry["user_id"],
            "points": entry["points"],
            "name": u.full_name if u else None,
            "photo_url": u.photo_url if u else None,
        })

    return {"success": True, "data": enriched}


@router.get("/me")
async def get_my_ranking(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna la posición y puntos del usuario autenticado en el ranking global.
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user_id_str = str(user.id)

    rank = await get_user_rank(user_id_str)
    points = await get_user_points_from_redis(user_id_str)

    return {
        "success": True,
        "data": {
            "user_id": user_id_str,
            "rank": rank,
            "points": points or 0,
        },
    }

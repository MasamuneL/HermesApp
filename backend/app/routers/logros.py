from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_db
from app.database.crud_users import get_user_by_email
from app.database.crud_achievements import get_user_achievements
from app.dependencies.auth import get_current_user
from app.achievements.achievements_config import ACHIEVEMENTS

router = APIRouter(prefix="/api/logros", tags=["Logros"])


@router.get("/me")
async def get_my_achievements(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user_achievements = await get_user_achievements(db, str(user.id))
    earned = {ach.ach_title: ach for ach in user_achievements}

    return [
        {
            "ach_id": str(earned[config["title"]].ach_id) if config["title"] in earned else key,
            "ach_title": config["title"],
            "ach_desc": config["description"],
            "ach_points": config["points"],
            "ach_rank": config["rank"],
            "status_completed": bool(earned.get(config["title"]) and earned[config["title"]].status_completed),
        }
        for key, config in ACHIEVEMENTS.items()
    ]

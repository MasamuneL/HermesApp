import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_db
from app.database.crud_users import get_user_by_email
from app.database.crud_achievements import get_user_achievements
from app.dependencies.auth import get_current_user
from app.achievements.achievements_config import ACHIEVEMENTS
from app.achievements import grant_achievement

router = APIRouter(prefix="/api/logros", tags=["Logros"])


class ToggleLogroRequest(BaseModel):
    completado: bool


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


@router.patch("/{ach_id}")
async def toggle_achievement(
    ach_id: str,
    body: ToggleLogroRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user_id = str(user.id)

    is_uuid = False
    try:
        uuid_lib.UUID(ach_id)
        is_uuid = True
    except ValueError:
        pass

    if is_uuid:
        user_achievements = await get_user_achievements(db, user_id)
        target = next((a for a in user_achievements if str(a.ach_id) == ach_id), None)
        if not target:
            raise HTTPException(status_code=404, detail="Logro no encontrado")
        target.status_completed = body.completado
        await db.flush()
    else:
        if body.completado:
            await grant_achievement(db, user_id, ach_id)
        else:
            # Mark unearned key as not-completed — no-op (not in DB yet)
            user_achievements = await get_user_achievements(db, user_id)
            config = ACHIEVEMENTS.get(ach_id)
            if config:
                target = next((a for a in user_achievements if a.ach_title == config["title"]), None)
                if target:
                    target.status_completed = False
                    await db.flush()

    return {"ok": True, "completado": body.completado}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_db
from app.database.crud_users import get_user_by_email
from app.dependencies.auth import get_current_user
from app.achievements import get_user_achievement_progress

router = APIRouter(prefix="/api/logros", tags=["Logros"])


@router.get("/me")
async def get_my_achievements(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return await get_user_achievement_progress(db, str(user.id))

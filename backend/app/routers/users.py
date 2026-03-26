from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_db
from app.database.crud_users import (
    get_user_by_email,
    create_user,
    update_user,
    deactivate_user,
)
from app.dependencies.auth import get_current_user
from app.schemas.users import UserResponse

router = APIRouter(prefix="/api/users", tags=["Usuarios"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Registra al usuario en PostgreSQL después de que Google OAuth lo autenticó.
    Se llama tras cada login — si el usuario ya existe, retorna su perfil actual.
    """
    existing = await get_user_by_email(db, current_user["email"])
    if existing:
        return existing

    user = await create_user(
        db,
        email=current_user["email"],
        full_name=current_user.get("name", ""),
        google_id=current_user["uid"],
    )
    return user


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna el perfil del usuario autenticado.
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    full_name: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Actualiza el nombre del usuario autenticado.
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    updated = await update_user(db, user.id, full_name=full_name)
    return updated


@router.delete("/me", status_code=204)
async def deactivate_my_account(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Desactiva la cuenta del usuario (soft delete — no borra de la DB).
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await deactivate_user(db, user.id)

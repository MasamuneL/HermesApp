from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date
import os

from app.database.postgres import get_db
from app.database.crud_users import (
    get_user_by_email,
    create_user,
    update_user,
    deactivate_user,
)
from app.dependencies.auth import get_current_user
from app.schemas.users import UserResponse, UpdateUserRequest
from app.database.redis_operations import update_user_ranking

from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/users", tags=["Usuarios"])


class PuntosRequest(BaseModel):
    puntos: int = Field(..., ge=1, le=500)


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
    body: UpdateUserRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Actualiza el perfil del usuario autenticado. Todos los campos son opcionales.
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    updated = await update_user(
        db, user.id,
        full_name=body.full_name,
        u_degree=body.u_degree,
        semester=body.semester,
        universidad=body.universidad,
        birth_date=body.birth_date,
    )
    return updated


UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/fotos")
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/foto", response_model=UserResponse)
async def upload_photo(
    foto: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sube o reemplaza la foto de perfil del usuario autenticado.
    Acepta jpeg, png y webp. Máximo ~5 MB (limitado por nginx/proxy en producción).
    """
    if foto.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Formato no permitido. Usa jpeg, png o webp.")

    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    MIME_TO_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = MIME_TO_EXT[foto.content_type]
    filename = f"{user.id}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    contents = await foto.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    photo_url = f"/static/fotos/{filename}"
    updated = await update_user(db, user.id, photo_url=photo_url)
    return updated


@router.put("/puntos")
async def update_puntos(
    body: PuntosRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    await update_user_ranking(str(user.id), body.puntos)
    return {"ok": True, "puntos": body.puntos}


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

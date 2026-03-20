from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from firebase_admin import auth as firebase_auth

from app.database.postgres import get_db
from app.database.crud_users import (
    get_user_by_email,
    create_user,
    update_user,
    deactivate_user,
)
from app.schemas.users import UserResponse

router = APIRouter(prefix="/api/users", tags=["Usuarios"])


async def get_current_user(authorization: str = Header()):
    """
    Dependency de Firebase Auth.
    Verifica el token Bearer y retorna el payload decodificado.
    El frontend siempre manda: Authorization: Bearer <firebase_token>
    """
    try:
        token = authorization.replace("Bearer ", "")
        return firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Registra al usuario en PostgreSQL después de que Firebase lo autenticó.
    Se llama una sola vez tras el primer login (Google OAuth o email/password).
    El frontend debe llamar este endpoint inmediatamente después del registro en Firebase.
    """
    # Si ya existe, no duplicar
    existing = await get_user_by_email(db, current_user["email"])
    if existing:
        raise HTTPException(status_code=409, detail="El usuario ya está registrado")

    # Detectar si entró con Google para guardar el google_id
    provider = current_user.get("firebase", {}).get("sign_in_provider", "")
    google_id = current_user.get("uid") if provider == "google.com" else None

    user = await create_user(
        db,
        email=current_user.get("email"),
        full_name=current_user.get("name", ""),
        google_id=google_id,
    )
    return user


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna el perfil del usuario autenticado.
    El frontend usa este endpoint al cargar la pantalla de perfil.
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
    Pendiente: cuando Martin agregue carrera/semestre al modelo User,
    este endpoint se extiende para recibir esos campos también.
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
    El campo is_active del modelo User pasa a False.
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await deactivate_user(db, user.id)

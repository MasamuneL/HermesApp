# app/crud/crud_users.py
"""
CRUD de Usuarios
Funciones para crear, leer, actualizar y borrar usuarios
"""
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.user import User
from app.database.ranking import Ranking
from typing import Optional, List
import uuid

# ==========================================
# CREATE - Crear usuario
# ==========================================

async def create_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    password_hash: str = None,
    google_id: str = None
) -> User:
    """
    Crea un nuevo usuario
    
    Parámetros:
        email: Email del usuario
        full_name: Nombre completo
        password_hash: Contraseña encriptada (si usa email/password)
        google_id: ID de Google (si usa OAuth)
    
    Retorna:
        Usuario creado
    
    Ejemplo:
        user = await create_user(
            db,
            email="juan@gmail.com",
            full_name="Juan Pérez",
            google_id="123456789"
        )
    """
    user = User(
        email=email,
        full_name=full_name,
        password_hash=password_hash,
        google_id=google_id
    )
    db.add(user)
    await db.flush()  # Para obtener el ID
    
    # Crear ranking automáticamente
    ranking = Ranking(id=user.id, user_id=user.id, points=0)
    db.add(ranking)
    
    return user

# ==========================================
# READ - Leer usuarios
# ==========================================

async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """
    Obtiene un usuario por su ID
    
    Ejemplo:
        user = await get_user_by_id(db, user_id)
        if user:
            print(user.email)
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Obtiene un usuario por su email
    
    Ejemplo:
        user = await get_user_by_email(db, "juan@gmail.com")
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_google_id(db: AsyncSession, google_id: str) -> Optional[User]:
    """
    Obtiene un usuario por su Google ID (para OAuth)
    
    Ejemplo:
        user = await get_user_by_google_id(db, "123456789")
    """
    result = await db.execute(select(User).where(User.google_id == google_id))
    return result.scalar_one_or_none()

async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """
    Obtiene todos los usuarios (paginado)
    
    Ejemplo:
        users = await get_all_users(db, skip=0, limit=10)
    """
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    return result.scalars().all()

# ==========================================
# UPDATE - Actualizar usuario
# ==========================================

async def update_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    full_name: str = None,
    email: str = None,
    u_degree: str = None,
    semester: int = None,
    universidad: str = None,
    birth_date=None,
    photo_url: str = None,
) -> Optional[User]:
    """
    Actualiza información del usuario

    Ejemplo:
        user = await update_user(
            db,
            user_id=user.id,
            full_name="Juan Carlos Pérez"
        )
    """
    # Preparar datos a actualizar
    update_data = {}
    if full_name is not None:
        update_data["full_name"] = full_name
    if email is not None:
        update_data["email"] = email
    if u_degree is not None:
        update_data["u_degree"] = u_degree
    if semester is not None:
        update_data["semester"] = semester
    if universidad is not None:
        update_data["universidad"] = universidad
    if birth_date is not None:
        update_data["birth_date"] = birth_date
    if photo_url is not None:
        update_data["photo_url"] = photo_url
    
    if not update_data:
        return await get_user_by_id(db, user_id)
    
    # Actualizar
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(**update_data)
    )
    await db.flush()

    return await get_user_by_id(db, user_id)

async def deactivate_user(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """
    Desactiva un usuario (no lo borra, solo lo marca como inactivo)
    
    Ejemplo:
        success = await deactivate_user(db, user.id)
    """
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=False)
    )
    await db.flush()
    return True

# ==========================================
# DELETE - Borrar usuario
# ==========================================

async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """
    Elimina un usuario PERMANENTEMENTE
    (También borra sus eventos y ranking por CASCADE)
    
    Ejemplo:
        deleted = await delete_user(db, user.id)
    """
    result = await db.execute(
        delete(User).where(User.id == user_id)
    )
    await db.flush()
    return result.rowcount > 0

# ==========================================
# SEARCH - Buscar usuarios
# ==========================================

async def search_users_by_name(db: AsyncSession, query: str, limit: int = 10) -> List[User]:
    """
    Busca usuarios por nombre (coincidencia parcial)
    
    Ejemplo:
        users = await search_users_by_name(db, "juan")
        # Encuentra "Juan", "Juana", "Juan Carlos", etc.
    """
    result = await db.execute(
        select(User)
        .where(User.full_name.ilike(f"%{query}%"))
        .limit(limit)
    )
    return result.scalars().all()
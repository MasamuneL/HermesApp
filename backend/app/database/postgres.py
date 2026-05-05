# app/database/postgres.py
"""
Configuración de conexión a PostgreSQL
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# URL de conexión (Dennis te la dará)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://hermes_user:password123@localhost:5432/hermes_db"
)

# Crear engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # Muestra las queries SQL en consola (útil para debug)
    pool_pre_ping=True,  # Verifica que la conexión esté viva
)

# Session maker
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base para los modelos
Base = declarative_base()

# Dependency para FastAPI (Víctor usará esto)
async def get_db():
    """
    Dependency que Víctor usará en sus endpoints
    
    Ejemplo:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            users = await crud.get_all_users(db)
            return users
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
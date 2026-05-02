import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.routers import users, ranking, chat, logros, calendar
from app.database.postgres import engine

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aplica schema.sql al arrancar — idempotente gracias a CREATE TABLE IF NOT EXISTS
    schema_path = os.path.join(os.path.dirname(__file__), "database", "schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r") as f:
            sql = f.read()
        async with engine.connect() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(sql)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Hermes API",
    description="Backend de la app académica Hermes — calendario inteligente, ranking y chatbot con Gemini.",
    version="0.0.3",
)

# CORS — permite que el frontend de Oswaldo llame al backend sin problemas
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción Dennis restringirá esto al dominio real
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(users.router)
app.include_router(ranking.router)
app.include_router(chat.router)
app.include_router(logros.router)
app.include_router(calendar.router)


os.makedirs("static/fotos", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return {"status": "ok", "app": "Hermes API v0.0.3"}

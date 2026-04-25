import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.routers import users, ranking, chat, logros, calendar

load_dotenv()

app = FastAPI(
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

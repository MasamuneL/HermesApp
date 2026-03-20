import os
import firebase_admin
from firebase_admin import credentials
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routers import users, ranking, chat, logros

load_dotenv()

# Inicializar Firebase Admin SDK una sola vez al arrancar el servidor.
# Lee las credenciales desde el archivo indicado en FIREBASE_CREDENTIALS_PATH.
_firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-credentials.json")
firebase_admin.initialize_app(credentials.Certificate(_firebase_creds_path))

app = FastAPI(
    title="Hermes API",
    description="Backend de la app académica Hermes — calendario inteligente, ranking y chatbot con Gemini.",
    version="0.0.2",
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


@app.get("/")
async def root():
    return {"status": "ok", "app": "Hermes API v0.0.2"}

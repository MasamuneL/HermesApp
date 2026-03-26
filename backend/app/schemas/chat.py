from pydantic import BaseModel
from typing import Optional


# Lo que el frontend MANDA
class ChatRequest(BaseModel):
    message: str
    history: Optional[list[dict]] = []  # [{role: "user"|"assistant", content: str}]


# Lo que el backend DEVUELVE
class ChatResponse(BaseModel):
    response: str  # Texto de Gemini
    intent: str | None  # Qué quiso hacer el usuario
    cached: bool  # Si vino de Redis o de Gemini


# Saludo inicial al abrir el chat
class GreetingResponse(BaseModel):
    message: str          # Mensaje que se muestra en el chat
    needs_onboarding: bool  # True si el usuario aún no tiene calendario configurado

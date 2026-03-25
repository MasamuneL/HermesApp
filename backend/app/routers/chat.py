"""
routers/chat.py — Endpoints del chatbot Hermes.

Auth: Google OAuth (access token). Un solo token sirve tanto para identificar
al usuario como para acceder a Google Calendar API.

Endpoints:
  POST /api/chat/         — Mensaje de texto al agente
  POST /api/chat/image    — Imagen de horario para OCR + registro en Calendar
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database.postgres import get_db
from app.database.crud_users import get_user_by_email
from app.database.redis_operations import get_cached_chat_response, cache_chat_response
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_orchestrator import process_message

router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ─────────────────────────────────────────────
# Auth dependency — Google OAuth
# ─────────────────────────────────────────────


async def get_current_user(authorization: str = Header()) -> dict:
    """
    Verifica el Google OAuth access token llamando al tokeninfo de Google.
    Retorna {"email": str, "google_token": str}.

    El frontend obtiene este token así:
        const result = await signInWithPopup(auth, googleProvider);
        const credential = GoogleAuthProvider.credentialFromResult(result);
        const googleToken = credential.accessToken;
        // Luego: Authorization: Bearer <googleToken>
    """
    token = authorization.removeprefix("Bearer ").strip()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": token},
                timeout=5.0,
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Token de Google inválido o expirado")

        info = resp.json()
        email = info.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="El token no contiene email")

        return {"email": email, "google_token": token}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Error al verificar el token de Google")


# ─────────────────────────────────────────────
# Schema adicional para el endpoint de imagen
# ─────────────────────────────────────────────


class ImageChatRequest(BaseModel):
    image_base64: str
    mime_type: str = "image/png"
    message: str = "Analiza este horario y registra las clases en mi calendario."


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────


@router.post("/", response_model=ChatResponse)
async def send_message_endpoint(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Recibe un mensaje de texto del usuario y retorna la respuesta del agente Hermes.

    Flujo:
    1. Verifica token de Google OAuth
    2. Busca al usuario en PostgreSQL
    3. Revisa cache de Redis — si la misma pregunta ya fue respondida, retorna directo
    4. Procesa el mensaje con el orquestador LangGraph
    5. Guarda la respuesta en Redis (TTL 1h) para futuras consultas iguales

    Headers requeridos:
    - Authorization: Bearer <google_oauth_access_token>

    Body:
    - message: texto del usuario
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado. Regístrate primero.")

    user_id = str(user.id)
    google_token = current_user["google_token"]

    # Revisar cache antes de llamar al agente
    cached = await get_cached_chat_response(body.message, user_id)
    if cached:
        return ChatResponse(response=cached, intent=None, cached=True)

    # Procesar con el orquestador LangGraph
    result = await process_message(
        message=body.message,
        user_id=user_id,
        google_token=google_token,
        is_new_user=not user.is_active,
    )

    await cache_chat_response(body.message, result["response"], user_id)

    return ChatResponse(
        response=result["response"],
        intent=result["intent"],
        cached=False,
    )


@router.post("/image", response_model=ChatResponse)
async def process_image_endpoint(
    body: ImageChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Recibe una imagen de horario en base64, la analiza con Gemini Vision
    y registra las clases en Google Calendar del usuario.

    Headers requeridos:
    - Authorization: Bearer <google_oauth_access_token>

    Body:
    - image_base64: imagen en base64
    - mime_type: "image/png" o "image/jpeg" (default: "image/png")
    - message: mensaje opcional (default: "Analiza este horario...")
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado. Regístrate primero.")

    result = await process_message(
        message=body.message,
        user_id=str(user.id),
        google_token=current_user["google_token"],
        image_base64=body.image_base64,
        image_mime_type=body.mime_type,
    )

    return ChatResponse(
        response=result["response"],
        intent=result["intent"],
        cached=False,
    )

"""
routers/chat.py — Endpoints del chatbot Hermes.

Auth: Google OAuth (access token). Un solo token sirve tanto para identificar
al usuario como para acceder a Google Calendar API.

Endpoints:
  POST /api/chat/         — Mensaje de texto al agente
  POST /api/chat/image    — Imagen de horario para OCR + registro en Calendar
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_db
from app.database.crud_users import get_user_by_email
from app.database.redis_operations import (
    get_cached_chat_response,
    cache_chat_response,
    get_onboarding_status,
    set_onboarding_complete,
)
from app.dependencies.auth import get_current_user
from app.schemas.chat import ChatRequest, ChatResponse, GreetingResponse
from app.services.llm_orchestrator import process_message
from app.services.action_tools import get_calendar_events

router = APIRouter(prefix="/api/chat", tags=["Chat"])


def _check_calendar(google_token: str) -> bool:
    """Retorna True si el usuario tiene al menos un evento en Google Calendar."""
    try:
        return len(get_calendar_events(google_token, max_results=1)) > 0
    except Exception:
        return False


async def _resolve_onboarding(user_id: str, user_name: str, google_token: str) -> bool:
    """
    Determina si el usuario necesita onboarding.
    Usa Redis como cache: si ya está marcado como completado, no llama a Calendar API.
    Marca el onboarding como completo cuando el usuario ya tiene nombre y eventos.
    Retorna True si AÚN necesita onboarding.
    """
    if await get_onboarding_status(user_id):
        return False  # ya completó onboarding

    has_calendar = _check_calendar(google_token)
    if user_name and has_calendar:
        await set_onboarding_complete(user_id)
        return False

    return True  # le falta nombre o calendario


class ImageChatRequest(BaseModel):
    image_base64: str
    mime_type: str = "image/png"
    message: str = "Analiza este horario y registra las clases en mi calendario."


@router.get("/greeting", response_model=GreetingResponse)
async def get_greeting(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna el mensaje inicial del chat al abrir la sesión.

    - Usuario nuevo / sin calendario → mensaje de onboarding de Gemini.
    - Usuario con nombre y calendario → saludo personalizado de vuelta.

    El frontend llama este endpoint al inicializar el chat (no el usuario).
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado. Regístrate primero.")

    user_id = str(user.id)
    user_name = user.full_name or current_user.get("name", "")
    google_token = current_user["google_token"]

    needs_onboarding = await _resolve_onboarding(user_id, user_name, google_token)

    if needs_onboarding:
        # Gemini genera el mensaje de bienvenida del onboarding
        result = await process_message(
            message="__init__",
            user_id=user_id,
            google_token=google_token,
            user_name=user_name,
            is_new_user=True,
            chat_history=[],
        )
        return GreetingResponse(message=result["response"], needs_onboarding=True)

    # Saludo de vuelta sin llamar a Gemini
    first_name = user_name.split()[0] if user_name else "de vuelta"
    return GreetingResponse(
        message=f"¡Hola de nuevo, {first_name}! ¿En qué puedo ayudarte hoy?",
        needs_onboarding=False,
    )


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
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado. Regístrate primero.")

    user_id = str(user.id)
    google_token = current_user["google_token"]
    user_name = user.full_name or current_user.get("name", "")

    cached = await get_cached_chat_response(body.message, user_id)
    if cached:
        return ChatResponse(response=cached, intent=None, cached=True)

    needs_onboarding = await _resolve_onboarding(user_id, user_name, google_token)

    result = await process_message(
        message=body.message,
        user_id=user_id,
        google_token=google_token,
        user_name=user_name,
        is_new_user=needs_onboarding,
        chat_history=body.history,
    )

    # Si el orquestador acaba de crear eventos (OCR o acción de calendario),
    # marcar onboarding como completo para la próxima sesión
    if needs_onboarding and result.get("calendar_result"):
        await set_onboarding_complete(user_id)

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

    if result.get("calendar_result"):
        await set_onboarding_complete(str(user.id))

    return ChatResponse(
        response=result["response"],
        intent=result["intent"],
        cached=False,
    )

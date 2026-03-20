from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from firebase_admin import auth as firebase_auth

from app.database.postgres import get_db
from app.database.crud_users import get_user_by_email
from app.database.redis_operations import get_cached_chat_response, cache_chat_response
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["Chat"])


async def get_current_user(authorization: str = Header()):
    """
    Dependency de Firebase Auth.
    Verifica el token Bearer y retorna el payload decodificado.
    """
    try:
        token = authorization.replace("Bearer ", "")
        return firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


@router.post("/", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Recibe un mensaje del usuario y retorna la respuesta de Gemini.

    Flujo:
    1. Verifica token de Firebase
    2. Revisa cache de Redis — si la misma pregunta ya fue respondida, retorna directo
    3. Si no hay cache, manda el mensaje a Gemini (llm_orchestrator.py — pendiente de implementar)
    4. Guarda la respuesta en Redis con TTL de 1 hora para futuras consultas iguales
    """
    user = await get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user_id = str(user.id)

    # Paso 2: revisar cache antes de llamar a Gemini
    cached = await get_cached_chat_response(body.message, user_id)
    if cached:
        return ChatResponse(response=cached, intent=None, cached=True)

    # Paso 3: llamar a Gemini a través del orquestador
    # TODO: implementar cuando Víctor conecte llm_orchestrator.py con Gemini
    # from app.services.llm_orchestrator import process_message
    # result = await process_message(body.message, user_id)
    # await cache_chat_response(body.message, result["response"], user_id)
    # return ChatResponse(response=result["response"], intent=result["intent"], cached=False)

    raise HTTPException(
        status_code=501,
        detail="Servicio de chat aún no implementado — esperar a que Víctor conecte Gemini",
    )

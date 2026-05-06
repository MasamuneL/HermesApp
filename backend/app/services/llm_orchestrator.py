"""
llm_orchestrator.py — Orquestador de flujo de conversación implementado con LangGraph.

Grafo de estados:
                    ┌──────────────┐
                    │  START       │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │  classify    │  ← Clasifica intención del mensaje
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┬──────────────┐
            ▼              ▼              ▼              ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
      │ question │  │ calendar │  │ image    │  │onboarding│
      │          │  │ _action  │  │ _ocr     │  │          │
      └──────────┘  └──────────┘  └──────────┘  └──────────┘
                           │              │
                    ┌──────┴──────────────┘
                    │  suggest_schedule    │
                    └──────────────────────┘
                           │
                    ┌──────┴───────┐
                    │    END       │
                    └──────────────┘

Punto de entrada: process_message()
"""

import os
import re
import json
import asyncio
import functools
import logging
from datetime import datetime, timedelta
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)

from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.services.gemini_agent import (
    send_message,
    classify_intent,
    analyze_image,
    get_llm,
    clean_markdown,
    SYSTEM_INSTRUCTION,
)
from app.services.action_tools import (
    create_calendar_event,
    get_calendar_events,
    update_calendar_event,
    delete_calendar_event,
    search_calendar_events,
)


async def _run_sync(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))


# ─────────────────────────────────────────────
# Estado del grafo
# ─────────────────────────────────────────────


class HermesStateRequired(TypedDict):
    message: str
    user_id: str
    google_token: str
    is_new_user: bool
    chat_history: list


class HermesState(HermesStateRequired, total=False):
    user_name: str
    image_base64: str
    image_mime_type: str
    intent: str
    response: str
    calendar_result: dict
    semester_start: str  # YYYY-MM-DD
    semester_end: str    # YYYY-MM-DD


# ─────────────────────────────────────────────
# Nodos del grafo
# ─────────────────────────────────────────────


async def classify_node(state: HermesState) -> dict:
    """
    Clasifica la intención del mensaje.
    Prioridad: is_new_user → image_base64 → LLM classification
    """
    if state.get("is_new_user", False):
        logger.debug(f"[HERMES] user={state['user_id']} → onboarding (sin calendario configurado)")
        return {"intent": "onboarding"}
    if state.get("image_base64"):
        logger.debug(f"[HERMES] user={state['user_id']} → image_ocr (imagen recibida)")
        return {"intent": "image_ocr"}
    intent = await classify_intent(state["message"])
    logger.debug(f"[HERMES] user={state['user_id']} → {intent} | msg='{state['message'][:60]}'")
    return {"intent": intent}


async def question_node(state: HermesState) -> dict:
    """
    Responde preguntas generales sobre el calendario del usuario.
    Enriquece el contexto con los próximos eventos antes de responder.
    """
    logger.debug(f"[HERMES][question_node] Consultando eventos y generando respuesta...")
    google_token = state.get("google_token")
    events_context = ""

    if google_token:
        try:
            events = await _run_sync(get_calendar_events, google_token, max_results=20)
            if events:
                events_context = "\n\nEventos próximos del usuario:\n"
                for e in events:
                    line = f"- {e['title']}: {e['start']} a {e['end']}"
                    if e.get("location"):
                        line += f" ({e['location']})"
                    events_context += line + "\n"
        except Exception:
            pass

    enriched = state["message"] + events_context
    response = await send_message(state.get("chat_history", []), enriched)
    return {"response": response}


async def calendar_action_node(state: HermesState) -> dict:
    """
    Maneja acciones CRUD sobre Google Calendar.
    Usa Gemini para parsear la intención en una acción concreta y ejecutarla.
    """
    logger.debug(f"[HERMES][calendar_action_node] Procesando acción de calendario...")
    google_token = state.get("google_token")
    if not google_token:
        return {
            "response": "Necesito acceso a tu Google Calendar para realizar esta acción.",
            "calendar_result": None,
        }

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.0,
    )

    # Fetch upcoming events so Gemini can resolve event_id for update/delete
    upcoming_events = []
    events_context = ""
    try:
        upcoming_events = await _run_sync(get_calendar_events, google_token, max_results=30)
        if upcoming_events:
            events_context = "\n\nEventos próximos del usuario (usa el ID exacto para update/delete):\n"
            for e in upcoming_events:
                events_context += f"- ID: {e['id']} | Título: {e['title']} | Inicio: {e['start']}\n"
    except Exception:
        pass

    parse_prompt = f"""El usuario quiere hacer una acción en su Google Calendar.
Analiza el mensaje y devuelve un JSON con la acción a realizar.

Acciones posibles: create, read, search, update, delete

Formatos de respuesta:
- create:  {{"action":"create","title":"...","start":"YYYY-MM-DDTHH:MM:SS","end":"YYYY-MM-DDTHH:MM:SS","description":"...","location":"..."}}
- read:    {{"action":"read","max_results":10}}
- search:  {{"action":"search","query":"..."}}
- update:  {{"action":"update","event_id":"<ID exacto de la lista>","title":"...","start":"YYYY-MM-DDTHH:MM:SS","end":"YYYY-MM-DDTHH:MM:SS","description":"...","location":"..."}}
- delete:  {{"action":"delete","event_id":"<ID exacto de la lista>"}}

Para update y delete DEBES usar el event_id exacto de la lista de eventos de abajo.
Si no puedes identificar el evento por ID, en delete puedes usar: {{"action":"delete","query":"nombre aproximado"}}
{events_context}
Fecha y hora actual: {datetime.now().isoformat()}
Mensaje del usuario: "{state['message']}"

Responde SOLO con el JSON, sin markdown ni explicación."""

    parse_response = await llm.ainvoke([HumanMessage(content=parse_prompt)])

    result = None
    confirmation = "No entendí qué acción querías realizar en tu calendario."

    # Gemini a veces envuelve el JSON en ```json ... ``` — lo limpiamos
    raw = parse_response.content.strip()
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    raw = json_match.group(1).strip() if json_match else raw

    try:
        action_data = json.loads(raw)
        action = action_data.get("action")

        if action == "create":
            # Devolvemos los datos al frontend para que el usuario confirme.
            # El frontend muestra la tarjeta de confirmación y crea el evento
            # via POST /api/calendar/events al confirmar.
            start_str = action_data.get("start", "")
            end_str   = action_data.get("end", "")
            return {
                "response": json.dumps({
                    "titulo":      action_data.get("title", "Nuevo evento"),
                    "fecha":       start_str[:10],
                    "hora":        start_str[11:16],
                    "hora_fin":    end_str[11:16],
                    "descripcion": action_data.get("description"),
                }),
                "intent": "crear_evento",
                "calendar_result": None,
            }

        elif action == "read":
            events = await _run_sync(
                get_calendar_events, google_token, max_results=action_data.get("max_results", 10)
            )
            result = {"events": events}
            if events:
                resumen = ". ".join(
                    f"{e['title']} el {e['start']}" for e in events[:5]
                )
                confirmation = f"Tienes {len(events)} eventos próximos. Los primeros son: {resumen}."
            else:
                confirmation = "No tienes eventos próximos en tu calendario."

        elif action == "search":
            query = action_data.get("query", "")
            events = await _run_sync(search_calendar_events, google_token, query=query)
            result = {"events": events}
            if events:
                resumen = ". ".join(f"{e['title']} el {e['start']}" for e in events)
                confirmation = f"Encontré {len(events)} eventos sobre '{query}': {resumen}."
            else:
                confirmation = f"No encontré eventos relacionados con '{query}'."

        elif action == "delete":
            event_id = action_data.get("event_id")
            if not event_id and action_data.get("query"):
                found = await _run_sync(
                    search_calendar_events, google_token, query=action_data["query"], max_results=1
                )
                if found:
                    event_id = found[0]["id"]
                    event_title = found[0]["title"]
                    result = await _run_sync(delete_calendar_event, google_token, event_id)
                    confirmation = f"Eliminé el evento '{event_title}'."
                else:
                    confirmation = f"No encontré el evento '{action_data.get('query')}' para eliminar."
            elif event_id:
                result = await _run_sync(delete_calendar_event, google_token, event_id)
                confirmation = "Evento eliminado correctamente."

        elif action == "update":
            event_id = action_data.get("event_id")
            if not event_id and action_data.get("query"):
                found = await _run_sync(
                    search_calendar_events, google_token, query=action_data["query"], max_results=1
                )
                if found:
                    event_id = found[0]["id"]
                else:
                    confirmation = f"No encontré el evento '{action_data.get('query')}' para actualizar."
                    event_id = None
            if event_id:
                result = await _run_sync(
                    update_calendar_event,
                    google_token=google_token,
                    event_id=event_id,
                    title=action_data.get("title"),
                    start=action_data.get("start"),
                    end=action_data.get("end"),
                    description=action_data.get("description"),
                    location=action_data.get("location"),
                )
                confirmation = f"Actualicé el evento '{result.get('title', 'seleccionado')}'."

    except Exception as e:
        logger.error(f"[HERMES][calendar_action_node] Error: {e}")
        confirmation = "Tuve un problema procesando la acción del calendario. Intenta de nuevo."
        result = None

    return {"response": confirmation, "calendar_result": result}


async def image_ocr_node(state: HermesState) -> dict:
    """
    Procesa una imagen de horario con Gemini Vision.
    Extrae las clases y las registra en Google Calendar como eventos semanales recurrentes.
    """
    logger.debug(f"[HERMES][image_ocr_node] Analizando imagen de horario con Gemini Vision...")
    image_base64 = state.get("image_base64")
    mime_type = state.get("image_mime_type", "image/png")
    google_token = state.get("google_token")

    if not image_base64:
        return {"response": "No se recibió ninguna imagen para analizar."}

    ocr_result = await analyze_image(image_base64, mime_type)
    classes = ocr_result.get("classes", [])
    conversational = ocr_result.get("conversational", "")

    if google_token and classes:
        day_map = {
            "Lunes": 0,
            "Martes": 1,
            "Miércoles": 2,
            "Miercoles": 2,
            "Jueves": 3,
            "Viernes": 4,
            "Sábado": 5,
            "Sabado": 5,
            "Domingo": 6,
        }
        # Fin de semestre por defecto: 4 meses desde hoy
        semester_end = (datetime.now() + timedelta(weeks=16)).strftime("%Y%m%dT000000Z")
        created_count = 0

        for cls in classes:
            target_weekday = day_map.get(cls.get("dia", ""))
            if target_weekday is None:
                continue

            today = datetime.now()
            days_ahead = (target_weekday - today.weekday()) % 7 or 7
            next_date = today + timedelta(days=days_ahead)

            try:
                hi = cls.get("hora_inicio", "07:00")
                hf = cls.get("hora_fin", "08:00")
                start_dt = next_date.strftime(f"%Y-%m-%dT{hi}:00")
                end_dt = next_date.strftime(f"%Y-%m-%dT{hf}:00")

                await _run_sync(
                    create_calendar_event,
                    google_token=google_token,
                    title=cls.get("materia", "Clase"),
                    start=start_dt,
                    end=end_dt,
                    description=f"Profesor: {cls.get('maestro', 'Sin maestro')}",
                    location=cls.get("salon", ""),
                    recurrence=[f"RRULE:FREQ=WEEKLY;UNTIL={semester_end}"],
                )
                created_count += 1
            except Exception:
                pass

        if created_count > 0:
            conversational += (
                f"\n\nRegistré {created_count} clases en tu Google Calendar "
                f"como eventos semanales recurrentes."
            )

    return {"response": conversational}


async def onboarding_node(state: HermesState) -> dict:
    """
    Guía al usuario nuevo a través del flujo de onboarding.

    Flujo:
    1. Saluda al usuario por su nombre (viene de Google OAuth).
    2. Explica brevemente qué puede hacer Hermes.
    3. Pide que suba una imagen de su horario de clases para configurar el calendario.
    4. Una vez subido el horario, confirma que todo quedó registrado.
    """
    logger.debug(f"[HERMES][onboarding_node] Iniciando flujo de onboarding...")

    chat_history = state.get("chat_history", [])
    user_name = state.get("user_name", "")
    first_name = user_name.split()[0] if user_name else ""

    name_line = f"El nombre del usuario es {first_name}." if first_name else ""

    onboarding_system = f"""Eres Hermes, asistente académico para universitarios.
{name_line}
El usuario acaba de entrar por primera vez. Sigue este flujo de forma natural y amigable:
1. Si el historial está vacío, salúdalo por su nombre y explica en 1-2 frases qué puede hacer Hermes (organizar su calendario, recordarle eventos, agendar clases).
   Luego pídele que suba una foto de su horario de clases para configurar su calendario automáticamente.
2. Si el usuario responde con preguntas o comentarios, respóndelos brevemente y vuelve a pedir la imagen del horario.
3. Cuando el horario ya haya sido registrado (el sistema lo confirmará), felicítalo y dile que ya puede hacer preguntas sobre su semana.

Determina en qué paso estás según el historial. NO uses asteriscos, emojis ni markdown. Sé breve y directo."""

    # Si es el mensaje de inicialización del sistema, no lo incluimos en el historial de usuario
    user_message = state["message"]
    lc_messages = [SystemMessage(content=onboarding_system)]
    for msg in chat_history:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        else:
            lc_messages.append(AIMessage(content=msg["content"]))

    if user_message != "__init__":
        lc_messages.append(HumanMessage(content=user_message))
    else:
        # Gemini requiere al menos un HumanMessage — __init__ solo activa el saludo inicial
        lc_messages.append(HumanMessage(content="Hola."))

    llm = get_llm()
    response = await llm.ainvoke(lc_messages)
    return {"response": clean_markdown(response.content)}


async def suggest_schedule_node(state: HermesState) -> dict:
    """
    Sugiere ajustes al itinerario del usuario basándose en sus eventos de Calendar.
    Considera el contexto completo del calendario antes de proponer horarios.
    """
    logger.debug(f"[HERMES][suggest_schedule_node] Generando sugerencias de horario...")
    google_token = state.get("google_token")
    events_context = ""

    if google_token:
        try:
            events = await _run_sync(get_calendar_events, google_token, max_results=30)
            if events:
                events_context = "\n\nEventos del usuario en las próximas semanas:\n"
                for e in events:
                    line = f"- {e['title']}: {e['start']} a {e['end']}"
                    if e.get("description"):
                        line += f" | {e['description']}"
                    events_context += line + "\n"
        except Exception:
            pass

    suggest_system = f"""Eres Hermes, asistente académico inteligente.
El usuario quiere sugerencias sobre su horario o plan de estudio.
{events_context}
Analiza los eventos del usuario y propone ajustes concretos y útiles.
Cuando sugieras horarios, menciona días y horas específicas.
NO uses asteriscos, emojis ni markdown. Sé conversacional y directo."""

    llm = get_llm()
    response = await llm.ainvoke(
        [
            SystemMessage(content=suggest_system),
            HumanMessage(content=state["message"]),
        ]
    )
    return {"response": clean_markdown(response.content)}


# ─────────────────────────────────────────────
# Routing y construcción del grafo
# ─────────────────────────────────────────────


def route_intent(state: HermesState) -> str:
    """Determina a qué nodo ir según la intención clasificada."""
    return state.get("intent", "question")


def _build_graph():
    graph = StateGraph(HermesState)

    graph.add_node("classify", classify_node)
    graph.add_node("question", question_node)
    graph.add_node("calendar_action", calendar_action_node)
    graph.add_node("image_ocr", image_ocr_node)
    graph.add_node("onboarding", onboarding_node)
    graph.add_node("suggest_schedule", suggest_schedule_node)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        route_intent,
        {
            "question": "question",
            "calendar_action": "calendar_action",
            "image_ocr": "image_ocr",
            "onboarding": "onboarding",
            "suggest_schedule": "suggest_schedule",
        },
    )
    graph.add_edge("question", END)
    graph.add_edge("calendar_action", END)
    graph.add_edge("image_ocr", END)
    graph.add_edge("onboarding", END)
    graph.add_edge("suggest_schedule", END)

    return graph.compile()


# Grafo compilado — se instancia una vez al importar el módulo
hermes_graph = _build_graph()


# ─────────────────────────────────────────────
# Punto de entrada público
# ─────────────────────────────────────────────


async def process_message(
    message: str,
    user_id: str,
    google_token: str,
    is_new_user: bool = False,
    user_name: str = "",
    chat_history: Optional[list] = None,
    image_base64: Optional[str] = None,
    image_mime_type: str = "image/png",
) -> dict:
    """
    Procesa un mensaje del usuario y retorna la respuesta del agente.

    Args:
        message: Mensaje de texto del usuario.
        user_id: ID del usuario en la base de datos.
        google_token: OAuth access token de Google (para Calendar API).
        is_new_user: Si es True, fuerza el flujo de onboarding.
        chat_history: Historial previo [{role, content}, ...].
        image_base64: Imagen en base64 (opcional, activa el nodo OCR).
        image_mime_type: Tipo MIME de la imagen.

    Returns:
        Dict con:
            - "response": Texto de respuesta para el usuario.
            - "intent": Intención detectada.
            - "calendar_result": Resultado de la operación de Calendar (o None).
    """
    initial_state: HermesState = {
        "message": message,
        "user_id": user_id,
        "google_token": google_token,
        "is_new_user": is_new_user,
        "user_name": user_name,
        "chat_history": chat_history or [],
    }
    if image_base64:
        initial_state["image_base64"] = image_base64
        initial_state["image_mime_type"] = image_mime_type

    result = await hermes_graph.ainvoke(initial_state)

    return {
        "response": result.get("response", "No pude procesar tu mensaje."),
        "intent": result.get("intent", "question"),
        "calendar_result": result.get("calendar_result"),
    }

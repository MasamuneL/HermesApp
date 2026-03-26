"""
gemini_agent.py — Conexión directa con Gemini 2.5 Flash via langchain-google-genai.

Responsabilidades:
- Envío de mensajes de texto con historial de conversación
- Análisis de imágenes de horarios (vision/OCR)
- Clasificación de intención del usuario
"""

import os
import re
import json
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


SYSTEM_INSTRUCTION = """Eres Hermes, un asistente académico inteligente para universitarios.
Sigue estas REGLAS ESTRICTAS:
1. Escribe en texto plano, conversacional y amigable. Usa puntos y comas para separar tus ideas y generar pausas naturales.
2. Al inicio de la conversación, cuando el usuario te diga su nombre, salúdalo por su nombre y sé amable. Recuérdalo y úsalo en la conversación. Si no sabes su nombre, habla normalmente sin mencionarlo.
3. NO le pidas el horario de clases hasta que el usuario te haya dicho su nombre.
4. Sé proactivo: si el usuario tiene tareas o exámenes próximos, recuérdaselos de forma natural."""


def get_llm(temperature: float = 0.6) -> ChatGoogleGenerativeAI:
    """Retorna una instancia configurada de Gemini 2.5 Flash."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=temperature,
    )


def clean_markdown(text: str) -> str:
    """Elimina artefactos de markdown para output de texto natural."""
    return text.replace("**", "").replace("```", "").strip()


def _build_lc_messages(chat_history: list[dict], new_message: str) -> list:
    """
    Convierte el historial de chat al formato de LangChain.

    Args:
        chat_history: Lista de dicts {"role": "user"|"assistant", "content": str}.
        new_message: Mensaje actual del usuario.

    Returns:
        Lista de mensajes LangChain con el system prompt prepended.
    """
    messages = [SystemMessage(content=SYSTEM_INSTRUCTION)]
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=new_message))
    return messages


async def send_message(chat_history: list[dict], message: str) -> str:
    """
    Envía un mensaje de texto a Gemini con el historial de conversación.

    Args:
        chat_history: Historial previo de la conversación.
        message: Mensaje actual del usuario.

    Returns:
        Respuesta de Gemini como texto limpio.
    """
    llm = get_llm()
    messages = _build_lc_messages(chat_history, message)
    response = await llm.ainvoke(messages)
    return clean_markdown(response.content)


async def classify_intent(message: str) -> str:
    """
    Clasifica la intención del mensaje del usuario.

    Returns:
        Una de: 'calendar_action' | 'suggest_schedule' | 'question'
    """
    llm = get_llm(temperature=0.0)
    prompt = f"""Clasifica la siguiente intención del usuario en UNA de estas categorías:
- calendar_action: el usuario quiere crear, editar, eliminar o buscar eventos en su calendario
- suggest_schedule: el usuario quiere sugerencias o ajustes sobre su horario o plan de estudio
- question: pregunta general sobre sus eventos, materias, o asistencia académica

Mensaje: "{message}"
Responde SOLO con el nombre de la categoría, sin explicación ni puntuación."""

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    intent = response.content.strip().lower().split()[0]
    if intent not in ["calendar_action", "suggest_schedule", "question"]:
        intent = "question"
    return intent


async def analyze_image(image_base64: str, mime_type: str = "image/png") -> dict:
    """
    Analiza una imagen de horario escolar con Gemini Vision.

    Extrae las materias, días, horas, salones y profesores de la imagen.

    Args:
        image_base64: Imagen en base64.
        mime_type: Tipo MIME de la imagen (image/png, image/jpeg).

    Returns:
        Dict con:
            - "conversational": Resumen natural para mostrar al usuario.
            - "classes": Lista de dicts con los datos de cada clase.
              Cada clase: {materia, dia, maestro, salon, hora_inicio, hora_fin}
    """
    llm = get_llm(temperature=0.3)

    prompt = """Eres Hermes. Analiza este horario escolar universitario.
1. Escribe un resumen de las materias AGRUPADAS POR DIA.
2. Para sonar natural, usa frases cortas separadas por puntos.
   Ejemplo: "Para el dia Lunes. Tienes la clase de Matematicas. De 7 a 9. En el salon H 202."
3. AL FINAL del resumen, pregunta: "¿Deseas hacer algun cambio?"
4. NO USES ASTERISCOS, EMOJIS ni markdown.
5. MUY IMPORTANTE: Incluye ESTRICTAMENTE un bloque JSON con este formato exacto para que el sistema lo procese:
```json
{"clases": [
  {"materia": "nombre", "dia": "Lunes", "maestro": "Sin maestro", "salon": "H 202", "hora_inicio": "07:00", "hora_fin": "08:55"}
]}
```"""

    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
            },
            {"type": "text", "text": prompt},
        ]
    )

    response = await llm.ainvoke([SystemMessage(content=SYSTEM_INSTRUCTION), message])
    text = response.content

    # Extraer el bloque JSON de la respuesta
    match = re.search(r"```json(.*?)```", text, re.DOTALL)
    classes = []
    if match:
        try:
            data = json.loads(match.group(1).strip())
            classes = data.get("clases", [])
        except Exception:
            pass
        conversational = re.sub(r"```json.*?```", "", text, flags=re.DOTALL).strip()
    else:
        conversational = text

    return {
        "conversational": clean_markdown(conversational),
        "classes": classes,
    }

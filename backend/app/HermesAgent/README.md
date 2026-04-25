# HermesAgent — Prototipo de escritorio (referencia histórica)

> **Este directorio es el prototipo original de Víctor, no el backend del web app.**
> El backend real está en `backend/app/` (FastAPI + routers + services).

---

## ¿Qué es `hermes_app.py`?

Es una aplicación de escritorio autónoma construida con **tkinter** que sirvió como prueba de concepto antes de que el equipo adoptara la arquitectura web. Corre de forma completamente independiente: no usa FastAPI, no se conecta a PostgreSQL ni Redis, y no requiere autenticación.

### Lo que hace

- Chat con Gemini Flash (conversación con historial en memoria)
- TTS con gTTS + pygame (el servidor genera el audio)
- Grabación de voz con sounddevice (5 segundos fijos) → enviada a Gemini como audio
- Escaneo de imagen de horario con Gemini Vision → extrae materias y las guarda en SQLite
- Panel de edición de clases (tabla tkinter con CRUD directo a SQLite)

### Por qué ya no se desarrolla

Todas sus funciones están implementadas en la arquitectura web:

| Feature | `hermes_app.py` | Web app |
|---------|----------------|---------|
| Chat Gemini | tkinter + SDK directo | `calendario.html` → `/api/chat` → LangGraph |
| TTS | gTTS server-side | Web Speech API (browser) |
| Voice input | sounddevice 5s | SpeechRecognition API (browser) |
| Horario | SQLite local | Google Calendar API |
| Auth | ninguna | Google OAuth (GIS) |

---

## Dependencias exclusivas de este prototipo

Estas librerías **no están** en `requirements.txt` del backend web y no deben agregarse:

```
sounddevice
scipy
gTTS
pygame
tkinter (nativa de Python)
```

---

## Para correrlo de forma aislada (opcional)

```bash
pip install sounddevice scipy gTTS pygame sqlalchemy python-dotenv google-genai
# Crear un .env con GOOGLE_API_KEY=tu_clave
python backend/app/HermesAgent/hermes_app.py
```

# Hermes App — Organizador Académico con IA

Hermes es una aplicación web para estudiantes universitarios. Combina un calendario inteligente con Google Calendar, un chatbot con Gemini Flash y gamificación con ranking en tiempo real.

## Flujo principal

1. **Login** — El usuario entra con su cuenta Google (Google Identity Services).
2. **Calendario** — Sus eventos de Google Calendar se sincronizan automáticamente.
3. **Chat con Gemini** — Le habla a Hermes en lenguaje natural: "¿qué tengo mañana?", "crea una clase de Cálculo el lunes a las 9".
4. **Motivación** — El sistema asigna puntos por actividad y muestra un ranking en tiempo real.

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | HTML5 + CSS + JavaScript (sin framework) |
| Backend | Python 3.12 + FastAPI (async) |
| Auth | Google OAuth 2.0 via Google Identity Services (GIS) |
| IA | Google Gemini Flash + LangGraph (chat + function calling) |
| Calendario | Google Calendar API |
| Base de datos | PostgreSQL 15 (SQLAlchemy 2.0 async + asyncpg) |
| Cache / Ranking | Redis 7 (sorted sets para leaderboard) |
| Deployment | Docker Compose (Dennis / Oscar) |

---

## Estructura del proyecto

```
HermesApp/
├── backend/
│   └── app/
│       ├── main.py                  # Entry point FastAPI
│       ├── dependencies/
│       │   └── auth.py              # Verificación de token Google OAuth
│       ├── database/                # Modelos SQLAlchemy + CRUDs
│       │   ├── postgres.py          # Conexión async a PostgreSQL
│       │   ├── user.py              # Modelo User
│       │   ├── ranking.py           # Modelo Ranking
│       │   ├── crud_users.py        # CRUD de usuarios
│       │   └── redis_operations.py  # Cache, sesiones y ranking en Redis
│       ├── schemas/                 # Modelos Pydantic (contrato frontend ↔ backend)
│       │   ├── users.py
│       │   ├── ranking.py
│       │   ├── chat.py
│       │   └── achievements.py
│       ├── routers/                 # Endpoints de la API
│       │   ├── users.py             # /api/users
│       │   ├── calendar.py          # /api/calendar
│       │   ├── chat.py              # /api/chat
│       │   ├── ranking.py           # /api/ranking
│       │   └── logros.py            # /api/logros
│       ├── services/                # Lógica de IA
│       │   ├── gemini_agent.py      # Conexión con Gemini API
│       │   ├── llm_orchestrator.py  # LangGraph: clasifica intención y ejecuta acción
│       │   └── action_tools.py      # Funciones que Gemini puede invocar
│       └── HermesAgent/
│           └── hermes_app.py        # Prototipo de escritorio de Víctor (referencia)
├── Frontend/
│   ├── login.html                   # Login con Google
│   ├── main.html                    # Dashboard principal
│   ├── calendario.html              # Calendario + chat con Gemini
│   ├── perfil.html
│   ├── ranking.html
│   ├── logros.html
│   └── auth.js                      # Módulo de autenticación (GIS)
├── docker-compose.yml               # PostgreSQL + Redis + backend
├── backend/Dockerfile
├── .env.example                     # Plantilla de variables de entorno
├── .gitignore
├── CLAUDE.md                        # Decisiones de arquitectura (para Claude Code)
└── AVANCES.md                       # Estado del proyecto y pendientes
```

---

## Configuración local

### Requisitos
- Docker Desktop
- Python 3.12+ (solo si corres el backend fuera de Docker)
- Chrome o Edge (para voice input con SpeechRecognition API)

### Pasos

**1. Clonar y pararse en la rama de desarrollo**
```bash
git clone https://github.com/MasamuneL/HermesApp.git
cd HermesApp
git checkout feature/google-oauth
```

**2. Configurar variables de entorno**
```bash
cp .env.example .env
```
Edita `.env` y llena:
- `GEMINI_API_KEY` — obtenla en [Google AI Studio](https://aistudio.google.com/app/apikey)
- `GOOGLE_CLIENT_ID` — ya está en el `.env.example` (el del proyecto)

**3. Levantar servicios con Docker**
```bash
docker-compose up --build
```
Esto levanta PostgreSQL, Redis y el backend FastAPI en `http://localhost:8000`.

**4. Aplicar el schema de base de datos (primera vez)**
```bash
docker exec -i hermes_postgres psql -U hermes_user -d hermes < backend/database/schema.sql
```

**5. Abrir el frontend**

Abre `Frontend/login.html` directamente en Chrome o sirve la carpeta con Live Server (VS Code).

La documentación interactiva de la API estará en: `http://localhost:8000/docs`

### Requisito de Google Cloud Console

El OAuth Client ID necesita `http://localhost` en **Authorized JavaScript origins**. Si ves error de origen no autorizado, agrégalo en:
> Google Cloud Console → APIs & Services → Credentials → tu OAuth 2.0 Client ID → Authorized JavaScript origins

---

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/users/register` | Registra o devuelve el usuario autenticado |
| `GET`  | `/api/users/me` | Perfil del usuario |
| `GET`  | `/api/calendar/events` | Lista eventos de Google Calendar |
| `POST` | `/api/calendar/events` | Crea un evento en Google Calendar |
| `POST` | `/api/chat/` | Envía mensaje a Gemini (con historial) |
| `GET`  | `/api/ranking/top` | Top N del leaderboard (público) |
| `GET`  | `/api/ranking/me` | Posición y puntos del usuario |
| `GET`  | `/api/logros/me` | Logros del usuario |

Todos los endpoints protegidos requieren `Authorization: Bearer <google_access_token>`.

---

## Equipo

| Integrante | Rol |
|-----------|-----|
| Víctor (Ferrokanon) | Backend + prototipo Gemini |
| Oswaldo | Frontend (HTML, CSS, JS) |
| Alan (MasamuneL) | APIs, schemas, auth, project management |
| Ángel | Bases de datos (schema SQL) |
| Dennis | Deployment (Docker) |
| Oscar | CI/CD |
| Álvaro | Comodín |
| Martin | DB: tabla achievements + campos User |

---

## Reglas del equipo

1. **Nunca trabajar directamente en `main`** — siempre crear una rama descriptiva.
2. **Pull Request antes de mergear** — un compañero debe revisar.
3. **No subir `.env`** al repo bajo ninguna circunstancia.

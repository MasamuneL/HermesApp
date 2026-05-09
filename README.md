# Hermes App — Organizador Académico con IA

Hermes es una app web para estudiantes universitarios. Combina un calendario inteligente con Google Calendar, un chatbot con Gemini Flash, gamificación con ranking en tiempo real y un sistema de logros.

## Flujo principal

1. **Login** — El usuario entra con su cuenta Google (Google Identity Services).
2. **Calendario** — Sus eventos de Google Calendar se sincronizan automáticamente.
3. **Chat con Gemini** — Le habla a Hermes en lenguaje natural: "¿qué tengo mañana?", "crea una clase de Cálculo el lunes a las 9", o sube una foto de su horario.
4. **Voz** — Dictado por micrófono y respuestas leídas en voz alta (Web Speech API).
5. **Motivación** — El sistema asigna puntos por actividad y muestra un ranking en tiempo real con logros desbloqueables.

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | HTML5 + Tailwind CSS + TypeScript (sin framework) |
| Servidor web | Nginx (sirve frontend + proxea API) |
| Backend | Python 3.12 + FastAPI (async) |
| Auth | Google OAuth 2.0 via Google Identity Services (GIS) |
| IA | Google Gemini Flash + LangGraph (chat + function calling) |
| Calendario | Google Calendar API |
| Base de datos | PostgreSQL 15 (SQLAlchemy 2.0 async + asyncpg) |
| Cache / Ranking | Redis 7 (sorted sets para leaderboard) |
| Deployment | Docker Compose (4 servicios: postgres, redis, backend, frontend) |

---

## Estructura del proyecto

```
HermesApp/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── static/
│   │   └── fotos/                   # Fotos de perfil subidas por usuarios
│   └── app/
│       ├── main.py                  # Entry point FastAPI (aplica schema al arrancar)
│       ├── dependencies/
│       │   └── auth.py              # Verificación de token Google OAuth (tokeninfo)
│       ├── database/                # Modelos SQLAlchemy + CRUDs
│       │   ├── postgres.py          # Conexión async a PostgreSQL
│       │   ├── schema.sql           # DDL completo de la base de datos
│       │   ├── user.py              # Modelo User
│       │   ├── ranking.py           # Modelo Ranking
│       │   ├── achievement.py       # Modelo Achievement
│       │   ├── crud_users.py        # CRUD de usuarios
│       │   ├── crud_achievements.py # CRUD de logros
│       │   └── redis_operations.py  # Cache, sesiones y ranking en Redis
│       ├── schemas/                 # Modelos Pydantic (contrato frontend ↔ backend)
│       │   ├── users.py
│       │   ├── ranking.py
│       │   ├── chat.py
│       │   ├── calendar.py
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
│       └── achievements/
│           ├── achievements_config.py  # Definición de todos los logros
│           └── achievement_service.py  # Lógica de desbloqueo de logros
├── Frontend/
│   ├── Dockerfile                   # Nginx que sirve el frontend
│   ├── nginx.conf                   # Proxea /api/ y /static/ al backend
│   ├── login.html                   # Login con Google (GIS)
│   ├── main.html                    # Dashboard principal
│   ├── calendario.html              # Calendario + chat con Gemini + voz
│   ├── perfil.html                  # Perfil de usuario con foto
│   ├── ranking.html                 # Leaderboard con avatares
│   ├── logros.html                  # Sistema de logros
│   └── auth.js                      # Módulo de autenticación (GIS)
├── docker-compose.yml               # PostgreSQL + Redis + backend + frontend (Nginx)
├── .env.example                     # Plantilla de variables de entorno
├── .gitignore
└── CLAUDE.md                        # Decisiones de arquitectura (para Claude Code)
```

---

## Configuración local

### Requisitos
- Docker y Docker Compose

### Pasos

**1. Clonar el repositorio**
```bash
git clone https://github.com/MasamuneL/HermesApp.git
cd HermesApp
```

**2. Configurar variables de entorno**
```bash
cp .env.example .env
```
Edita `.env` y llena:
- `GEMINI_API_KEY` — obtenla en [Google AI Studio](https://aistudio.google.com/app/apikey)
- `POSTGRES_PASSWORD` — contraseña para la base de datos local
- `GOOGLE_CLIENT_ID` — ya está en el `.env.example` (el del proyecto)

**3. Levantar todos los servicios**
```bash
docker-compose up --build
```
Esto levanta PostgreSQL, Redis, el backend FastAPI y el frontend con Nginx.
El schema de la base de datos se aplica automáticamente al arrancar.

**4. Abrir la app**

| Servicio | URL |
|----------|-----|
| Frontend | `http://localhost` |
| API docs (Swagger) | `http://localhost/api/docs` → redirige a `http://localhost:8000/docs` |
| Backend directo | `http://localhost:8000` |

### Requisito de Google Cloud Console

El OAuth Client ID necesita `http://localhost` en **Authorized JavaScript origins**. Si ves error de origen no autorizado, agrégalo en:
> Google Cloud Console → APIs & Services → Credentials → tu OAuth Client ID → Authorized JavaScript origins

---

## Endpoints de la API

Todos los endpoints marcados con 🔒 requieren `Authorization: Bearer <google_access_token>`.

### Usuarios `/api/users`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/users/register` | 🔒 | Registra o devuelve el usuario autenticado (upsert) |
| `GET`  | `/api/users/me` | 🔒 | Perfil del usuario |
| `PUT`  | `/api/users/me` | 🔒 | Actualiza nombre, carrera, semestre |
| `POST` | `/api/users/foto` | 🔒 | Sube foto de perfil (multipart/form-data) |
| `PUT`  | `/api/users/puntos` | 🔒 | Actualiza puntos del usuario |
| `DELETE` | `/api/users/me` | 🔒 | Desactiva la cuenta (soft delete) |

### Calendario `/api/calendar`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET`  | `/api/calendar/events` | 🔒 | Lista eventos de Google Calendar |
| `POST` | `/api/calendar/events` | 🔒 | Crea un evento en Google Calendar |

### Chat `/api/chat`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET`  | `/api/chat/greeting` | 🔒 | Saludo inicial personalizado de Gemini |
| `POST` | `/api/chat/` | 🔒 | Envía mensaje a Gemini (con historial de conversación) |
| `POST` | `/api/chat/image` | 🔒 | Procesa imagen (ej: foto de horario) con Gemini Vision |

### Ranking `/api/ranking`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET`  | `/api/ranking/top` | público | Top N del leaderboard con avatares |
| `GET`  | `/api/ranking/me` | 🔒 | Posición y puntos del usuario autenticado |

### Logros `/api/logros`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET`   | `/api/logros/me` | 🔒 | Lista de logros del usuario (desbloqueados y bloqueados) |
| `PATCH` | `/api/logros/{ach_id}` | 🔒 | Activa/desactiva un logro del usuario |

---

## Funcionalidades destacadas

- **Chat con historial** — el contexto de la conversación persiste durante la sesión
- **Gemini Vision** — sube una foto de tu horario impreso y Gemini lo interpreta
- **TTS** — las respuestas de Gemini se leen en voz alta (Web Speech API, `es-MX`)
- **Voice input** — dictado por micrófono con auto-envío (Chrome/Edge)
- **Panel de horario semanal** — FAB 📋 en el calendario, muestra los próximos 7 días agrupados por día
- **Ranking con avatares** — fotos de perfil en el leaderboard en tiempo real (Redis Sorted Sets)
- **Fotos de perfil** — subida y servida desde el backend (`/static/fotos/`)
- **Schema automático** — `schema.sql` se aplica al arrancar el backend (idempotente)

---

## Equipo

| Integrante | Rol |
|-----------|-----|
| Víctor (Ferrokanon) | Backend + prototipo Gemini |
| Oswaldo | Frontend (HTML, Tailwind, TS) |
| Alan (MasamuneL) | APIs, schemas, auth, project management |
| Ángel | Bases de datos (schema SQL) |
| Dennis | Deployment (Docker) |
| Oscar | CI/CD |
| Álvaro | Comodín |

---

## Reglas del equipo

1. **Nunca trabajar directamente en `main`** — siempre crear una rama descriptiva.
2. **Pull Request antes de mergear** — un compañero debe revisar.
3. **No subir `.env`** al repo bajo ninguna circunstancia.

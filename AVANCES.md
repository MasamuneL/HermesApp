# Avances — Hermes App

Última actualización: 25 de marzo de 2026

---

## ¿Qué funciona hoy? (rama `feature/google-oauth`)

### Auth — Migrado de Firebase a Google OAuth directo
- Eliminado Firebase Admin SDK del backend y Firebase JS SDK del frontend.
- Login con Google a través de **Google Identity Services (GIS)** — un solo token de acceso con scopes `openid email profile calendar`.
- El token se verifica en el backend via `https://oauth2.googleapis.com/tokeninfo`.
- El mismo token sirve para autenticación **y** para llamar a la Google Calendar API (sin header separado).
- Nuevos archivos: `Frontend/auth.js` (reemplaza `firebase.js`), `backend/app/dependencies/auth.py` (dependency compartida).

### Backend — Todos los routers funcionales
- `main.py` con FastAPI, CORS, sin Firebase.
- **Usuarios** (`/api/users`):
  - `POST /api/users/register` — upsert: registra o devuelve usuario existente
  - `GET  /api/users/me` — perfil del usuario autenticado
  - `PUT  /api/users/me` — actualiza nombre
  - `DELETE /api/users/me` — soft delete
- **Calendario** (`/api/calendar`):
  - `GET    /api/calendar/events` — lista eventos de Google Calendar del usuario
  - `POST   /api/calendar/events` — crea evento en Google Calendar
  - `DELETE /api/calendar/events/{event_id}` — elimina evento
  - El access token del usuario se obtiene directamente desde `current_user["google_token"]`
- **Chat** (`/api/chat`):
  - `POST /api/chat/` — recibe mensaje e historial, pasa por LangGraph orchestrator, devuelve respuesta de Gemini
  - Historial de conversación soportado (`history: list[dict]` en el request)
- **Ranking** (`/api/ranking`):
  - `GET /api/ranking/top` — top N desde Redis (público)
  - `GET /api/ranking/me` — posición y puntos del usuario
- **Logros** (`/api/logros`):
  - `GET /api/logros/me` — estructura lista, pendiente tabla de Martin

### Servicios de IA — Conectados
- `gemini_agent.py` — corregida variable de entorno (`GEMINI_API_KEY`, no `GOOGLE_API_KEY`)
- `llm_orchestrator.py` — LangGraph clasificando intención y ejecutando acciones
- `action_tools.py` — herramientas que Gemini puede invocar (Google Calendar)

### Frontend — Conectado al backend
- `login.html` — GIS token client, botón "Continuar con Google", redirige a `main.html`
- `main.html`, `perfil.html`, `ranking.html`, `logros.html` — todos migrados a `auth.js`
- `calendario.html` — totalmente funcional con:
  - Chat con Gemini (historial persistente en sesión)
  - **TTS** — botón 🔇/🔊, respuestas de Gemini leídas en voz (Web Speech API, `es-MX`)
  - **Voice input** — botón 🎤, dictado con auto-envío (Chrome/Edge)
  - **Panel de horario semanal** — FAB 📋, eventos de los próximos 7 días agrupados por día, botón "Editar" pre-llena el chat de Gemini

### Infraestructura
- `docker-compose.yml` — PostgreSQL 15 + Redis 7 + backend FastAPI (con `--reload`)
- `backend/Dockerfile` — Python 3.12-slim con gcc y libpq-dev para asyncpg
- `.env.example` actualizado: sin Firebase, hosts correctos (`postgres`, `redis`)

---

## Pendiente

| Qué | Quién | Estado |
|-----|-------|--------|
| Tabla `achievements` en PostgreSQL | Martin | Bloqueado (pendiente Martin) |
| Agregar `carrera` y `semestre` al modelo `User` | Martin | Bloqueado (pendiente Martin) |
| Aplicar `schema.sql` al contenedor Docker de PostgreSQL | Dennis / Alan | Pendiente |
| Mergear `feature/google-oauth` a `main` | Alan | Pendiente (falta prueba end-to-end) |
| Prueba end-to-end: Docker + `.env` real + schema | Todo el equipo | Pendiente |
| Corregir bug `is_new_user` en `users.py` (siempre es `False`) | Alan / Víctor | Identificado, no bloqueante |
| Persistencia de historial de chat en Redis/PostgreSQL | Víctor | Nice-to-have |
| CI/CD pipeline | Dennis / Oscar | En progreso (branch `oscar_ci/cd`) |

---

## Decisiones de arquitectura — actualizadas

- **Auth**: Google OAuth directo con GIS. Se eliminó Firebase porque Google lo discontinuará. Un solo access token con scope de calendario.
- **Calendario**: Google Calendar API como fuente de verdad.
- **IA**: Gemini Flash con LangGraph como orchestrator. Gemini clasifica intención → backend ejecuta acción.
- **Achievements**: Tabla separada en PostgreSQL (Martin la implementará), no JSONB en `rankings`.
- **Ranking en tiempo real**: Redis Sorted Sets.
- **TTS / Voz**: Web Speech API del navegador (sin costo de servidor, sin dependencias extra).

---

## Cómo correr el proyecto localmente

```bash
# 1. Clonar y pararse en la rama correcta
git clone https://github.com/MasamuneL/HermesApp.git
cd HermesApp
git checkout feature/google-oauth

# 2. Variables de entorno
cp .env.example .env
# Llenar: GEMINI_API_KEY y verificar GOOGLE_CLIENT_ID

# 3. Levantar PostgreSQL, Redis y backend con Docker
docker-compose up --build

# 4. Aplicar el schema de base de datos (una sola vez)
docker exec -i hermes_postgres psql -U hermes_user -d hermes < backend/database/schema.sql

# API docs en: http://localhost:8000/docs
# Frontend: abrir Frontend/login.html en el navegador (o servir con Live Server)
```

> **Nota**: El frontend hace fetch a `http://localhost:8000`. Para que Google OAuth funcione, `http://localhost` debe estar en los **Authorized JavaScript origins** de tu OAuth Client ID en Google Cloud Console.

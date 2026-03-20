# Avances — Hermes App

Última actualización: 19 de marzo de 2026

---

## ¿Qué funciona hoy?

### Backend — Estructura base completa
- `main.py` configurado con FastAPI, CORS y Firebase Admin SDK inicializado al arrancar.
- 4 routers registrados y documentados en `/docs`:
  - `POST /api/users/register` — registra al usuario en PostgreSQL tras el primer login con Firebase
  - `GET  /api/users/me` — retorna el perfil del usuario autenticado
  - `PUT  /api/users/me` — actualiza el nombre del usuario
  - `DELETE /api/users/me` — desactiva la cuenta (soft delete)
  - `GET  /api/ranking/top` — top N del leaderboard desde Redis (público)
  - `GET  /api/ranking/me` — posición y puntos del usuario en el ranking global
  - `POST /api/chat/` — estructura lista, pendiente conectar Gemini
  - `GET  /api/logros/me` — estructura lista, pendiente tabla de Martin

### Base de datos — Modelos y CRUDs listos
- Modelos SQLAlchemy: `User`, `CalendarEvent`, `Ranking`
- CRUDs completos: `crud_users.py`, `crud_events.py`
- Operaciones Redis: cache de chat, ranking con sorted sets, sesiones con TTL

### Schemas Pydantic — Contrato frontend ↔ backend
- `UserResponse`, `RankingResponse`, `ChatRequest`, `ChatResponse`, `AchievementsResponse`

### Configuración y documentación
- `.env.example` con todas las variables necesarias
- `.gitignore` protegiendo `.env` y `firebase-credentials.json`
- `CLAUDE.md` con decisiones de arquitectura del proyecto
- `README.md` actualizado con stack real, estructura real y pasos de instalación
- `PLAN.txt` con plan de entrega al 23 de marzo

---

## Pendiente (por integrante)

| Qué | Quién | Bloqueado por |
|-----|-------|---------------|
| Descargar `firebase-credentials.json` y probar login | Víctor | — |
| Implementar `llm_orchestrator.py` con Gemini 3.0 Flash | Víctor | firebase-credentials |
| Implementar `gemini_agent.py` y `action_tools.py` | Víctor | llm_orchestrator |
| Conectar frontend con todos los endpoints | Oswaldo | routers listos ✓ |
| Restaurar `docker-compose.yml` (PostgreSQL + Redis) | Dennis | — |
| Integrar Google Calendar API | Alan / Ángel | — |
| Tabla de `achievements` en la DB | Martin | — |
| Agregar `carrera` y `semestre` al modelo `User` | Martin | — |
| Mergear todas las branches a `main` | Alan | — |

---

## Decisiones de arquitectura tomadas

- **Auth**: Firebase Auth (Google OAuth + email/password). El backend solo verifica tokens, no maneja contraseñas.
- **Calendario**: Google Calendar API como fuente de verdad (no se construye calendario propio).
- **IA**: Gemini 3.0 Flash con function calling. Gemini interpreta el mensaje, el backend ejecuta la acción.
- **Achievements**: Tabla separada en PostgreSQL (Martin la implementará), no JSONB en `rankings`.
- **Ranking en tiempo real**: Redis Sorted Sets — lectura O(log n), no toca PostgreSQL.
- **Cache de chat**: Redis con TTL de 1 hora — evita llamar a Gemini para preguntas repetidas.

---

## Cómo correr el proyecto localmente

```bash
# 1. Clonar
git clone https://github.com/MasamuneL/HermesApp.git
cd HermesApp

# 2. Variables de entorno
cp .env.example .env
# Edita .env con tus credenciales

# 3. Agregar firebase-credentials.json en la raíz (pedírselo a Víctor)

# 4. Levantar DB y Redis
docker-compose up -d

# 5. Instalar dependencias
pip install -r requirements.txt

# 6. Correr servidor
uvicorn app.main:app --reload

# API docs en: http://localhost:8000/docs
```

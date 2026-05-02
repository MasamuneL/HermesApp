**HERMES App — Contexto para Claude Code**  
**¿Qué es HERMES?**  
App web de productividad académica para universitarios. Calendario inteligente, gamificación (ranking/logros), chatbot con Gemini Flash, y funciones sociales.  
**Stack**  
- **Backend**: Python + FastAPI (async)  
- **ORM**: SQLAlchemy 2.0 async + asyncpg  
- **DB principal**: PostgreSQL (usuarios, ranking, logros, amigos, chat)  
- **Cache/Ranking real-time**: Redis (sorted sets, sesiones, cache de chat)  
- **IA**: Gemini 3.0 Flash (chatbot con function calling)  
- **Auth**: Firebase Auth (Google OAuth + email/password)  
- **Calendario**: Decisión pendiente entre Google Calendar API o PostgreSQL propio  
- **Frontend**: HTML + Tailwind CSS + TypeScript (sin framework)  
**Estructura del proyecto**  
backend/  
 └── app/  
     ├── main.py                  ← Entry point FastAPI (POR IMPLEMENTAR)  
     ├── database/                ← YA EXISTE  
     │   ├── postgres.py          ← Conexión async + get_db() dependency  
     │   ├── user.py              ← Modelo User  
     │   ├── event.py             ← Modelo CalendarEvent  
     │   ├── ranking.py           ← Modelo Ranking  
    │   ├── crud_users.py        ← CRUD completo de usuarios  
     │   ├── crud_events.py       ← CRUD completo de eventos  
     │   └── redis_operations.py  ← Cache chat, ranking sorted set, sesiones  
     ├── services/                ← YA EXISTE (archivos vacíos)  
     │   ├── gemini_agent.py      ← Conexión con Gemini API  
     │   ├── llm_orchestrator.py  ← Decide intención del usuario  
     │   └── action_tools.py      ← Funciones que Gemini puede ejecutar  
     ├── schemas/                 ← NUEVO (Pydantic models)  
     │   ├── ranking.py  
     │   ├── users.py  
     │   ├── chat.py  
     │   └── achievements.py  
     └── routers/                 ← NUEVO (endpoints/APIs)  
         ├── auth.py  
         ├── users.py  
         ├── events.py  
         ├── chat.py  
         └── ranking.py  
   
**Decisiones de arquitectura tomadas**  
**Auth: Firebase Auth**  
- Dos métodos: Google OAuth y email/password  
- Firebase maneja encriptación de contraseñas internamente — NO guardar contraseñas en PostgreSQL  
- Backend solo verifica tokens con firebase_admin.auth.verify_id_token()  
- Si el usuario se registra con email/password y quiere usar Google Calendar, debe vincular su cuenta Google con linkWithPopup()  
- El campo password_hash del modelo User probablemente no se necesita  
**Calendario: Google Calendar API**
- Se usa Google Calendar API como fuente de verdad (razón: proyecto universitario, no hay tiempo para construir calendario desde cero)
- Los CRUDs de eventos en crud_events.py y el modelo CalendarEvent quedan en standby — no se usarán por ahora
- La sincronización del teléfono viene gratis con esta decisión
**Gemini: Solo para lenguaje natural**  
- Acciones directas (clicks, formularios) → fetch directo al backend, sin Gemini  
- Mensajes en chat → pasan por Gemini para interpretar intención → backend ejecuta la acción  
- Gemini NO ejecuta funciones directamente, usa function calling para pedirle al backend que las ejecute  
**Ranking y gamificación**  
- Puntos se suman automáticamente cuando el usuario completa acciones  
- Racha diaria = días consecutivos de actividad en la app (no de tareas)  
- El campo last_activity del modelo Ranking se usa para calcular la racha  
- Ranking global usa Redis Sorted Sets para lectura rápida  
**Schemas (Pydantic)**  
- Solo crear Request schemas para endpoints que RECIBEN datos (POST, PUT)  
- Siempre crear Response schemas para lo que DEVUELVE el backend  
- Usar ConfigDict(from_attributes=True) para convertir objetos SQLAlchemy  
- Los schemas son el "contrato" entre frontend y backend  
**Decisiones pendientes de implementación (le toca a Martin)**
- Agregar campos carrera y u_degree al modelo User
- Crear tabla separada para achievements (no JSONB en rankings)
- Los nombres de campos en los schemas no coinciden con la DB (ej: usr_id vs id, nombre vs full_name, puntos vs points) — alinear cuando Martin entregue los modelos
**Patrones de código**  
**Cómo crear un router**  
from fastapi import APIRouter, Depends  
 from app.schemas.ranking import RankingResponse  
 from app.database.redis_operations import get_top_ranking  
 from app.database.postgres import get_db  
   
 router = APIRouter()  
   
 @router.get("/api/ranking/top")  
 async def top_ranking():  
     ranking = await get_top_ranking(10)  
     return {"success": True, "data": ranking}  
   
**Cómo registrar routers en main.py**  
from fastapi import FastAPI  
 from fastapi.middleware.cors import CORSMiddleware  
 from app.routers import auth, users, events, chat, ranking  
   
 app = FastAPI()  
   
 app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  
   
 app.include_router(auth.router)  
 app.include_router(users.router)  
 app.include_router(events.router)  
 app.include_router(chat.router)  
 app.include_router(ranking.router)  
   
**Cómo verificar token de Firebase en el backend**  
import firebase_admin  
 from firebase_admin import auth as firebase_auth  
 from fastapi import Header, HTTPException, Depends  
   
 async def get_current_user(authorization: str = Header()):  
     token = authorization.replace("Bearer ", "")  
     try:  
         decoded = firebase_auth.verify_id_token(token)  
         return decoded  
     except:  
         raise HTTPException(status_code=401, detail="Token inválido")  
   
**Cómo el frontend llama al backend**  
// GET — pedir datos  
 const response = await fetch("http://localhost:8000/api/ranking/top");  
 const data = await response.json();  
   
 // POST — enviar datos  
 const response = await fetch("http://localhost:8000/api/chat", {  
     method: "POST",  
     headers: {  
         "Content-Type": "application/json",  
         "Authorization": "Bearer " + token  
     },  
     body: JSON.stringify({ message: "¿Qué tengo mañana?" })  
 });  
   
**Equipo**  
- **Víctor (Ferrokanon)** — Backend. Prototipo monolítico con Gemini (branch Ferrokanon-patch-1, archivo hermes_app.py)  
- **Oswaldo** — Frontend. HTML, Tailwind CSS, TypeScript  
- **Alan (MasamuneL)** — APIs y Project Management. Owner del repo en GitHub, schemas Pydantic  
- **Ángel** — Bases de datos en general. Schema SQL completo (branch angel/database-models)  
- **Dennis** — Deployment (branch oscar_ci/cd junto con Oscar)  
- **Oscar** — Deployment, CI/CD  
- **Álvaro** — Comodín (apoya donde se necesite)  

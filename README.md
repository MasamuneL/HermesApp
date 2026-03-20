# Hermes App — Organizador Académico con IA

Hermes es una aplicación web para estudiantes universitarios. Transforma horarios físicos en calendarios digitales inteligentes y motiva el estudio mediante gamificación y un ranking en tiempo real.

## Flujo principal

1. **Login** — El usuario entra con Google o email/password a través de Firebase Auth.
2. **Captura** — Sube una foto de su horario en papel.
3. **Procesamiento** — Gemini 3.0 Flash lee la imagen y extrae materias, horarios y salones.
4. **Calendario** — La información se sincroniza en Google Calendar automáticamente.
5. **Motivación** — El sistema asigna puntos por actividad y muestra un ranking en tiempo real.

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | HTML5 + Tailwind CSS + TypeScript (sin framework) |
| Backend | Python 3.11+ + FastAPI (async) |
| Auth | Firebase Auth (Google OAuth + email/password) |
| IA | Google Gemini 3.0 Flash (chat + OCR de horarios) |
| Calendario | Google Calendar API |
| Base de datos principal | PostgreSQL 16 (SQLAlchemy 2.0 async) |
| Cache y ranking | Redis 7 (sorted sets para leaderboard) |
| Deployment | Docker + CI/CD (Dennis y Oscar) |

---

## Estructura del proyecto

```
HermesApp/
├── backend/
│   └── app/
│       ├── main.py              # Entry point FastAPI + init Firebase
│       ├── database/            # Modelos SQLAlchemy y CRUDs
│       │   ├── postgres.py      # Conexión async a PostgreSQL
│       │   ├── user.py          # Modelo User
│       │   ├── ranking.py       # Modelo Ranking
│       │   ├── crud_users.py    # CRUD de usuarios
│       │   └── redis_operations.py  # Cache, sesiones y ranking en Redis
│       ├── schemas/             # Modelos Pydantic (contrato frontend ↔ backend)
│       │   ├── users.py
│       │   ├── ranking.py
│       │   ├── chat.py
│       │   └── achivements.py
│       ├── routers/             # Endpoints de la API
│       │   ├── users.py         # /api/users
│       │   ├── ranking.py       # /api/ranking
│       │   ├── chat.py          # /api/chat
│       │   └── logros.py        # /api/logros
│       └── services/            # Lógica de IA (Gemini)
│           ├── gemini_agent.py
│           ├── llm_orchestrator.py
│           └── action_tools.py
├── Frontend/                    # Código del frontend (Oswaldo)
├── .env.example                 # Plantilla de variables de entorno
├── .gitignore
├── CLAUDE.md                    # Contexto y decisiones de arquitectura
└── PLAN.txt                     # Plan de entrega al 23 de marzo
```

---

## Configuración local (para desarrolladores)

### Requisitos previos
- Python 3.11+
- Docker Desktop
- Git

### Pasos

**1. Clonar el repo**
```bash
git clone https://github.com/MasamuneL/HermesApp.git
cd HermesApp
```

**2. Configurar variables de entorno**
```bash
cp .env.example .env
# Edita .env con tus credenciales reales
```

**3. Agregar credenciales de Firebase**

Descarga `firebase-credentials.json` desde Firebase Console y colócalo en la raíz del proyecto. **Nunca lo subas al repo.**

**4. Levantar PostgreSQL y Redis con Docker**
```bash
docker-compose up -d
```

**5. Instalar dependencias de Python**
```bash
pip install -r requirements.txt
```

**6. Correr el servidor**
```bash
uvicorn app.main:app --reload
```

La documentación interactiva de la API estará en: `http://localhost:8000/docs`

---

## Equipo

| Integrante | Rol |
|-----------|-----|
| Víctor (Ferrokanon) | Backend + Gemini AI |
| Oswaldo | Frontend (HTML, Tailwind, TypeScript) |
| Alan (MasamuneL) | APIs, schemas Pydantic, project management |
| Ángel | Bases de datos |
| Dennis | Deployment |
| Oscar | CI/CD |
| Álvaro | Comodín |
| Martin | DB: tabla achievements + campos User |

---

## Reglas del equipo

1. **Nunca trabajar directamente en `main`** — siempre crear una rama descriptiva (ej. `feature/google-calendar` o `fix/login-error`).
2. **Pull Request antes de mergear** — un compañero debe revisar el código.
3. **No subir `.env` ni `firebase-credentials.json`** al repo bajo ninguna circunstancia.

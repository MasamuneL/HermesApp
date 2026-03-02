
# 🕊️ HermesApp: Tu Organizador Académico con IA

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-05998b)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.0.20-orange)](https://langchain-ai.github.io/langgraph/)

Hermes es una aplicación web orientada a estudiantes. Su objetivo principal es resolver el problema de la organización del tiempo, transformando horarios físicos en calendarios digitales inteligentes y motivando el estudio mediante gamificación.

## 🚀 Flujo Principal
1. **Captura:** El usuario toma una foto de su horario escolar en papel a través de la web app.
2. **Procesamiento:** La Inteligencia Artificial (Gemini 3.0 Flash) lee la foto y extrae las clases, horas y días.
3. **Sincronización:** El sistema analiza la información y la inserta en un calendario digital, sugiriendo bloques de estudio.
4. **Motivación:** Para mantener al usuario motivado, la aplicación cuenta con un sistema de puntos y un ranking en tiempo real para competir con amigos.

---

## 🛠️ Stack Tecnológico

### **1. Frontend (El Frente)**
Es lo que el usuario ve y toca en su pantalla.
* **Lenguajes:** HTML5, CSS3 y JavaScript puro (Vanilla JS) para construir las pantallas sin dependencias pesadas.
* **Estilos:** **Tailwind CSS** para que la aplicación se vea bien en celulares y computadoras rápidamente.
* **Cámara:** **WebRTC API**, la tecnología nativa del navegador para capturar la foto del horario.
* **Componentes:** **FullCalendar**, una librería prefabricada que dibuja un calendario interactivo.

### **2. Backend (El Motor)**
Es el cerebro en el servidor que procesa los datos.
* **Lenguaje:** **Python 3.11+**.
* **Framework:** **FastAPI** para crear endpoints rápidos y seguros.
* **Orquestador de IA:** **LangGraph**, que gestiona el flujo de la conversación y decide cuándo activar herramientas (como agendar en el calendario) basándose en lo que la IA interpreta.

### **3. Bases de Datos (Almacenamiento)**
* **PostgreSQL 16:** Base de datos relacional altamente segura para guardar usuarios, amigos y eventos del calendario.
* **Redis 7:** Base de datos de "memoria rápida" para la tabla de clasificación (ranking), evitando que PostgreSQL colapse por consultas masivas.

### **4. Inteligencia Artificial**
* **Google Gemini API (3.0 Flash):** Encargada de ver la foto, leer el texto (VLM), y funcionar como el cerebro del chat inteligente mediante "Tool Calling".

---

## 📂 Estructura del Proyecto

```text
backend/
├── app/
│   ├── main.py                # Punto de entrada de FastAPI
│   ├── api/                   # Rutas web (auth, calendar, users)
│   ├── database/              # Modelos de SQLAlchemy y migraciones (Alembic)
│   └── services/              # LÓGICA DEL ORQUESTADOR (IA)
│       ├── llm_orchestrator.py # Coordinador principal de LangGraph
│       ├── gemini_agent.py    # Nodo de razonamiento IA (Agente único para MVP)
│       ├── action_tools.py    # Herramientas (Google Calendar / Pushbullet)
│       └── schemas/           # Modelos Pydantic (Estado del Grafo)
├── docker-compose.yml         # Contenedores para Postgres y Redis
└── .env.example               # Plantilla de variables de entorno y secretos

```

---

## ⚙️ Configuración del Entorno (Para Desarrolladores)

### **Programas Necesarios**

Antes de escribir código, instala en tu computadora:

1. Python (Versión 3.11 o superior).
2. Docker Desktop.
3. Git.

### **Pasos para Iniciar**

1. **Clonar el repositorio y configurar variables:**
```bash
git clone [https://github.com/tu-usuario/HermesApp.git](https://github.com/tu-usuario/HermesApp.git)
cd HermesApp
cp backend/.env.example backend/.env  # Edita el .env con tus contraseñas y API Keys

```


2. **Encender las bases de datos vacías (Docker):**
```bash
docker-compose up -d postgres redis

```


3. **Crear las tablas en la base de datos (Alembic):**
```bash
alembic upgrade head

```


4. **Instalar dependencias y encender el motor principal:**
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

```


*Nota: Este proyecto utiliza LangChain 0.1.0 y Pydantic 2.5.3 para asegurar compatibilidad con el orquestador.*

---

## 🗺️ Pasos de Desarrollo (Hoja de Ruta del MVP)

Para no abrumarnos, construiremos la aplicación en 6 fases ordenadas. **No se debe avanzar a la siguiente fase sin terminar la anterior.**

### **FASE 1: Preparación y Almacenamiento (La Base)**

* Crear la estructura de carpetas y el archivo de configuraciones secretas (`.env`).
* Traducir el mapa de la base de datos a código Python (modelos de PostgreSQL).

### **FASE 2: El Motor Principal y la Seguridad**

* Sistema de ingreso seguro (Autenticación OAuth2/JWT).
* Crear funciones básicas de usuarios (solicitudes de amistad).
* Crear funciones CRUD del calendario.

### **FASE 3: Orquestador de Inteligencia Artificial (LangGraph)**

* Diseñar el prompt del sistema para Gemini 3.0 Flash.
* Crear la ruta de escaneo de imágenes.
* Implementar el Orquestador con LangGraph para que la IA pueda insertar eventos directamente en la base de datos.

### **FASE 4: Interfaz Visual (Frontend Vanilla)**

* Navegación fluida (SPA) entre chat, calendario y ranking.
* Módulo de Cámara WebRTC en JavaScript.
* Conectar visualmente FullCalendar con la base de datos.

### **FASE 5: Competencia y Tareas Automáticas**

* Asignación de puntos en la base de datos por acciones realizadas.
* Configurar el trabajador invisible (Scheduler) para actualizar el ranking en Redis cada 5 minutos.
* Alertas automáticas de superación en el ranking.

### **FASE 6: Pruebas y Lanzamiento**

* Empaquetar el proyecto completo en Docker.
* Pruebas generales de usuario (Simulacro).
* Despliegue en la nube.

---

## 🤝 Reglas para Trabajar en Equipo

1. **Ramas (Branches):** Nunca trabajar sobre el archivo principal (`main`). Siempre crea una rama aislada explicando qué se está haciendo (ej. `feature/camara-de-fotos` o `fix/error-login`).
2. **Revisiones (PRs):** Una vez terminado el trabajo en la rama, pide a un compañero que revise el código mediante un Pull Request antes de mezclarlo.
3. **Dependencias:** No actualizar versiones de librerías de IA sin consultarlo con el equipo, ya que puede romper el orquestador.


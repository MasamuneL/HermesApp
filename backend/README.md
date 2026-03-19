# Hermes App - Asistente Escolar
**Documentación y Manual de Usuario**

## Descripción
Hermes es un asistente virtual académico interactivo impulsado por Inteligencia Artificial. Está diseñado para ayudarte a gestionar tu horario escolar, organizar la información de tus clases y mantener un registro detallado de los contactos de tus profesores.

---

## Requisitos y Tecnologías Utilizadas
Para que Hermes funcione correctamente, el sistema integra diversas tecnologías, herramientas de Google y librerías de Python:

### 1. Herramientas de Google (Ecosistema IA)
* **Google AI Studio:** Plataforma utilizada para generar la API Key.
* **Modelo Gemini 2.5 Flash:** Motor principal de inteligencia artificial utilizado para la comprensión de texto, generación de respuestas conversacionales y Visión Artificial (análisis de imágenes del horario).
* **Google Text-to-Speech (gTTS):** Servicio de Google utilizado para convertir las respuestas de texto de Hermes en voz natural.

### 2. Librerías de Terceros (Requieren instalación vía PIP)
* **`google-genai`:** El SDK oficial y más reciente de Google para conectar el código con los modelos de Gemini.
* **`python-dotenv`:** Para cargar variables de entorno (como la API Key) de forma segura desde el archivo `.env`.
* **`sounddevice`:** Para capturar el audio del micrófono en tiempo real.
* **`scipy`:** Específicamente el módulo `scipy.io.wavfile` para guardar la grabación de voz en un formato que la IA pueda procesar.
* **`gTTS`:** Para generar los archivos de audio con la voz de Hermes.
* **`pygame`:** Para reproducir los audios generados sin bloquear la interfaz gráfica.
* **`sqlalchemy`:** Como ORM (Object-Relational Mapping) para gestionar la creación, lectura y edición de la base de datos local de manera segura.

### 3. Librerías Nativas de Python (No usan PIP)
* **`tkinter`:** Motor principal de la Interfaz Gráfica (GUI) y sus módulos `ttk`, `scrolledtext`, `filedialog` y `messagebox`.
* **`sqlite3` (vía SQLAlchemy):** Motor de base de datos local ligero.
* **`os` y `sys`:** Para interacciones con el sistema operativo y rutas.
* **`uuid`:** Para generar identificadores únicos para usuarios y archivos.
* **`json`:** Para estructurar e interpretar los datos extraídos por la IA.
* **`threading`:** Para ejecutar el motor de IA y el audio en segundo plano sin congelar la aplicación.
* **`time` y `datetime`:** Para el manejo de pausas y tiempos del sistema.
* **`re` (Regex):** Para limpiar el texto de formatos no deseados y buscar patrones específicos en las respuestas de la IA.

---

## Instalación y Configuración

1. Guarda el código principal en un archivo llamado `hermes_app.py`.
2. Abre tu terminal en la carpeta donde guardaste el archivo y ejecuta el siguiente comando para instalar todas las dependencias externas:
   ```bash
   pip install sounddevice scipy gTTS pygame sqlalchemy python-dotenv google-genai

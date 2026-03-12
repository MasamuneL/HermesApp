# README: Hermes App - Ecosistema de Gestion de Horarios con IA

## 1. Descripcion General
Hermes App es un agente inteligente diseñado para automatizar la transicion de horarios fisicos (imagenes) a entornos digitales. El sistema permite a los estudiantes registrarse, autenticarse y procesar fotografias de sus horarios escolares. 

Utilizando modelos de vision por computadora de Google Gemini 2.0 Flash, el programa identifica las materias y utiliza herramientas automaticas para estructurar la informacion en una base de datos, ofreciendo visualizaciones en formato Web (HTML) e Interfaz de Escritorio (GUI).

---

## 2. Guia de Instalacion y Configuracion

### Requisitos Previos
* Python 3.10 o superior.
* Conexion a Internet para las peticiones a la API de Google.
* Google AI Studio API Key.

### Instalacion de Dependencias
Ejecute el siguiente comando en la terminal para instalar el entorno completo:

pip install sqlalchemy aiosqlite langchain-google-genai langgraph python-dotenv

### Configuracion del Entorno (.env)
Cree un archivo llamado .env en la raiz de la carpeta del proyecto con el siguiente contenido:

GOOGLE_API_KEY=tu_clave_de_gemini_aqui
DATABASE_URL=sqlite+aiosqlite:///hermes_db.sqlite

---

## 3. Arquitectura del Backend
El motor de Hermes App esta construido sobre un stack asincrono:

* Paradigma: Programacion Orientada a Objetos (POO) con manejo de eventos asincronos (asyncio).
* ORM (Object-Relational Mapping): SQLAlchemy con motor aiosqlite para una base de datos local ligera.
* Flujo Agentico: LangGraph, que permite al modelo Gemini interactuar con el sistema de archivos y la base de datos de manera autonoma.

---

## 4. Diccionario de Librerias e Importaciones

Libreria: os / sys
Proposito: Gestion de directorios, rutas de archivos y parametros del sistema operativo.

Libreria: uuid
Proposito: Genera identificadores unicos para asegurar que cada clase y usuario sea irrepetible.

Libreria: base64
Proposito: Codifica la imagen del horario en texto para el procesamiento de la IA.

Libreria: asyncio
Proposito: Gestiona el asincronismo para evitar que la aplicacion se congele durante el procesamiento.

Libreria: sqlalchemy
Proposito: Gestiona la comunicacion con la base de datos y previene inyecciones SQL.

Libreria: langchain
Proposito: Conecta el modelo de lenguaje con mensajes y herramientas externas.

Libreria: langgraph
Proposito: Orquestador de agentes que define como la IA utiliza las herramientas de guardado.

Libreria: tkinter
Proposito: Proporciona el explorador de archivos y la ventana de visualizacion de datos.

Libreria: dotenv
Proposito: Carga de variables de entorno para proteccion de la API KEY.

---

## 5. Estructura de Datos (Modelos)

Clase Usuario (Tabla: usuarios_registrados)
Almacena el perfil del alumno.
Campos: id (UUID), nombre, correo, codigo_alumno, contrasena, semestre.

Clase ClaseDelHorario (Tabla: mis_clases_guardadas)
Almacena la informacion extraida por la IA.
Campos: id, usuario_id (Relacion FK), materia, profesor, hora_inicio, hora_fin, salon.

---

## 6. Desglose de Metodos y Funciones

Acceso y Seguridad
* preparar_base_de_datos(): Inicializa el motor y crea las tablas si el archivo .sqlite no existe.
* registrar_nuevo_alumno(): Captura y guarda los datos del usuario en la base de datos.
* iniciar_sesion(): Valida identidad mediante correo o codigo de alumno.
* menu_acceso(): Orquestador logico del inicio del programa.

Procesamiento de IA
* guardar_clase_en_postgres() (Tool): Herramienta que la IA invoca por cada clase encontrada en la foto para realizar la insercion en la base de datos.
* leer_horario_con_ia(): Funcion principal de vision. Envia la imagen a Gemini y coordina al agente para procesar la informacion.

Interfaces de Usuario
* seleccionar_imagen_con_ventana(): Abre el explorador de archivos nativo con filtros de imagen.
* crear_pagina_web(): Transforma los datos de la base de datos en un archivo HTML con diseño CSS.
* extraer_y_mostrar_interfaz(): Lanza una ventana de escritorio con un componente de tabla para visualizacion de datos.

---

## 7. Flujo de Funcionamiento
1. Inicio: Verificacion de la integridad de la base de datos local.
2. Identificacion: Registro o inicio de sesion del usuario.
3. Captura: Seleccion de la imagen del horario.
4. Extraccion: Analisis de la IA y guardado automatico de materias vinculadas al usuario.
5. Entrega: Seleccion de visualizacion entre reporte Web o Interfaz de escritorio.

---
Version: Hermes App v1.0.
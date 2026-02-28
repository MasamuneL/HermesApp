# HermesApp
====================================================================
DOCUMENTO DE DESARROLLO - PROYECTO HERMES
====================================================================

¿Que es Hermes?
Hermes es una aplicacion web orientada a estudiantes. Su objetivo principal es resolver el problema de la organizacion de tiempo. 

El flujo principal es:
1. El usuario toma una foto de su horario escolar en papel.
2. La Inteligencia Artificial lee la foto y la transforma en un calendario digital.
3. El sistema analiza los huecos libres y sugiere bloques de estudio.
4. Para mantener al usuario motivado, la aplicacion cuenta con un sistema de puntos y una tabla de clasificacion (ranking) para competir con amigos.

--------------------------------------------------------------------
TECNOLOGIAS A UTILIZAR Y SU PROPOSITO
--------------------------------------------------------------------

Para construir este proyecto, utilizaremos herramientas divididas en varias areas:

1. El Frente (Frontend): Es lo que el usuario ve y toca en su pantalla.
- HTML, CSS y JavaScript puro: Para construir las pantallas sin dependencias pesadas.
- Tailwind CSS: Una herramienta de diseño para que la aplicacion se vea bien en celulares y computadoras rapidamente.
- WebRTC: La tecnologia nativa del navegador que nos permitira encender la camara del celular o computadora para tomar la foto del horario.
- FullCalendar: Una libreria de diseño prefabricada que dibuja un calendario interactivo en la pantalla.

2. El Motor (Backend): Es el cerebro que esta en el servidor, procesa los datos y hace los calculos.
- Python: El lenguaje de programacion principal.
- FastAPI: Un marco de trabajo (framework) de Python que nos permite crear "puertas de comunicacion" (endpoints) para que el Frontend y la Base de Datos se hablen de forma rapida y segura.

3. Almacenamiento (Bases de Datos): Donde guardamos la informacion para que no se borre.
- PostgreSQL: Una base de datos relacional. Imaginala como un conjunto de hojas de calculo altamente seguras donde guardaremos los nombres de los usuarios, sus amigos, y sus eventos del calendario.
- Redis: Una base de datos de "memoria rapida". Aqui guardaremos la tabla de clasificacion (ranking) de los jugadores. Como el ranking se consulta muchas veces por segundo, usar Redis evita que PostgreSQL colapse.

4. Inteligencia Artificial:
- Google Gemini API: Sera la herramienta encargada de ver la foto del horario escolar, leer el texto, entender las columnas y filas, y devolvernos los datos ordenados. Tambien funcionara como el cerebro del chat inteligente.

--------------------------------------------------------------------
PROGRAMAS NECESARIOS PARA LOS PROGRAMADORES
--------------------------------------------------------------------
Antes de escribir una sola linea de codigo, cualquier persona que trabaje en este proyecto debe instalar en su computadora:

1. Python (Version 3.11 o superior).
2. PostgreSQL (Version 16).
3. Redis (Version 7).
4. Docker Desktop: Es un programa que crea "cajas virtuales" (contenedores) para que el codigo funcione exactamente igual en la computadora del programador que en el servidor final de internet.
5. Git: El programa para guardar el historial de cambios del codigo y trabajar en equipo sin borrar el trabajo de otros.

--------------------------------------------------------------------
PASOS DE DESARROLLO (HOJA DE RUTA DETALLADA)
--------------------------------------------------------------------
Para no abrumarnos, construiremos la aplicacion en 6 fases ordenadas. No se debe avanzar a la siguiente fase sin terminar la anterior.

FASE 1: Preparacion y Almacenamiento (La Base)
En esta fase preparamos el terreno de trabajo.
- Paso 1: Crear las carpetas del proyecto de forma ordenada (una carpeta para la base de datos, otra para las rutas de internet, otra para la seguridad).
- Paso 2: Crear el archivo de configuraciones secretas. Aqui pondremos las contraseñas de la base de datos y las claves de Google, para que no esten publicas en el codigo.
- Paso 3: Traducir el mapa de la base de datos a codigo Python. Escribiremos el codigo que le diga a PostgreSQL como deben ser las tablas de "Usuarios", "Amigos", "Logros" y "Eventos de Calendario".

FASE 2: El Motor Principal y la Seguridad (Comunicacion)
Aqui construiremos las rutas web para que la aplicacion reciba peticiones.
- Paso 1: Sistema de ingreso seguro. Programaremos la validacion para que los usuarios inicien sesion usando su cuenta de Google de forma segura (Autenticacion mediante tokens).
- Paso 2: Crear funciones basicas de usuarios. Escribir el codigo para que un usuario pueda buscar a otro y enviarle una solicitud de amistad.
- Paso 3: Crear funciones del calendario. Escribir el codigo para guardar una clase nueva, borrarla o editarla. Esto incluye la logica para que, si una clase es todos los lunes, se repita automaticamente en el calendario sin tener que crearla manualmente cada semana.

FASE 3: Inteligencia Artificial y Camara
Esta es la fase central que hace unica a la aplicacion.
- Paso 1: Diseñar las instrucciones de la Inteligencia Artificial. Escribiremos el texto exacto (prompt) que le enviara la foto a Gemini y le ordenara que nos devuelva la informacion de las clases estructurada y lista para guardar.
- Paso 2: Ruta de escaneo. Crearemos la puerta de comunicacion que reciba la fotografia desde el telefono del usuario y se la mande a la Inteligencia Artificial.
- Paso 3: Configurar el Chatbot. Le daremos permisos a Gemini para que, si el usuario le escribe "Agendame un bloque de estudio de matematicas mañana", la Inteligencia Artificial pueda insertar ese evento directamente en la base de datos del usuario.

FASE 4: Interfaz Visual (Las Pantallas del Usuario)
Aqui construiremos lo que el estudiante vera en su telefono.
- Paso 1: Navegacion fluida. Programaremos la pagina para que el usuario pueda cambiar entre el chat, su calendario y la pantalla de posiciones sin que la pagina web se ponga en blanco o tenga que recargar.
- Paso 2: Modulo de Camara. Escribiremos el codigo en JavaScript para solicitar permiso para usar la camara del celular, mostrar lo que la camara ve, capturar la foto y enviarla al servidor ocultando la complejidad al usuario.
- Paso 3: Conectar el calendario visual. Uniremos la herramienta FullCalendar con nuestra base de datos para que las clases aparezcan dibujadas como bloques de colores en la pantalla.

FASE 5: Competencia y Tareas Automaticas
Aqui le damos vida al juego y a la competencia entre amigos.
- Paso 1: Asignacion de puntos. Programaremos que cada vez que un usuario agregue una materia o estudie sus horas, la base de datos le sume puntos a su perfil.
- Paso 2: El trabajador invisible (Scheduler). Crearemos un programa en Python que viva en el fondo y despierte cada 5 minutos. Su unica tarea sera revisar los puntos de todos, ordenarlos de mayor a menor y actualizar la tabla de posiciones en la memoria rapida (Redis).
- Paso 3: Alertas. Le enseñaremos a ese trabajador invisible que, si nota que el Usuario A acaba de superar en puntos al Usuario B, mande una notificacion automatica avisandoles del cambio.

FASE 6: Pruebas y Lanzamiento a Internet
La fase final antes de que los usuarios puedan usarla.
- Paso 1: Empaquetar todo. Usaremos Docker para meter todo nuestro trabajo en contenedores (cajas virtuales) para que no haya errores al cambiar de computadora.
- Paso 2: Simulacro general. Haremos pruebas manuales pretendiendo ser un usuario: iniciaremos sesion, tomaremos una foto, veremos si el calendario se llena y revisaremos si los puntos suben.
- Paso 3: Subida a la nube. Contrataremos un servicio de internet (servidor) para subir nuestro codigo. A partir de este momento, cualquier persona con el enlace podra entrar a la aplicacion desde su telefono celular.

--------------------------------------------------------------------
COMANDOS RAPIDOS PARA EL PROGRAMADOR
--------------------------------------------------------------------
Estos son los comandos de texto que se escribiran en la terminal (consola) para encender la aplicacion durante el desarrollo:

1. Para encender las bases de datos vacias usando Docker:
   docker-compose up -d postgres redis

2. Para que Python cree las tablas vacias dentro de la base de datos:
   alembic upgrade head

3. Para encender el motor principal (FastAPI) y empezar a programar:
   uvicorn app.main:app --reload --port 8000

--------------------------------------------------------------------
REGLAS PARA TRABAJAR EN EQUIPO
--------------------------------------------------------------------
1. Nunca trabajar sobre el archivo principal del proyecto. Siempre se debe crear una "rama" (una copia de trabajo aislada) para experimentar.
2. Nombrar las copias de trabajo explicando que se esta haciendo. Ejemplo: "rama/camara-de-fotos" o "rama/reparar-error-login".
3. Una vez terminado el trabajo en la copia, pedir a otro compañero del equipo que revise el codigo antes de mezclarlo con el archivo principal.

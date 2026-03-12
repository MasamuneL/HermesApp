# Importaciones y Librerias:

import os           # Sirve para leer carpetas, archivos y rutas de tu computadora.
import sys          # Sirve para configurar opciones internas de tu sistema operativo (como Windows).
import uuid         # Sirve para generar numeros de identificacion unicos (ID) que nunca se repiten.
import base64       # Sirve para traducir una imagen a texto, asi la Inteligencia Artificial puede leerla.
import asyncio      # Sirve para que el programa pueda hacer varias cosas al mismo tiempo sin trabarse.
import webbrowser   # Sirve para abrir paginas web automaticamente en tu navegador.
from datetime import datetime # Sirve para que Python entienda y maneje formatos de fechas y horas.

# ventanas de archivos e interfaces
import tkinter as tk             # Sirve para crear ventanas e interfaces graficas basicas.
from tkinter import filedialog, ttk   # Sirve especificamente para abrir la ventana de "Buscar archivo" y crear tablas.

# Herramienta para seguridad
from dotenv import load_dotenv # Sirve para leer el archivo .env donde escondemos nuestras contrasenas.

# para conectarnos a la base de datos (Compatible con SQLite y PostgreSQL)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.future import select

# Herramientas para la Inteligencia Artificial (Google Gemini y LangChain)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent


# Configuracion y BaseDe datos
load_dotenv()


# CONFIGURACION DE LA BASE DE DATOS

# --- OPCION 1: SQLite (USO ACTUAL - LOCAL Y SIN INSTALAR NADA EXTRA) ---
# Esto creara un archivo llamado 'hermes_db.sqlite' en tu carpeta automaticamente.
ruta_base_datos = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///hermes_db.sqlite")

# --- OPCION 2: PostgreSQL (PARA EL FUTURO) ---
# Cuando decidas usar Postgres, ponle un '#' a la linea de arriba y quitale el '#' a la de abajo:
# ruta_base_datos = os.getenv("DATABASE_URL", "postgresql+asyncpg://TU_USUARIO:TU_CONTRASEÑA@localhost:5432/TU_BASE_DE_DATOS")

# Iniciamos el motor con la ruta que este activa
motor_base_datos = create_async_engine(ruta_base_datos, echo=False)
crear_sesion = async_sessionmaker(motor_base_datos, class_=AsyncSession, expire_on_commit=False)
Base_Datos = declarative_base()

# =====================================================================


# Variable global para recordar quien inicio sesion durante todo el programa
usuario_actual_id = None

# tabla para guardar los datos personales del alumno
class Usuario(Base_Datos):
    __tablename__ = "usuarios_registrados"
    
    # Se usa String(36) para que sea compatible con SQLite y genere IDs unicos tipo UUID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, nullable=False)
    correo = Column(String, unique=True, nullable=False)
    codigo_alumno = Column(String, unique=True, nullable=False)
    contrasena = Column(String, nullable=False)
    semestre = Column(String, nullable=False)

# tabla para las clases, vinculada al alumno
class ClaseDelHorario(Base_Datos):
    __tablename__ = "mis_clases_guardadas"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = Column(String(36), ForeignKey("usuarios_registrados.id"))
    materia = Column(String, nullable=False)
    profesor = Column(String)
    hora_inicio = Column(DateTime(timezone=True))
    hora_fin = Column(DateTime(timezone=True))
    salon = Column(String)

async def preparar_base_de_datos():
    async with motor_base_datos.begin() as conexion:
        await conexion.run_sync(Base_Datos.metadata.create_all)


# Registro de Usuario e inicio de sesión

async def registrar_nuevo_alumno():
    print("\n--- REGISTRO DE NUEVO ALUMNO ---")
    nombre_input = input("Ingresa tu nombre completo: ")
    correo_input = input("Ingresa tu correo electronico: ")
    codigo_input = input("Ingresa tu codigo de alumno: ")
    contra_input = input("Crea una contrasena: ")
    semestre_input = input("Ingresa tu semestre actual: ")
    
    async with crear_sesion() as sesion_bd:
        nuevo_usuario = Usuario(
            nombre=nombre_input,
            correo=correo_input,
            codigo_alumno=codigo_input,
            contrasena=contra_input,
            semestre=semestre_input
        )
        sesion_bd.add(nuevo_usuario)
        await sesion_bd.commit()
        await sesion_bd.refresh(nuevo_usuario)
        
        print("\nRegistro exitoso. Bienvenido, " + nuevo_usuario.nombre)
        return nuevo_usuario.id

async def iniciar_sesion():
    print("\n--- INICIAR SESION ---")
    identificador = input("Ingresa tu correo o tu codigo de alumno: ")
    contra_input = input("Ingresa tu contrasena: ")
    
    async with crear_sesion() as sesion_bd:
        consulta = select(Usuario).where(
            ((Usuario.correo == identificador) | (Usuario.codigo_alumno == identificador)) & 
            (Usuario.contrasena == contra_input)
        )
        resultado = await sesion_bd.execute(consulta)
        usuario_encontrado = resultado.scalar_one_or_none()
        
        if usuario_encontrado:
            print("\nSesion iniciada correctamente. Hola de nuevo, " + usuario_encontrado.nombre)
            return usuario_encontrado.id
        else:
            print("\nError: Datos incorrectos. Intentalo de nuevo.")
            return None

async def menu_acceso():
    print("=======================================")
    print(" BIENVENIDO A HERMES_APP ")
    print("=======================================")
    
    while True:
        print("\nElige una opcion:")
        print("1. Iniciar sesion")
        print("2. Registrarme como nuevo alumno")
        print("3. Salir")
        
        opcion = input("Tu eleccion (1/2/3): ")
        
        if opcion == "1":
            id_obtenido = await iniciar_sesion()
            if id_obtenido:
                return id_obtenido
        elif opcion == "2":
            id_obtenido = await registrar_nuevo_alumno()
            if id_obtenido:
                return id_obtenido
        elif opcion == "3":
            print("Saliendo del programa...")
            sys.exit()
        else:
            print("Opcion no valida.")


# IA

@tool
async def guardar_clase_en_postgres(nombre_materia: str, inicio_fecha_hora: str, fin_fecha_hora: str, nombre_salon: str, nombre_maestro: str) -> str:
    """
    Instruccion para la IA: Usar esta herramienta por CADA clase que aparezca en la foto.
    """
    global usuario_actual_id
    
    try:
        fecha_inicio_real = datetime.fromisoformat(inicio_fecha_hora.replace('Z', '+00:00'))
        fecha_fin_real = datetime.fromisoformat(fin_fecha_hora.replace('Z', '+00:00'))
        
        async with crear_sesion() as sesion_bd:
            nueva_clase = ClaseDelHorario(
                usuario_id=usuario_actual_id,
                materia=nombre_materia,
                profesor=nombre_maestro if nombre_maestro else "Sin maestro",
                hora_inicio=fecha_inicio_real,
                hora_fin=fecha_fin_real,
                salon=nombre_salon if nombre_salon else "Sin salon"
            )
            sesion_bd.add(nueva_clase)
            await sesion_bd.commit()
            
            return f"Exito: Acabo de guardar la materia de {nombre_materia}."
    except Exception as error:
        return f"error al guardar {nombre_materia}: {str(error)}"

async def leer_horario_con_ia(ruta_de_la_foto: str):
    print("\nProcesando tu horario con IA. Por favor espera...")
    
    _, extension = os.path.splitext(ruta_de_la_foto.lower())
    tipo_mime = "image/jpeg" if extension in ['.jpg', '.jpeg'] else f"image/{extension[1:]}"
    
    # Cambiamos a 2.0-flash para mayor compatibilidad
    cerebro_ia = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.1)
    
    # Definimos las instrucciones como un SystemMessage simple
    instrucciones = SystemMessage(content="""
    Eres un asistente experto en lectura de horarios. 
    1. Analiza la imagen.
    2. Por CADA materia detectada, usa la herramienta 'guardar_clase_en_postgres'.
    3. Usa formato ISO 8601 para las fechas.
    """)
    
    # Creamos el agente de la forma más básica posible (sin modificadores que den error)
    agente_trabajador = create_react_agent(
        model=cerebro_ia, 
        tools=[guardar_clase_en_postgres]
    )
    
    with open(ruta_de_la_foto, "rb") as archivo_foto:
        foto_en_texto = base64.b64encode(archivo_foto.read()).decode('utf-8')

    # IMPORTANTE: Metemos las instrucciones directamente en la lista de mensajes
    # Así la IA las lee al inicio sin importar la versión de LangGraph
    mensaje_para_ia = HumanMessage(content=[
        {"type": "text", "text": "Revisa esta foto de mi horario y guarda todas mis clases, por favor."},
        {"type": "image_url", "image_url": {"url": f"data:{tipo_mime};base64,{foto_en_texto}"}}
    ])

    # Ejecutamos pasando las instrucciones primero y luego la imagen
    await agente_trabajador.ainvoke({
        "messages": [instrucciones, mensaje_para_ia]
    })
    
    print("\n¡El procesamiento de tu horario ha terminado!")


# GENERACION DE LA PAGINA WEB ESTATICA (OPCION 1)

async def crear_pagina_web():
    global usuario_actual_id
    print("\nGenerando tu vista digital del horario...")
    
    async with crear_sesion() as sesion_bd:
        consulta = select(ClaseDelHorario).where(ClaseDelHorario.usuario_id == usuario_actual_id)
        resultado = await sesion_bd.execute(consulta)
        todas_las_clases = resultado.scalars().all()

    if not todas_las_clases:
        print("No se encontraron clases para mostrar. Asegurate de que la IA leyo la foto correctamente.")
        return

    codigo_html = "<html><head><meta charset='utf-8'><title>Mi Horario</title>"
    codigo_html += "<style>body{font-family:Arial; background:#eef2f3; padding:20px;} table{background:white; width:100%; border-collapse:collapse;} th,td{padding:15px; border: 1px solid #ddd;} th{background:#007BFF; color:white;}</style>"
    codigo_html += "</head><body><h1>Tu horario procesado</h1><table>"
    codigo_html += "<tr><th>Materia</th><th>Maestro</th><th>Salon</th></tr>"

    for clase in todas_las_clases:
        codigo_html += f"<tr><td>{clase.materia}</td><td>{clase.profesor}</td><td>{clase.salon}</td></tr>"

    codigo_html += "</table></body></html>"

    nombre_archivo_web = "mi_horario_generado.html"
    with open(nombre_archivo_web, "w", encoding="utf-8") as archivo:
        archivo.write(codigo_html)
        
    print("Abriendo tu horario en el navegador web...")
    webbrowser.open("file://" + os.path.abspath(nombre_archivo_web))



# INTERFAZ GRAFICA INTERACTIVA - Ventana Interactiva (OPCION 2)

def mostrar_ventana_interactiva(todas_las_clases):
    # Creamos la ventana de escritorio
    ventana = tk.Tk()
    ventana.title("Hermes App - Horario Interactivo")
    ventana.geometry("900x400")
    
    # Configuramos los colores y estilos
    estilo = ttk.Style()
    estilo.theme_use("clam")
    estilo.configure("Treeview.Heading", font=('Arial', 10, 'bold'), background="#007BFF", foreground="white")
    estilo.configure("Treeview", rowheight=30, font=('Arial', 10))
    
    marco = ttk.Frame(ventana)
    marco.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    scroll = ttk.Scrollbar(marco)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Preparamos las columnas
    columnas = ("materia", "maestro", "salon", "inicio", "fin")
    tabla = ttk.Treeview(marco, columns=columnas, show="headings", yscrollcommand=scroll.set)
    
    tabla.heading("materia", text="Materia")
    tabla.heading("maestro", text="Maestro")
    tabla.heading("salon", text="Salón")
    tabla.heading("inicio", text="Hora Inicio")
    tabla.heading("fin", text="Hora Fin")
    
    for col in columnas:
        tabla.column(col, width=150, anchor=tk.CENTER)
        
    # Agregamos las materias a la tabla
    for clase in todas_las_clases:
        inicio_str = clase.hora_inicio.strftime("%H:%M") if clase.hora_inicio else "N/A"
        fin_str = clase.hora_fin.strftime("%H:%M") if clase.hora_fin else "N/A"
        tabla.insert("", tk.END, values=(clase.materia, clase.profesor, clase.salon, inicio_str, fin_str))
        
    tabla.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.config(command=tabla.yview)
    
    btn_cerrar = ttk.Button(ventana, text="Cerrar", command=ventana.destroy)
    btn_cerrar.pack(pady=10)
    
    # Muestra la ventana y detiene el programa hasta que se cierre
    ventana.mainloop()

async def extraer_y_mostrar_interfaz():
    global usuario_actual_id
    print("\nGenerando tu ventana interactiva...")
    
    async with crear_sesion() as sesion_bd:
        consulta = select(ClaseDelHorario).where(ClaseDelHorario.usuario_id == usuario_actual_id)
        resultado = await sesion_bd.execute(consulta)
        todas_las_clases = resultado.scalars().all()

    if not todas_las_clases:
        print("No se encontraron clases para mostrar. Asegurate de que la IA leyo la foto correctamente.")
        return

    mostrar_ventana_interactiva(todas_las_clases)



# ORQUESTADOR PRINCIPAL

def seleccionar_imagen_con_ventana():
    # Creamos una ventana de tkinter invisible, solo la usamos para el cuadro de dialogo
    ventana_raiz = tk.Tk()
    ventana_raiz.withdraw() 
    
    # Esto asegura que la ventana de busqueda aparezca por encima de todas las demas aplicaciones
    ventana_raiz.attributes('-topmost', True)
    
    # Abrimos el explorador de archivos con filtros solo para imagenes
    ruta_seleccionada = filedialog.askopenfilename(
        title="Seleccione Imagen de horario",
        filetypes=[
            ("Imagenes de Horario", "*.png *.jpg *.jpeg *.webp"),
            ("Todos los archivos", "*.*")
        ]
    )
    
    # Destruimos la ventana invisible para liberar memoria
    ventana_raiz.destroy()
    
    return ruta_seleccionada

async def iniciar_programa():
    global usuario_actual_id
    
    # Preparamos las tablas de la base de datos
    await preparar_base_de_datos()
    
    # Mostramos el menu para que el usuario ingrese
    usuario_actual_id = await menu_acceso()
    
    # Usamos la nueva funcion para abrir el explorador de archivos
    print("\n--- CARGAR HORARIO ---")
    print("Abriendo el explorador de archivos. Por favor, selecciona la imagen de tu horario...")
    
    ruta_foto = seleccionar_imagen_con_ventana()
    
    # Verificamos si el usuario selecciono un archivo o si cerro la ventana
    if not ruta_foto:
        print("\nOperacion cancelada: No seleccionaste ninguna imagen.")
        return

    # Si selecciono algo, procesamos
    print(f"\nImagen seleccionada: {ruta_foto}")
    await leer_horario_con_ia(ruta_foto)
    
    # === SELECCION DE VISTA ===
    print("\n=======================================")
    print(" ¿COMO DESEAS VER TU HORARIO? ")
    print("=======================================")
    print("1. Generar Pagina Web")
    print("2. Abrir Ventana Interactiva")
    
    opcion_vista = input("\nElige una opcion (1 o 2): ")
    
    if opcion_vista == "1":
        await crear_pagina_web()
    elif opcion_vista == "2":
        await extraer_y_mostrar_interfaz()
    else:
        print("\nOpcion no valida. Mostrando Pagina Web por defecto...")
        await crear_pagina_web()


# Puerta de entrada del programa
if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(iniciar_programa())
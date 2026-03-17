import time
import os
import sys
import base64
import asyncio
import webbrowser
from datetime import datetime
import json

# Ventanas e interfaces
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

# Seguridad y variables de entorno
from dotenv import load_dotenv

# IA
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from sqlalchemy.future import select

# --- IMPORTACIONES MODULARES 
# Importamos la configuracion de la base de datos centralizada
from base_datos import preparar_base_de_datos, crear_sesion, ClaseDelHorario, Usuario
# Importamos el modulo que maneja el inicio de sesion y el registro del ciclo escolar
from modulo_ciclo import menu_acceso

# --- IMPORTACIONES MODULARES 
from base_datos import preparar_base_de_datos, crear_sesion, ClaseDelHorario, Usuario
from modulo_ciclo import menu_acceso
from modulo_agenda import abrir_agenda 



# Configuracion inicial
load_dotenv()
usuario_actual_id = None


# =====================================================================
# 1. MÓDULO DE IA Y GUARDADO DEL HORARIO EN BASE DE DATOS
# =====================================================================

async def guardar_clase_en_postgres(nombre_materia, dia, inicio_fecha_hora, fin_fecha_hora, nombre_salon, nombre_maestro):
    """Guarda una sola materia extraida por la IA en la base de datos."""
    global usuario_actual_id
    try:
        # Convertimos las fechas ISO que manda Gemini a objetos de Python
        fecha_inicio_real = datetime.fromisoformat(inicio_fecha_hora.replace('Z', '+00:00'))
        fecha_fin_real = datetime.fromisoformat(fin_fecha_hora.replace('Z', '+00:00'))
        
        async with crear_sesion() as sesion_bd:
            # Creamos la clase usando el modelo importado de base_datos.py
            nueva_clase = ClaseDelHorario(
                usuario_id=usuario_actual_id,
                materia=nombre_materia, 
                dia=dia,
                profesor=nombre_maestro if nombre_maestro else "Sin maestro asignado",
                contacto_profesor="[]", # Inicializado como JSON vacio (lista)
                hora_inicio=fecha_inicio_real, 
                hora_fin=fecha_fin_real,
                salon=nombre_salon if nombre_salon else "Sin salon"
            )
            sesion_bd.add(nueva_clase)
            await sesion_bd.commit()
            
            # Pausa breve para no saturar procesos
            time.sleep(1) 
            return f"Exito: Guardada la materia '{nombre_materia}' el día {dia}."
    except Exception as error:
        return f"Error al guardar '{nombre_materia}': {str(error)}"

async def leer_horario_con_ia(ruta_de_la_foto: str):
    """Toma la foto del horario, la envia a Gemini y procesa la respuesta."""
    print("\nProcesando tu horario con IA. Por favor espera...")
    _, extension = os.path.splitext(ruta_de_la_foto.lower())
    tipo_mime = "image/jpeg" if extension in ['.jpg', '.jpeg'] else f"image/{extension[1:]}"
    
    # Configuracion de Gemini
    cerebro_ia = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, max_retries=1)  
    
    with open(ruta_de_la_foto, "rb") as archivo_foto:
        foto_en_texto = base64.b64encode(archivo_foto.read()).decode('utf-8')

    instrucciones = """
    Eres un asistente experto en lectura de horarios escolares.
    Extrae TODAS las clases de la imagen. 
    Regla estricta para días: Usa Lunes, Martes, Miércoles, Jueves, Viernes, Sábado.
    Devuelve ÚNICAMENTE un objeto JSON válido con la siguiente estructura exacta:
    {"clases": [{"nombre_materia": "", "dia": "", "inicio_fecha_hora": "YYYY-MM-DDTHH:MM:SSZ", "fin_fecha_hora": "YYYY-MM-DDTHH:MM:SSZ", "nombre_salon": "", "nombre_maestro": ""}]}
    No incluyas markdown, ni comillas invertidas, solo el texto JSON puro.
    """
    mensaje = [
        {"type": "text", "text": instrucciones}, 
        {"type": "image_url", "image_url": {"url": f"data:{tipo_mime};base64,{foto_en_texto}"}}
    ]

    exito = False
    intentos = 0
    max_intentos = 3

    while not exito and intentos < max_intentos:
        try:
            respuesta = await cerebro_ia.ainvoke([HumanMessage(content=mensaje)])
            texto_respuesta = respuesta.content.strip()
            
            # Limpieza de Markdown si Gemini lo envia por error
            if texto_respuesta.startswith("```json"): 
                texto_respuesta = texto_respuesta[7:-3]
            elif texto_respuesta.startswith("```"): 
                texto_respuesta = texto_respuesta[3:-3]
                
            datos_extraidos = json.loads(texto_respuesta)
            lista_clases = datos_extraidos.get("clases", [])
            print(f"\n¡Extracción exitosa! Se encontraron {len(lista_clases)} clases.")
            
            for clase in lista_clases:
                res = await guardar_clase_en_postgres(
                    clase.get("nombre_materia"), 
                    clase.get("dia", "Sin día"), 
                    clase.get("inicio_fecha_hora"), 
                    clase.get("fin_fecha_hora"),
                    clase.get("nombre_salon", "Sin salon"), 
                    clase.get("nombre_maestro", "Sin maestro")
                )
                print(f"- {res}")
            exito = True 
            
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                intentos += 1
                print(f"\n[Aviso] Límite de IA alcanzado. Pausando automáticamente por 60 segundos... (Intento {intentos}/{max_intentos})")
                await asyncio.sleep(60)
            else:
                print(f"\nError al procesar el horario: {e}")
                print(f"Respuesta cruda de la IA: {texto_respuesta if 'texto_respuesta' in locals() else 'N/A'}")
                break


# =====================================================================
# 2. MÓDULO DE INTERFAZ GRÁFICA INTERACTIVA (VER Y EDITAR - TKINTER)
# =====================================================================

async def actualizar_clases_en_bd(datos_modificados):
    """Sube los cambios hechos en la tabla de Tkinter a la base de datos central."""
    async with crear_sesion() as sesion_bd:
        for clase_dict in datos_modificados:
            consulta = select(ClaseDelHorario).where(ClaseDelHorario.id == clase_dict["id"])
            resultado = await sesion_bd.execute(consulta)
            clase_obj = resultado.scalar_one_or_none()
            
            if clase_obj:
                clase_obj.materia = clase_dict["materia"]
                clase_obj.dia = clase_dict["dia"]
                clase_obj.profesor = clase_dict["profesor"]
                clase_obj.contacto_profesor = clase_dict["contacto"]
                clase_obj.salon = clase_dict["salon"]
                
                # Transformamos la hora en texto (HH:MM) de vuelta a objeto datetime
                try:
                    h_ini, m_ini = map(int, clase_dict["inicio"].split(":"))
                    if clase_obj.hora_inicio: 
                        clase_obj.hora_inicio = clase_obj.hora_inicio.replace(hour=h_ini, minute=m_ini)
                        
                    h_fin, m_fin = map(int, clase_dict["fin"].split(":"))
                    if clase_obj.hora_fin: 
                        clase_obj.hora_fin = clase_obj.hora_fin.replace(hour=h_fin, minute=m_fin)
                except Exception: 
                    pass # Si hay error de formato, ignoramos la hora
                    
        await sesion_bd.commit()

def recopilar_datos_tabla(tabla):
    """Extrae las filas visibles de la tabla para guardarlas."""
    datos_recolectados = []
    for fila_id in tabla.get_children():
        fila_datos = tabla.item(fila_id, 'values')
        datos_recolectados.append({
            "id": fila_datos[0],
            "materia": fila_datos[1],
            "dia": fila_datos[2],
            "profesor": fila_datos[3],
            "contacto": fila_datos[4], 
            "salon": fila_datos[5],
            "inicio": fila_datos[6],
            "fin": fila_datos[7]
        })
    return datos_recolectados

def abrir_ventana_edicion_fila(tabla, item_id, ventana_padre):
    """Abre una ventana secundaria para editar una fila especifica."""
    valores_actuales = tabla.item(item_id, 'values')
    
    ventana_edicion = tk.Toplevel(ventana_padre)
    ventana_edicion.title(f"Editar: {valores_actuales[1]}")
    ventana_edicion.geometry("400x450")
    ventana_edicion.grab_set() # Bloquea la ventana principal
    
    campos = ["Materia", "Día", "Maestro", "Contacto JSON", "Salón", "Hora Inicio (HH:MM)", "Hora Fin (HH:MM)"]
    entradas = []
    
    # Crea un formulario basado en los valores actuales
    for i, campo in enumerate(campos):
        ttk.Label(ventana_edicion, text=campo + ":").pack(pady=(10, 2), padx=20, anchor="w")
        entrada = ttk.Entry(ventana_edicion, width=40)
        # Offset de +1 porque el indice 0 es el ID oculto
        entrada.insert(0, valores_actuales[i+1])
        entrada.pack(padx=20)
        entradas.append(entrada)
        
    def guardar_cambios_locales():
        nuevos_valores = [valores_actuales[0]] + [e.get() for e in entradas]
        tabla.item(item_id, values=nuevos_valores)
        ventana_edicion.destroy()
        
    ttk.Button(ventana_edicion, text="Guardar Cambios en Tabla", command=guardar_cambios_locales).pack(pady=20)


def crear_ventana_interactiva(todas_las_clases):
    """Crea la ventana principal de Tkinter con la tabla del horario."""
    ventana = tk.Tk()
    ventana.title("Hermes App - Horario Interactivo")
    ventana.geometry("1100x550")
    
    # Diccionario para controlar el estado asíncrono
    estado_ventana = {"cerrar": False, "guardar_ahora": False, "abrir_agenda": False}
    
    # Título
    ttk.Label(ventana, text="Mi Horario Escolar", font=("Helvetica", 16, "bold")).pack(pady=10)
    
    marco = ttk.Frame(ventana)
    marco.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 5))
    scroll = ttk.Scrollbar(marco)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Configuracion de la tabla
    columnas = ("id_clase", "materia", "dia", "maestro", "contacto", "salon", "inicio", "fin")
    tabla = ttk.Treeview(marco, columns=columnas, show="headings", yscrollcommand=scroll.set)
    
    encabezados = ["ID", "Materia", "Día", "Maestro", "Contacto", "Salón", "Inicio", "Fin"]
    for col, text in zip(tabla["columns"], encabezados): 
        tabla.heading(col, text=text)
        
    # Ocultamos columnas de sistema
    tabla.column("id_clase", width=0, stretch=tk.NO)
    tabla.column("contacto", width=0, stretch=tk.NO) 
    
    # Ajustamos anchos
    anchos = {"materia": 250, "dia": 100, "maestro": 200, "salon": 100, "inicio": 80, "fin": 80}
    for col, ancho in anchos.items(): 
        tabla.column(col, width=ancho, anchor=tk.CENTER)

    # Llenamos la tabla con los datos de la BD
    for clase in todas_las_clases:
        contacto = clase.contacto_profesor if clase.contacto_profesor else "[]"
        h_ini = clase.hora_inicio.strftime("%H:%M") if clase.hora_inicio else "N/A"
        h_fin = clase.hora_fin.strftime("%H:%M") if clase.hora_fin else "N/A"
        
        tabla.insert("", tk.END, values=(
            clase.id, clase.materia, clase.dia, clase.profesor, 
            contacto, clase.salon, h_ini, h_fin
        ))
        
    tabla.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.config(command=tabla.yview)

    # --- ZONA DE BOTONES DE ACCIÓN ---
    marco_botones = ttk.Frame(ventana)
    marco_botones.pack(pady=15)
    
    def on_editar_click():
        seleccion = tabla.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Por favor selecciona una materia de la tabla primero.", parent=ventana)
            return
        abrir_ventana_edicion_fila(tabla, seleccion[0], ventana)

    btn_editar = ttk.Button(marco_botones, text="✏️ Editar Materia Seleccionada", command=on_editar_click)
    btn_editar.grid(row=0, column=0, padx=10)
    
    btn_guardar = ttk.Button(marco_botones, text="💾 Guardar Cambios en BD", 
                             command=lambda: estado_ventana.update({"guardar_ahora": True}))
    btn_guardar.grid(row=0, column=1, padx=10)
    
    # --- REQUISITO 3: BOTÓN HACIA LA AGENDA CONECTADO ---
    btn_agenda = ttk.Button(marco_botones, text="📅 Abrir Agenda Escolar", 
                            command=lambda: estado_ventana.update({"abrir_agenda": True}))
    btn_agenda.grid(row=0, column=2, padx=10)
    
    btn_cerrar = ttk.Button(marco_botones, text="✖ Cerrar Ventana", 
                            command=lambda: estado_ventana.update({"cerrar": True}))
    btn_cerrar.grid(row=0, column=3, padx=10)
    
    # Atrapa la 'X' de la ventana
    ventana.protocol("WM_DELETE_WINDOW", lambda: estado_ventana.update({"cerrar": True}))

    return ventana, tabla, estado_ventana

async def extraer_y_mostrar_interfaz():
    """Conecta la base de datos con la ventana grafica asincrona."""
    global usuario_actual_id
    
    async with crear_sesion() as sesion_bd:
        consulta = select(ClaseDelHorario).where(ClaseDelHorario.usuario_id == usuario_actual_id)
        todas_las_clases = (await sesion_bd.execute(consulta)).scalars().all()
        
    if not todas_las_clases: 
        print("\nNo se encontraron clases registradas. Por favor, sube tu horario primero (Opción 1).")
        return

    ventana, tabla, estado_ventana = crear_ventana_interactiva(todas_las_clases)
    
    try:
        # Bucle asíncrono para mantener viva la ventana de Tkinter junto con Asyncio
        while not estado_ventana["cerrar"]:
            ventana.update()
            
            if estado_ventana["guardar_ahora"]:
                estado_ventana["guardar_ahora"] = False
                await actualizar_clases_en_bd(recopilar_datos_tabla(tabla))
                messagebox.showinfo("Éxito", "Tus cambios han sido guardados exitosamente.", parent=ventana)
                
            
            if estado_ventana.get("abrir_agenda"):
                estado_ventana["abrir_agenda"] = False
                await abrir_agenda(usuario_actual_id)
            # ---------------------------------
                
            await asyncio.sleep(0.05) 
    except tk.TclError: 
        pass # La ventana se cerro a la fuerza
    finally:
        try: 
            ventana.destroy()
        except: 
            pass


# =====================================================================
# 3. MÓDULO DE GENERACIÓN DE REPORTE WEB (HTML)
# =====================================================================

async def generar_html_horario():
    """Genera una página web estática hermosa con el horario actual del usuario."""
    global usuario_actual_id
    
    async with crear_sesion() as sesion_bd:
        consulta_clases = select(ClaseDelHorario).where(ClaseDelHorario.usuario_id == usuario_actual_id)
        clases_bd = (await sesion_bd.execute(consulta_clases)).scalars().all()
        
        consulta_usuario = select(Usuario).where(Usuario.id == usuario_actual_id)
        usuario = (await sesion_bd.execute(consulta_usuario)).scalar_one_or_none()
        nombre_usuario = usuario.nombre if usuario else "Alumno"

    if not clases_bd:
        print("\nNo hay clases guardadas para generar el reporte.")
        return

    # Construccion de filas HTML
    filas_html = ""
    for clase in clases_bd:
        h_ini = clase.hora_inicio.strftime("%H:%M") if clase.hora_inicio else "--:--"
        h_fin = clase.hora_fin.strftime("%H:%M") if clase.hora_fin else "--:--"
        
        filas_html += f"""
        <tr>
            <td>{clase.materia}</td>
            <td><span class="badge dia-{clase.dia.lower()[:2] if clase.dia else 'nd'}">{clase.dia}</span></td>
            <td>{h_ini} - {h_fin}</td>
            <td>{clase.profesor}</td>
            <td>{clase.salon}</td>
        </tr>
        """

    # Plantilla HTML con CSS incrustado
    html_completo = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mi Horario - Hermes App</title>
        <style>
            :root {{
                --primary: #4F46E5; --bg: #F3F4F6; --card: #FFFFFF; --text: #1F2937;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: var(--bg); color: var(--text);
                margin: 0; padding: 40px 20px;
                display: flex; flex-direction: column; align-items: center;
            }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .header h1 {{ color: var(--primary); margin-bottom: 5px; }}
            .table-container {{
                background: var(--card); border-radius: 12px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
                overflow: hidden; width: 100%; max-width: 1000px;
            }}
            table {{ width: 100%; border-collapse: collapse; text-align: left; }}
            thead {{ background-color: var(--primary); color: white; }}
            th, td {{ padding: 16px 20px; border-bottom: 1px solid #E5E7EB; }}
            tbody tr:hover {{ background-color: #F9FAFB; }}
            .badge {{
                padding: 6px 12px; border-radius: 20px; font-size: 0.85em;
                font-weight: 600; color: white; background-color: #6B7280;
            }}
            .dia-lu {{ background-color: #EF4444; }} /* Rojo */
            .dia-ma {{ background-color: #F59E0B; }} /* Naranja */
            .dia-mi {{ background-color: #10B981; }} /* Verde */
            .dia-ju {{ background-color: #3B82F6; }} /* Azul */
            .dia-vi {{ background-color: #8B5CF6; }} /* Morado */
            .footer {{ margin-top: 30px; font-size: 0.9em; color: #6B7280; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Horario Escolar Oficial</h1>
            <p>Generado por Hermes App para: <strong>{nombre_usuario}</strong></p>
        </div>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Materia</th><th>Día</th><th>Horario</th><th>Profesor</th><th>Salón</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_html}
                </tbody>
            </table>
        </div>
        <div class="footer">Generado automáticamente el {datetime.now().strftime("%d/%m/%Y a las %H:%M")}</div>
    </body>
    </html>
    """
    
    nombre_archivo = f"Horario_{nombre_usuario.replace(' ', '_')}.html"
    ruta_absoluta = os.path.abspath(nombre_archivo)
    
    with open(nombre_archivo, "w", encoding="utf-8") as archivo:
        archivo.write(html_completo)
        
    print(f"\n¡Reporte web generado exitosamente!")
    print(f"Ruta: {ruta_absoluta}")
    
    # Abre el navegador automaticamente
    webbrowser.open(f"file://{ruta_absoluta}")


# =====================================================================
# 4. ORQUESTADOR PRINCIPAL (MENÚ DE TERMINAL)
# =====================================================================

def seleccionar_imagen_con_ventana():
    """Abre el explorador de archivos del sistema operativo para elegir la foto."""
    ventana_raiz = tk.Tk()
    ventana_raiz.withdraw() 
    ventana_raiz.attributes('-topmost', True)
    
    ruta = filedialog.askopenfilename(
        title="Seleccione Imagen del Horario", 
        filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.webp")]
    )
    ventana_raiz.destroy()
    return ruta


async def iniciar_programa():
    """Punto de entrada: Inicializa BD, Módulo de Ciclo y el Menú Principal."""
    global usuario_actual_id
    
    # 1. Preparamos las tablas (Base de Datos)
    await preparar_base_de_datos()
    
    # 2. Llamamos al módulo modularizado para Registro/Login (REQUISITO 1)
    usuario_actual_id = await menu_acceso() 
    
    # 3. Bucle Principal de la aplicación en consola
    while True:
        print("\n=======================================")
        print("        HERMES APP - MENÚ PRINCIPAL    ")
        print("=======================================")
        print("1. Cargar e interpretar NUEVO horario (IA)")
        print("2. Abrir Ventana de Horario Interactiva")
        print("3. Generar y Ver Reporte Web (HTML)")
        print("4. Salir")
        
        opcion_vista = input("\nElige una opción (1/2/3/4): ")
        
        if opcion_vista == "1":
            ruta_foto = seleccionar_imagen_con_ventana()
            if ruta_foto: 
                await leer_horario_con_ia(ruta_foto)
            else:
                print("Operación cancelada. No se seleccionó ninguna imagen.")
                
        elif opcion_vista == "2": 
            await extraer_y_mostrar_interfaz()
            
        elif opcion_vista == "3":
            await generar_html_horario()
            
        elif opcion_vista == "4": 
            print("Cerrando sistema Hermes. ¡Hasta pronto!")
            sys.exit()
            
        else:
            print("Opción inválida. Inténtalo de nuevo.")

if __name__ == "__main__":
    # Solucion para un error comun de Asyncio en Windows
    if sys.platform == 'win32': 
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    # Arrancamos la aplicación
    asyncio.run(iniciar_programa())
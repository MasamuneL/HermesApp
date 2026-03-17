# =====================================================================
# MÓDULO DE AGENDA ESCOLAR - HERMES APP
# Este módulo gestiona las tareas, proyectos y exámenes de los alumnos.
# =====================================================================

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
from sqlalchemy.future import select
from sqlalchemy import Column, Integer, String

# --- IMPORTACIÓN DE LA BASE DE DATOS ---
# NOTA: Importamos la configuración central desde tu archivo de base de datos.
# Si en tu proyecto la base de datos se llama 'Base_Datos' en lugar de 'Base', 
# ajustamos la importación dinámicamente para evitar errores.
try:
    from base_datos import Base, crear_sesion, ClaseDelHorario
except ImportError:
    try:
        from base_datos import Base_Datos as Base, crear_sesion, ClaseDelHorario
    except ImportError:
        from hermes_app import Base_Datos as Base, crear_sesion, ClaseDelHorario


# =====================================================================
# MODELO DE BASE DE DATOS (Se crea automáticamente al iniciar la app)
# =====================================================================
class TareaAgenda(Base):
    __tablename__ = 'tareas_agenda'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(String(36), nullable=False) # Vinculado al UUID del usuario
    materia_nombre = Column(String, nullable=False)
    tipo = Column(String, nullable=False)           # Tarea, Examen, Proyecto, etc.
    descripcion = Column(String, nullable=False)
    fecha_entrega = Column(String, nullable=False)
    estado = Column(String, default="Pendiente ⏳")   # Pendiente o Completada


# =====================================================================
# FUNCIONES DE BASE DE DATOS PARA LA AGENDA
# =====================================================================
async def obtener_materias_usuario(usuario_id):
    """Obtiene los nombres únicos de las materias registradas en el horario del usuario."""
    try:
        async with crear_sesion() as sesion:
            consulta = select(ClaseDelHorario.materia).where(ClaseDelHorario.usuario_id == usuario_id).distinct()
            resultado = await sesion.execute(consulta)
            materias = [materia for materia, in resultado.all()]
            return materias if materias else ["Sin materias registradas"]
    except Exception as e:
        print(f"Error al obtener materias: {e}")
        return ["Error al cargar materias"]

async def obtener_tareas(usuario_id):
    """Obtiene todas las tareas pendientes y completadas del usuario actual."""
    async with crear_sesion() as sesion:
        # Ordenamos primero por estado (Pendientes arriba) y luego por fecha
        consulta = select(TareaAgenda).where(
            TareaAgenda.usuario_id == usuario_id
        ).order_by(TareaAgenda.estado.desc(), TareaAgenda.fecha_entrega)
        
        resultado = await sesion.execute(consulta)
        return resultado.scalars().all()


# =====================================================================
# INTERFAZ GRÁFICA Y LÓGICA DE LA AGENDA
# =====================================================================
def construir_interfaz_agenda(materias, ventana_padre=None):
    """Crea la ventana de Tkinter para la Agenda con diseño mejorado."""
    ventana = tk.Toplevel(ventana_padre)
    ventana.title("Hermes App - Agenda Escolar y Tareas")
    ventana.geometry("950x600")
    ventana.minsize(800, 500)
    
    # Bloquea la ventana principal del horario mientras la agenda está abierta
    ventana.grab_set() 
    ventana.configure(bg="#f4f6f9")
    
    # --- APLICACIÓN DE ESTILOS ---
    estilo = ttk.Style()
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass
        
    estilo.configure("Treeview", background="#ffffff", foreground="black", rowheight=30, font=('Segoe UI', 10))
    estilo.map('Treeview', background=[('selected', '#0078D7')], foreground=[('selected', 'white')])
    estilo.configure("Treeview.Heading", background="#0078D7", foreground="white", font=('Segoe UI', 10, 'bold'))
    estilo.map("Treeview.Heading", background=[('active', '#005A9E')])
    
    # Variables de control asíncrono
    estado = {
        "cerrar": False,
        "nueva_tarea": None,
        "completar_id": None,
        "eliminar_id": None
    }
    
    # --- TÍTULO PRINCIPAL ---
    lbl_titulo = tk.Label(ventana, text="📅 Mi Agenda de Actividades", font=("Segoe UI", 16, "bold"), bg="#f4f6f9", fg="#2c3e50")
    lbl_titulo.pack(pady=(15, 5))

    # --- PANEL SUPERIOR: FORMULARIO DE NUEVA TAREA ---
    marco_form = tk.LabelFrame(ventana, text=" 📝 Agregar Nueva Actividad ", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=15, pady=15)
    marco_form.pack(fill=tk.X, padx=20, pady=10)
    
    var_materia = tk.StringVar()
    var_tipo = tk.StringVar()
    var_desc = tk.StringVar()
    var_fecha = tk.StringVar()
    
    # Fila 1 del formulario
    tk.Label(marco_form, text="Materia:", bg="#ffffff", font=("Segoe UI", 9)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
    combo_materia = ttk.Combobox(marco_form, textvariable=var_materia, values=materias, state="readonly", width=30)
    combo_materia.grid(row=0, column=1, padx=10, pady=5)
    if materias: combo_materia.current(0)
    
    tk.Label(marco_form, text="Tipo de Actividad:", bg="#ffffff", font=("Segoe UI", 9)).grid(row=0, column=2, padx=10, pady=5, sticky="w")
    combo_tipo = ttk.Combobox(marco_form, textvariable=var_tipo, values=["Tarea", "Examen", "Proyecto", "Lectura", "Presentación", "Trámite", "Otro"], state="readonly", width=20)
    combo_tipo.grid(row=0, column=3, padx=10, pady=5)
    combo_tipo.current(0)
    
    # Fila 2 del formulario
    tk.Label(marco_form, text="Descripción:", bg="#ffffff", font=("Segoe UI", 9)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
    entry_desc = ttk.Entry(marco_form, textvariable=var_desc, width=33)
    entry_desc.grid(row=1, column=1, padx=10, pady=5)
    
    tk.Label(marco_form, text="Fecha (Ej. 15/Oct):", bg="#ffffff", font=("Segoe UI", 9)).grid(row=1, column=2, padx=10, pady=5, sticky="w")
    entry_fecha = ttk.Entry(marco_form, textvariable=var_fecha, width=23)
    entry_fecha.grid(row=1, column=3, padx=10, pady=5)
    
    def on_agregar():
        if not var_materia.get() or not var_desc.get().strip() or not var_fecha.get().strip():
            messagebox.showwarning("Campos incompletos", "Por favor llena la descripción y la fecha de entrega.", parent=ventana)
            return
            
        estado["nueva_tarea"] = {
            "materia_nombre": var_materia.get(),
            "tipo": var_tipo.get(),
            "descripcion": var_desc.get().strip(),
            "fecha_entrega": var_fecha.get().strip()
        }
        var_desc.set("")
        var_fecha.set("")

    btn_guardar = ttk.Button(marco_form, text="➕ Guardar Actividad", command=on_agregar)
    btn_guardar.grid(row=0, column=4, rowspan=2, padx=20, pady=5, sticky="ns")

    # --- PANEL CENTRAL: TABLA DE TAREAS ---
    marco_tabla = tk.Frame(ventana, bg="#f4f6f9")
    marco_tabla.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
    
    scroll = ttk.Scrollbar(marco_tabla)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    columnas = ("id", "materia", "tipo", "descripcion", "fecha", "estado")
    tabla = ttk.Treeview(marco_tabla, columns=columnas, show="headings", yscrollcommand=scroll.set)
    
    encabezados = {"id": "ID", "materia": "Materia", "tipo": "Tipo", "descripcion": "Descripción de la Actividad", "fecha": "Fecha", "estado": "Estado"}
    anchos = {"id": 0, "materia": 180, "tipo": 120, "descripcion": 350, "fecha": 100, "estado": 120}
    
    for col in columnas:
        tabla.heading(col, text=encabezados[col])
        tabla.column(col, width=anchos[col], anchor=tk.CENTER if col != "descripcion" else tk.W)
        
    tabla.column("id", stretch=tk.NO, width=0) # Ocultar columna ID interna
    tabla.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.config(command=tabla.yview)

    # --- PANEL INFERIOR: BOTONES DE ACCIÓN RÁPIDA ---
    marco_acciones = tk.Frame(ventana, bg="#f4f6f9")
    marco_acciones.pack(pady=15)

    def on_completar():
        seleccion = tabla.selection()
        if not seleccion:
            messagebox.showinfo("Aviso", "Selecciona una tarea de la tabla primero.", parent=ventana)
            return
        estado["completar_id"] = tabla.item(seleccion[0], 'values')[0]

    def on_eliminar():
        seleccion = tabla.selection()
        if not seleccion:
            messagebox.showinfo("Aviso", "Selecciona una tarea de la tabla primero.", parent=ventana)
            return
        if messagebox.askyesno("Confirmar", "¿Estás seguro de eliminar esta actividad permanentemente?", parent=ventana):
            estado["eliminar_id"] = tabla.item(seleccion[0], 'values')[0]

    ttk.Button(marco_acciones, text="✅ Marcar como Completada", command=on_completar).grid(row=0, column=0, padx=10)
    ttk.Button(marco_acciones, text="🗑️ Eliminar Seleccionada", command=on_eliminar).grid(row=0, column=1, padx=10)
    ttk.Button(marco_acciones, text="✖ Cerrar Agenda", command=lambda: estado.update({"cerrar": True})).grid(row=0, column=2, padx=10)

    # Configurar el cierre desde la "X" de la ventana
    ventana.protocol("WM_DELETE_WINDOW", lambda: estado.update({"cerrar": True}))
    
    return ventana, tabla, estado


# =====================================================================
# BUCLE ASÍNCRONO PRINCIPAL (Conecta Interfaz con Base de Datos)
# =====================================================================
async def abrir_agenda(usuario_id):
    """
    Función principal asíncrona que gestiona la agenda.
    Se asegura de crear la tabla si no existe y maneja el flujo de datos.
    """
    # 1. Aseguramos que la tabla de la agenda exista en la base de datos
    try:
        from hermes_app import motor_base_datos
        async with motor_base_datos.begin() as conexion:
            await conexion.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"Nota: Validando tabla de agenda... ({e})")

    # 2. Obtenemos las materias del usuario para el menú desplegable
    materias = await obtener_materias_usuario(usuario_id)
        
    # 3. Construimos la ventana gráfica
    ventana, tabla, estado = construir_interfaz_agenda(materias)

    async def refrescar_tabla():
        """Limpia la tabla gráfica y vuelve a cargar los datos frescos desde la BD."""
        for item in tabla.get_children():
            tabla.delete(item)
            
        tareas_actualizadas = await obtener_tareas(usuario_id)
        for t in tareas_actualizadas:
            # Insertar en el Treeview
            item_id = tabla.insert("", tk.END, values=(t.id, t.materia_nombre, t.tipo, t.descripcion, t.fecha_entrega, t.estado))
            # Dar color verde ligero si está completada
            if "Completada" in t.estado:
                tabla.item(item_id, tags=('completada',))
                
        tabla.tag_configure('completada', background='#e6ffe6', foreground='#006600')

    # Carga inicial de datos al abrir la ventana
    await refrescar_tabla()

    try:
        # Bucle continuo: Mantiene la ventana viva y procesa las peticiones a la BD sin congelarse
        while not estado["cerrar"]:
            ventana.update()
            
            # --- LÓGICA: GUARDAR NUEVA TAREA ---
            if estado["nueva_tarea"]:
                datos = estado["nueva_tarea"]
                async with crear_sesion() as sesion:
                    nueva_tarea = TareaAgenda(usuario_id=usuario_id, **datos)
                    sesion.add(nueva_tarea)
                    await sesion.commit()
                estado["nueva_tarea"] = None
                await refrescar_tabla()

            # --- LÓGICA: COMPLETAR TAREA ---
            if estado["completar_id"]:
                async with crear_sesion() as sesion:
                    consulta = select(TareaAgenda).where(TareaAgenda.id == int(estado["completar_id"]))
                    tarea = (await sesion.execute(consulta)).scalar_one_or_none()
                    if tarea:
                        tarea.estado = "Completada ✅"
                        await sesion.commit()
                estado["completar_id"] = None
                await refrescar_tabla()

            # --- LÓGICA: ELIMINAR TAREA ---
            if estado["eliminar_id"]:
                async with crear_sesion() as sesion:
                    consulta = select(TareaAgenda).where(TareaAgenda.id == int(estado["eliminar_id"]))
                    tarea = (await sesion.execute(consulta)).scalar_one_or_none()
                    if tarea:
                        await sesion.delete(tarea)
                        await sesion.commit()
                estado["eliminar_id"] = None
                await refrescar_tabla()

            # Pequeña pausa para no saturar el procesador
            await asyncio.sleep(0.05)
            
    except tk.TclError:
        pass # Ignorar error si la ventana se cerró forzosamente desde la "X" del sistema operativo
    finally:
        try:
            ventana.destroy()
        except Exception:
            pass
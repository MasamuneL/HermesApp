# =====================================================================
# PARTE 1: IMPORTACIONES MONOLITICAS (NUEVA ARQUITECTURA)
# =====================================================================
import os
import sys
import uuid
import json
import threading
import time
import re
from datetime import datetime

# Interfaz Grafica (GUI)
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

# Audio (Escuchar y Hablar localmente)
import sounddevice as sd
from scipy.io.wavfile import write
from gtts import gTTS
import pygame

# Base de Datos (SQLAlchemy)
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

# NUEVO SDK DE GOOGLE - Inteligencia Artificial
from dotenv import load_dotenv
from google import genai
from google.genai import types

# =====================================================================
# PARTE 2: CONFIGURACION DE IA Y BASE DE DATOS
# =====================================================================
print("[BACKEND] Iniciando sistemas de Hermes Version 2.7...")

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("[ERROR BACKEND] No se encontro GOOGLE_API_KEY en el archivo .env")
    sys.exit()

cliente_ai = genai.Client(api_key=API_KEY)
print("[BACKEND] Conexion a servidores de Google establecida.")

instrucciones_sistema = """
Eres Hermes, un asistente academico inteligente.
Sigue estas REGLAS ESTRICTAS:
1. No uses formato markdown (como asteriscos) ni emojis bajo ninguna circunstancia.
2. Escribe en texto plano, conversacional y amigable. Usa puntos y comas para separar tus ideas y generar pausas naturales al hablar.
3. Al inicio de la conversacion, el sistema ya le pregunto al usuario su nombre. Cuando el usuario te responda diciendo como se llama, saludalo por su nombre y dile ESTRICTAMENTE y como unica instruccion siguiente: "Para dar inicio al proceso. ¿Me podrias proporcionar tu horario?. Puedes usar el boton Subir Horario de abajo."
4. NO le pidas el horario hasta que te haya dicho su nombre.
"""

sesion_chat = cliente_ai.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        system_instruction=instrucciones_sistema,
        temperature=0.6 
    )
)

pygame.mixer.init()

# Base de Datos Local
ruta_db = "sqlite:///hermes_unificado.sqlite"
motor_bd = create_engine(ruta_db, echo=False)
SesionBD = sessionmaker(bind=motor_bd)
Base = declarative_base()

# =====================================================================
# PARTE 3: MOLDES DE BASE DE DATOS
# =====================================================================
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, nullable=False)
    correo = Column(String, unique=True, nullable=False)
    carrera = Column(String)

class ClaseHorario(Base):
    __tablename__ = "clases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(String(36), ForeignKey("usuarios.id"))
    materia = Column(String, nullable=False)
    dia = Column(String, nullable=False)
    maestro = Column(String, default="Sin maestro")
    contacto_maestro = Column(String, default="Sin contacto")
    salon = Column(String, default="Por definir")
    hora_inicio = Column(String, default="00:00")
    hora_fin = Column(String, default="00:00")

Base.metadata.create_all(motor_bd)
print("[BACKEND] Base de datos verificada y montada.")
usuario_actual_id = "temp_user_01" 

# =====================================================================
# PARTE 4: FUNCIONES AUXILIARES
# =====================================================================
def limpiar_texto_markdown(texto):
    """Limpia asteriscos y bloques de codigo del texto final."""
    return texto.replace("**", "").replace("```", "").strip()

# =====================================================================
# PARTE 5: MOTOR MULTIMODAL
# =====================================================================

def reproducir_audio(texto):
    try:
        texto_limpio = limpiar_texto_markdown(texto)
        print(f"[BACKEND] Generando audio TTS para: '{texto_limpio[:40]}...'")
        nombre_archivo = f"hermes_voz_{uuid.uuid4().hex[:8]}.mp3"
        
        tts = gTTS(text=texto_limpio, lang='es', tld='com.mx')
        tts.save(nombre_archivo)
        
        pygame.mixer.music.load(nombre_archivo)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        
        def borrar_seguro():
            time.sleep(1)
            try: os.remove(nombre_archivo)
            except: pass
        threading.Thread(target=borrar_seguro, daemon=True).start()
        
    except Exception as e:
        print(f"[ERROR BACKEND] Error de audio: {e}")

def procesar_mensaje_texto(texto, ui_callback):
    print(f"\n[BACKEND] Enviando prompt: '{texto}'")
    try:
        respuesta = sesion_chat.send_message(texto)
        texto_limpio = limpiar_texto_markdown(respuesta.text)
        ui_callback(texto_limpio, emisor="Hermes")
        threading.Thread(target=reproducir_audio, args=(texto_limpio,), daemon=True).start()
    except Exception as e:
        ui_callback(f"Error de conexion: {e}", "Hermes")

def procesar_audio_microfono(ui_callback, ui_status_callback):
    fs = 44100
    duracion = 5 
    
    ui_status_callback("Escuchando... (5s)")
    print(f"\n[BACKEND] Grabando microfono...")
    try:
        grabacion = sd.rec(int(duracion * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        ui_status_callback("Procesando voz...")
        
        nombre_wav = f"temp_rec_{uuid.uuid4().hex[:8]}.wav"
        write(nombre_wav, fs, grabacion)
        
        with open(nombre_wav, "rb") as f:
            audio_bytes = f.read()
            
        prompt_voz = "Escucha este audio del usuario y respondele conversacionalmente. Evita usar markdown."
        respuesta = sesion_chat.send_message([types.Part.from_bytes(data=audio_bytes, mime_type='audio/wav'), prompt_voz])
        os.remove(nombre_wav)
        
        ui_status_callback("Hermes en linea")
        texto_limpio = limpiar_texto_markdown(respuesta.text)
        
        ui_callback("Mensaje de voz enviado", emisor="Tu")
        ui_callback(texto_limpio, emisor="Hermes")
        threading.Thread(target=reproducir_audio, args=(texto_limpio,), daemon=True).start()
        
    except Exception as e:
        print(f"[ERROR BACKEND] Error procesando voz: {e}")
        ui_status_callback("Hermes en linea")
        ui_callback(f"No pude procesar el audio: {e}", "Hermes")

def procesar_imagen_horario(ruta_imagen, ui_callback):
    print(f"\n[BACKEND] Iniciando escaneo de imagen: {ruta_imagen}")
    ui_callback("Horario subido. Analizando con Gemini Vision...", emisor="Tu")
    
    try:
        archivo_img = cliente_ai.files.upload(file=ruta_imagen)
        prompt = """
        Eres Hermes. Analiza este horario escolar.
        1. Escribe un resumen de las materias AGRUPADAS POR DIA.
        2. Para sonar natural al leerlo, usa frases cortas separadas por puntos. Di el dia, punto, la materia, punto, y los detalles.
        EJEMPLO DE COMO DEBES HABLAR: "Para el dia Lunes. Tienes la clase de Matematicas. De 7 a 9. En el salon H 202. Para el dia Martes. Tienes..."
        3. AL FINAL DEL RESUMEN, haz una pausa y pregunta: "¿Deseas hacer algun cambio?. Puedes usar el boton Mi Horario Detallado para editarlo."
        4. NO USES ASTERISCOS, EMOJIS ni markdown.
        5. MUY IMPORTANTE: Incluye ESTRICTAMENTE un bloque de codigo JSON con este formato exacto para que mi sistema lo lea (yo lo borrare antes de mostralo):
        ```json
        {"clases": [
          {"materia": "nombre", "dia": "Lunes", "maestro": "Sin maestro", "contacto": "Sin contacto", "salon": "H 202", "hora_inicio": "07:00", "hora_fin": "08:55"}
        ]}
        ```
        """
        respuesta = sesion_chat.send_message([archivo_img, prompt])
        cliente_ai.files.delete(name=archivo_img.name)
        
        texto_ia = respuesta.text
        
        match_json = re.search(r'```json(.*?)```', texto_ia, re.DOTALL)
        
        if match_json:
            json_str = match_json.group(1).strip()
            mensaje_conversacional_sucio = re.sub(r'```json.*?```', '', texto_ia, flags=re.DOTALL).strip()
            mensaje_conversacional = limpiar_texto_markdown(mensaje_conversacional_sucio)
            
            print("[BACKEND] JSON extraido de forma segura. Insertando en SQLite...")
            try:
                datos = json.loads(json_str)
                with SesionBD() as sesion:
                    for c in datos.get("clases", []):
                        nueva_clase = ClaseHorario(
                            usuario_id=usuario_actual_id, materia=c.get("materia",""), dia=c.get("dia",""),
                            maestro=c.get("maestro", "Sin maestro"), contacto_maestro=c.get("contacto", "Sin contacto"),
                            salon=c.get("salon", "Por definir"), hora_inicio=c.get("hora_inicio", "00:00"),
                            hora_fin=c.get("hora_fin", "00:00")
                        )
                        sesion.add(nueva_clase)
                    sesion.commit()
                print("[BACKEND] Base de datos de horario actualizada.")
            except Exception as e:
                print(f"[ERROR BACKEND] Error parseando JSON interno: {e}")
        else:
            mensaje_conversacional = limpiar_texto_markdown(texto_ia)
            
        ui_callback(mensaje_conversacional, emisor="Hermes")
        threading.Thread(target=reproducir_audio, args=(mensaje_conversacional,), daemon=True).start()
        
    except Exception as e:
        print(f"[ERROR BACKEND] Error visual: {e}")
        ui_callback(f"Tuve un problema leyendo el horario: {e}", "Hermes")

# =====================================================================
# PARTE 6: INTERFAZ GRAFICA INTERACTIVA Y PANEL DE EDICION
# =====================================================================

class HermesGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Hermes App - Asistente Escolar Unificado")
        self.root.geometry("600x750")
        self.root.configure(bg="#1E1E2E")
        self.root.minsize(400, 500)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6, relief="flat", background="#89B4FA", foreground="#11111B", font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[('active', '#B4BEFE')])

        self.lbl_status = tk.Label(root, text="Hermes en linea", bg="#181825", fg="#A6E3A1", font=("Segoe UI", 12, "bold"), pady=10)
        self.lbl_status.pack(side=tk.TOP, fill=tk.X)

        frame_botones = tk.Frame(root, bg="#1E1E2E")
        frame_botones.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 15))

        ttk.Button(frame_botones, text="Enviar", command=self.enviar_texto).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_botones, text="Voz", command=self.enviar_voz).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_botones, text="Subir Horario", command=self.abrir_explorador).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_botones, text="Mi Horario Detallado", command=self.abrir_visor_horario_ampliado).pack(side=tk.RIGHT, padx=2)

        frame_controles = tk.Frame(root, bg="#1E1E2E")
        frame_controles.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        self.entrada_texto = tk.Entry(frame_controles, font=("Segoe UI", 12), bg="#313244", fg="#CDD6F4", insertbackground="white", relief="flat")
        self.entrada_texto.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10), ipady=8)
        self.entrada_texto.bind("<Return>", lambda event: self.enviar_texto())

        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, bg="#1E1E2E", fg="#CDD6F4", font=("Segoe UI", 11), state=tk.DISABLED, padx=10, pady=10)
        self.chat_area.pack(side=tk.TOP, expand=True, fill=tk.BOTH, padx=10, pady=10)

        msg_bienvenida = "Hola. Soy Hermes, tu asistente escolar. ¿Como te llamas?"
        self.agregar_mensaje(msg_bienvenida, "Hermes")
        threading.Thread(target=reproducir_audio, args=(msg_bienvenida,), daemon=True).start()

    def agregar_mensaje(self, texto, emisor):
        self.chat_area.config(state=tk.NORMAL)
        if emisor == "Tu":
            self.chat_area.insert(tk.END, f"\nTu:\n{texto}\n", "usuario")
            self.chat_area.tag_config("usuario", foreground="#89B4FA")
        else:
            self.chat_area.insert(tk.END, f"\nHermes:\n{texto}\n", "hermes")
            self.chat_area.tag_config("hermes", foreground="#A6E3A1")
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def cambiar_estado(self, texto): self.lbl_status.config(text=texto)

    def enviar_texto(self):
        texto = self.entrada_texto.get().strip()
        if not texto: return
        self.entrada_texto.delete(0, tk.END)
        self.agregar_mensaje(texto, "Tu")
        threading.Thread(target=procesar_mensaje_texto, args=(texto, self.actualizar_ui_desde_hilo), daemon=True).start()

    def enviar_voz(self):
        threading.Thread(target=procesar_audio_microfono, args=(self.actualizar_ui_desde_hilo, self.actualizar_estado_desde_hilo), daemon=True).start()

    def abrir_explorador(self):
        ruta = filedialog.askopenfilename(title="Selecciona la imagen de tu horario", filetypes=[("Imagenes", "*.png *.jpg *.jpeg")])
        if ruta: threading.Thread(target=procesar_imagen_horario, args=(ruta, self.actualizar_ui_desde_hilo), daemon=True).start()

    def abrir_visor_horario_ampliado(self):
        ventana_horario = tk.Toplevel(self.root)
        ventana_horario.title("Hermes App - Horario Interactivo (Modo Edicion)")
        ventana_horario.geometry("900x550")
        ventana_horario.configure(bg="#1E1E2E")
        ventana_horario.grab_set()

        frame_tabla = tk.Frame(ventana_horario, bg="#1E1E2E")
        frame_tabla.pack(expand=True, fill=tk.BOTH, padx=15, pady=15)

        columnas = ("ID", "Materia", "Dia", "Maestro", "Salon", "Hora Inicio", "Hora Fin")
        tabla = ttk.Treeview(frame_tabla, columns=columnas, show="headings")
        
        for col in columnas: tabla.heading(col, text=col)
        
        tabla.column("ID", width=40, anchor="center"); tabla.column("Materia", width=250)
        tabla.column("Dia", width=100, anchor="center"); tabla.column("Maestro", width=150)
        tabla.column("Salon", width=80, anchor="center"); tabla.column("Hora Inicio", width=80, anchor="center")
        tabla.column("Hora Fin", width=80, anchor="center")
        
        scrollbar_y = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=tabla.yview)
        tabla.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        tabla.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)

        frame_contacto = tk.Frame(ventana_horario, bg="#CCCCCC", relief="solid", borderwidth=1)
        frame_contacto.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        tk.Label(frame_contacto, text="Informacion de Contacto del Maestro", bg="#CCCCCC", fg="black", font=("Segoe UI", 9, "bold"), anchor="w").pack(fill=tk.X, padx=5, pady=(2, 0))
        lbl_contacto = tk.Label(frame_contacto, text="Selecciona una clase...", bg="#CCCCCC", fg="black", font=("Segoe UI", 9), anchor="w")
        lbl_contacto.pack(fill=tk.X, padx=5, pady=(0, 5))

        clases_en_memoria = {}
        
        def recargar_tabla():
            tabla.delete(*tabla.get_children())
            clases_en_memoria.clear()
            with SesionBD() as sesion:
                clases = sesion.query(ClaseHorario).filter_by(usuario_id=usuario_actual_id).all()
                for c in clases:
                    tabla.insert("", tk.END, values=(c.id, c.materia, c.dia, c.maestro, c.salon, c.hora_inicio, c.hora_fin))
                    clases_en_memoria[c.id] = c.contacto_maestro
        
        recargar_tabla()
        
        def on_treeview_select(event):
            seleccion = tabla.selection()
            if seleccion:
                item_id = seleccion[0]
                valores = tabla.item(item_id, 'values')
                db_id = int(valores[0])
                contacto = clases_en_memoria.get(db_id, "Sin contacto guardado")
                lbl_contacto.config(text=f"Contactos de {valores[3]}: {contacto}")
        
        tabla.bind("<<TreeviewSelect>>", on_treeview_select)

        def abrir_edicion_completa():
            seleccion = tabla.selection()
            if not seleccion: return
            
            item_id = seleccion[0]
            valores = tabla.item(item_id, 'values')
            db_id = valores[0]
            contacto_actual = clases_en_memoria.get(int(db_id), "")
            
            asignatura_original = valores[1]

            edit_win = tk.Toplevel(ventana_horario)
            edit_win.title(f"Editando: {asignatura_original}")
            edit_win.geometry("500x550")
            edit_win.configure(bg="#CCCCCC")
            
            tk.Label(edit_win, text="Modifica los datos que necesites:", bg="#CCCCCC", fg="black", font=("Segoe UI", 12, "bold")).pack(pady=20)
            frame_form = tk.Frame(edit_win, bg="#CCCCCC"); frame_form.pack(expand=True)
            
            def create_entry(lbl_text, row, val):
                tk.Label(frame_form, text=f"{lbl_text}:", bg="#CCCCCC", fg="black", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="e", padx=10, pady=8)
                ent = tk.Entry(frame_form, font=("Segoe UI", 10), width=35); ent.insert(0, val); ent.grid(row=row, column=1, sticky="w")
                return ent

            ent_materia = create_entry("Materia", 0, valores[1])
            ent_dia = create_entry("Dia", 1, valores[2])
            ent_maestro = create_entry("Maestro", 2, valores[3])
            
            tk.Label(frame_form, text="Contacto Maestro:", bg="#CCCCCC", fg="black", font=("Segoe UI", 10)).grid(row=3, column=0, sticky="ne", padx=10, pady=8)
            
            frame_contactos = tk.Frame(frame_form, bg="#CCCCCC")
            frame_contactos.grid(row=3, column=1, sticky="w", pady=8)

            listbox_contactos = tk.Listbox(frame_contactos, height=4, width=35, font=("Segoe UI", 9))
            listbox_contactos.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

            if contacto_actual and contacto_actual != "Sin contacto":
                for c in contacto_actual.split(" | "):
                    if c.strip():
                        listbox_contactos.insert(tk.END, c.strip())

            frame_add_contacto = tk.Frame(frame_contactos, bg="#CCCCCC")
            frame_add_contacto.pack(side=tk.TOP, fill=tk.X)

            combo_tipo = ttk.Combobox(frame_add_contacto, values=["Correo", "Telefono", "WhatsApp", "Classroom", "Grupo de Facebook", "Otro"], width=12, state="readonly", font=("Segoe UI", 9))
            combo_tipo.set("Correo")
            combo_tipo.pack(side=tk.LEFT, padx=(0, 5))

            ent_nuevo_contacto = tk.Entry(frame_add_contacto, font=("Segoe UI", 9), width=15)
            ent_nuevo_contacto.pack(side=tk.LEFT, padx=(0, 5))

            def agregar_contacto():
                t = combo_tipo.get().strip()
                v = ent_nuevo_contacto.get().strip()
                if v:
                    listbox_contactos.insert(tk.END, f"{t}: {v}")
                    ent_nuevo_contacto.delete(0, tk.END)

            def eliminar_contacto():
                seleccion = listbox_contactos.curselection()
                if seleccion:
                    listbox_contactos.delete(seleccion)

            btn_add = tk.Button(frame_add_contacto, text="+", command=agregar_contacto, font=("Segoe UI", 9, "bold"), bg="#A6E3A1", fg="black", width=2)
            btn_add.pack(side=tk.LEFT)

            btn_del = tk.Button(frame_add_contacto, text="-", command=eliminar_contacto, font=("Segoe UI", 9, "bold"), bg="#F38BA8", fg="black", width=2)
            btn_del.pack(side=tk.LEFT, padx=(5, 0))

            ent_salon = create_entry("Salon", 4, valores[4])
            ent_h_ini = create_entry("Hora de Inicio", 5, valores[5])
            ent_h_fin = create_entry("Hora de Fin", 6, valores[6])

            def guardar_cambios_completo():
                n_mat = ent_materia.get().strip()
                n_dia = ent_dia.get().strip()
                n_mae = ent_maestro.get().strip()
                
                contactos_finales = listbox_contactos.get(0, tk.END)
                n_con = " | ".join(contactos_finales) if contactos_finales else "Sin contacto"
                
                n_sal = ent_salon.get().strip()
                n_hi = ent_h_ini.get().strip()
                n_hf = ent_h_fin.get().strip()
                
                cambios = []
                with SesionBD() as s:
                    c_db = s.query(ClaseHorario).get(db_id)
                    if c_db:
                        if c_db.materia != n_mat: cambios.append(f"Materia a '{n_mat}'")
                        if c_db.dia != n_dia: cambios.append(f"Dia a '{n_dia}'")
                        if c_db.salon != n_sal: cambios.append(f"Salon a '{n_sal}'")
                        if c_db.maestro != n_mae: cambios.append(f"Maestro a '{n_mae}'")
                        if c_db.contacto_maestro != n_con: cambios.append(f"Contactos actualizados")
                        if c_db.hora_inicio != n_hi or c_db.hora_fin != n_hf: cambios.append(f"Horario a '{n_hi}-{n_hf}'")
                        
                        c_db.materia = n_mat; c_db.dia = n_dia; c_db.maestro = n_mae
                        c_db.contacto_maestro = n_con; c_db.salon = n_sal; c_db.hora_inicio = n_hi; c_db.hora_fin = n_hf
                        s.commit()

                recargar_tabla()
                edit_win.destroy()
                
                if cambios:
                    lista_modificaciones = ", ".join(cambios)
                    msg = f"Se han realizado cambios en la asignatura {asignatura_original}. Modificaste lo siguiente: {lista_modificaciones}."
                    self.actualizar_ui_desde_hilo(msg, "Hermes")
                    threading.Thread(target=reproducir_audio, args=(msg,), daemon=True).start()

            ttk.Button(edit_win, text="Aceptar Cambios", command=guardar_cambios_completo).pack(pady=20)

        frame_acciones = tk.Frame(ventana_horario, bg="#CCCCCC")
        frame_acciones.pack(fill=tk.X, ipady=10)
        frame_btn_cont = tk.Frame(frame_acciones, bg="#CCCCCC"); frame_btn_cont.pack()

        tk.Button(frame_btn_cont, text="Editar Seleccion", command=abrir_edicion_completa, font=("Segoe UI", 10), bg="white", fg="black", padx=10).pack(side=tk.LEFT, padx=10)
        tk.Button(frame_btn_cont, text="Cerrar Panel", command=ventana_horario.destroy, font=("Segoe UI", 10), bg="white", fg="black", padx=10).pack(side=tk.LEFT, padx=10)

    def actualizar_ui_desde_hilo(self, texto, emisor): self.root.after(0, self.agregar_mensaje, texto, emisor)
    def actualizar_estado_desde_hilo(self, texto): self.root.after(0, self.cambiar_estado, texto)

if __name__ == "__main__":
    root = tk.Tk()
    app = HermesGUI(root)
    root.mainloop()
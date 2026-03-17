import os
import uuid
from datetime import date, time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime, ForeignKey, Date, Time
from dotenv import load_dotenv

load_dotenv()
ruta_base_datos = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///hermes_db.sqlite")

motor_base_datos = create_async_engine(ruta_base_datos, echo=False)
crear_sesion = async_sessionmaker(motor_base_datos, class_=AsyncSession, expire_on_commit=False)
Base_Datos = declarative_base()

#  Tabla de Usuarios (Limpiada, sin semestre)
class Usuario(Base_Datos):
    __tablename__ = "usuarios_registrados"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, nullable=False)
    correo = Column(String, unique=True, nullable=False)
    codigo_alumno = Column(String, unique=True, nullable=False)
    contrasena = Column(String, nullable=False)

#  Tabla del Ciclo Escolar y Fechas Límite
class CicloEscolar(Base_Datos):
    __tablename__ = "ciclos_escolares"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = Column(String(36), ForeignKey("usuarios_registrados.id"))
    carrera = Column(String, nullable=False)
    semestre = Column(String, nullable=False)
    nombre_ciclo = Column(String, nullable=False) # Ej. 2026-A
    fecha_inicio = Column(Date, nullable=False)   # Limite Inferior
    fecha_fin = Column(Date, nullable=False)      # Limite Superior

#  Tabla del Horario (Ya la teníamos)
class ClaseDelHorario(Base_Datos):
    __tablename__ = "mis_clases_guardadas"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = Column(String(36), ForeignKey("usuarios_registrados.id"))
    materia = Column(String, nullable=False)
    dia = Column(String) 
    profesor = Column(String)
    contacto_profesor = Column(String, default="[]") 
    hora_inicio = Column(DateTime(timezone=True))
    hora_fin = Column(DateTime(timezone=True))
    salon = Column(String)

#  Tabla de la Agenda (Vinculada a la Materia)
class EventoAgenda(Base_Datos):
    __tablename__ = "eventos_agenda"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = Column(String(36), ForeignKey("usuarios_registrados.id"))
    clase_id = Column(String(36), ForeignKey("mis_clases_guardadas.id")) # VINCULO CON EL HORARIO
    titulo = Column(String, nullable=False)
    descripcion = Column(String)
    tipo_evento = Column(String, nullable=False) # Evento, Recordatorio, Anotacion
    fecha_evento = Column(Date, nullable=False)
    hora_evento = Column(Time, nullable=False)
    estado = Column(String, default="Pendiente") # Pendiente, Completado

async def preparar_base_de_datos():
    async with motor_base_datos.begin() as conexion:
        await conexion.run_sync(Base_Datos.metadata.create_all)
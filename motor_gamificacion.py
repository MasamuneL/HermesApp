# backend/app/services/motor_gamificacion.py
"""
MOTOR DE GAMIFICACIÓN "HERMES"

Filosofía de Diseño (World of Warcraft):
- Común (Blanco): 5-10 pts. Logros de introducción, inevitables al jugar.
- Raro (Azul): 20-50 pts. Requieren farmeo intencional o descubrir mecánicas.
- Épico (Morado): 100-250 pts. Requieren grindeo extremo. Otorgan Títulos.
- Legendario (Naranja/Dorado): 500-5000 pts. Proezas, Meta-logros y Fin del Juego.

Escalabilidad
1. Catálogo exhaustivo de descripciones para que el Frontend sepa qué mostrar.
2. Lógica de Semestres (carreras de 6 a 8 semestres).
3. Lore y comentarios culturales en los Eventos de Mundo.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

# Importaciones de los CRUD originales
from app.crud.crud_users import get_user_by_id
from app.crud.redis_operations import update_user_ranking

# =====================================================================
# DICCIONARIO MAESTRO DE LOGROS (REGISTRY)
# Contiene el Título, la Descripción de cómo obtenerlo y la Rareza.
# =====================================================================
REGISTRO_LOGROS = {
    # --- RAMA 1: MAESTRO DEL TIEMPO (25 LOGROS) ---
    "TIEMPO_1": {"nombre": "La Primera Piedra", "desc": "Crea tu primer evento manual en el calendario.", "rareza": "Común"},
    "TIEMPO_2": {"nombre": "Tomando el Control", "desc": "Crea 10 eventos en total.", "rareza": "Común"},
    "TIEMPO_3": {"nombre": "Agenda Activa", "desc": "Crea 50 eventos en total.", "rareza": "Común"},
    "TIEMPO_4": {"nombre": "Semana Ocupada", "desc": "Agenda 5 eventos en una sola semana.", "rareza": "Común"},
    "TIEMPO_5": {"nombre": "Previsor", "desc": "Crea un evento con más de 30 días de anticipación.", "rareza": "Común"},
    "TIEMPO_6": {"nombre": "El Cronometrador", "desc": "Crea 100 eventos en total.", "rareza": "Raro"},
    "TIEMPO_7": {"nombre": "Detallista", "desc": "Crea 20 eventos que incluyan ubicación y descripción.", "rareza": "Raro"},
    "TIEMPO_8": {"nombre": "Maratón de Estudio", "desc": "Agenda un evento tipo 'Estudio' de más de 4 horas continuas.", "rareza": "Raro"},
    "TIEMPO_9": {"nombre": "El Corrector", "desc": "Edita la información de eventos existentes 15 veces.", "rareza": "Raro"},
    "TIEMPO_10": {"nombre": "Limpieza de Primavera", "desc": "Elimina 10 eventos cancelados o que ya no sirven.", "rareza": "Raro"},
    "TIEMPO_11": {"nombre": "Buscador de la Verdad", "desc": "Usa el comando de búsqueda de calendario 20 veces.", "rareza": "Raro"},
    "TIEMPO_12": {"nombre": "Fin de Semana Productivo", "desc": "Agenda 5 eventos en sábados o domingos.", "rareza": "Raro"},
    "TIEMPO_13": {"nombre": "Agenda de Hierro", "desc": "Crea 250 eventos en total.", "rareza": "Épico"},
    "TIEMPO_14": {"nombre": "Micromanager", "desc": "Ten 10 eventos agendados en un solo día.", "rareza": "Épico"},
    "TIEMPO_15": {"nombre": "Anticipación Extrema", "desc": "Agenda un evento con más de 6 meses de anticipación.", "rareza": "Épico"},
    "TIEMPO_16": {"nombre": "Categorizador NATO", "desc": "Usa 5 tipos diferentes de eventos.", "rareza": "Épico"},
    "TIEMPO_17": {"nombre": "El Insomne", "desc": "Crea un evento entre las 2:00 AM y las 5:00 AM.", "rareza": "Épico"},
    "TIEMPO_18": {"nombre": "Planificador Mensual", "desc": "Ten al menos un evento agendado cada día durante 30 días seguidos.", "rareza": "Épico"},
    "TIEMPO_19": {"nombre": "Cien Búsquedas", "desc": "Usa la búsqueda de eventos 100 veces.", "rareza": "Épico"},
    "TIEMPO_20": {"nombre": "El Erudito del Calendario", "desc": "Crea 500 eventos en total.", "rareza": "Épico"},
    "TIEMPO_21": {"nombre": "Señor de los Exámenes", "desc": "Agenda 50 eventos con la etiqueta 'Examen'.", "rareza": "Legendario"},
    "TIEMPO_22": {"nombre": "El Arquitecto", "desc": "Crea 1,000 eventos en total. Otorga el título [El Arquitecto].", "rareza": "Legendario"},
    "TIEMPO_23": {"nombre": "Vida Equilibrada", "desc": "Ten 100 eventos académicos y 50 eventos personales.", "rareza": "Legendario"},
    "TIEMPO_24": {"nombre": "Maestro Manipulador", "desc": "Edita 100 eventos.", "rareza": "Legendario"},
    "TIEMPO_25": {"nombre": "META: Guardián del Tiempo", "desc": "Completa los 24 logros anteriores. Otorga el título [Guardián del Tiempo].", "rareza": "Legendario"},

    # --- RAMA 2: SIMBIOSIS CON IA (25 LOGROS) ---
    "IA_1": {"nombre": "Hola Mundo", "desc": "Envía tu primer mensaje a Hermes.", "rareza": "Común"},
    "IA_2": {"nombre": "Curioso", "desc": "Realiza 10 consultas al chatbot.", "rareza": "Común"},
    "IA_3": {"nombre": "Parlanchín", "desc": "Envía 50 mensajes.", "rareza": "Común"},
    "IA_4": {"nombre": "Noctámbulo", "desc": "Habla con Hermes después de la medianoche.", "rareza": "Común"},
    "IA_5": {"nombre": "Madrugador", "desc": "Habla con Hermes antes de las 6:00 AM.", "rareza": "Común"},
    "IA_6": {"nombre": "Conversador Asiduo", "desc": "Alcanza los 100 mensajes enviados.", "rareza": "Raro"},
    "IA_7": {"nombre": "El Interrogador", "desc": "Haz 50 preguntas que terminen en signo de interrogación.", "rareza": "Raro"},
    "IA_8": {"nombre": "Lector Rápido", "desc": "Recibe 50 respuestas de Hermes.", "rareza": "Raro"},
    "IA_9": {"nombre": "Sobrecarga de Servidor", "desc": "Envía 20 mensajes en un solo día.", "rareza": "Raro"},
    "IA_10": {"nombre": "Buscador de Consejos", "desc": "Pídele a Hermes que te sugiera horarios 10 veces.", "rareza": "Raro"},
    "IA_11": {"nombre": "Delegador", "desc": "Pídele a Hermes que te lea tu agenda del día 15 veces.", "rareza": "Raro"},
    "IA_12": {"nombre": "Petición de Auxilio", "desc": "Menciona palabras como 'estrés', 'ayuda' o 'difícil'.", "rareza": "Raro"},
    "IA_13": {"nombre": "Compañero de Estudio", "desc": "Alcanza los 500 mensajes enviados.", "rareza": "Épico"},
    "IA_14": {"nombre": "El Consejero Escucha", "desc": "Activa la sugerencia de horarios 50 veces.", "rareza": "Épico"},
    "IA_15": {"nombre": "Largas Charlas", "desc": "Mantén una conversación continua de más de 20 mensajes.", "rareza": "Épico"},
    "IA_16": {"nombre": "Usuario de Confianza", "desc": "Habla con Hermes en 50 días distintos.", "rareza": "Épico"},
    "IA_17": {"nombre": "Telepatía Digital", "desc": "Alcanza 1,000 mensajes enviados.", "rareza": "Épico"},
    "IA_18": {"nombre": "Dependencia Sana", "desc": "Envía al menos un mensaje diario durante 14 días.", "rareza": "Épico"},
    "IA_19": {"nombre": "Mente Maestra", "desc": "Pídele a Hermes acciones complejas de calendario en un solo mensaje.", "rareza": "Épico"},
    "IA_20": {"nombre": "El Filósofo", "desc": "Recibe una respuesta de Hermes de más de 200 palabras 50 veces.", "rareza": "Épico"},
    "IA_21": {"nombre": "Voz del Sistema", "desc": "Alcanza 2,500 mensajes enviados.", "rareza": "Legendario"},
    "IA_22": {"nombre": "Oráculo de Hermes", "desc": "Alcanza 5,000 mensajes. Otorga título [El Oráculo].", "rareza": "Legendario"},
    "IA_23": {"nombre": "Analista Táctico", "desc": "Usa todas las herramientas y nodos de IA 100 veces.", "rareza": "Legendario"},
    "IA_24": {"nombre": "Amigo de la Máquina", "desc": "Habla con Hermes durante 100 días distintos.", "rareza": "Legendario"},
    "IA_25": {"nombre": "META: El Turing Humano", "desc": "Completa los 24 logros de IA. Otorga título [El Ciborg].", "rareza": "Legendario"},

    # --- EVENTOS DE MUNDO (EFEMÉRIDES) ---
    "EVT_AÑO_NUEVO": {"nombre": "El Renovado", "desc": "Inicia sesión el 1 de Enero. Otorga título [El Renovado].", "rareza": "Legendario"},
    "EVT_REYES_MAGOS": {"nombre": "El Sabio", "desc": "Inicia sesión el 6 de Enero (Día de Reyes).", "rareza": "Legendario"},
    "EVT_ROMANCE": {"nombre": "El Romántico", "desc": "Inicia sesión el 14 de Febrero.", "rareza": "Legendario"},
    "EVT_INDEPENDENCIA": {"nombre": "El Insurgente", "desc": "Inicia sesión durante las fiestas patrias (15-16 Septiembre).", "rareza": "Legendario"},
    "EVT_FUNDACION_UDG": {"nombre": "León de Guadalajara", "desc": "Conéctate el 12 de Octubre, aniversario de la UdeG.", "rareza": "Legendario"},
    "EVT_ROMERIA_ZAPOPAN": {"nombre": "El Peregrino", "desc": "Conéctate el 12 de Octubre durante la Romería de Zapopan.", "rareza": "Legendario"},
    "EVT_DIA_MUERTOS": {"nombre": "El Trascendido", "desc": "Conéctate el 1 o 2 de Noviembre.", "rareza": "Legendario"},
    "EVT_POSADAS": {"nombre": "El Fiestero", "desc": "Conéctate en época de Posadas (16-24 Diciembre).", "rareza": "Legendario"},
    "META_VIAJE_ANUAL": {"nombre": "Viajero del Año", "desc": "Consigue los logros de todos los eventos festivos del año.", "rareza": "Legendario"},

    # --- LOGROS RIDÍCULOS (BROMA) ---
    "JOKE_OVER_9000": {"nombre": "¡Es más de 9000!", "desc": "Supera los 9000 puntos en el ranking global.", "rareza": "Épico"},
    "JOKE_AMOR_NO_TAREA": {"nombre": "Haz el amor, no la tarea", "desc": "Manda un mensaje en la madrugada de un fin de semana.", "rareza": "Épico"},
    "JOKE_EVOLUCION": {"nombre": "Evolución contra mi teclado", "desc": "Manda un mensaje frustrado de más de 1000 caracteres.", "rareza": "Épico"},
    "JOKE_BUROCRACIA": {"nombre": "Bailando con la burocracia", "desc": "Edita eventos innecesariamente 50 veces.", "rareza": "Épico"},
    "JOKE_MUY_DIFICIL": {"nombre": "¿No que era muy difícil?", "desc": "Sobrevive agendando 10 eventos de tipo 'Examen'.", "rareza": "Épico"},

    # --- CÚSPIDE (SEMESTRES Y GRADUACIÓN) ---
    "CUSPIDE_SEMESTRE_1": {"nombre": "Novato Prometedor", "desc": "Supera tu 1er Semestre con actividad en Hermes.", "rareza": "Morado"},
    "CUSPIDE_SEMESTRE_MEDIO": {"nombre": "A la Mitad del Camino", "desc": "Supera el 4to Semestre (Ecuador de la carrera).", "rareza": "Morado"},
    "CUSPIDE_SOBREVIVIENTE": {"nombre": "Sobreviviente del Semestre", "desc": "Mantén actividad constante hasta el final del ciclo (Jun/Dic).", "rareza": "Legendario"},
    "PROEZA_GAMEMASTER": {"nombre": "Maestro del Tiempo y el Espacio", "desc": "Alcanza tu semestre final (6 a 8) y obtén tu titulación.", "rareza": "Legendario"},
}

# Diccionario de asignación rápida de títulos al desbloquear el ID correspondiente.
MAPA_TITULOS = {
    "TIEMPO_22": "El Arquitecto", "TIEMPO_25": "Guardián del Tiempo",
    "IA_22": "El Oráculo", "IA_25": "El Ciborg",
    "RED_22": "Rey de la Colina", "RED_25": "El Rector",
    "VOLUNTAD_22": "El Inmortal", "VOLUNTAD_25": "El Inquebrantable",
    "CUSPIDE_SOBREVIVIENTE": "El Sobreviviente", "PROEZA_GAMEMASTER": "GAMEMASTER",
    "EVT_AÑO_NUEVO": "El Renovado", "EVT_REYES_MAGOS": "El Sabio",
    "EVT_ROMANCE": "El Romántico", "EVT_INDEPENDENCIA": "El Insurgente",
    "EVT_FUNDACION_UDG": "León de Guadalajara", "EVT_ROMERIA_ZAPOPAN": "El Peregrino",
    "EVT_DIA_MUERTOS": "El Trascendido", "EVT_POSADAS": "El Posadero",
    "META_VIAJE_ANUAL": "Viajero del Año",
    "JOKE_OVER_9000": "Super Saiyajin", "JOKE_AMOR_NO_TAREA": "El Fiestero Empedernido",
    "JOKE_EVOLUCION": "El Cavernícola Digital"
}


class MotorGamificacion:
    def __init__(self, bd: AsyncSession):
        self.bd = bd

    async def procesar_accion(self, id_usuario: str, tipo_accion: str, metadatos: Optional[Dict[str, Any]] = None):
        """
        Punto de entrada principal del motor.
        Se evalúa toda la mochila de logros del usuario (JSONB) en busca de nuevas medallas.
        """
        usuario = await get_user_by_id(self.bd, id_usuario)
        if not usuario or not usuario.ranking:
            return

        ranking = usuario.ranking
        stats = ranking.achievements if ranking.achievements else {}
        metadatos = metadatos or {} 
        
        # Inicializar mochila de jugador
        if "contadores" not in stats: stats["contadores"] = {}
        if "ids_desbloqueados" not in stats: stats["ids_desbloqueados"] = []
        if "titulos_ganados" not in stats: stats["titulos_ganados"] = []

        stats["contadores"][tipo_accion] = stats["contadores"].get(tipo_accion, 0) + 1
        puntos_obtenidos = 0

        # --- EVALUACIÓN DE LAS 4 RAMAS BASE ---
        puntos_obtenidos += await self._evaluar_rama_tiempo(stats, tipo_accion, metadatos)
        puntos_obtenidos += await self._evaluar_rama_ia(stats, tipo_accion, metadatos)
        puntos_obtenidos += await self._evaluar_rama_identidad(stats, tipo_accion, usuario, ranking.points)
        puntos_obtenidos += await self._evaluar_rama_voluntad(stats, ranking.daily_streak, tipo_accion)

        # --- EVENTOS, RIDÍCULOS Y CÚSPIDE ---
        puntos_obtenidos += await self._evaluar_eventos_mundo(stats)
        puntos_obtenidos += await self._evaluar_logros_cuspide(stats, tipo_accion, usuario)
        puntos_obtenidos += await self._evaluar_logros_ridiculos(stats, tipo_accion, metadatos, ranking.points)

        # --- ACTUALIZAR BASE DE DATOS Y REDIS ---
        ranking.achievements = stats
        ranking.points += puntos_obtenidos
        ranking.level = (ranking.points // 1000) + 1  # Escalado RPG: 1 nivel cada 1000 XP
        
        await update_user_ranking(str(id_usuario), ranking.points)
        await self.bd.commit()
        
        return stats

    async def _otorgar(self, stats: Dict, id_logro: str, puntos: int) -> int:
        """ 
        Agrega el logro a la mochila del usuario y verifica si otorga un Título.
        """
        if id_logro not in stats["ids_desbloqueados"]:
            stats["ids_desbloqueados"].append(id_logro)
            # Si el logro conlleva un título, se le asigna a su lista de títulos
            if id_logro in MAPA_TITULOS:
                titulo = MAPA_TITULOS[id_logro]
                if titulo not in stats["titulos_ganados"]:
                    stats["titulos_ganados"].append(titulo)
            return puntos
        return 0

    # =====================================================================
    # RAMA 1: MAESTRO DEL TIEMPO (CALENDARIO)
    # =====================================================================
    async def _evaluar_rama_tiempo(self, stats: Dict, accion: str, meta: Dict) -> int:
        pts = 0
        c_evt = stats["contadores"].get("crear_evento", 0)

        if accion == "crear_evento":
            # Escala de progresión de Eventos Creados
            if c_evt >= 1: pts += await self._otorgar(stats, "TIEMPO_1", 10) 
            if c_evt >= 10: pts += await self._otorgar(stats, "TIEMPO_2", 10) 
            if c_evt >= 50: pts += await self._otorgar(stats, "TIEMPO_3", 10) 
            if c_evt >= 100: pts += await self._otorgar(stats, "TIEMPO_6", 50)
            if c_evt >= 250: pts += await self._otorgar(stats, "TIEMPO_13", 200)
            if c_evt >= 500: pts += await self._otorgar(stats, "TIEMPO_20", 200)
            if c_evt >= 1000: pts += await self._otorgar(stats, "TIEMPO_22", 500) # Otorga Título

            # Metadatos del evento
            if meta.get("dias_anticipacion", 0) >= 30: pts += await self._otorgar(stats, "TIEMPO_5", 10)
            if meta.get("dias_anticipacion", 0) >= 180: pts += await self._otorgar(stats, "TIEMPO_15", 200)
            
            # Evaluación del meta-logro
            logros_rama = [f"TIEMPO_{i}" for i in range(1, 25)]
            if all(l in stats["ids_desbloqueados"] for l in logros_rama):
                pts += await self._otorgar(stats, "TIEMPO_25", 500)

        # Lógica de ediciones y búsquedas (reducida por brevedad, sigue el mismo patrón)
        if accion == "editar_evento" and stats["contadores"].get("editar_evento", 0) >= 15:
            pts += await self._otorgar(stats, "TIEMPO_9", 50)
            
        return pts

    # =====================================================================
    # RAMA 2: SIMBIOSIS CON IA (CHATBOT)
    # =====================================================================
    async def _evaluar_rama_ia(self, stats: Dict, accion: str, meta: Dict) -> int:
        pts = 0
        c_msg = stats["contadores"].get("enviar_mensaje", 0)

        if accion == "enviar_mensaje":
            if c_msg >= 1: pts += await self._otorgar(stats, "IA_1", 10)
            if c_msg >= 10: pts += await self._otorgar(stats, "IA_2", 10)
            if c_msg >= 50: pts += await self._otorgar(stats, "IA_3", 10)
            if c_msg >= 100: pts += await self._otorgar(stats, "IA_6", 50)
            if c_msg >= 500: pts += await self._otorgar(stats, "IA_13", 200)
            if c_msg >= 1000: pts += await self._otorgar(stats, "IA_17", 200)
            if c_msg >= 2500: pts += await self._otorgar(stats, "IA_21", 500)
            if c_msg >= 5000: pts += await self._otorgar(stats, "IA_22", 500) # Otorga Título

            if all(f"IA_{i}" in stats["ids_desbloqueados"] for i in range(1, 25)):
                pts += await self._otorgar(stats, "IA_25", 500)
        return pts

    # =====================================================================
    # RAMA 3 Y 4: IDENTIDAD, RED Y VOLUNTAD (Simplificadas en esta vista)
    # =====================================================================
    async def _evaluar_rama_identidad(self, stats: Dict, accion: str, usuario, puntos_globales: int) -> int:
        pts = 0
        if usuario.full_name: pts += await self._otorgar(stats, "RED_1", 10)
        if usuario.u_degree: pts += await self._otorgar(stats, "RED_4", 10)
        # Ranking check
        if puntos_globales >= 50000: pts += await self._otorgar(stats, "RED_22", 500)
        return pts

    async def _evaluar_rama_voluntad(self, stats: Dict, racha: int, accion: str) -> int:
        pts = 0
        if racha >= 7: pts += await self._otorgar(stats, "VOLUNTAD_3", 10)
        if racha >= 30: pts += await self._otorgar(stats, "VOLUNTAD_7", 50)
        if racha >= 100: pts += await self._otorgar(stats, "VOLUNTAD_14", 200)
        if racha >= 365: pts += await self._otorgar(stats, "VOLUNTAD_22", 500) # Título Inmortal
        return pts

    # =====================================================================
    # EVENTOS DE MUNDO (EFEMÉRIDES CULTURALES CON LORE)
    # Referencia WoW: "World Events" que ocurren solo en fechas precisas.
    # =====================================================================
    async def _evaluar_eventos_mundo(self, stats: Dict) -> int:
        pts = 0
        hoy = datetime.now()
        dia, mes = hoy.day, hoy.month

        # 1 de Enero - Año Nuevo: Celebración global del inicio de un nuevo ciclo solar.
        # Referencia WoW: Lunar Festival.
        if mes == 1 and dia == 1: pts += await self._otorgar(stats, "EVT_AÑO_NUEVO", 0)
        
        # 6 de Enero - Día de Reyes: Tradición donde se parte la rosca en México.
        elif mes == 1 and dia == 6: pts += await self._otorgar(stats, "EVT_REYES_MAGOS", 0)
        
        # 15-16 de Septiembre - Independencia: El Grito de Dolores.
        # Referencia WoW: Midsummer Fire Festival.
        elif mes == 9 and (dia == 15 or dia == 16): pts += await self._otorgar(stats, "EVT_INDEPENDENCIA", 0)
        
        # 12 de Octubre - Fundación UdeG y Romería:
        # La Universidad de Guadalajara fue fundada un 12 de octubre. Adicionalmente,
        # en Zapopan (sede de tu proyecto), millones peregrinan en la Romería de la Virgen.
        # Referencia WoW: Pilgrim's Bounty / Aniversario de Facción.
        elif mes == 10 and dia == 12:
            pts += await self._otorgar(stats, "EVT_FUNDACION_UDG", 0)
            pts += await self._otorgar(stats, "EVT_ROMERIA_ZAPOPAN", 0)
            
        # 1 y 2 de Noviembre - Día de Muertos: Honrar a los que trascendieron.
        # Referencia WoW: Hallow's End.
        elif mes == 11 and (dia == 1 or dia == 2): pts += await self._otorgar(stats, "EVT_DIA_MUERTOS", 0)
        
        # 16 al 24 de Diciembre - Las Posadas: Fiestas tradicionales decembrinas.
        # Referencia WoW: Feast of Winter Veil.
        elif mes == 12 and (16 <= dia <= 24): pts += await self._otorgar(stats, "EVT_POSADAS", 0)

        # Meta-Logro Anual: Otorgado si se completan las fiestas mayores.
        requeridos = ["EVT_INDEPENDENCIA", "EVT_FUNDACION_UDG", "EVT_DIA_MUERTOS", "EVT_POSADAS"]
        if all(e in stats["ids_desbloqueados"] for e in requeridos):
            pts += await self._otorgar(stats, "META_VIAJE_ANUAL", 0)

        return pts

    # =====================================================================
    # LÓGICA DE SEMESTRES Y GRADUACIÓN (EL ENDGAME)
    # Evaluamos en qué etapa de la carrera universitaria se encuentra.
    # =====================================================================
    async def _evaluar_logros_cuspide(self, stats: Dict, accion: str, usuario) -> int:
        pts = 0
        mes_actual = datetime.now().month
        
        # Las carreras universitarias en este dominio duran entre 6 y 8 semestres.
        semestre = usuario.semester if usuario.semester else 1

        # Hito 1: Terminar el primer semestre
        if semestre == 2 and "CUSPIDE_SEMESTRE_1" not in stats["ids_desbloqueados"]:
            pts += await self._otorgar(stats, "CUSPIDE_SEMESTRE_1", 200)

        # Hito 2: Llegar a la mitad de la carrera (Semestre 4)
        if semestre == 4 and "CUSPIDE_SEMESTRE_MEDIO" not in stats["ids_desbloqueados"]:
            pts += await self._otorgar(stats, "CUSPIDE_SEMESTRE_MEDIO", 500)

        # Sobreviviente del Semestre (Junio o Diciembre - Fin de ciclos escolares)
        if mes_actual in [6, 12] and stats["contadores"].get("crear_evento", 0) > 50:
            pts += await self._otorgar(stats, "CUSPIDE_SOBREVIVIENTE", 1000)

        # GAMEMASTER (Graduación - Fin de Expansión)
        # Se requiere llegar al menos al semestre 6 y declarar explícitamente graduación.
        if accion == "graduacion" and semestre >= 6:
            pts += await self._otorgar(stats, "PROEZA_GAMEMASTER", 5000)
            stats["estado_legendario"] = True # Dispara animaciones especiales en UI
                
        return pts

    # =====================================================================
    # LOGROS RIDÍCULOS / JOKES (EASTER EGGS DE WOW Y CULTURA POP)
    # =====================================================================
    async def _evaluar_logros_ridiculos(self, stats: Dict, accion: str, meta: Dict, puntos_totales: int) -> int:
        pts = 0
        
        # 1. "It's Over 9000!" - Referencia a Dragon Ball Z popularizada en WoW.
        if puntos_totales >= 9000:
            pts += await self._otorgar(stats, "JOKE_OVER_9000", 0)

        if accion == "enviar_mensaje":
            ahora = datetime.now()
            # 2. "Make Love, Not Warcraft" (South Park ep.) - Mensaje 3AM un sábado.
            if ahora.hour in [2, 3, 4] and ahora.weekday() in [4, 5]:
                pts += await self._otorgar(stats, "JOKE_AMOR_NO_TAREA", 50)

            # 3. "Millions of Years of Evolution..." - Berrinche de más de 1000 caracteres a la IA.
            if meta.get("longitud_mensaje", 0) > 1000:
                pts += await self._otorgar(stats, "JOKE_EVOLUCION", 20)

        elif accion == "editar_evento":
            # 4. "Dances With Oozes" - Recompensa por perder el tiempo editando 50 veces inútilmente.
            if stats["contadores"].get("editar_evento", 0) == 50:
                pts += await self._otorgar(stats, "JOKE_BUROCRACIA", 15)

        elif accion == "crear_evento":
            # 5. "I Thought He Was Supposed to Be Hard?" - Agendar 10 exámenes y sobrevivir.
            if meta.get("tipo_evento") == "examen":
                stats["contadores"]["joke_examenes"] = stats["contadores"].get("joke_examenes", 0) + 1
                if stats["contadores"]["joke_examenes"] == 10:
                    pts += await self._otorgar(stats, "JOKE_MUY_DIFICIL", 100)

        return pts

# =====================================================================
# GUÍA DE INTEGRACIÓN Y USO DE LA CLASE
# =====================================================================
"""

COMO INTEGRARLO AL CÓDIGO EXISTENTE:

Dado que ahora contamos con un diccionario llamado 'REGISTRO_LOGROS', el frontend
solo necesita recibir el array de 'ids_desbloqueados'. Para ello:

1. CREAR EL ARCHIVO:
   CIntegrar este codigo en `backend/app/services/motor_gamificacion.py`

2. INTEGRAR EN ROUTER DE CHAT (`app/routers/chat.py`):
   Añadir `BackgroundTasks` en la definición de la ruta.
   Extraer metadatos:
     metadatos = {"longitud_mensaje": len(body.message)}
   Llamar de forma asíncrona ANTES de retornar:
     motor = MotorGamificacion(db)
     background_tasks.add_task(motor.procesar_accion, current_user["uid"], "enviar_mensaje", metadatos)

3. INTEGRAR EN ROUTER DE CALENDARIO (`app/routers/calendar.py`):
   Hacer lo mismo en el endpoint de creación de eventos.
   Extraer metadatos:
     metadatos = {"tipo_evento": body.event_type}
   Llamar a la tarea:
     background_tasks.add_task(motor.procesar_accion, current_user["uid"], "crear_evento", metadatos)

4. ENDPOINT PARA MOSTRAR LOS LOGROS:
   En `app/routers/logros.py`, al llamar al endpoint `/api/logros/me`, 
   el servidor debe leer los `ids_desbloqueados` del `JSONB` del ranking y 
   mapearlos con la variable `REGISTRO_LOGROS` que declaramos arriba. De esta manera, 
   el frontend recibe el "nombre", "descripción" y "rareza" de forma dinámica, 
   mostrando la mochila completa del jugador.
"""
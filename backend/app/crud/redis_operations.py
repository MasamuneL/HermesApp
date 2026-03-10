# app/crud/redis_operations.py
"""
Operaciones de Redis
Cache, ranking y sesiones
"""
import redis.asyncio as redis
import hashlib
import json
from typing import Optional, List, Dict
import os
from dotenv import load_dotenv

load_dotenv()

# URL de conexión (Dennis te la dará)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Cliente Redis
redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

# ==========================================
# CACHE DE CHAT
# ==========================================

async def cache_chat_response(message: str, response: str, user_id: str, ttl: int = 3600):
    """
    Guarda respuesta del chatbot en cache
    
    Parámetros:
        message: Mensaje del usuario
        response: Respuesta de Gemini
        user_id: ID del usuario
        ttl: Tiempo en segundos (por defecto 1 hora = 3600)
    
    Ejemplo:
        await cache_chat_response(
            message="¿Qué tareas tengo?",
            response="Tienes 3 tareas pendientes...",
            user_id="abc-123"
        )
    """
    # Crear hash único del mensaje + user_id
    cache_key = hashlib.md5(f"{user_id}:{message}".encode()).hexdigest()
    key = f"chat:response:{cache_key}"
    
    # Guardar con TTL (se borra automáticamente después de 1 hora)
    await redis_client.setex(key, ttl, response)

async def get_cached_chat_response(message: str, user_id: str) -> Optional[str]:
    """
    Obtiene respuesta cacheada del chatbot
    
    Retorna:
        Respuesta si existe en cache, None si no existe
    
    Ejemplo:
        cached = await get_cached_chat_response("¿Qué tareas tengo?", "abc-123")
        if cached:
            print("¡Ya tengo la respuesta en cache!")
            return cached
        else:
            print("No hay cache, llamar a Gemini")
    """
    cache_key = hashlib.md5(f"{user_id}:{message}".encode()).hexdigest()
    key = f"chat:response:{cache_key}"
    
    return await redis_client.get(key)

async def clear_user_chat_cache(user_id: str):
    """
    Limpia todo el cache de chat de un usuario
    
    Ejemplo:
        await clear_user_chat_cache("abc-123")
    """
    # Buscar todas las keys que empiecen con chat:response y contengan user_id
    # Nota: En producción esto es costoso, mejor poner TTL corto
    pattern = f"chat:response:*"
    keys = []
    async for key in redis_client.scan_iter(match=pattern):
        keys.append(key)
    
    if keys:
        await redis_client.delete(*keys)

# ==========================================
# RANKING GLOBAL (Sorted Set)
# ==========================================

async def update_user_ranking(user_id: str, points: int):
    """
    Actualiza los puntos de un usuario en el ranking global
    
    Parámetros:
        user_id: ID del usuario
        points: Puntos totales (NO incrementales, es el total)
    
    Ejemplo:
        # Usuario tiene 150 puntos totales
        await update_user_ranking("abc-123", 150)
    """
    await redis_client.zadd("ranking:global", {user_id: points})

async def get_top_ranking(limit: int = 10) -> List[Dict]:
    """
    Obtiene el top N del ranking
    
    Retorna:
        Lista de diccionarios con user_id y puntos
    
    Ejemplo:
        top10 = await get_top_ranking(10)
        for i, user in enumerate(top10, 1):
            print(f"{i}. User {user['user_id']}: {user['points']} puntos")
    """
    # ZREVRANGE obtiene del mayor al menor
    results = await redis_client.zrevrange("ranking:global", 0, limit - 1, withscores=True)
    
    # Convertir a lista de diccionarios
    ranking = []
    for user_id, points in results:
        ranking.append({
            "user_id": user_id,
            "points": int(points)
        })
    
    return ranking

async def get_user_rank(user_id: str) -> Optional[int]:
    """
    Obtiene la posición de un usuario en el ranking
    
    Retorna:
        Posición (1 = primero, 2 = segundo, etc.) o None si no está
    
    Ejemplo:
        rank = await get_user_rank("abc-123")
        if rank:
            print(f"Estás en la posición #{rank}")
    """
    rank = await redis_client.zrevrank("ranking:global", user_id)
    if rank is not None:
        return rank + 1  # Redis usa índice 0, nosotros queremos 1
    return None

async def get_user_points_from_redis(user_id: str) -> Optional[int]:
    """
    Obtiene los puntos de un usuario desde Redis
    
    Ejemplo:
        points = await get_user_points_from_redis("abc-123")
    """
    score = await redis_client.zscore("ranking:global", user_id)
    return int(score) if score else None

async def remove_from_ranking(user_id: str):
    """
    Elimina un usuario del ranking
    
    Ejemplo:
        await remove_from_ranking("abc-123")
    """
    await redis_client.zrem("ranking:global", user_id)

# ==========================================
# SESIONES DE USUARIO
# ==========================================

async def create_session(user_id: str, session_data: dict, ttl: int = 86400):
    """
    Crea una sesión de usuario
    
    Parámetros:
        user_id: ID del usuario
        session_data: Diccionario con datos de la sesión
        ttl: Tiempo en segundos (por defecto 24 horas = 86400)
    
    Ejemplo:
        await create_session(
            "abc-123",
            {
                "email": "juan@gmail.com",
                "name": "Juan Pérez",
                "login_at": "2026-03-04T10:30:00"
            }
        )
    """
    key = f"session:{user_id}"
    
    # Convertir valores a strings
    string_data = {k: str(v) for k, v in session_data.items()}
    
    # Guardar como hash
    await redis_client.hset(key, mapping=string_data)
    
    # Establecer TTL
    await redis_client.expire(key, ttl)

async def get_session(user_id: str) -> Optional[Dict]:
    """
    Obtiene la sesión de un usuario
    
    Retorna:
        Diccionario con datos de sesión o None si no existe
    
    Ejemplo:
        session = await get_session("abc-123")
        if session:
            print(f"Usuario: {session['name']}")
        else:
            print("Sesión expirada o no existe")
    """
    key = f"session:{user_id}"
    session = await redis_client.hgetall(key)
    
    return dict(session) if session else None

async def update_session(user_id: str, field: str, value: str):
    """
    Actualiza un campo específico de la sesión
    
    Ejemplo:
        await update_session("abc-123", "last_activity", "2026-03-04T11:00:00")
    """
    key = f"session:{user_id}"
    await redis_client.hset(key, field, value)

async def delete_session(user_id: str):
    """
    Elimina la sesión (logout)
    
    Ejemplo:
        await delete_session("abc-123")
    """
    key = f"session:{user_id}"
    await redis_client.delete(key)

async def session_exists(user_id: str) -> bool:
    """
    Verifica si existe una sesión activa
    
    Ejemplo:
        if await session_exists("abc-123"):
            print("Usuario logueado")
    """
    key = f"session:{user_id}"
    return await redis_client.exists(key) > 0

# ==========================================
# UTILIDADES
# ==========================================

async def ping_redis() -> bool:
    """
    Verifica si Redis está funcionando
    
    Ejemplo:
        if await ping_redis():
            print("Redis OK")
    """
    try:
        await redis_client.ping()
        return True
    except:
        return False

async def close_redis():
    """
    Cierra la conexión a Redis
    (Llamar al cerrar la aplicación)
    """
    await redis_client.close()
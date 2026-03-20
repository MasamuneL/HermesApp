-- ═══════════════════════════════════════════════════════════════════════════════
-- ⚔  HERMES — Sistema de Gestión Académica con Chatbot IA
-- Schema de Base de Datos PostgreSQL 16
--
-- Este archivo crea todas las tablas necesarias desde cero
-- Ejecutar: psql -U hermes_user -d hermes_db -f schema.sql
--
-- ═══════════════════════════════════════════════════════════════════════════════
--
-- DECISIONES DE DISEÑO:
--
-- [¿Por qué PostgreSQL y no MongoDB?]
--   ✅ Datos RELACIONALES: usuario → eventos → amigos → ranking
--   ✅ Integridad referencial: CASCADE deletes automáticos
--   ✅ Búsquedas complejas con JOINs (ranking con amigos)
--   ✅ Transacciones ACID: crear usuario + ranking debe ser atómico
--   ❌ NO guardamos imágenes: solo texto extraído por Gemini OCR
--      Las imágenes se procesan y se descartan inmediatamente
--
-- [¿Está normalizado (3NF)?]
--   ✅ SÍ — Sin redundancia de datos
--   ✅ Cada columna depende directamente de su clave primaria
--   ✅ Sin dependencias transitivas
--   ✅ Foreign keys garantizan consistencia
--
-- [¿Dónde usamos Redis?]
--   Redis NO está en este archivo (es in-memory, separado):
--   - Cache de respuestas del chatbot (TTL 1 hora)
--   - Ranking global en Sorted Set (5ms vs 500ms en PostgreSQL)
--   - Sesiones de usuario (TTL 24 horas)
--
-- ═══════════════════════════════════════════════════════════════════════════════

-- Extensión para generar UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ─────────────────────────────────────────────────────────────────────────────
-- Tabla: users
-- Descripción: Usuarios del sistema (estudiantes universitarios)
-- Autenticación: Google OAuth 2.0 o email/password
-- 
-- [NORMALIZACIÓN]
--   Esta tabla está en 3NF:
--   - Cada campo depende directamente del ID del usuario
--   - No hay dependencias transitivas
--   - google_id puede ser NULL (si usa email/password)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    password_hash VARCHAR(255),
    google_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Índices para búsquedas rápidas en login
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);

COMMENT ON TABLE users IS 'Usuarios del sistema - Estudiantes universitarios';
COMMENT ON COLUMN users.google_id IS 'ID de Google para OAuth 2.0 - NULL si usa email/password';
COMMENT ON COLUMN users.is_active IS 'Usuario activo (true) o desactivado (false)';


-- ─────────────────────────────────────────────────────────────────────────────
-- Tabla: calendar_events
-- Descripción: Eventos del calendario (clases, exámenes, tareas, estudio)
-- Origen: Extraídos de fotos con Gemini Vision OCR o creados manualmente
-- 
-- [NORMALIZACIÓN]
--   Relación 1:N con users (un usuario tiene muchos eventos)
--   ON DELETE CASCADE: Si se borra un usuario, se borran sus eventos
--   
-- [¿Por qué NO guardamos las imágenes aquí?]
--   Las imágenes NO se almacenan. El flujo es:
--   1. Usuario sube foto del horario
--   2. Gemini extrae eventos (OCR)
--   3. Se guardan SOLO los eventos como registros
--   4. La imagen se descarta
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type VARCHAR(50),      -- 'clase', 'examen', 'tarea', 'estudio'
    classroom VARCHAR(100),
    professor VARCHAR(255),
    recurrence VARCHAR(50),       -- 'daily', 'weekly', 'monthly', NULL
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Índices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_events_user_id ON calendar_events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_start_time ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_events_type ON calendar_events(event_type);

COMMENT ON TABLE calendar_events IS 'Eventos del calendario extraídos de fotos (OCR) o creados manualmente';
COMMENT ON COLUMN calendar_events.event_type IS 'Tipo: clase, examen, tarea, estudio';
COMMENT ON COLUMN calendar_events.recurrence IS 'Frecuencia de repetición: daily, weekly, monthly, o NULL';


-- ─────────────────────────────────────────────────────────────────────────────
-- Tabla: rankings
-- Descripción: Sistema de gamificación (puntos, niveles, logros, rachas)
-- Relación: 1:1 con users (cada usuario tiene exactamente un ranking)
-- 
-- [NORMALIZACIÓN]
--   id = user_id (relación 1:1 estricta)
--   achievements usa JSONB para flexibilidad
--   Ejemplo: {"first_scan": true, "week_streak": true, "top_10": false}
--
-- [DENORMALIZACIÓN INTENCIONAL]
--   'points' se duplica en Redis para velocidad
--   PostgreSQL = fuente de verdad
--   Redis = cache para ranking global (actualizado cada 5 minutos)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rankings (
    id UUID PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    points INTEGER DEFAULT 0 NOT NULL CHECK (points >= 0),
    level INTEGER DEFAULT 1 CHECK (level >= 1),
    achievements JSONB DEFAULT '{}',
    daily_streak INTEGER DEFAULT 0 CHECK (daily_streak >= 0),
    last_activity TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Índice crítico para ordenar el ranking global
CREATE INDEX IF NOT EXISTS idx_rankings_points ON rankings(points DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_user_id ON rankings(user_id);

COMMENT ON TABLE rankings IS 'Sistema de gamificación - Puntos, niveles y logros';
COMMENT ON COLUMN rankings.achievements IS 'Logros desbloqueados en formato JSON: {"first_scan": true, "week_streak": false}';
COMMENT ON COLUMN rankings.daily_streak IS 'Días consecutivos usando la app';


-- ─────────────────────────────────────────────────────────────────────────────
-- Tabla: friendships
-- Descripción: Relaciones de amistad para competir en el ranking
-- Relación: N:M entre users (un usuario puede tener muchos amigos)
-- 
-- [NORMALIZACIÓN]
--   Tabla de unión (junction table) para relación N:M
--   CHECK: un usuario no puede ser amigo de sí mismo
--   UNIQUE: no pueden haber amistades duplicadas
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS friendships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    friend_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'accepted', 'rejected'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, friend_id),
    CHECK (user_id != friend_id)
);

-- Índices para búsquedas bidireccionales
CREATE INDEX IF NOT EXISTS idx_friendships_user_id ON friendships(user_id);
CREATE INDEX IF NOT EXISTS idx_friendships_friend_id ON friendships(friend_id);
CREATE INDEX IF NOT EXISTS idx_friendships_status ON friendships(status);

COMMENT ON TABLE friendships IS 'Relaciones de amistad para competir en ranking';
COMMENT ON COLUMN friendships.status IS 'Estado: pending (pendiente), accepted (aceptada), rejected (rechazada)';


-- ─────────────────────────────────────────────────────────────────────────────
-- Tabla: chat_history
-- Descripción: Historial de conversaciones con Gemini
-- Propósito: Contexto a largo plazo para el chatbot
-- 
-- [DENORMALIZACIÓN INTENCIONAL]
--   Esta tabla duplica datos que podrían estar en Redis
--   ¿Por qué? Redis es volátil (cache), necesitamos persistencia
--   PostgreSQL = historial permanente
--   Redis = cache temporal (TTL 1 hora)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    intent VARCHAR(50),           -- 'query_info', 'create_task', 'search_notes', 'small_talk'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para consultas de historial
CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_history(created_at DESC);

COMMENT ON TABLE chat_history IS 'Historial permanente de conversaciones con Gemini';
COMMENT ON COLUMN chat_history.intent IS 'Intención detectada por Gemini: query_info, create_task, search_notes, small_talk';


-- ═══════════════════════════════════════════════════════════════════════════════
-- VISTAS ÚTILES
-- ═══════════════════════════════════════════════════════════════════════════════

-- Vista: Ranking global con nombres de usuarios
CREATE OR REPLACE VIEW v_ranking_leaderboard AS
SELECT 
    u.id,
    u.full_name,
    u.email,
    r.points,
    r.level,
    r.daily_streak,
    ROW_NUMBER() OVER (ORDER BY r.points DESC) as rank
FROM users u
JOIN rankings r ON u.id = r.user_id
WHERE u.is_active = TRUE
ORDER BY r.points DESC;

COMMENT ON VIEW v_ranking_leaderboard IS 'Ranking global ordenado por puntos con nombres de usuarios';


-- Vista: Eventos próximos (siguientes 7 días)
CREATE OR REPLACE VIEW v_upcoming_events AS
SELECT 
    e.*,
    u.full_name as user_name
FROM calendar_events e
JOIN users u ON e.user_id = u.id
WHERE e.start_time > NOW()
  AND e.start_time < NOW() + INTERVAL '7 days'
ORDER BY e.start_time ASC;

COMMENT ON VIEW v_upcoming_events IS 'Eventos de los próximos 7 días con nombre de usuario';


-- Vista: Ranking de amigos (para un usuario específico)
-- Nota: Esta vista requiere pasar user_id como parámetro en la query
CREATE OR REPLACE VIEW v_friends_ranking AS
SELECT 
    u.id,
    u.full_name,
    r.points,
    r.level,
    r.daily_streak,
    f.user_id as requester_id
FROM friendships f
JOIN users u ON f.friend_id = u.id
JOIN rankings r ON u.id = r.user_id
WHERE f.status = 'accepted'
ORDER BY r.points DESC;

COMMENT ON VIEW v_friends_ranking IS 'Ranking de amigos aceptados - filtrar por requester_id en query';


-- ═══════════════════════════════════════════════════════════════════════════════
-- DATOS DE EJEMPLO (OPCIONAL - comentar en producción)
-- ═══════════════════════════════════════════════════════════════════════════════

-- Usuario de prueba
INSERT INTO users (email, full_name, is_active) 
VALUES ('test@hermes.com', 'Usuario Prueba', TRUE)
ON CONFLICT (email) DO NOTHING;

-- Ranking del usuario de prueba
INSERT INTO rankings (id, user_id, points, level)
SELECT id, id, 0, 1 FROM users WHERE email = 'test@hermes.com'
ON CONFLICT (user_id) DO NOTHING;

-- Evento de prueba
INSERT INTO calendar_events (user_id, title, start_time, end_time, event_type)
SELECT 
    id,
    'Cálculo Diferencial',
    NOW() + INTERVAL '1 day',
    NOW() + INTERVAL '1 day' + INTERVAL '2 hours',
    'clase'
FROM users WHERE email = 'test@hermes.com'
ON CONFLICT DO NOTHING;


-- ═══════════════════════════════════════════════════════════════════════════════
-- QUERIES DE EJEMPLO PARA VERIFICACIÓN Y TESTING
-- Copiar y ejecutar estas queries para verificar que todo funciona
-- ═══════════════════════════════════════════════════════════════════════════════

/*
-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Verificar que todas las tablas se crearon correctamente
-- ─────────────────────────────────────────────────────────────────────────────
\dt

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Contar registros en cada tabla
-- ─────────────────────────────────────────────────────────────────────────────
SELECT 'users' as tabla, COUNT(*) as registros FROM users
UNION ALL
SELECT 'calendar_events', COUNT(*) FROM calendar_events
UNION ALL
SELECT 'rankings', COUNT(*) FROM rankings
UNION ALL
SELECT 'friendships', COUNT(*) FROM friendships
UNION ALL
SELECT 'chat_history', COUNT(*) FROM chat_history
ORDER BY tabla;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Ver el ranking global (top 10)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT * FROM v_ranking_leaderboard LIMIT 10;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Ver eventos próximos
-- ─────────────────────────────────────────────────────────────────────────────
SELECT * FROM v_upcoming_events LIMIT 10;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Buscar eventos de un usuario específico (reemplazar email)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT e.title, e.start_time, e.event_type, e.classroom
FROM calendar_events e
JOIN users u ON e.user_id = u.id
WHERE u.email = 'test@hermes.com'
ORDER BY e.start_time;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. Verificar integridad referencial (CASCADE DELETE)
-- Este query muestra cuántos eventos tiene cada usuario
-- Si borras un usuario, sus eventos se borran automáticamente
-- ─────────────────────────────────────────────────────────────────────────────
SELECT 
    u.email,
    COUNT(e.id) as num_eventos,
    r.points as puntos
FROM users u
LEFT JOIN calendar_events e ON e.user_id = u.id
LEFT JOIN rankings r ON r.user_id = u.id
GROUP BY u.email, r.points
ORDER BY r.points DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. Solicitudes de amistad pendientes para un usuario
-- ─────────────────────────────────────────────────────────────────────────────
SELECT 
    u.full_name as solicitante,
    f.created_at as fecha_solicitud
FROM friendships f
JOIN users u ON f.user_id = u.id
WHERE f.friend_id = (SELECT id FROM users WHERE email = 'test@hermes.com')
  AND f.status = 'pending'
ORDER BY f.created_at DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. Historial de chat de un usuario (últimos 10 mensajes)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT 
    message,
    response,
    intent,
    created_at
FROM chat_history
WHERE user_id = (SELECT id FROM users WHERE email = 'test@hermes.com')
ORDER BY created_at DESC
LIMIT 10;

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. Estadísticas de eventos por tipo
-- ─────────────────────────────────────────────────────────────────────────────
SELECT 
    event_type,
    COUNT(*) as cantidad,
    AVG(EXTRACT(EPOCH FROM (end_time - start_time))/3600) as duracion_promedio_horas
FROM calendar_events
GROUP BY event_type
ORDER BY cantidad DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 10. Verificar logros en formato JSON
-- ─────────────────────────────────────────────────────────────────────────────
SELECT 
    u.full_name,
    r.points,
    r.achievements
FROM rankings r
JOIN users u ON r.user_id = u.id
WHERE r.achievements != '{}'::jsonb
ORDER BY r.points DESC;
*/

-- ═══════════════════════════════════════════════════════════════════════════════
-- FIN DEL SCHEMA
-- ═══════════════════════════════════════════════════════════════════════════════
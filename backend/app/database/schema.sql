-- ═══════════════════════════════════════════════════════════════════════════════
-- HERMES - Base de Datos Schema ACTUALIZADO
-- Sistema de gestión académica con chatbot IA
-- Actualizado con campos requeridos por los schemas del backend
-- ═══════════════════════════════════════════════════════════════════════════════

-- Extensión para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════
-- Tabla: users (ACTUALIZADA)
-- Agregados: u_degree, semester
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    password_hash VARCHAR(255),
    google_id VARCHAR(255) UNIQUE,
    u_degree VARCHAR(255),           -- NUEVO: Carrera del estudiante
    semester INTEGER,                 -- NUEVO: Semestre actual
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);

COMMENT ON TABLE users IS 'Usuarios del sistema - Estudiantes universitarios';
COMMENT ON COLUMN users.u_degree IS 'Carrera o grado académico del estudiante';
COMMENT ON COLUMN users.semester IS 'Semestre actual del estudiante';

-- ═══════════════════════════════════════════════════════════════════
-- Tabla: calendar_events (ACTUALIZADA)
-- Agregado: location
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type VARCHAR(50),
    classroom VARCHAR(100),
    professor VARCHAR(255),
    location VARCHAR(255),            -- NUEVO: Ubicación del evento
    recurrence VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_events_user_id ON calendar_events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_start_time ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_events_type ON calendar_events(event_type);

COMMENT ON TABLE calendar_events IS 'Eventos del calendario extraídos de fotos (OCR) o creados manualmente';
COMMENT ON COLUMN calendar_events.location IS 'Ubicación del evento (puede ser igual a classroom)';

-- ═══════════════════════════════════════════════════════════════════
-- Tabla: rankings
-- ═══════════════════════════════════════════════════════════════════
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

CREATE INDEX IF NOT EXISTS idx_rankings_points ON rankings(points DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_user_id ON rankings(user_id);

COMMENT ON TABLE rankings IS 'Sistema de gamificación - Puntos, niveles y logros';
COMMENT ON COLUMN rankings.achievements IS 'Logros desbloqueados en formato JSON';

-- ═══════════════════════════════════════════════════════════════════
-- Tabla: achievements (NUEVA)
-- Logros individuales que pueden desbloquearse
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS achievements (
    ach_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usr_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ach_title VARCHAR(255) NOT NULL,
    ach_desc TEXT,
    ach_points INTEGER NOT NULL,
    ach_rank INTEGER,
    fecha_objetivo INTEGER,
    status_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_achievements_user ON achievements(usr_id);
CREATE INDEX IF NOT EXISTS idx_achievements_completed ON achievements(status_completed);

COMMENT ON TABLE achievements IS 'Logros individuales de usuarios';
COMMENT ON COLUMN achievements.ach_title IS 'Título del logro';
COMMENT ON COLUMN achievements.ach_desc IS 'Descripción del logro';
COMMENT ON COLUMN achievements.ach_points IS 'Puntos que otorga el logro';
COMMENT ON COLUMN achievements.fecha_objetivo IS 'Fecha objetivo para completar (timestamp)';

-- ═══════════════════════════════════════════════════════════════════
-- Tabla: friendships
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS friendships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    friend_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, friend_id),
    CHECK (user_id != friend_id)
);

CREATE INDEX IF NOT EXISTS idx_friendships_user_id ON friendships(user_id);
CREATE INDEX IF NOT EXISTS idx_friendships_friend_id ON friendships(friend_id);
CREATE INDEX IF NOT EXISTS idx_friendships_status ON friendships(status);

COMMENT ON TABLE friendships IS 'Relaciones de amistad para competir en ranking';

-- ═══════════════════════════════════════════════════════════════════
-- Tabla: chat_history
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    intent VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_history(created_at DESC);

COMMENT ON TABLE chat_history IS 'Historial de conversaciones con Gemini';

-- ═══════════════════════════════════════════════════════════════════
-- VISTAS
-- ═══════════════════════════════════════════════════════════════════

CREATE OR REPLACE VIEW v_ranking_leaderboard AS
SELECT 
    u.id,
    u.full_name,
    u.email,
    u.u_degree,
    u.semester,
    r.points,
    r.level,
    r.daily_streak,
    ROW_NUMBER() OVER (ORDER BY r.points DESC) as rank
FROM users u
JOIN rankings r ON u.id = r.user_id
WHERE u.is_active = TRUE
ORDER BY r.points DESC;

CREATE OR REPLACE VIEW v_upcoming_events AS
SELECT 
    e.*,
    u.full_name as user_name
FROM calendar_events e
JOIN users u ON e.user_id = u.id
WHERE e.start_time > NOW()
  AND e.start_time < NOW() + INTERVAL '7 days'
ORDER BY e.start_time ASC;

-- ═══════════════════════════════════════════════════════════════════
-- DATOS DE EJEMPLO
-- ═══════════════════════════════════════════════════════════════════

-- Usuario de prueba
INSERT INTO users (email, full_name, u_degree, semester, is_active) 
VALUES ('test@hermes.com', 'Usuario Prueba', 'Ingeniería en Sistemas', 5, TRUE)
ON CONFLICT (email) DO NOTHING;

-- Ranking del usuario de prueba
INSERT INTO rankings (id, user_id, points, level)
SELECT id, id, 0, 1 FROM users WHERE email = 'test@hermes.com'
ON CONFLICT (user_id) DO NOTHING;

-- Evento de prueba
INSERT INTO calendar_events (user_id, title, start_time, end_time, event_type, classroom, location)
SELECT 
    id,
    'Cálculo Diferencial',
    NOW() + INTERVAL '1 day',
    NOW() + INTERVAL '1 day' + INTERVAL '2 hours',
    'clase',
    'Aula 301',
    'Edificio A, Piso 3'
FROM users WHERE email = 'test@hermes.com'
ON CONFLICT DO NOTHING;

-- Logro de ejemplo
INSERT INTO achievements (usr_id, ach_title, ach_desc, ach_points, ach_rank, status_completed)
SELECT 
    id,
    'Primera Tarea',
    'Completa tu primera tarea en Hermes',
    10,
    1,
    FALSE
FROM users WHERE email = 'test@hermes.com';

-- ═══════════════════════════════════════════════════════════════════
-- FIN
-- ═══════════════════════════════════════════════════════════════════
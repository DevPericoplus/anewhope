-- ============================================================================
-- Migración: Crear tabla flujos y relación con proyectos
-- Base de datos: myllm_projects_db
-- Fecha: 2026-01-31
-- Descripción: Crea tabla catálogo de flujos de trabajo y añade relación
--              con la tabla proyectos para indicar el paso actual.
-- ============================================================================

USE myllm_projects_db;

-- ============================================================================
-- 0. Asegurar que la base de datos y conexión soportan utf8mb4 (emojis)
-- ============================================================================
ALTER DATABASE myllm_projects_db CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ============================================================================
-- 1. Crear tabla catálogo de flujos
-- ============================================================================
CREATE TABLE IF NOT EXISTS flujos (
    id_flujo INT NOT NULL AUTO_INCREMENT,
    clave VARCHAR(50) NOT NULL UNIQUE COMMENT 'Identificador interno del paso (snake_case)',
    nombre VARCHAR(100) NOT NULL COMMENT 'Nombre visible del paso',
    descripcion VARCHAR(255) DEFAULT NULL COMMENT 'Descripción del paso',
    emoji VARCHAR(10) DEFAULT NULL COMMENT 'Emoji representativo del paso',
    color VARCHAR(20) DEFAULT NULL COMMENT 'Color hexadecimal para UI',
    orden INT NOT NULL COMMENT 'Orden secuencial del paso en el flujo',
    es_bloque_inicio TINYINT(1) DEFAULT 0 COMMENT 'Indica si pertenece al bloque inicial',
    es_bloque_iteracion TINYINT(1) DEFAULT 0 COMMENT 'Indica si pertenece al bloque de iteración',
    activo TINYINT(1) DEFAULT 1 COMMENT 'Indica si el paso está activo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_flujo),
    INDEX idx_flujos_orden (orden),
    INDEX idx_flujos_clave (clave)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Catálogo de pasos del flujo de trabajo para generación de modelos LLM';

-- ============================================================================
-- 2. Insertar los 12 pasos del flujo de trabajo
-- ============================================================================
INSERT INTO flujos (clave, nombre, descripcion, emoji, color, orden, es_bloque_inicio, es_bloque_iteracion) VALUES
-- Bloque inicial (propuesta y revisión)
('propuesta_cliente', 'Propuesta Cliente', 'El cliente envía la propuesta inicial del proyecto', '📝', '#3b82f6', 1, 1, 0),
('revision_interna', 'Revisión Interna', 'Revisión interna de la propuesta del cliente', '🔍', '#8b5cf6', 2, 1, 0),
('propuesta_mejoras', 'Propuesta de Mejoras', 'Propuesta de mejoras basada en la revisión', '⚙️', '#f59e0b', 3, 1, 0),

-- Punto de aceptación
('aceptacion_cliente', 'Aceptación Cliente', 'El cliente acepta la propuesta y mejoras', '✅', '#22c55e', 4, 0, 0),
('aceptacion_interna', 'Aceptación Interna', 'Aprobación interna para continuar', '✅', '#22c55e', 5, 0, 0),

-- Entrenamiento inicial
('entrenamiento_inicial', 'Entrenamiento Inicial', 'Primera fase de entrenamiento del modelo', '🎓', '#10b981', 6, 0, 0),

-- Bloque de iteración (evaluación y optimización)
('evaluacion_entrenamiento', 'Evaluación Entrenamiento', 'Evaluación de los resultados del entrenamiento', '📊', '#6366f1', 7, 0, 1),
('reentrenamiento', 'Reentrenamiento', 'Reentrenamiento del modelo con ajustes', '🔄', '#ec4899', 8, 0, 1),
('optimizacion', 'Optimización', 'Optimización de parámetros y rendimiento', '⚡', '#06b6d4', 9, 0, 1),

-- Aprobación y generación
('aprobacion_calidad', 'Aprobación Calidad', 'Control de calidad del modelo entrenado', '✅', '#22c55e', 10, 0, 0),
('generacion_llm', 'Generación del Modelo LLM', 'Generación final del modelo LLM', '🤖', '#10b981', 11, 0, 0),

-- Finalización
('notificacion_descarga', 'Notificación de Descarga', 'Notificación al cliente de que el modelo está disponible', '🔔', '#10b981', 12, 0, 0)
ON DUPLICATE KEY UPDATE
    nombre = VALUES(nombre),
    descripcion = VALUES(descripcion),
    emoji = VALUES(emoji),
    color = VALUES(color),
    orden = VALUES(orden),
    es_bloque_inicio = VALUES(es_bloque_inicio),
    es_bloque_iteracion = VALUES(es_bloque_iteracion);

-- ============================================================================
-- 3. Añadir campo id_flujo a la tabla proyectos
-- ============================================================================
-- Primero eliminar FK existente si la hay (para poder modificar la columna)
SET @fk_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE TABLE_SCHEMA = 'myllm_projects_db' 
    AND TABLE_NAME = 'proyectos' 
    AND CONSTRAINT_NAME = 'fk_proyectos_flujo'
);

SET @sql = IF(@fk_exists > 0,
    'ALTER TABLE proyectos DROP FOREIGN KEY fk_proyectos_flujo',
    'SELECT "No existe FK previa"'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Verificar si la columna ya existe
SET @column_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'myllm_projects_db' 
    AND TABLE_NAME = 'proyectos' 
    AND COLUMN_NAME = 'id_flujo'
);

-- Si existe, asegurar que el tipo sea correcto (INT NOT NULL para FK)
SET @sql = IF(@column_exists > 0,
    'ALTER TABLE proyectos MODIFY COLUMN id_flujo INT NULL DEFAULT 1 COMMENT "Paso actual del proyecto en el flujo de trabajo"',
    'ALTER TABLE proyectos ADD COLUMN id_flujo INT NULL DEFAULT 1 COMMENT "Paso actual del proyecto en el flujo de trabajo"'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT 'Columna id_flujo configurada correctamente' AS resultado;

-- ============================================================================
-- 4. Crear índice para el campo id_flujo si no existe
-- ============================================================================
SET @index_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE TABLE_SCHEMA = 'myllm_projects_db' 
    AND TABLE_NAME = 'proyectos' 
    AND INDEX_NAME = 'idx_proyectos_flujo'
);

SET @sql = IF(@index_exists = 0,
    'CREATE INDEX idx_proyectos_flujo ON proyectos(id_flujo)',
    'SELECT "El índice idx_proyectos_flujo ya existe"'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================================================
-- 5. Crear Foreign Key
-- ============================================================================
ALTER TABLE proyectos 
ADD CONSTRAINT fk_proyectos_flujo 
FOREIGN KEY (id_flujo) REFERENCES flujos(id_flujo) 
ON DELETE SET NULL 
ON UPDATE CASCADE;

-- ============================================================================
-- 6. Vista útil: proyectos con su paso actual del flujo
-- ============================================================================
CREATE OR REPLACE VIEW view_proyectos_flujo AS
SELECT 
    p.id AS proyecto_id,
    p.nombre AS proyecto_nombre,
    p.id_organizacion,
    p.id_flujo,
    f.clave AS flujo_clave,
    f.nombre AS flujo_nombre,
    f.descripcion AS flujo_descripcion,
    f.emoji AS flujo_emoji,
    f.color AS flujo_color,
    f.orden AS flujo_orden,
    f.es_bloque_inicio,
    f.es_bloque_iteracion
FROM proyectos p
LEFT JOIN flujos f ON p.id_flujo = f.id_flujo;

-- ============================================================================
-- Verificación final
-- ============================================================================
SELECT 'Tabla flujos creada con éxito' AS resultado;
SELECT COUNT(*) AS total_flujos FROM flujos;
SELECT 'Campo id_flujo añadido a proyectos' AS resultado;
DESCRIBE proyectos;

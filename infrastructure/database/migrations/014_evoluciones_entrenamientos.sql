-- ============================================================================
-- Migración: 014_evoluciones_entrenamientos.sql
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-12
-- Descripción: Crea la tabla `evoluciones_entrenamientos` para registrar
--              el progreso detallado de cada subfase durante el entrenamiento.
--              Permite auditoría, métricas de performance y consulta en tiempo real.
-- ============================================================================

USE myllm_projects_db;

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ============================================================================
-- 1. evoluciones_entrenamientos — Progreso detallado por subfase
-- ============================================================================
CREATE TABLE IF NOT EXISTS evoluciones_entrenamientos (
    id                      INT AUTO_INCREMENT PRIMARY KEY,

    -- Referencia al entrenamiento
    id_entrenamiento        INT             NOT NULL        COMMENT 'FK al entrenamiento en curso',

    -- Identificación de fase y subfase
    phase_key               VARCHAR(10)     NOT NULL        COMMENT 'Clave de fase: "1", "2", "3", "4", "5"',
    subfase_key             VARCHAR(10)     NOT NULL        COMMENT 'Clave de subfase: "2.1", "2.2", "3.1", etc',
    subfase_name            VARCHAR(100)    NOT NULL        COMMENT 'Nombre descriptivo de la subfase',

    -- Estado y tiempos
    status                  VARCHAR(20)     NOT NULL        COMMENT 'Estado: pending, in_progress, completed, error',
    fecha_inicio            TIMESTAMP       NULL            COMMENT 'Inicio de la subfase',
    fecha_fin               TIMESTAMP       NULL            COMMENT 'Fin de la subfase',
    duracion_segundos       INT             NULL            COMMENT 'Duración en segundos',

    -- Error (si aplica)
    error_mensaje           TEXT            NULL            COMMENT 'Mensaje de error si status=error',

    -- Control temporal
    created_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign keys
    CONSTRAINT fk_evol_entrenamiento
        FOREIGN KEY (id_entrenamiento) REFERENCES entrenamientos(id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    -- Índices
    INDEX idx_evol_entrenamiento    (id_entrenamiento),
    INDEX idx_evol_status           (status),
    INDEX idx_evol_fase             (phase_key, subfase_key),
    INDEX idx_evol_created          (created_at),

    -- Garantizar una sola entrada por subfase por entrenamiento
    UNIQUE KEY unique_entrenamiento_subfase (id_entrenamiento, subfase_key)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Evolución detallada de subfases de entrenamientos para auditoría y métricas';

-- ============================================================================
-- PERMISOS
-- ============================================================================

-- myllm_writer: operaciones CRUD completas
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.evoluciones_entrenamientos TO 'myllm_writer'@'localhost';

-- myllm_reader: solo lectura
GRANT SELECT ON myllm_projects_db.evoluciones_entrenamientos TO 'myllm_reader'@'localhost';

FLUSH PRIVILEGES;

-- ============================================================================
-- VISTA ÚTIL: evoluciones con datos del entrenamiento
-- ============================================================================
CREATE OR REPLACE VIEW view_evoluciones_entrenamientos AS
SELECT
    e.id,
    e.id_entrenamiento,
    ent.id_organizacion,
    o.organization_name,
    ent.id_proyecto,
    p.nombre            AS proyecto_nombre,
    ent.id_version,
    ent.numero_secuencia,
    e.phase_key,
    e.subfase_key,
    e.subfase_name,
    e.status,
    e.fecha_inicio,
    e.fecha_fin,
    e.duracion_segundos,
    e.error_mensaje,
    e.created_at,
    e.updated_at
FROM evoluciones_entrenamientos e
INNER JOIN entrenamientos ent
    ON e.id_entrenamiento = ent.id
LEFT JOIN myllm_core_db.organizations o
    ON ent.id_organizacion = o.organization_id
LEFT JOIN proyectos p
    ON ent.id_proyecto = p.id
ORDER BY e.id_entrenamiento DESC, e.phase_key, e.subfase_key;

-- Permiso de lectura sobre la vista
GRANT SELECT ON myllm_projects_db.view_evoluciones_entrenamientos TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.view_evoluciones_entrenamientos TO 'myllm_writer'@'localhost';

FLUSH PRIVILEGES;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
SELECT '✅ Migración 014 completada: Tabla evoluciones_entrenamientos creada' AS resultado;
SELECT COUNT(*) AS total_evoluciones FROM evoluciones_entrenamientos;

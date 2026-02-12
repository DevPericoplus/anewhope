-- ============================================================================
-- Migración: 012_entrenamientos.sql
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-11
-- Descripción: Crea la tabla `entrenamientos` para registrar cada proceso
--              de entrenamiento (inicial o reentrenamiento) de modelos LLM.
--              Cada registro enlaza con `jobs_entrenamientos` para conservar
--              los parámetros específicos usados en esa iteración.
-- ============================================================================

USE myllm_projects_db;

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ============================================================================
-- 1. entrenamientos — Registro de procesos de entrenamiento
-- ============================================================================
CREATE TABLE IF NOT EXISTS entrenamientos (
    id                      INT AUTO_INCREMENT PRIMARY KEY,

    -- Referencia a la versión entrenada
    id_organizacion         INT             NOT NULL        COMMENT 'ID de la organización (ref myllm_core_db.organizations)',
    id_proyecto             INT             NOT NULL        COMMENT 'ID del proyecto (ref proyectos.id)',
    id_version              INT             NOT NULL        COMMENT 'ID de la versión entrenada',
    pat_version             VARCHAR(500)    NOT NULL        COMMENT 'Ruta completa del contenido de la versión',

    -- Tipo de entrenamiento
    entrenamiento_inicial   TINYINT(1)      DEFAULT 1       COMMENT '1=primer entrenamiento de la versión',
    reentrenamiento         TINYINT(1)      DEFAULT 0       COMMENT '1=reentrenamiento para optimizar modelo',
    numero_secuencia        INT             DEFAULT 1       COMMENT 'Secuencia autoincremental por versión (1,2,3...)',

    -- Seguimiento del proceso
    fase_actual             VARCHAR(50)     DEFAULT 'recepcion'
                                                            COMMENT 'Fase en curso: recepcion, validacion, preparacion, configuracion, entrenamiento',
    estado                  VARCHAR(50)     DEFAULT 'pendiente'
                                                            COMMENT 'Estado global: pendiente, en_progreso, completado, error',

    -- ChromaDB
    collection_name         VARCHAR(300)    DEFAULT NULL    COMMENT 'Nombre de la colección ChromaDB (ORG_PRJ_v_ENT_SEQ)',

    -- Modelo generado
    modelo_path             VARCHAR(500)    DEFAULT NULL    COMMENT 'Ruta del fichero del modelo generado',

    -- Error
    error_mensaje           TEXT            DEFAULT NULL    COMMENT 'Mensaje de error si el proceso falló',

    -- Parámetros usados (FK a jobs_entrenamientos)
    id_job_entrenamientos   INT             DEFAULT NULL    COMMENT 'FK a jobs_entrenamientos con los parámetros de esta iteración',

    -- Control temporal
    fecha_inicio            DATETIME        DEFAULT NULL    COMMENT 'Inicio del proceso de entrenamiento',
    fecha_fin               DATETIME        DEFAULT NULL    COMMENT 'Fin del proceso de entrenamiento',
    created_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign keys
    CONSTRAINT fk_ent_job_params
        FOREIGN KEY (id_job_entrenamientos) REFERENCES jobs_entrenamientos(id)
        ON DELETE SET NULL ON UPDATE CASCADE,

    -- Índices
    INDEX idx_ent_org_prj_ver   (id_organizacion, id_proyecto, id_version),
    INDEX idx_ent_estado        (estado),
    INDEX idx_ent_fase          (fase_actual),
    INDEX idx_ent_secuencia     (id_version, numero_secuencia),
    INDEX idx_ent_collection    (collection_name)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Registro de procesos de entrenamiento (inicial y reentrenamientos)';

-- ============================================================================
-- PERMISOS
-- ============================================================================

-- myllm_writer: operaciones CRUD completas
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.entrenamientos TO 'myllm_writer'@'localhost';

-- myllm_reader: solo lectura
GRANT SELECT ON myllm_projects_db.entrenamientos TO 'myllm_reader'@'localhost';

FLUSH PRIVILEGES;

-- ============================================================================
-- VISTA ÚTIL: entrenamientos con nombres resueltos
-- ============================================================================
CREATE OR REPLACE VIEW view_entrenamientos_detalle AS
SELECT
    e.id,
    e.id_organizacion,
    o.organization_name,
    e.id_proyecto,
    p.nombre            AS proyecto_nombre,
    e.id_version,
    e.pat_version,
    e.entrenamiento_inicial,
    e.reentrenamiento,
    e.numero_secuencia,
    e.fase_actual,
    e.estado,
    e.collection_name,
    e.modelo_path,
    e.error_mensaje,
    e.id_job_entrenamientos,
    je.nombre           AS params_nombre,
    je.learning_rate,
    je.batch_size,
    je.epochs,
    je.embedding_dimension,
    je.chunk_size,
    je.chunk_overlap,
    e.fecha_inicio,
    e.fecha_fin,
    e.created_at,
    e.updated_at
FROM entrenamientos e
LEFT JOIN myllm_core_db.organizations o
    ON e.id_organizacion = o.organization_id
LEFT JOIN proyectos p
    ON e.id_proyecto = p.id
LEFT JOIN jobs_entrenamientos je
    ON e.id_job_entrenamientos = je.id
ORDER BY e.created_at DESC;

-- Permiso de lectura sobre la vista
GRANT SELECT ON myllm_projects_db.view_entrenamientos_detalle TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.view_entrenamientos_detalle TO 'myllm_writer'@'localhost';

FLUSH PRIVILEGES;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
SELECT '✅ Migración 012 completada: Tabla entrenamientos creada' AS resultado;
SELECT COUNT(*) AS total_entrenamientos FROM entrenamientos;

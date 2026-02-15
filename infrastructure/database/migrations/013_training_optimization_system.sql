-- ============================================================================
-- Migración: 013_training_optimization_system.sql
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-15
-- Descripción: Sistema de análisis y optimización automática de entrenamientos.
--              - Tabla de métricas de entrenamiento (resultados observados)
--              - Tabla de sugerencias de parámetros para reentrenamiento
--              - Sistema de mejora continua iterativa
-- ============================================================================

USE myllm_projects_db;

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ============================================================================
-- 1. entrenamientos_metricas — Métricas y resultados de cada entrenamiento
-- ============================================================================
CREATE TABLE IF NOT EXISTS entrenamientos_metricas (
    id                      INT AUTO_INCREMENT PRIMARY KEY,

    -- Relación con entrenamiento
    id_entrenamiento        INT             NOT NULL        COMMENT 'FK a entrenamientos',

    -- Métricas de pérdida (loss)
    loss_inicial            DECIMAL(12,6)   DEFAULT NULL    COMMENT 'Loss en época 1',
    loss_final              DECIMAL(12,6)   DEFAULT NULL    COMMENT 'Loss en última época',
    loss_promedio           DECIMAL(12,6)   DEFAULT NULL    COMMENT 'Loss promedio en todas las épocas',
    loss_minimo             DECIMAL(12,6)   DEFAULT NULL    COMMENT 'Mejor loss alcanzado',
    epoca_mejor_loss        INT             DEFAULT NULL    COMMENT 'Época donde se alcanzó el mejor loss',

    -- Métricas de validación
    accuracy_validacion     DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Accuracy en set de validación (0-1)',
    f1_score                DECIMAL(7,4)    DEFAULT NULL    COMMENT 'F1-Score',
    precision_score         DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Precisión',
    recall_score            DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Recall',

    -- Métricas de RAG
    retrieval_precision     DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Precisión de recuperación RAG (0-1)',
    retrieval_recall        DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Recall de recuperación RAG (0-1)',
    avg_similarity_score    DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Score de similitud promedio',

    -- Métricas de generación
    perplexity              DECIMAL(12,4)   DEFAULT NULL    COMMENT 'Perplejidad del modelo',
    bleu_score              DECIMAL(7,4)    DEFAULT NULL    COMMENT 'BLEU score (calidad de generación)',
    rouge_l_score           DECIMAL(7,4)    DEFAULT NULL    COMMENT 'ROUGE-L score',

    -- Métricas de eficiencia
    tiempo_entrenamiento_seg INT            DEFAULT NULL    COMMENT 'Tiempo total de entrenamiento en segundos',
    tokens_procesados       BIGINT          DEFAULT NULL    COMMENT 'Total de tokens procesados',
    tokens_por_segundo      DECIMAL(12,2)   DEFAULT NULL    COMMENT 'Throughput de procesamiento',
    memoria_pico_mb         INT             DEFAULT NULL    COMMENT 'Uso máximo de memoria en MB',

    -- Indicadores de problemas
    overfitting_detectado   TINYINT(1)      DEFAULT 0       COMMENT '1=Se detectó overfitting (loss val > loss train)',
    underfitting_detectado  TINYINT(1)      DEFAULT 0       COMMENT '1=Se detectó underfitting (loss alto estable)',
    convergencia_lenta      TINYINT(1)      DEFAULT 0       COMMENT '1=Convergencia muy lenta',
    gradientes_explosivos   TINYINT(1)      DEFAULT 0       COMMENT '1=Se detectaron gradientes explosivos',

    -- Observaciones adicionales (JSON flexible)
    metricas_adicionales    JSON            DEFAULT NULL    COMMENT 'Métricas adicionales específicas del modelo',
    graficas_paths          JSON            DEFAULT NULL    COMMENT 'Paths a gráficas de pérdida, accuracy, etc.',

    -- Control temporal
    created_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign keys
    CONSTRAINT fk_metricas_entrenamiento
        FOREIGN KEY (id_entrenamiento) REFERENCES entrenamientos(id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    -- Índices
    INDEX idx_metricas_entrenamiento (id_entrenamiento),
    INDEX idx_metricas_loss_final (loss_final),
    INDEX idx_metricas_accuracy (accuracy_validacion)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Métricas y resultados observados de entrenamientos';

-- ============================================================================
-- 2. jobs_entrenamientos_sugeridos — Sugerencias de parámetros para reentrenamiento
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_entrenamientos_sugeridos (
    id                      INT AUTO_INCREMENT PRIMARY KEY,

    -- Relación 1:1 con jobs_entrenamientos (parámetros originales)
    id_job_entrenamiento    INT             NOT NULL UNIQUE COMMENT 'FK a jobs_entrenamientos (parámetros usados)',
    id_entrenamiento        INT             NOT NULL        COMMENT 'FK a entrenamientos',

    -- Identificación de la sugerencia
    nombre_sugerencia       VARCHAR(200)    NOT NULL        COMMENT 'Nombre descriptivo de la sugerencia',
    razon_sugerencia        TEXT            NOT NULL        COMMENT 'Explicación del por qué de los cambios',

    -- Score de confianza
    confianza_score         DECIMAL(5,2)    DEFAULT 0.00    COMMENT 'Confianza en la sugerencia 0-100',
    mejora_esperada_pct     DECIMAL(7,2)    DEFAULT NULL    COMMENT 'Mejora esperada en % (ej: 15.5 = 15.5%)',

    -- ========================================================================
    -- PARÁMETROS SUGERIDOS (misma estructura que jobs_entrenamientos)
    -- ========================================================================

    -- Parámetros de entrenamiento
    learning_rate_sugerido      DECIMAL(10,8)   DEFAULT NULL    COMMENT 'Tasa de aprendizaje sugerida',
    learning_rate_cambio        VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    learning_rate_razon         TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    batch_size_sugerido         INT             DEFAULT NULL    COMMENT 'Tamaño de lote sugerido',
    batch_size_cambio           VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    batch_size_razon            TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    epochs_sugerido             INT             DEFAULT NULL    COMMENT 'Número de épocas sugerido',
    epochs_cambio               VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    epochs_razon                TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    embedding_dimension_sugerido INT            DEFAULT NULL    COMMENT 'Dimensión de embeddings sugerida',
    embedding_dimension_cambio  VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    embedding_dimension_razon   TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    sequence_length_sugerido    INT             DEFAULT NULL    COMMENT 'Longitud de secuencia sugerida',
    sequence_length_cambio      VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    sequence_length_razon       TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    hidden_units_sugerido       INT             DEFAULT NULL    COMMENT 'Unidades ocultas sugeridas',
    hidden_units_cambio         VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    hidden_units_razon          TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    dropout_rate_sugerido       DECIMAL(5,4)    DEFAULT NULL    COMMENT 'Tasa de dropout sugerida',
    dropout_rate_cambio         VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    dropout_rate_razon          TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    -- Parámetros ChromaDB / RAG
    distance_metric_sugerido    VARCHAR(50)     DEFAULT NULL    COMMENT 'Métrica de distancia sugerida',
    distance_metric_cambio      VARCHAR(20)     DEFAULT NULL    COMMENT 'cambiar|mantener',
    distance_metric_razon       TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    top_k_sugerido              INT             DEFAULT NULL    COMMENT 'Top-k sugerido',
    top_k_cambio                VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    top_k_razon                 TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    chunk_size_sugerido         INT             DEFAULT NULL    COMMENT 'Tamaño de chunk sugerido',
    chunk_size_cambio           VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    chunk_size_razon            TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    chunk_overlap_sugerido      INT             DEFAULT NULL    COMMENT 'Overlap sugerido',
    chunk_overlap_cambio        VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    chunk_overlap_razon         TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    -- Parámetros de generación
    temperature_sugerido        DECIMAL(4,3)    DEFAULT NULL    COMMENT 'Temperatura sugerida',
    temperature_cambio          VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    temperature_razon           TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    max_tokens_sugerido         INT             DEFAULT NULL    COMMENT 'Max tokens sugerido',
    max_tokens_cambio           VARCHAR(20)     DEFAULT NULL    COMMENT 'aumentar|disminuir|mantener',
    max_tokens_razon            TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    -- Parámetros de optimización
    loss_function_sugerido      VARCHAR(100)    DEFAULT NULL    COMMENT 'Función de pérdida sugerida',
    loss_function_cambio        VARCHAR(20)     DEFAULT NULL    COMMENT 'cambiar|mantener',
    loss_function_razon         TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    optimizer_sugerido          VARCHAR(100)    DEFAULT NULL    COMMENT 'Optimizador sugerido',
    optimizer_cambio            VARCHAR(20)     DEFAULT NULL    COMMENT 'cambiar|mantener',
    optimizer_razon             TEXT            DEFAULT NULL    COMMENT 'Razón del cambio',

    -- Información adicional
    tecnicas_adicionales        JSON            DEFAULT NULL    COMMENT 'Técnicas adicionales sugeridas (early stopping, lr schedule, etc.)',
    prioridad_cambios           JSON            DEFAULT NULL    COMMENT 'Array ordenado de cambios por prioridad',

    -- Estado de aplicación
    aplicado                    TINYINT(1)      DEFAULT 0       COMMENT '1=Sugerencias aplicadas en nuevo entrenamiento',
    id_entrenamiento_aplicado   INT             DEFAULT NULL    COMMENT 'FK a entrenamientos donde se aplicó',

    -- Control temporal
    created_at                  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign keys
    CONSTRAINT fk_sugerencia_job_params
        FOREIGN KEY (id_job_entrenamiento) REFERENCES jobs_entrenamientos(id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_sugerencia_entrenamiento
        FOREIGN KEY (id_entrenamiento) REFERENCES entrenamientos(id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_sugerencia_aplicado
        FOREIGN KEY (id_entrenamiento_aplicado) REFERENCES entrenamientos(id)
        ON DELETE SET NULL ON UPDATE CASCADE,

    -- Índices
    INDEX idx_sugerencias_job (id_job_entrenamiento),
    INDEX idx_sugerencias_entrenamiento (id_entrenamiento),
    INDEX idx_sugerencias_aplicado (aplicado),
    INDEX idx_sugerencias_confianza (confianza_score)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Sugerencias automáticas de parámetros para reentrenamiento';

-- ============================================================================
-- 3. VISTA: Comparativa parámetros originales vs sugeridos
-- ============================================================================
CREATE OR REPLACE VIEW view_parametros_comparativa AS
SELECT
    e.id AS entrenamiento_id,
    e.numero_secuencia,
    e.estado AS entrenamiento_estado,

    -- Info del job original
    je.id AS params_originales_id,
    je.nombre AS params_originales_nombre,

    -- Info de sugerencias
    js.id AS sugerencias_id,
    js.nombre_sugerencia,
    js.razon_sugerencia,
    js.confianza_score,
    js.mejora_esperada_pct,
    js.aplicado,

    -- Métricas del entrenamiento
    em.loss_final,
    em.accuracy_validacion,
    em.retrieval_precision,
    em.overfitting_detectado,
    em.convergencia_lenta,

    -- Comparativa Learning Rate
    je.learning_rate AS lr_original,
    js.learning_rate_sugerido AS lr_sugerido,
    js.learning_rate_cambio AS lr_cambio,

    -- Comparativa Batch Size
    je.batch_size AS batch_original,
    js.batch_size_sugerido AS batch_sugerido,
    js.batch_size_cambio AS batch_cambio,

    -- Comparativa Epochs
    je.epochs AS epochs_original,
    js.epochs_sugerido AS epochs_sugerido,
    js.epochs_cambio AS epochs_cambio,

    -- Comparativa Dropout
    je.dropout_rate AS dropout_original,
    js.dropout_rate_sugerido AS dropout_sugerido,
    js.dropout_rate_cambio AS dropout_cambio,

    -- Comparativa Chunk Size
    je.chunk_size AS chunk_size_original,
    js.chunk_size_sugerido AS chunk_size_sugerido,
    js.chunk_size_cambio AS chunk_size_cambio,

    -- Comparativa Temperature
    je.temperature AS temp_original,
    js.temperature_sugerido AS temp_sugerido,
    js.temperature_cambio AS temp_cambio,

    e.created_at,
    js.updated_at AS sugerencias_fecha

FROM entrenamientos e
LEFT JOIN jobs_entrenamientos je
    ON e.id_job_entrenamientos = je.id
LEFT JOIN jobs_entrenamientos_sugeridos js
    ON je.id = js.id_job_entrenamiento
LEFT JOIN entrenamientos_metricas em
    ON e.id = em.id_entrenamiento
ORDER BY e.created_at DESC;

-- ============================================================================
-- PERMISOS
-- ============================================================================

-- Tabla entrenamientos_metricas
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.entrenamientos_metricas TO 'myllm_writer'@'localhost';
GRANT SELECT ON myllm_projects_db.entrenamientos_metricas TO 'myllm_reader'@'localhost';

-- Tabla jobs_entrenamientos_sugeridos
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_entrenamientos_sugeridos TO 'myllm_writer'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_entrenamientos_sugeridos TO 'myllm_reader'@'localhost';

-- Vista
GRANT SELECT ON myllm_projects_db.view_parametros_comparativa TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.view_parametros_comparativa TO 'myllm_writer'@'localhost';

FLUSH PRIVILEGES;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
SELECT '✅ Migración 013 completada: Sistema de optimización de entrenamientos creado' AS resultado;
SELECT COUNT(*) AS total_metricas FROM entrenamientos_metricas;
SELECT COUNT(*) AS total_sugerencias FROM jobs_entrenamientos_sugeridos;

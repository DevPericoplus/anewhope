-- ============================================================================
-- Migración: 014_training_model_analysis.sql
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-15
-- Descripción: Tabla para almacenar análisis de modelos generados.
--              Permite tracking de evolución de calidad del modelo a través
--              de múltiples reentrenamientos.
-- ============================================================================

USE myllm_projects_db;

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ============================================================================
-- job_entrenamientos_analisis — Análisis de calidad de modelos generados
-- ============================================================================
CREATE TABLE IF NOT EXISTS job_entrenamientos_analisis (
    id                          INT AUTO_INCREMENT PRIMARY KEY,

    -- Relación con entrenamiento
    id_entrenamiento            INT             NOT NULL UNIQUE COMMENT 'FK a entrenamientos',
    id_job_entrenamientos       INT             NOT NULL        COMMENT 'FK a jobs_entrenamientos',

    -- Identificación del modelo
    numero_secuencia            INT             NOT NULL        COMMENT 'Secuencia del entrenamiento',
    nombre_modelo               VARCHAR(300)    DEFAULT NULL    COMMENT 'Nombre del modelo generado',
    ruta_modelo                 VARCHAR(500)    DEFAULT NULL    COMMENT 'Ruta del modelo en filesystem',

    -- Métricas de calidad RAG
    rag_precision               DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Precisión de recuperación 0-1',
    rag_recall                  DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Recall de recuperación 0-1',
    rag_f1_score                DECIMAL(7,4)    DEFAULT NULL    COMMENT 'F1 score de RAG',
    rag_mrr                     DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Mean Reciprocal Rank',
    rag_ndcg                    DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Normalized Discounted Cumulative Gain',
    avg_retrieval_time_ms       INT             DEFAULT NULL    COMMENT 'Tiempo promedio de recuperación en ms',

    -- Métricas de calidad de respuestas
    response_relevance          DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Relevancia de respuestas 0-1',
    response_coherence          DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Coherencia de respuestas 0-1',
    response_fluency            DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Fluidez de respuestas 0-1',
    response_groundedness       DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Fundamentación en documentos 0-1',
    response_completeness       DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Completitud de respuestas 0-1',

    -- Métricas de similitud semántica
    semantic_similarity_score   DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Score promedio de similitud semántica',
    embedding_quality_score     DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Calidad de embeddings generados',

    -- Métricas de generación
    bleu_score                  DECIMAL(7,4)    DEFAULT NULL    COMMENT 'BLEU score (n-gram overlap)',
    rouge_1                     DECIMAL(7,4)    DEFAULT NULL    COMMENT 'ROUGE-1 score',
    rouge_2                     DECIMAL(7,4)    DEFAULT NULL    COMMENT 'ROUGE-2 score',
    rouge_l                     DECIMAL(7,4)    DEFAULT NULL    COMMENT 'ROUGE-L score',
    meteor_score                DECIMAL(7,4)    DEFAULT NULL    COMMENT 'METEOR score',
    perplexity                  DECIMAL(12,4)   DEFAULT NULL    COMMENT 'Perplejidad del modelo',

    -- Métricas de factualidad
    factual_accuracy            DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Precisión factual 0-1',
    hallucination_rate          DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Tasa de alucinaciones 0-1 (menor mejor)',
    citation_accuracy           DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Precisión de citaciones 0-1',

    -- Métricas de eficiencia
    avg_inference_time_ms       INT             DEFAULT NULL    COMMENT 'Tiempo promedio de inferencia en ms',
    tokens_per_second           DECIMAL(10,2)   DEFAULT NULL    COMMENT 'Throughput de generación',
    memory_usage_mb             INT             DEFAULT NULL    COMMENT 'Uso de memoria en MB',
    model_size_mb               INT             DEFAULT NULL    COMMENT 'Tamaño del modelo en MB',

    -- Métricas de evaluación de usuario (simuladas o reales)
    user_satisfaction_score     DECIMAL(4,2)    DEFAULT NULL    COMMENT 'Score de satisfacción 1-5',
    task_completion_rate        DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Tasa de completación de tareas 0-1',

    -- Score general (calculado)
    overall_quality_score       DECIMAL(7,4)    DEFAULT NULL    COMMENT 'Score general ponderado 0-1',
    improvement_vs_previous_pct DECIMAL(7,2)    DEFAULT NULL    COMMENT 'Mejora vs entrenamiento anterior %',

    -- Dataset de evaluación usado
    eval_dataset_size           INT             DEFAULT NULL    COMMENT 'Tamaño del dataset de evaluación',
    eval_dataset_name           VARCHAR(200)    DEFAULT NULL    COMMENT 'Nombre del dataset usado',

    -- Notas y observaciones
    notas                       TEXT            DEFAULT NULL    COMMENT 'Observaciones del análisis',
    metricas_adicionales        JSON            DEFAULT NULL    COMMENT 'Métricas adicionales en JSON',

    -- Control de versiones de análisis
    version_analisis            INT             DEFAULT 1       COMMENT 'Versión del análisis (para reanalizar)',
    analisis_automatico         TINYINT(1)      DEFAULT 1       COMMENT '1=automático, 0=manual',

    -- Control temporal
    fecha_analisis              DATETIME        DEFAULT NULL    COMMENT 'Cuándo se realizó el análisis',
    duracion_analisis_seg       INT             DEFAULT NULL    COMMENT 'Duración del análisis en segundos',
    created_at                  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign keys
    CONSTRAINT fk_analisis_entrenamiento
        FOREIGN KEY (id_entrenamiento) REFERENCES entrenamientos(id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_analisis_job_params
        FOREIGN KEY (id_job_entrenamientos) REFERENCES jobs_entrenamientos(id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    -- Índices
    INDEX idx_analisis_entrenamiento (id_entrenamiento),
    INDEX idx_analisis_secuencia (numero_secuencia),
    INDEX idx_analisis_quality (overall_quality_score),
    INDEX idx_analisis_fecha (fecha_analisis)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Análisis de calidad de modelos generados por entrenamiento';

-- ============================================================================
-- VISTA: Evolución de calidad por versión
-- ============================================================================
CREATE OR REPLACE VIEW view_evolucion_modelos AS
SELECT
    e.id_organizacion,
    e.id_proyecto,
    e.id_version,
    e.numero_secuencia,
    e.id AS entrenamiento_id,
    e.estado AS entrenamiento_estado,
    e.fecha_fin AS fecha_entrenamiento,

    -- Parámetros usados
    je.learning_rate,
    je.batch_size,
    je.epochs,
    je.dropout_rate,
    je.chunk_size,
    je.temperature,

    -- Métricas de análisis
    ja.overall_quality_score,
    ja.improvement_vs_previous_pct,
    ja.rag_precision,
    ja.rag_recall,
    ja.rag_f1_score,
    ja.response_relevance,
    ja.response_coherence,
    ja.bleu_score,
    ja.perplexity,
    ja.factual_accuracy,
    ja.hallucination_rate,
    ja.avg_inference_time_ms,

    -- Tiene sugerencias
    CASE WHEN js.id IS NOT NULL THEN 1 ELSE 0 END AS tiene_sugerencias,
    js.confianza_score AS sugerencias_confianza,
    js.mejora_esperada_pct AS sugerencias_mejora_esperada,

    ja.fecha_analisis,
    e.created_at

FROM entrenamientos e
LEFT JOIN jobs_entrenamientos je
    ON e.id_job_entrenamientos = je.id
LEFT JOIN job_entrenamientos_analisis ja
    ON e.id = ja.id_entrenamiento
LEFT JOIN jobs_entrenamientos_sugeridos js
    ON e.id_job_entrenamientos = js.id_job_entrenamiento

WHERE e.estado = 'completado'
ORDER BY e.id_organizacion, e.id_proyecto, e.id_version, e.numero_secuencia;

-- ============================================================================
-- VISTA: Comparativa entre entrenamientos consecutivos
-- ============================================================================
CREATE OR REPLACE VIEW view_comparativa_consecutivos AS
SELECT
    curr.id_organizacion,
    curr.id_proyecto,
    curr.id_version,
    curr.numero_secuencia AS secuencia_actual,
    prev.numero_secuencia AS secuencia_anterior,

    -- Scores actuales
    curr.overall_quality_score AS score_actual,
    prev.overall_quality_score AS score_anterior,

    -- Mejora real
    ROUND(
        ((curr.overall_quality_score - prev.overall_quality_score) / prev.overall_quality_score) * 100,
        2
    ) AS mejora_real_pct,

    -- Mejora esperada vs real
    curr.sugerencias_mejora_esperada AS mejora_esperada_pct,
    ROUND(
        (((curr.overall_quality_score - prev.overall_quality_score) / prev.overall_quality_score) * 100) -
        COALESCE(curr.sugerencias_mejora_esperada, 0),
        2
    ) AS desviacion_pct,

    -- Métricas específicas
    curr.rag_precision AS rag_precision_actual,
    prev.rag_precision AS rag_precision_anterior,
    curr.response_relevance AS relevance_actual,
    prev.response_relevance AS relevance_anterior,
    curr.perplexity AS perplexity_actual,
    prev.perplexity AS perplexity_anterior,

    -- Parámetros cambiados
    CASE WHEN curr.learning_rate != prev.learning_rate THEN 1 ELSE 0 END AS cambio_lr,
    CASE WHEN curr.batch_size != prev.batch_size THEN 1 ELSE 0 END AS cambio_batch,
    CASE WHEN curr.epochs != prev.epochs THEN 1 ELSE 0 END AS cambio_epochs,

    curr.fecha_analisis AS fecha_analisis_actual,
    prev.fecha_analisis AS fecha_analisis_anterior

FROM view_evolucion_modelos curr
LEFT JOIN view_evolucion_modelos prev
    ON curr.id_organizacion = prev.id_organizacion
    AND curr.id_proyecto = prev.id_proyecto
    AND curr.id_version = prev.id_version
    AND curr.numero_secuencia = prev.numero_secuencia + 1

WHERE curr.overall_quality_score IS NOT NULL
  AND prev.overall_quality_score IS NOT NULL;

-- ============================================================================
-- PERMISOS
-- ============================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.job_entrenamientos_analisis TO 'myllm_writer'@'localhost';
GRANT SELECT ON myllm_projects_db.job_entrenamientos_analisis TO 'myllm_reader'@'localhost';

GRANT SELECT ON myllm_projects_db.view_evolucion_modelos TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.view_evolucion_modelos TO 'myllm_writer'@'localhost';

GRANT SELECT ON myllm_projects_db.view_comparativa_consecutivos TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.view_comparativa_consecutivos TO 'myllm_writer'@'localhost';

FLUSH PRIVILEGES;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
SELECT '✅ Migración 014 completada: Tabla de análisis de modelos creada' AS resultado;
SELECT COUNT(*) AS total_analisis FROM job_entrenamientos_analisis;

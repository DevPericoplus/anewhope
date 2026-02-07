-- ============================================================================
-- Migración: Extensión de tabla estado_version para ciclo de vida completo
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-07
-- Descripción:
--   - Extiende estado_version con campos para gestionar el flujo completo
--   - Agrega state_internal para uso en backoffice
--   - Mantiene state original para explorador (estabilidad)
--   - Soporta fases: Propuesta → Entrenamiento → Evaluación → Generación → Notificación
-- ============================================================================

USE myllm_projects_db;
SET NAMES utf8mb4;

-- ============================================================================
-- 1. Agregar campo state_internal (estado interno para backoffice)
-- ============================================================================

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS state_internal VARCHAR(50) NULL DEFAULT 'propuesta_cliente'
COMMENT 'Estado interno para backoffice (sincronizado con página Flujos)';

-- Crear índice para búsquedas por estado interno
CREATE INDEX IF NOT EXISTS idx_state_internal ON estado_version(state_internal);

SELECT 'Campo state_internal agregado' AS resultado;

-- ============================================================================
-- 2. Agregar campos de Fase 1: Bucle de Propuesta/Revisión
-- ============================================================================
-- NOTA: propuesta_cliente ya existe como final_c (implícito)
-- aceptacion_cliente = final_c
-- aceptacion_interna = final_i

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS revision_interna TINYINT(1) NOT NULL DEFAULT 0
COMMENT 'Revisión interna en curso (bucle propuesta-revisión-mejoras)';

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS propuesta_mejoras TINYINT(1) NOT NULL DEFAULT 0
COMMENT 'Propuesta de mejoras generada (bucle propuesta-revisión-mejoras)';

SELECT 'Campos de Fase 1 (Propuesta/Revisión) agregados' AS resultado;

-- ============================================================================
-- 3. Agregar campos de Fase 2: Entrenamiento Inicial
-- ============================================================================

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS entrenamiento_inicial_solicitado TINYINT(1) NOT NULL DEFAULT 0
COMMENT 'Entrenamiento inicial solicitado (activado automáticamente cuando final_c=1 AND final_i=1)';

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS entrenamiento_inicial_completado TINYINT(1) NOT NULL DEFAULT 0
COMMENT 'Entrenamiento inicial completado';

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS entrenamiento_inicial_fecha DATETIME NULL DEFAULT NULL
COMMENT 'Fecha de completado del entrenamiento inicial';

SELECT 'Campos de Fase 2 (Entrenamiento Inicial) agregados' AS resultado;

-- ============================================================================
-- 4. Agregar campos de Fase 3: Bucle de Evaluación/Reentrenamiento
-- ============================================================================

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS evaluacion_entrenamiento TINYINT(1) NOT NULL DEFAULT 0
COMMENT 'Evaluación del entrenamiento en curso (bucle evaluación-reentrenamiento-optimización)';

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS reentrenamiento TINYINT(1) NOT NULL DEFAULT 0
COMMENT 'Reentrenamiento en curso (bucle evaluación-reentrenamiento-optimización)';

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS optimizacion TINYINT(1) NOT NULL DEFAULT 0
COMMENT 'Optimización del modelo en curso (bucle evaluación-reentrenamiento-optimización)';

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS control_calidad_aprobado TINYINT(1) NOT NULL DEFAULT 0
COMMENT 'Control de calidad aprobado (salida del bucle de entrenamiento)';

SELECT 'Campos de Fase 3 (Evaluación/Reentrenamiento) agregados' AS resultado;

-- ============================================================================
-- 5. Agregar campos de Fase 4: Generación del Modelo LLM
-- ============================================================================

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS generacion_llm_solicitada TINYINT(1) NOT NULL DEFAULT 0
COMMENT 'Generación del fichero LLM solicitada';

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS generacion_llm_completada TINYINT(1) NOT NULL DEFAULT 0
COMMENT 'Generación del fichero LLM completada';

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS generacion_llm_fecha DATETIME NULL DEFAULT NULL
COMMENT 'Fecha de completado de la generación del modelo';

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS ruta_fichero_modelo VARCHAR(500) NULL DEFAULT NULL
COMMENT 'Ruta del fichero del modelo LLM generado';

SELECT 'Campos de Fase 4 (Generación LLM) agregados' AS resultado;

-- ============================================================================
-- 6. Agregar campos de Fase 5: Notificación de Descarga
-- ============================================================================

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS notificacion_descarga_enviada TINYINT(1) NOT NULL DEFAULT 0
COMMENT 'Notificación de descarga enviada al cliente';

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS notificacion_descarga_fecha DATETIME NULL DEFAULT NULL
COMMENT 'Fecha de envío de la notificación de descarga';

SELECT 'Campos de Fase 5 (Notificación) agregados' AS resultado;

-- ============================================================================
-- 7. Agregar campos de Metadatos
-- ============================================================================

ALTER TABLE estado_version
ADD COLUMN IF NOT EXISTS updated_by INT NULL DEFAULT NULL
COMMENT 'ID del usuario que hizo el último cambio (myllm_core_db.users.user_id)';

-- Crear índice para búsquedas por usuario
CREATE INDEX IF NOT EXISTS idx_updated_by ON estado_version(updated_by);

SELECT 'Campos de Metadatos agregados' AS resultado;

-- ============================================================================
-- 8. Crear índices compuestos para consultas frecuentes
-- ============================================================================

-- Índice para búsquedas por fase de entrenamiento
CREATE INDEX IF NOT EXISTS idx_fase_entrenamiento
ON estado_version(entrenamiento_inicial_solicitado, entrenamiento_inicial_completado);

-- Índice para búsquedas por control de calidad
CREATE INDEX IF NOT EXISTS idx_control_calidad
ON estado_version(control_calidad_aprobado);

-- Índice para búsquedas por generación LLM
CREATE INDEX IF NOT EXISTS idx_generacion_llm
ON estado_version(generacion_llm_solicitada, generacion_llm_completada);

SELECT 'Índices compuestos creados' AS resultado;

-- ============================================================================
-- 9. Vista para consultar estado completo con nombres legibles
-- ============================================================================

CREATE OR REPLACE VIEW view_estado_version_completo AS
SELECT
    ev.id,
    ev.id_organizacion,
    ev.id_proyecto,
    p.nombre AS proyecto_nombre,
    ev.id_version,
    ev.state,
    ev.state_internal,
    ev.protected,
    ev.size,

    -- Fase 1: Propuesta/Revisión
    ev.final_c AS propuesta_cliente,
    ev.revision_interna,
    ev.propuesta_mejoras,
    ev.final_c AS aceptacion_cliente,
    ev.final_i AS aceptacion_interna,

    -- Fase 2: Entrenamiento Inicial
    ev.entrenamiento_inicial_solicitado,
    ev.entrenamiento_inicial_completado,
    ev.entrenamiento_inicial_fecha,

    -- Fase 3: Evaluación/Reentrenamiento
    ev.evaluacion_entrenamiento,
    ev.reentrenamiento,
    ev.optimizacion,
    ev.control_calidad_aprobado,

    -- Fase 4: Generación LLM
    ev.generacion_llm_solicitada,
    ev.generacion_llm_completada,
    ev.generacion_llm_fecha,
    ev.ruta_fichero_modelo,

    -- Fase 5: Notificación
    ev.notificacion_descarga_enviada,
    ev.notificacion_descarga_fecha,

    -- Metadatos
    ev.created_at,
    ev.updated_at,
    ev.updated_by
FROM estado_version ev
INNER JOIN proyectos p ON ev.id_proyecto = p.id
ORDER BY ev.id_organizacion, p.nombre, ev.id_version;

SELECT 'Vista view_estado_version_completo creada' AS resultado;

-- ============================================================================
-- 10. Documentación de valores de state_internal
-- ============================================================================
-- El campo state_internal puede tener los siguientes valores:
--
-- Fase 1 (Propuesta/Revisión):
--   'propuesta_cliente'     - Cliente propone/solicita (estado inicial)
--   'revision_interna'      - Revisión interna en curso
--   'propuesta_mejoras'     - Propuesta de mejoras generada
--   'aceptacion_cliente'    - Esperando aceptación del cliente (final_c)
--   'aceptacion_interna'    - Esperando aceptación interna (final_i)
--
-- Fase 2 (Entrenamiento Inicial):
--   'entrenamiento_inicial' - Entrenamiento inicial en curso
--
-- Fase 3 (Evaluación/Reentrenamiento):
--   'evaluacion_entrenamiento' - Evaluación en curso
--   'reentrenamiento'          - Reentrenamiento en curso
--   'optimizacion'             - Optimización en curso
--   'aprobacion_calidad'       - Esperando aprobación de calidad
--
-- Fase 4 (Generación LLM):
--   'generacion_llm'        - Generación del modelo LLM en curso
--
-- Fase 5 (Notificación):
--   'notificacion_descarga' - Descarga disponible, notificación enviada

-- ============================================================================
-- 11. Verificación final
-- ============================================================================
SELECT '========== RESUMEN DE CAMBIOS APLICADOS ==========' AS info;

-- Verificar columnas agregadas
SELECT 'Columnas en estado_version:' AS tipo, COUNT(*) AS cantidad
FROM information_schema.columns
WHERE table_schema = 'myllm_projects_db'
AND table_name = 'estado_version';

-- Verificar vista
SELECT 'Vista view_estado_version_completo:' AS tipo,
    CASE WHEN COUNT(*) > 0 THEN 'Existe' ELSE 'No existe' END AS estado
FROM information_schema.views
WHERE table_schema = 'myllm_projects_db'
AND table_name = 'view_estado_version_completo';

-- Verificar índices
SELECT 'Índices en estado_version:' AS tipo, COUNT(*) AS cantidad
FROM information_schema.statistics
WHERE table_schema = 'myllm_projects_db'
AND table_name = 'estado_version';

SELECT '========== MIGRACIÓN COMPLETADA ==========' AS info;

-- ============================================================================
-- NOTAS IMPORTANTES:
-- ============================================================================
-- 1. El campo 'state' original se mantiene sin cambios (para explorador)
-- 2. El nuevo campo 'state_internal' se usa para backoffice/flujos
-- 3. Los triggers de sincronización con tabla 'estado' se crean en migración 009
-- 4. Los triggers de automatización de transiciones se crean en migración 009
-- 5. Al crear nueva versión, se debe inicializar con propuesta_cliente=1 (trigger)
-- ============================================================================

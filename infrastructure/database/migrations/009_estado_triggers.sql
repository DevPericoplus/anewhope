-- ============================================================================
-- Migración: Triggers para sincronización y automatización de estado_version
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-07
-- Descripción:
--   - Triggers para sincronización bidireccional entre estado_version y estado
--   - Triggers para automatización de transiciones de estado
--   - Trigger para actualización automática de state_internal
--   - Inicialización automática al crear nueva versión
-- ============================================================================

USE myllm_projects_db;
SET NAMES utf8mb4;

-- ============================================================================
-- 1. TRIGGER: Inicialización automática al crear nueva versión
-- ============================================================================
-- Cuando se crea una nueva versión en tabla 'versiones', se debe crear
-- automáticamente el registro correspondiente en 'estado_version' con
-- estado inicial (propuesta_cliente = true)

DELIMITER //

DROP TRIGGER IF EXISTS trg_versiones_after_insert//

CREATE TRIGGER trg_versiones_after_insert
AFTER INSERT ON versiones
FOR EACH ROW
BEGIN
    -- Crear registro en estado_version con valores iniciales
    INSERT INTO estado_version (
        id_organizacion,
        id_proyecto,
        id_version,
        state,
        state_internal,
        final_c,
        final_i,
        protected,
        size,
        created_at,
        updated_at
    ) VALUES (
        NEW.id_organizacion,
        NEW.id_proyecto,
        NEW.id_version,
        'stable',                    -- Estado inicial para explorador
        'propuesta_cliente',         -- Estado inicial para backoffice
        0,                           -- Cliente aún no acepta
        0,                           -- Interno aún no acepta
        0,                           -- No protegida por defecto
        0,                           -- Tamaño inicial
        NOW(),
        NOW()
    );
END//

DELIMITER ;

SELECT 'Trigger trg_versiones_after_insert creado' AS resultado;

-- ============================================================================
-- 2. TRIGGER: Sincronización estado_version → estado (AFTER INSERT)
-- ============================================================================
-- Cuando se crea un registro en estado_version, crear el correspondiente
-- en tabla estado con los mismos valores

DELIMITER //

DROP TRIGGER IF EXISTS trg_estado_version_after_insert//

CREATE TRIGGER trg_estado_version_after_insert
AFTER INSERT ON estado_version
FOR EACH ROW
BEGIN
    -- Crear registro espejo en tabla estado
    INSERT INTO estado (
        id_organizacion,
        id_proyecto,
        id_version,
        propuesta_cliente,
        revision_interna,
        propuesta_mejoras,
        aceptacion_cliente,
        aceptacion_interna,
        entrenamiento_inicial,
        evaluacion_entrenamiento,
        reentrenamiento,
        optimizacion,
        aprobacion_calidad,
        generacion_llm,
        notificacion_descarga
    ) VALUES (
        NEW.id_organizacion,
        NEW.id_proyecto,
        NEW.id_version,
        1,                                      -- propuesta_cliente siempre true al inicio
        IFNULL(NEW.revision_interna, 0),
        IFNULL(NEW.propuesta_mejoras, 0),
        IFNULL(NEW.final_c, 0),                -- aceptacion_cliente = final_c
        IFNULL(NEW.final_i, 0),                -- aceptacion_interna = final_i
        IFNULL(NEW.entrenamiento_inicial_completado, 0),
        IFNULL(NEW.evaluacion_entrenamiento, 0),
        IFNULL(NEW.reentrenamiento, 0),
        IFNULL(NEW.optimizacion, 0),
        IFNULL(NEW.control_calidad_aprobado, 0),
        IFNULL(NEW.generacion_llm_completada, 0),
        IFNULL(NEW.notificacion_descarga_enviada, 0)
    );
END//

DELIMITER ;

SELECT 'Trigger trg_estado_version_after_insert creado' AS resultado;

-- ============================================================================
-- 3. TRIGGER: Sincronización estado_version → estado (AFTER UPDATE)
-- ============================================================================
-- Cuando se actualiza estado_version, sincronizar cambios a tabla estado

DELIMITER //

DROP TRIGGER IF EXISTS trg_estado_version_after_update//

CREATE TRIGGER trg_estado_version_after_update
AFTER UPDATE ON estado_version
FOR EACH ROW
BEGIN
    -- Actualizar registro en tabla estado con los valores de estado_version
    UPDATE estado
    SET
        revision_interna = IFNULL(NEW.revision_interna, 0),
        propuesta_mejoras = IFNULL(NEW.propuesta_mejoras, 0),
        aceptacion_cliente = IFNULL(NEW.final_c, 0),
        aceptacion_interna = IFNULL(NEW.final_i, 0),
        entrenamiento_inicial = IFNULL(NEW.entrenamiento_inicial_completado, 0),
        evaluacion_entrenamiento = IFNULL(NEW.evaluacion_entrenamiento, 0),
        reentrenamiento = IFNULL(NEW.reentrenamiento, 0),
        optimizacion = IFNULL(NEW.optimizacion, 0),
        aprobacion_calidad = IFNULL(NEW.control_calidad_aprobado, 0),
        generacion_llm = IFNULL(NEW.generacion_llm_completada, 0),
        notificacion_descarga = IFNULL(NEW.notificacion_descarga_enviada, 0)
    WHERE
        id_organizacion = NEW.id_organizacion
        AND id_proyecto = NEW.id_proyecto
        AND id_version = NEW.id_version;
END//

DELIMITER ;

SELECT 'Trigger trg_estado_version_after_update creado' AS resultado;

-- ============================================================================
-- 4. TRIGGER: Automatización de transición a entrenamiento inicial
-- ============================================================================
-- Cuando final_c=true AND final_i=true → entrenamiento_inicial_solicitado=true
-- Cuando final_c=false OR final_i=false → entrenamiento_inicial_solicitado=false

DELIMITER //

DROP TRIGGER IF EXISTS trg_estado_version_auto_entrenamiento//

CREATE TRIGGER trg_estado_version_auto_entrenamiento
BEFORE UPDATE ON estado_version
FOR EACH ROW
BEGIN
    -- Activar entrenamiento si ambos aprueban
    IF NEW.final_c = 1 AND NEW.final_i = 1 THEN
        SET NEW.entrenamiento_inicial_solicitado = 1;
    END IF;

    -- Desactivar entrenamiento si alguno retira aprobación
    IF NEW.final_c = 0 OR NEW.final_i = 0 THEN
        SET NEW.entrenamiento_inicial_solicitado = 0;
        -- También resetear completado si se retira la solicitud
        IF OLD.entrenamiento_inicial_solicitado = 1 THEN
            SET NEW.entrenamiento_inicial_completado = 0;
            SET NEW.entrenamiento_inicial_fecha = NULL;
        END IF;
    END IF;

    -- Actualizar timestamp
    SET NEW.updated_at = NOW();
END//

DELIMITER ;

SELECT 'Trigger trg_estado_version_auto_entrenamiento creado' AS resultado;

-- ============================================================================
-- 5. TRIGGER: Actualización automática de state_internal
-- ============================================================================
-- Actualiza state_internal basándose en el estado actual del flujo
-- Prioriza el estado más avanzado activo

DELIMITER //

DROP TRIGGER IF EXISTS trg_estado_version_auto_state_internal//

CREATE TRIGGER trg_estado_version_auto_state_internal
BEFORE UPDATE ON estado_version
FOR EACH ROW
BEGIN
    DECLARE new_state_internal VARCHAR(50);

    -- Fase 5: Notificación (más prioritaria)
    IF NEW.notificacion_descarga_enviada = 1 THEN
        SET new_state_internal = 'notificacion_descarga';

    -- Fase 4: Generación LLM
    ELSEIF NEW.generacion_llm_completada = 1 THEN
        SET new_state_internal = 'generacion_llm_completada';
    ELSEIF NEW.generacion_llm_solicitada = 1 THEN
        SET new_state_internal = 'generacion_llm';

    -- Fase 3: Evaluación/Reentrenamiento
    ELSEIF NEW.control_calidad_aprobado = 1 THEN
        SET new_state_internal = 'aprobacion_calidad';
    ELSEIF NEW.optimizacion = 1 THEN
        SET new_state_internal = 'optimizacion';
    ELSEIF NEW.reentrenamiento = 1 THEN
        SET new_state_internal = 'reentrenamiento';
    ELSEIF NEW.evaluacion_entrenamiento = 1 THEN
        SET new_state_internal = 'evaluacion_entrenamiento';

    -- Fase 2: Entrenamiento Inicial
    ELSEIF NEW.entrenamiento_inicial_completado = 1 THEN
        SET new_state_internal = 'entrenamiento_inicial_completado';
    ELSEIF NEW.entrenamiento_inicial_solicitado = 1 THEN
        SET new_state_internal = 'entrenamiento_inicial';

    -- Fase 1: Propuesta/Revisión (bucle)
    ELSEIF NEW.final_i = 1 THEN
        SET new_state_internal = 'aceptacion_interna';
    ELSEIF NEW.final_c = 1 THEN
        SET new_state_internal = 'aceptacion_cliente';
    ELSEIF NEW.propuesta_mejoras = 1 THEN
        SET new_state_internal = 'propuesta_mejoras';
    ELSEIF NEW.revision_interna = 1 THEN
        SET new_state_internal = 'revision_interna';
    ELSE
        SET new_state_internal = 'propuesta_cliente';
    END IF;

    -- Actualizar si cambió
    IF NEW.state_internal != new_state_internal THEN
        SET NEW.state_internal = new_state_internal;
    END IF;
END//

DELIMITER ;

SELECT 'Trigger trg_estado_version_auto_state_internal creado' AS resultado;

-- ============================================================================
-- 6. TRIGGER: Control de transiciones de calidad
-- ============================================================================
-- Asegura que no se pueda solicitar generación LLM sin aprobación de calidad

DELIMITER //

DROP TRIGGER IF EXISTS trg_estado_version_validacion_transiciones//

CREATE TRIGGER trg_estado_version_validacion_transiciones
BEFORE UPDATE ON estado_version
FOR EACH ROW
BEGIN
    -- No permitir generación LLM sin aprobación de calidad
    IF NEW.generacion_llm_solicitada = 1 AND NEW.control_calidad_aprobado = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'No se puede solicitar generación LLM sin aprobación de calidad';
    END IF;

    -- No permitir notificación sin generación completada
    IF NEW.notificacion_descarga_enviada = 1 AND NEW.generacion_llm_completada = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'No se puede enviar notificación sin generación LLM completada';
    END IF;

    -- Actualizar fecha de entrenamiento si se completa
    IF NEW.entrenamiento_inicial_completado = 1 AND OLD.entrenamiento_inicial_completado = 0 THEN
        SET NEW.entrenamiento_inicial_fecha = NOW();
    END IF;

    -- Actualizar fecha de generación si se completa
    IF NEW.generacion_llm_completada = 1 AND OLD.generacion_llm_completada = 0 THEN
        SET NEW.generacion_llm_fecha = NOW();
    END IF;

    -- Actualizar fecha de notificación si se envía
    IF NEW.notificacion_descarga_enviada = 1 AND OLD.notificacion_descarga_enviada = 0 THEN
        SET NEW.notificacion_descarga_fecha = NOW();
    END IF;
END//

DELIMITER ;

SELECT 'Trigger trg_estado_version_validacion_transiciones creado' AS resultado;

-- ============================================================================
-- 7. Verificación de triggers creados
-- ============================================================================
SELECT '========== RESUMEN DE TRIGGERS CREADOS ==========' AS info;

SELECT
    TRIGGER_NAME,
    EVENT_MANIPULATION,
    EVENT_OBJECT_TABLE,
    ACTION_TIMING
FROM information_schema.TRIGGERS
WHERE TRIGGER_SCHEMA = 'myllm_projects_db'
  AND EVENT_OBJECT_TABLE IN ('versiones', 'estado_version')
ORDER BY EVENT_OBJECT_TABLE, ACTION_TIMING, TRIGGER_NAME;

SELECT '========== MIGRACIÓN COMPLETADA ==========' AS info;

-- ============================================================================
-- DOCUMENTACIÓN DE TRIGGERS:
-- ============================================================================
--
-- 1. trg_versiones_after_insert
--    - Tabla: versiones
--    - Momento: AFTER INSERT
--    - Función: Crea registro inicial en estado_version con propuesta_cliente
--    - Valores iniciales: state='stable', state_internal='propuesta_cliente'
--
-- 2. trg_estado_version_after_insert
--    - Tabla: estado_version
--    - Momento: AFTER INSERT
--    - Función: Crea registro espejo en tabla estado
--    - Sincronización: Mapea campos de estado_version a estado
--
-- 3. trg_estado_version_after_update
--    - Tabla: estado_version
--    - Momento: AFTER UPDATE
--    - Función: Sincroniza cambios a tabla estado
--    - Sincronización: Unidireccional estado_version → estado
--
-- 4. trg_estado_version_auto_entrenamiento
--    - Tabla: estado_version
--    - Momento: BEFORE UPDATE
--    - Función: Automatiza transición a entrenamiento
--    - Lógica:
--      * Si final_c=1 AND final_i=1 → entrenamiento_inicial_solicitado=1
--      * Si final_c=0 OR final_i=0 → entrenamiento_inicial_solicitado=0
--      * Resetea completado si se retira solicitud
--
-- 5. trg_estado_version_auto_state_internal
--    - Tabla: estado_version
--    - Momento: BEFORE UPDATE
--    - Función: Actualiza state_internal según fase activa
--    - Prioridad: Fase 5 > Fase 4 > Fase 3 > Fase 2 > Fase 1
--    - Estados posibles (ver líneas 210-232 de migración 008)
--
-- 6. trg_estado_version_validacion_transiciones
--    - Tabla: estado_version
--    - Momento: BEFORE UPDATE
--    - Función: Valida transiciones y actualiza fechas
--    - Validaciones:
--      * Generación LLM requiere aprobación de calidad
--      * Notificación requiere generación completada
--    - Automatiza fechas:
--      * entrenamiento_inicial_fecha
--      * generacion_llm_fecha
--      * notificacion_descarga_fecha
--
-- ============================================================================
-- FLUJO COMPLETO DE TRIGGERS:
-- ============================================================================
--
-- ESCENARIO 1: Crear nueva versión desde 'Proyecciones'
-- -------------------------------------------------------
-- 1. INSERT INTO versiones (...)
--    ↓ [trg_versiones_after_insert]
-- 2. INSERT INTO estado_version (..., state_internal='propuesta_cliente')
--    ↓ [trg_estado_version_after_insert]
-- 3. INSERT INTO estado (..., propuesta_cliente=1)
--
-- ESCENARIO 2: Aprobar propuesta (cliente + interno)
-- -------------------------------------------------------
-- 1. UPDATE estado_version SET final_c=1, final_i=1
--    ↓ [trg_estado_version_auto_entrenamiento]
-- 2. Automáticamente: entrenamiento_inicial_solicitado=1
--    ↓ [trg_estado_version_auto_state_internal]
-- 3. Automáticamente: state_internal='entrenamiento_inicial'
--    ↓ [trg_estado_version_after_update]
-- 4. UPDATE estado SET aceptacion_cliente=1, aceptacion_interna=1
--
-- ESCENARIO 3: Completar entrenamiento y aprobar calidad
-- -------------------------------------------------------
-- 1. UPDATE estado_version SET entrenamiento_inicial_completado=1
--    ↓ [trg_estado_version_validacion_transiciones]
-- 2. Automáticamente: entrenamiento_inicial_fecha=NOW()
--    ↓ [trg_estado_version_auto_state_internal]
-- 3. Automáticamente: state_internal='entrenamiento_inicial_completado'
-- 4. UPDATE estado_version SET control_calidad_aprobado=1
--    ↓ [trg_estado_version_auto_state_internal]
-- 5. Automáticamente: state_internal='aprobacion_calidad'
--
-- ESCENARIO 4: Generar modelo y notificar
-- -------------------------------------------------------
-- 1. UPDATE estado_version SET generacion_llm_solicitada=1
--    ↓ [trg_estado_version_validacion_transiciones] - Valida calidad aprobada
-- 2. Si OK → continúa
-- 3. UPDATE estado_version SET generacion_llm_completada=1
--    ↓ [trg_estado_version_validacion_transiciones]
-- 4. Automáticamente: generacion_llm_fecha=NOW()
--    ↓ [trg_estado_version_auto_state_internal]
-- 5. Automáticamente: state_internal='generacion_llm_completada'
-- 6. UPDATE estado_version SET notificacion_descarga_enviada=1
--    ↓ [trg_estado_version_validacion_transiciones]
-- 7. Automáticamente: notificacion_descarga_fecha=NOW()
--    ↓ [trg_estado_version_auto_state_internal]
-- 8. Automáticamente: state_internal='notificacion_descarga'
--
-- ============================================================================

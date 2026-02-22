-- ============================================================================
-- Migración: 016_fix_estado_fk_version.sql
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-21
-- Descripción:
--   Corrige la FK fk_estado_version en tabla 'estado', reconstruye los datos,
--   y corrige los triggers de sincronización estado_version → estado.
--
--   Problema raíz: La tabla estado almacenaba versiones.id (PK auto-increment)
--   como id_version, cuando debería almacenar versiones.id_version (número de
--   versión del proyecto: 1, 2, 3...).
--
--   Esto afectaba a:
--   - FK fk_estado_version: referenciaba versiones(id) en vez de (id_proyecto, id_version)
--   - Trigger trg_estado_version_after_insert: hacía SELECT id INTO versiones_id
--     y lo usaba como id_version en el INSERT a estado
--   - Trigger trg_estado_version_after_update: mismo patrón incorrecto
--   - Datos en estado: mezclaban versiones.id (viejos) con versiones.id_version (nuevos)
--
--   Solución:
--   1. Eliminar FK incorrecta
--   2. Corregir triggers para usar NEW.id_version directamente
--   3. Reconstruir datos de estado desde estado_version
--   4. Crear FK compuesta referenciando versiones(id_proyecto, id_version)
-- ============================================================================

USE myllm_projects_db;

-- ============================================================================
-- 1. Eliminar la FK incorrecta (idempotente)
-- ============================================================================
SET @fk_exists = (
    SELECT COUNT(*)
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = 'myllm_projects_db'
      AND TABLE_NAME = 'estado'
      AND CONSTRAINT_NAME = 'fk_estado_version'
);

SET @sql_drop_fk = IF(@fk_exists > 0,
    'ALTER TABLE estado DROP FOREIGN KEY fk_estado_version',
    'SELECT "FK ya eliminada" AS info');
PREPARE stmt FROM @sql_drop_fk;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @idx_exists = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = 'myllm_projects_db'
      AND TABLE_NAME = 'estado'
      AND INDEX_NAME = 'idx_estado_version'
);

SET @sql_drop_idx = IF(@idx_exists > 0,
    'ALTER TABLE estado DROP INDEX idx_estado_version',
    'SELECT "Índice ya eliminado" AS info');
PREPARE stmt FROM @sql_drop_idx;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT 'Paso 1: FK e índice eliminados' AS status;

-- ============================================================================
-- 2. Corregir trigger trg_estado_version_after_insert
--    Antes: hacía SELECT versiones.id y lo insertaba como id_version
--    Ahora: usa NEW.id_version directamente (el número de versión correcto)
-- ============================================================================

DROP TRIGGER IF EXISTS trg_estado_version_after_insert;

DELIMITER $$
CREATE TRIGGER trg_estado_version_after_insert
AFTER INSERT ON estado_version
FOR EACH ROW
BEGIN
    -- Insertar registro espejo en tabla estado usando id_version directamente
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
        1,
        IFNULL(NEW.revision_interna, 0),
        IFNULL(NEW.propuesta_mejoras, 0),
        IFNULL(NEW.final_c, 0),
        IFNULL(NEW.final_i, 0),
        IFNULL(NEW.entrenamiento_inicial_completado, 0),
        IFNULL(NEW.evaluacion_entrenamiento, 0),
        IFNULL(NEW.reentrenamiento, 0),
        IFNULL(NEW.optimizacion, 0),
        IFNULL(NEW.control_calidad_aprobado, 0),
        IFNULL(NEW.generacion_llm_completada, 0),
        IFNULL(NEW.notificacion_descarga_enviada, 0)
    );
END$$
DELIMITER ;

SELECT 'Paso 2a: Trigger trg_estado_version_after_insert corregido' AS status;

-- ============================================================================
-- 3. Corregir trigger trg_estado_version_after_update
--    Antes: hacía SELECT versiones.id y lo usaba para localizar el registro en estado
--    Ahora: usa NEW.id_version directamente
-- ============================================================================

DROP TRIGGER IF EXISTS trg_estado_version_after_update;

DELIMITER $$
CREATE TRIGGER trg_estado_version_after_update
AFTER UPDATE ON estado_version
FOR EACH ROW
BEGIN
    -- Actualizar registro en tabla estado usando id_version directamente
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
END$$
DELIMITER ;

SELECT 'Paso 2b: Trigger trg_estado_version_after_update corregido' AS status;

-- ============================================================================
-- 4. Reconstruir datos de estado desde estado_version
-- ============================================================================

TRUNCATE TABLE estado;

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
)
SELECT
    ev.id_organizacion,
    ev.id_proyecto,
    ev.id_version,
    1,
    IFNULL(ev.revision_interna, 0),
    IFNULL(ev.propuesta_mejoras, 0),
    IFNULL(ev.final_c, 0),
    IFNULL(ev.final_i, 0),
    IFNULL(ev.entrenamiento_inicial_completado, 0),
    IFNULL(ev.evaluacion_entrenamiento, 0),
    IFNULL(ev.reentrenamiento, 0),
    IFNULL(ev.optimizacion, 0),
    IFNULL(ev.control_calidad_aprobado, 0),
    IFNULL(ev.generacion_llm_completada, 0),
    IFNULL(ev.notificacion_descarga_enviada, 0)
FROM estado_version ev;

SELECT CONCAT('Paso 3: Datos reconstruidos - ', COUNT(*), ' registros') AS status FROM estado;

-- ============================================================================
-- 5. Crear FK compuesta correcta
-- ============================================================================
ALTER TABLE estado
  ADD CONSTRAINT fk_estado_version
  FOREIGN KEY (id_proyecto, id_version)
  REFERENCES versiones (id_proyecto, id_version)
  ON DELETE CASCADE;

SELECT 'Paso 4: FK compuesta fk_estado_version creada' AS status;

-- ============================================================================
-- 6. Verificación
-- ============================================================================
SELECT
  CONSTRAINT_NAME,
  COLUMN_NAME,
  REFERENCED_TABLE_NAME,
  REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'myllm_projects_db'
  AND TABLE_NAME = 'estado'
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION;

SELECT '016_fix_estado_fk_version: COMPLETADA' AS resultado;

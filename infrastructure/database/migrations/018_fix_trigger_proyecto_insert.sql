-- ============================================================================
-- Migración: 018_fix_trigger_proyecto_insert.sql
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-22
-- Descripción:
--   ELIMINA el trigger tr_proyecto_after_insert.
--
--   Problema raíz: El trigger intentaba INSERT en 'cambios' con id_version=0,
--   pero la FK fk_cambios_version requiere que id_version exista en versiones(id).
--   En el momento del trigger (AFTER INSERT ON proyectos) aún no existe
--   ninguna versión para ese proyecto.
--
--   Solución: Eliminar el trigger por completo. La creación de la versión v001,
--   carpeta fmanagement, estado y registro en cambios la gestiona íntegramente
--   create_version_full() en el backend core (routercore.py PASO 2).
--   Esa función:
--     1. Inserta en 'versiones' → dispara trg_versiones_after_insert
--        → INSERT estado_version → trg_estado_version_after_insert → INSERT estado
--     2. Inserta en 'cambios' con tipo 'VERSION_CREADA'
--     3. El código de create_project() también registra 'alta_proyecto' en cambios
-- ============================================================================

USE myllm_projects_db;

-- ============================================================================
-- 1. Eliminar trigger tr_proyecto_after_insert
-- ============================================================================

DROP TRIGGER IF EXISTS tr_proyecto_after_insert;

SELECT 'Paso 1: Trigger tr_proyecto_after_insert ELIMINADO' AS status;

-- ============================================================================
-- 2. Verificación de triggers restantes
-- ============================================================================
SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE, ACTION_TIMING
FROM information_schema.TRIGGERS
WHERE TRIGGER_SCHEMA = 'myllm_projects_db'
  AND EVENT_OBJECT_TABLE IN ('proyectos', 'versiones', 'estado_version')
ORDER BY EVENT_OBJECT_TABLE, ACTION_TIMING;

SELECT '018_fix_trigger_proyecto_insert: COMPLETADA (trigger eliminado)' AS resultado;

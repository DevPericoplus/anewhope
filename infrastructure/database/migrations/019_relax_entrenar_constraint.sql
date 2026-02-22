-- ============================================================================
-- Migración: 019_relax_entrenar_constraint.sql
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-22
-- Descripción:
--   Relaja el CHECK constraint chk_state_protected para que el estado
--   'Entrenar' permita final_i=0 o final_i=1.
--
--   Problema: El constraint original exigía final_i=0 para 'Entrenar',
--   pero el trigger trg_estado_version_auto_entrenamiento requiere
--   final_c=1 AND final_i=1 para activar entrenamiento_inicial_solicitado.
--   Esto impedía que la acción "Entrenar" del explorador hiciera visible
--   la versión en la página de Entrenamientos.
--
--   Solución: Permitir que 'Entrenar' tenga cualquier valor de final_i.
--   Así el explorador puede establecer todos los campos del workflow
--   y el trigger activará entrenamiento_inicial_solicitado automáticamente.
-- ============================================================================

USE myllm_projects_db;

-- ============================================================================
-- 1. Eliminar constraint actual
-- ============================================================================

ALTER TABLE estado_version DROP CONSTRAINT IF EXISTS chk_state_protected;

SELECT 'Paso 1: CHECK constraint eliminado' AS status;

-- ============================================================================
-- 2. Crear constraint relajado
-- ============================================================================
-- Entrenar: protected=1, final_c=1 (final_i libre para 0 o 1)
-- El resto de estados mantienen sus restricciones originales

ALTER TABLE estado_version ADD CONSTRAINT chk_state_protected CHECK (
    (state = 'Abierta'   AND protected = 0 AND final_c = 0 AND final_i = 0)
 OR (state = 'Bloqueada' AND protected = 1 AND final_c = 0 AND final_i = 0)
 OR (state = 'Entrenar'  AND protected = 1 AND final_c = 1)
 OR (state = 'Final'     AND protected = 1 AND final_c = 1 AND final_i = 1)
);

SELECT 'Paso 2: CHECK constraint recreado (Entrenar con final_i flexible)' AS status;

-- ============================================================================
-- 3. Verificación
-- ============================================================================

SELECT CONSTRAINT_NAME, CHECK_CLAUSE
FROM information_schema.CHECK_CONSTRAINTS
WHERE TABLE_NAME = 'estado_version'
  AND CONSTRAINT_SCHEMA = 'myllm_projects_db';

SELECT '019_relax_entrenar_constraint: COMPLETADA' AS resultado;

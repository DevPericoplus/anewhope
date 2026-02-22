-- ============================================================================
-- Migración: 017_fix_estado_enum_entrenar.sql
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-22
-- Descripción:
--   Corrige el ENUM de state en estado_version y version_states:
--   - Cambia 'Protegida' → 'Entrenar' para coincidir con la documentación
--   - Actualiza el CHECK constraint chk_state_protected
--   - Actualiza datos existentes con state='Protegida' a state='Entrenar'
--
--   Según AGENTS.md sección 25.1, los estados válidos son:
--   Abierta, Bloqueada, Entrenar, Final
-- ============================================================================

USE myllm_projects_db;

-- ============================================================================
-- 1. Eliminar CHECK constraint existente (usa 'Protegida')
-- ============================================================================
ALTER TABLE estado_version DROP CONSTRAINT IF EXISTS chk_state_protected;

SELECT 'Paso 1: CHECK constraint eliminado' AS status;

-- ============================================================================
-- 2. Cambiar ENUM en estado_version: añadir 'Entrenar'
-- ============================================================================
ALTER TABLE estado_version
MODIFY COLUMN state ENUM('Abierta', 'Bloqueada', 'Protegida', 'Entrenar', 'Final')
NOT NULL DEFAULT 'Abierta';

SELECT 'Paso 2: ENUM ampliado con Entrenar' AS status;

-- ============================================================================
-- 3. Migrar datos existentes: 'Protegida' → 'Entrenar'
-- ============================================================================
UPDATE estado_version SET state = 'Entrenar' WHERE state = 'Protegida';

SELECT CONCAT('Paso 3: ', ROW_COUNT(), ' registros migrados de Protegida a Entrenar') AS status;

-- ============================================================================
-- 4. Eliminar 'Protegida' del ENUM (ya no se usa)
-- ============================================================================
ALTER TABLE estado_version
MODIFY COLUMN state ENUM('Abierta', 'Bloqueada', 'Entrenar', 'Final')
NOT NULL DEFAULT 'Abierta';

SELECT 'Paso 4: Protegida eliminado del ENUM' AS status;

-- ============================================================================
-- 5. Recrear CHECK constraint con 'Entrenar'
-- ============================================================================
ALTER TABLE estado_version
ADD CONSTRAINT chk_state_protected CHECK (
    (state = 'Abierta' AND protected = FALSE AND final_c = FALSE AND final_i = FALSE) OR
    (state = 'Bloqueada' AND protected = TRUE AND final_c = FALSE AND final_i = FALSE) OR
    (state = 'Entrenar' AND protected = TRUE AND final_c = TRUE AND final_i = FALSE) OR
    (state = 'Final' AND protected = TRUE AND final_c = TRUE AND final_i = TRUE)
);

SELECT 'Paso 5: CHECK constraint recreado con Entrenar' AS status;

-- ============================================================================
-- 6. Actualizar version_states también (por consistencia)
-- ============================================================================
UPDATE version_states SET state = 'Entrenar' WHERE state = 'Protegida';

ALTER TABLE version_states
MODIFY COLUMN state ENUM('Abierta', 'Bloqueada', 'Entrenar', 'Final')
NOT NULL DEFAULT 'Abierta';

SELECT 'Paso 6: version_states actualizada' AS status;

-- ============================================================================
-- 7. Verificación
-- ============================================================================
SELECT 'ENUM estado_version:' AS tipo, COLUMN_TYPE AS valor
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'myllm_projects_db'
  AND TABLE_NAME = 'estado_version'
  AND COLUMN_NAME = 'state';

SELECT 'CHECK constraint:' AS tipo, CHECK_CLAUSE AS valor
FROM information_schema.CHECK_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'myllm_projects_db'
  AND TABLE_NAME = 'estado_version';

SELECT '017_fix_estado_enum_entrenar: COMPLETADA' AS resultado;

-- ============================================================================
-- Migración: 010_fix_invalid_project_roles.sql
-- Descripción: Limpia roles inválidos en proyectos_roles y añade FK
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-09
-- ============================================================================
--
-- PROBLEMA: Existen registros en proyectos_roles con id_rol que NO existe
-- en proyectos_roles_base (por ejemplo id_rol=1 o id_rol=2). Estos son datos
-- legacy que se crearon antes del catálogo de roles base (migración 005).
--
-- Los roles válidos en proyectos_roles_base son:
--   0 = Sin asignar (usuario no ve el proyecto)
--   3 = Editor
--   4 = Lector
--   5 = Auditor
--
-- ACCIÓN: Eliminar registros con roles inválidos y añadir FK para prevenir
-- futuros registros con roles no existentes en el catálogo.
-- ============================================================================

USE myllm_projects_db;

-- -----------------------------------------------------------------------------
-- 1. Diagnóstico: Mostrar registros con roles inválidos ANTES de limpiar
-- -----------------------------------------------------------------------------
SELECT '=== DIAGNÓSTICO: Registros con roles inválidos ===' AS info;

SELECT 
    pr.id,
    pr.id_usuario,
    pr.id_proyecto,
    p.nombre AS proyecto,
    pr.id_organizacion,
    pr.id_rol,
    pr.active,
    pr.created_at
FROM proyectos_roles pr
LEFT JOIN proyectos p ON pr.id_proyecto = p.id
WHERE pr.id_rol NOT IN (SELECT id FROM proyectos_roles_base);

-- -----------------------------------------------------------------------------
-- 2. Eliminar registros con roles inválidos
-- -----------------------------------------------------------------------------
-- Se eliminan (no se actualizan a rol 0) porque un rol inválido indica que
-- el registro no fue creado correctamente y debe recrearse desde la UI.

DELETE FROM proyectos_roles
WHERE id_rol NOT IN (SELECT id FROM proyectos_roles_base);

SELECT CONCAT('Registros eliminados: ', ROW_COUNT()) AS resultado;

-- -----------------------------------------------------------------------------
-- 3. Añadir Foreign Key a proyectos_roles_base para prevenir roles inválidos
-- -----------------------------------------------------------------------------
-- Primero verificar si ya existe la FK
SET @fk_exists = (
    SELECT COUNT(*)
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = 'myllm_projects_db'
    AND TABLE_NAME = 'proyectos_roles'
    AND CONSTRAINT_NAME = 'fk_proyectos_roles_rol_base'
);

-- Solo crear si no existe
SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE proyectos_roles ADD CONSTRAINT fk_proyectos_roles_rol_base FOREIGN KEY (id_rol) REFERENCES proyectos_roles_base(id) ON UPDATE CASCADE ON DELETE RESTRICT',
    'SELECT "FK fk_proyectos_roles_rol_base ya existe" AS info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- -----------------------------------------------------------------------------
-- 4. Verificación final
-- -----------------------------------------------------------------------------
SELECT '=== VERIFICACIÓN: Registros actuales en proyectos_roles ===' AS info;

SELECT 
    pr.id,
    pr.id_usuario,
    pr.id_proyecto,
    p.nombre AS proyecto,
    pr.id_organizacion,
    pr.id_rol,
    prb.nombre_rol,
    pr.active,
    pr.created_at
FROM proyectos_roles pr
LEFT JOIN proyectos p ON pr.id_proyecto = p.id
LEFT JOIN proyectos_roles_base prb ON pr.id_rol = prb.id
ORDER BY pr.id;

SELECT '=== VERIFICACIÓN: FK constraints en proyectos_roles ===' AS info;

SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'myllm_projects_db'
AND TABLE_NAME = 'proyectos_roles'
AND REFERENCED_TABLE_NAME IS NOT NULL;

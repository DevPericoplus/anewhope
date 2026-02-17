-- ============================================================================
-- Migración: 013_fix_trigger_versiones_state.sql
-- Fecha: 2026-02-16
-- Descripción: Corrige el trigger trg_versiones_after_insert para usar 'Abierta'
--              en lugar de 'stable' en la columna state de estado_version.
--
-- Problema: El trigger estaba intentando insertar 'stable' en un ENUM que solo
--           acepta: 'Abierta', 'Bloqueada', 'Protegida', 'Final'
--           Esto causaba el error: Data truncated for column 'state' at row 1
--
-- Solución: Cambiar el valor de 'stable' a 'Abierta' en el trigger
-- ============================================================================

USE myllm_projects_db;

-- Eliminar el trigger existente
DROP TRIGGER IF EXISTS trg_versiones_after_insert;

-- Recrear el trigger con el valor correcto
DELIMITER $$
CREATE TRIGGER trg_versiones_after_insert
AFTER INSERT ON versiones
FOR EACH ROW
BEGIN
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
        'Abierta',                   -- CORREGIDO: era 'stable', ahora 'Abierta'
        'propuesta_cliente',
        0,
        0,
        0,
        0,
        NOW(),
        NOW()
    );
END$$
DELIMITER ;

-- Verificar que el trigger se creó correctamente
SELECT 'Trigger actualizado correctamente' AS status;
SHOW TRIGGERS LIKE 'versiones';

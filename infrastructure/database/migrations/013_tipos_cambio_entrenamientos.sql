-- ============================================================================
-- Migración: 013_tipos_cambio_entrenamientos.sql
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-12
-- Descripción: Añade tipos de cambio para auditoría de entrenamientos
-- ============================================================================

USE myllm_projects_db;
SET NAMES utf8mb4;

-- ============================================================================
-- Añadir tipos de cambio para entrenamientos
-- ============================================================================

INSERT INTO tipos_cambio (clave, nombre, descripcion_plantilla, aplica_a) VALUES
('inicio_entrenamiento', 'Inicio de entrenamiento', 'Inicio del proceso de entrenamiento', 'entrenamiento'),
('completado_entrenamiento', 'Entrenamiento completado', 'Finalización exitosa del entrenamiento', 'entrenamiento'),
('error_entrenamiento', 'Error en entrenamiento', 'Fallo durante el proceso de entrenamiento', 'entrenamiento'),
('cancelado_entrenamiento', 'Entrenamiento cancelado', 'Cancelación del proceso de entrenamiento por usuario', 'entrenamiento')
ON DUPLICATE KEY UPDATE
    nombre = VALUES(nombre),
    descripcion_plantilla = VALUES(descripcion_plantilla);

SELECT '✅ Tipos de cambio para entrenamientos añadidos' AS resultado;

-- ============================================================================
-- Procedimiento para registrar cambio de entrenamiento
-- ============================================================================

DROP PROCEDURE IF EXISTS sp_registrar_cambio_entrenamiento;

DELIMITER //

CREATE PROCEDURE sp_registrar_cambio_entrenamiento(
    IN p_id_entrenamiento INT,
    IN p_tipo_cambio VARCHAR(100),
    IN p_descripcion VARCHAR(255)
)
BEGIN
    DECLARE v_fecha_actual TIMESTAMP DEFAULT NOW();
    DECLARE v_id_proyecto INT;
    DECLARE v_id_organizacion INT;
    DECLARE v_id_version INT;

    -- Obtener datos del entrenamiento
    SELECT id_proyecto, id_organizacion, id_version
    INTO v_id_proyecto, v_id_organizacion, v_id_version
    FROM entrenamientos
    WHERE id = p_id_entrenamiento;

    -- Si no se encuentra el entrenamiento, salir
    IF v_id_proyecto IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Entrenamiento no encontrado';
    END IF;

    -- Insertar cambio
    INSERT INTO cambios (
        id_version,
        fecha_cambio,
        tipo_cambio,
        descripcion,
        creado_at,
        id_proyecto,
        id_organizacion
    ) VALUES (
        v_id_version,
        v_fecha_actual,
        p_tipo_cambio,
        p_descripcion,
        v_fecha_actual,
        v_id_proyecto,
        v_id_organizacion
    );

    SELECT LAST_INSERT_ID() AS id_cambio, 'Cambio de entrenamiento registrado' AS mensaje;
END //

DELIMITER ;

SELECT '✅ Procedimiento sp_registrar_cambio_entrenamiento creado' AS resultado;

-- ============================================================================
-- Permisos
-- ============================================================================

GRANT EXECUTE ON PROCEDURE myllm_projects_db.sp_registrar_cambio_entrenamiento TO 'myllm_writer'@'localhost';
FLUSH PRIVILEGES;

SELECT '✅ Permisos EXECUTE otorgados a myllm_writer' AS resultado;

-- ============================================================================
-- Verificación
-- ============================================================================

SELECT '========== TIPOS DE CAMBIO PARA ENTRENAMIENTOS ==========' AS info;

SELECT clave, nombre, descripcion_plantilla, aplica_a
FROM tipos_cambio
WHERE aplica_a = 'entrenamiento';

SELECT '✅ Migración 013 completada' AS resultado;

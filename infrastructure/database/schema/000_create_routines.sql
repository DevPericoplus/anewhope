-- ============================================================================
-- 000_create_routines.sql
-- Stored procedures y funciones para myllm_projects_db
-- Fuentes:
--   - fn_get_estado_por_flujo: exportado de PRE
--   - sp_clear_sesion_contexto: exportado de PRE
--   - sp_set_sesion_contexto: migrations/002_flujo_historico_y_trigger.sql
--   - sp_registrar_cambio_entrenamiento: exportado de PRE
--   - sp_registrar_cambio_proyecto: migrations/003_triggers_proyecto_estado_cambios.sql
-- Fecha de captura: 2026-02-24
-- Total: 1 función + 4 stored procedures
-- ============================================================================

USE myllm_projects_db;

-- ============================================================================
-- 1. Función: fn_get_estado_por_flujo
-- Devuelve 1/0 indicando si un campo de estado debería estar activo
-- dado el paso actual del flujo
-- ============================================================================

DROP FUNCTION IF EXISTS fn_get_estado_por_flujo;

DELIMITER //

CREATE DEFINER=`root`@`localhost` FUNCTION fn_get_estado_por_flujo(
    p_id_flujo INT,
    p_campo VARCHAR(50)
) RETURNS TINYINT(1)
    DETERMINISTIC
BEGIN
    DECLARE v_orden INT DEFAULT 0;
    DECLARE v_campo_orden INT DEFAULT 0;

    -- Obtener el orden del flujo actual
    SELECT orden INTO v_orden FROM flujos WHERE id_flujo = p_id_flujo;

    -- Mapear campo a su posición ordinal
    SET v_campo_orden = CASE p_campo
        WHEN 'propuesta_cliente' THEN 1
        WHEN 'revision_interna' THEN 2
        WHEN 'propuesta_mejoras' THEN 3
        WHEN 'aceptacion_cliente' THEN 4
        WHEN 'aceptacion_interna' THEN 5
        WHEN 'entrenamiento_inicial' THEN 6
        WHEN 'evaluacion_entrenamiento' THEN 7
        WHEN 'reentrenamiento' THEN 8
        WHEN 'optimizacion' THEN 9
        WHEN 'aprobacion_calidad' THEN 10
        WHEN 'generacion_llm' THEN 11
        WHEN 'notificacion_descarga' THEN 12
        ELSE 0
    END;

    -- Si el campo tiene un orden válido y es <= al paso actual, devolver 1
    RETURN IF(v_campo_orden > 0 AND v_campo_orden <= v_orden, 1, 0);
END //

DELIMITER ;

-- ============================================================================
-- 2. Procedimiento: sp_set_sesion_contexto
-- Establece el contexto de sesión para que los triggers puedan
-- registrar quién hizo el cambio
-- ============================================================================

DROP PROCEDURE IF EXISTS sp_set_sesion_contexto;

DELIMITER //

CREATE DEFINER=`root`@`localhost` PROCEDURE sp_set_sesion_contexto(
    IN p_id_usuario INT,
    IN p_ip_origen VARCHAR(45),
    IN p_app_origen VARCHAR(50),
    IN p_motivo_cambio VARCHAR(500)
)
BEGIN
    DECLARE v_sesion_id VARCHAR(100);
    SET v_sesion_id = CAST(CONNECTION_ID() AS CHAR);

    INSERT INTO sesion_contexto (id_sesion, id_usuario, ip_origen, app_origen, motivo_cambio)
    VALUES (v_sesion_id, p_id_usuario, p_ip_origen, p_app_origen, p_motivo_cambio)
    ON DUPLICATE KEY UPDATE
        id_usuario = p_id_usuario,
        ip_origen = p_ip_origen,
        app_origen = p_app_origen,
        motivo_cambio = p_motivo_cambio,
        updated_at = NOW();
END //

DELIMITER ;

-- ============================================================================
-- 3. Procedimiento: sp_clear_sesion_contexto
-- Limpia el contexto de sesión después de la operación
-- ============================================================================

DROP PROCEDURE IF EXISTS sp_clear_sesion_contexto;

DELIMITER //

CREATE DEFINER=`root`@`localhost` PROCEDURE sp_clear_sesion_contexto()
BEGIN
    DELETE FROM sesion_contexto
    WHERE id_sesion = CAST(CONNECTION_ID() AS CHAR);
END //

DELIMITER ;

-- ============================================================================
-- 4. Procedimiento: sp_registrar_cambio_entrenamiento
-- Registra un cambio asociado a un entrenamiento en la tabla de cambios
-- ============================================================================

DROP PROCEDURE IF EXISTS sp_registrar_cambio_entrenamiento;

DELIMITER //

CREATE DEFINER=`root`@`localhost` PROCEDURE sp_registrar_cambio_entrenamiento(
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

    -- Validar que existe
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

-- ============================================================================
-- 5. Procedimiento: sp_registrar_cambio_proyecto
-- Registra un cambio manual asociado a un proyecto (desde Backend Core)
-- ============================================================================

DROP PROCEDURE IF EXISTS sp_registrar_cambio_proyecto;

DELIMITER //

CREATE DEFINER=`root`@`localhost` PROCEDURE sp_registrar_cambio_proyecto(
    IN p_id_proyecto INT,
    IN p_id_organizacion INT,
    IN p_tipo_cambio VARCHAR(100),
    IN p_descripcion VARCHAR(255),
    IN p_id_usuario INT
)
BEGIN
    DECLARE v_fecha_actual TIMESTAMP DEFAULT NOW();
    DECLARE v_id_version INT DEFAULT 1;

    -- Obtener última versión del proyecto
    SELECT COALESCE(MAX(id_version), 1) INTO v_id_version
    FROM estado
    WHERE id_proyecto = p_id_proyecto AND id_organizacion = p_id_organizacion;

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
        p_id_proyecto,
        p_id_organizacion
    );

    SELECT LAST_INSERT_ID() AS id_cambio, 'Cambio registrado correctamente' AS mensaje;
END //

DELIMITER ;

-- ============================================================================
-- Otorgar permisos de EXECUTE a los usuarios de aplicación
-- ============================================================================

GRANT EXECUTE ON FUNCTION myllm_projects_db.fn_get_estado_por_flujo TO 'myllm_admin'@'localhost';
GRANT EXECUTE ON PROCEDURE myllm_projects_db.sp_set_sesion_contexto TO 'myllm_admin'@'localhost';
GRANT EXECUTE ON PROCEDURE myllm_projects_db.sp_clear_sesion_contexto TO 'myllm_admin'@'localhost';
GRANT EXECUTE ON PROCEDURE myllm_projects_db.sp_registrar_cambio_entrenamiento TO 'myllm_admin'@'localhost';
GRANT EXECUTE ON PROCEDURE myllm_projects_db.sp_registrar_cambio_proyecto TO 'myllm_admin'@'localhost';
GRANT EXECUTE ON PROCEDURE myllm_projects_db.sp_registrar_cambio_proyecto TO 'myllm_writer'@'localhost';
GRANT EXECUTE ON PROCEDURE myllm_projects_db.sp_registrar_cambio_entrenamiento TO 'myllm_writer'@'localhost';

FLUSH PRIVILEGES;

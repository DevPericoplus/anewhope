-- ============================================================================
-- Migración: Triggers para automatizar estado y cambios de proyectos
-- Base de datos: myllm_projects_db
-- Fecha: 2026-01-31
-- Descripción: 
--   - Trigger INSERT proyectos → crea registro en estado + cambios
--   - Trigger UPDATE proyectos.id_flujo → actualiza estado + registra cambio
--   - Catálogo de tipos de cambio
-- ============================================================================

USE myllm_projects_db;
SET NAMES utf8mb4;

-- ============================================================================
-- 1. Tabla catálogo de tipos de cambio
-- ============================================================================
CREATE TABLE IF NOT EXISTS tipos_cambio (
    id_tipo_cambio INT NOT NULL AUTO_INCREMENT,
    clave VARCHAR(50) NOT NULL UNIQUE COMMENT 'Identificador interno',
    nombre VARCHAR(100) NOT NULL COMMENT 'Nombre visible',
    descripcion_plantilla VARCHAR(255) NOT NULL COMMENT 'Plantilla de descripción',
    aplica_a VARCHAR(50) NOT NULL DEFAULT 'proyecto' COMMENT 'Entidad afectada: proyecto, version, usuario',
    activo TINYINT(1) DEFAULT 1,
    PRIMARY KEY (id_tipo_cambio),
    INDEX idx_tipos_cambio_clave (clave)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Catálogo de tipos de cambio para auditoría';

-- Insertar tipos de cambio
INSERT INTO tipos_cambio (clave, nombre, descripcion_plantilla, aplica_a) VALUES
('alta_proyecto', 'Alta proyecto', 'Creación de un nuevo proyecto', 'proyecto'),
('modificacion_proyecto', 'Modificación proyecto', 'Modificación de datos del proyecto', 'proyecto'),
('borrado_proyecto', 'Borrado de proyecto', 'Eliminación del proyecto', 'proyecto'),
('cambio_flujo', 'Cambio de flujo', 'Cambio de paso en el flujo de trabajo', 'proyecto'),
('asignacion_usuario', 'Asignación usuario', 'Asignación de usuario al proyecto', 'proyecto'),
('quitar_usuario', 'Quitar usuario', 'Eliminación de usuario del proyecto', 'proyecto'),
('bloquear_proyecto', 'Bloquear proyecto', 'Bloqueo del proyecto', 'proyecto'),
('desbloquear_proyecto', 'Desbloquear proyecto', 'Desbloqueo del proyecto', 'proyecto'),
('solicitud_soporte', 'Solicitud soporte proyecto', 'Solicitud de soporte técnico', 'proyecto'),
('respuesta_soporte', 'Respuesta soporte proyecto', 'Respuesta a solicitud de soporte', 'proyecto'),
('alta_version', 'Alta versión', 'Creación de una nueva versión', 'version'),
('modificacion_version', 'Modificación versión', 'Modificación de datos de la versión', 'version'),
('borrado_version', 'Borrado versión', 'Eliminación de la versión', 'version')
ON DUPLICATE KEY UPDATE
    nombre = VALUES(nombre),
    descripcion_plantilla = VALUES(descripcion_plantilla);

SELECT 'Tabla tipos_cambio creada y poblada' AS resultado;

-- ============================================================================
-- 2. Función para obtener campos booleanos del flujo según id_flujo
-- ============================================================================
-- Devuelve qué campos del estado deben estar a TRUE según el orden del flujo

DROP FUNCTION IF EXISTS fn_get_estado_por_flujo;

DELIMITER //

CREATE FUNCTION fn_get_estado_por_flujo(p_id_flujo INT, p_campo VARCHAR(50))
RETURNS TINYINT(1)
DETERMINISTIC
BEGIN
    DECLARE v_orden INT DEFAULT 0;
    DECLARE v_campo_orden INT DEFAULT 0;
    
    -- Obtener orden del flujo actual
    SELECT orden INTO v_orden FROM flujos WHERE id_flujo = p_id_flujo;
    
    -- Mapear campo a su orden
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
    
    -- El campo está a TRUE si su orden es <= al orden del flujo actual
    RETURN IF(v_campo_orden > 0 AND v_campo_orden <= v_orden, 1, 0);
END //

DELIMITER ;

SELECT 'Función fn_get_estado_por_flujo creada' AS resultado;

-- ============================================================================
-- 3. Trigger AFTER INSERT en proyectos
-- ============================================================================
-- Crea automáticamente:
--   - Registro en tabla estado con versión 1
--   - Registro en tabla cambios con tipo "alta_proyecto"

DROP TRIGGER IF EXISTS tr_proyecto_after_insert;

DELIMITER //

CREATE TRIGGER tr_proyecto_after_insert
AFTER INSERT ON proyectos
FOR EACH ROW
BEGIN
    DECLARE v_fecha_actual TIMESTAMP DEFAULT NOW();
    DECLARE v_id_flujo INT DEFAULT COALESCE(NEW.id_flujo, 1);
    
    -- 1. Crear registro en tabla estado para versión 1
    INSERT INTO estado (
        id_organizacion,
        id_proyecto,
        id_version,
        creado_at,
        actualizado_at,
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
        NEW.id,
        1,  -- Primera versión
        v_fecha_actual,
        NULL,  -- actualizado_at NULL en alta
        fn_get_estado_por_flujo(v_id_flujo, 'propuesta_cliente'),
        fn_get_estado_por_flujo(v_id_flujo, 'revision_interna'),
        fn_get_estado_por_flujo(v_id_flujo, 'propuesta_mejoras'),
        fn_get_estado_por_flujo(v_id_flujo, 'aceptacion_cliente'),
        fn_get_estado_por_flujo(v_id_flujo, 'aceptacion_interna'),
        fn_get_estado_por_flujo(v_id_flujo, 'entrenamiento_inicial'),
        fn_get_estado_por_flujo(v_id_flujo, 'evaluacion_entrenamiento'),
        fn_get_estado_por_flujo(v_id_flujo, 'reentrenamiento'),
        fn_get_estado_por_flujo(v_id_flujo, 'optimizacion'),
        fn_get_estado_por_flujo(v_id_flujo, 'aprobacion_calidad'),
        fn_get_estado_por_flujo(v_id_flujo, 'generacion_llm'),
        fn_get_estado_por_flujo(v_id_flujo, 'notificacion_descarga')
    );
    
    -- 2. Crear registro en tabla cambios
    INSERT INTO cambios (
        id_version,
        fecha_cambio,
        tipo_cambio,
        descripcion,
        creado_at,
        id_proyecto,
        id_organizacion
    ) VALUES (
        1,  -- Primera versión
        v_fecha_actual,
        'Alta proyecto',
        CONCAT('Creación de un nuevo proyecto: ', NEW.nombre),
        v_fecha_actual,
        NEW.id,
        NEW.id_organizacion
    );
    
END //

DELIMITER ;

SELECT 'Trigger tr_proyecto_after_insert creado' AS resultado;

-- ============================================================================
-- 4. Trigger AFTER UPDATE en proyectos (cambio de id_flujo)
-- ============================================================================
-- Cuando cambia id_flujo:
--   - Actualiza todos los registros de estado del proyecto
--   - Registra cambio en tabla cambios

DROP TRIGGER IF EXISTS tr_proyecto_flujo_update;

DELIMITER //

CREATE TRIGGER tr_proyecto_flujo_update
AFTER UPDATE ON proyectos
FOR EACH ROW
BEGIN
    DECLARE v_fecha_actual TIMESTAMP DEFAULT NOW();
    DECLARE v_tipo_cambio VARCHAR(100);
    DECLARE v_descripcion VARCHAR(255);
    DECLARE v_flujo_nombre VARCHAR(100);
    
    -- Solo si cambió el id_flujo
    IF (OLD.id_flujo IS NULL AND NEW.id_flujo IS NOT NULL) 
       OR (OLD.id_flujo IS NOT NULL AND NEW.id_flujo IS NULL)
       OR (OLD.id_flujo <> NEW.id_flujo) THEN
        
        -- Obtener nombre del nuevo flujo
        SELECT nombre INTO v_flujo_nombre FROM flujos WHERE id_flujo = NEW.id_flujo;
        
        SET v_tipo_cambio = 'Cambio de flujo';
        SET v_descripcion = CONCAT('Cambio a paso: ', COALESCE(v_flujo_nombre, 'Desconocido'));
        
        -- 1. Actualizar todos los registros de estado del proyecto
        UPDATE estado SET
            actualizado_at = v_fecha_actual,
            propuesta_cliente = fn_get_estado_por_flujo(NEW.id_flujo, 'propuesta_cliente'),
            revision_interna = fn_get_estado_por_flujo(NEW.id_flujo, 'revision_interna'),
            propuesta_mejoras = fn_get_estado_por_flujo(NEW.id_flujo, 'propuesta_mejoras'),
            aceptacion_cliente = fn_get_estado_por_flujo(NEW.id_flujo, 'aceptacion_cliente'),
            aceptacion_interna = fn_get_estado_por_flujo(NEW.id_flujo, 'aceptacion_interna'),
            entrenamiento_inicial = fn_get_estado_por_flujo(NEW.id_flujo, 'entrenamiento_inicial'),
            evaluacion_entrenamiento = fn_get_estado_por_flujo(NEW.id_flujo, 'evaluacion_entrenamiento'),
            reentrenamiento = fn_get_estado_por_flujo(NEW.id_flujo, 'reentrenamiento'),
            optimizacion = fn_get_estado_por_flujo(NEW.id_flujo, 'optimizacion'),
            aprobacion_calidad = fn_get_estado_por_flujo(NEW.id_flujo, 'aprobacion_calidad'),
            generacion_llm = fn_get_estado_por_flujo(NEW.id_flujo, 'generacion_llm'),
            notificacion_descarga = fn_get_estado_por_flujo(NEW.id_flujo, 'notificacion_descarga')
        WHERE id_proyecto = NEW.id AND id_organizacion = NEW.id_organizacion;
        
        -- 2. Registrar cambio (para todas las versiones, usamos la última)
        INSERT INTO cambios (
            id_version,
            fecha_cambio,
            tipo_cambio,
            descripcion,
            creado_at,
            id_proyecto,
            id_organizacion
        ) 
        SELECT 
            COALESCE(MAX(id_version), 1),
            v_fecha_actual,
            v_tipo_cambio,
            v_descripcion,
            v_fecha_actual,
            NEW.id,
            NEW.id_organizacion
        FROM estado 
        WHERE id_proyecto = NEW.id AND id_organizacion = NEW.id_organizacion;
        
    END IF;
    
    -- Detectar otros tipos de cambios
    
    -- Bloqueo/Desbloqueo (si existe campo bloqueado)
    IF OLD.bloqueado IS NOT NULL AND NEW.bloqueado IS NOT NULL AND OLD.bloqueado <> NEW.bloqueado THEN
        IF NEW.bloqueado = 1 THEN
            SET v_tipo_cambio = 'Bloquear proyecto';
            SET v_descripcion = 'Proyecto bloqueado';
        ELSE
            SET v_tipo_cambio = 'Desbloquear proyecto';
            SET v_descripcion = 'Proyecto desbloqueado';
        END IF;
        
        INSERT INTO cambios (id_version, fecha_cambio, tipo_cambio, descripcion, creado_at, id_proyecto, id_organizacion)
        SELECT COALESCE(MAX(id_version), 1), v_fecha_actual, v_tipo_cambio, v_descripcion, v_fecha_actual, NEW.id, NEW.id_organizacion
        FROM estado WHERE id_proyecto = NEW.id;
    END IF;
    
    -- Cambio de nombre o descripción
    IF (OLD.nombre <> NEW.nombre) OR (COALESCE(OLD.descripcion, '') <> COALESCE(NEW.descripcion, '')) THEN
        SET v_tipo_cambio = 'Modificación proyecto';
        SET v_descripcion = 'Modificación de datos del proyecto';
        
        INSERT INTO cambios (id_version, fecha_cambio, tipo_cambio, descripcion, creado_at, id_proyecto, id_organizacion)
        SELECT COALESCE(MAX(id_version), 1), v_fecha_actual, v_tipo_cambio, v_descripcion, v_fecha_actual, NEW.id, NEW.id_organizacion
        FROM estado WHERE id_proyecto = NEW.id;
    END IF;
    
END //

DELIMITER ;

SELECT 'Trigger tr_proyecto_flujo_update creado' AS resultado;

-- ============================================================================
-- 5. Trigger BEFORE DELETE en proyectos
-- ============================================================================
-- Registra el borrado antes de eliminar

DROP TRIGGER IF EXISTS tr_proyecto_before_delete;

DELIMITER //

CREATE TRIGGER tr_proyecto_before_delete
BEFORE DELETE ON proyectos
FOR EACH ROW
BEGIN
    DECLARE v_fecha_actual TIMESTAMP DEFAULT NOW();
    
    -- Registrar el borrado
    INSERT INTO cambios (
        id_version,
        fecha_cambio,
        tipo_cambio,
        descripcion,
        creado_at,
        id_proyecto,
        id_organizacion
    ) VALUES (
        0,  -- Sin versión (proyecto eliminado)
        v_fecha_actual,
        'Borrado de proyecto',
        CONCAT('Eliminación del proyecto: ', OLD.nombre),
        v_fecha_actual,
        OLD.id,
        OLD.id_organizacion
    );
    
END //

DELIMITER ;

SELECT 'Trigger tr_proyecto_before_delete creado' AS resultado;

-- ============================================================================
-- 6. Procedimiento para registrar cambios manuales (desde Backend Core)
-- ============================================================================
-- Usado para cambios que no se detectan automáticamente por triggers

DROP PROCEDURE IF EXISTS sp_registrar_cambio_proyecto;

DELIMITER //

CREATE PROCEDURE sp_registrar_cambio_proyecto(
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

SELECT 'Procedimiento sp_registrar_cambio_proyecto creado' AS resultado;

-- ============================================================================
-- 7. Vista de proyectos con estado actual
-- ============================================================================

CREATE OR REPLACE VIEW view_proyectos_completo AS
SELECT 
    p.id AS proyecto_id,
    p.nombre AS proyecto_nombre,
    p.descripcion AS proyecto_descripcion,
    p.id_organizacion,
    p.active AS proyecto_activo,
    p.id_flujo,
    f.nombre AS flujo_nombre,
    f.emoji AS flujo_emoji,
    f.orden AS flujo_orden,
    e.id_version AS version_actual,
    e.creado_at AS proyecto_creado_at,
    e.actualizado_at AS proyecto_actualizado_at,
    -- Estados del flujo
    e.propuesta_cliente,
    e.revision_interna,
    e.propuesta_mejoras,
    e.aceptacion_cliente,
    e.aceptacion_interna,
    e.entrenamiento_inicial,
    e.evaluacion_entrenamiento,
    e.reentrenamiento,
    e.optimizacion,
    e.aprobacion_calidad,
    e.generacion_llm,
    e.notificacion_descarga
FROM proyectos p
LEFT JOIN flujos f ON p.id_flujo = f.id_flujo
LEFT JOIN estado e ON p.id = e.id_proyecto 
    AND p.id_organizacion = e.id_organizacion 
    AND e.id_version = (
        SELECT MAX(id_version) 
        FROM estado 
        WHERE id_proyecto = p.id AND id_organizacion = p.id_organizacion
    );

SELECT 'Vista view_proyectos_completo creada' AS resultado;

-- ============================================================================
-- 8. Vista de cambios recientes
-- ============================================================================

CREATE OR REPLACE VIEW view_cambios_recientes AS
SELECT 
    c.id AS cambio_id,
    c.id_proyecto,
    p.nombre AS proyecto_nombre,
    c.id_organizacion,
    c.id_version,
    c.fecha_cambio,
    c.tipo_cambio,
    c.descripcion,
    c.creado_at
FROM cambios c
LEFT JOIN proyectos p ON c.id_proyecto = p.id
ORDER BY c.fecha_cambio DESC;

SELECT 'Vista view_cambios_recientes creada' AS resultado;

-- ============================================================================
-- Verificación final
-- ============================================================================
SELECT '========== RESUMEN DE OBJETOS CREADOS ==========' AS info;

SELECT 'Triggers en proyectos:' AS tipo, GROUP_CONCAT(trigger_name) AS objetos
FROM information_schema.triggers 
WHERE trigger_schema = 'myllm_projects_db'
AND event_object_table = 'proyectos';

SELECT 'Funciones:' AS tipo, GROUP_CONCAT(routine_name) AS objetos
FROM information_schema.routines 
WHERE routine_schema = 'myllm_projects_db'
AND routine_type = 'FUNCTION';

SELECT 'Procedimientos:' AS tipo, GROUP_CONCAT(routine_name) AS objetos
FROM information_schema.routines 
WHERE routine_schema = 'myllm_projects_db'
AND routine_type = 'PROCEDURE';

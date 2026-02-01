-- ============================================================================
-- Migración: Histórico de cambios de flujo y triggers
-- Base de datos: myllm_projects_db
-- Fecha: 2026-01-31
-- Descripción: Crea tabla de auditoría para cambios de flujo en proyectos
--              y triggers para registro automático.
-- ============================================================================

USE myllm_projects_db;
SET NAMES utf8mb4;

-- ============================================================================
-- 1. Tabla de histórico de cambios de flujo
-- ============================================================================
-- Registra cada transición de un proyecto entre pasos del flujo.
-- Permite auditoría, análisis de tiempos y trazabilidad completa.

CREATE TABLE IF NOT EXISTS proyecto_flujo_historico (
    id BIGINT NOT NULL AUTO_INCREMENT,
    
    -- Referencia al proyecto
    id_proyecto INT NOT NULL COMMENT 'FK a proyectos.id',
    id_organizacion INT NOT NULL COMMENT 'FK a organizaciones (desnormalizado para consultas rápidas)',
    
    -- Transición de flujo
    id_flujo_anterior INT NULL COMMENT 'FK a flujos.id_flujo (NULL si es el primer estado)',
    id_flujo_nuevo INT NOT NULL COMMENT 'FK a flujos.id_flujo',
    
    -- Auditoría
    fecha_cambio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Momento del cambio',
    id_usuario_cambio INT NULL COMMENT 'FK a users.user_id (quien realizó el cambio)',
    motivo_cambio VARCHAR(500) NULL COMMENT 'Motivo o comentario del cambio (opcional)',
    
    -- Métricas de tiempo
    tiempo_en_paso_anterior_segundos BIGINT NULL COMMENT 'Segundos que estuvo en el paso anterior',
    
    -- Metadata
    ip_origen VARCHAR(45) NULL COMMENT 'IP desde donde se realizó el cambio',
    app_origen VARCHAR(50) NULL COMMENT 'Aplicación origen (frontend, backoffice, api)',
    
    PRIMARY KEY (id),
    INDEX idx_historico_proyecto (id_proyecto),
    INDEX idx_historico_organizacion (id_organizacion),
    INDEX idx_historico_fecha (fecha_cambio),
    INDEX idx_historico_flujo_nuevo (id_flujo_nuevo),
    INDEX idx_historico_usuario (id_usuario_cambio),
    
    -- Foreign Keys
    CONSTRAINT fk_historico_proyecto FOREIGN KEY (id_proyecto) 
        REFERENCES proyectos(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_historico_flujo_anterior FOREIGN KEY (id_flujo_anterior) 
        REFERENCES flujos(id_flujo) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_historico_flujo_nuevo FOREIGN KEY (id_flujo_nuevo) 
        REFERENCES flujos(id_flujo) ON DELETE RESTRICT ON UPDATE CASCADE
        
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Auditoría de cambios de flujo en proyectos';

SELECT 'Tabla proyecto_flujo_historico creada' AS resultado;

-- ============================================================================
-- 2. Tabla de variables de sesión para triggers
-- ============================================================================
-- MariaDB no tiene forma nativa de pasar contexto a triggers.
-- Usamos una tabla temporal o variables de sesión.
-- Esta tabla almacena el contexto del usuario actual para el trigger.

CREATE TABLE IF NOT EXISTS sesion_contexto (
    id_sesion VARCHAR(100) NOT NULL COMMENT 'CONNECTION_ID() o session_token',
    id_usuario INT NULL COMMENT 'Usuario que está ejecutando la operación',
    ip_origen VARCHAR(45) NULL COMMENT 'IP del cliente',
    app_origen VARCHAR(50) NULL COMMENT 'frontend, backoffice, api, etc.',
    motivo_cambio VARCHAR(500) NULL COMMENT 'Motivo del cambio (si aplica)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_sesion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Contexto de sesión para triggers (temporal por conexión)';

SELECT 'Tabla sesion_contexto creada' AS resultado;

-- ============================================================================
-- 3. Procedimiento para establecer contexto de sesión
-- ============================================================================
-- Debe llamarse desde la aplicación antes de hacer cambios en proyectos.

DROP PROCEDURE IF EXISTS sp_set_sesion_contexto;

DELIMITER //

CREATE PROCEDURE sp_set_sesion_contexto(
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

SELECT 'Procedimiento sp_set_sesion_contexto creado' AS resultado;

-- ============================================================================
-- 4. Procedimiento para limpiar contexto de sesión
-- ============================================================================

DROP PROCEDURE IF EXISTS sp_clear_sesion_contexto;

DELIMITER //

CREATE PROCEDURE sp_clear_sesion_contexto()
BEGIN
    DELETE FROM sesion_contexto 
    WHERE id_sesion = CAST(CONNECTION_ID() AS CHAR);
END //

DELIMITER ;

SELECT 'Procedimiento sp_clear_sesion_contexto creado' AS resultado;

-- ============================================================================
-- 5. Trigger AFTER UPDATE para registrar cambios de flujo
-- ============================================================================

DROP TRIGGER IF EXISTS tr_proyecto_flujo_cambio;

DELIMITER //

CREATE TRIGGER tr_proyecto_flujo_cambio
AFTER UPDATE ON proyectos
FOR EACH ROW
BEGIN
    DECLARE v_id_usuario INT DEFAULT NULL;
    DECLARE v_ip_origen VARCHAR(45) DEFAULT NULL;
    DECLARE v_app_origen VARCHAR(50) DEFAULT NULL;
    DECLARE v_motivo VARCHAR(500) DEFAULT NULL;
    DECLARE v_tiempo_anterior BIGINT DEFAULT NULL;
    DECLARE v_fecha_ultimo_cambio TIMESTAMP DEFAULT NULL;
    DECLARE v_sesion_id VARCHAR(100);
    
    -- Solo registrar si cambió el id_flujo
    IF (OLD.id_flujo IS NULL AND NEW.id_flujo IS NOT NULL) 
       OR (OLD.id_flujo IS NOT NULL AND NEW.id_flujo IS NULL)
       OR (OLD.id_flujo <> NEW.id_flujo) THEN
        
        -- Obtener contexto de sesión
        SET v_sesion_id = CAST(CONNECTION_ID() AS CHAR);
        
        SELECT id_usuario, ip_origen, app_origen, motivo_cambio
        INTO v_id_usuario, v_ip_origen, v_app_origen, v_motivo
        FROM sesion_contexto
        WHERE id_sesion = v_sesion_id
        LIMIT 1;
        
        -- Calcular tiempo en el paso anterior
        SELECT fecha_cambio INTO v_fecha_ultimo_cambio
        FROM proyecto_flujo_historico
        WHERE id_proyecto = OLD.id
        ORDER BY fecha_cambio DESC
        LIMIT 1;
        
        IF v_fecha_ultimo_cambio IS NOT NULL THEN
            SET v_tiempo_anterior = TIMESTAMPDIFF(SECOND, v_fecha_ultimo_cambio, NOW());
        END IF;
        
        -- Insertar registro en el histórico
        INSERT INTO proyecto_flujo_historico (
            id_proyecto,
            id_organizacion,
            id_flujo_anterior,
            id_flujo_nuevo,
            fecha_cambio,
            id_usuario_cambio,
            motivo_cambio,
            tiempo_en_paso_anterior_segundos,
            ip_origen,
            app_origen
        ) VALUES (
            NEW.id,
            NEW.id_organizacion,
            OLD.id_flujo,
            NEW.id_flujo,
            NOW(),
            v_id_usuario,
            v_motivo,
            v_tiempo_anterior,
            v_ip_origen,
            v_app_origen
        );
        
    END IF;
END //

DELIMITER ;

SELECT 'Trigger tr_proyecto_flujo_cambio creado' AS resultado;

-- ============================================================================
-- 6. Trigger AFTER INSERT para registrar estado inicial
-- ============================================================================

DROP TRIGGER IF EXISTS tr_proyecto_flujo_inicial;

DELIMITER //

CREATE TRIGGER tr_proyecto_flujo_inicial
AFTER INSERT ON proyectos
FOR EACH ROW
BEGIN
    DECLARE v_id_usuario INT DEFAULT NULL;
    DECLARE v_ip_origen VARCHAR(45) DEFAULT NULL;
    DECLARE v_app_origen VARCHAR(50) DEFAULT NULL;
    DECLARE v_sesion_id VARCHAR(100);
    
    -- Solo si tiene un id_flujo asignado
    IF NEW.id_flujo IS NOT NULL THEN
        
        -- Obtener contexto de sesión
        SET v_sesion_id = CAST(CONNECTION_ID() AS CHAR);
        
        SELECT id_usuario, ip_origen, app_origen
        INTO v_id_usuario, v_ip_origen, v_app_origen
        FROM sesion_contexto
        WHERE id_sesion = v_sesion_id
        LIMIT 1;
        
        -- Insertar registro inicial en el histórico
        INSERT INTO proyecto_flujo_historico (
            id_proyecto,
            id_organizacion,
            id_flujo_anterior,
            id_flujo_nuevo,
            fecha_cambio,
            id_usuario_cambio,
            motivo_cambio,
            tiempo_en_paso_anterior_segundos,
            ip_origen,
            app_origen
        ) VALUES (
            NEW.id,
            NEW.id_organizacion,
            NULL,  -- Sin estado anterior (es nuevo)
            NEW.id_flujo,
            NOW(),
            v_id_usuario,
            'Creación del proyecto',
            NULL,
            v_ip_origen,
            v_app_origen
        );
        
    END IF;
END //

DELIMITER ;

SELECT 'Trigger tr_proyecto_flujo_inicial creado' AS resultado;

-- ============================================================================
-- 7. Vista enriquecida del histórico de flujos
-- ============================================================================

CREATE OR REPLACE VIEW view_proyecto_flujo_historico AS
SELECT 
    h.id AS historico_id,
    h.id_proyecto,
    p.nombre AS proyecto_nombre,
    h.id_organizacion,
    o.organization_name AS organizacion_nombre,
    
    -- Flujo anterior
    h.id_flujo_anterior,
    fa.clave AS flujo_anterior_clave,
    fa.nombre AS flujo_anterior_nombre,
    fa.emoji AS flujo_anterior_emoji,
    fa.orden AS flujo_anterior_orden,
    
    -- Flujo nuevo
    h.id_flujo_nuevo,
    fn.clave AS flujo_nuevo_clave,
    fn.nombre AS flujo_nuevo_nombre,
    fn.emoji AS flujo_nuevo_emoji,
    fn.orden AS flujo_nuevo_orden,
    
    -- Dirección del cambio
    CASE 
        WHEN h.id_flujo_anterior IS NULL THEN 'INICIO'
        WHEN fn.orden > fa.orden THEN 'AVANCE'
        WHEN fn.orden < fa.orden THEN 'RETROCESO'
        ELSE 'MISMO_NIVEL'
    END AS direccion_cambio,
    
    -- Auditoría
    h.fecha_cambio,
    h.id_usuario_cambio,
    h.motivo_cambio,
    h.ip_origen,
    h.app_origen,
    
    -- Métricas
    h.tiempo_en_paso_anterior_segundos,
    CASE 
        WHEN h.tiempo_en_paso_anterior_segundos IS NULL THEN NULL
        WHEN h.tiempo_en_paso_anterior_segundos < 60 THEN CONCAT(h.tiempo_en_paso_anterior_segundos, ' seg')
        WHEN h.tiempo_en_paso_anterior_segundos < 3600 THEN CONCAT(ROUND(h.tiempo_en_paso_anterior_segundos / 60, 1), ' min')
        WHEN h.tiempo_en_paso_anterior_segundos < 86400 THEN CONCAT(ROUND(h.tiempo_en_paso_anterior_segundos / 3600, 1), ' hrs')
        ELSE CONCAT(ROUND(h.tiempo_en_paso_anterior_segundos / 86400, 1), ' días')
    END AS tiempo_en_paso_anterior_formato

FROM proyecto_flujo_historico h
LEFT JOIN proyectos p ON h.id_proyecto = p.id
LEFT JOIN organizaciones o ON h.id_organizacion = o.organization_id
LEFT JOIN flujos fa ON h.id_flujo_anterior = fa.id_flujo
LEFT JOIN flujos fn ON h.id_flujo_nuevo = fn.id_flujo
ORDER BY h.fecha_cambio DESC;

SELECT 'Vista view_proyecto_flujo_historico creada' AS resultado;

-- ============================================================================
-- 8. Vista de métricas por flujo (tiempo promedio en cada paso)
-- ============================================================================

CREATE OR REPLACE VIEW view_flujo_metricas AS
SELECT 
    f.id_flujo,
    f.clave,
    f.nombre,
    f.emoji,
    f.orden,
    COUNT(h.id) AS total_transiciones,
    AVG(h.tiempo_en_paso_anterior_segundos) AS tiempo_promedio_segundos,
    MIN(h.tiempo_en_paso_anterior_segundos) AS tiempo_minimo_segundos,
    MAX(h.tiempo_en_paso_anterior_segundos) AS tiempo_maximo_segundos
FROM flujos f
LEFT JOIN proyecto_flujo_historico h ON f.id_flujo = h.id_flujo_anterior
GROUP BY f.id_flujo, f.clave, f.nombre, f.emoji, f.orden
ORDER BY f.orden;

SELECT 'Vista view_flujo_metricas creada' AS resultado;

-- ============================================================================
-- 9. Procedimiento para avanzar proyecto al siguiente paso
-- ============================================================================

DROP PROCEDURE IF EXISTS sp_avanzar_proyecto_flujo;

DELIMITER //

CREATE PROCEDURE sp_avanzar_proyecto_flujo(
    IN p_id_proyecto INT,
    IN p_id_usuario INT,
    IN p_motivo VARCHAR(500),
    IN p_ip_origen VARCHAR(45),
    IN p_app_origen VARCHAR(50)
)
BEGIN
    DECLARE v_id_flujo_actual INT;
    DECLARE v_orden_actual INT;
    DECLARE v_id_flujo_siguiente INT;
    DECLARE v_nombre_siguiente VARCHAR(100);
    
    -- Obtener flujo actual del proyecto
    SELECT p.id_flujo, f.orden 
    INTO v_id_flujo_actual, v_orden_actual
    FROM proyectos p
    LEFT JOIN flujos f ON p.id_flujo = f.id_flujo
    WHERE p.id = p_id_proyecto;
    
    -- Obtener siguiente paso del flujo
    SELECT id_flujo, nombre 
    INTO v_id_flujo_siguiente, v_nombre_siguiente
    FROM flujos
    WHERE orden = v_orden_actual + 1
    AND activo = 1
    LIMIT 1;
    
    IF v_id_flujo_siguiente IS NULL THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'El proyecto ya está en el último paso del flujo';
    END IF;
    
    -- Establecer contexto de sesión
    CALL sp_set_sesion_contexto(p_id_usuario, p_ip_origen, p_app_origen, p_motivo);
    
    -- Actualizar el proyecto (el trigger se encarga del histórico)
    UPDATE proyectos 
    SET id_flujo = v_id_flujo_siguiente
    WHERE id = p_id_proyecto;
    
    -- Limpiar contexto
    CALL sp_clear_sesion_contexto();
    
    -- Retornar información del nuevo estado
    SELECT 
        p_id_proyecto AS id_proyecto,
        v_id_flujo_siguiente AS id_flujo_nuevo,
        v_nombre_siguiente AS nombre_flujo_nuevo,
        'Proyecto avanzado correctamente' AS mensaje;
        
END //

DELIMITER ;

SELECT 'Procedimiento sp_avanzar_proyecto_flujo creado' AS resultado;

-- ============================================================================
-- 10. Limpieza de contextos de sesión antiguos (job de mantenimiento)
-- ============================================================================

DROP EVENT IF EXISTS ev_limpiar_sesion_contexto;

-- Nota: Requiere que el event_scheduler esté activo
-- SET GLOBAL event_scheduler = ON;

DELIMITER //

CREATE EVENT IF NOT EXISTS ev_limpiar_sesion_contexto
ON SCHEDULE EVERY 1 HOUR
DO
BEGIN
    -- Eliminar contextos más antiguos de 1 hora
    DELETE FROM sesion_contexto 
    WHERE updated_at < DATE_SUB(NOW(), INTERVAL 1 HOUR);
END //

DELIMITER ;

SELECT 'Evento ev_limpiar_sesion_contexto creado (requiere event_scheduler activo)' AS resultado;

-- ============================================================================
-- Verificación final
-- ============================================================================
SELECT '========== RESUMEN DE OBJETOS CREADOS ==========' AS info;
SELECT 'Tablas:' AS tipo, GROUP_CONCAT(table_name) AS objetos
FROM information_schema.tables 
WHERE table_schema = 'myllm_projects_db' 
AND table_name IN ('proyecto_flujo_historico', 'sesion_contexto');

SELECT 'Triggers:' AS tipo, GROUP_CONCAT(trigger_name) AS objetos
FROM information_schema.triggers 
WHERE trigger_schema = 'myllm_projects_db'
AND trigger_name LIKE 'tr_proyecto_flujo%';

SELECT 'Vistas:' AS tipo, GROUP_CONCAT(table_name) AS objetos
FROM information_schema.views 
WHERE table_schema = 'myllm_projects_db'
AND table_name LIKE 'view_%flujo%';

SELECT 'Procedimientos:' AS tipo, GROUP_CONCAT(routine_name) AS objetos
FROM information_schema.routines 
WHERE routine_schema = 'myllm_projects_db'
AND routine_type = 'PROCEDURE'
AND routine_name LIKE 'sp_%';

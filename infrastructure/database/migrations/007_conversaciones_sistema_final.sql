-- ============================================================================
-- 007_conversaciones_sistema_final.sql
-- Sistema de conversaciones entre clientes (frontend) e internos (backoffice)
--
-- NOTA: Las FKs a users y organizations se omiten porque esas tablas están
-- en myllm_core_db (base de datos diferente). La validación de integridad
-- referencial se realiza en la capa de aplicación.
-- ============================================================================

USE myllm_projects_db;

-- ----------------------------------------------------------------------------
-- Tabla: asignaciones_organizaciones_internas
-- Gestiona qué usuarios internos están asignados a qué organizaciones
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS asignaciones_organizaciones_internas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario_interno INT NOT NULL COMMENT 'Usuario interno (ref: myllm_core_db.users)',
    id_organizacion INT NOT NULL COMMENT 'Organización cliente (ref: myllm_core_db.organizations)',
    id_rol INT NOT NULL COMMENT 'Rol del usuario interno para esta organización',
    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE COMMENT 'Si la asignación está activa',
    asignado_por INT NOT NULL COMMENT 'Super admin que hizo la asignación (ref: myllm_core_db.users)',
    notas TEXT COMMENT 'Notas sobre la asignación',
    fecha_desactivacion TIMESTAMP NULL COMMENT 'Cuándo se desactivó',
    desactivado_por INT NULL COMMENT 'Quién desactivó (ref: myllm_core_db.users)',

    -- FK solo a tabla local
    FOREIGN KEY (id_rol) REFERENCES proyectos_roles_base(id) ON DELETE RESTRICT,

    UNIQUE KEY unique_asignacion (id_usuario_interno, id_organizacion, id_rol),
    INDEX idx_usuario_interno (id_usuario_interno, activo),
    INDEX idx_organizacion (id_organizacion, activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Asignación de usuarios internos a organizaciones cliente';

-- ----------------------------------------------------------------------------
-- Tabla: conversaciones
-- Registro de cada conversación iniciada desde el frontend
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversaciones (
    id_conversacion INT AUTO_INCREMENT PRIMARY KEY,
    id_organizacion INT NOT NULL COMMENT 'Organización (ref: myllm_core_db.organizations)',
    id_usuario_cliente INT NOT NULL COMMENT 'Usuario cliente (ref: myllm_core_db.users)',
    id_ticket_principal INT NULL COMMENT 'Ticket principal relacionado (opcional)',
    asunto VARCHAR(255) COMMENT 'Título o tema de la conversación',
    estado ENUM('abierta', 'en_curso', 'resuelta', 'cerrada') DEFAULT 'abierta',
    prioridad ENUM('baja', 'media', 'alta', 'urgente') DEFAULT 'media',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ultimo_mensaje_texto TEXT COMMENT 'Cache del último mensaje',
    ultimo_mensaje_de ENUM('cliente', 'interno') COMMENT 'Quién envió el último mensaje',
    ultimo_mensaje_fecha TIMESTAMP NULL COMMENT 'Fecha del último mensaje',
    mensajes_sin_leer_cliente INT DEFAULT 0 COMMENT 'Contador de mensajes sin leer por cliente',
    mensajes_sin_leer_interno INT DEFAULT 0 COMMENT 'Contador de mensajes sin leer por internos',
    total_mensajes INT DEFAULT 0 COMMENT 'Total de mensajes en la conversación',
    cerrada_por INT NULL COMMENT 'Usuario que cerró (ref: myllm_core_db.users)',
    fecha_cierre TIMESTAMP NULL COMMENT 'Fecha de cierre',

    -- FK solo a tablas locales
    FOREIGN KEY (id_ticket_principal) REFERENCES tickets(id) ON DELETE SET NULL,

    INDEX idx_org_estado (id_organizacion, estado),
    INDEX idx_fecha_actualizacion (fecha_ultima_actualizacion DESC),
    INDEX idx_usuario_cliente (id_usuario_cliente, estado),
    INDEX idx_ticket (id_ticket_principal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Conversaciones entre clientes e internos';

-- ----------------------------------------------------------------------------
-- Tabla: participantes_conversacion
-- Tracking de quién participa en cada conversación
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS participantes_conversacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_conversacion INT NOT NULL,
    id_usuario INT NOT NULL COMMENT 'Usuario participante (ref: myllm_core_db.users)',
    tipo_participante ENUM('cliente', 'interno') NOT NULL,
    fecha_union TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Cuándo se unió a la conversación',
    activo BOOLEAN DEFAULT TRUE,
    ultimo_acceso TIMESTAMP NULL COMMENT 'Última vez que accedió a la conversación',
    notificaciones_activadas BOOLEAN DEFAULT TRUE COMMENT 'Si recibe notificaciones',

    -- FK solo a tabla local
    FOREIGN KEY (id_conversacion) REFERENCES conversaciones(id_conversacion) ON DELETE CASCADE,

    UNIQUE KEY unique_participante (id_conversacion, id_usuario),
    INDEX idx_usuario_tipo (id_usuario, tipo_participante, activo),
    INDEX idx_conversacion (id_conversacion, activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Participantes de cada conversación';

-- ----------------------------------------------------------------------------
-- Tabla: mensajes_conversacion
-- Todos los mensajes de todas las conversaciones
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mensajes_conversacion (
    id_mensaje INT AUTO_INCREMENT PRIMARY KEY,
    id_conversacion INT NOT NULL,
    id_usuario_emisor INT NOT NULL COMMENT 'Usuario emisor (ref: myllm_core_db.users)',
    tipo_emisor ENUM('cliente', 'interno') NOT NULL,
    id_ticket_referenciado INT NULL COMMENT 'Ticket mencionado en este mensaje',
    texto_mensaje TEXT NOT NULL,
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    leido_por_cliente BOOLEAN DEFAULT FALSE COMMENT 'Si el cliente leyó este mensaje',
    leido_por_interno BOOLEAN DEFAULT FALSE COMMENT 'Si algún interno leyó este mensaje',
    fecha_lectura_cliente TIMESTAMP NULL,
    fecha_lectura_interno TIMESTAMP NULL,
    editado BOOLEAN DEFAULT FALSE,
    fecha_edicion TIMESTAMP NULL,
    editado_por INT NULL COMMENT 'Usuario que editó (ref: myllm_core_db.users)',
    mensaje_sistema BOOLEAN DEFAULT FALSE COMMENT 'Si es un mensaje automático del sistema',

    -- FK solo a tablas locales
    FOREIGN KEY (id_conversacion) REFERENCES conversaciones(id_conversacion) ON DELETE CASCADE,
    FOREIGN KEY (id_ticket_referenciado) REFERENCES tickets(id) ON DELETE SET NULL,

    INDEX idx_conversacion_fecha (id_conversacion, fecha_envio ASC),
    INDEX idx_no_leidos_cliente (id_conversacion, leido_por_cliente, tipo_emisor),
    INDEX idx_no_leidos_interno (id_conversacion, leido_por_interno, tipo_emisor),
    INDEX idx_ticket_ref (id_ticket_referenciado),
    INDEX idx_usuario_emisor (id_usuario_emisor)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Mensajes de las conversaciones';

-- ----------------------------------------------------------------------------
-- Tabla: conversaciones_tickets_relacionados
-- Tracking de todos los tickets relacionados con cada conversación
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversaciones_tickets_relacionados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_conversacion INT NOT NULL,
    id_ticket INT NOT NULL,
    tipo_relacion ENUM('principal', 'secundario', 'mencionado') DEFAULT 'mencionado',
    mencionado_por INT COMMENT 'Usuario que hizo referencia (ref: myllm_core_db.users)',
    fecha_vinculacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notas TEXT COMMENT 'Notas sobre la relación',

    -- FK solo a tablas locales
    FOREIGN KEY (id_conversacion) REFERENCES conversaciones(id_conversacion) ON DELETE CASCADE,
    FOREIGN KEY (id_ticket) REFERENCES tickets(id) ON DELETE CASCADE,

    UNIQUE KEY unique_conv_ticket (id_conversacion, id_ticket),
    INDEX idx_ticket (id_ticket),
    INDEX idx_tipo_relacion (tipo_relacion),
    INDEX idx_mencionado_por (mencionado_por)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Relaciones entre conversaciones y tickets';

-- ----------------------------------------------------------------------------
-- Triggers para mantener contadores actualizados
-- ----------------------------------------------------------------------------

DELIMITER //

-- Trigger: Actualizar último mensaje y contadores al insertar mensaje
DROP TRIGGER IF EXISTS after_mensaje_insert//
CREATE TRIGGER after_mensaje_insert
AFTER INSERT ON mensajes_conversacion
FOR EACH ROW
BEGIN
    -- Actualizar campos de último mensaje
    UPDATE conversaciones
    SET
        ultimo_mensaje_texto = NEW.texto_mensaje,
        ultimo_mensaje_de = NEW.tipo_emisor,
        ultimo_mensaje_fecha = NEW.fecha_envio,
        total_mensajes = total_mensajes + 1,
        mensajes_sin_leer_cliente = CASE
            WHEN NEW.tipo_emisor = 'interno' THEN mensajes_sin_leer_cliente + 1
            ELSE mensajes_sin_leer_cliente
        END,
        mensajes_sin_leer_interno = CASE
            WHEN NEW.tipo_emisor = 'cliente' THEN mensajes_sin_leer_interno + 1
            ELSE mensajes_sin_leer_interno
        END
    WHERE id_conversacion = NEW.id_conversacion;

    -- Si el mensaje referencia un ticket, crear relación si no existe
    IF NEW.id_ticket_referenciado IS NOT NULL THEN
        INSERT IGNORE INTO conversaciones_tickets_relacionados
            (id_conversacion, id_ticket, tipo_relacion, mencionado_por)
        VALUES
            (NEW.id_conversacion, NEW.id_ticket_referenciado, 'mencionado', NEW.id_usuario_emisor);
    END IF;
END//

-- Trigger: Actualizar contadores cuando se marca mensaje como leído por cliente
DROP TRIGGER IF EXISTS after_mensaje_leido_cliente//
CREATE TRIGGER after_mensaje_leido_cliente
AFTER UPDATE ON mensajes_conversacion
FOR EACH ROW
BEGIN
    IF NEW.leido_por_cliente = TRUE AND OLD.leido_por_cliente = FALSE AND NEW.tipo_emisor = 'interno' THEN
        UPDATE conversaciones
        SET mensajes_sin_leer_cliente = GREATEST(0, mensajes_sin_leer_cliente - 1)
        WHERE id_conversacion = NEW.id_conversacion;
    END IF;
END//

-- Trigger: Actualizar contadores cuando se marca mensaje como leído por interno
DROP TRIGGER IF EXISTS after_mensaje_leido_interno//
CREATE TRIGGER after_mensaje_leido_interno
AFTER UPDATE ON mensajes_conversacion
FOR EACH ROW
BEGIN
    IF NEW.leido_por_interno = TRUE AND OLD.leido_por_interno = FALSE AND NEW.tipo_emisor = 'cliente' THEN
        UPDATE conversaciones
        SET mensajes_sin_leer_interno = GREATEST(0, mensajes_sin_leer_interno - 1)
        WHERE id_conversacion = NEW.id_conversacion;
    END IF;
END//

DELIMITER ;

-- ============================================================================
-- Vistas útiles para reportes
-- ============================================================================

-- Vista: Conversaciones activas con información completa
CREATE OR REPLACE VIEW v_conversaciones_activas AS
SELECT
    c.id_conversacion,
    c.asunto,
    c.estado,
    c.prioridad,
    c.id_organizacion,
    c.id_usuario_cliente,
    t.titulo as ticket_titulo,
    t.estado as ticket_estado,
    c.fecha_creacion,
    c.fecha_ultima_actualizacion,
    c.ultimo_mensaje_texto,
    c.ultimo_mensaje_de,
    c.mensajes_sin_leer_interno,
    c.total_mensajes,
    GROUP_CONCAT(DISTINCT pc.id_usuario SEPARATOR ',') as usuarios_internos_ids
FROM conversaciones c
LEFT JOIN tickets t ON c.id_ticket_principal = t.id
LEFT JOIN participantes_conversacion pc ON c.id_conversacion = pc.id_conversacion
    AND pc.tipo_participante = 'interno'
WHERE c.estado IN ('abierta', 'en_curso')
GROUP BY c.id_conversacion;

-- ============================================================================
-- Índices adicionales para optimización
-- ============================================================================

-- Índice compuesto para queries frecuentes
CREATE INDEX idx_conv_org_estado_fecha ON conversaciones(id_organizacion, estado, fecha_ultima_actualizacion DESC);

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

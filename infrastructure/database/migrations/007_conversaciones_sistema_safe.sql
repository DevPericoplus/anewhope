-- ============================================================================
-- 007_conversaciones_sistema_safe.sql
-- Sistema de conversaciones (versión segura para ejecución)
-- ============================================================================

USE myllm_projects_db;

-- Tabla 1: asignaciones_organizaciones_internas
CREATE TABLE IF NOT EXISTS asignaciones_organizaciones_internas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario_interno INT NOT NULL,
    id_organizacion INT NOT NULL,
    id_rol INT NOT NULL,
    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    asignado_por INT NOT NULL,
    notas TEXT,
    fecha_desactivacion TIMESTAMP NULL,
    desactivado_por INT NULL,
    FOREIGN KEY (id_usuario_interno) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (id_organizacion) REFERENCES organizaciones(id) ON DELETE CASCADE,
    FOREIGN KEY (id_rol) REFERENCES proyectos_roles_base(id) ON DELETE RESTRICT,
    FOREIGN KEY (asignado_por) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (desactivado_por) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_asignacion (id_usuario_interno, id_organizacion, id_rol),
    INDEX idx_usuario_interno (id_usuario_interno, activo),
    INDEX idx_organizacion (id_organizacion, activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla 2: conversaciones
CREATE TABLE IF NOT EXISTS conversaciones (
    id_conversacion INT AUTO_INCREMENT PRIMARY KEY,
    id_organizacion INT NOT NULL,
    id_usuario_cliente INT NOT NULL,
    id_ticket_principal INT NULL,
    asunto VARCHAR(255),
    estado ENUM('abierta', 'en_curso', 'resuelta', 'cerrada') DEFAULT 'abierta',
    prioridad ENUM('baja', 'media', 'alta', 'urgente') DEFAULT 'media',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ultimo_mensaje_texto TEXT,
    ultimo_mensaje_de ENUM('cliente', 'interno'),
    ultimo_mensaje_fecha TIMESTAMP NULL,
    mensajes_sin_leer_cliente INT DEFAULT 0,
    mensajes_sin_leer_interno INT DEFAULT 0,
    total_mensajes INT DEFAULT 0,
    cerrada_por INT NULL,
    fecha_cierre TIMESTAMP NULL,
    FOREIGN KEY (id_organizacion) REFERENCES organizaciones(id) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario_cliente) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (id_ticket_principal) REFERENCES tickets(id) ON DELETE SET NULL,
    FOREIGN KEY (cerrada_por) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_org_estado (id_organizacion, estado),
    INDEX idx_fecha_actualizacion (fecha_ultima_actualizacion DESC),
    INDEX idx_usuario_cliente (id_usuario_cliente, estado),
    INDEX idx_ticket (id_ticket_principal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla 3: participantes_conversacion
CREATE TABLE IF NOT EXISTS participantes_conversacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_conversacion INT NOT NULL,
    id_usuario INT NOT NULL,
    tipo_participante ENUM('cliente', 'interno') NOT NULL,
    fecha_union TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    ultimo_acceso TIMESTAMP NULL,
    notificaciones_activadas BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (id_conversacion) REFERENCES conversaciones(id_conversacion) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_participante (id_conversacion, id_usuario),
    INDEX idx_usuario_tipo (id_usuario, tipo_participante, activo),
    INDEX idx_conversacion (id_conversacion, activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla 4: mensajes_conversacion
CREATE TABLE IF NOT EXISTS mensajes_conversacion (
    id_mensaje INT AUTO_INCREMENT PRIMARY KEY,
    id_conversacion INT NOT NULL,
    id_usuario_emisor INT NOT NULL,
    tipo_emisor ENUM('cliente', 'interno') NOT NULL,
    id_ticket_referenciado INT NULL,
    texto_mensaje TEXT NOT NULL,
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    leido_por_cliente BOOLEAN DEFAULT FALSE,
    leido_por_interno BOOLEAN DEFAULT FALSE,
    fecha_lectura_cliente TIMESTAMP NULL,
    fecha_lectura_interno TIMESTAMP NULL,
    editado BOOLEAN DEFAULT FALSE,
    fecha_edicion TIMESTAMP NULL,
    editado_por INT NULL,
    mensaje_sistema BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (id_conversacion) REFERENCES conversaciones(id_conversacion) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario_emisor) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (id_ticket_referenciado) REFERENCES tickets(id) ON DELETE SET NULL,
    FOREIGN KEY (editado_por) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_conversacion_fecha (id_conversacion, fecha_envio ASC),
    INDEX idx_no_leidos_cliente (id_conversacion, leido_por_cliente, tipo_emisor),
    INDEX idx_no_leidos_interno (id_conversacion, leido_por_interno, tipo_emisor),
    INDEX idx_ticket_ref (id_ticket_referenciado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla 5: conversaciones_tickets_relacionados
CREATE TABLE IF NOT EXISTS conversaciones_tickets_relacionados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_conversacion INT NOT NULL,
    id_ticket INT NOT NULL,
    tipo_relacion ENUM('principal', 'secundario', 'mencionado') DEFAULT 'mencionado',
    mencionado_por INT,
    fecha_vinculacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notas TEXT,
    FOREIGN KEY (id_conversacion) REFERENCES conversaciones(id_conversacion) ON DELETE CASCADE,
    FOREIGN KEY (id_ticket) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (mencionado_por) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_conv_ticket (id_conversacion, id_ticket),
    INDEX idx_ticket (id_ticket),
    INDEX idx_tipo_relacion (tipo_relacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

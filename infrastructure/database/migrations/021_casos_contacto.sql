-- ============================================================================
-- Migración 021: Casos de contacto LAIM Web
-- Tablas: estados_casos_contacto, casos_contacto, casos_contacto_imagenes
-- Base de datos: laim_core_db
-- El id autogenerado de casos_contacto es el número de caso.
-- Altas nuevas: id_estado = 1 (Abierto).
-- ============================================================================

USE `laim_core_db`;

CREATE TABLE IF NOT EXISTS `estados_casos_contacto` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `clave` varchar(50) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `orden` int(11) NOT NULL DEFAULT 1,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_estados_casos_contacto_clave` (`clave`),
  KEY `idx_estados_casos_contacto_orden` (`orden`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Catálogo de estados de casos de contacto';

INSERT INTO `estados_casos_contacto` (`id`, `clave`, `nombre`, `descripcion`, `orden`, `active`)
VALUES
  (1, 'abierto', 'Abierto', 'Caso recibido, pendiente de atención', 1, 1),
  (2, 'gestionando', 'Gestionando', 'Caso en trámite por el equipo', 2, 1),
  (3, 'escalado', 'Escalado', 'Caso elevado a un nivel superior', 3, 1),
  (4, 'resuelto', 'Resuelto', 'Caso cerrado con respuesta o solución', 4, 1)
ON DUPLICATE KEY UPDATE
  `clave` = VALUES(`clave`),
  `nombre` = VALUES(`nombre`),
  `descripcion` = VALUES(`descripcion`),
  `orden` = VALUES(`orden`),
  `active` = VALUES(`active`);

CREATE TABLE IF NOT EXISTS `casos_contacto` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'Número de caso',
  `id_estado` int(11) NOT NULL DEFAULT 1,
  `usage_mode` enum('local','share','connect','remote','other') NOT NULL DEFAULT 'local',
  `affected_user_info` varchar(500) DEFAULT NULL,
  `message_body` text NOT NULL,
  `reply_email` varchar(255) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `user_name` varchar(255) DEFAULT NULL,
  `organization_id` int(11) DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_casos_contacto_estado` (`id_estado`),
  KEY `idx_casos_contacto_created_at` (`created_at`),
  KEY `idx_casos_contacto_reply_email` (`reply_email`),
  KEY `idx_casos_contacto_user_id` (`user_id`),
  CONSTRAINT `casos_contacto_estado_fk`
    FOREIGN KEY (`id_estado`) REFERENCES `estados_casos_contacto` (`id`),
  CONSTRAINT `casos_contacto_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Casos del formulario de contacto (id = número de caso)';

CREATE TABLE IF NOT EXISTS `casos_contacto_imagenes` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_caso` bigint(20) NOT NULL,
  `file_name` varchar(255) NOT NULL,
  `mime_type` varchar(100) NOT NULL,
  `file_size` int(10) unsigned NOT NULL,
  `image_data` mediumblob NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_casos_contacto_imagenes_caso` (`id_caso`),
  CONSTRAINT `casos_contacto_imagenes_caso_fk`
    FOREIGN KEY (`id_caso`) REFERENCES `casos_contacto` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Capturas adjuntas a casos de contacto';

GRANT SELECT ON `laim_core_db`.`estados_casos_contacto` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`casos_contacto` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`casos_contacto_imagenes` TO 'laim_reader'@'localhost';

GRANT SELECT ON `laim_core_db`.`estados_casos_contacto` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`casos_contacto` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`casos_contacto_imagenes` TO 'laim_writer'@'localhost';

GRANT SELECT ON `laim_core_db`.`estados_casos_contacto` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`casos_contacto` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`casos_contacto_imagenes` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`estados_casos_contacto` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`casos_contacto` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`casos_contacto_imagenes` TO 'laim_writer'@'%';

FLUSH PRIVILEGES;

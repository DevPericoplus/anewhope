-- ============================================================================
-- Migración 028: tickets de soporte LAIM
-- Tablas: laim_ticket_estados, laim_tickets, laim_ticket_mensajes,
--         laim_ticket_eventos, laim_ticket_notificaciones
-- Base de datos: laim_core_db
-- Canal distinto de casos_contacto. Requiere usuario autenticado.
-- ============================================================================

USE `laim_core_db`;

CREATE TABLE IF NOT EXISTS `laim_ticket_estados` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `clave` varchar(50) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `orden` int(11) NOT NULL DEFAULT 1,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_laim_ticket_estados_clave` (`clave`),
  KEY `idx_laim_ticket_estados_orden` (`orden`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Catálogo de estados de tickets de soporte';

INSERT INTO `laim_ticket_estados` (`id`, `clave`, `nombre`, `descripcion`, `orden`, `active`)
VALUES
  (1, 'abierto', 'Abierto', 'Ticket recién creado, pendiente de atención', 1, 1),
  (2, 'en_curso', 'En curso', 'El equipo está trabajando en el ticket', 2, 1),
  (3, 'esperando_usuario', 'Esperando usuario', 'Se ha pedido más información al usuario', 3, 1),
  (4, 'cerrado', 'Cerrado', 'Ticket cerrado; solo lectura salvo Reabrir', 4, 1)
ON DUPLICATE KEY UPDATE
  `clave` = VALUES(`clave`),
  `nombre` = VALUES(`nombre`),
  `descripcion` = VALUES(`descripcion`),
  `orden` = VALUES(`orden`),
  `active` = VALUES(`active`);

CREATE TABLE IF NOT EXISTS `laim_tickets` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'Número público del ticket',
  `id_estado` int(11) NOT NULL DEFAULT 1,
  `user_id` int(11) NOT NULL,
  `user_name` varchar(255) NOT NULL,
  `user_email` varchar(255) NOT NULL,
  `organization_id` int(11) DEFAULT NULL,
  `edition` enum('community_edition','advance') NOT NULL DEFAULT 'community_edition',
  `subject` varchar(200) NOT NULL,
  `body` text NOT NULL,
  `opened_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `closed_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_tickets_estado` (`id_estado`),
  KEY `idx_laim_tickets_user` (`user_id`),
  KEY `idx_laim_tickets_opened` (`opened_at`),
  CONSTRAINT `laim_tickets_estado_fk`
    FOREIGN KEY (`id_estado`) REFERENCES `laim_ticket_estados` (`id`),
  CONSTRAINT `laim_tickets_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Tickets de soporte (usuario autenticado)';

CREATE TABLE IF NOT EXISTS `laim_ticket_mensajes` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `ticket_id` bigint(20) NOT NULL,
  `autor` enum('usuario','operador') NOT NULL,
  `actor_name` varchar(128) NOT NULL,
  `cuerpo` text NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_ticket_mensajes_ticket` (`ticket_id`, `created_at`),
  CONSTRAINT `laim_ticket_mensajes_ticket_fk`
    FOREIGN KEY (`ticket_id`) REFERENCES `laim_tickets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Hilo público de un ticket de soporte';

CREATE TABLE IF NOT EXISTS `laim_ticket_eventos` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `ticket_id` bigint(20) NOT NULL,
  `tipo` enum('created','replied','status_changed','reopened') NOT NULL,
  `estado_desde` int(11) DEFAULT NULL,
  `estado_hasta` int(11) DEFAULT NULL,
  `actor` varchar(128) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_ticket_eventos_ticket` (`ticket_id`, `created_at`),
  CONSTRAINT `laim_ticket_eventos_ticket_fk`
    FOREIGN KEY (`ticket_id`) REFERENCES `laim_tickets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Cronología de sistema de un ticket de soporte';

CREATE TABLE IF NOT EXISTS `laim_ticket_notificaciones` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `ticket_id` bigint(20) NOT NULL,
  `destinatario` enum('usuario','operador') NOT NULL,
  `user_id` int(11) DEFAULT NULL COMMENT 'Dueño del ticket si destinatario=usuario; NULL para operador',
  `tipo` enum('ticket_created','ticket_replied','ticket_status','ticket_reopened') NOT NULL,
  `leida` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_ticket_notif_pending` (`destinatario`, `user_id`, `leida`, `created_at`),
  KEY `idx_laim_ticket_notif_ticket` (`ticket_id`),
  CONSTRAINT `laim_ticket_notif_ticket_fk`
    FOREIGN KEY (`ticket_id`) REFERENCES `laim_tickets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Avisos persistidos de tickets (no notifications.dat)';

GRANT SELECT ON `laim_core_db`.`laim_ticket_estados` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_tickets` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_ticket_mensajes` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_ticket_eventos` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_ticket_notificaciones` TO 'laim_reader'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_ticket_estados` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_tickets` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_ticket_mensajes` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_ticket_eventos` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_ticket_notificaciones` TO 'laim_writer'@'localhost';

GRANT SELECT ON `laim_core_db`.`laim_ticket_estados` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`laim_tickets` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`laim_ticket_mensajes` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`laim_ticket_eventos` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`laim_ticket_notificaciones` TO 'laim_reader'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_ticket_estados` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_tickets` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_ticket_mensajes` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_ticket_eventos` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_ticket_notificaciones` TO 'laim_writer'@'%';

FLUSH PRIVILEGES;

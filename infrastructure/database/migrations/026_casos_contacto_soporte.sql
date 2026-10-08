-- ============================================================================
-- Migración 026: gestión de soporte sobre casos de contacto
-- Añade estado descartado y tablas de respuestas, etiquetas y auditoría.
-- Base de datos: laim_core_db
-- ============================================================================

USE `laim_core_db`;

INSERT INTO `estados_casos_contacto` (`id`, `clave`, `nombre`, `descripcion`, `orden`, `active`)
VALUES
  (5, 'descartado', 'Descartado', 'Caso informativo que no precisa respuesta', 5, 1)
ON DUPLICATE KEY UPDATE
  `clave` = VALUES(`clave`),
  `nombre` = VALUES(`nombre`),
  `descripcion` = VALUES(`descripcion`),
  `orden` = VALUES(`orden`),
  `active` = VALUES(`active`);

CREATE TABLE IF NOT EXISTS `casos_contacto_respuestas` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_caso` bigint(20) NOT NULL,
  `cuerpo` text NOT NULL,
  `origen` enum('manual','ia') NOT NULL DEFAULT 'manual',
  `estado` enum('borrador','enviada') NOT NULL DEFAULT 'borrador',
  `kb_candidata` tinyint(1) NOT NULL DEFAULT 0,
  `creado_en` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_casos_contacto_respuestas_caso` (`id_caso`),
  CONSTRAINT `casos_contacto_respuestas_caso_fk`
    FOREIGN KEY (`id_caso`) REFERENCES `casos_contacto` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Borradores y respuestas de soporte (envío de correo pendiente)';

CREATE TABLE IF NOT EXISTS `casos_contacto_etiquetas` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_caso` bigint(20) NOT NULL,
  `keyword` varchar(80) NOT NULL,
  `fuente` enum('ia','manual') NOT NULL DEFAULT 'ia',
  `confianza` decimal(4,3) DEFAULT NULL,
  `creado_en` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_casos_contacto_etiquetas_caso_kw` (`id_caso`, `keyword`),
  KEY `idx_casos_contacto_etiquetas_keyword` (`keyword`),
  CONSTRAINT `casos_contacto_etiquetas_caso_fk`
    FOREIGN KEY (`id_caso`) REFERENCES `casos_contacto` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Keywords de clasificación de casos de soporte';

CREATE TABLE IF NOT EXISTS `casos_contacto_auditoria` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_caso` bigint(20) NOT NULL,
  `estado_desde` int(11) NOT NULL,
  `estado_hasta` int(11) NOT NULL,
  `actor` varchar(128) NOT NULL,
  `creado_en` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_casos_contacto_auditoria_caso` (`id_caso`),
  CONSTRAINT `casos_contacto_auditoria_caso_fk`
    FOREIGN KEY (`id_caso`) REFERENCES `casos_contacto` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Historial de cambios de estado de casos de contacto';

GRANT SELECT ON `laim_core_db`.`casos_contacto_respuestas` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`casos_contacto_etiquetas` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`casos_contacto_auditoria` TO 'laim_reader'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`casos_contacto_respuestas` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`casos_contacto_etiquetas` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`casos_contacto_auditoria` TO 'laim_writer'@'localhost';

GRANT SELECT ON `laim_core_db`.`casos_contacto_respuestas` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`casos_contacto_etiquetas` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`casos_contacto_auditoria` TO 'laim_reader'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`casos_contacto_respuestas` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`casos_contacto_etiquetas` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`casos_contacto_auditoria` TO 'laim_writer'@'%';

FLUSH PRIVILEGES;

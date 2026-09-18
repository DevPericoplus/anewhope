-- ============================================================================
-- Migración 024: laim_product_audit_log
-- Auditoría real de instalaciones/actualizaciones de producto y plugins,
-- en ambas modalidades — ver anewhope/AGENTS.md § 37.4. El menú "Auditoría"
-- de laimweb (static_pages/config_auditoria.md) es hoy solo texto de
-- documentación; el patrón más cercano que existe (_append_auth_log en
-- routermiddleware.py) escribe a un fichero JSON, no consultable para
-- estadísticas agregadas — esta tabla es la base real de un futuro cuadro
-- de mando, todavía sin diseñar.
-- ============================================================================

USE `laim_core_db`;

CREATE TABLE IF NOT EXISTS `laim_product_audit_log` (
  `audit_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `serial_number` varchar(64) NOT NULL COMMENT 'Instalación de laim que realizó la operación',
  `owner_type` enum('user','organization') NOT NULL,
  `owner_id` int(11) NOT NULL,
  `operation` enum('install','update') NOT NULL,
  `target_type` enum('product','plugin') NOT NULL,
  `plugin_name` varchar(100) DEFAULT NULL COMMENT 'NULL cuando target_type=product',
  `edition` enum('community_edition','advance') NOT NULL,
  `version_from` varchar(32) DEFAULT NULL COMMENT 'NULL en una instalación nueva (sin versión previa)',
  `version_to` varchar(32) NOT NULL,
  `platform` enum('windows','mac_intel','mac_silicon','linux_deb','linux_rpm') NOT NULL,
  `result` enum('success','failed') NOT NULL,
  `error_detail` text DEFAULT NULL COMMENT 'Poblado cuando result=failed',
  `occurred_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`audit_id`),
  KEY `idx_serial_number` (`serial_number`),
  KEY `idx_owner` (`owner_type`, `owner_id`),
  KEY `idx_occurred_at` (`occurred_at`),
  KEY `idx_edition_op_result` (`edition`, `operation`, `result`),
  KEY `idx_plugin_name` (`plugin_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Auditoría de instalación/actualización de producto y plugins (base del futuro cuadro de mando)';

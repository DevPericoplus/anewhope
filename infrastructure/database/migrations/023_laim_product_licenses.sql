-- ============================================================================
-- Migración 023: laim_product_licenses + laim_product_license_plugins
-- Persistencia real para src/1_shared_domain/entities/product_license.py,
-- que hasta ahora vivía en un mock JSON (2_shared_application/moks/) y no
-- tenía ningún llamador en todo el repo — sin dependencias que migrar.
--
-- Añade vigencia real (fecha_inicio/fecha_fin) para "advance", ausente en
-- el mock. laim_product_license_plugins deja abierto el modelo SaaS futuro
-- descrito en anewhope/AGENTS.md § 37.5 — renovación selectiva por-plugin,
-- independiente de la vigencia del producto core — sin implementar pagos
-- todavía (eso sigue expresamente fuera de alcance).
-- ============================================================================

USE `laim_core_db`;

CREATE TABLE IF NOT EXISTS `laim_product_licenses` (
  `license_id` int(11) NOT NULL AUTO_INCREMENT,
  `serial_number` varchar(64) NOT NULL COMMENT 'Generado por laim init, ver laim/internal/utils/serial.go',
  `edition` enum('community_edition','advance') NOT NULL,
  `status` enum('FREE','PENDING','ACTIVE','EXPIRED','CANCELLED') NOT NULL,
  `owner_type` enum('user','organization') NOT NULL,
  `owner_id` int(11) NOT NULL,
  `fecha_inicio` timestamp NULL DEFAULT NULL COMMENT 'Vigencia advance — NULL en community_edition, no aplica',
  `fecha_fin` timestamp NULL DEFAULT NULL COMMENT 'Tras esta fecha sin renovación, se comporta como community_edition (ver AGENTS.md § 37.5) — el registro se conserva para auditoría, no se borra',
  `registered_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`license_id`),
  UNIQUE KEY `uk_serial_number` (`serial_number`),
  KEY `idx_owner` (`owner_type`, `owner_id`),
  KEY `idx_edition_status` (`edition`, `status`),
  KEY `idx_fecha_fin` (`fecha_fin`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Registro de licencias de producto (serial -> edición/vigencia)';

CREATE TABLE IF NOT EXISTS `laim_product_license_plugins` (
  `entitlement_id` int(11) NOT NULL AUTO_INCREMENT,
  `license_id` int(11) NOT NULL,
  `plugin_name` varchar(100) NOT NULL COMMENT 'Coincide con el nombre de carpeta cmd/<nombre> en laim',
  `fecha_inicio` timestamp NOT NULL,
  `fecha_fin` timestamp NOT NULL COMMENT 'Vigencia propia del plugin, independiente de la del core (renovación selectiva, ver AGENTS.md § 37.5)',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`entitlement_id`),
  UNIQUE KEY `uk_license_plugin` (`license_id`, `plugin_name`) COMMENT 'v1: una renovación sobrescribe la vigencia existente, no se guarda histórico de renovaciones',
  KEY `idx_plugin_name` (`plugin_name`),
  KEY `idx_fecha_fin` (`fecha_fin`),
  CONSTRAINT `laim_plp_ibfk_1` FOREIGN KEY (`license_id`) REFERENCES `laim_product_licenses` (`license_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Vigencia de plugins advance por licencia, independiente entre sí';

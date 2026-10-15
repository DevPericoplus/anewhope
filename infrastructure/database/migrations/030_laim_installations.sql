-- ============================================================================
-- Migración 030: registro de instalaciones LAIM + KeySerialSigning
-- laim_installations es el inventario de dispositivos del portal (página
-- Registro). Distinto de laim_product_licenses (edición/pago): al confirmar
-- un registro se crea la licencia CE FREE (o PENDING si advance).
--
-- key_kind en laim_exchange_keys: exchange = KeyExchageLaimApp (servidor→
-- cliente); serial_signing = KeySerialSigning (cliente→servidor). No mezclar.
-- ============================================================================

USE `laim_core_db`;

ALTER TABLE `laim_exchange_keys`
  ADD COLUMN `key_kind` enum('exchange','serial_signing') NOT NULL DEFAULT 'exchange'
    COMMENT 'exchange=KeyExchageLaimApp; serial_signing=KeySerialSigning'
    AFTER `major_version`;

CREATE TABLE IF NOT EXISTS `laim_installations` (
  `installation_id` int(11) NOT NULL AUTO_INCREMENT,
  `serial_number` varchar(64) NOT NULL COMMENT 'laim init, VerifySerial en backend_core',
  `user_id` int(11) NOT NULL,
  `hostname` varchar(255) NOT NULL COMMENT 'Inmutable tras persistir (nombre de máquina)',
  `operating_system` enum('windows','mac','linux') NOT NULL,
  `edition` enum('community_edition','advance') NOT NULL DEFAULT 'community_edition',
  `origin` enum('manual','laim') NOT NULL,
  `status` enum('pending_recognition','registered','rejected') NOT NULL,
  `license_id` int(11) DEFAULT NULL,
  `proposed_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `registered_at` timestamp NULL DEFAULT NULL,
  `recognized_at` timestamp NULL DEFAULT NULL,
  `rejected_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`installation_id`),
  UNIQUE KEY `uk_serial_number` (`serial_number`),
  KEY `idx_user_status` (`user_id`, `status`),
  CONSTRAINT `laim_inst_user_fk` FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`),
  CONSTRAINT `laim_inst_license_fk` FOREIGN KEY (`license_id`) REFERENCES `laim_product_licenses` (`license_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Instalaciones registradas o pendientes de reconocer';

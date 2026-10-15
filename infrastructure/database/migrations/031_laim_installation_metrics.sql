-- ============================================================================
-- Migración 031: alias de dispositivo, bloqueo de intentos, avisos y métricas
-- Alias (display_name) es mutable; hostname y serial siguen inmutables.
-- Intentos fallidos van por correo (3 → bloqueo; el operador desbloquea
-- vía ticket de soporte). Los eventos de métrica congelan SO/edición en
-- el momento del registro para que un cambio posterior de SO no reescriba
-- el histórico. Avisos de propuesta pendiente: mismo patrón que tickets
-- (el poll no hace ack).
-- ============================================================================

USE `laim_core_db`;

ALTER TABLE `laim_installations`
  ADD COLUMN `display_name` varchar(80) NOT NULL DEFAULT ''
    COMMENT 'Alias mutable del dispositivo; distinto del hostname de máquina'
    AFTER `hostname`;

CREATE TABLE IF NOT EXISTS `laim_installation_register_guards` (
  `user_email` varchar(255) NOT NULL COMMENT 'Clave de bloqueo: el correo de la cuenta',
  `fail_count` int(11) NOT NULL DEFAULT 0,
  `blocked_at` timestamp NULL DEFAULT NULL,
  `last_reason` varchar(255) NOT NULL DEFAULT '',
  `last_fail_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`user_email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Intentos de registro fallidos por correo (máx. 3)';

CREATE TABLE IF NOT EXISTS `laim_installation_notifications` (
  `notification_id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `installation_id` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `acked_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`notification_id`),
  KEY `idx_inst_notif_pending` (`user_id`, `acked_at`),
  CONSTRAINT `laim_inst_notif_user_fk` FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`),
  CONSTRAINT `laim_inst_notif_inst_fk` FOREIGN KEY (`installation_id`) REFERENCES `laim_installations` (`installation_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Aviso de propuesta de instalación pendiente de reconocer';

CREATE TABLE IF NOT EXISTS `laim_installation_metric_events` (
  `event_id` int(11) NOT NULL AUTO_INCREMENT,
  `installation_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `operating_system` enum('windows','mac','linux') NOT NULL,
  `edition` enum('community_edition','advance') NOT NULL,
  `origin` enum('manual','laim') NOT NULL,
  `event_type` enum('registered') NOT NULL DEFAULT 'registered'
    COMMENT 'registered = se creó la licencia; futuro: advance_activated',
  `occurred_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`event_id`),
  KEY `idx_inst_metric_month` (`event_type`, `occurred_at`),
  KEY `idx_inst_metric_os` (`operating_system`, `occurred_at`),
  CONSTRAINT `laim_inst_metric_inst_fk` FOREIGN KEY (`installation_id`) REFERENCES `laim_installations` (`installation_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Instantáneas de registro para el dashboard de métricas';

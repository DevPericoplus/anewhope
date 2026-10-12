-- ============================================================================
-- Migración 027: tokens de recuperación de contraseña LAIM
-- SHA-256 del secreto (nunca el raw), TTL 15 min, used_at invalida el enlace.
-- Base de datos: laim_core_db
-- ============================================================================

USE `laim_core_db`;

CREATE TABLE IF NOT EXISTS `laim_password_reset_tokens` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `token_hash` char(64) NOT NULL,
  `expires_at` timestamp NOT NULL,
  `used_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `request_ip` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_laim_password_reset_token_hash` (`token_hash`),
  KEY `idx_laim_password_reset_user` (`user_id`),
  KEY `idx_laim_password_reset_expires` (`expires_at`),
  CONSTRAINT `laim_password_reset_tokens_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Tokens opacos de recuperación de contraseña (hash SHA-256, 15 min)';

GRANT SELECT ON `laim_core_db`.`laim_password_reset_tokens` TO 'laim_reader'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_password_reset_tokens` TO 'laim_writer'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_password_reset_tokens` TO 'laim_reader'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_password_reset_tokens` TO 'laim_writer'@'%';

FLUSH PRIVILEGES;

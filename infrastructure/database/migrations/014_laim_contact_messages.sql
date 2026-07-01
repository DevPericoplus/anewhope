-- ============================================================================
-- Migración 014: Mensajes de contacto LAIM Web
-- Tablas: laim_contact_messages, laim_contact_messages_images
-- Base de datos: laim_core_db
-- ============================================================================

USE `laim_core_db`;

CREATE TABLE IF NOT EXISTS `laim_contact_messages` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `usage_mode` enum('local','share','connect','remote','other') NOT NULL DEFAULT 'local',
  `affected_user_info` varchar(500) DEFAULT NULL,
  `message_body` text NOT NULL,
  `reply_email` varchar(255) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `user_name` varchar(255) DEFAULT NULL,
  `organization_id` int(11) DEFAULT NULL,
  `status` enum('pending','in_review','answered','closed') NOT NULL DEFAULT 'pending',
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_contact_status` (`status`),
  KEY `idx_laim_contact_created_at` (`created_at`),
  KEY `idx_laim_contact_reply_email` (`reply_email`),
  KEY `idx_laim_contact_user_id` (`user_id`),
  CONSTRAINT `laim_contact_messages_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Mensajes del formulario de contacto del portal';

CREATE TABLE IF NOT EXISTS `laim_contact_messages_images` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `message_id` bigint(20) NOT NULL,
  `file_name` varchar(255) NOT NULL,
  `mime_type` varchar(100) NOT NULL,
  `file_size` int(10) unsigned NOT NULL,
  `image_data` mediumblob NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_contact_images_message_id` (`message_id`),
  CONSTRAINT `laim_contact_images_message_fk`
    FOREIGN KEY (`message_id`) REFERENCES `laim_contact_messages` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Capturas adjuntas a mensajes de contacto';

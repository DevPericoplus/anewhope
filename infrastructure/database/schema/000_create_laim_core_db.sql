-- ============================================================================
-- Migración 012: Creación de laim_core_db
-- Clonado de estructura de myllm_core_db con prefijo laim_
-- Solo estructura, sin datos
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `laim_core_db`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `laim_core_db`;

-- ============================================================================
-- Tablas base (sin dependencias de FK)
-- ============================================================================

CREATE TABLE IF NOT EXISTS `laim_organizations` (
  `organization_id` int(11) NOT NULL AUTO_INCREMENT,
  `organization_name` varchar(255) NOT NULL,
  `organization_email` varchar(255) NOT NULL,
  `organization_tlf` varchar(20) DEFAULT NULL,
  `organization_address` text DEFAULT NULL,
  `organization_country` varchar(100) DEFAULT NULL,
  `organization_state` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `active` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`organization_id`),
  KEY `idx_organization_name` (`organization_name`),
  KEY `idx_organization_email` (`organization_email`),
  KEY `idx_active` (`active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Organizations in the system';

CREATE TABLE IF NOT EXISTS `laim_identity_types` (
  `identity_type_id` int(11) NOT NULL AUTO_INCREMENT,
  `identity_type_name` varchar(255) NOT NULL,
  `identity_type_rol` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`identity_type_id`),
  KEY `idx_identity_type_name` (`identity_type_name`),
  KEY `idx_identity_type_rol` (`identity_type_rol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Different types of identities or roles in the system';

CREATE TABLE IF NOT EXISTS `laim_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `permission_name` varchar(255) NOT NULL,
  `permission_description` text NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `permission_name` (`permission_name`),
  KEY `idx_permission_name` (`permission_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Basic permissions for the application';

CREATE TABLE IF NOT EXISTS `laim_basic_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `permission_name` varchar(255) NOT NULL,
  `permission_description` text NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `permission_name` (`permission_name`),
  KEY `idx_basic_permission_name` (`permission_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Basic permissions source';

CREATE TABLE IF NOT EXISTS `laim_low_level_permissions` (
  `id_permissions` int(11) NOT NULL,
  `folder_create` tinyint(1) DEFAULT 0,
  `folder_delete` tinyint(1) DEFAULT 0,
  `folder_rename` tinyint(1) DEFAULT 0,
  `folder_read` tinyint(1) DEFAULT 0,
  `file_create` tinyint(1) DEFAULT 0,
  `file_read` tinyint(1) DEFAULT 0,
  `file_update` tinyint(1) DEFAULT 0,
  `file_delete` tinyint(1) DEFAULT 0,
  `project_create` tinyint(1) DEFAULT 0,
  `project_read` tinyint(1) DEFAULT 0,
  `project_update` tinyint(1) DEFAULT 0,
  `project_delete` tinyint(1) DEFAULT 0,
  `version_create` tinyint(1) DEFAULT 0,
  `version_read` tinyint(1) DEFAULT 0,
  `version_update` tinyint(1) DEFAULT 0,
  `version_delete` tinyint(1) DEFAULT 0,
  `training_create` tinyint(1) DEFAULT 0,
  `training_read` tinyint(1) DEFAULT 0,
  `training_update` tinyint(1) DEFAULT 0,
  `training_delete` tinyint(1) DEFAULT 0,
  `training_start` tinyint(1) DEFAULT 0,
  `training_stop` tinyint(1) DEFAULT 0,
  `parameters_create` tinyint(1) DEFAULT 0,
  `parameters_read` tinyint(1) DEFAULT 0,
  `parameters_update` tinyint(1) DEFAULT 0,
  `parameters_delete` tinyint(1) DEFAULT 0,
  `notifications_create` tinyint(1) DEFAULT 0,
  `notifications_read` tinyint(1) DEFAULT 0,
  `notifications_update` tinyint(1) DEFAULT 0,
  `notifications_delete` tinyint(1) DEFAULT 0,
  `user_create` tinyint(1) DEFAULT 0,
  `user_read` tinyint(1) DEFAULT 0,
  `user_update` tinyint(1) DEFAULT 0,
  `user_delete` tinyint(1) DEFAULT 0,
  `user_enable` tinyint(1) DEFAULT 0,
  `user_disable` tinyint(1) DEFAULT 0,
  `folder_list` tinyint(1) DEFAULT 0,
  `file_list` tinyint(1) DEFAULT 0,
  `project_list` tinyint(1) DEFAULT 0,
  `version_list` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id_permissions`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Low level permissions matrix';

-- ============================================================================
-- Tablas con dependencias de FK (nivel 1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS `laim_users` (
  `user_id` int(11) NOT NULL AUTO_INCREMENT,
  `organization_id` int(11) NOT NULL,
  `identity_type_id` int(11) NOT NULL,
  `user_name` varchar(255) NOT NULL,
  `user_password` varchar(500) NOT NULL,
  `user_email` varchar(255) NOT NULL,
  `user_mobile` varchar(20) DEFAULT NULL,
  `user_otp` varchar(10) DEFAULT NULL,
  `active` tinyint(1) DEFAULT 1,
  `blocked` tinyint(1) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `user_name` (`user_name`),
  KEY `idx_user_name` (`user_name`),
  KEY `idx_user_email` (`user_email`),
  KEY `idx_organization_id` (`organization_id`),
  KEY `idx_identity_type_id` (`identity_type_id`),
  KEY `idx_active_blocked` (`active`,`blocked`),
  CONSTRAINT `laim_users_ibfk_1` FOREIGN KEY (`organization_id`) REFERENCES `laim_organizations` (`organization_id`),
  CONSTRAINT `laim_users_ibfk_2` FOREIGN KEY (`identity_type_id`) REFERENCES `laim_identity_types` (`identity_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - User accounts in the system';

CREATE TABLE IF NOT EXISTS `laim_roles` (
  `identity_type_id` int(11) NOT NULL,
  `identity_type_name` varchar(255) NOT NULL,
  `identity_type_rol` varchar(255) NOT NULL,
  `identity_type_group_permission` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`identity_type_id`),
  KEY `idx_roles_permission` (`identity_type_group_permission`),
  CONSTRAINT `laim_roles_ibfk_1` FOREIGN KEY (`identity_type_group_permission`) REFERENCES `laim_permissions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Roles source';

CREATE TABLE IF NOT EXISTS `laim_identity_type_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `identity_type_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_identity_permission` (`identity_type_id`,`permission_id`),
  UNIQUE KEY `uk_identity_type_id` (`identity_type_id`),
  UNIQUE KEY `uk_permission_id` (`permission_id`),
  KEY `idx_identity_type_id` (`identity_type_id`),
  KEY `idx_permission_id` (`permission_id`),
  CONSTRAINT `laim_itp_ibfk_1` FOREIGN KEY (`identity_type_id`) REFERENCES `laim_identity_types` (`identity_type_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_itp_ibfk_2` FOREIGN KEY (`permission_id`) REFERENCES `laim_permissions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Mapping between identity types and permissions';

-- ============================================================================
-- Tablas con dependencias de FK (nivel 2)
-- ============================================================================

CREATE TABLE IF NOT EXISTS `laim_sessions` (
  `session_id` varchar(36) NOT NULL,
  `user_id` int(11) NOT NULL,
  `organization_id` int(11) NOT NULL,
  `identity_type_id` int(11) NOT NULL,
  `access_token_jti` varchar(36) DEFAULT NULL,
  `session_token_jti` varchar(36) DEFAULT NULL,
  `status` enum('active','inactive','expired','revoked') DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `last_activity` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `expires_at` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` text DEFAULT NULL,
  PRIMARY KEY (`session_id`),
  KEY `organization_id` (`organization_id`),
  KEY `identity_type_id` (`identity_type_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_expires_at` (`expires_at`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `laim_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_sessions_ibfk_2` FOREIGN KEY (`organization_id`) REFERENCES `laim_organizations` (`organization_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_sessions_ibfk_3` FOREIGN KEY (`identity_type_id`) REFERENCES `laim_identity_types` (`identity_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - User session tracking';

CREATE TABLE IF NOT EXISTS `laim_auth_logs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `timestamp` timestamp NOT NULL DEFAULT current_timestamp(),
  `user_name` varchar(255) DEFAULT NULL,
  `event` enum('login_success','login_failed','logout','password_change','otp_verification','token_refresh','permission_denied','login_attempt','login_blocked','otp_request') NOT NULL,
  `status` enum('success','failure','failed','blocked') NOT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `session_id` varchar(36) DEFAULT NULL,
  `user_agent` text DEFAULT NULL,
  `details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`details`)),
  PRIMARY KEY (`id`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_user_name` (`user_name`),
  KEY `idx_event` (`event`),
  KEY `idx_status` (`status`),
  KEY `idx_ip_address` (`ip_address`),
  KEY `idx_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Authentication and security event logs';

CREATE TABLE IF NOT EXISTS `laim_user_billing_info` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `first_name` varchar(100) DEFAULT NULL,
  `sur_name` varchar(100) DEFAULT NULL,
  `country` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `zip_code` varchar(20) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_names` (`first_name`,`sur_name`),
  CONSTRAINT `laim_ubi_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - User billing information';

CREATE TABLE IF NOT EXISTS `laim_user_contact_info` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `first_name` varchar(100) DEFAULT NULL,
  `sur_name` varchar(100) DEFAULT NULL,
  `country` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `zip_code` varchar(20) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_names` (`first_name`,`sur_name`),
  CONSTRAINT `laim_uci_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - User contact information';

CREATE TABLE IF NOT EXISTS `laim_user_organization_management` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `organization_id` int(11) NOT NULL,
  `identity_type_id` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by_user_id` int(11) DEFAULT NULL,
  `active` tinyint(1) DEFAULT 1,
  `project_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_org_role` (`user_id`,`organization_id`,`identity_type_id`),
  KEY `created_by_user_id` (`created_by_user_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_organization_id` (`organization_id`),
  KEY `idx_identity_type_id` (`identity_type_id`),
  KEY `idx_active` (`active`),
  CONSTRAINT `laim_uom_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_uom_ibfk_2` FOREIGN KEY (`organization_id`) REFERENCES `laim_organizations` (`organization_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_uom_ibfk_3` FOREIGN KEY (`identity_type_id`) REFERENCES `laim_identity_types` (`identity_type_id`),
  CONSTRAINT `laim_uom_ibfk_4` FOREIGN KEY (`created_by_user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - User organization and role management';

CREATE TABLE IF NOT EXISTS `laim_estado_version` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_organizacion` int(11) NOT NULL,
  `id_proyecto` int(11) NOT NULL,
  `id_version` int(11) NOT NULL,
  `state` enum('Abierta','Bloqueada','Protegida','Final') NOT NULL DEFAULT 'Abierta',
  `protected` tinyint(1) NOT NULL DEFAULT 0,
  `size` bigint(20) unsigned NOT NULL DEFAULT 0 COMMENT 'Tamaño en bytes',
  `final_c` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Cliente solicita entrenamiento',
  `final_i` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Interno confirma entrenamiento',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_version` (`id_organizacion`,`id_proyecto`,`id_version`),
  KEY `idx_org_project` (`id_organizacion`,`id_proyecto`),
  CONSTRAINT `chk_state_protected` CHECK (
    (`state` = 'Abierta' AND `protected` = 0 AND `final_c` = 0 AND `final_i` = 0) OR
    (`state` = 'Bloqueada' AND `protected` = 1 AND `final_c` = 0 AND `final_i` = 0) OR
    (`state` = 'Protegida' AND `protected` = 1 AND `final_c` = 1 AND `final_i` = 0) OR
    (`state` = 'Final' AND `protected` = 1 AND `final_c` = 1 AND `final_i` = 1)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Version state tracking';

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
  COMMENT='LAIM - Capturas adjuntas a mensajes de contacto (legacy)';

CREATE TABLE IF NOT EXISTS `estados_casos_contacto` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `clave` varchar(50) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `orden` int(11) NOT NULL DEFAULT 1,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_estados_casos_contacto_clave` (`clave`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Catálogo de estados de casos de contacto';

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

INSERT INTO `estados_casos_contacto` (`id`, `clave`, `nombre`, `descripcion`, `orden`, `active`)
VALUES
  (1, 'abierto', 'Abierto', 'Caso recibido, pendiente de atención', 1, 1),
  (2, 'gestionando', 'Gestionando', 'Caso en trámite por el equipo', 2, 1),
  (3, 'escalado', 'Escalado', 'Caso elevado a un nivel superior', 3, 1),
  (4, 'resuelto', 'Resuelto', 'Caso cerrado con respuesta o solución', 4, 1)
ON DUPLICATE KEY UPDATE
  `clave` = VALUES(`clave`),
  `nombre` = VALUES(`nombre`);

-- ============================================================================
-- Vistas
-- ============================================================================

CREATE OR REPLACE VIEW `laim_permissions_explorer` AS
SELECT
  `id_permissions`,
  `folder_create`, `folder_delete`, `folder_rename`, `folder_read`, `folder_list`,
  `file_create`, `file_read`, `file_update`, `file_delete`, `file_list`,
  `version_create`, `training_create`
FROM `laim_low_level_permissions`;

CREATE OR REPLACE VIEW `laim_view_users_otp` AS
SELECT `user_id`, `user_name`, `user_otp`
FROM `laim_users`
ORDER BY `user_id`;

CREATE OR REPLACE VIEW `laim_v_active_sessions` AS
SELECT
  s.`session_id`,
  s.`user_id`,
  u.`user_name`,
  u.`user_email`,
  s.`organization_id`,
  o.`organization_name`,
  s.`status`,
  s.`created_at`,
  s.`last_activity`,
  s.`expires_at`,
  s.`ip_address`,
  TIMESTAMPDIFF(MINUTE, s.`last_activity`, CURRENT_TIMESTAMP()) AS `inactive_minutes`
FROM `laim_sessions` s
LEFT JOIN `laim_users` u ON s.`user_id` = u.`user_id`
LEFT JOIN `laim_organizations` o ON s.`organization_id` = o.`organization_id`
WHERE s.`status` = 'active' AND s.`expires_at` > CURRENT_TIMESTAMP();

CREATE OR REPLACE VIEW `laim_v_auth_events_summary` AS
SELECT
  CAST(`timestamp` AS DATE) AS `event_date`,
  `event`,
  `status`,
  COUNT(*) AS `event_count`
FROM `laim_auth_logs`
GROUP BY CAST(`timestamp` AS DATE), `event`, `status`
ORDER BY CAST(`timestamp` AS DATE) DESC, `event`;

CREATE OR REPLACE VIEW `laim_v_organization_user_stats` AS
SELECT
  o.`organization_id`,
  o.`organization_name`,
  COUNT(DISTINCT u.`user_id`) AS `total_users`,
  SUM(CASE WHEN u.`active` = 1 THEN 1 ELSE 0 END) AS `active_users`,
  SUM(CASE WHEN u.`blocked` = 1 THEN 1 ELSE 0 END) AS `blocked_users`,
  COUNT(DISTINCT s.`session_id`) AS `active_sessions`
FROM `laim_organizations` o
LEFT JOIN `laim_users` u ON o.`organization_id` = u.`organization_id`
LEFT JOIN `laim_sessions` s ON u.`user_id` = s.`user_id`
  AND s.`status` = 'active' AND s.`expires_at` > CURRENT_TIMESTAMP()
GROUP BY o.`organization_id`, o.`organization_name`;

CREATE OR REPLACE VIEW `laim_v_user_full_info` AS
SELECT
  u.`user_id`,
  u.`user_name`,
  u.`user_email`,
  u.`user_mobile`,
  u.`active`,
  u.`blocked`,
  o.`organization_id`,
  o.`organization_name`,
  it.`identity_type_id`,
  it.`identity_type_name`,
  it.`identity_type_rol`,
  uci.`first_name`,
  uci.`sur_name`,
  uci.`country`,
  uci.`state`,
  u.`created_at`,
  u.`modified_at`
FROM `laim_users` u
LEFT JOIN `laim_organizations` o ON u.`organization_id` = o.`organization_id`
LEFT JOIN `laim_identity_types` it ON u.`identity_type_id` = it.`identity_type_id`
LEFT JOIN `laim_user_contact_info` uci ON u.`user_id` = uci.`user_id`;

CREATE OR REPLACE VIEW `laim_v_user_permissions` AS
SELECT
  u.`user_id`,
  u.`user_name`,
  u.`organization_id`,
  it.`identity_type_id`,
  it.`identity_type_name`,
  p.`id` AS `permission_id`,
  p.`permission_name`,
  p.`permission_description`
FROM `laim_users` u
LEFT JOIN `laim_identity_types` it ON u.`identity_type_id` = it.`identity_type_id`
LEFT JOIN `laim_identity_type_permissions` itp ON it.`identity_type_id` = itp.`identity_type_id`
LEFT JOIN `laim_permissions` p ON itp.`permission_id` = p.`id`;

-- ============================================================================
-- Usuarios dedicados para laim_core_db (credenciales independientes de myllm_*)
-- ============================================================================

CREATE USER IF NOT EXISTS 'laim_admin'@'localhost' IDENTIFIED BY 'NDt@dL_0Rxw6aiI_@XSE';
CREATE USER IF NOT EXISTS 'laim_writer'@'localhost' IDENTIFIED BY 'YzKG89nsIWvMf2M5q0B7';
CREATE USER IF NOT EXISTS 'laim_reader'@'localhost' IDENTIFIED BY 'Avv7VZs4x3iuxAgPysrH';

GRANT ALL PRIVILEGES ON `laim_core_db`.* TO 'laim_admin'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.* TO 'laim_writer'@'localhost';
GRANT SELECT ON `laim_core_db`.* TO 'laim_reader'@'localhost';

FLUSH PRIVILEGES;

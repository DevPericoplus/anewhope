-- ============================================================================
-- Migración 015: Sistema de foro LAIM Web
-- Tablas: imágenes, perfil foro, catálogo, contenido, moderación, valoraciones
-- Base de datos: laim_core_db
-- ============================================================================

USE `laim_core_db`;

-- ============================================================================
-- Imágenes del foro (metadatos; binarios en filesystem del backend)
-- ============================================================================

CREATE TABLE IF NOT EXISTS `laim_forum_images` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `image_kind` enum('avatar_catalog','avatar_user','post_attachment') NOT NULL,
  `storage_key` varchar(512) NOT NULL,
  `file_name` varchar(255) NOT NULL,
  `mime_type` varchar(100) NOT NULL,
  `file_size` int(10) unsigned NOT NULL,
  `uploaded_by_user_id` int(11) DEFAULT NULL,
  `checksum_sha256` char(64) DEFAULT NULL,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_laim_forum_images_storage_key` (`storage_key`),
  KEY `idx_laim_forum_images_kind` (`image_kind`),
  KEY `idx_laim_forum_images_uploader` (`uploaded_by_user_id`),
  CONSTRAINT `laim_forum_images_user_fk`
    FOREIGN KEY (`uploaded_by_user_id`) REFERENCES `laim_users` (`user_id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - metadatos de imágenes (avatars y adjuntos)';

CREATE TABLE IF NOT EXISTS `laim_forum_avatar_catalog` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `image_id` bigint(20) NOT NULL,
  `label` varchar(100) NOT NULL,
  `is_default` tinyint(1) NOT NULL DEFAULT 0,
  `sort_order` int(11) NOT NULL DEFAULT 0,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_forum_avatar_catalog_active` (`active`, `sort_order`),
  CONSTRAINT `laim_forum_avatar_catalog_image_fk`
    FOREIGN KEY (`image_id`) REFERENCES `laim_forum_images` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - catálogo de avatares seleccionables';

-- ============================================================================
-- Perfil de usuario extendido para el foro
-- ============================================================================

CREATE TABLE IF NOT EXISTS `laim_user_forum` (
  `user_id` int(11) NOT NULL,
  `avatar_image_id` bigint(20) DEFAULT NULL,
  `forum_display_name` varchar(100) DEFAULT NULL,
  `signature_md` text DEFAULT NULL,
  `reputation_avg` decimal(3,2) NOT NULL DEFAULT 0.00,
  `reputation_votes` int(11) NOT NULL DEFAULT 0,
  `notify_mentions` tinyint(1) NOT NULL DEFAULT 1,
  `notify_replies` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`user_id`),
  KEY `idx_laim_user_forum_avatar` (`avatar_image_id`),
  CONSTRAINT `laim_user_forum_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_user_forum_avatar_fk`
    FOREIGN KEY (`avatar_image_id`) REFERENCES `laim_forum_images` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - extensión de perfil de usuario';

-- ============================================================================
-- Catálogo del foro
-- ============================================================================

CREATE TABLE IF NOT EXISTS `laim_forum_categories` (
  `id` varchar(64) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(500) DEFAULT NULL,
  `orden` int(11) NOT NULL DEFAULT 0,
  `activa` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_forum_categories_activa_orden` (`activa`, `orden`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - categorías';

CREATE TABLE IF NOT EXISTS `laim_forum_subcategories` (
  `id` varchar(64) NOT NULL,
  `categoria_id` varchar(64) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(500) DEFAULT NULL,
  `orden` int(11) NOT NULL DEFAULT 0,
  `activa` tinyint(1) NOT NULL DEFAULT 1,
  `ban_seconds` int(11) NOT NULL DEFAULT 86400,
  `log_rotation` enum('weekly','daily','none') NOT NULL DEFAULT 'weekly',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_forum_subcategories_categoria` (`categoria_id`, `activa`, `orden`),
  CONSTRAINT `laim_forum_subcategories_categoria_fk`
    FOREIGN KEY (`categoria_id`) REFERENCES `laim_forum_categories` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - subcategorías';

CREATE TABLE IF NOT EXISTS `laim_forum_prefixes` (
  `id` varchar(64) NOT NULL,
  `texto` varchar(50) NOT NULL,
  `color_scheme` varchar(30) NOT NULL DEFAULT 'green',
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_forum_prefixes_activo` (`activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - prefijos de hilo';

-- ============================================================================
-- Contenido: hilos y respuestas
-- ============================================================================

CREATE TABLE IF NOT EXISTS `laim_forum_threads` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `subcategory_id` varchar(64) NOT NULL,
  `prefix_id` varchar(64) DEFAULT NULL,
  `titulo` varchar(255) NOT NULL,
  `user_id` int(11) NOT NULL,
  `user_name` varchar(255) NOT NULL,
  `cuerpo_md` mediumtext NOT NULL,
  `fijado` tinyint(1) NOT NULL DEFAULT 0,
  `cerrado` tinyint(1) NOT NULL DEFAULT 0,
  `deleted` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_forum_threads_subcategory` (`subcategory_id`, `fijado`, `updated_at`),
  KEY `idx_laim_forum_threads_user` (`user_id`),
  CONSTRAINT `laim_forum_threads_subcategory_fk`
    FOREIGN KEY (`subcategory_id`) REFERENCES `laim_forum_subcategories` (`id`)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `laim_forum_threads_prefix_fk`
    FOREIGN KEY (`prefix_id`) REFERENCES `laim_forum_prefixes` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `laim_forum_threads_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - hilos';

CREATE TABLE IF NOT EXISTS `laim_forum_posts` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `thread_id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `user_name` varchar(255) NOT NULL,
  `cuerpo_md` mediumtext NOT NULL,
  `deleted` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_forum_posts_thread` (`thread_id`, `created_at`),
  KEY `idx_laim_forum_posts_user` (`user_id`),
  CONSTRAINT `laim_forum_posts_thread_fk`
    FOREIGN KEY (`thread_id`) REFERENCES `laim_forum_threads` (`id`) ON DELETE CASCADE,
  CONSTRAINT `laim_forum_posts_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - respuestas';

CREATE TABLE IF NOT EXISTS `laim_forum_thread_images` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `thread_id` bigint(20) NOT NULL,
  `image_id` bigint(20) NOT NULL,
  `sort_order` tinyint(3) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_laim_forum_thread_image` (`thread_id`, `image_id`),
  CONSTRAINT `laim_forum_thread_images_thread_fk`
    FOREIGN KEY (`thread_id`) REFERENCES `laim_forum_threads` (`id`) ON DELETE CASCADE,
  CONSTRAINT `laim_forum_thread_images_image_fk`
    FOREIGN KEY (`image_id`) REFERENCES `laim_forum_images` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - adjuntos en hilos';

CREATE TABLE IF NOT EXISTS `laim_forum_post_images` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `post_id` bigint(20) NOT NULL,
  `image_id` bigint(20) NOT NULL,
  `sort_order` tinyint(3) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_laim_forum_post_image` (`post_id`, `image_id`),
  CONSTRAINT `laim_forum_post_images_post_fk`
    FOREIGN KEY (`post_id`) REFERENCES `laim_forum_posts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `laim_forum_post_images_image_fk`
    FOREIGN KEY (`image_id`) REFERENCES `laim_forum_images` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - adjuntos en respuestas';

-- ============================================================================
-- Moderación y configuración
-- ============================================================================

CREATE TABLE IF NOT EXISTS `laim_forum_moderators` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `user_name` varchar(255) NOT NULL,
  `subcategory_id` varchar(64) NOT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_laim_forum_moderator` (`user_id`, `subcategory_id`),
  KEY `idx_laim_forum_moderators_subcategory` (`subcategory_id`, `activo`),
  CONSTRAINT `laim_forum_moderators_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_forum_moderators_subcategory_fk`
    FOREIGN KEY (`subcategory_id`) REFERENCES `laim_forum_subcategories` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - moderadores por subcategoría';

CREATE TABLE IF NOT EXISTS `laim_forum_settings` (
  `id` tinyint(3) unsigned NOT NULL DEFAULT 1,
  `anunciar_ban_en_log` tinyint(1) NOT NULL DEFAULT 1,
  `plantilla_ban` text NOT NULL,
  `plantilla_eliminacion` text NOT NULL,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - configuración singleton de moderación';

INSERT INTO `laim_forum_settings` (`id`, `plantilla_ban`, `plantilla_eliminacion`)
VALUES (
  1,
  'El usuario @usuario ha sido baneado en @subcategoria. Motivo: @motivo',
  'Contenido eliminado por moderación. Motivo: @motivo'
)
ON DUPLICATE KEY UPDATE `id` = `id`;

CREATE TABLE IF NOT EXISTS `laim_forum_word_rules` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `palabra` varchar(100) NOT NULL,
  `accion` varchar(50) NOT NULL,
  `mensaje` varchar(500) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_forum_word_rules_activo` (`activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - reglas automáticas de palabras';

CREATE TABLE IF NOT EXISTS `laim_forum_allowed_urls` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dominio` varchar(255) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_laim_forum_allowed_urls_dominio` (`dominio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - dominios permitidos en markdown';

CREATE TABLE IF NOT EXISTS `laim_forum_bans` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `subcategory_id` varchar(64) NOT NULL,
  `motivo` varchar(500) NOT NULL,
  `moderador_user_id` int(11) DEFAULT NULL,
  `moderador_user_name` varchar(255) DEFAULT NULL,
  `expires_at` timestamp NULL DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  `automatico` tinyint(1) NOT NULL DEFAULT 0,
  `revocado_por_user_id` int(11) DEFAULT NULL,
  `revocado_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_forum_bans_user_sub` (`user_id`, `subcategory_id`, `activo`),
  CONSTRAINT `laim_forum_bans_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_forum_bans_subcategory_fk`
    FOREIGN KEY (`subcategory_id`) REFERENCES `laim_forum_subcategories` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - baneos por subcategoría';

CREATE TABLE IF NOT EXISTS `laim_forum_infractions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `subcategory_id` varchar(64) NOT NULL,
  `tipo` varchar(50) NOT NULL,
  `strikes` int(11) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_forum_infractions_user_sub` (`user_id`, `subcategory_id`),
  CONSTRAINT `laim_forum_infractions_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_forum_infractions_subcategory_fk`
    FOREIGN KEY (`subcategory_id`) REFERENCES `laim_forum_subcategories` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - infracciones / strikes';

CREATE TABLE IF NOT EXISTS `laim_forum_notifications` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `tipo` varchar(50) NOT NULL,
  `titulo` varchar(255) NOT NULL,
  `mensaje` varchar(1000) NOT NULL,
  `category_id` varchar(64) DEFAULT NULL,
  `subcategory_id` varchar(64) DEFAULT NULL,
  `thread_id` bigint(20) DEFAULT NULL,
  `post_id` bigint(20) DEFAULT NULL,
  `entregada` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_forum_notifications_user_pending` (`user_id`, `entregada`, `created_at`),
  CONSTRAINT `laim_forum_notifications_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - notificaciones pendientes';

CREATE TABLE IF NOT EXISTS `laim_forum_post_ratings` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `post_id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `target_user_id` int(11) NOT NULL,
  `valoracion` tinyint(3) unsigned NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_laim_forum_post_ratings_voter` (`post_id`, `user_id`),
  KEY `idx_laim_forum_post_ratings_target` (`target_user_id`),
  CONSTRAINT `laim_forum_post_ratings_post_fk`
    FOREIGN KEY (`post_id`) REFERENCES `laim_forum_posts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `laim_forum_post_ratings_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_forum_post_ratings_target_fk`
    FOREIGN KEY (`target_user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_forum_post_ratings_valoracion_chk`
    CHECK (`valoracion` BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - valoraciones 1-5 por respuesta';

CREATE TABLE IF NOT EXISTS `laim_forum_moderation_logs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `subcategory_id` varchar(64) NOT NULL,
  `event_type` varchar(50) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `user_name` varchar(255) DEFAULT NULL,
  `moderator_user_id` int(11) DEFAULT NULL,
  `moderator_user_name` varchar(255) DEFAULT NULL,
  `thread_id` bigint(20) DEFAULT NULL,
  `post_id` bigint(20) DEFAULT NULL,
  `message` text NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_laim_forum_mod_logs_sub_created` (`subcategory_id`, `created_at`),
  CONSTRAINT `laim_forum_mod_logs_subcategory_fk`
    FOREIGN KEY (`subcategory_id`) REFERENCES `laim_forum_subcategories` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - logs de moderación por subcategoría';

-- ============================================================================
-- Permisos MariaDB
-- ============================================================================

GRANT SELECT ON `laim_core_db`.`laim_forum_images` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_avatar_catalog` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_user_forum` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_categories` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_subcategories` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_prefixes` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_threads` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_posts` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_thread_images` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_post_images` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_moderators` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_settings` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_word_rules` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_allowed_urls` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_bans` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_infractions` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_notifications` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_post_ratings` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_forum_moderation_logs` TO 'laim_reader'@'localhost';

GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_images` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_avatar_catalog` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_user_forum` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_categories` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_subcategories` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_prefixes` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_threads` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_posts` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_thread_images` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_post_images` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_moderators` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE ON `laim_core_db`.`laim_forum_settings` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_word_rules` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_allowed_urls` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_bans` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_infractions` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_notifications` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_post_ratings` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT ON `laim_core_db`.`laim_forum_moderation_logs` TO 'laim_writer'@'localhost';

FLUSH PRIVILEGES;

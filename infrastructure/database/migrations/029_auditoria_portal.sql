-- ============================================================================
-- Migración 029: auditoría de uso del portal laimweb
-- Tablas: auditoria_usuarios, auditoria_visitas, auditoria_paginas,
--         auditoria_instaladores, auditoria_foro
-- Eventos append-only (o intervalos) para el futuro dashboard. Sin backfill.
-- Distinto de laim_product_audit_log (install/update del cliente desktop)
-- y de laim_auth_logs (seguridad). Doble escritura desde auth/foro.
-- Base de datos: laim_core_db
-- ============================================================================

USE `laim_core_db`;

CREATE TABLE IF NOT EXISTS `auditoria_usuarios` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `accion` enum('alta','login','logout','login_fallido','bloqueo') NOT NULL,
  `user_id` int(11) DEFAULT NULL COMMENT 'NULL en login_fallido / bloqueo sin cuenta',
  `user_name` varchar(255) NOT NULL,
  `session_id` varchar(128) DEFAULT NULL,
  `occurred_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_auditoria_usuarios_occurred` (`occurred_at`),
  KEY `idx_auditoria_usuarios_user` (`user_id`, `occurred_at`),
  KEY `idx_auditoria_usuarios_accion` (`accion`, `occurred_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Altas y accesos del portal (tendencias, no sustituye laim_auth_logs)';

CREATE TABLE IF NOT EXISTS `auditoria_visitas` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `session_id` varchar(128) NOT NULL,
  `started_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `last_seen_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `segundos` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_auditoria_visitas_session` (`session_id`, `id`),
  KEY `idx_auditoria_visitas_user` (`user_id`, `started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Tiempo de visita autenticada (UPSERT por heartbeat)';

CREATE TABLE IF NOT EXISTS `auditoria_paginas` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `session_id` varchar(128) NOT NULL,
  `seccion` enum('home','instaladores','foro','faq','tickets','contacto','share','login','registro','config','otros') NOT NULL,
  `started_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `ended_at` timestamp NULL DEFAULT NULL,
  `segundos` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_auditoria_paginas_open` (`session_id`, `ended_at`),
  KEY `idx_auditoria_paginas_seccion` (`seccion`, `started_at`),
  KEY `idx_auditoria_paginas_user` (`user_id`, `started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Tramo por sección del portal para hábitos y uso relativo';

CREATE TABLE IF NOT EXISTS `auditoria_instaladores` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `accion` enum('copia_script','script_http','descarga') NOT NULL,
  `edition` enum('community_edition','advance') NOT NULL,
  `platform` enum('windows','mac_intel','mac_silicon','linux_deb','linux_rpm') NOT NULL,
  `version` varchar(32) DEFAULT NULL,
  `filename` varchar(255) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL COMMENT 'NULL si anónimo; nunca IP',
  `occurred_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_auditoria_instaladores_occurred` (`occurred_at`),
  KEY `idx_auditoria_instaladores_combo` (`edition`, `platform`, `accion`, `occurred_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Copia de script y descargas web (anónimos sin identificar)';

CREATE TABLE IF NOT EXISTS `auditoria_foro` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `accion` enum('crear_hilo','crear_respuesta') NOT NULL,
  `user_id` int(11) NOT NULL,
  `thread_id` bigint(20) NOT NULL,
  `post_id` bigint(20) DEFAULT NULL,
  `subcategory_id` varchar(64) DEFAULT NULL,
  `occurred_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_auditoria_foro_occurred` (`occurred_at`),
  KEY `idx_auditoria_foro_user` (`user_id`, `occurred_at`),
  KEY `idx_auditoria_foro_thread` (`thread_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Escritura de foro (hilos y respuestas; no lecturas)';

GRANT SELECT ON `laim_core_db`.`auditoria_usuarios` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`auditoria_visitas` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`auditoria_paginas` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`auditoria_instaladores` TO 'laim_reader'@'localhost';
GRANT SELECT ON `laim_core_db`.`auditoria_foro` TO 'laim_reader'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`auditoria_usuarios` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`auditoria_visitas` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`auditoria_paginas` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`auditoria_instaladores` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`auditoria_foro` TO 'laim_writer'@'localhost';

GRANT SELECT ON `laim_core_db`.`auditoria_usuarios` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`auditoria_visitas` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`auditoria_paginas` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`auditoria_instaladores` TO 'laim_reader'@'%';
GRANT SELECT ON `laim_core_db`.`auditoria_foro` TO 'laim_reader'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`auditoria_usuarios` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`auditoria_visitas` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`auditoria_paginas` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`auditoria_instaladores` TO 'laim_writer'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`auditoria_foro` TO 'laim_writer'@'%';

FLUSH PRIVILEGES;

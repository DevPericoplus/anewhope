-- ============================================================================
-- LAIM Foro — valoraciones por hilo (1 voto por usuario por hilo)
-- Migración: 016_laim_forum_thread_ratings.sql
-- ============================================================================

USE `laim_core_db`;

ALTER TABLE `laim_forum_threads`
  ADD COLUMN IF NOT EXISTS `rating_avg` decimal(4,2) NOT NULL DEFAULT 0.00
    COMMENT 'Promedio de valoraciones del hilo (1-5)',
  ADD COLUMN IF NOT EXISTS `rating_count` int(10) unsigned NOT NULL DEFAULT 0
    COMMENT 'Número total de valoraciones del hilo';

CREATE TABLE IF NOT EXISTS `laim_forum_thread_ratings` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `thread_id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `valoracion` tinyint(3) unsigned NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp()
    ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_laim_forum_thread_ratings_voter` (`thread_id`, `user_id`),
  KEY `idx_laim_forum_thread_ratings_user` (`user_id`),
  CONSTRAINT `laim_forum_thread_ratings_thread_fk`
    FOREIGN KEY (`thread_id`) REFERENCES `laim_forum_threads` (`id`) ON DELETE CASCADE,
  CONSTRAINT `laim_forum_thread_ratings_user_fk`
    FOREIGN KEY (`user_id`) REFERENCES `laim_users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `laim_forum_thread_ratings_valoracion_chk`
    CHECK (`valoracion` BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM Foro - valoraciones 1-5 por hilo (una por usuario)';

DROP TRIGGER IF EXISTS `trg_laim_forum_thread_ratings_ai`;
DROP TRIGGER IF EXISTS `trg_laim_forum_thread_ratings_au`;
DROP TRIGGER IF EXISTS `trg_laim_forum_thread_ratings_ad`;

CREATE TRIGGER `trg_laim_forum_thread_ratings_ai`
AFTER INSERT ON `laim_forum_thread_ratings`
FOR EACH ROW
UPDATE `laim_forum_threads` AS t
SET
  t.`rating_avg` = COALESCE(
    (
      SELECT ROUND(AVG(r.`valoracion`), 2)
      FROM `laim_forum_thread_ratings` AS r
      WHERE r.`thread_id` = NEW.`thread_id`
    ),
    0.00
  ),
  t.`rating_count` = (
    SELECT COUNT(*)
    FROM `laim_forum_thread_ratings` AS r
    WHERE r.`thread_id` = NEW.`thread_id`
  )
WHERE t.`id` = NEW.`thread_id`;

CREATE TRIGGER `trg_laim_forum_thread_ratings_au`
AFTER UPDATE ON `laim_forum_thread_ratings`
FOR EACH ROW
UPDATE `laim_forum_threads` AS t
SET
  t.`rating_avg` = COALESCE(
    (
      SELECT ROUND(AVG(r.`valoracion`), 2)
      FROM `laim_forum_thread_ratings` AS r
      WHERE r.`thread_id` = NEW.`thread_id`
    ),
    0.00
  ),
  t.`rating_count` = (
    SELECT COUNT(*)
    FROM `laim_forum_thread_ratings` AS r
    WHERE r.`thread_id` = NEW.`thread_id`
  )
WHERE t.`id` = NEW.`thread_id`;

CREATE TRIGGER `trg_laim_forum_thread_ratings_ad`
AFTER DELETE ON `laim_forum_thread_ratings`
FOR EACH ROW
UPDATE `laim_forum_threads` AS t
SET
  t.`rating_avg` = COALESCE(
    (
      SELECT ROUND(AVG(r.`valoracion`), 2)
      FROM `laim_forum_thread_ratings` AS r
      WHERE r.`thread_id` = OLD.`thread_id`
    ),
    0.00
  ),
  t.`rating_count` = (
    SELECT COUNT(*)
    FROM `laim_forum_thread_ratings` AS r
    WHERE r.`thread_id` = OLD.`thread_id`
  )
WHERE t.`id` = OLD.`thread_id`;

GRANT SELECT ON `laim_core_db`.`laim_forum_thread_ratings` TO 'laim_reader'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_forum_thread_ratings` TO 'laim_writer'@'localhost';

FLUSH PRIVILEGES;

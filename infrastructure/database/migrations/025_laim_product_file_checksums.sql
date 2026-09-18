-- ============================================================================
-- Migración 025: laim_product_file_checksums
-- Base de la detección de manipulación en la caché de laimweb — ver
-- anewhope/AGENTS.md § 37.3. Un fichero de producto/parche/plugin vive en
-- el storage del backend (LAIM_PRODUCT_STORAGE); esta tabla guarda su
-- SHA-256 real, calculado por backend_core (que ya monta ese storage
-- directamente) la primera vez que sirve cada fichero. laimweb compara su
-- copia cacheada contra este valor antes de servirla.
--
-- SHA-256, no MD5 — misma convención ya usada en laim_forum_image_storage
-- (checksum_sha256) y, a diferencia de MD5, sigue siendo apropiado para
-- detectar manipulación deliberada, no solo corrupción accidental.
-- ============================================================================

USE `laim_core_db`;

CREATE TABLE IF NOT EXISTS `laim_product_file_checksums` (
  `checksum_id` int(11) NOT NULL AUTO_INCREMENT,
  `relative_path` varchar(500) NOT NULL COMMENT 'Ruta relativa dentro de LAIM_PRODUCT_STORAGE, p.ej. community_edition/installers/linux/deb/0.3.14/laim_install_0.3.14_amd64.deb',
  `sha256` char(64) NOT NULL,
  `file_size_bytes` bigint(20) unsigned NOT NULL,
  `computed_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`checksum_id`),
  UNIQUE KEY `uk_relative_path` (`relative_path`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - SHA-256 de referencia de cada fichero de producto/parche/plugin en el storage del backend';

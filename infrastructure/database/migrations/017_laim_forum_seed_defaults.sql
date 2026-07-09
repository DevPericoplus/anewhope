-- ============================================================================
-- Migración 017: Datos iniciales del foro LAIM (equivalente a Radikal JSON)
-- Base de datos: laim_core_db
-- ============================================================================

USE `laim_core_db`;

-- Categoría general
INSERT INTO `laim_forum_categories` (`id`, `nombre`, `descripcion`, `orden`, `activa`)
VALUES (
  'general',
  'General',
  'Categoría general del foro del portal',
  1,
  1
)
ON DUPLICATE KEY UPDATE
  `nombre` = VALUES(`nombre`),
  `descripcion` = VALUES(`descripcion`),
  `orden` = VALUES(`orden`),
  `activa` = VALUES(`activa`);

-- Subcategorías por defecto
INSERT INTO `laim_forum_subcategories` (
  `id`, `categoria_id`, `nombre`, `descripcion`, `orden`, `activa`,
  `ban_seconds`, `log_rotation`
)
VALUES
  (
    'presentaciones',
    'general',
    'Presentaciones',
    'Preséntate a la comunidad',
    1,
    1,
    86400,
    'weekly'
  ),
  (
    'debate',
    'general',
    'Debate',
    'Temas abiertos de conversación',
    2,
    1,
    86400,
    'weekly'
  )
ON DUPLICATE KEY UPDATE
  `nombre` = VALUES(`nombre`),
  `descripcion` = VALUES(`descripcion`),
  `orden` = VALUES(`orden`),
  `activa` = VALUES(`activa`),
  `ban_seconds` = VALUES(`ban_seconds`),
  `log_rotation` = VALUES(`log_rotation`);

-- Prefijos de hilo
INSERT INTO `laim_forum_prefixes` (`id`, `texto`, `color_scheme`, `activo`)
VALUES
  ('duda', '[Duda]', 'blue', 1),
  ('anuncio', '[Anuncio]', 'amber', 1),
  ('resuelto', '[Resuelto]', 'green', 1)
ON DUPLICATE KEY UPDATE
  `texto` = VALUES(`texto`),
  `color_scheme` = VALUES(`color_scheme`),
  `activo` = VALUES(`activo`);

-- URL autorizada por defecto
INSERT INTO `laim_forum_allowed_urls` (`dominio`, `descripcion`, `activo`)
VALUES ('youtube.com', 'YouTube', 1)
ON DUPLICATE KEY UPDATE
  `descripcion` = VALUES(`descripcion`),
  `activo` = VALUES(`activo`);

-- Plantillas de moderación (alineadas con Radikal)
UPDATE `laim_forum_settings`
SET
  `anunciar_ban_en_log` = 1,
  `plantilla_ban` = 'Usuario {usuario} baneado del foro. Motivo: {motivo}',
  `plantilla_eliminacion` = 'Mensaje eliminado por moderación. Motivo: {motivo}'
WHERE `id` = 1;

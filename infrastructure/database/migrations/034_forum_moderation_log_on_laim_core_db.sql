-- 033 quedó registrada, pero el ALTER corrió en la base por defecto del
-- cliente (myllm_core_db). El foro escribe en laim_core_db, donde la
-- clave ajena sigue rechazando categoría, prefijo, regla y dominio.
-- Esta pasada es idempotente: si la clave ya no está, no falla.

USE `laim_core_db`;

SET @fk_name := (
  SELECT CONSTRAINT_NAME
  FROM information_schema.KEY_COLUMN_USAGE
  WHERE TABLE_SCHEMA = 'laim_core_db'
    AND TABLE_NAME = 'laim_forum_moderation_logs'
    AND COLUMN_NAME = 'subcategory_id'
    AND REFERENCED_TABLE_NAME IS NOT NULL
  LIMIT 1
);

SET @drop_fk := IF(
  @fk_name IS NULL,
  'SELECT 1',
  CONCAT(
    'ALTER TABLE `laim_forum_moderation_logs` DROP FOREIGN KEY `',
    @fk_name,
    '`'
  )
);

PREPARE laim_drop_modlog_fk FROM @drop_fk;
EXECUTE laim_drop_modlog_fk;
DEALLOCATE PREPARE laim_drop_modlog_fk;

ALTER TABLE `laim_forum_moderation_logs`
  MODIFY `subcategory_id` varchar(64) NULL;

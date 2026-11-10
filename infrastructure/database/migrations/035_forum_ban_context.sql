-- Contexto del baneo automático y excepción de una regla de palabra.
-- La palabra y el fragmento permiten decidir si fue un falso positivo.
-- excepcion_tiene / excepcion_no_tiene permiten la palabra en ese contexto.
-- patron es la expresión editable; vacía, se usa la palabra.

USE `laim_core_db`;

SET @add_rule_context := (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = 'laim_core_db'
        AND TABLE_NAME = 'laim_forum_word_rules'
        AND COLUMN_NAME = 'excepcion_tiene'
    ),
    'SELECT 1',
    'ALTER TABLE `laim_forum_word_rules`
       ADD COLUMN `excepcion_tiene` varchar(500) NULL AFTER `mensaje`,
       ADD COLUMN `excepcion_no_tiene` varchar(500) NULL AFTER `excepcion_tiene`,
       ADD COLUMN `patron` varchar(500) NULL AFTER `excepcion_no_tiene`'
  )
);
PREPARE laim_add_rule_context FROM @add_rule_context;
EXECUTE laim_add_rule_context;
DEALLOCATE PREPARE laim_add_rule_context;

SET @add_ban_context := (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = 'laim_core_db'
        AND TABLE_NAME = 'laim_forum_bans'
        AND COLUMN_NAME = 'palabra'
    ),
    'SELECT 1',
    'ALTER TABLE `laim_forum_bans`
       ADD COLUMN `palabra` varchar(100) NULL AFTER `motivo`,
       ADD COLUMN `fragmento` varchar(500) NULL AFTER `palabra`'
  )
);
PREPARE laim_add_ban_context FROM @add_ban_context;
EXECUTE laim_add_ban_context;
DEALLOCATE PREPARE laim_add_ban_context;

-- El visor de moderación también registra cambios de configuración
-- (categorías, prefijos, reglas, dominios, ajustes). Esos eventos no
-- pertenecen a una subcategoría, y borrar una subcategoría no debe
-- llevarse el historial con ella: la clave ajena en cascada vaciaba
-- el log en cuanto la prueba de QA limpiaba lo que acababa de crear.
-- El cliente de migraciones abre myllm_core_db; sin este USE el ALTER
-- no toca la tabla que escribe el foro.

USE `laim_core_db`;

ALTER TABLE `laim_forum_moderation_logs`
  DROP FOREIGN KEY `laim_forum_mod_logs_subcategory_fk`;

ALTER TABLE `laim_forum_moderation_logs`
  MODIFY `subcategory_id` varchar(64) NULL;

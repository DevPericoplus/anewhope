-- ============================================================================
-- Migración 022: laim_exchange_keys
-- Persistencia del lado servidor de KeyExchageLaimApp (laim/internal/utils/
-- version.go) — clave HMAC compartida entre laim y laimweb para autenticar
-- (no cifrar; ver anewhope/AGENTS.md § 37.2) las respuestas de
-- /check_last_version y de descarga de parches/plugins.
--
-- Una tabla, no un valor único en protected_values.py, porque
-- GlobalInstallationKeys rota por versión mayor de laim y anewhope necesita
-- poder validar contra varias claves vigentes a la vez durante la
-- transición de una versión mayor a la siguiente.
--
-- El valor real de la clave NO se inserta en esta migración ni en ningún
-- fichero versionado — se aplica directamente en base de datos cuando se
-- implemente el consumidor (mismo criterio ya seguido con
-- jwt_access_secret_key).
-- ============================================================================

USE `laim_core_db`;

CREATE TABLE IF NOT EXISTS `laim_exchange_keys` (
  `key_id` int(11) NOT NULL AUTO_INCREMENT,
  `major_version` varchar(20) NOT NULL COMMENT 'Versión mayor de laim a la que corresponde esta clave (p.ej. "0", "1")',
  -- TODO: el cifrado en reposo de este valor está pendiente de diseño —
  -- anewhope no tiene hoy un equivalente a LoadMasterKey() (laim_dat.go)
  -- para cifrar/descifrar de forma reversible. Hasta que exista, el acceso
  -- a esta columna se protege solo por permisos de base de datos, igual
  -- que las contraseñas de servicio en 012_laim_core_db_schema.sql — no
  -- es el estado final deseado, ver anewhope/AGENTS.md § 37.2.
  `key_value_cipher` varchar(500) NOT NULL COMMENT 'Valor de la clave, cifrado en reposo (mecanismo de cifrado: pendiente de diseño)',
  `valid_from` timestamp NOT NULL DEFAULT current_timestamp(),
  `valid_until` timestamp NULL DEFAULT NULL COMMENT 'NULL = sin fecha de expiración fijada todavía',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`key_id`),
  KEY `idx_major_version` (`major_version`),
  KEY `idx_validity` (`valid_from`, `valid_until`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='LAIM - Claves HMAC de intercambio laim<->laimweb, una fila por versión mayor vigente';

-- ============================================================================
-- Migración 013: Seed catálogo LAIM + organización «laim»
-- Copia catálogo desde myllm_core_db (si existe) cuando las tablas están vacías
-- ============================================================================

USE `laim_core_db`;

SET FOREIGN_KEY_CHECKS = 0;

-- --------------------------------------------------------------------------
-- Catálogo: basic_permissions
-- --------------------------------------------------------------------------
INSERT INTO `laim_basic_permissions` (
    `id`, `permission_name`, `permission_description`, `created_at`, `modified_at`
)
SELECT
    src.`id`, src.`permission_name`, src.`permission_description`,
    src.`created_at`, src.`modified_at`
FROM `myllm_core_db`.`basic_permissions` AS src
WHERE (SELECT COUNT(*) FROM `laim_basic_permissions`) = 0
  AND EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'myllm_core_db' AND table_name = 'basic_permissions'
  );

-- --------------------------------------------------------------------------
-- Catálogo: permissions
-- --------------------------------------------------------------------------
INSERT INTO `laim_permissions` (
    `id`, `permission_name`, `permission_description`, `created_at`, `modified_at`
)
SELECT
    src.`id`, src.`permission_name`, src.`permission_description`,
    src.`created_at`, src.`modified_at`
FROM `myllm_core_db`.`permissions` AS src
WHERE (SELECT COUNT(*) FROM `laim_permissions`) = 0
  AND EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'myllm_core_db' AND table_name = 'permissions'
  );

-- --------------------------------------------------------------------------
-- Catálogo: identity_types
-- --------------------------------------------------------------------------
INSERT INTO `laim_identity_types` (
    `identity_type_id`, `identity_type_name`, `identity_type_rol`,
    `created_at`, `modified_at`
)
SELECT
    src.`identity_type_id`, src.`identity_type_name`, src.`identity_type_rol`,
    src.`created_at`, src.`modified_at`
FROM `myllm_core_db`.`identity_types` AS src
WHERE (SELECT COUNT(*) FROM `laim_identity_types`) = 0
  AND EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'myllm_core_db' AND table_name = 'identity_types'
  );

-- --------------------------------------------------------------------------
-- Catálogo: low_level_permissions
-- --------------------------------------------------------------------------
INSERT INTO `laim_low_level_permissions` (
    `id_permissions`,
    `folder_create`, `folder_delete`, `folder_rename`, `folder_read`, `folder_list`,
    `file_create`, `file_read`, `file_update`, `file_delete`, `file_list`,
    `project_create`, `project_read`, `project_update`, `project_delete`, `project_list`,
    `version_create`, `version_read`, `version_update`, `version_delete`, `version_list`,
    `training_create`, `training_read`, `training_update`, `training_delete`,
    `training_start`, `training_stop`,
    `parameters_create`, `parameters_read`, `parameters_update`, `parameters_delete`,
    `notifications_create`, `notifications_read`, `notifications_update`, `notifications_delete`,
    `user_create`, `user_read`, `user_update`, `user_delete`, `user_enable`, `user_disable`
)
SELECT
    src.`id_permissions`,
    src.`folder_create`, src.`folder_delete`, src.`folder_rename`, src.`folder_read`, src.`folder_list`,
    src.`file_create`, src.`file_read`, src.`file_update`, src.`file_delete`, src.`file_list`,
    src.`project_create`, src.`project_read`, src.`project_update`, src.`project_delete`, src.`project_list`,
    src.`version_create`, src.`version_read`, src.`version_update`, src.`version_delete`, src.`version_list`,
    src.`training_create`, src.`training_read`, src.`training_update`, src.`training_delete`,
    src.`training_start`, src.`training_stop`,
    src.`parameters_create`, src.`parameters_read`, src.`parameters_update`, src.`parameters_delete`,
    src.`notifications_create`, src.`notifications_read`, src.`notifications_update`, src.`notifications_delete`,
    src.`user_create`, src.`user_read`, src.`user_update`, src.`user_delete`, src.`user_enable`, src.`user_disable`
FROM `myllm_core_db`.`low_level_permissions` AS src
WHERE (SELECT COUNT(*) FROM `laim_low_level_permissions`) = 0
  AND EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'myllm_core_db' AND table_name = 'low_level_permissions'
  );

-- --------------------------------------------------------------------------
-- Catálogo: roles (depende de permissions)
-- --------------------------------------------------------------------------
INSERT INTO `laim_roles` (
    `identity_type_id`, `identity_type_name`, `identity_type_rol`,
    `identity_type_group_permission`, `created_at`, `modified_at`
)
SELECT
    src.`identity_type_id`, src.`identity_type_name`, src.`identity_type_rol`,
    src.`identity_type_group_permission`, src.`created_at`, src.`modified_at`
FROM `myllm_core_db`.`roles` AS src
WHERE (SELECT COUNT(*) FROM `laim_roles`) = 0
  AND EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'myllm_core_db' AND table_name = 'roles'
  );

-- --------------------------------------------------------------------------
-- Catálogo: identity_type_permissions
-- --------------------------------------------------------------------------
INSERT INTO `laim_identity_type_permissions` (
    `id`, `identity_type_id`, `permission_id`, `created_at`
)
SELECT
    src.`id`, src.`identity_type_id`, src.`permission_id`, src.`created_at`
FROM `myllm_core_db`.`identity_type_permissions` AS src
WHERE (SELECT COUNT(*) FROM `laim_identity_type_permissions`) = 0
  AND EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'myllm_core_db' AND table_name = 'identity_type_permissions'
  );

-- --------------------------------------------------------------------------
-- Organización fija «laim» (registro público por defecto)
-- --------------------------------------------------------------------------
INSERT INTO `laim_organizations` (
    `organization_name`, `organization_email`, `organization_tlf`, `active`
)
SELECT 'laim', 'info@laim.app', NULL, 1
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM `laim_organizations`
    WHERE LOWER(`organization_name`) = 'laim'
);

SET FOREIGN_KEY_CHECKS = 1;

-- Permisos de escritura en tablas de auth (refuerzo)
GRANT SELECT, INSERT, UPDATE, DELETE ON `laim_core_db`.`laim_users` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE ON `laim_core_db`.`laim_sessions` TO 'laim_writer'@'localhost';
GRANT INSERT ON `laim_core_db`.`laim_auth_logs` TO 'laim_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE ON `laim_core_db`.`laim_user_contact_info` TO 'laim_writer'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_low_level_permissions` TO 'laim_writer'@'localhost';
GRANT SELECT ON `laim_core_db`.`laim_organizations` TO 'laim_writer'@'localhost';
FLUSH PRIVILEGES;

-- ============================================================================
-- 020_individual_accounts_and_org_acronym.sql
-- Cuentas individuales (sin org sombra) + acrónimo de organización.
-- Solo myllm_core_db. No toca laim_core_db.
-- ============================================================================

USE myllm_core_db;

-- Acrónimo cosmético de login (generado por la aplicación)
ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS organization_acronym VARCHAR(32) NULL
  AFTER organization_name;

-- Backfill: slug [a-z0-9] del nombre
UPDATE organizations
SET organization_acronym = LOWER(
    REGEXP_REPLACE(REPLACE(REPLACE(organization_name, '_', ''), ' ', ''), '[^a-zA-Z0-9]', '')
)
WHERE organization_acronym IS NULL OR organization_acronym = '';

-- Rellenar slugs cortos repitiendo la base hasta ≥ 5 (ong → ongong)
UPDATE organizations
SET organization_acronym = REPEAT(
    organization_acronym,
    CEILING(5 / CHAR_LENGTH(organization_acronym))
)
WHERE organization_acronym IS NOT NULL
  AND organization_acronym <> ''
  AND CHAR_LENGTH(organization_acronym) < 5;

-- Reservados: no usar admin/system/internal/laim/personal/www/getmylllm
UPDATE organizations
SET organization_acronym = CONCAT(organization_acronym, '2')
WHERE organization_acronym IN (
    'admin', 'system', 'internal', 'laim', 'personal', 'www', 'getmylllm'
);

ALTER TABLE organizations
  ADD UNIQUE KEY IF NOT EXISTS uq_organizations_acronym (organization_acronym);

-- Usuarios individuales: organization_id NULL (sin org sombra)
ALTER TABLE users DROP FOREIGN KEY IF EXISTS users_ibfk_1;
ALTER TABLE users MODIFY organization_id INT NULL;
ALTER TABLE users
  ADD CONSTRAINT users_ibfk_1
  FOREIGN KEY (organization_id) REFERENCES organizations (organization_id);

ALTER TABLE users DROP INDEX IF EXISTS user_name;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS login_scope_key VARCHAR(80) AS (
    IF(
      organization_id IS NULL,
      CONCAT('ind:', user_name),
      CONCAT('org:', organization_id, ':', user_name)
    )
  ) STORED;

ALTER TABLE users
  ADD UNIQUE KEY IF NOT EXISTS uq_users_login_scope (login_scope_key);

-- Email único global (los mocks duplicados se corrigen en JSON)
ALTER TABLE users
  ADD UNIQUE KEY IF NOT EXISTS uq_users_email (user_email);

-- Sesiones de individuales
ALTER TABLE sessions DROP FOREIGN KEY IF EXISTS sessions_ibfk_2;
ALTER TABLE sessions MODIFY organization_id INT NULL;
ALTER TABLE sessions
  ADD CONSTRAINT sessions_ibfk_2
  FOREIGN KEY (organization_id) REFERENCES organizations (organization_id)
  ON DELETE CASCADE;

-- Tipo 6: Usuario individual
UPDATE identity_types
SET identity_type_name = 'Usuario individual',
    identity_type_rol = 'Individual User'
WHERE identity_type_id = 6;

UPDATE roles
SET identity_type_name = 'Usuario individual',
    identity_type_rol = 'Individual User'
WHERE identity_type_id = 6;

-- Permisos tipo 6: como admin de org, sin user_* ni training_*
INSERT INTO low_level_permissions (
    id_permissions,
    folder_create, folder_delete, folder_rename, folder_read,
    file_create, file_read, file_update, file_delete,
    project_create, project_read, project_update, project_delete,
    version_create, version_read, version_update, version_delete,
    training_create, training_read, training_update, training_delete,
    training_start, training_stop,
    parameters_create, parameters_read, parameters_update, parameters_delete,
    notifications_create, notifications_read, notifications_update, notifications_delete,
    user_create, user_read, user_update, user_delete, user_enable, user_disable,
    folder_list, file_list, project_list, version_list
) VALUES (
    6,
    1, 1, 1, 1,
    1, 1, 0, 1,
    1, 1, 1, 0,
    1, 1, 1, 0,
    0, 0, 0, 0,
    0, 0,
    0, 0, 0, 0,
    1, 1, 0, 1,
    0, 0, 0, 0, 0, 0,
    1, 1, 1, 1
)
ON DUPLICATE KEY UPDATE
    folder_create = VALUES(folder_create),
    folder_delete = VALUES(folder_delete),
    folder_rename = VALUES(folder_rename),
    folder_read = VALUES(folder_read),
    file_create = VALUES(file_create),
    file_read = VALUES(file_read),
    file_update = VALUES(file_update),
    file_delete = VALUES(file_delete),
    project_create = VALUES(project_create),
    project_read = VALUES(project_read),
    project_update = VALUES(project_update),
    project_delete = VALUES(project_delete),
    version_create = VALUES(version_create),
    version_read = VALUES(version_read),
    version_update = VALUES(version_update),
    version_delete = VALUES(version_delete),
    training_create = 0,
    training_read = 0,
    training_update = 0,
    training_delete = 0,
    training_start = 0,
    training_stop = 0,
    notifications_create = VALUES(notifications_create),
    notifications_read = VALUES(notifications_read),
    notifications_delete = VALUES(notifications_delete),
    user_create = 0,
    user_read = 0,
    user_update = 0,
    user_delete = 0,
    user_enable = 0,
    user_disable = 0,
    folder_list = VALUES(folder_list),
    file_list = VALUES(file_list),
    project_list = VALUES(project_list),
    version_list = VALUES(version_list);

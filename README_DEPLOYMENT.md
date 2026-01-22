# Despliegue

Guía rápida de despliegue y verificación para entornos locales o servidores.

## Verificación de carga en MariaDB

Ejecuta el script de inicialización y revisa los conteos por tabla:

```bash
/usr/local/opt/mariadb@10.6/bin/mysql -u root -p'RootP@ssw0rd2026' --database=myllm_core_db --init-command="SET @users_json_path='/ruta/a/users.json'; SET @permissions_json_path='/ruta/a/basic_permissions.json'; SET @low_level_permissions_json_path='/ruta/a/low_level_permisions.json'; SET @roles_json_path='/ruta/a/roles.json'; SET @organizations_json_path='/ruta/a/organizations.json'; SET @manage_roles_json_path='/ruta/a/manage_roles_by_org.json'; SET @sessions_json_path='/ruta/a/sessions.json';" < /ruta/a/init_myllm_core_db.sql
```

Bloque de verificación (incluido en el script):

```sql
SELECT 'permissions' AS table_name, COUNT(*) AS total FROM permissions
UNION ALL
SELECT 'low_level_permissions', COUNT(*) FROM low_level_permissions
UNION ALL
SELECT 'identity_types', COUNT(*) FROM identity_types
UNION ALL
SELECT 'identity_type_permissions', COUNT(*) FROM identity_type_permissions
UNION ALL
SELECT 'organizations', COUNT(*) FROM organizations
UNION ALL
SELECT 'users', COUNT(*) FROM users
UNION ALL
SELECT 'user_contact_info', COUNT(*) FROM user_contact_info
UNION ALL
SELECT 'user_billing_info', COUNT(*) FROM user_billing_info
UNION ALL
SELECT 'user_organization_management', COUNT(*) FROM user_organization_management
UNION ALL
SELECT 'sessions', COUNT(*) FROM sessions
UNION ALL
SELECT 'auth_logs', COUNT(*) FROM auth_logs;
```

## Estructura de base de datos (referencia viva)

Este apartado documenta las tablas principales del core. Se irá actualizando
cuando se incorporen nuevas funcionalidades o entidades.
Cada cambio en la estructura debe reflejarse aquí (nuevas tablas, columnas
o relaciones), junto con la fecha y una nota breve del motivo.

### Tablas actuales

- `permissions`: catálogo de permisos básicos.
- `low_level_permissions`: permisos de bajo nivel asociados 1 a 1 con `permissions`.
- `identity_types`: tipos de identidad y roles.
- `identity_type_permissions`: relación **1 a 1** entre tipos de identidad y permisos (claves únicas por `identity_type_id` y `permission_id`).
- `organizations`: organizaciones registradas.
- `users`: usuarios registrados.
- `user_contact_info`: información de contacto por usuario.
- `user_billing_info`: información de facturación por usuario.
- `user_organization_management`: relación usuario-organización y estado.
- `sessions`: sesiones activas/inactivas para auditoría y seguridad.
- `auth_logs`: auditoría de login/logout y eventos de autenticación.

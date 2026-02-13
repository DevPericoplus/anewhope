# Agent Instructions for Anewhope Project

## Database Connection

To connect to the MariaDB database, read credentials from `protected_values.py`:

```bash
# Credentials are in infrastructure/environments/<env>/protected_values.py
# Variables: mariadb_admin_user, mariadb_admin_password
/usr/local/opt/mariadb@10.6/bin/mariadb -u <mariadb_admin_user> -p'<mariadb_admin_password>'
```

For non-interactive queries, use heredoc:

```bash
/usr/local/opt/mariadb@10.6/bin/mariadb -u <mariadb_admin_user> -p'<mariadb_admin_password>' << 'EOF'
USE myllm_projects_db;
SHOW TABLES;
EOF
```

## Database Schema Notes

- **Database name**: `myllm_projects_db`
- **Admin user**: see `mariadb_admin_user` / `mariadb_admin_password` in `protected_values.py`
- **App user** (used by backend): see `mariadb_writer_user` / `mariadb_writer_password` in `protected_values.py`
- **Credentials location**: `infrastructure/environments/<environment>/protected_values.py` (gitignored)

## Important Tables

- `versiones`: Project versions (requires `fecha_lanzamiento`, `descripcion`)
- `estado`: Version workflow states (all boolean flags for stages)
- `cambios`: Version change history (requires `fecha_cambio`, `tipo_cambio`, `descripcion`)
- `proyectos`: Projects table
- `tecnologia`: Technology catalog
- `tickets`: Support tickets
- `flujos`: Workflow definitions

## Common Database Queries

```sql
-- Show all tables
SHOW TABLES;

-- Describe a table structure
DESCRIBE table_name;

-- Check tables by pattern
SHOW TABLES LIKE '%pattern%';
```

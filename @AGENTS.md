# Agent Instructions for Anewhope Project

## Database Connection

To connect to the MariaDB database, use:

```bash
/usr/local/opt/mariadb@10.6/bin/mariadb -u myllm_admin -p'Us3r@dminP@ss'
```

For non-interactive queries, use heredoc:

```bash
/usr/local/opt/mariadb@10.6/bin/mariadb -u myllm_admin -p'Us3r@dminP@ss' << 'EOF'
USE myllm_projects_db;
SHOW TABLES;
EOF
```

## Database Schema Notes

- **Database name**: `myllm_projects_db`
- **Admin user**: `myllm_admin` / `Us3r@dminP@ss`
- **App user** (used by backend): `myllm_app_user` / `pass@2024.DesApp`

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

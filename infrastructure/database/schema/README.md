# Database Schema - myllm

Schema canónico de las bases de datos MariaDB del proyecto, exportado desde el entorno PRE.

## Ficheros

| Fichero | Contenido | Origen |
|---|---|---|
| `000_create_myllm_core_db.sql` | 14 tablas + 7 vistas (auth, users, orgs, sessions, permissions) | PRE mysqldump |
| `000_create_myllm_projects_db.sql` | 50 tablas + 11 triggers + 12 vistas (proyectos, entrenamientos, jobs, tickets) | PRE mysqldump |
| `000_create_routines.sql` | 1 función + 4 stored procedures | PRE dump + migrations |

## Flujos de Inicialización

### 1. Schema-only (entorno nuevo sin datos)

Para crear las bases de datos vacías con toda la estructura:

```bash
# Opción A: Manual (macbook)
mariadb -u root -p'<password>' < infrastructure/database/schema/000_create_myllm_core_db.sql
mariadb -u root -p'<password>' < infrastructure/database/schema/000_create_myllm_projects_db.sql
mariadb -u root -p'<password>' < infrastructure/database/schema/000_create_routines.sql

# Opción B: Con Ansible (entornos remotos)
./deploy_custom.sh --env dev --server backend --tags mariadb,users,schema-init
```

### 2. Full dump (clonar datos de otro entorno)

Para copiar estructura + datos desde macbook:

```bash
# 1. Exportar desde macbook
cd /Users/administrator/develop/anh_ansible_environments
./scripts/export_mariadb_from_macbook.sh dev

# 2. Migrar al entorno destino
ansible-playbook -i env/dev/host migrate_mariadb.yml -e deploy_env=dev
```

### 3. Actualización incremental

Para aplicar migraciones nuevas sobre un entorno existente:

```bash
./deploy_custom.sh --env dev --server backend --tags code,migrations
```

## Conteos Esperados (referencia PRE)

| Objeto | myllm_core_db | myllm_projects_db |
|---|---|---|
| Tablas (BASE TABLE) | 14 | 50 |
| Vistas (VIEW) | 7 | 12 |
| Triggers | 0 | 11 |
| Routines (SP + FN) | 0 | 5 |

## Otras Bases de Datos

### Redis (schema-less)

- **Uso:** Sesiones Reflex (frontend/backoffice) con TTL automático
- **Configuración:** Password en `env/<entorno>/frontend.yml` → `redis_password`
- **Puerto:** 6379
- **No requiere schema:** Las claves se crean/expiran automáticamente
- **Instalación:** Automática por el playbook `frontend.yml` con tag `redis`

### ChromaDB (schema-less)

- **Uso:** Almacenamiento de embeddings para RAG
- **Puerto:** 8100
- **No requiere schema:** Las colecciones se crean dinámicamente durante el entrenamiento
- **Convención de nombres:** `ORG{id}_PRJ{id}_v{ver}_ENT{id}_SEQ{seq}`
- **Migración:** `migrate_chromadb.yml` para copiar colecciones entre entornos
- **Instalación:** Automática por el playbook `trainer.yml` con tag `chromadb`

## Matriz de Uso por Escenario

| Escenario | Comando |
|---|---|
| Entorno nuevo (sin datos) | `./deploy_custom.sh --env <env> --server backend --tags mariadb,users,schema-init` |
| Clonar entorno (con datos) | `export_mariadb_from_macbook.sh <env>` + `migrate_mariadb.yml` |
| Actualización incremental | `./deploy_custom.sh --env <env> --server backend --tags code,migrations` |
| Exportar schema de PRE | `./scripts/export_mariadb_schema.sh pre --to-anewhope` |
| Redis | Sin acción - instalación automática por playbook, sesiones con TTL |
| ChromaDB | Sin acción - colecciones creadas dinámicamente por el trainer |

## Actualizar Schema Canónico

Cuando PRE tenga cambios de estructura (nuevas tablas, columnas, etc.):

```bash
cd /Users/administrator/develop/anh_ansible_environments
./scripts/export_mariadb_schema.sh pre --to-anewhope
```

Esto sobreescribe los ficheros de schema con la estructura actual de PRE.

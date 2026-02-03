# Anewhope

Proyecto para gestionar infraestructura, aplicaciones y flujos de personalización de modelos LLM.

## Estructura principal

- `info.txt`: guía rápida para crear y activar el entorno virtual, además de notas de operación.
- `infrastructure/environments/<entorno>/protected_values.py`: variables sensibles por entorno.
- `README_DEPLOYMENT.md`: guía de despliegue con verificación SQL y estructura de base de datos.
- `src/`: monorepo con organización hexagonal y dominios compartidos.
  - `main.py`: punto de entrada central para orquestar servicios.
  - `config/`: configuración compartida.
  - `tests/`: pruebas comunes.
  - `1_shared_domain/`: entidades y reglas de negocio reutilizables.
    - `entities/`
    - `business_rules/`
  - `2_shared_application/`: contratos y DTOs compartidos.
    - `interfaces/`
    - `dtos/`
    - `security/`: librería de utilidades criptográficas y secretos (`custom_cipher_lib.py`, `basesecuritypass.json`).
  - `apps/`: implementaciones específicas por servicio.
    - `3_backend/`: API REST principal (gestión y orquestación).
      - `1_domain/`
      - `2_application/`
      - `3_adapters/` (incluye `controllers/` y `mappers/`)
      - `4_infrastructure/` (`persistence/`, `web/`)
    - `4_trainer/`: servicio de entrenamiento y fine-tuning.
      - `1_domain/`
      - `2_application/`
      - `3_adapters/` (`controllers/`)
      - `4_infrastructure/` (`gpu_processor/`, `web/`)
    - `5_web_frontend/`: cliente web basado en Reflex.
      - `__init__.py`
      - `frontend_reflex/` (`__init__.py`, `components/`, `pages/`)
      - `adapters/` (`api_client.py`)
- `monorepo_llm_personalizado/`: estructura de referencia en español utilizada para planificar la migración a `src/`.
- `infrastructure/`: scripts y utilidades adicionales (pendiente de completar).
- `test/`: pruebas heredadas o de exploración.

## Configuración por entorno

### Estructura de configuración

El proyecto soporta configuración personalizada por entorno usando cuatro niveles de archivos:

1. **`.envglobal`** (raíz del proyecto): Define el entorno activo globalmente
   ```
   # Configuración global del entorno
   current_environment: macbook
   ```
   Este archivo es la fuente principal para determinar qué entorno usar. Copia `.envglobal.example` 
   a `.envglobal` y modifica el valor según tu entorno de trabajo.

2. **`.env`** (raíz del proyecto): Variables de entorno adicionales (opcional)
   Puede sobrescribir el entorno definido en `.envglobal`:
   ```
   ENVIRONMENT=macbook
   ```

3. **`infrastructure/environments/<entorno>/env.yaml`**: Variables públicas y comunes
   - `storage_mode`: modo de almacenamiento (`mock`, `mock_and_db`, `db_only`)
   - `active_sync_db_jsons`: habilita/deshabilita sincronización DB→JSON (`"1"` o `"0"`)
   - `sync_database_interval_seconds`: intervalo de sincronización en segundos
   - Variables de aplicaciones (host y puerto por cada aplicación)
   - URLs de servicios internos (broker, core, middleware, fmanagement, trainer)
   - Configuración de Redis para sesión compartida

4. **`infrastructure/environments/<entorno>/protected_values.py`**: Variables sensibles
   - Credenciales de MariaDB
   - Secrets JWT
   - Claves de encriptación
   - Tokens de servicios externos

### Entornos disponibles

| Entorno | Descripción | Plataforma | Dominio interno | Dominio público |
|---------|-------------|------------|-----------------|-----------------|
| `macbook` | Desarrollo local | macOS 14.8.1 | localhost | localhost |
| `dev` | Desarrollo en servidor | Oracle Linux 10 (VirtualBox) | house.loc | house.loc |
| `pre` | Preproducción | Oracle Linux 10 (AWS) | anewhope.aws | getmyllm.com |
| `pro` | Producción | Oracle Linux 10 (AWS) | anewhope.aws | getmyllm.com |

**Nota sobre dominios en pre/pro:**
- **Dominio público (`getmyllm.com`):** Utilizado solo por nginx para exponer el frontend al exterior.
- **Dominio interno (`anewhope.aws`):** Utilizado para la comunicación entre servicios dentro de AWS.

### Variables de aplicaciones en servidores

Cada archivo `env.yaml` define las variables de host y puerto para cada aplicación. Esto permite
que las aplicaciones conozcan la ubicación de los otros servicios en cada entorno.

**Regla de puertos:** `8000 + primer dígito del nombre de la carpeta de la aplicación`

| Aplicación | Carpeta | Puerto | Variable host | Variable puerto |
|------------|---------|--------|---------------|-----------------|
| Backend Core | `3_backend` | 8003 | `backend_core_host` | `backend_core_port` |
| Trainer (Backend IA) | `4_trainer` | 8004 | `trainer_host` | `trainer_port` |
| Web Frontend | `5_web_frontend` | 8005 | `frontend_host` | `frontend_port` |
| Web Backoffice | `6_web_backoffice` | 8006 | `backoffice_host` | `backoffice_port` |
| Middleware | `7_service_frontend` | 8007 | `middleware_host` | `middleware_port` |
| Broker | `8_service_backend` | 8008 | `broker_host` | `broker_port` |
| Fmanagement | API Go | 1666 | `fmanagement_host` | `fmanagement_port` |

**Distribución de aplicaciones en servidores por entorno (dominio interno):**

| Entorno | Servidor Frontend | Servidor Backend | Servidor Trainer |
|---------|-------------------|------------------|------------------|
| macbook | localhost | localhost | localhost |
| dev | frontend.house.loc | backend.house.loc | trainer.house.loc |
| pre | frontend.anewhope.aws | backend.anewhope.aws | trainer.anewhope.aws |
| pro | frontend.anewhope.aws | backend.anewhope.aws | trainer.anewhope.aws |

**Aplicaciones por servidor:**

- **Servidor Frontend:** `5_web_frontend`, `6_web_backoffice`, `7_service_frontend`, Redis
- **Servidor Backend:** `3_backend`, `8_service_backend`, Fmanagement, MariaDB
- **Servidor Trainer:** `4_trainer`, Ollama (IA local), base de datos vectorial (Keras - pendiente)

### Endpoint de Consulta de Entorno Activo

El sistema expone endpoints para consultar el entorno activo en tiempo de ejecución.
Esto permite a los servicios (especialmente fmanagement en Go) configurarse dinámicamente.

**Endpoints disponibles:**

| Servicio | Endpoint | Puerto | Uso |
|----------|----------|--------|-----|
| Broker | `GET /config/environment` | 8008 | Fuente primaria del entorno |
| Backend Core | `GET /config/environment` | 8003 | Usado por fmanagement |

**Respuesta JSON:**

```json
{
    "environment": "macbook",
    "source": "ENVIRONMENT"
}
```

**Valores de entorno posibles:** `macbook`, `dev`, `pre`, `pro`

**Flujo de consulta para fmanagement:**

```
┌─────────────┐       GET /config/environment       ┌──────────────┐
│ fmanagement │ ─────────────────────────────────►  │ Backend Core │
│    (Go)     │                                     │   (Python)   │
│ Puerto 1666 │ ◄─────────────────────────────────  │  Puerto 8003 │
└─────────────┘   {"environment": "macbook", ...}   └──────────────┘
```

**Uso en fmanagement (Go) - inicialización:**

```go
// En init() o main()
func getActiveEnvironment() string {
    resp, err := http.Get("http://localhost:8003/config/environment")
    if err != nil {
        return "unknown"
    }
    defer resp.Body.Close()
    
    var result struct {
        Environment string `json:"environment"`
    }
    json.NewDecoder(resp.Body).Decode(&result)
    return result.Environment
}

// Uso para configurar rutas base
env := getActiveEnvironment()
switch env {
case "macbook":
    basePath = "/Users/administrator/develop/anewhope/data"
case "dev", "pre", "pro":
    basePath = "/data/files/external"
}
```

**Uso en Python (Backend Core/Broker):**

```python
import os

# Directamente desde variable de entorno
environment = os.environ.get("ENVIRONMENT", "unknown")
```

### Cómo obtener URLs de servicios en código

Las aplicaciones deben usar `get_env_value()` del módulo `env_settings.py` para obtener las URLs
de otros servicios. Esto garantiza que las variables de `env.yaml` se carguen correctamente
según el entorno activo.

**Ejemplo correcto:**

```python
# Cargar el módulo de configuración (carga dinámica por nombre numérico)
from src.2_shared_application.config import env_settings

def _get_middleware_base_url() -> str:
    """Obtiene la URL del middleware con prioridad correcta."""
    return env_settings.get_env_value("MIDDLEWARE_BASE_URL", "http://localhost:8007")
```

**Orden de prioridad al resolver valores:**

1. Variable de entorno explícita (definida con `export VARIABLE=valor`)
2. Valor en `env.yaml` del entorno activo (definido por `.envglobal`)
3. Valor por defecto proporcionado al llamar `get_env_value()`

**Variables de URL típicas:**

| Variable | Uso | Valor en macbook |
|----------|-----|------------------|
| `MIDDLEWARE_BASE_URL` | Frontend/Backoffice → Middleware | `http://localhost:8007` |
| `BROKER_BACKEND_BASE_URL` | Middleware → Broker | `http://localhost:8008` |
| `CORE_BACKEND_BASE_URL` | Broker → Backend Core | `http://localhost:8003` |
| `TRAINER_BACKEND_BASE_URL` | Broker → Trainer | `http://localhost:8004` |
| `FMANAGEMENT_BASE_URL` | Backend Core → Fmanagement | `http://localhost:1666` |

### Servicios planificados en el servidor Trainer

El servidor trainer albergará los siguientes servicios:

| Servicio | Puerto | Descripción | Estado |
|----------|--------|-------------|--------|
| `4_trainer` | 8004 | Backend IA - gestiona entrenamientos y uso de modelos | Implementado |
| Ollama | 11434 | Servidor de modelos LLM locales | Planificado |
| Base de datos vectorial | Por definir | Almacenamiento de embeddings (Keras/Chroma) | Pendiente diseño |

**Flujo de comunicación:**
```
Broker (8008) → 4_trainer (8004) → Ollama (11434)
                     ↓
              BD Vectorial
```

### Variables protegidas por entorno (protected_values.py)

Cada entorno tiene su archivo `protected_values.py` con credenciales y URLs internas:

| Variable | macbook | dev | pre/pro |
|----------|---------|-----|---------|
| `mariadb_host` | localhost | backend.house.loc | backend.anewhope.aws |
| `broker_backend_base_url` | http://localhost:8008 | http://backend.house.loc:8008 | http://backend.anewhope.aws:8008 |
| `core_backend_base_url` | http://localhost:8003 | http://backend.house.loc:8003 | http://backend.anewhope.aws:8003 |
| `mariadb_cli_path` | /usr/local/opt/mariadb@10.6/bin/mysql | /usr/bin/mariadb | /usr/bin/mariadb |

**Importante:** En producción (`pro`), todas las contraseñas y claves JWT deben cambiarse antes del despliegue.

### Orden de carga y prioridad

Las aplicaciones cargan la configuración en este orden:

1. **`.envglobal`** → Define el entorno base (`current_environment`)
2. **`.env`** → Puede sobrescribir con `ENVIRONMENT=<entorno>`
3. **`env.yaml`** del entorno → Variables públicas
4. **`protected_values.py`** del entorno → Variables sensibles

**Prioridad para determinar el entorno:**
1. Variable de entorno `ENVIRONMENT` (definida en `.env` o shell)
2. `current_environment` en `.envglobal`
3. Valor por defecto: `macbook`

### Uso en código

Todas las aplicaciones deben usar el helper centralizado para cargar configuración:

```python
from src.2_shared_application.config.env_settings import (
    get_environment_name,
    get_env_value,
    get_protected_value,
    get_environment_paths,
    load_protected_settings,
    print_environment_info,
)

# Obtener el entorno activo
env = get_environment_name()  # "macbook", "dev", "pre", "pro"

# Leer variable pública
storage_mode = get_env_value("storage_mode", "mock")

# Leer variable sensible
db_password = get_protected_value("writer_password")

# Obtener todas las rutas de configuración
paths = get_environment_paths()
# paths = {
#     "root": Path("/Users/.../anewhope"),
#     "env_yaml": Path(".../infrastructure/environments/macbook/env.yaml"),
#     "protected_values": Path(".../infrastructure/environments/macbook/protected_values.py"),
#     "envglobal": Path(".../anewhope/.envglobal"),
#     "environment": "macbook"
# }

# Diagnóstico de configuración (útil para debugging)
print_environment_info()
# Output:
# Entorno activo: macbook
#   Root: /Users/.../anewhope
#   env.yaml: .../env.yaml (existe: True)
#   protected_values: .../protected_values.py (existe: True)
#   .envglobal: .../anewhope/.envglobal (existe: True)

# O cargar todos los valores protegidos
settings = load_protected_settings()
```

### Exportador de variables

Para generar un archivo de variables de entorno compatible con scripts shell o Docker:

```bash
# Formato shell
python infrastructure/export_env.py --environment macbook

# Formato envfile para Docker
python infrastructure/export_env.py --environment macbook --format envfile
```

## Entornos y plataformas

- `macbook`: desarrollo local en macOS 14.8.1 (equipo único que asume util01, frontend, backend, trainer).
- `dev`: virtualización en VirtualBox con Oracle Linux 10 (util01, frontend, backend, trainer).
- `pre` y `pro`: instancias en AWS con Oracle Linux 10 (util01, frontend, backend, trainer).

## Infraestructura de almacenamiento y datos

El proyecto utiliza una estructura de carpetas específica para organizar logs, datos de clientes, modelos generados y persistencia de bases de datos.

### Estructura base por entorno

| Entorno | Ruta base | Descripción |
|---------|-----------|-------------|
| **macbook** | `~/data/anewhope/files/` | Desarrollo local con subdirectorios por tipo de servidor |
| **dev/pre/pro** | `/data/` | Producción - cada servidor tiene su propia estructura en `/data/` |

### Organización por servidor

**Backend Server** (`backend.house.loc` / `backend.anewhope.aws`):
```
/data/
├── backend_core/logs/       # Logs de backend_core (puerto 8003)
├── service_backend/logs/    # Logs de broker (puerto 8008)
├── fmanagement/logs/        # Logs de fmanagement (puerto 1666)
├── external/                # Contenido de clientes (ORG####/PRJ#####/v###/)
├── internal/                # Contenido generado (models/, reports/)
├── Mariadb/                 # Persistencia de MariaDB
└── images/                  # Imágenes Docker (tar.gz)
```

**Frontend Server** (`frontend.house.loc` / `frontend.anewhope.aws`):
```
/data/
├── frontend/logs/           # Logs de frontend (puerto 8005)
├── backoffice/logs/         # Logs de backoffice (puerto 8006)
├── middleware/logs/         # Logs de middleware (puerto 8007)
├── persistence/redis/       # Persistencia de Redis
└── images/                  # Imágenes Docker (tar.gz)
```

**Trainer Server** (`trainer.house.loc` / `trainer.anewhope.aws`):
```
/data/
├── backend_ia/logs/         # Logs de backend_ia (puerto 8004)
├── external/                # Contenido sincronizado desde backend
├── internal/                # Modelos y reports generados
├── persistence/chroma/      # Persistencia de Chroma DB (vectorial)
└── images/                  # Imágenes Docker (tar.gz)
```

### External vs Internal

| Carpeta | Contenido | Acceso | Sincronización |
|---------|-----------|--------|----------------|
| **external** | Documentos/imágenes de clientes | Frontend → fmanagement → Backend | Backend → Trainer (bajo demanda con `transferversion`) |
| **internal** | Modelos LLM y reportes generados | Solo sistema | Trainer → Backend (automático cada 5 min) |

**Estructura de external:**
- Jerarquía: `ORG####/PRJ#####/v###/` (los usuarios pueden crear cualquier estructura dentro de cada versión)
- Ejemplo: `external/ORG0001/PRJ00001/v001/images/logo.png`

**Estructura de internal:**
- Carpetas fijas: `models/` y `reports/`
- Jerarquía: `ORG####/PRJ#####/v###/` (igual que external)
- Ejemplo: `internal/models/ORG0001/PRJ00001/v001/model_llm.tar.gz`
- Ejemplo: `internal/reports/ORG0001/PRJ00001/v001/training_report.md`

### Variables de configuración

Todas las rutas se configuran en `infrastructure/environments/{entorno}/fmanagement_paths.yml`:

```yaml
# External (contenido de clientes)
backend_core_base_storage: /data/external              # dev/pre/pro
backend_ia_base_storage: /data/external                # dev/pre/pro

# Internal (contenido generado por sistema)
backend_core_internal_storage: /data/internal
backend_ia_internal_storage: /data/internal
backend_core_models_storage: /data/internal/models
backend_core_reports_storage: /data/internal/reports

# Logs por servicio
backend_core_logs_path: /data/backend_core/logs
frontend_logs_path: /data/frontend/logs
middleware_logs_path: /data/middleware/logs

# Persistencia
mariadb_data_path: /data/Mariadb
redis_data_path: /data/persistence/redis
chroma_data_path: /data/persistence/chroma

# Versiones de imágenes Docker
backend_core_image_version: 1.0.0
frontend_image_version: 1.0.0
```

### Scripts de gestión

| Script | Descripción | Uso |
|--------|-------------|-----|
| `scripts/setup_data_structure.sh` | Crear toda la jerarquía de carpetas | `./scripts/setup_data_structure.sh macbook` |
| `scripts/generate_docker_env.sh` | Generar `.env` desde YAML para docker-compose | `./scripts/generate_docker_env.sh dev backend` |
| `scripts/verify_fmanagement_sync.sh` | Verificar sincronización de configuración | `./scripts/verify_fmanagement_sync.sh` |

**Crear estructura de carpetas:**
```bash
# Desarrollo local (macbook)
./scripts/setup_data_structure.sh macbook

# Producción (ejecutar en cada servidor)
./scripts/setup_data_structure.sh dev backend    # En backend server
./scripts/setup_data_structure.sh dev frontend   # En frontend server
./scripts/setup_data_structure.sh dev trainer    # En trainer server
```

**Generar archivos .env para Docker:**
```bash
# Generar .env para todos los servicios de un servidor
./scripts/generate_docker_env.sh dev backend
# Genera: infrastructure/environments/dev/.env.backend

# Los archivos .env se utilizan en docker-compose.yml:
# docker-compose --env-file .env.backend up -d
```

### Sincronización rsync (dev/pre/pro)

Entre backend y trainer servers se sincroniza contenido automáticamente:

| Contenido | Dirección | Frecuencia |
|-----------|-----------|------------|
| `external/` | Backend → Trainer | Bajo demanda (`transferversion`) |
| `internal/models/` | Trainer → Backend | Automático (cada 5 min) |
| `internal/reports/` | Trainer → Backend | Automático (cada 5 min) |

**Configuración SSH:**
```yaml
# En fmanagement_paths.yml
trainer_ssh_host: trainer.house.loc
trainer_ssh_user: rsync_user
trainer_ssh_key_path: /opt/anewhope/keys/rsync_key
rsync_automatic_interval: 300  # 5 minutos
```

**NO se sincronizan:**
- `logs/` - Cada servidor mantiene sus propios logs
- `persistence/` - Cada base de datos es independiente
- `images/` - Las imágenes Docker son específicas de cada servidor

### Diferencias macbook vs producción

| Aspecto | Macbook | Dev/Pre/Pro |
|---------|---------|-------------|
| Ruta base | `~/data/anewhope/files/{servidor}/` | `/data/` |
| Servidores | 3 subdirectorios en misma máquina | 3 servidores físicos separados |
| Sincronización | No necesaria | rsync over SSH |
| Docker | No se usa (ejecutar con `run.sh`) | docker-compose por servidor |

**Documentación completa:**
- Variables por entorno: `infrastructure/environments/{entorno}/fmanagement_paths.yml`
- Reglas de infraestructura: `AGENTS.md` sección 5.3.1
- Sincronización fmanagement: `infrastructure/environments/README_FMANAGEMENT_SYNC.md`

## Estrategia de Dockerfiles y despliegue

### Dockerfiles por aplicación

Cada aplicación en `src/apps/*` tiene su propio `Dockerfile` y un script `docker_execution.sh` 
que facilita la construcción y ejecución del contenedor:

- `src/apps/3_backend/Dockerfile` y `docker_execution.sh`
- `src/apps/5_web_frontend/Dockerfile` y `docker_execution.sh`
- `src/apps/6_web_backoffice/Dockerfile` y `docker_execution.sh`
- `src/apps/7_service_frontend/Dockerfile` y `docker_execution.sh`
- `src/apps/8_service_backend/Dockerfile` y `docker_execution.sh`

El script `docker_execution.sh` de cada aplicación:
1. Carga las variables de entorno desde `.env` y `env.yaml` del entorno activo
2. Construye la imagen Docker con `docker build`
3. Ejecuta el contenedor exponiendo el puerto fijo de la aplicación

Ejemplo de uso:
```bash
cd src/apps/7_service_frontend
bash docker_execution.sh
```

### Docker Compose por servidor

Los archivos `docker-compose.yml` están organizados por servidor en `infrastructure/servers/*` 
y agrupan los servicios que se ejecutarán juntos en cada servidor:

- `infrastructure/servers/frontend/docker-compose.yml`: `nginx`, `5_web_frontend`, 
  `6_web_backoffice`, `7_service_frontend`
- `infrastructure/servers/backend/docker-compose.yml`: `8_service_backend`, `3_backend`, 
  `fmanagement` (Go API), `mariadb`
- `infrastructure/servers/trainer/docker-compose.yml`: `4_trainer` (Backend IA), 
  `keras_service` (placeholder para servicio Keras)
- `infrastructure/servers/macbook/docker-compose.yml`: solo aplicaciones internas 
  (MariaDB y Keras nativos)

### Servidor frontend (Linux)

- `infrastructure/servers/frontend/docker-compose.yml`: `nginx`, `5_web_frontend`,
  `6_web_backoffice`, `7_service_frontend`.
- Plantilla Nginx para ansible:
  `infrastructure/servers/frontend/nginx/nginx.conf.template`.

### Servidor backend (Linux)

- `infrastructure/servers/backend/docker-compose.yml`: `8_service_backend`,
  `3_backend`, `fmanagement` (imagen externa), `mariadb`.

### Servidor trainer (Linux)

- `infrastructure/servers/trainer/docker-compose.yml`: `4_trainer` (placeholder),
  `keras_service` (placeholder).
- En macOS se instalará TensorFlow CPU en un venv ` .env_trainer` y Keras 2.15
  con TensorFlow 2.15. [Keras getting started](https://keras.io/getting_started/)

### Macbook (local)

- `infrastructure/servers/macbook/docker-compose.yml` solo contiene aplicaciones internas.
- MariaDB se usa nativa (instalada).
- **Redis se usa nativo (instalado con Homebrew)** para sesión compartida.
- Nginx se instala con Homebrew y se configura con:
  `infrastructure/servers/macbook/nginx/nginx.conf`.

#### Redis para sesión compartida

**Instalación en macbook:**

Redis se usa como backend de sesión compartida entre frontend y backoffice, permitiendo que ambas aplicaciones Reflex compartan el state del usuario de forma nativa.

```bash
# Instalar Redis con Homebrew
brew install redis

# Iniciar Redis (automático en cada boot)
brew services start redis

# O iniciar manualmente con configuración específica
redis-server infrastructure/redis/macbook/redis.conf

# O usar configuración por defecto del sistema
redis-server /usr/local/etc/redis.conf

# Verificar estado
./scripts/manage_redis.sh status

# Ver sesiones activas
./scripts/monitor_redis_sessions.py

# Monitoreo continuo
./scripts/monitor_redis_sessions.py --continuous
```

**Configuración:**

Redis está configurado con:
- **Host**: `localhost` (solo conexiones locales)
- **Puerto**: `6379` (estándar)
- **Base de datos**: `0` (compartida entre frontend y backoffice)
- **Password**: Almacenado en `protected_values.py` de cada entorno
- **Persistencia AOF**: Activada para durabilidad de datos
- **TTL sesiones**: 3600 segundos (1 hora, configurable en `env.yaml`)
- **Archivo de configuración**: `infrastructure/redis/macbook/redis.conf`

**Variables de configuración:**

En `infrastructure/environments/<entorno>/env.yaml`:
```yaml
redis_host: localhost
redis_port: "6379"
redis_db: "0"
redis_token_expiration: "3600"
redis_lock_expiration: "10000"
redis_lock_warning_threshold: "1000"
```

En `infrastructure/environments/<entorno>/protected_values.py`:
```python
redis_password = "PassRedis2025"
```

**Gestión del servicio:**

```bash
# Script de gestión
./scripts/manage_redis.sh {install|start|stop|restart|status|cli|flush|sessions|monitor}

# Ejemplos
./scripts/manage_redis.sh install    # Instalar Redis
./scripts/manage_redis.sh start      # Iniciar servicio
./scripts/manage_redis.sh status     # Ver estado
./scripts/manage_redis.sh sessions   # Listar sesiones activas
./scripts/manage_redis.sh cli        # Abrir Redis CLI
```

**Arquitectura de sesión compartida:**

```
┌─────────────┐         ┌──────────────┐
│   Frontend  │←────────┤  Redis Server│
│  (Puerto    │  State  │  (Puerto     │
│   8005)     │ Shared  │   6379)      │
└─────────────┘         └──────────────┘
                              ↑
┌─────────────┐               │
│  Backoffice │───────────────┘
│  (Puerto    │    State Shared
│   8006)     │
└─────────────┘
```

Ambas aplicaciones (frontend y backoffice) comparten automáticamente:
- Datos del usuario
- Permisos de bajo nivel
- Tokens JWT
- Estado de navegación

**Monitoreo:**

```bash
# Ver todas las sesiones en tiempo real
./scripts/monitor_redis_sessions.py

# Salida ejemplo:
# 📊 MONITOR DE SESIONES REDIS - 2026-01-26 10:30:15
# ✅ Sesiones activas: 2
# 
# 🔑 Session Key: reflex:session:abc123...
# ⏱️  TTL: 3456 segundos (57 minutos)
# 👤 Usuario:
#    ID: 1
#    Nombre: adminone
#    Email: adminone@tfmmyllm.ai
# 🔐 Permisos Críticos:
#    training_create: ✅
# 🔧 Acceso Backoffice: ✅ SÍ
```

**Limpieza de sesiones:**

```bash
# Limpiar sesiones expiradas manualmente
./scripts/monitor_redis_sessions.py --cleanup

# Limpiar TODAS las sesiones (⚠️ CUIDADO)
redis-cli -a $(grep redis_password infrastructure/environments/macbook/protected_values.py | cut -d'"' -f2) FLUSHALL
```

**Documentación completa:**
- **ADRs (Decisiones arquitectónicas):**
  - `src/docs/stack_of_technologies.adr` - ADR: Sesión Compartida Frontend/Backoffice usando Redis
  - `src/docs/stack_of_technologies.adr` - ADR: Compatibilidad Redis 5.2.1 con Reflex 0.8.25
- **Implementación técnica:**
  - Implementación: `docs/REDIS_IMPLEMENTATION.md`
  - Estado de implementación: `docs/REDIS_IMPLEMENTATION_STATUS.md`
  - **Despliegue Docker (dev/pre/pro):** `docs/REDIS_DOCKER_DEPLOYMENT.md` ✅ NUEVO
  - Diseño de conmutación: `docs/SWITCHING_DESIGN.md`
  - Guía de instalación macbook: `infrastructure/redis/macbook/INSTALATION_GUIDE.md`
  - Configuraciones por entorno: `infrastructure/redis/{macbook,dev,pre,pro}/`
  - **Docker Compose:** `infrastructure/servers/frontend/docker-compose.yml` ✅ ACTUALIZADO
  - **Guía servidor frontend:** `infrastructure/servers/frontend/README.md` ✅ NUEVO
- **Código:**
  - **Estado compartido:** `src/2_shared_application/reflex_shared/shared_session_state.py`
  - Tests de integración: `src/apps/{5_web_frontend,6_web_backoffice}/tests/test_redis_integration.py`
- **Automatización Docker:**
  - Scripts por entorno: `infrastructure/redis/{dev,pre,pro}/build_and_run_docker.sh` ✅ NUEVO
  - Dockerfiles: `infrastructure/redis/{dev,pre,pro}/Dockerfile` ✅ NUEVO

**SharedSessionState:**

El estado de sesión se gestiona mediante la clase `SharedSessionState` que hereda de `rx.State`:

```python
from src.2_shared_application.reflex_shared import SharedSessionState

class FrontendState(SharedSessionState):
    """Hereda automáticamente 13 campos de usuario, 45 permisos, tokens JWT y metadata."""
    pass
```

**Características:**
- ✅ 13 campos de usuario (`user_id`, `organization_id`, `user_name`, `user_email`, etc.)
- ✅ 45 permisos de bajo nivel (`can_data_read`, `can_folder_create`, `can_training_create`, etc.)
- ✅ 2 tokens JWT (`access_token`, `session_token`)
- ✅ 4 campos de metadata (`session_id`, `login_time`, `last_activity`, `current_app`)
- ✅ Métodos: `load_user_data()`, `clear_session()`, `go_to_backoffice()`, `go_to_frontend()`, `logout()`
- ✅ Propiedades: `can_access_backoffice`, `user_display_name`, `user_display_email`

**Ejemplos de uso:**
- Frontend: `docs/examples/frontend_state_with_shared_session.py`
- Backoffice: `docs/examples/backoffice_state_with_shared_session.py`
- **Validación de permisos en UI:** `docs/examples/permission_validation_example.py`

**Validación de permisos en componentes UI:**

Los permisos de bajo nivel (`low_level_permissions`) están disponibles como campos booleanos
en el estado compartido. Ejemplo para mostrar/ocultar una opción de "Renombrar carpeta":

```python
# En un componente Reflex
def folder_context_menu(state):
    return rx.menu.content(
        # La opción solo se muestra si el usuario tiene permiso folder_rename
        rx.cond(
            state.can_folder_rename,  # ← Permiso cargado desde sesión/JWT
            rx.menu.item("Renombrar carpeta", on_click=state.rename_folder),
            rx.fragment(),  # No renderiza nada si no tiene permiso
        ),
        rx.cond(
            state.can_folder_delete,
            rx.menu.item("Eliminar carpeta", on_click=state.delete_folder),
            rx.fragment(),
        ),
    )
```

**Validación en backend (complementaria):**

El middleware valida permisos con `has_low_level_permission(session, "folder_rename")`:

```python
# En el middleware o backend
if not router.has_low_level_permission(session, "folder_rename"):
    raise HTTPException(status_code=403, detail="Sin permiso")
```

**Aplicaciones creadas:**
- ✅ `5_web_frontend`: Puerto 8005, VE `.venv_frontend313`, URL `https://tfmmyllm.ai`
- ✅ `6_web_backoffice`: Puerto 8006, VE `.venv_backoffice313`, URL `https://tfmmyllm.ai/backoffice`

**Script de clonación:** `scripts/clone_frontend_to_backoffice.sh`
- Clona automáticamente `5_web_frontend` → `6_web_backoffice`
- Renombra carpetas, actualiza imports, cambia colores verde→naranja
- Crea `rxconfig.py` con configuración Redis completa
- Actualiza `run.sh` para puerto 8006 y entorno `.venv_backoffice313`

**Estado de implementación:**
- ✅ **Fases 1-7 completadas (100%)** - Redis + SharedSessionState + Integración completa
- ✅ **Frontend integrado** con herencia de SharedSessionState
- ✅ **Backoffice integrado** con herencia de SharedSessionState
- ✅ **Verificación exitosa** de compilación en ambas apps
- 📚 **Guía completa:** `docs/REDIS_IMPLEMENTATION_STATUS.md`
- 📋 **Testing:** `docs/INTEGRATION_COMPLETED.md`
- 🔍 **Script verificación:** `scripts/verify_redis_integration.sh`
- Actualiza `run.sh` para puerto 8006 y entorno `.venv_backoffice313`

### Estilos visuales diferenciados (Frontend vs Backoffice)

Las aplicaciones web tienen **estilos de renderizado markdown diferenciados** para proporcionar
identidad visual única a cada aplicación:

| Aplicación | Estilo Markdown | Tamaño de fuente | Uso |
|------------|-----------------|------------------|-----|
| `5_web_frontend` | **Zoom aumentado** | h1: 9, h2: 7, h3: 5, p/li: 1.15em | Orientado a usuarios finales, lectura cómoda |
| `6_web_backoffice` | **Tamaño estándar** | h1: 7, h2: 5, h3: 4, p/li: 1em | Orientado a administradores, densidad de información |

**Archivos de contenido markdown (secciones públicas):**
- `presentation.md` - Presentación de la empresa
- `services.md` - Catálogo de servicios
- `proyectos.md` - Metodología de proyectos
- `contacto.md` - Información de contacto
- `soporte.md` - Servicios de soporte

**Implementación técnica:**
- El renderizado usa `rx.markdown()` con `component_map` personalizado
- Frontend: fuentes aumentadas (~15% más grandes) para mejor legibilidad
- Backoffice: fuentes estándar para mayor densidad de información
- Ambos usan el mismo contenido markdown pero con estilos diferenciados
- La función `load_menu_content()` carga automáticamente `.md` con fallback a `.txt`

**Archivos de configuración:**
- `src/apps/5_web_frontend/web_frontend/web_frontend.py` (función `info_panel()`)
- `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py` (función `info_panel()`)

#### Prerrequisitos para Nginx en macbook

**Herramientas necesarias (se verifican automáticamente):**
- **Homebrew**: Gestor de paquetes para macOS
  ```bash
  # Instalar si no está disponible
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

- **OpenSSL**: Ya instalado en el sistema (OpenSSL 3.5.4)
  - Ubicación: `/opt/local/bin/openssl`
  - Usado para generar certificados SSL/TLS autofirmados

**Herramientas recomendadas para desarrollo local:**
- **mkcert**: Genera certificados locales de confianza automáticamente
  ```bash
  # Instalar con Homebrew
  brew install mkcert nss
  
  # Instalar la CA local (solo una vez)
  mkcert -install
  ```

##### Generación de certificado SSL para tfmmyllm.ai (desarrollo local)

**Prerequisito obligatorio: Instalar mkcert**

Si mkcert no está instalado en tu sistema, debes instalarlo primero:

```bash
# Instalar mkcert y nss con Homebrew
brew install mkcert nss

# Instalar la Certificate Authority (CA) local
mkcert -install
```

Este paso es **obligatorio** antes de generar certificados. El comando `mkcert -install` instalará una CA local confiable en tu sistema, permitiendo que los navegadores acepten los certificados sin advertencias de seguridad.

---

**Paso 1: Preparar el directorio de certificados**
```bash
# Crear directorio para almacenar certificados
mkdir -p infrastructure/certificates/macbook
```

**Paso 2: Configurar /etc/hosts (si no está configurado)**
```bash
# Añadir entrada al archivo hosts
echo "127.0.0.1       tfmmyllm.ai" | sudo tee -a /etc/hosts
```

**Paso 3: Generar certificado con mkcert**

**Opción A - Usar el script automatizado (recomendado):**
```bash
# Ejecutar el script de generación
cd infrastructure/certificates/macbook
./generate_certs.sh
```

El script verificará las dependencias, generará los certificados y mostrará información detallada.

**Opción B - Comando manual:**
```bash
# Navegar al directorio de certificados
cd infrastructure/certificates/macbook

# Generar certificado para tfmmyllm.ai y wildcard
mkcert -key-file tfmmyllm.ai-key.pem \
       -cert-file tfmmyllm.ai.pem \
       tfmmyllm.ai "*.tfmmyllm.ai" localhost 127.0.0.1 ::1
```

**Archivos generados:**
- `tfmmyllm.ai.pem` - Certificado público
- `tfmmyllm.ai-key.pem` - Clave privada

**Dominios incluidos en el certificado:**
- `tfmmyllm.ai` (dominio principal)
- `*.tfmmyllm.ai` (wildcard para subdominios: www, api, backoffice, etc.)
- `localhost`, `127.0.0.1`, `::1` (aliases locales)

**Paso 4: Verificar el certificado generado**
```bash
# Ver información del certificado
openssl x509 -in tfmmyllm.ai.pem -text -noout | grep -A 2 "Subject:"

# Ver fecha de expiración
openssl x509 -in tfmmyllm.ai.pem -noout -dates

# Ver todos los dominios incluidos (SANs)
openssl x509 -in tfmmyllm.ai.pem -noout -text | grep -A 1 "Subject Alternative Name"
```

**Validez del certificado:**
- mkcert genera certificados con validez predeterminada según su versión
- Versiones recientes: ~10 años (3650 días)
- La validez exacta depende de la versión instalada de mkcert

**Renovación del certificado:**

Si el certificado expira o necesitas regenerarlo:

```bash
# Opción 1: Regenerar con el mismo comando
cd infrastructure/certificates/macbook
mkcert -key-file tfmmyllm.ai-key.pem \
       -cert-file tfmmyllm.ai.pem \
       tfmmyllm.ai "*.tfmmyllm.ai" localhost 127.0.0.1 ::1

# Opción 2: Reinstalar la CA de mkcert (si hay problemas de confianza)
mkcert -uninstall
mkcert -install
# Luego regenerar el certificado con el comando anterior

# Opción 3: Verificar y actualizar mkcert
brew upgrade mkcert
mkcert -install
```

**Después de regenerar, reiniciar nginx:**
```bash
./deploy_nginx_macbook.sh
```

**Notas importantes:**
- Los certificados de mkcert son automáticamente confiables en navegadores
- No generan advertencias de seguridad en desarrollo local
- Los archivos de certificados NO deben commiterse a git (ya están en `.gitignore`)
- Para producción, usar certificados de Let's Encrypt o una CA comercial

**Configuración de nginx con SSL:**

Los certificados se almacenan en la ruta del proyecto y nginx los referencia mediante rutas absolutas:

**Ubicación de los certificados:**
```
/Users/administrator/develop/anewhope/infrastructure/certificates/macbook/
├── tfmmyllm.ai.pem           # Certificado público
└── tfmmyllm.ai-key.pem       # Clave privada
```

**Configuración en nginx:**

El archivo `infrastructure/servers/macbook/nginx/nginx.conf` referencia los certificados con rutas absolutas:

```nginx
http {
    # Configuración SSL global
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Servidor HTTP (puerto 8080) - Redirección a HTTPS
    server {
        listen 8080;
        server_name tfmmyllm.ai *.tfmmyllm.ai;
        return 301 https://$host$request_uri;
    }

    # Servidor HTTPS (puerto 443)
    server {
        listen 443 ssl;
        server_name tfmmyllm.ai *.tfmmyllm.ai;
        
        # Certificados SSL (rutas absolutas)
        ssl_certificate /Users/administrator/develop/anewhope/infrastructure/certificates/macbook/tfmmyllm.ai.pem;
        ssl_certificate_key /Users/administrator/develop/anewhope/infrastructure/certificates/macbook/tfmmyllm.ai-key.pem;
        
        # Configuración SSL adicional
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        
        # Proxy al frontend
        location / {
            proxy_pass http://127.0.0.1:8005;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Proxy al backoffice
        location /backoffice/ {
            proxy_pass http://127.0.0.1:8006;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

**Características de la configuración:**

1. **Puerto 8080 (HTTP)**: Redirige automáticamente a HTTPS
2. **Puerto 443 (HTTPS)**: Conexión segura con certificados SSL
3. **Rutas absolutas**: Los certificados se referencian con la ruta completa del proyecto
4. **Wildcard support**: Acepta `tfmmyllm.ai` y subdominios (`*.tfmmyllm.ai`)
5. **Headers proxy**: Incluye `X-Forwarded-Proto` para que las aplicaciones detecten HTTPS
6. **Protocolos modernos**: TLSv1.2 y TLSv1.3 únicamente
7. **Caché de sesión SSL**: Mejora el rendimiento de las conexiones HTTPS

**Acceso después de configurar:**
- HTTP: `http://tfmmyllm.ai:8080` → Redirige a HTTPS
- HTTPS: `https://tfmmyllm.ai` (puerto 443 por defecto)
- Backoffice: `https://tfmmyllm.ai/backoffice/`

**Generación de certificados SSL con OpenSSL (alternativa no recomendada):**
```bash
# Crear directorio para certificados
mkdir -p /usr/local/etc/nginx/ssl

# Generar certificado autofirmado (válido por 365 días)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /usr/local/etc/nginx/ssl/localhost.key \
  -out /usr/local/etc/nginx/ssl/localhost.crt \
  -subj "/C=ES/ST=Madrid/L=Madrid/O=TFM MyLLM/CN=localhost"
```

**Nota sobre certificados autofirmados:**
Los certificados generados con OpenSSL mostrarán advertencias de seguridad en el navegador.
Para desarrollo local sin advertencias, se recomienda usar `mkcert`.

#### Prerrequisitos para Python 3.12 en servidor trainer

El servicio `4_trainer` (Backend IA) requiere **Python 3.12** debido a la compatibilidad con 
dependencias de IA como TensorFlow y Keras. Esta es la única excepción a la regla general 
de Python 3.13 del proyecto.

**Instalación en macOS (macbook):**

```bash
# Instalar Python 3.12 con Homebrew
brew install python@3.12

# Verificar instalación
python3.12 --version
# Esperado: Python 3.12.x

# Verificar ubicación
which python3.12
# Esperado: /usr/local/bin/python3.12
```

**Instalación en Oracle Linux 10 (servidor trainer):**

```bash
# Actualizar repositorios
sudo dnf update -y

# Instalar Python 3.12 desde AppStream
sudo dnf install python3.12 python3.12-pip python3.12-devel -y

# Verificar instalación
python3.12 --version
# Esperado: Python 3.12.x

# Si no está disponible en AppStream, instalar desde fuente:
sudo dnf groupinstall "Development Tools" -y
sudo dnf install openssl-devel bzip2-devel libffi-devel zlib-devel -y

# Descargar y compilar Python 3.12
cd /tmp
curl -O https://www.python.org/ftp/python/3.12.8/Python-3.12.8.tgz
tar xzf Python-3.12.8.tgz
cd Python-3.12.8
./configure --enable-optimizations --prefix=/usr/local
make -j$(nproc)
sudo make altinstall

# Verificar
/usr/local/bin/python3.12 --version
```

**Creación del entorno virtual `.venv_trainer312`:**

```bash
# Desde la raíz del proyecto
cd /Users/administrator/develop/anewhope  # macOS
# o
cd /opt/anewhope  # Linux

# Crear entorno virtual con Python 3.12
python3.12 -m venv .venv_trainer312

# Activar entorno
source .venv_trainer312/bin/activate

# Instalar dependencias del trainer
pip install --upgrade pip
pip install -r src/apps/4_trainer/requirements.txt

# Verificar versión de Python en el entorno
python --version
# Esperado: Python 3.12.x
```

**Notas importantes:**
- El script `src/apps/4_trainer/run.sh` activa automáticamente `.venv_trainer312`
- El `Dockerfile` de `4_trainer` usa la imagen `python:3.12-slim`
- Este entorno es exclusivo para el Backend IA; otros servicios usan Python 3.13
- Ver ADR completo en `src/docs/stack_of_technologies.adr`

#### Despliegue de Nginx en macbook

Para desplegar y configurar nginx en el entorno macbook, se proporciona el script `deploy_nginx_macbook.sh`:

```bash
./deploy_nginx_macbook.sh
```

**Funcionalidades del script:**
- Verifica e instala nginx con Homebrew solo si no está instalado
- Copia la configuración desde `infrastructure/servers/macbook/nginx/nginx.conf`
- Valida la sintaxis del archivo de configuración con `nginx -t`
- Inicia nginx si está detenido o lo reinicia si ya está en ejecución
- Muestra el estado final y la URL de acceso

**Configuración de nginx:**
- **Puerto 8080 (HTTP)**: Redirige automáticamente a HTTPS
- **Puerto 443 (HTTPS)**: Conexión segura con certificados SSL
- **Frontend principal**: `https://tfmmyllm.ai/` → Proxy a `5_web_frontend` (puerto 8005)
- **Backoffice**: `https://tfmmyllm.ai/backoffice/` → Proxy a `6_web_backoffice` (puerto 8006)

**URLs de acceso:**
- Producción (HTTPS): `https://tfmmyllm.ai`
- Backoffice: `https://tfmmyllm.ai/backoffice/`
- HTTP (redirige): `http://tfmmyllm.ai:8080` → `https://tfmmyllm.ai`

**Flujo completo de despliegue:**

```bash
# 1. Instalar mkcert (si no está instalado) - OBLIGATORIO
# Verificar si mkcert está instalado
if ! command -v mkcert &> /dev/null; then
    echo "mkcert no está instalado. Instalando..."
    brew install mkcert nss
    mkcert -install
else
    echo "mkcert ya está instalado"
fi

# 2. Generar certificados SSL
brew install mkcert nss
mkcert -install

# 2. Generar certificados SSL
cd infrastructure/certificates/macbook
./generate_certs.sh
cd ../../..

# 3. Desplegar nginx con la configuración SSL
./deploy_nginx_macbook.sh

# 4. Verificar que nginx está corriendo
curl -I https://tfmmyllm.ai
```

**Verificación de certificados en nginx:**
```bash
# Ver información del certificado usado por nginx
echo | openssl s_client -connect tfmmyllm.ai:443 2>/dev/null | openssl x509 -noout -dates -subject

# Verificar que los certificados están en la ubicación correcta
ls -lh infrastructure/certificates/macbook/
```

### Solución de problemas (Troubleshooting)

#### Problema 1: Error "Not Found" (404) al acceder a https://tfmmyllm.ai

**Síntoma:**
Al acceder a `https://tfmmyllm.ai` en el navegador, aparece el mensaje "Not Found" en texto plano.

**Causa:**
El frontend de Reflex no ha cargado correctamente las rutas, o necesita ser reiniciado después de configurar nginx con HTTPS.

**Solución:**

```bash
# Paso 1: Detener el proceso actual del frontend
# Encuentra el proceso de Reflex
ps aux | grep "reflex run" | grep -v grep

# Si hay un proceso corriendo, detenerlo (Ctrl+C en la terminal o usar kill)
ps aux | grep "reflex run" | grep -v grep | awk '{print $2}' | xargs kill -9

# Paso 2: Reiniciar el frontend
cd src/apps/5_web_frontend
bash run.sh

# Paso 3: Esperar a que Reflex compile (~30 segundos)
# Verás mensajes como:
# "Compiling:  ✓ (100%)"
# "App running at: http://localhost:8005"

# Paso 4: Verificar que funciona
curl -I http://127.0.0.1:8005
# Debería devolver: HTTP/1.1 200 OK

# Paso 5: Acceder desde el navegador
# https://tfmmyllm.ai
```

**Verificación:**
- ✅ Nginx está corriendo: `brew services list | grep nginx`
- ✅ Frontend está corriendo: `lsof -i :8005`
- ✅ Puerto 443 escucha: `lsof -i :443 | grep nginx`
- ✅ Ruta funciona directamente: `curl -I http://127.0.0.1:8005`

**Nota:** Si el acceso directo al puerto 8005 devuelve 404, el problema es del frontend, no de nginx. Reinicia el frontend siguiendo los pasos anteriores.

---

#### Problema 2: Error "Connection refused" o "ERR_CONNECTION_REFUSED"

**Síntoma:**
El navegador no puede conectar a `https://tfmmyllm.ai`.

**Causa:**
Nginx no está corriendo o no está escuchando en el puerto 443.

**Solución:**

```bash
# Verificar estado de nginx
brew services list | grep nginx

# Si no está corriendo, iniciarlo
./deploy_nginx_macbook.sh

# Verificar que escucha en puerto 443
lsof -i :443 | grep nginx

# Ver logs de nginx para errores
tail -f /usr/local/var/log/nginx/error.log
```

---

#### Problema 3: Advertencia de certificado no confiable

**Síntoma:**
El navegador muestra advertencias de seguridad sobre el certificado SSL.

**Causa:**
La Certificate Authority (CA) de mkcert no está instalada en el sistema.

**Solución:**

```bash
# Reinstalar la CA de mkcert
mkcert -uninstall
mkcert -install

# Regenerar los certificados
cd infrastructure/certificates/macbook
./generate_certs.sh

# Reiniciar nginx
cd ../../..
./deploy_nginx_macbook.sh

# Reiniciar el navegador completamente
# (cierra todas las ventanas y vuelve a abrir)
```

---

#### Problema 4: Error "Address already in use" en puerto 443 o 8005

**Síntoma:**
Al iniciar nginx o el frontend aparece el error "Address already in use".

**Solución:**

```bash
# Para puerto 443 (nginx)
lsof -i :443
# Si hay un proceso que no es nginx, detenerlo:
kill -9 <PID>

# Para puerto 8005 (frontend)
lsof -i :8005
# Si hay un proceso viejo de Reflex, detenerlo:
kill -9 <PID>

# Reiniciar los servicios
./deploy_nginx_macbook.sh
cd src/apps/5_web_frontend && bash run.sh
```

---

#### Problema 5: Nginx muestra "502 Bad Gateway"

**Síntoma:**
Nginx responde pero con error "502 Bad Gateway".

**Causa:**
El frontend no está corriendo o no responde en el puerto 8005.

**Solución:**

```bash
# Verificar que el frontend está corriendo
lsof -i :8005

# Si no está corriendo, iniciarlo
cd src/apps/5_web_frontend
bash run.sh

# Verificar que responde
curl -I http://127.0.0.1:8005

# Ver logs de nginx
tail -f /usr/local/var/log/nginx/error.log
```

---

#### Problema 6: No se encuentra el dominio tfmmyllm.ai

**Síntoma:**
El navegador dice que no puede encontrar el servidor `tfmmyllm.ai`.

**Causa:**
El archivo `/etc/hosts` no tiene la entrada para el dominio.

**Solución:**

```bash
# Verificar si la entrada existe
grep tfmmyllm.ai /etc/hosts

# Si no existe, añadirla
echo "127.0.0.1       tfmmyllm.ai" | sudo tee -a /etc/hosts

# Verificar que se añadió correctamente
grep tfmmyllm.ai /etc/hosts

# Limpiar caché DNS (macOS)
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

---

#### Problema 7: Error de WebSocket "Cannot connect to server: websocket error"

**Síntoma:**
El frontend carga correctamente, pero aparece un mensaje de error: "Cannot connect to server: websocket error. Check if server is reachable at wss://tfmmyllm.ai/_event"

**Causas comunes:**

1. **El frontend no está recogiendo la configuración de `api_url`**: El frontend necesita ser reconstruido desde cero cuando se cambia la configuración en `rxconfig.py`.

2. **Cache del build del frontend**: Los assets compilados pueden tener cacheada una URL anterior.

3. **Los servicios no están sincronizados**: El frontend y el backend pueden estar corriendo en modos diferentes.

**Solución completa:**

```bash
# Paso 1: Detener todos los procesos de Reflex
ps aux | grep -E "(reflex|node.*3001|python.*8005)" | grep -v grep | awk '{print $2}' | xargs kill -9

# Paso 2: Limpiar completamente el build del frontend
cd src/apps/5_web_frontend
rm -rf .web public

# Paso 3: Activar el entorno virtual
source ../../../.venv_frontend313/bin/activate

# Paso 4: Verificar que rxconfig.py tiene la configuración correcta
# Debe contener:
# api_url="https://tfmmyllm.ai"
# env=rx.Env.PROD
# backend_port=8005

# Paso 5: Exportar el frontend desde cero
reflex export --no-zip

# Paso 6: Reiniciar Reflex en modo producción
reflex run --env prod

# Paso 7: Esperar a que compile (verás "App Running" en los logs)
# Frontend debería estar en http://0.0.0.0:3001/
# Backend debería estar en http://0.0.0.0:8005

# Paso 8: Reiniciar nginx para asegurar configuración
cd ../../..
./deploy_nginx_macbook.sh

# Paso 9: Verificar puertos
lsof -i :3001 -i :8005 | grep LISTEN

# Paso 10: Probar acceso directo
curl -I http://127.0.0.1:3001  # Frontend
curl -I http://127.0.0.1:8005/_event  # Backend WebSocket

# Paso 11: Probar a través de Nginx
curl -I https://tfmmyllm.ai  # Debería devolver 200 OK

# Paso 12: Limpiar caché del navegador
# - Abrir Developer Tools (F12)
# - Click derecho en el botón de recargar
# - Seleccionar "Empty Cache and Hard Reload"
# O simplemente usar el modo incógnito

# Paso 13: Acceder desde el navegador
# https://tfmmyllm.ai
```

**Verificación:**
- ✅ `rxconfig.py` tiene `api_url="https://tfmmyllm.ai"`
- ✅ Frontend en puerto 3001: `lsof -i :3001`
- ✅ Backend en puerto 8005: `lsof -i :8005`
- ✅ Nginx escuchando en 443: `lsof -i :443 | grep nginx`
- ✅ Nginx proxying a 3001: Ver `/usr/local/etc/nginx/nginx.conf` location `/`
- ✅ Nginx proxying `/_event` a 8005: Ver `nginx.conf` location `/_event`

**Nota importante:** En modo producción, Reflex compila los assets del frontend con el valor de `api_url` embebido. Si cambias este valor, debes limpiar el build completo (`rm -rf .web public`) y exportar de nuevo (`reflex export --no-zip`).

---

#### Problema 8: "Blocked request. This host is not allowed" en Vite

**Síntoma:**
Al arrancar el frontend, aparece el error:
```
Blocked request. This host ("tfmmyllm.ai") is not allowed.
To allow this host, add "tfmmyllm.ai" to `server.allowedHosts` in vite.config.js.
```

**Causa:**
A partir de Vite 6.0.9, el servidor de desarrollo valida los hosts entrantes por motivos de seguridad (CVE-2025-30208). Los hosts que no estén explícitamente permitidos son bloqueados.

Reflex genera automáticamente el archivo `.web/vite.config.js`, pero no incluye `allowedHosts` por defecto.

**Solución:**

El proyecto incluye un script de parche automático que se ejecuta al arrancar el frontend:

```bash
# El parche se aplica automáticamente al ejecutar:
cd src/apps/5_web_frontend
./run.sh
```

**Solución manual (si el parche automático no funciona):**

1. Editar el archivo `.web/vite.config.js`
2. Localizar la sección `server: { ... }`
3. Añadir la línea `allowedHosts`:

```javascript
server: {
  port: process.env.PORT,
  hmr: true,
  allowedHosts: ['tfmmyllm.ai', '.tfmmyllm.ai', 'localhost'],  // ← Añadir esta línea
  watch: {
    // ...
  },
},
```

**Archivos relacionados:**
- `src/apps/5_web_frontend/patch_vite_config.py`: Script de parche automático
- `src/apps/5_web_frontend/.web/vite.config.js`: Configuración de Vite (auto-generada)
- `src/apps/6_web_backoffice/patch_vite_config.py`: Script equivalente para backoffice

**Nota:** Si ejecutas `reflex init` y se regenera `.web/`, el parche se volverá a aplicar automáticamente la próxima vez que ejecutes `./run.sh`.

---

#### Comandos útiles de diagnóstico

**Script automatizado:**
```bash
./diagnose_system.sh
```

Este script verifica el estado completo del sistema: nginx, frontend, middleware, backend core, broker backend, certificados, /etc/hosts y logs recientes.

**Comandos manuales:**
```bash
# Estado completo del sistema
echo "=== Estado de Nginx ==="
brew services list | grep nginx
lsof -i :443 | grep nginx

echo "=== Estado del Frontend ==="
lsof -i :8005

echo "=== Verificar certificados ==="
ls -lh infrastructure/certificates/macbook/

echo "=== Test de conectividad ==="
curl -I https://tfmmyllm.ai 2>&1 | head -5

echo "=== Test directo al frontend ==="
curl -I http://127.0.0.1:8005

echo "=== Verificar /etc/hosts ==="
grep tfmmyllm.ai /etc/hosts
```

**Logs importantes:**
- Nginx error log: `/usr/local/var/log/nginx/error.log`
- Nginx access log: `/usr/local/var/log/nginx/access.log`
- Frontend log: `src/apps/5_web_frontend/logs/frontend_secure.log`
- Middleware log: `src/apps/7_service_frontend/logs/middleware_activiy.log`

## Diagrama de arquitectura (Mermaid)

El esquema de arquitectura está definido en `context/schemas/mermaid-ai-diagram-myllm.mmd`.
Resume la relación entre roles de usuario, servidores (frontend, backend y trainer),
el middleware (`7_service_frontend`), el backend (`3_backend`), el servicio backend
(`8_service_backend`), y los componentes compartidos (`1_shared_domain`, `2_shared_application`),
además de las dependencias con Nginx y MariaDB.

### Relación entre servicios (interpretación)

- Dos interfaces web consumen el middleware: `5_web_frontend` y `6_web_backoffice`.
- El middleware (`7_service_frontend`) enruta hacia el broker backend (`8_service_backend`),
  que reparte peticiones entre el backend core y el backend IA.
- El broker decide el destino:
  - **Operaciones de datos** (MariaDB/MySQL y sistema de ficheros): las atiende el backend core `3_backend`
    ejecutado en el servidor backend.
  - **Operaciones de IA** (uso interno y entrenamiento): las atiende `4_trainer`, que tendrá API REST y se
    ejecutará en el servidor trainer con base de datos vectorial Keras para entrenamientos.
- La capa de dominio común vive en `src/1_shared_domain/`.
- La capa de aplicación compartida vive en `src/2_shared_application/`.

### Flujo obligatorio de peticiones (CRÍTICO)

**REGLA FUNDAMENTAL:** Todas las peticiones de los frontales web (frontend y backoffice) 
DEBEN seguir el flujo completo a través de la arquitectura de servicios.

#### Flujo para operaciones de datos (MariaDB)

```
┌─────────────────┐    ┌────────────────┐    ┌────────────────┐    ┌─────────────────┐    ┌──────────┐
│  5_web_frontend │───▶│ 7_middleware   │───▶│ 8_broker       │───▶│ 3_backend_core  │───▶│ MariaDB  │
│  6_web_backoffice│   │ (apife.py)     │    │ (routerbroker) │    │ (routercore.py) │    │          │
└─────────────────┘    └────────────────┘    └────────────────┘    └─────────────────┘    └──────────┘
        │                      │                      │                      │                   │
        │ HTTP (REST)          │ HTTP (REST)          │ HTTP (REST)          │ SQLAlchemy        │
        │ Puerto 8007          │ Puerto 8008          │ Puerto 8003          │ Puerto 3306       │
        └──────────────────────┴──────────────────────┴──────────────────────┴───────────────────┘
```

#### Flujo para operaciones de IA (Entrenamiento)

```
┌─────────────────┐    ┌────────────────┐    ┌────────────────┐    ┌─────────────────┐
│  5_web_frontend │───▶│ 7_middleware   │───▶│ 8_broker       │───▶│ 4_trainer       │
│  6_web_backoffice│   │ (apife.py)     │    │ (routerbroker) │    │ (API REST + IA) │
└─────────────────┘    └────────────────┘    └────────────────┘    └─────────────────┘
        │                      │                      │                      │
        │ HTTP (REST)          │ HTTP (REST)          │ HTTP (REST)          │
        │ Puerto 8007          │ Puerto 8008          │ Puerto 8004          │
        └──────────────────────┴──────────────────────┴──────────────────────┘
```

#### Reglas del flujo

1. **Frontend/Backoffice → Middleware:** SIEMPRE. Nunca acceder directamente al broker o backend.
2. **Middleware → Broker:** SIEMPRE para operaciones de datos o IA. El middleware NO debe acceder directamente a MariaDB.
3. **Broker → Backend Core:** Para operaciones de datos (usuarios, organizaciones, permisos, etc.).
4. **Broker → Trainer:** Para operaciones de IA (entrenamiento, modelos, métricas).
5. **Backend Core → MariaDB:** Solo el backend core accede a la base de datos.

#### Ejemplo: Habilitar/Deshabilitar usuario

```
1. Frontend: Clic en botón "Deshabilitar"
   └─▶ State.disable_user(user_id)
   
2. Frontend → Middleware:
   └─▶ PATCH /users/{user_id}/status {"active": false}
   
3. Middleware → Broker:
   └─▶ broker_client.update_user_status(user_id, active, requester_org_id)
   └─▶ PATCH http://localhost:8008/users/{user_id}/status
   
4. Broker → Backend Core:
   └─▶ core_client.update_user_status(user_id, active, requester_org_id)
   └─▶ PATCH http://localhost:8003/users/{user_id}/status
   
5. Backend Core → MariaDB:
   └─▶ UPDATE users SET active = 0 WHERE user_id = ?
   
6. Respuesta regresa por el mismo camino:
   └─▶ Backend Core → Broker → Middleware → Frontend
```

#### Archivos involucrados en el flujo

| Capa | Archivo | Función |
|------|---------|---------|
| Frontend | `adapters/api_client.py` | `update_user_status()` |
| Middleware API | `apife.py` | `@app.patch("/users/{user_id}/status")` |
| Middleware Router | `routermiddleware.py` | `update_user_active_status()` |
| Middleware → Broker | `broker_backend_client.py` | `update_user_status()` |
| Broker API | `apibe.py` | `@app.patch("/users/{user_id}/status")` |
| Broker Router | `routerbroker.py` | `update_user_status()` |
| Broker → Core | `interfacetocore.py` | `update_user_status()` |
| Backend Core API | `apicore.py` | `@app.patch("/users/{user_id}/status")` |
| Backend Core Router | `routercore.py` | `update_user_status()` |

### Control de acceso por identity_type_id (SEGURIDAD)

El sistema utiliza `identity_type_id` para controlar qué operaciones puede realizar cada usuario.
Esta restricción se aplica en **dos niveles** para garantizar **Defense in Depth**:

1. **UI (Frontend/Backoffice)**: Ocultar elementos para los que el usuario no tiene permisos
2. **API (Middleware)**: Rechazar peticiones no autorizadas con HTTP 403

#### Matriz de permisos por identity_type_id

| identity_type_id | Rol | Gestionar usuarios | Gestionar proyectos | Acceso backoffice |
|------------------|-----|-------------------|--------------------|--------------------|
| 1 | SuperAdmin | ✅ Sí | ✅ Sí | ✅ Sí |
| 2 | Admin de Organización | ✅ Sí | ✅ Sí | ✅ Sí |
| 3 | Editor | ❌ No | ✅ Editar | ✅ Sí |
| 4 | Lector | ❌ No | ❌ Solo lectura | ❌ No |
| 5 | Auditor | ❌ No | ❌ Solo lectura | ❌ No |
| 10 | Agente Admin | ✅ Sí | ✅ Sí | ✅ Sí |
| 11 | Agente Editor | ❌ No | ✅ Editar | ✅ Sí |
| 12 | Agente Lector | ❌ No | ❌ Solo lectura | ❌ No |
| 13 | Agente Auditor | ❌ No | ❌ Solo lectura | ❌ No |

#### Implementación en UI (Reflex)

```python
# Propiedad computada en el State
@rx.var
def can_manage_org_users(self) -> bool:
    """Solo SuperAdmin, Admin Org, y Agente Admin pueden gestionar usuarios."""
    return self.identity_type_id in (1, 2, 10)

# En el componente, usar rx.cond para mostrar/ocultar
rx.cond(
    State.can_manage_org_users,
    rx.button("Eliminar usuario", on_click=State.delete_user(user_id)),
    rx.fragment(),  # No mostrar nada si no tiene permisos
)
```

#### Implementación en API (Middleware)

```python
@app.patch("/users/{user_id}/status")
async def update_user_status_endpoint(
    user_id: int,
    session: SessionContext = Depends(get_session_context),
):
    # VALIDACIÓN OBLIGATORIA: Verificar permisos antes de ejecutar
    allowed_identity_types = (1, 2, 10)  # SuperAdmin, Admin Org, Agente Admin
    if session.identity_type_id not in allowed_identity_types:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Sin permisos (identity_type_id={session.identity_type_id})",
        )
    # ... ejecutar operación
```

#### Reglas para nuevas funcionalidades

Al implementar nuevas funcionalidades que requieran control de acceso:

1. ✅ Definir qué `identity_type_id` pueden realizar la operación
2. ✅ Añadir propiedad computada `can_<operacion>` en el State
3. ✅ Usar `rx.cond()` en la UI para mostrar/ocultar elementos
4. ✅ Añadir validación en el endpoint del middleware ANTES de ejecutar
5. ✅ Retornar HTTP 403 si el usuario no tiene permisos
6. ✅ Documentar en esta sección y en AGENTS.md

### Borrado lógico de usuarios (IMPORTANTE)

El sistema implementa **borrado LÓGICO** de usuarios, no borrado físico. Esto significa:

- **Borrar usuario**: Actualiza `active = false` en la tabla `users`
- **Habilitar usuario**: Actualiza `active = true` en la tabla `users`
- **El registro NUNCA se elimina** de la base de datos

#### Comportamiento por aplicación

| Aplicación | Parámetro | Usuarios visibles | Acciones disponibles |
|------------|-----------|-------------------|----------------------|
| **Frontend** | `active_only=true` | Solo activos | Borrar (→ inactivo) |
| **Backoffice** | `active_only=false` | Todos | Habilitar, Deshabilitar, Borrar |

#### Flujo de datos

```
Frontend/Backoffice
       │
       ▼
    Middleware (update_user_status)
       │
       ▼
    Broker Backend
       │
       ▼
    Backend Core
       │
       ▼
    MariaDB: UPDATE users SET active = 0/1 WHERE user_id = ?
```

#### Endpoint utilizado

```
PUT /users/{user_id}/status
{
    "active": true/false
}
```

#### Indicadores visuales

- **Badge "Activo"** (verde): Usuario con `active = true`
- **Badge "Inactivo"** (rojo): Usuario con `active = false`

#### Botones de acción (Backoffice)

| Botón | Icono | Acción | Resultado |
|-------|-------|--------|-----------|
| Habilitar usuario | `user-check` | `active = true` | Usuario puede iniciar sesión |
| Deshabilitar usuario | `user-x` | `active = false` | Usuario no puede iniciar sesión |
| Borrar usuario | `trash-2` | `active = false` | Igual que deshabilitar |

**Nota**: "Borrar" y "Deshabilitar" tienen el mismo efecto (borrado lógico).
La diferencia es semántica: "Borrar" sugiere permanencia, "Deshabilitar" sugiere temporalidad.

#### Permisos requeridos

Solo usuarios con `identity_type_id` en `(1, 2, 10)` pueden gestionar usuarios:
- `1`: SuperAdmin
- `2`: Administrador de Organización
- `10`: Agente Administrador

### Gestión de ficheros (fmanagement)

Las operaciones sobre carpetas y ficheros se delegan desde `3_backend` a la API externa
`fmanagement` (Go). Esta API usa permisos de bajo nivel y trabaja sobre un volumen
de datos en el servidor backend.

Ruta de almacenamiento esperada en producción: `/data/files/external`.

Estructura esperada:
```
/data/files/external/
  ORG0001/
    PRJ00001/
      v001/
      v002/
```

En desarrollo existe un ejemplo en `fmanagement/example`, pero la implementación final
no debe depender de esa ruta.

#### Endpoints de fmanagement

- `GET /fmo`: operaciones sobre fichero/carpeta con `operation=view|delete|rename|create`.
  Parámetros clave: `iduser`, `basepath`, `orgpath`, `prjpath`, `versionpath`,
  `subfolders`, `filename`, `extfile`, `new_filename`, `new_extfile`.
- `POST /fmo`: subida de fichero (`operation=upload`, `multipart/form-data` con `file`).
  Parámetros clave: `iduser`, `basepath`, `orgpath`, `prjpath`, `versionpath`,
  `subfolders`, `filename`, `extfile`.
- `GET /fmo/list`: listado recursivo de directorios (estructura).
  Parámetros clave: `iduser`, `basepath`, `orgpath`, `prjpath`, `versionpath`, `subfolders`.
- `POST /fmo/newversion`: clona una versión a la siguiente (`v001` → `v002`).
  Parámetros clave: `iduser`, `basepath`, `orgpath`, `prjpath`, `versionpath`.
- `GET /fmo/diffversion`: compara dos versiones.
  Parámetros clave: `iduser`, `basepath`, `orgpath`, `prjpath`,
  `versionpath`, `compare_versionpath`.
- `POST /fmo/transferversion`: transfiere una versión entre servidores (backend ↔ trainer).
  Parámetros clave: `iduser`, `orgpath`, `prjpath`, `versionpath`, `target_type`,
  `identity_type_id`.

Headers requeridos para permisos:
- `Authorization: Bearer <access_token>`
- `X-Session-Token: <session_token>`

En modo `db_only` es obligatorio incluir `identity_type_id` (query param).

#### Transferencia de versiones (Backend Core ↔ Trainer)

La transferencia de versiones permite replicar una versión de proyecto desde el servidor
backend al servidor trainer (o viceversa) para su uso en entrenamiento de modelos de IA.

**Flujo:**
```
Backend Core → fmanagement → rsync/SSH → Servidor Trainer
                              (o copia local en macbook)
```

**Modos de transferencia:**
- **Local** (`TRANSFER_MODE=local`): Copia directa entre carpetas (desarrollo)
- **Remoto** (`TRANSFER_MODE=remote`): rsync over SSH (producción)

**Variables de entorno (añadir a env.yaml):**
```yaml
# Rutas de almacenamiento
backend_core_base_storage: /data/files/external
backend_ia_base_storage: /data/files/trainer

# Configuración de transferencia
transfer_mode: local  # "local" o "remote"
trainer_ssh_host: trainer.internal
trainer_ssh_user: rsync_user
trainer_ssh_key_path: /opt/anewhope/keys/rsync_key
trainer_ssh_port: "22"
```

**Endpoint de Backend Core:**
```
POST /fmo/transferversion
{
    "id_user": 1,
    "id_organization": 1,
    "id_project": 1,
    "version_path": "v001",
    "target_type": "trainer",  // o "core"
    "identity_type_id": 2
}
```

**Permisos requeridos:** `version_create`

**Script de configuración (macbook):**
```bash
./scripts/setup_transfer_environment.sh
```

## ADRs (Architecture Decision Records)

El proyecto documenta decisiones arquitectónicas importantes en:

**`src/docs/stack_of_technologies.adr`** - Contiene 3 ADRs fundamentales:

1. **Python 3.13**: Justifica el uso de Python 3.13 y el downgrade temporal desde 3.14 
   por incompatibilidades con Pydantic y PyO3.
   - **Fecha:** 2026-01-19
   - **Decisión:** Adoptar Python 3.13 como versión base del proyecto
   - **Razón:** Python 3.14 tiene incompatibilidades con pydantic-core

2. **Compatibilidad Redis 5.2.1 con Reflex 0.8.25**: Documenta la actualización de la 
   librería redis-py para cumplir con los requisitos de Reflex.
   - **Fecha:** 2026-01-26
   - **Decisión:** Actualizar de `redis==5.0.1` a `redis==5.2.1`
   - **Razón:** Reflex 0.8.25 requiere `redis>=5.2.1,<8.0`
   - **Impacto:** Compatibilidad garantizada con el state manager de Reflex

3. **Sesión Compartida Frontend/Backoffice usando Redis**: Documenta el análisis de 
   alternativas y la decisión de usar Redis como backend de sesión compartida.
   - **Fecha:** 2026-01-24 a 2026-01-26
   - **Decisión:** Usar Redis con `StateManagerRedis` nativo de Reflex
   - **Alternativas analizadas:** MariaDB, JSON en disco, Memcached, JWT stateless
   - **Razón:** Integración nativa con Reflex, alto rendimiento, TTL automático, 
     locks distribuidos
   - **Impacto:** Usuarios navegan entre frontend y backoffice sin re-autenticación

**Consultar el ADR completo para detalles de:**
- Contexto y problema técnico
- Análisis exhaustivo de alternativas
- Justificación de decisiones
- Consecuencias y trade-offs
- Verificación y testing
- Referencias y documentación relacionada

## Entornos virtuales dedicados

El proyecto usa **Python 3.13** como versión base. Para evitar conflictos de dependencias y 
garantizar aislamiento entre servicios, cada aplicación tiene su propio entorno virtual dedicado 
en la raíz del proyecto.

### Matriz de entornos virtuales por aplicación

| Entorno Virtual | Puerto | Aplicaciones | Uso |
|-----------------|--------|--------------|-----|
| `.venv_frontend313` | 8005 | `5_web_frontend`, `2_shared_application` | Frontend web principal y capa compartida |
| `.venv_backoffice313` | 8006 | `6_web_backoffice` | Interfaz administrativa |
| `.venv_middleware313` | 8007 | `7_service_frontend`, `8_service_backend`, `3_backend` | Servicios middleware y backend |
| `.venv_backend313` | 8003 | `3_backend` (alternativa) | Backend core en desarrollo aislado |
| `.venv_trainer312` | 8004 | `4_trainer` | Backend IA - **Python 3.12** (compatibilidad TensorFlow/Keras) |
| `.venv_broker313` | 8008 | `8_service_backend` (alternativa) | Broker backend en desarrollo aislado |

**Nota:** El `4_trainer` usa Python 3.12 (no 3.13) debido a compatibilidad con TensorFlow y Keras.
Ver `src/docs/stack_of_technologies.adr` para detalles de la decisión arquitectónica.

**Reglas de uso:**

1. ✅ **Cada aplicación usa SOLO su entorno virtual asignado**
2. ✅ **No se comparten entornos virtuales entre aplicaciones**
3. ✅ **Los scripts `run.sh` activan automáticamente el entorno correcto**
4. ✅ **Los tests deben ejecutarse en el entorno virtual correspondiente**
5. ✅ **Los contenedores Docker usan dependencias instaladas en la imagen**

**Verificación de entornos:**

```bash
# Verificar configuración de entornos virtuales
./scripts/verify_environments.sh

# Verificar configuración de tests
./scripts/verify_tests_environments.sh
```

Estos scripts validan que cada aplicación tiene su propio entorno virtual y que no hay compartición.

**Documentación completa:**

- **Auditoría de entornos:** `docs/VIRTUAL_ENVIRONMENTS_AUDIT.md` - Análisis detallado de cada aplicación
- **Guía de tests:** `docs/TESTING_VIRTUAL_ENVIRONMENTS.md` - Reglas y buenas prácticas para tests
- **Resumen ejecutivo:** `docs/SUMMARY_ENVIRONMENTS_TESTING.md` - Resumen de la implementación
- **Reglas de agentes:** `AGENTS.md` (sección 5.1) - Reglas para tests y entornos virtuales

### Creación de entornos virtuales

```bash
# Frontend
python3.13 -m venv .venv_frontend313
source .venv_frontend313/bin/activate
pip install -r src/apps/5_web_frontend/requirements.txt
deactivate

# Middleware
python3.13 -m venv .venv_middleware313
source .venv_middleware313/bin/activate
pip install -r src/apps/7_service_frontend/requirements.txt
deactivate

# Backend Core
python3.13 -m venv .venv_backend313
source .venv_backend313/bin/activate
pip install -r src/apps/3_backend/requirements.txt
deactivate

# Broker Backend
python3.13 -m venv .venv_broker313
source .venv_broker313/bin/activate
pip install -r src/apps/8_service_backend/requirements.txt
deactivate
```

### Ejecución de servicios

Cada aplicación en `src/apps/*` incluye un script `run.sh` que activa automáticamente 
su entorno virtual dedicado antes de iniciar el servicio:

```bash
# Backend Core
cd src/apps/3_backend && bash run.sh

# Broker Backend
cd src/apps/8_service_backend && bash run.sh

# Middleware
cd src/apps/7_service_frontend && bash run.sh

# Frontend
cd src/apps/5_web_frontend && bash run.sh
```

## Scripts útiles

### full_test.sh

Script de ejecución de tests que valida todos los módulos del proyecto con salida detallada:

```bash
./full_test.sh
```

**Características:**
- Ejecuta tests de forma secuencial por módulo
- Muestra cada test individual con su estado (PASSED/FAILED)
- Usa entornos virtuales dedicados automáticamente:
  - `.venv_frontend313` para `2_shared_application` y `5_web_frontend`
  - `.venv_middleware313` para `7_service_frontend`, `8_service_backend` y `3_backend`
- Proporciona separadores visuales entre grupos de tests
- Salida verbose (`-v`) para máxima trazabilidad

**Módulos testeados:**
1. `src/2_shared_application/tests` (14 tests): DTOs, helpers, validaciones
2. `src/apps/5_web_frontend/tests` (23 tests): componentes web, integración middleware
3. `src/apps/7_service_frontend/tests` (8 tests): middleware, sesiones, permisos
4. `src/apps/8_service_backend/tests` (1 test): broker backend, routing
5. `src/apps/3_backend/tests` (1 test): backend core, endpoints

### clear_caches.sh

Script de limpieza de caches de Reflex y herramientas de desarrollo:

```bash
./clear_caches.sh
```

**Limpia:**
- Caches de Reflex: `.web`, `.states`
- Caches de tooling: `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `.hypothesis`

### diagnose_system.sh

Script de diagnóstico completo del sistema para verificar el estado de todos los servicios y configuraciones:

```bash
./diagnose_system.sh
```

**Verifica:**
- Estado de nginx y puerto 443
- Estado del frontend (puerto 8005)
- Estado del middleware (puerto 8007)
- Estado del backend core (puerto 8003)
- Estado del broker backend (puerto 8008)
- Existencia y validez de certificados SSL
- Conectividad HTTPS y HTTP
- Configuración de `/etc/hosts`
- Logs recientes de nginx

**Uso recomendado:**
Ejecutar este script cuando se presenten problemas de conectividad o después de cambios en la configuración para verificar que todo está funcionando correctamente.

### renewall_fernet_key.sh

Script de seguridad para renovar la clave Fernet y re-encriptar todos los valores cifrados
(contraseñas de usuarios) con la nueva clave:

```bash
./scripts/renewall_fernet_key.sh [--dry-run] [--backup-only]
```

**Opciones:**
- `--dry-run`: Simula la operación sin modificar archivos (recomendado para verificar)
- `--backup-only`: Solo crea backups sin renovar la clave
- `--help`, `-h`: Muestra la ayuda

**Proceso de renovación:**
1. Verifica que existan los archivos requeridos (`basesecuritypass.json`, `users.json`)
2. Crea backups automáticos en `backups/fernet_rotation/`
3. Carga la clave Fernet antigua
4. Genera una nueva clave Fernet
5. Para cada usuario con contraseña cifrada:
   - Descifra con la clave antigua
   - Re-encripta con la clave nueva
6. Guarda la nueva clave y los usuarios actualizados

**Archivos afectados:**
- `src/2_shared_application/security/basesecuritypass.json` (clave Fernet)
- `src/2_shared_application/moks/users.json` (contraseñas de usuarios)

**IMPORTANTE - Antes de ejecutar:**
1. Detener todos los servicios que usen cifrado (frontend, backoffice, middleware)
2. Verificar con `--dry-run` que no hay errores
3. Ejecutar sin flags para aplicar los cambios
4. Reiniciar todos los servicios
5. Verificar que el login funciona correctamente

**Ejemplo de uso:**
```bash
# 1. Verificar primero (sin cambios)
./scripts/renewall_fernet_key.sh --dry-run

# 2. Aplicar la renovación
./scripts/renewall_fernet_key.sh

# 3. Reiniciar servicios y verificar
```

**Cuándo usar este script:**
- Después de detectar exposición de la clave Fernet (como en commits accidentales)
- Como parte de una política de rotación periódica de credenciales
- Antes de un despliegue en producción con claves nuevas

### Seguridad de la clave Fernet en despliegue

#### Análisis de riesgo y criticidad

La clave Fernet almacenada en `basesecuritypass.json` fue expuesta en el historial de Git
durante el desarrollo. Sin embargo, la **criticidad es reducida** por las siguientes razones:

1. **`protected_values.py` nunca fue expuesto**: El archivo `protected_values.py` que contiene
   la clave privada base para derivar secretos siempre estuvo en `.gitignore` desde el inicio
   del proyecto.

2. **Aislamiento por entorno**: Cada entorno (macbook, dev, pre, pro) debe usar claves
   diferentes definidas en su propio `protected_values.py`.

3. **Entorno de desarrollo**: La clave expuesta solo se usaba en el entorno de desarrollo
   local (macbook) y no tiene acceso a datos sensibles de producción.

4. **Uso limitado**: La clave Fernet se usa principalmente para cifrar contraseñas de
   usuarios en el mock de desarrollo, no datos críticos de negocio.

#### Eliminación del historial de Git (opcional)

Es posible eliminar la clave del historial usando herramientas especializadas:

| Herramienta | Descripción | Complejidad |
|-------------|-------------|-------------|
| `git filter-repo` | Recomendada, moderna y eficiente | Media |
| `BFG Repo-Cleaner` | Simple para archivos específicos | Baja |
| `git filter-branch` | Tradicional pero lenta | Alta |

**⚠️ Implicaciones de reescribir el historial:**
- Cambian todos los hashes de commits posteriores al archivo eliminado
- Todos los colaboradores deben ejecutar `git fetch && git reset --hard origin/<branch>`
- Requiere `git push --force` al repositorio remoto
- Puede romper referencias en PRs, issues y CI/CD

**Recomendación**: Dado que la criticidad es reducida y `protected_values.py` nunca fue
expuesto, es preferible **rotar la clave Fernet** en lugar de reescribir el historial.

#### Proceso obligatorio en despliegue (dev/pre/pro)

**⚠️ CRÍTICO**: Al desplegar en cualquier entorno que no sea macbook, es **OBLIGATORIO**
ejecutar el proceso de renovación de la clave Fernet:

```bash
# 1. Configurar valores únicos en protected_values.py del entorno
vim infrastructure/environments/<entorno>/protected_values.py
# Cambiar TODOS los valores sensibles:
# - jwt_access_secret
# - jwt_session_secret
# - writer_password
# - reader_password
# - redis_password
# - (otros secretos específicos del entorno)

# 2. Generar nueva clave Fernet y re-encriptar contraseñas
./scripts/renewall_fernet_key.sh --dry-run  # Verificar primero
./scripts/renewall_fernet_key.sh            # Aplicar cambios

# 3. Verificar que el sistema funciona con las nuevas claves
# Reiniciar todos los servicios y probar login
```

**Checklist de despliegue seguro:**

- [ ] `protected_values.py` tiene valores únicos para el entorno
- [ ] `basesecuritypass.json` tiene una clave Fernet nueva (generada con el script)
- [ ] Contraseñas en `users.json` re-encriptadas con la nueva clave
- [ ] Login funciona correctamente después del cambio
- [ ] Backups creados antes de la renovación

#### Valores que deben ser únicos por entorno

El archivo `infrastructure/environments/<entorno>/protected_values.py` debe contener
valores **DIFERENTES** para cada entorno:

```python
# Ejemplo de protected_values.py para un entorno
jwt_access_secret = "VALOR_UNICO_GENERADO_PARA_ESTE_ENTORNO"
jwt_session_secret = "OTRO_VALOR_UNICO_GENERADO"
writer_password = "PASSWORD_BD_ESCRITURA_UNICO"
reader_password = "PASSWORD_BD_LECTURA_UNICO"
redis_password = "PASSWORD_REDIS_UNICO"
# ... otros valores sensibles
```

**Generación de secretos seguros:**

```bash
# Generar un secreto aleatorio de 32 bytes en base64
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generar una clave Fernet válida
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**IMPORTANTE**: Nunca reutilices valores de un entorno a otro. Cada entorno debe ser
completamente independiente en términos de credenciales y secretos.

## Servicio frontend en contenedor

El servicio `7_service_frontend` puede ejecutarse de forma independiente en Docker
usando el compose del servidor frontend.

```bash
docker compose -f infrastructure/servers/frontend/docker-compose.yml up --build
```

Para inyectar variables por entorno, se recomienda generar un envfile con:
`python infrastructure/export_env.py --environment <entorno> --format envfile`.

Variables relevantes (ver `src/apps/7_service_frontend/.env.example`):
- `JWT_ACCESS_SECRET`
- `JWT_SESSION_SECRET`
- `JWT_ALGORITHM`
- `BACKEND_BASE_URL`
- `SERVICE_HOST`
- `SERVICE_PORT`
- `SERVICE_RELOAD`
- `USERS_DATA_PATH`
- `ORGANIZATIONS_DATA_PATH`
- `SESSIONS_DATA_PATH` (opcional, sobrescribe `src/2_shared_application/moks/sessions.json`)
- `FERNET_KEY_PATH`
- `ACTIVITY_LOG_PATH` (opcional, sobrescribe la ruta de `middleware_activiy.log`)
- `STORAGE_MODE` (modos: `mock`, `mock_and_db`, `db_only`)
- `BROKER_BACKEND_BASE_URL` (URL del broker backend)
- `SYNC_DATABASE_INTERVAL_SECONDS` (intervalo de sincronización DB/JSON)
- `ACTIVE_SYNC_DB_JSONS` (switch de sincronización DB/JSON)

Dependencias del servicio (pip):
- `src/apps/7_service_frontend/requirements.txt`

### Modos de almacenamiento (storage_mode)

El sistema puede operar con tres modos configurables mediante `storage_mode` en `env.yaml`:

| Modo | Descripción | Uso recomendado |
|------|-------------|-----------------|
| `mock` | Solo archivos JSON | Pruebas sin base de datos |
| `mock_and_db` | JSON + sincronización con MariaDB | Desarrollo híbrido |
| `db_only` | Solo MariaDB (lectura/escritura) | **Desarrollo normal y producción** |

**Flujo de datos con `db_only`:**
```
Frontend/Backoffice → Middleware → Broker → Backend Core → MariaDB
```

Cuando el modo es `mock_and_db` o `db_only`, el middleware delega persistencia en el
broker backend (`8_service_backend`) mediante `BROKER_BACKEND_BASE_URL`.

### Sincronización DB → JSON (active_sync_db_jsons)

La variable `active_sync_db_jsons` controla la sincronización periódica de MariaDB a JSON:

| Valor | Descripción | Entornos permitidos |
|-------|-------------|---------------------|
| `"1"` | Habilitada - copia datos de MariaDB a JSON cada N segundos | macbook, dev, pre |
| `"0"` | Deshabilitada | **pro (obligatorio)** |

**CRÍTICO para producción:**
- En producción (`ENVIRONMENT=pro`), la sincronización está **deshabilitada por seguridad**
- No se deben exponer datos en archivos JSON en producción
- El código valida automáticamente y bloquea la sincronización en producción

### Seguridad en producción (entorno pro)

El entorno de producción tiene restricciones especiales:

1. **storage_mode obligatorio:** Solo se permite `db_only`
2. **Sincronización deshabilitada:** `active_sync_db_jsons` debe ser `"0"`
3. **Sin archivos moks:** Los Dockerfiles eliminan automáticamente la carpeta `moks`
4. **Validación en código:** El middleware fuerza `db_only` si detecta otro modo en producción

**Build de Docker para producción:**
```bash
docker build --build-arg ENVIRONMENT=pro -t mi-app:pro .
```

Esto automáticamente:
- Establece `ENVIRONMENT=pro` en el contenedor
- Elimina la carpeta `src/2_shared_application/moks`
- El middleware valida y fuerza `db_only`

### Base de datos de proyectos (sin mocks)

La base de datos `myllm_projects_db` **no** tiene espejo en ficheros JSON de
`src/2_shared_application/moks`. Todas las operaciones contra esta base de datos
se realizan **directamente en MariaDB**, sin fallback ni sincronización con mocks.

Notas de UX y trazabilidad (Flujos):
- El selector de proyectos **solo** muestra el nombre del proyecto; el `id` se usa
  internamente y puede registrarse en logs para trazabilidad.
- El selector de versiones **sí** muestra el `id_version` (visible para el usuario),
  ya que es el identificador usado en consultas a `versiones` y `estado`.

### Configuración de permisos MariaDB (CRÍTICO)

El Backend Core utiliza **dos usuarios de MariaDB** según el tipo de operación:

| Usuario | Propósito | Operaciones |
|---------|-----------|-------------|
| `myllm_reader` | Solo lectura | SELECT |
| `myllm_writer` | Escritura | INSERT, UPDATE, DELETE, EXECUTE |

#### Script de permisos completo

Ejecutar como root en MariaDB antes de usar las funcionalidades de proyectos y roles:

```sql
-- ============================================================================
-- PERMISOS PARA myllm_writer EN myllm_projects_db
-- ============================================================================

-- Tablas: SELECT, INSERT, UPDATE, DELETE
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.proyectos TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.proyectos_roles TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT ON myllm_projects_db.cambios TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE ON myllm_projects_db.estado TO 'myllm_writer'@'localhost';
GRANT SELECT ON myllm_projects_db.flujos TO 'myllm_writer'@'localhost';
GRANT SELECT ON myllm_projects_db.proyectos_roles_base TO 'myllm_writer'@'localhost';

-- Stored Procedures: EXECUTE
GRANT EXECUTE ON PROCEDURE myllm_projects_db.sp_registrar_cambio_proyecto TO 'myllm_writer'@'localhost';

-- ============================================================================
-- PERMISOS PARA myllm_reader EN myllm_projects_db (solo lectura)
-- ============================================================================

GRANT SELECT ON myllm_projects_db.proyectos TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.proyectos_roles TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.cambios TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.estado TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.flujos TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.proyectos_roles_base TO 'myllm_reader'@'localhost';

-- ============================================================================
-- PERMISOS PARA myllm_writer EN myllm_core_db
-- ============================================================================

GRANT SELECT, UPDATE ON myllm_core_db.users TO 'myllm_writer'@'localhost';

-- ============================================================================
-- Aplicar cambios
-- ============================================================================

FLUSH PRIVILEGES;
```

#### Stored Procedure requerido

Si el SP no existe, crearlo:

```sql
USE myllm_projects_db;

DROP PROCEDURE IF EXISTS sp_registrar_cambio_proyecto;

DELIMITER //

CREATE PROCEDURE sp_registrar_cambio_proyecto(
    IN p_id_proyecto INT,
    IN p_id_organizacion INT,
    IN p_tipo_cambio VARCHAR(100),
    IN p_descripcion VARCHAR(255),
    IN p_id_usuario INT
)
BEGIN
    DECLARE v_fecha_actual TIMESTAMP DEFAULT NOW();
    DECLARE v_id_version INT DEFAULT 1;
    
    SELECT COALESCE(MAX(id_version), 1) INTO v_id_version
    FROM estado 
    WHERE id_proyecto = p_id_proyecto AND id_organizacion = p_id_organizacion;
    
    INSERT INTO cambios (
        id_version, fecha_cambio, tipo_cambio, descripcion, 
        creado_at, id_proyecto, id_organizacion
    ) VALUES (
        v_id_version, v_fecha_actual, p_tipo_cambio, p_descripcion,
        v_fecha_actual, p_id_proyecto, p_id_organizacion
    );
    
    SELECT LAST_INSERT_ID() AS id_cambio, 'Cambio registrado' AS mensaje;
END //

DELIMITER ;

-- Otorgar permiso
GRANT EXECUTE ON PROCEDURE sp_registrar_cambio_proyecto TO 'myllm_writer'@'localhost';
FLUSH PRIVILEGES;
```

#### Verificar permisos

```sql
SHOW GRANTS FOR 'myllm_writer'@'localhost';
SHOW GRANTS FOR 'myllm_reader'@'localhost';
SHOW PROCEDURE STATUS WHERE Db = 'myllm_projects_db';
```

#### Archivos de migración

Las migraciones SQL están en `infrastructure/database/migrations/`:

| Archivo | Contenido |
|---------|-----------|
| `001_create_flujos_table.sql` | Catálogo de flujos de trabajo |
| `002_flujo_historico_y_trigger.sql` | Historial de cambios de flujo |
| `003_triggers_proyecto_estado_cambios.sql` | Triggers y SP para automatización |
| `004_proyectos_roles_table.sql` | Tabla de asignación usuario-proyecto-rol |
| `005_proyectos_roles_base_table.sql` | Catálogo maestro de roles de proyecto |

### Sincronización OTP (frontend y middleware)

Cuando se actualiza el OTP de un usuario, el cambio se persiste **en JSON y en
MariaDB de forma sincrónica** (modo `mock_and_db` o `db_only`). Se añade una
validación de consistencia que compara los OTP entre `users.json` y la tabla
`users`, registrando el resultado en:

- `src/apps/5_web_frontend/logs/frontend_secure.log`

### Envío de SMS con verificación de entrega (Infobip)

El sistema utiliza la API de **Infobip** para enviar mensajes SMS (códigos OTP).
A partir de ahora, la aplicación **verifica automáticamente el estado final de entrega**
de cada mensaje SMS para garantizar que llegó al dispositivo del destinatario.

#### Estados de entrega

Infobip devuelve múltiples estados durante el ciclo de vida de un SMS:

| Estado | Tipo | Descripción |
|--------|------|-------------|
| `PENDING_ACCEPTED` | Intermedio | Mensaje aceptado por Infobip y enviado al operador móvil |
| `PENDING` | Intermedio | Mensaje en tránsito |
| `DELIVERED_TO_HANDSET` | **Final** | ✅ Mensaje entregado exitosamente al dispositivo |
| `DELIVERED_TO_NETWORK` | **Final** | ✅ Mensaje entregado a la red del operador |
| `REJECTED` | **Final** | ❌ Mensaje rechazado por el operador |
| `REJECTED_NETWORK` | **Final** | ❌ Mensaje rechazado por la red |
| `UNDELIVERABLE` | **Final** | ❌ Mensaje no se pudo entregar |
| `EXPIRED` | **Final** | ❌ Mensaje expiró antes de entregarse |

**Importante**: El estado `PENDING_ACCEPTED` NO significa que el mensaje fue entregado.
Solo indica que fue aceptado por Infobip y enviado al operador. La entrega real puede
tardar entre 3 y 30 segundos adicionales.

#### Verificación automática de entrega

La función `send_message_by_sms()` en `src/2_shared_application/security/common_security.py`
ahora detecta automáticamente estados intermedios (`PENDING_*`) y consulta el **delivery report**
de Infobip para obtener el estado final:

```python
# En common_security.py
from .sms_delivery_checker import check_sms_delivery_status

# Si recibe estado intermedio, verifica el delivery status final
delivered, final_status, delivery_report = check_sms_delivery_status(
    message_id=message_id,
    api_url=sms_api_url,
    api_key=sms_api_key,
    max_wait_seconds=30,  # Espera hasta 30 segundos
    check_interval=5,      # Consulta cada 5 segundos
)
```

El proceso completo:
1. **Envío inicial**: Se envía el SMS a Infobip vía `POST /sms/2/text/advanced`
2. **Respuesta inmediata**: Infobip devuelve `PENDING_ACCEPTED` con un `messageId`
3. **Verificación automática**: Si el estado es intermedio, se activa el verificador
4. **Polling**: Consulta `GET /sms/3/reports?messageId={id}` cada 5 segundos
5. **Estado final**: Cuando Infobip devuelve `DELIVERED_TO_HANDSET`, se confirma la entrega
6. **Logging**: Se registra el estado final en `frontend_secure.log`

#### Módulo `sms_delivery_checker.py`

Ubicación: `src/2_shared_application/security/sms_delivery_checker.py`

**Función principal**:

```python
def check_sms_delivery_status(
    message_id: str,
    api_url: str,
    api_key: str,
    max_wait_seconds: int = 30,
    check_interval: int = 5,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verifica el estado final de entrega de un mensaje SMS.

    Returns:
        Tupla de (delivered, status_name, full_report):
        - delivered (bool): True si el mensaje fue entregado exitosamente
        - status_name (str): Nombre del estado final (ej: "DELIVERED_TO_HANDSET")
        - full_report (dict): Delivery report completo de Infobip
    """
```

**Uso standalone**:

```python
from src.2_shared_application.security.sms_delivery_checker import check_sms_delivery_status

delivered, status, report = check_sms_delivery_status(
    message_id="4700646034707951434964",
    api_url="https://pdy6d3.api.infobip.com",
    api_key="your-api-key",
    max_wait_seconds=30,
    check_interval=5,
)

if delivered:
    print(f"✅ SMS entregado: {status}")
    print(f"Enviado: {report['sentAt']}")
    print(f"Entregado: {report['doneAt']}")
else:
    print(f"❌ SMS no entregado: {status}")
```

#### Configuración

Las credenciales de Infobip deben estar configuradas en
`infrastructure/environments/{entorno}/protected_values.py`:

```python
# API de Infobip para envío de SMS
sms_api_url = "https://pdy6d3.api.infobip.com"
sms_api_key = "tu-api-key-de-infobip"
sms_from = "InfoSMS"  # Sender ID
```

#### Testing

**Test manual con script**:

```bash
cd /Users/administrator/develop/anewhope
python test_sms_with_verification.py
```

Este script:
1. Envía un SMS de prueba al número configurado
2. Muestra el estado inicial (normalmente `PENDING_ACCEPTED`)
3. Verifica automáticamente el delivery status
4. Muestra el estado final (`DELIVERED_TO_HANDSET` si todo va bien)
5. Muestra el tiempo total de entrega (típicamente 3-6 segundos)

**Test automatizado**:

```bash
cd src/apps/5_web_frontend
source .venv_frontend313/bin/activate
pytest tests/test_change_password.py::test_request_otp_for_adminone_user -v
```

Este test:
- Simula una solicitud de OTP para el usuario `adminone`
- Verifica que el SMS se envía correctamente
- Confirma que el estado final es `DELIVERED_TO_HANDSET`
- Valida que el OTP se guardó en la base de datos

#### Logs

Los envíos de SMS se registran en:

```
src/apps/5_web_frontend/logs/frontend_secure.log
```

Ejemplo de log exitoso:

```
2026-02-02 20:36:43 | INFO     | common_security | 📤 SMS enviado - Status: PENDING_ACCEPTED, MessageId: 4700664472197950960814
2026-02-02 20:36:43 | INFO     | common_security | ⏳ Estado intermedio detectado (PENDING_ACCEPTED). Verificando delivery status final...
2026-02-02 20:36:46 | INFO     | sms_delivery_checker | Delivery report obtenido - MessageId: 4700664472197950960814, Status: DELIVERED_TO_HANDSET
2026-02-02 20:36:46 | INFO     | common_security | ✅ Estado final verificado: DELIVERED_TO_HANDSET - ✅ Mensaje entregado exitosamente al dispositivo
```

#### Troubleshooting

**Problema**: SMS marcado como "enviado" pero no llega al móvil

**Diagnóstico**:
1. Verificar el log en `frontend_secure.log`
2. Buscar el `messageId` del mensaje
3. Verificar el estado final registrado

**Causas comunes**:

| Estado Final | Causa | Solución |
|--------------|-------|----------|
| `REJECTED` | Número inválido o bloqueado | Verificar formato del número (+34...) |
| `REJECTED_NETWORK` | Operador rechazó el mensaje | Verificar sender ID y cuenta Infobip |
| `EXPIRED` | Mensaje no entregado en tiempo límite | El móvil estuvo apagado o sin cobertura |
| `TIMEOUT` | No se obtuvo estado final en 30s | Red lenta o problema en Infobip |

**Verificación manual en Infobip**:
1. Acceder a https://portal.infobip.com
2. Ir a "Logs" → "SMS Logs"
3. Buscar el `messageId`
4. Revisar el "Delivery Report" completo

**Problema**: Error "requests module not found"

**Solución**:
```bash
source src/apps/5_web_frontend/.venv_frontend313/bin/activate
pip install requests
```

### Agentes automáticos por proyecto

Al crear un proyecto, el sistema genera **4 agentes automáticos** asociados a la
organización y al proyecto, con nombres `agente_rol_organizacion_proyecto` y roles:

- `identity_type_id=10`: administrador
- `identity_type_id=11`: editor
- `identity_type_id=12`: lector
- `identity_type_id=13`: auditor

Estos agentes se almacenan en `users.json` y en la tabla `users` para asegurar
trazabilidad. El email se construye como `{nombre}@tfmmyllm.ai` y el OTP se genera
con 4 dígitos.

### Sincronización periódica DB/JSON (middleware)

Cuando `STORAGE_MODE` es `mock_and_db` o `db_only`, el middleware ejecuta una
sincronización periódica entre las tablas de MariaDB (vía broker backend) y los
ficheros JSON locales. Ante diferencias, **prevalece la base de datos** y se
reescriben los JSON para mantener coherencia.

Configuración:
- `SYNC_DATABASE_INTERVAL_SECONDS`: intervalo de sincronización en segundos
  (por defecto `300`, mínimo `30`).

Logs:
- `src/apps/7_service_frontend/logs/sync_database_and_jsons.log` registra los
  cambios detectados y las acciones aplicadas para regularizar datos.

Recomendación para producción:
- `ACTIVE_SYNC_DB_JSONS=0`
- `STORAGE_MODE="db_only"` en `.env`

### Broker backend y backend core

El broker backend (`8_service_backend`) recibe operaciones desde el middleware y
las reenvía al backend core (`3_backend`) cuando se trata de datos o filesystem.
Por ahora, el backend core usa los mocks JSON, pero su capa de infraestructura está
lista para conectar con MariaDB y la API externa `fmanagement` en futuras iteraciones.

Variables relevantes (broker):
- `CORE_BACKEND_BASE_URL`
- `BROKER_ACTIVITY_LOG_PATH` (opcional, ruta del log de actividad)

Variables relevantes (core):
- `CORE_ACTIVITY_LOG_PATH` (opcional, ruta del log de actividad)
- `USERS_DATA_PATH`, `ORGANIZATIONS_DATA_PATH`, `ROLES_DATA_PATH`,
  `BASIC_PERMISSIONS_PATH`, `LOW_LEVEL_PERMISSIONS_PATH`,
  `MANAGE_ROLES_BY_ORG_PATH` (mocks JSON)

### Ejemplos de despliegue en servidores (contenedores)

Servidor **Frontend** (web + middleware):

```bash
cd /Users/administrator/develop/anewhope
docker compose -f src/apps/5_web_frontend/docker-compose.yml up --build -d
docker compose -f src/apps/7_service_frontend/docker-compose.yml up --build -d
```

Servidor **Backend** (broker + core):

```bash
cd /Users/administrator/develop/anewhope
docker compose -f src/apps/3_backend/docker-compose.yml up --build -d
docker compose -f src/apps/8_service_backend/docker-compose.yml up --build -d
```

Ejemplo de configuración en el middleware para trabajar con el broker:

```bash
export STORAGE_MODE=db_only
export BROKER_BACKEND_BASE_URL=http://<ip-backend>:8008
```

Ejemplo de configuración en el broker para apuntar al core:

```bash
export CORE_BACKEND_BASE_URL=http://<ip-backend>:8003
```

### Sesiones y auditoría (middleware)

El middleware mantiene un registro temporal de sesiones y auditoría en
`src/2_shared_application/moks/sessions.json` (estructura `sessions` y `auth_logs`).
Se añade `jti` y `session_id` a los JWT (HS256) para validar que la sesión está activa
y no ha sido revocada, y para cerrar sesiones de forma explícita.
Estados soportados: `active`, `inactive`, `revoked`, `expired`.

Regla de seguridad: tres intentos de login fallidos consecutivos dentro de una ventana de 10 minutos
registran el bloqueo del usuario en el mock de usuarios (`blocked=true`) hasta nueva intervención.

Endpoint relevante:
- `POST /logout` invalida la sesión actual (marca `inactive`).

Directiva **security by design**: los tokens no se aceptan si no están vinculados a una sesión activa
en `sessions.json` con `session_id` y `jti` coincidentes. Al cerrar sesión se invalida la sesión y
se rechazan tokens antiguos, evitando reutilización si son filtrados.

Directiva **security by default**: cualquier token emitido queda invalidado tras logout; si el usuario
quiere acceder de nuevo, debe autenticarse con credenciales y OTP para generar una nueva sesión válida.

#### Entidades compartidas de sesión

Para reutilizar la lógica de sesión y permisos entre aplicaciones, se añaden entidades
compartidas en `src/1_shared_domain/entities/session.py` y DTOs en
`src/2_shared_application/dtos/session_dtos.py`:

- `SessionStatus`: estados de sesión (`active`, `inactive`, `revoked`, `expired`).
- `SessionTokenBinding`: JTIs asociados a la sesión.
- `Session`: entidad principal de sesión con `session_id`, usuario, estado y expiración.
- `UserSessionContext`: contexto mínimo para validar permisos en otras capas.

El acceso a persistencia se estandariza con el repositorio `SessionRepository` en
`src/2_shared_application/interfaces/session_repository.py`.

## Web frontend (Reflex)

Regla de puertos: cada aplicación usa **8000 + el primer número del nombre de la carpeta**.

- `3_backend` → **8003** (Backend Core - datos, usuarios, permisos)
- `4_trainer` → **8004** (Backend IA - entrenamiento, modelos, métricas)
- `5_web_frontend` → **8005**
- `6_web_backoffice` → **8006** (reservado)
- `7_service_frontend` → **8007**
- `8_service_backend` → **8008** (Broker - enruta a Core e IA)

La aplicación web (`5_web_frontend`) usa **puerto backend fijo 8005** para el servidor interno de Reflex. Esto se configura en `src/apps/5_web_frontend/rxconfig.py` con `backend_port=8005` y no debe cambiarse para evitar conflictos con el middleware.

## TODO

- Evaluar migración a Python 3.14 cuando `pydantic-core` y Reflex certifiquen compatibilidad.
- Tests verificados con `./full_test.sh` en Python 3.13 sin warning de Pydantic (2026-01-19).

## Modelo de Dominio

El módulo `src/1_shared_domain/entities/domain_models.py` contiene las entidades centrales del sistema, diseñadas siguiendo principios de Domain-Driven Design (DDD).

### Entidades principales

#### `Organization`
Representa una organización en el sistema. Múltiples usuarios pueden pertenecer a la misma organización.

**Atributos:**
- `organization_id`: Identificador único
- `organization_name`: Nombre de la organización
- `organization_email`: Email de contacto (validado)
- `organization_tlf`: Teléfono de contacto
- `organization_address`: Dirección física
- `organization_country`: País
- `organization_state`: Estado/Provincia

**Características:**
- Validación de email en constructor y setters
- Métodos: `update_contact_info()`, `is_valid()`
- Comparación por ID (`__eq__`, `__hash__`)

#### `IdentityGlobal`
Define tipos de identidad con roles y permisos asociados. Se relaciona con `User` a través de `identity_type_id`.

**Atributos:**
- `identity_type_id`: Identificador único
- `identity_type_name`: Nombre del tipo (ej: "Admin", "Usuario")
- `identity_type_rol`: Rol asociado
- `identity_type_group_permissions`: Lista de objetos `Permissions`

**Características:**
- Gestión de permisos: `add_permission()`, `remove_permission()`, `has_permission()`
- Validaciones en todos los setters
- Comparación por ID (`__eq__`, `__hash__`)

#### `Permissions`
Representa un permiso con operaciones CRUD y acciones específicas.

**Atributos:**
- `id_permission`: Identificador único
- `permission_name`: Nombre del permiso
- `permission_description`: Descripción
- `enable`: Estado habilitado/deshabilitado
- `create`, `read`, `write`, `delete`, `execute`: Operaciones permitidas
- `log`: Indica si se registra en log
- `expired`: Fecha de expiración (`datetime | None`)

**Características:**
- Métodos: `is_expired()`, `is_active()`, `has_crud_permissions()`, `can_perform_action()`
- Validación de fecha de expiración
- Comparación por ID (`__eq__`, `__hash__`)

#### `User`
Entidad central que representa un usuario del sistema.

**Atributos:**
- `id`: Identificador único
- `organization_id`: Relación con `Organization`
- `identity_type_id`: Relación con `IdentityGlobal`
- `user_name`, `user_password`, `user_email`, `user_mobile`, `user_otp`
- `active`, `blocked`: Estados del usuario

**Invariantes:**
- Un usuario no puede estar activo y bloqueado simultáneamente
- Email debe tener formato válido
- Contraseña mínimo 8 caracteres
- OTP debe tener exactamente 4 dígitos

**Características:**
- Métodos: `activate_user()`, `deactivate_user()`, `block_user()`, `unblock_user()`, `can_perform_action()`, `generate_otp()`
- Validaciones completas en todos los setters
- Comparación por ID (`__eq__`, `__hash__`)

#### `Session`
Entidad que representa la sesión activa del usuario y su vínculo con tokens.

**Atributos:**
- `session_id`: Identificador único de sesión
- `user_id`, `organization_id`, `identity_type_id`
- `tokens`: JTIs asociados (`access_token_jti`, `session_token_jti`)
- `status`: Estado de sesión (`active`, `inactive`, `revoked`, `expired`)
- `created_at`, `last_activity`, `expires_at`

**Características:**
- Validación de estructura y expiración
- Métodos: `is_active()`, `is_expired()`, `mark_inactive()`, `mark_revoked()`

#### `UserExtended`
Extiende `User` con información de contacto adicional.

**Atributos adicionales:**
- `contact_info`: Objeto `ContactInfo` (inmutable)
- `billing_info`: Objeto `ContactInfo` para facturación

#### `UserGoogle`
Extiende `User` con autenticación OAuth de Google.

**Atributos adicionales:**
- `google_auth_info`: Objeto `GoogleAuthInfo` con tokens y datos de Google

**Características:**
- Métodos: `is_token_expired()`, `update_tokens()`
- Gestión automática de expiración de tokens

### Value Objects

#### `ContactInfo`
Value Object inmutable para información de contacto.

**Atributos:** `first_name`, `sur_name`, `country`, `state`, `zip_code`, `address`

#### `GoogleAuthInfo`
Value Object para datos de autenticación Google OAuth.

**Atributos:** `google_id`, `google_access_token`, `google_refresh_token`, `google_token_expires_at`, `google_picture_url`, `google_verified_email`

### Relaciones del modelo

```
Organization (1) ──< (N) User
IdentityGlobal (1) ──< (N) User
IdentityGlobal (1) ──< (N) Permissions
User (1) ──< (1) UserExtended
User (1) ──< (1) UserGoogle
```

### Características de diseño

- **Encapsulación:** Todos los atributos son privados con getters/setters
- **Validaciones:** Invariantes de dominio validadas en constructores y setters
- **Excepciones de dominio:** `DomainError` para errores de negocio
- **Comportamiento rico:** Métodos de dominio en lugar de simples DTOs
- **Inmutabilidad:** Value Objects como `ContactInfo` son inmutables
- **Comparación:** Entidades comparables por ID (`__eq__`, `__hash__`)

### Uso

```python
from src.1_shared_domain.entities.domain_models import (
    Organization, IdentityGlobal, Permissions, User, UserExtended, UserGoogle
)

# Crear organización
org = Organization(
    organization_id=1,
    organization_name="Mi Empresa",
    organization_email="contacto@empresa.com",
    organization_tlf="+1234567890",
    organization_address="Calle Principal 123",
    organization_country="España",
    organization_state="Madrid"
)

# Crear permisos
perm = Permissions(
    id_permission=1,
    permission_name="read_users",
    permission_description="Permite leer usuarios"
)

# Crear tipo de identidad con permisos
identity = IdentityGlobal(
    identity_type_id=1,
    identity_type_name="Admin",
    identity_type_rol="Administrator",
    identity_type_group_permissions=[perm]
)

# Crear usuario
user = User(
    user_id=1,
    organization_id=org.organization_id,
    identity_type_id=identity.identity_type_id,
    user_name="jdoe",
    password="securepass123",
    email="jdoe@empresa.com",
    mobile="+1234567890",
    otp="1234"
)
```

## Gestión de Proyectos

El sistema de gestión de proyectos permite crear, modificar y controlar proyectos de la organización
siguiendo el flujo de trabajo de generación de modelos LLM.

### Crear Proyecto (UI)

El botón "Crear proyecto" en la página Organización abre un modal con los siguientes campos:

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| Nombre | texto | Sí | Nombre del proyecto |
| Descripción | texto largo | No | Descripción del proyecto |

**Campos automáticos (enviados por el sistema):**
- `id_organizacion`: de la sesión de usuario
- `created_at`: fecha actual del sistema
- `active`: True (proyecto activo)
- `id_flujo`: 1 (Propuesta Cliente - primer paso)

### Flujo de creación

```
┌─────────────────┐      ┌──────────────┐      ┌────────┐      ┌──────────────┐      ┌──────────┐
│    Frontend     │ ──►  │  Middleware  │ ──►  │ Broker │ ──►  │ Backend Core │ ──►  │ MariaDB  │
│ save_new_project│      │ POST /projects│     │  route │      │ INSERT INTO  │      │ TRIGGERS │
└─────────────────┘      └──────────────┘      └────────┘      │  proyectos   │      └──────────┘
                                                                └──────────────┘           │
                                                                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ TRIGGERS AUTOMÁTICOS:                                                                         │
│ 1. tr_proyecto_after_insert → Crea registro en 'estado' (versión 1, campos según id_flujo=1)│
│ 2. tr_proyecto_after_insert → Crea registro en 'cambios' (tipo="Alta proyecto")              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Tipos de cambio registrados

La tabla `cambios` registra automáticamente (vía triggers) o manualmente (vía Backend Core):

| Tipo de cambio | Origen | Descripción |
|----------------|--------|-------------|
| Alta proyecto | Trigger INSERT | Al crear un nuevo proyecto |
| Modificación proyecto | Trigger UPDATE | Al cambiar nombre/descripción |
| Cambio de flujo | Trigger UPDATE | Al cambiar el paso del flujo |
| Borrado de proyecto | Trigger DELETE | Al eliminar un proyecto |
| Bloquear proyecto | Trigger UPDATE | Al bloquear un proyecto |
| Desbloquear proyecto | Trigger UPDATE | Al desbloquear un proyecto |
| Asignación usuario | Backend Core | Al asignar usuario al proyecto |
| Quitar usuario | Backend Core | Al quitar usuario del proyecto |
| Solicitud soporte proyecto | Backend Core | Al solicitar soporte técnico |
| Respuesta soporte proyecto | Backend Core | Al responder solicitud de soporte |

### Tabla `estado` (sincronizada automáticamente)

Cuando se crea un proyecto, el trigger crea un registro en `estado` con:

- `id_organizacion`: del proyecto
- `id_proyecto`: del proyecto creado
- `id_version`: 1 (primera versión)
- `creado_at`: fecha de creación
- `actualizado_at`: NULL (en alta)
- Campos booleanos del flujo: calculados según `id_flujo` (solo el paso actual y anteriores = TRUE)

**Función auxiliar:** `fn_get_estado_por_flujo(id_flujo, campo)` calcula si un campo debe estar a TRUE.

### Migraciones SQL

| Archivo | Descripción |
|---------|-------------|
| `001_create_flujos_table.sql` | Catálogo de pasos del flujo |
| `002_flujo_historico_y_trigger.sql` | Histórico de cambios de flujo |
| `003_triggers_proyecto_estado_cambios.sql` | Triggers para estado y cambios |

### Ejemplo de uso (SQL)

```sql
-- Ver proyectos con su estado actual
SELECT * FROM view_proyectos_completo WHERE id_organizacion = 1;

-- Ver cambios recientes
SELECT * FROM view_cambios_recientes WHERE id_proyecto = 1;

-- Avanzar proyecto al siguiente paso del flujo
UPDATE proyectos SET id_flujo = 2 WHERE id = 1;  -- El trigger actualiza estado y cambios
```

### Endpoints de API para Proyectos

El sistema expone endpoints REST en cada capa para gestionar proyectos:

| Endpoint | Método | Descripción | Permiso requerido |
|----------|--------|-------------|-------------------|
| `/projects/organization/{org_id}` | GET | Listar proyectos de organización | project_read |
| `/projects` | POST | Crear nuevo proyecto | project_create |
| `/projects/{project_id}` | PATCH | Actualizar proyecto | project_update |
| `/projects/{project_id}` | DELETE | Eliminar proyecto | project_delete |
| `/projects/{project_id}/support` | POST | Solicitar soporte | (ninguno) |

**Flujo completo de cada endpoint:**

```
Frontend (api_client.py)
    │
    ▼
Middleware (apife.py + routermiddleware.py)
    │ Valida permisos (Security by Design)
    ▼
Broker (apibe.py + routerbroker.py)
    │ Enruta a Backend Core
    ▼
Backend Core (apicore.py + routercore.py)
    │ Ejecuta operación en BD
    ▼
MariaDB (myllm_projects_db)
    │ Triggers automáticos
    ▼
estado + cambios (registros auditados)
```

**Ejemplo de uso desde Frontend (Python):**

```python
from adapters.api_client import (
    get_organization_projects,
    create_organization_project,
    update_project_status,
    delete_organization_project,
    request_project_support_api,
)

# Listar proyectos
projects = get_organization_projects(
    organization_id=1,
    access_token=token,
    session_token=session,
)

# Crear proyecto
result = create_organization_project(
    organization_id=1,
    project_name="Nuevo LLM",
    project_description="Modelo de lenguaje personalizado",
    access_token=token,
    session_token=session,
)

# Bloquear proyecto
update_project_status(
    project_id=result["project_id"],
    locked=True,
    access_token=token,
    session_token=session,
)

# Solicitar soporte
request_project_support_api(
    project_id=result["project_id"],
    access_token=token,
    session_token=session,
)

# Eliminar proyecto
delete_organization_project(
    project_id=result["project_id"],
    access_token=token,
    session_token=session,
)
```

## Gestión de Tecnologías

El sistema permite asignar tecnologías de IA a los proyectos de la organización. Cada proyecto puede
tener una única tecnología asignada que define el enfoque de procesamiento del modelo LLM.

### Tabla de Tecnologías

Base de datos: `myllm_projects_db`, tabla: `tecnologia`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT | Identificador único de la tecnología |
| `name` | VARCHAR | Nombre de la tecnología (RAG, Fine-tuning, etc.) |
| `descripcion` | TEXT | Descripción detallada de la tecnología |
| `active` | TINYINT | 1=Activa, 0=Inactiva (visible pero no seleccionable) |

### Tecnologías disponibles

| ID | Nombre | Descripción | Activa |
|----|--------|-------------|--------|
| 1 | RAG | Generación Aumentada por Recuperación - combina LLM con datos externos | Sí |
| 2 | Knowledge Graphs | Conecta datos mediante nodos y relaciones (metadatos complejos) | No |
| 3 | Long Context Windows | Inyecta estructura documental directamente en el prompt | No |
| 4 | Agentic RAG | Agentes que deciden cómo buscar según metadatos | No |
| 5 | Semantic Caching | Cache semántico para consultas frecuentes | No |
| 6 | DSPy | Optimización automática de uso de documentos | No |
| 7 | Fine-tuning | Especialización del modelo en dominio específico | No |
| 8 | Creación de Agentes | Agentes de IA autónomos para alcanzar objetivos | No |

### Tabla de Asignación Proyecto-Tecnología

Base de datos: `myllm_projects_db`, tabla: `proyectos_tecnologia`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT | Identificador único de la asignación |
| `id_proyecto` | INT | ID del proyecto (UNIQUE - un proyecto solo tiene una tecnología) |
| `id_tecnologia` | INT | ID de la tecnología asignada |
| `coste_base` | VARCHAR | Coste base del proyecto (default: "17% sobre base") |

### Reglas de Negocio

| Regla | Descripción |
|-------|-------------|
| **Una tecnología por proyecto** | Cada proyecto solo puede tener una tecnología asignada (constraint UNIQUE en `id_proyecto`) |
| **Frontend: asignar una vez** | El frontend solo permite asignar tecnología si el proyecto no tiene ninguna asignada |
| **Backoffice: modificar siempre** | El backoffice puede cambiar la tecnología asignada en cualquier momento |
| **Tecnologías inactivas** | Las tecnologías con `active=0` se muestran en la lista pero aparecen deshabilitadas |
| **Coste base por defecto** | Si no se especifica, el coste base es "17% sobre base" |

### Flujo de Asignación

```
┌─────────────────┐      ┌──────────────┐      ┌────────┐      ┌──────────────┐      ┌──────────┐
│    Frontend     │ ──►  │  Middleware  │ ──►  │ Broker │ ──►  │ Backend Core │ ──►  │ MariaDB  │
│ POST (primera)  │      │     /api     │      │  8008  │      │     8003     │      │          │
│ (sin tech prev) │      └──────────────┘      └────────┘      └──────────────┘      └──────────┘
└─────────────────┘                                                                        │
                                                                                           ▼
┌─────────────────┐      ┌──────────────┐      ┌────────┐      ┌──────────────┐      ┌──────────┐
│   Backoffice    │ ──►  │  Middleware  │ ──►  │ Broker │ ──►  │ Backend Core │ ──►  │ MariaDB  │
│ PATCH (siempre) │      │     /api     │      │  8008  │      │     8003     │      │          │
│ (puede cambiar) │      └──────────────┘      └────────┘      └──────────────┘      └──────────┘
```

### Endpoints de API

| Método | Endpoint | Descripción | Cliente |
|--------|----------|-------------|---------|
| GET | `/tecnologias` | Lista todas las tecnologías (activas e inactivas) | Frontend/Backoffice |
| GET | `/proyectos/{id}/tecnologia` | Obtiene la tecnología asignada a un proyecto | Frontend/Backoffice |
| POST | `/proyectos/{id}/tecnologia` | Asigna tecnología a proyecto (primera vez) | Frontend |
| PATCH | `/proyectos/{id}/tecnologia` | Actualiza tecnología de proyecto | Backoffice |

### Request de Asignación/Actualización

```json
{
  "id_tecnologia": 1,
  "coste_base": "17% sobre base"
}
```

### Response de Tecnología Asignada

```json
{
  "success": true,
  "asignacion": {
    "id": 1,
    "id_proyecto": 5,
    "id_tecnologia": 1,
    "coste_base": "17% sobre base",
    "tecnologia_name": "RAG"
  }
}
```

### Uso en Frontend (Reflex)

```python
# Cargar tecnologías
from adapters.api_client import get_tecnologias, get_proyecto_tecnologia, asignar_tecnologia

# Obtener lista de tecnologías
result = get_tecnologias(access_token=token, session_token=session)
tecnologias = result.get("tecnologias", [])

# Verificar si proyecto tiene tecnología
result = get_proyecto_tecnologia(project_id=5, access_token=token, session_token=session)
if result.get("asignacion"):
    # Proyecto ya tiene tecnología - mostrar info y deshabilitar cambio
    pass
else:
    # Proyecto sin tecnología - permitir asignar
    pass

# Asignar tecnología (solo si no tiene)
result = asignar_tecnologia(
    project_id=5,
    id_tecnologia=1,
    access_token=token,
    session_token=session,
)
```

### Uso en Backoffice (Reflex)

```python
from adapters.api_client import actualizar_tecnologia

# Cambiar tecnología (siempre permitido en backoffice)
result = actualizar_tecnologia(
    project_id=5,
    id_tecnologia=2,  # Nueva tecnología
    coste_base="20% sobre base",
    access_token=token,
    session_token=session,
)
```

### Tests

Los tests de tecnologías se encuentran en:

| Archivo | Entorno Virtual | Descripción |
|---------|-----------------|-------------|
| `src/apps/3_backend/tests/test_tecnologias_api.py` | `.venv_middleware313` | Tests de DTOs, validación y lógica de negocio |
| `src/apps/7_service_frontend/tests/test_tecnologias_middleware.py` | `.venv_middleware313` | Tests de estructuras y reglas de negocio |

Ejecutar tests:
```bash
./full_test.sh
# O individualmente:
source .venv_middleware313/bin/activate
pytest -v src/apps/3_backend/tests/test_tecnologias_api.py
pytest -v src/apps/7_service_frontend/tests/test_tecnologias_middleware.py
```

---

## Gestión de Versiones de Proyectos (Proyecciones)

El sistema permite administrar las versiones de los proyectos y organizar el repositorio de contenidos
para el entrenamiento de modelos LLM. Cada proyecto puede tener múltiples versiones numeradas secuencialmente.

### Tabla de Versiones

Base de datos: `myllm_projects_db`, tabla: `versiones`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_version` | INT | Número de versión dentro del proyecto (1, 2, 3, ...) |
| `id_proyecto` | INT | ID del proyecto al que pertenece |
| `id_organizacion` | INT | ID de la organización (para aislamiento) |

**Constraint UNIQUE**: (`id_proyecto`, `id_version`) - Cada proyecto tiene sus versiones numeradas desde 1.

### Formato de Carpetas

El sistema utiliza identificadores formateados para organizar el sistema de archivos:

| Entidad | Función Helper | Formato | Ejemplo |
|---------|----------------|---------|---------|
| Organización | `get_folder_by_id_organization(1)` | `ORG####` | `ORG0001` |
| Proyecto | `get_folder_by_id_project(2)` | `PRJ####` | `PRJ0002` |
| Versión | `get_folder_by_id_version(3)` | `v###` | `v003` |

**Helper disponible**: `src/2_shared_application/storage_access_structure.py`

### Componente UI (3 Capas)

La página de Proyecciones está dividida en 3 capas funcionales:

#### Capa 1: Selector de Proyecto
- Dropdown con proyectos activos y existentes de la organización
- Al seleccionar un proyecto, se generan automáticamente:
  - `proyecciones_org_folder`: Ej. `ORG0001`
  - `proyecciones_prj_folder`: Ej. `PRJ0002`
- Se cargan las versiones asociadas al proyecto

#### Capa 2: Selector de Versión + Botón Crear
- Dropdown con versiones del proyecto formateadas: `v001`, `v002`, `v003`, ...
- Botón "Crear nueva versión" que:
  - Calcula el siguiente `id_version` (MAX + 1)
  - Inserta en tabla `versiones`
  - Recarga la lista automáticamente
- Al seleccionar una versión, se genera:
  - `proyecciones_version_folder`: Ej. `v003`

#### Capa 3: Explorador de Archivos (Placeholder)
- Recibe contexto completo: `ORG0001` / `PRJ0002` / `v003`
- Componente complejo a implementar próximamente
- Permitirá navegar y gestionar archivos de la versión

### Flujo de Creación de Versión

```
┌─────────────────┐      ┌──────────────┐      ┌────────┐      ┌──────────────┐      ┌──────────┐
│ Frontend/       │ ──►  │  Middleware  │ ──►  │ Broker │ ──►  │ Backend Core │ ──►  │ MariaDB  │
│ Backoffice      │      │     /api     │      │  8008  │      │     8003     │      │          │
│ POST /versiones │      └──────────────┘      └────────┘      └──────────────┘      └──────────┘
└─────────────────┘                                                                        │
                                                                                           ▼
                   1. Backend Core calcula: SELECT MAX(id_version) + 1 WHERE id_proyecto=X
                   2. Inserta nueva versión: INSERT INTO versiones (id_version, id_proyecto, id_organizacion)
                   3. Retorna versión creada con version_folder formateado
```

### Endpoints de API

| Método | Endpoint | Descripción | Cliente |
|--------|----------|-------------|---------|
| GET | `/proyectos/{id}/versiones?org_id={org_id}` | Lista versiones de un proyecto | Frontend/Backoffice |
| POST | `/proyectos/{id}/versiones` | Crea nueva versión (auto-incrementa) | Frontend/Backoffice |

### Request de Creación de Versión

```json
{
  "id_proyecto": 2,
  "id_organizacion": 5
}
```

### Response de Lista de Versiones

```json
{
  "versiones": [
    {
      "id_version": 1,
      "id_proyecto": 2,
      "id_organizacion": 5,
      "version_folder": "v001"
    },
    {
      "id_version": 2,
      "id_proyecto": 2,
      "id_organizacion": 5,
      "version_folder": "v002"
    }
  ],
  "total": 2
}
```

### Response de Creación de Versión

```json
{
  "success": true,
  "version": {
    "id_version": 3,
    "id_proyecto": 2,
    "id_organizacion": 5,
    "version_folder": "v003"
  },
  "mensaje": "Versión v003 creada correctamente"
}
```

### Uso en Frontend/Backoffice (Reflex)

```python
from adapters.api_client import get_project_versions, create_project_version

# Obtener versiones de un proyecto
versiones = get_project_versions(
    project_id=2,
    access_token=token,
    session_token=session,
)

# Versiones retornadas: [{"id_version": 1, "version_folder": "v001"}, ...]

# Crear nueva versión (calcula automáticamente el siguiente id_version)
result = create_project_version(
    project_id=2,
    organization_id=5,
    access_token=token,
    session_token=session,
)

if result.get("success"):
    nueva_version_folder = result["version"]["version_folder"]  # "v003"
    nueva_version_id = result["version"]["id_version"]  # 3
```

### Estado en Reflex (Componente de 3 capas)

```python
# Estado para gestión de proyecciones
proyecciones_project_id: int = 0          # ID del proyecto seleccionado
proyecciones_project_name: str = ""       # Nombre del proyecto
proyecciones_versions: list[dict] = []    # Lista de versiones del proyecto
proyecciones_version_id: int = 0          # ID de versión seleccionada
proyecciones_version_folder: str = ""     # Carpeta formateada (v001, v002, etc.)
proyecciones_org_folder: str = ""         # Carpeta de organización (ORG0001)
proyecciones_prj_folder: str = ""         # Carpeta de proyecto (PRJ0002)
```

### Helpers de Formato

```python
from storage_access_structure import (
    get_folder_by_id_organization,
    get_folder_by_id_project,
    get_folder_by_id_version,
)

# Generar identificadores formateados
org_folder = get_folder_by_id_organization(1)  # "ORG0001"
prj_folder = get_folder_by_id_project(2)       # "PRJ0002"
ver_folder = get_folder_by_id_version(3)       # "v003"

# Ruta completa para el explorador de archivos
# /data/files/external/ORG0001/PRJ0002/v003/
```

### Tests

Los tests de versiones se encuentran en:

| Archivo | Entorno Virtual | Descripción |
|---------|-----------------|-------------|
| `src/apps/3_backend/tests/test_versiones_api.py` | `.venv_middleware313` | Tests de DTOs, numeración automática, aislamiento por org |
| `src/apps/7_service_frontend/tests/test_versiones_middleware.py` | `.venv_middleware313` | Tests de estructuras, reglas de negocio, seguridad |

Ejecutar tests:
```bash
./full_test.sh
# O individualmente:
source .venv_middleware313/bin/activate
pytest -v src/apps/3_backend/tests/test_versiones_api.py
pytest -v src/apps/7_service_frontend/tests/test_versiones_middleware.py
```

---

## Jerarquía de Trabajo y Roles de Proyecto

El sistema implementa una jerarquía de trabajo que determina la visibilidad y acceso de los usuarios.

### Jerarquía de acceso

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    JERARQUÍA DE TRABAJO DEL USUARIO                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Organización  ──►  Proyectos  ──►  Versiones  ──►  Contenido              │
│        │                  │                │                │                │
│   id_organizacion    id_proyecto      id_version      archivos/datos        │
│                          │                                                   │
│                    ┌─────▼─────┐                                            │
│                    │ FILTRO DE │                                            │
│                    │VISIBILIDAD│                                            │
│                    └─────┬─────┘                                            │
│                          │                                                   │
│            ┌─────────────┴─────────────┐                                    │
│            │   proyectos_roles         │                                    │
│            │   (id_usuario, id_rol,    │                                    │
│            │    id_proyecto, active)   │                                    │
│            └───────────────────────────┘                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Reglas de visibilidad de proyectos

Un usuario **SOLO puede ver** un proyecto si cumple **TODAS** las condiciones:

| Condición | Requerido | Descripción |
|-----------|-----------|-------------|
| Registro existe | ✅ | Debe existir registro en `proyectos_roles` para el usuario y proyecto |
| `active = TRUE` | ✅ | El registro debe estar activo |
| `id_rol > 0` | ✅ | El rol NO puede ser "Sin asignar" (id=0) |

**Si cualquier condición falla → El usuario NO VE el proyecto.**

### Catálogo de roles de proyecto (proyectos_roles_base)

| ID | Nombre | Descripción | Visibilidad |
|----|--------|-------------|-------------|
| 0 | Sin asignar | Usuario sin rol asignado | ❌ No ve el proyecto |
| 3 | Editor | Puede crear, modificar y eliminar contenido | ✅ Ve el proyecto |
| 4 | Lector | Solo puede ver el contenido (lectura) | ✅ Ve el proyecto |
| 5 | Auditor | Acceso limitado para auditoría y revisión | ✅ Ve el proyecto |

### Tabla proyectos_roles_base

```sql
-- Base de datos: myllm_projects_db
CREATE TABLE proyectos_roles_base (
    id INT NOT NULL PRIMARY KEY,           -- 0, 3, 4, 5
    nombre_rol VARCHAR(50) NOT NULL,       -- "Sin asignar", "Editor", "Lector", "Auditor"
    descripcion VARCHAR(255) DEFAULT NULL, -- Descripción del rol
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Endpoint para consultar roles base

```
GET /project-roles-base
```

**Flujo:** Frontend → Middleware → Broker → Backend Core → MariaDB

**Respuesta:**
```json
{
  "roles": [
    {"id": 0, "nombre_rol": "Sin asignar", "descripcion": "Usuario sin rol asignado"},
    {"id": 3, "nombre_rol": "Editor", "descripcion": "Puede modificar contenido"},
    {"id": 4, "nombre_rol": "Lector", "descripcion": "Solo lectura"},
    {"id": 5, "nombre_rol": "Auditor", "descripcion": "Acceso limitado"}
  ],
  "total": 4
}
```

### Uso en selectores (Frontend)

```python
# Cargar roles base desde API
from adapters.api_client import get_project_roles_base

roles = get_project_roles_base(access_token=token, session_token=session)
# Resultado: [{"id": 0, "nombre_rol": "Sin asignar", ...}, ...]

# En selectores, excluir "Sin asignar" (id=0)
roles_para_selector = [r["nombre_rol"] for r in roles if r["id"] > 0]
# Resultado: ["Editor", "Lector", "Auditor"]
```

### Migración SQL

Archivo: `infrastructure/database/migrations/005_proyectos_roles_base_table.sql`

## Sistema de Permisos (Security by Design)

El proyecto implementa un sistema de permisos centralizado basado en el principio **Security by Design**.
La tabla `low_level_permissions` es el **CORE del concepto Security by Default**.

### Modelo de Datos de Permisos

El sistema de permisos se basa en una relación directa **1 a 1** entre el rol del usuario y sus permisos:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MODELO DE DATOS DE PERMISOS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   SESIÓN                    TABLA users              TABLA low_level_permissions
│   ┌──────────┐              ┌──────────────────┐     ┌────────────────────────┐
│   │ user_id  │──────────────│ user_id          │     │ id_permissions         │
│   └──────────┘              │ identity_type_id │─────│ folder_create (bool)   │
│                             └──────────────────┘     │ folder_delete (bool)   │
│                                    │                 │ folder_rename (bool)   │
│                                    │                 │ folder_read (bool)     │
│                                    │                 │ file_create (bool)     │
│                                    ▼                 │ file_read (bool)       │
│                           identity_type_id           │ ...                    │
│                                  =                   │ user_create (bool)     │
│                           id_permissions             │ user_enable (bool)     │
│                             (RELACIÓN 1:1)           └────────────────────────┘
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Consulta SQL de Permisos

Para obtener **TODOS los permisos** de un usuario logado:

```sql
-- Desde el user_id de la sesión, obtener todos los permisos
SELECT llp.*
FROM users u
INNER JOIN low_level_permissions llp 
    ON u.identity_type_id = llp.id_permissions
WHERE u.user_id = :user_id_from_session;
```

**Ejemplo práctico:**

```sql
-- Usuario con user_id = 42, identity_type_id = 2 (Administrador)
SELECT llp.folder_create, llp.folder_delete, llp.user_create, llp.training_start
FROM users u
INNER JOIN low_level_permissions llp ON u.identity_type_id = llp.id_permissions
WHERE u.user_id = 42;

-- Resultado:
-- folder_create | folder_delete | user_create | training_start
-- 1             | 1             | 1           | 1
```

**Para verificar un permiso específico:**

```sql
-- ¿El usuario 42 puede crear usuarios?
SELECT llp.user_create
FROM users u
INNER JOIN low_level_permissions llp ON u.identity_type_id = llp.id_permissions
WHERE u.user_id = 42;
-- Resultado: 1 (true) → tiene permiso
```

### Vista SQL Recomendada

Para simplificar las consultas, se puede crear una vista:

```sql
CREATE OR REPLACE VIEW view_user_permissions AS
SELECT 
    u.user_id,
    u.user_name,
    u.organization_id,
    u.identity_type_id,
    llp.*
FROM users u
INNER JOIN low_level_permissions llp 
    ON u.identity_type_id = llp.id_permissions;

-- Uso:
SELECT folder_create, user_create FROM view_user_permissions WHERE user_id = 42;
```

### Flujo de Consulta de Permisos en el Código

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    FLUJO: SESIÓN → PERMISOS                                 │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Usuario logado → sesión contiene user_id                                │
│                           │                                                 │
│  2. Consulta tabla users  │ SELECT identity_type_id FROM users              │
│     con user_id           │ WHERE user_id = :session_user_id               │
│                           ▼                                                 │
│  3. Obtiene identity_type_id (ej: 2 = Admin, 5 = Auditor)                   │
│                           │                                                 │
│  4. JOIN con low_level_permissions                                          │
│     WHERE id_permissions = identity_type_id                                 │
│                           ▼                                                 │
│  5. Obtiene 40 permisos booleanos:                                          │
│     - folder_create = true/false                                            │
│     - file_delete = true/false                                              │
│     - user_create = true/false                                              │
│     - training_start = true/false                                           │
│     - ... (40 campos en total)                                              │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### Uso de Permisos en el Sistema

Los permisos obtenidos se utilizan en **TODAS las capas** del sistema:

| Capa | Uso | Ejemplo |
|------|-----|---------|
| **Frontend/Backoffice** | Mostrar/ocultar elementos UI | `rx.cond(state.can_user_create, boton_crear_usuario)` |
| **Middleware** | Validar antes de procesar requests | `if not has_permission("user_create"): raise HTTP 403` |
| **Broker** | Validar antes de enrutar | `if not can_perform("training_start"): reject request` |
| **Backend Core** | Validar antes de ejecutar lógica | `validate_permission(identity_type_id, "file_delete")` |
| **Backend IA** | Validar antes de operaciones IA | `if not has_permission("training_start"): deny` |

### Interpretación de Valores

| Valor en BD | Valor Python | Significado |
|-------------|--------------|-------------|
| `1` | `True` | Usuario **TIENE** el permiso |
| `0` | `False` | Usuario **NO TIENE** el permiso |

### Arquitectura de permisos

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Flujo de Validación de Permisos                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Usuario → Login → JWT (identity_type_id)                               │
│                          ↓                                              │
│               roles.json → identity_type_group_permissions              │
│                          ↓                                              │
│            low_level_permissions.json → permisos específicos            │
│                          ↓                                              │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                   Validación en TODAS las capas                │     │
│  ├───────────────────────────────────────────────────────────────┤     │
│  │ Frontend/Backoffice │ SharedSessionState.can_*                 │     │
│  │ Middleware          │ router.has_low_level_permission()        │     │
│  │ Backend Core        │ PermissionValidationService              │     │
│  │ fmanagement         │ Valida via Backend Core                  │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Componentes del sistema

| Componente | Ubicación | Función |
|------------|-----------|---------|
| **low_level_permissions.json** | `src/2_shared_application/moks/` | Fuente de permisos por rol |
| **SharedSessionState** | `src/2_shared_application/reflex_shared/` | Estado de sesión con 40 permisos |
| **PermissionValidationService** | `src/2_shared_application/services/` | Servicio centralizado de validación |
| **Project/Version entities** | `src/1_shared_domain/entities/` | Entidades de dominio con estados |
| **Adaptadores JSON** | `src/2_shared_application/adapters/` | Implementaciones de repositorios |

### Permisos disponibles (40 campos)

| Categoría | Permisos |
|-----------|----------|
| **Carpetas** | `folder_create`, `folder_delete`, `folder_rename`, `folder_read`, `folder_list` |
| **Ficheros** | `file_create`, `file_read`, `file_update`, `file_delete`, `file_list` |
| **Proyectos** | `project_create`, `project_read`, `project_update`, `project_delete`, `project_list` |
| **Versiones** | `version_create`, `version_read`, `version_update`, `version_delete`, `version_list` |
| **Entrenamiento** | `training_create`, `training_read`, `training_update`, `training_delete`, `training_start`, `training_stop` |
| **Parámetros** | `parameters_create`, `parameters_read`, `parameters_update`, `parameters_delete` |
| **Notificaciones** | `notifications_create`, `notifications_read`, `notifications_update`, `notifications_delete` |
| **Usuarios** | `user_create`, `user_read`, `user_update`, `user_delete`, `user_enable`, `user_disable` |

### PermissionValidationService (servicio centralizado)

Ubicación: `src/2_shared_application/services/permission_validation_service.py`

```python
from src.2_shared_application.services.permission_validation_service import (
    PermissionValidationService,
    PermissionContext,
    get_permission_service,
)

# Obtener instancia singleton
service = get_permission_service()

# Validar un permiso
service.can_perform_action(identity_type_id=2, permission_key="folder_rename")  # → bool

# Validar con contexto (para auditoría)
context = PermissionContext(user_id=1, organization_id=5, identity_type_id=2)
result = service.validate_permission(context, "folder_rename")
if not result.allowed:
    logger.warning(result.reason)

# Métodos de conveniencia
service.can_manage_folders(identity_type_id)    # ¿Puede gestionar carpetas?
service.can_manage_files(identity_type_id)      # ¿Puede gestionar archivos?
service.can_manage_training(identity_type_id)   # ¿Puede gestionar entrenamiento?
service.can_access_backoffice(identity_type_id) # ¿Puede acceder al backoffice?
```

### Ejemplo: Validación de notificaciones por rol

```python
# En UI (Frontend/Backoffice)
def chat_notifications(state):
    return rx.box(
        rx.cond(
            state.can_notifications_read,  # Solo mostrar si puede leer
            rx.vstack(
                rx.foreach(state.notifications, notification_item),
                rx.cond(
                    state.can_notifications_create,  # Crear solo si tiene permiso
                    rx.input(on_submit=state.send_notification),
                ),
            ),
        ),
    )

# En Middleware (validación obligatoria)
if not router.has_low_level_permission(session, "notifications_create"):
    raise HTTPException(status_code=403, detail="Sin permiso")

# En Backend Core
self.validate_permission(identity_type_id, "notifications_create")
```

### Roles por defecto

| identity_type_id | Rol | Descripción |
|------------------|-----|-------------|
| 1 | SuperAdmin | Todos los permisos |
| 2 | Administrador Org | CRUD completo en su organización |
| 3 | Editor | Crear/editar sin eliminar |
| 4 | Lector | Solo lectura |
| 5 | Auditor | Solo lectura de logs/config |
| 10-13 | Agentes proyecto | Permisos según tipo de agente |

### Entidades de dominio: Project y Version

El sistema incluye entidades de dominio para proyectos y versiones con estados de ciclo de vida.

**Archivos:**
- `src/1_shared_domain/entities/project.py` - Entidad Project
- `src/1_shared_domain/entities/version.py` - Entidad Version
- `src/2_shared_application/dtos/project_dtos.py` - DTOs
- `src/2_shared_application/interfaces/project_repository.py` - Contrato
- `src/2_shared_application/interfaces/version_repository.py` - Contrato

**Estados de versión:**
```
draft → in_review → approved_client → approved_myllm → ready_for_training → training → trained
```

**Uso:**
```python
from src.1_shared_domain.entities.project import Project, ProjectStatus
from src.1_shared_domain.entities.version import Version, VersionStatus

project = Project.from_dict({"project_id": 1, "status": "active", ...})
if project.can_create_version():
    version = Version.from_dict({"version_id": 1, "status": "draft", ...})
    if version.can_start_training():
        iniciar_entrenamiento()
```

### Archivos de permisos (mock)

- `src/2_shared_application/moks/roles.json`: define roles. El atributo
  `identity_type_group_permissions` contiene un único permiso básico (relación 1 a 1).
- `src/2_shared_application/moks/basic_permissions.json`: catálogo de permisos básicos.
- `src/2_shared_application/moks/low_level_permisions.json`: permisos de bajo nivel
  asociados 1 a 1 con `basic_permissions.json`.
- `src/2_shared_application/moks/manage_roles_by_org.json`: asigna roles a
  usuarios dentro de una organización.

En la gestión de permisos del token JWT se incluyen `user_id`, `organization_id`
e `identity_type_id` para resolver los permisos asociados.

Estructura de `manage_roles_by_org.json`:
```
{
  "id_user": 1,
  "id_organization": 1,
  "identity_type_id": 2,
  "create_date": "18/01/26-10:30",
  "modification_date": "",
  "id_modifier_user": 1,
  "active": true
}
```

El campo `identity_type_id` permite consultar los permisos del rol en
`basic_permissions.json`.

### Dominio y DTOs (roles por organización)

- **Dominio**: `ManagedRoleByOrg` y `ManageRolesByOrg` en `src/1_shared_domain/security_hierarchy.py`.
  La entidad expone `user_id`, `organization_id`, `identity_type_id` y metadatos de auditoría.
- **DTOs**: `ManageRoleByOrgDto` en `src/2_shared_application/dtos/security_dtos.py` mapea los campos
  `id_user`, `id_organization`, `identity_type_id`, `create_date`, `modification_date`,
  `id_modifier_user`, `active` hacia la entidad de dominio.

Este mapeo garantiza que el atributo `identity_type_id` del mock se preserve al cruzar capas.

### Persistencia (mock y MariaDB)

- **Mock JSON**: `src/2_shared_application/moks/manage_roles_by_org.json` es la fuente primaria para
  desarrollo y pruebas en modo `mock`.
- **MariaDB**: la tabla `user_organization_management` (definida en
  `anh_ansible_environments/env/macbook/files/init_myllm_core_db.sql`) refleja el mismo concepto con
  columnas `user_id`, `organization_id`, `identity_type_id`, `created_by_user_id`, `active`.
- **Carga**: el script de inicialización inserta desde JSON usando `JSON_TABLE()` y transforma
  `create_date` → `created_at`.

Estado verificado en BD (local): la tabla `user_organization_management` contiene 5 registros y
respeta los valores de `identity_type_id` del mock.

### Permisos básicos (dominio, DTO, mock y BD)

- **Dominio**: `BasicPermission` y `BasicPermissions` en `src/1_shared_domain/security_hierarchy.py`.
  El dominio consume `id`, `PermissionName`, `PermissionDescription` y valida su estructura.
- **DTOs**: `BasicPermissionDto` en `src/2_shared_application/dtos/security_dtos.py` mapea
  `id` → `permission_id`, `PermissionName` → `permission_name` y
  `PermissionDescription` → `permission_description`.
- **Mock JSON**: `src/2_shared_application/moks/basic_permissions.json` es la fuente principal.
  `PermissionName` se utiliza en el código para verificaciones, y `PermissionDescription`
  se usa para documentación y mensajes administrativos.
- **MariaDB**: los datos se cargan en la tabla `permissions` (script
  `anh_ansible_environments/env/macbook/files/init_myllm_core_db.sql`) mediante `JSON_TABLE()`.
  La relación entre `identity_types` y `permissions` es **1 a 1** y se controla con
  claves únicas en `identity_type_permissions`.

Estado verificado en BD (local): la tabla `permissions` contiene 13 registros y conserva los
`PermissionName`/`PermissionDescription` del mock.

### Permisos de bajo nivel (dominio, DTO, mock y BD)

- **Dominio**: `LowLevelPermission` y `LowLevelPermissions` en `src/1_shared_domain/security_hierarchy.py`.
  Cada registro utiliza `id_permissions` y flags booleanos por recurso/acción.
- **DTOs**: `LowLevelPermissionDto` en `src/2_shared_application/dtos/security_dtos.py`.
- **Mock JSON**: `src/2_shared_application/moks/low_level_permisions.json` exportado desde
  MariaDB. El `id_permissions` coincide 1 a 1 con `basic_permissions.json` y `roles.json`.
- **MariaDB**: tabla `low_level_permissions` con relación 1 a 1 con `permissions`.

Uso previsto: el token aporta `identity_type_id`; con ese ID se resuelve el permiso base,
su descripción y los flags de bajo nivel en la misma cadena de seguridad.

Ejemplo de plantilla para validar una acción concreta desde sesión/JWT:

```python
def can_rename_folder(session: SessionContext) -> bool:
    """Valida si el usuario puede renombrar carpetas."""

    permissions = router.get_permissions(session)
    return bool(permissions.get("low_level_permissions", {}).get("folder_rename"))
```

### Flujo entre APIs (permisos básicos)

- `7_service_frontend` carga permisos vía JSON o broker (`/basic-permissions`) según `STORAGE_MODE`.
- `8_service_backend` expone `GET /basic-permissions` y delega al core.
- `3_backend` expone `GET /basic-permissions` y devuelve los permisos desde el almacenamiento.

### Flujo entre APIs (permisos de bajo nivel)

- `7_service_frontend` carga permisos vía JSON o broker (`/low-level-permissions`) según `STORAGE_MODE`.
- `8_service_backend` expone `GET /low-level-permissions` y delega al core.
- `3_backend` expone `GET /low-level-permissions` y devuelve los permisos desde el almacenamiento.

### Trazabilidad X-Client-App

El sistema implementa trazabilidad de peticiones entre servicios mediante el header `X-Client-App`.
Este header permite identificar el origen de cada petición a través de toda la cadena de servicios.

**Flujo de propagación:**

```
Frontend/Backoffice → Middleware → Broker → Backend Core → fmanagement
     [frontend]        [middleware]  [broker]   [core]     [fmanagement]
```

**Valores soportados:**
| Origen | Header X-Client-App |
|--------|---------------------|
| `5_web_frontend` | `frontend` |
| `6_web_backoffice` | `backoffice` |
| `7_service_frontend` | `middleware` |
| `8_service_backend` | `broker` |

**Implementación por servicio:**

1. **Frontend/Backoffice** (`adapters/api_client.py`):
   ```python
   request_headers = {
       "Content-Type": "application/json",
       "X-Client-App": "frontend",  # o "backoffice"
   }
   ```

2. **Middleware** (`apife.py`, `broker_backend_client.py`):
   - Extrae el header con `get_client_app()` como dependencia
   - Inyecta el valor al `BrokerBackendClient` via `get_router_middleware()`
   - Lo propaga al broker en peticiones salientes

3. **Broker** (`apibe.py`, `interfacetocore.py`):
   - Extrae el header de peticiones entrantes
   - Registra en logs: `[frontend] Consulta permisos role_id=2`
   - Lo propaga al backend core

4. **Backend Core** (`apicore.py`, `fmanagement_client.py`):
   - Extrae el header de peticiones entrantes
   - Lo propaga a fmanagement

**Formato de logs:**
```
2026-01-27 10:30:45 | INFO | [frontend] | user_id=1 | action=login
2026-01-27 10:30:46 | INFO | [backoffice] | user_id=2 | action=create_training
```

## Estructura de almacenamiento (helpers)

En `src/2_shared_application/storage_access_structure.py` se definen helpers
para construir los nombres de carpetas en disco a partir de IDs numéricos:

```python
get_folder_by_id_organization(1)  # "ORG0001"
get_folder_by_id_project(1)       # "PRJ0001"
```

Estos helpers deben usarse de forma consistente en todas las capas cuando se
trabaje con rutas del storage (`/data/files/external`).

## Interfaces compartidas (aplicación)

Los contratos en `src/2_shared_application/interfaces/` desacoplan el acceso a
las entidades de dominio de la infraestructura (JSON hoy, MariaDB mañana).

**Repositorios de seguridad:**
- `basic_permissions_repository.py`: `BasicPermissionsRepository`
- `low_level_permissions_repository.py`: `LowLevelPermissionsRepository`
- `manage_roles_by_org_repository.py`: `ManageRolesByOrgRepository`
- `roles_repository.py`: `RolesRepository`

**Repositorios de entidades principales:**
- `user_repository.py`: `UserRepository`
- `organization_repository.py`: `OrganizationRepository`
- `project_repository.py`: `ProjectRepository` ← **NUEVO**
- `version_repository.py`: `VersionRepository` ← **NUEVO**
- `session_repository.py`: `SessionRepository`

**Repositorios auxiliares:**
- `identity_global_repository.py`: `IdentityGlobalRepository`
- `permissions_repository.py`: `PermissionsRepository`
- `tenant_repository.py`: `TenantRepository`
- `dataset_repository.py`: `DatasetRepository`
- `model_version_repository.py`: `ModelVersionRepository`

### Adaptadores JSON (implementaciones)

Los adaptadores implementan los contratos de repositorio usando JSON como almacenamiento:

- `src/2_shared_application/adapters/json_user_repository.py`: `JsonUserRepository`
- `src/2_shared_application/adapters/json_organization_repository.py`: `JsonOrganizationRepository`

**Uso:**
```python
from src.2_shared_application.adapters import JsonUserRepository, JsonOrganizationRepository

user_repo = JsonUserRepository()
user = user_repo.get_by_email("admin@example.com")
if user_repo.exists_by_email("nuevo@email.com"):
    print("Email ya existe")

org_repo = JsonOrganizationRepository()
org = org_repo.get_by_id(1)
org_repo.save({"organization_name": "Nueva Org"})
```

### Ejemplos de implementación en adaptadores

Ejemplos simplificados (sin datos reales) para implementar repositorios desde
JSON o desde MariaDB usando DTOs. Los adaptadores viven en la capa de
infraestructura y transforman datos externos a entidades de dominio.

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from src.1_shared_domain.security_hierarchy import Roles
from src.2_shared_application.interfaces.roles_repository import RolesRepository


class RolesJsonRepository(RolesRepository):
    """Repositorio basado en JSON para roles (solo ejemplo)."""

    def __init__(self, json_path: Path) -> None:
        self._json_path = json_path

    def fetch_roles(self) -> Roles:
        records = _read_json_list(self._json_path)
        # El dominio valida estructura al construir
        return Roles.from_records(records)


def _read_json_list(json_path: Path) -> list[dict[str, object]]:
    """Lee una lista JSON de forma segura."""

    with json_path.open("r", encoding="utf-8") as file_handler:
        data = json.load(file_handler)
    if not isinstance(data, list):
        raise ValueError("El JSON debe contener una lista")
    return data
```

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.1_shared_domain.entities.domain_models import User
from src.2_shared_application.interfaces.user_repository import UserRepository


@dataclass(frozen=True)
class UserDto:
    """DTO simulado retornado por MariaDB."""

    id: int
    organization_id: int
    identity_type_id: int
    user_name: str
    user_password: str
    user_email: str
    user_mobile: str
    user_otp: str
    active: bool
    blocked: bool


class UsersMariaDbAdapter(UserRepository):
    """Repositorio simulado que mapea DTOs a entidad de dominio."""

    def __init__(self, gateway: "UserQueryGateway") -> None:
        self._gateway = gateway

    def get_by_id(self, user_id: int) -> User | None:
        dto = self._gateway.fetch_by_id(user_id)
        if dto is None:
            return None
        return _map_user(dto)

    def get_by_email(self, user_email: str) -> User | None:
        dto = self._gateway.fetch_by_email(user_email)
        if dto is None:
            return None
        return _map_user(dto)

    def get_by_name(self, user_name: str) -> User | None:
        dto = self._gateway.fetch_by_name(user_name)
        if dto is None:
            return None
        return _map_user(dto)

    def exists_by_email(self, user_email: str) -> bool:
        return self._gateway.exists_by_email(user_email)

    def exists_by_mobile(self, user_mobile: str) -> bool:
        return self._gateway.exists_by_mobile(user_mobile)

    def exists_by_name(self, user_name: str) -> bool:
        return self._gateway.exists_by_name(user_name)

    def save(self, user: User) -> User:
        dto = self._gateway.insert_user(user)
        return _map_user(dto)

    def update_password_and_otp(
        self, user_email: str, new_password: str, new_otp: str
    ) -> bool:
        return self._gateway.update_password_and_otp(
            user_email, new_password, new_otp
        )


class UserQueryGateway(Protocol):
    """Gateway simulado hacia MariaDB."""

    def fetch_by_id(self, user_id: int) -> UserDto | None:
        """Obtiene un usuario por id."""

    def fetch_by_email(self, user_email: str) -> UserDto | None:
        """Obtiene un usuario por email."""

    def fetch_by_name(self, user_name: str) -> UserDto | None:
        """Obtiene un usuario por nombre."""

    def exists_by_email(self, user_email: str) -> bool:
        """Verifica existencia por email."""

    def exists_by_mobile(self, user_mobile: str) -> bool:
        """Verifica existencia por teléfono."""

    def exists_by_name(self, user_name: str) -> bool:
        """Verifica existencia por nombre."""

    def insert_user(self, user: User) -> UserDto:
        """Inserta y retorna el DTO persistido."""

    def update_password_and_otp(
        self, user_email: str, new_password: str, new_otp: str
    ) -> bool:
        """Actualiza contraseña y OTP en base de datos."""


def _map_user(dto: UserDto) -> User:
    """Convierte un DTO en entidad de dominio."""

    return User(
        user_id=dto.id,
        organization_id=dto.organization_id,
        identity_type_id=dto.identity_type_id,
        user_name=dto.user_name,
        password=dto.user_password,
        email=dto.user_email,
        mobile=dto.user_mobile,
        otp=dto.user_otp,
        active=dto.active,
        blocked=dto.blocked,
    )
```

```python
from __future__ import annotations

import json
from pathlib import Path

from src.1_shared_domain.entities.session import Session, SessionStatus
from src.2_shared_application.interfaces.session_repository import SessionRepository


class SessionJsonRepository(SessionRepository):
    """Repositorio basado en JSON para sesiones (solo ejemplo)."""

    def __init__(self, json_path: Path) -> None:
        self._json_path = json_path

    def get_by_session_id(self, session_id: str) -> Session | None:
        records = _read_json_dict(self._json_path).get("sessions", [])
        for record in records:
            if record.get("session_id") == session_id:
                return Session.from_record(record)
        return None

    def list_by_user_id(self, user_id: int) -> tuple[Session, ...]:
        records = _read_json_dict(self._json_path).get("sessions", [])
        sessions = [
            Session.from_record(record)
            for record in records
            if int(record.get("user_id", 0)) == user_id
        ]
        return tuple(sessions)

    def save(self, session: Session) -> Session:
        payload = _read_json_dict(self._json_path)
        sessions = payload.get("sessions", [])
        sessions.append(session.to_record())
        payload["sessions"] = sessions
        _write_json_dict(self._json_path, payload)
        return session

    def update_status(
        self, session_id: str, status: SessionStatus, updated_at=None
    ) -> bool:
        payload = _read_json_dict(self._json_path)
        sessions = payload.get("sessions", [])
        for record in sessions:
            if record.get("session_id") == session_id:
                record["status"] = status.value
                return True
        return False

    def update_activity(self, session_id: str, last_activity) -> bool:
        payload = _read_json_dict(self._json_path)
        sessions = payload.get("sessions", [])
        for record in sessions:
            if record.get("session_id") == session_id:
                record["last_activity"] = last_activity
                return True
        return False


def _read_json_dict(json_path: Path) -> dict[str, object]:
    """Lee un JSON tipo dict de forma segura."""

    if not json_path.exists():
        return {}
    with json_path.open("r", encoding="utf-8") as file_handler:
        data = json.load(file_handler)
    if not isinstance(data, dict):
        raise ValueError("El JSON debe contener un objeto")
    return data


def _write_json_dict(json_path: Path, payload: dict[str, object]) -> None:
    """Escribe un JSON tipo dict de forma segura."""

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as file_handler:
        json.dump(payload, file_handler, ensure_ascii=False, indent=2)
```

## Logging de seguridad

Las escrituras de logs de seguridad se realizan en el middleware (`7_service_frontend`).
El frontend solo envía la acción al endpoint `/security/log`.

Archivo de log (middleware):
- `src/apps/7_service_frontend/logs/middleware_secure.log`

## Logging de actividad (middleware)

El middleware registra la actividad de las APIs en un log dedicado para trazabilidad.
Este log captura acciones como autenticación, validaciones y operaciones CRUD.

Archivo de log (middleware):
- `src/apps/7_service_frontend/logs/middleware_activiy.log`

## Logging de actividad (broker y core)

Cada API registra su actividad en logs locales:

- `src/apps/8_service_backend/logs/broker_backend_activity.log`
- `src/apps/3_backend/logs/backend_core_activity.log`

## Sistema de logging unificado (console.log)

Todas las aplicaciones escriben simultáneamente a un archivo `console.log` unificado en su 
directorio `logs/`. Este archivo está diseñado para facilitar la trazabilidad y el diagnóstico 
de incidencias por parte de técnicos de soporte.

### Archivos console.log por aplicación

| Aplicación | Ruta del archivo |
|------------|------------------|
| Backend Core | `src/apps/3_backend/logs/console.log` |
| Trainer (Backend IA) | `src/apps/4_trainer/logs/console.log` |
| Frontend | `src/apps/5_web_frontend/logs/console.log` |
| Backoffice | `src/apps/6_web_backoffice/logs/console.log` |
| Middleware | `src/apps/7_service_frontend/logs/console.log` |
| Broker | `src/apps/8_service_backend/logs/console.log` |

### Formato de logs

Todos los logs usan un formato unificado legible para soporte técnico:

```
YYYY-MM-DD HH:MM:SS | LEVEL    | APP_NAME        | MENSAJE
```

Ejemplo:
```
2026-01-28 10:30:45 | INFO     | backend_core    | APPLICATION STARTUP | listening on 0.0.0.0:8003
2026-01-28 10:30:46 | INFO     | middleware      | AUTH LOGIN | SUCCESS | user=adminone | user_id=1
2026-01-28 10:30:47 | WARNING  | broker          | PERMISSION folder_delete | DENIED | user_id=4
```

### Captura de logs de uvicorn

Las aplicaciones FastAPI (3_backend, 4_trainer, 7_service_frontend, 8_service_backend) capturan
automáticamente los logs de uvicorn en `console.log`. Esto incluye:

- **Logs de acceso HTTP:** Peticiones entrantes con IP, método, ruta y código de respuesta
- **Logs de errores:** Excepciones y errores del servidor
- **Logs de inicio/parada:** Mensajes de arranque y cierre del servidor

Los loggers configurados son:
- `uvicorn`: Logger principal de uvicorn
- `uvicorn.access`: Logger de peticiones HTTP (método, ruta, status)
- `uvicorn.error`: Logger de errores y excepciones

### Rotación de logs

Los archivos `console.log` implementan rotación automática:
- **Tamaño máximo:** 10 MB por archivo
- **Backups:** 5 archivos (`console.log.1`, `console.log.2`, etc.)
- **Codificación:** UTF-8

### Módulo compartido de logging

El sistema usa el módulo `src/2_shared_application/console_logger.py` que proporciona:

```python
from src.2_shared_application.console_logger import create_console_logger

# En el punto de entrada de cada aplicación
logger = create_console_logger("mi_app", logs_dir)

# Métodos disponibles
logger.startup(host="0.0.0.0", port=8003)   # Inicio de aplicación
logger.shutdown()                             # Cierre de aplicación
logger.request("GET", "/api/users")           # Petición HTTP
logger.response("GET", "/api/users", 200)     # Respuesta HTTP
logger.operation("create_user", success=True) # Operación de negocio
logger.auth("LOGIN", username="admin")        # Evento de autenticación
logger.permission("CHECK", "folder_rename")   # Verificación de permisos
logger.data("CREATE", "user", entity_id=1)    # Operación CRUD
logger.connection("MariaDB", "OK")            # Estado de conexión
logger.config("API_URL", "http://...")        # Configuración cargada
```

### Uso para diagnóstico de incidencias

**Seguimiento de flujo entre componentes:**

```bash
# Ver actividad reciente en todos los servicios
tail -f src/apps/*/logs/console.log

# Buscar errores en todo el sistema
grep "ERROR" src/apps/*/logs/console.log

# Seguir una petición específica por user_id
grep "user_id=1" src/apps/*/logs/console.log | sort

# Ver solo el middleware y broker
tail -f src/apps/{7_service_frontend,8_service_backend}/logs/console.log
```

**Correlación de eventos:**

1. Identificar el timestamp del error
2. Buscar en todos los `console.log` con ese timestamp
3. Seguir el flujo: Frontend → Middleware → Broker → Backend Core

### Estructura JWT (middleware)

El middleware emite dos tokens:
- **Access Token** (15 min)
- **Session Token** (45 min)

Payload mínimo común en ambos:
```
{
  "user_id": 1,
  "organization_id": 1,
  "identity_type_id": 2,
  "iat": 1700000000,
  "exp": 1700000900
}
```

## Gestión de Usuarios de Organización

### Alta de usuarios dentro de una organización

El sistema permite que usuarios autorizados (administradores de organización) creen nuevos usuarios dentro de su propia organización. Esta funcionalidad está disponible desde la página **"Organización"** tanto en el frontend (`5_web_frontend`) como en el backoffice (`6_web_backoffice`).

#### Flujo de creación de usuario

```
Usuario (Frontend/Backoffice)
    ↓ Click en "Crear usuario"
    ↓ Completar formulario: user_name, user_email, user_mobile
    ↓ Click en "Guardar"
    ↓
API Client (create_organization_user)
    ↓ Genera OTP aleatorio (4 dígitos)
    ↓ Genera password temporal cifrada (Fernet)
    ↓ Prepara payload completo
    ↓
POST /users → Middleware (7_service_frontend)
    ↓ Según STORAGE_MODE:
    │   - mock: Solo JSON local
    │   - mock_and_db: JSON + Broker
    │   - db_only: Solo Broker
    ↓
POST /users → Broker (8_service_backend)
    ↓
POST /users → Backend Core (3_backend)
    ↓ Persiste en: users, user_contact_info, user_billing_info
    ↓
Respuesta: { user_id, organization_id, identity_type_id }
```

#### Datos generados automáticamente

| Campo | Origen |
|-------|--------|
| `user_id` | Autoincremental (asignado por el sistema) |
| `organization_id` | Extraído del JWT/sesión del usuario que crea |
| `identity_type_id` | **Siempre `5` (auditor)** - ver regla de roles abajo |
| `user_password` | Generada aleatoriamente y cifrada con Fernet |
| `user_otp` | OTP aleatorio de 4 dígitos |
| `active` | `true` |
| `blocked` | `false` |
| `created_at` | Timestamp actual |
| `contact_info.first_name` | Nombre ingresado en el formulario |
| `contact_info.sur_name` | "Usuario de la organizacion" |
| `billing_info.first_name` | Nombre ingresado en el formulario |
| `billing_info.sur_name` | "Usuario de la organizacion" |

#### Regla de roles para usuarios de organización

**IMPORTANTE**: Los usuarios creados desde el panel "Gestión de Usuarios" de la página Organización **SIEMPRE** reciben `identity_type_id = 5` (auditor).

| identity_type_id | Rol | Descripción |
|------------------|-----|-------------|
| 1 | SuperAdmin | Administrador global del sistema (solo myllm) |
| 2 | Administrador de Organización | **Único por organización** - Se asigna automáticamente al primer usuario |
| 3 | Editor | Puede crear/editar contenido |
| 4 | Lector | Solo lectura |
| 5 | **Auditor** | **Rol por defecto para usuarios creados desde el panel** |

**Razones de esta regla:**

1. **Seguridad por defecto**: Los usuarios nuevos tienen permisos restringidos hasta que se les asignen roles específicos en proyectos.
2. **Un administrador por organización**: Solo puede haber UN usuario con `identity_type_id = 2` por organización (el que la creó).
3. **Roles por proyecto**: Los usuarios pueden tener roles adicionales (editor, lector) asignados en tablas relacionadas con proyectos específicos.
4. **Principio de mínimo privilegio**: Comenzar con permisos mínimos y escalar según necesidad.

#### Primer acceso del nuevo usuario

El usuario creado debe seguir estos pasos para configurar su contraseña:

1. Ir a la página de login
2. Click en **"Recordar contraseña"**
3. Ingresar su `user_name`
4. Recibir OTP en el teléfono configurado (`user_mobile`)
5. Configurar su nueva contraseña

#### Archivos involucrados

| Capa | Archivo | Función |
|------|---------|---------|
| Frontend | `adapters/api_client.py` | `create_organization_user()` |
| Frontend | `web_frontend/web_frontend.py` | `State.save_new_user()`, modal UI |
| Backoffice | `adapters/api_client.py` | `create_organization_user()` |
| Backoffice | `web_backoffice/web_backoffice.py` | `State.save_new_user()`, modal UI |
| Middleware | `routermiddleware.py` | `RouterMiddleware.create_user()` |
| Broker | `routerbroker.py` | `BrokerBackendRouter.create_user()` |
| Backend Core | `routercore.py` | `BackendCoreRouter.create_user()` |

#### Configuración de STORAGE_MODE

El comportamiento de persistencia depende de la variable de entorno `STORAGE_MODE`:

```yaml
# infrastructure/environments/<env>/env.yaml
storage_mode: "db_only"  # Producción: solo base de datos
storage_mode: "mock_and_db"  # Desarrollo: JSON + base de datos
storage_mode: "mock"  # Testing: solo JSON
```

#### Permisos requeridos

Para crear usuarios, el usuario que realiza la operación debe tener el permiso `user_create` en su `identity_type_id`. Este permiso se valida en:

- **Frontend/Backoffice**: `rx.cond(State.can_user_create, ...)` para mostrar/ocultar botón
- **Middleware**: Validación antes de procesar la petición
- **Backend Core**: Validación adicional antes de persistir

### Tests de creación de usuarios

El sistema incluye tests de integración para validar el flujo de creación de usuarios.

#### Ubicación del test

```
src/apps/7_service_frontend/tests/test_admin_create_user_integration.py
```

#### Ejecutar el test individualmente

```bash
# Activar entorno virtual del middleware
source .venv_middleware313/bin/activate

# Ejecutar test específico
pytest -v src/apps/7_service_frontend/tests/test_admin_create_user_integration.py

# Ejecutar con salida detallada
pytest -v -s src/apps/7_service_frontend/tests/test_admin_create_user_integration.py
```

#### Casos de test incluidos

| Test | Descripción |
|------|-------------|
| `test_admin_can_create_user_successfully` | Valida creación completa: persistencia, contraseña cifrada con Fernet, OTP aleatorio |
| `test_admin_creates_multiple_users_with_incremental_ids` | Valida que los user_id se asignan incrementalmente |
| `test_created_user_has_correct_default_values` | Valida valores por defecto (active=True, blocked=False) y contraseña cifrada |
| `test_user_creation_registers_in_manage_roles` | Valida que se registra la entrada en manage_roles_by_org |
| `test_user_email_is_stored_lowercase` | Valida normalización del email a minúsculas |
| `test_user_name_is_trimmed` | Valida eliminación de espacios en el nombre |

**Nota sobre seguridad**: Todos los tests utilizan contraseñas cifradas con Fernet (como en producción). Se genera una clave Fernet temporal para cada ejecución de test, lo que garantiza que los tests validan el comportamiento real del sistema.

#### Validaciones realizadas

El test `test_admin_can_create_user_successfully` valida:

1. **user_id autoincremental**: El nuevo usuario recibe ID = 2 (siguiente al admin)
2. **Persistencia en users.json**:
   - user_name, user_email, user_mobile correctos
   - organization_id heredado
   - active = True, blocked = False
3. **Contraseña cifrada con Fernet**:
   - La contraseña NO se guarda en texto plano
   - Se genera una contraseña temporal aleatoria con `secrets.token_urlsafe(16)`
   - Se cifra usando Fernet antes de persistir
   - El test verifica que la contraseña comienza con `gAAAAA` (header Fernet base64)
   - El test verifica que se puede descifrar correctamente
4. **OTP generado aleatoriamente**:
   - OTP de 4 dígitos generado con `secrets.randbelow(10000)`
5. **contact_info y billing_info**:
   - first_name = nombre del usuario
   - sur_name = "Usuario de la organizacion"
6. **Registro en manage_roles_by_org.json**:
   - id_user = ID del usuario creado
   - id_organization = ID de la organización
   - active = True
   - create_date con formato DD/MM/YY-HH:MM

#### Ejecutar todos los tests

```bash
./full_test.sh
```

El script `full_test.sh` incluye automáticamente el test de creación de usuarios como parte de la suite completa.

## Sistema de Tickets de Soporte

### Arquitectura de datos

El sistema de tickets utiliza dos tablas en `myllm_projects_db`:

**Tabla `tickets` (cabecera):**
- `id`: ID autoincremental
- `titulo`: Motivo del ticket (máx 200 chars)
- `cliente_id`: ID del usuario que crea el ticket
- `estado`: abierto | en_espera | resuelto | cerrado (default: abierto)
- `prioridad`: baja | media | alta | urgente (default: media)
- `fecha_creacion`: Timestamp automático
- `fecha_actualizacion`: Timestamp de última modificación

**Tabla `ticket_interacciones` (detalle):**
- `id`: ID autoincremental
- `ticket_id`: FK a tickets
- `autor_consulta_id`: ID del usuario que hace la consulta (Frontend)
- `autor_respuesta_id`: ID del usuario que responde (Backoffice)
- `consulta`: Texto de la consulta (MEDIUMTEXT)
- `respuesta`: Texto de la respuesta (MEDIUMTEXT)
- `fecha_consulta`: Timestamp de la consulta
- `fecha_respuesta`: Timestamp de la respuesta

### Flujo de operaciones

**Desde Frontend:**
1. Usuario hace clic en "Solicitud de soporte" en un proyecto
2. Se abre modal con: Motivo (obligatorio), Consulta (obligatorio)
3. Estado y Prioridad son informativos (abierto, media)
4. Al guardar: crea ticket + primera interacción

**Desde Backoffice:**
1. Panel "Gestión de Tickets" muestra tickets de la organización
2. Puede cambiar estado (selector) y prioridad (selector)
3. Puede añadir respuesta a la consulta
4. Los cambios actualizan `fecha_actualizacion` y `fecha_respuesta`

### Endpoints de la API

| Método | Endpoint | Descripción | Origen |
|--------|----------|-------------|--------|
| POST | `/tickets` | Crear ticket con consulta inicial | Frontend |
| GET | `/tickets/organization/{org_id}` | Listar tickets de la organización | Ambos |
| GET | `/tickets/{ticket_id}` | Detalle de un ticket | Ambos |
| PATCH | `/tickets/{ticket_id}` | Actualizar estado/prioridad | Backoffice |
| POST | `/tickets/{ticket_id}/respuesta` | Añadir respuesta | Backoffice |

### Registro de cambios

Cada operación genera un registro en la tabla `cambios`:

| Operación | tipo_cambio | descripcion |
|-----------|-------------|-------------|
| Crear ticket | "Solicitud soporte proyecto" | "Ticket #{id}: {titulo}" |
| Añadir respuesta | "Respuesta soporte proyecto" | "Respuesta a ticket #{id}" |
| Cambiar estado | "Actualización soporte proyecto" | "Ticket #{id}: estado → {nuevo}" |
| Cambiar prioridad | "Actualización soporte proyecto" | "Ticket #{id}: prioridad → {nueva}" |

### SQL de creación de tablas

```sql
USE myllm_projects_db;

CREATE TABLE IF NOT EXISTS tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(200) NOT NULL,
    cliente_id INT NOT NULL,
    estado ENUM('abierto', 'en_espera', 'resuelto', 'cerrado') DEFAULT 'abierto',
    prioridad ENUM('baja', 'media', 'alta', 'urgente') DEFAULT 'media',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX (cliente_id),
    INDEX (estado)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ticket_interacciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    autor_consulta_id INT NOT NULL,
    autor_respuesta_id INT DEFAULT NULL,
    consulta MEDIUMTEXT NOT NULL,
    respuesta MEDIUMTEXT DEFAULT NULL,
    fecha_consulta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_respuesta TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT fk_ticket_rel FOREIGN KEY (ticket_id) 
        REFERENCES tickets(id) ON DELETE CASCADE,
    INDEX (ticket_id)
) ENGINE=InnoDB;

-- Permisos
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.tickets TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.ticket_interacciones TO 'myllm_writer'@'localhost';
GRANT SELECT ON myllm_projects_db.tickets TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.ticket_interacciones TO 'myllm_reader'@'localhost';
FLUSH PRIVILEGES;
```

## Roles y automatización (referencia)

Los roles Ansible importados se encuentran en el repositorio `anh_ansible`. Incluyen BIND, NTPD, NTPDATE, MariaDB, Nginx, Postfix, entre otros, y sirven como apoyo para el despliegue de la plataforma.

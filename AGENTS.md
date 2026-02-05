# Agent Rules for Python Project

You are an expert Python developer with a focus on writing clean, maintainable, and high-performance code. Follow these rules strictly when modifying or creating code in this repository.

## 1. Python Standards & Style
* **Version:** Target Python **3.13** features (e.g., structural pattern matching, union types `int | str`).
* **Límite:** No usar versiones de Python superiores a **3.13** en este repositorio.
* **Style Guide:** Adhere strictly to **PEP 8**.
* **Naming Conventions:**
    * Functions and variables: `snake_case`
    * Classes: `PascalCase`
    * Constants: `UPPER_SNAKE_CASE`
    * Private members: `_leading_underscore`
* **Formatting:** Use `black` or `ruff` style formatting. Use double quotes for strings unless the string contains double quotes.

## 2. Type Hinting & Validation
* **Mandatory Typing:** Use **Type Hints** for all function signatures (parameters and return types).
* **Clarity:** Use `typing.Annotated` for complex types and `TypeAlias` for readability.
* **Pydantic:** If creating data models, use Pydantic v2 for validation and settings management.

## 3. Best Practices & Design Patterns
* **Explicit over Implicit:** Avoid `from module import *`. Use explicit imports.
* **List Comprehensions:** Use them for simple transformations, but favor `for` loops for complex logic to maintain readability.
* **Context Managers:** Use `with` statements for resource management (files, database connections, locks).
* **Dependency Injection:** Prefer passing dependencies as arguments rather than hardcoding them inside functions/classes.
* **Docstrings:** Provide Google-style or NumPy-style docstrings for all public modules, classes, and functions.

## 4. Error Handling
* **Specific Exceptions:** Never use bare `except:`. Always catch specific exceptions (e.g., `ValueError`, `KeyError`).
* **Custom Exceptions:** Create domain-specific exception classes inheriting from `Exception`.
* **Logging:** Use the standard `logging` library or `loguru`. Avoid `print()` for debugging or info in production code.

## 5. Testing & Environment
* **Framework:** Use `pytest` for testing.
* **Style:** Write small, atomic tests. Use `pytest.fixture` for setup logic.
* **Async:** If the project uses `asyncio`, ensure tests are handled with `pytest-asyncio`.
* **Dependencies:** Management is handled via `poetry` or `pip compile` (check `pyproject.toml`). Do not add new dependencies without asking.
* **Ejecución:** Usar `./full_test.sh` para ejecutar toda la suite de tests con salida detallada.

### 5.1. Reglas de entornos virtuales en tests

**CRÍTICO:** Los tests deben ejecutarse en el entorno virtual correcto para reflejar las dependencias 
reales de cada aplicación y evitar falsos positivos o negativos.

#### Matriz de entornos virtuales para tests:

| Entorno Virtual | Tests que ejecuta | Aplicaciones testeadas |
|-----------------|-------------------|------------------------|
| `.venv_frontend313` | `2_shared_application/tests`, `5_web_frontend/tests` | Capa compartida, Frontend |
| `.venv_backoffice313` | `6_web_backoffice/tests` | Backoffice |
| `.venv_middleware313` | `7_service_frontend/tests`, `8_service_backend/tests`, `3_backend/tests` | Middleware, Broker, Backend Core |

#### Reglas obligatorias:

1. ✅ **Activar entorno virtual correcto:** Cada test DEBE ejecutarse en el entorno virtual de su aplicación
2. ✅ **No usar entornos compartidos:** Nunca ejecutar tests de frontend con entorno de middleware o viceversa
3. ✅ **Aislar dependencias:** Los tests NO deben importar módulos de otras aplicaciones fuera de shared
4. ✅ **Mock de servicios externos:** Los tests deben configurar `STORAGE_MODE=mock` con `monkeypatch.setenv()`
5. ✅ **Verificar antes de ejecutar:** El script `full_test.sh` valida automáticamente los entornos

#### Ejemplo de test con entorno virtual correcto:

```python
# ✅ CORRECTO: Test de frontend (se ejecuta con .venv_frontend313)
# src/apps/5_web_frontend/tests/test_user_creation.py

import pytest
from unittest.mock import patch

def test_user_creation(monkeypatch):
    """Test que se ejecuta en .venv_frontend313"""
    # Aislar de servicios externos
    monkeypatch.setenv("STORAGE_MODE", "mock")
    
    # Test logic here
    pass
```

```python
# ✅ CORRECTO: Test de middleware (se ejecuta con .venv_middleware313)
# src/apps/7_service_frontend/tests/test_user_creation_middleware.py

import pytest

def test_middleware_user_creation(monkeypatch):
    """Test que se ejecuta en .venv_middleware313"""
    monkeypatch.setenv("STORAGE_MODE", "mock")
    
    # Test logic here
    pass
```

```python
# ❌ INCORRECTO: Test ejecutado en entorno equivocado
# Si test_frontend.py se ejecuta con .venv_middleware313:
# - Puede faltar dependencias específicas de frontend (reflex)
# - Puede tener dependencias conflictivas
# - Resultados no fiables
```

#### Variables de entorno en tests:

* **Obligatorio:** Los tests deben configurar `STORAGE_MODE=mock` con `monkeypatch.setenv()` 
  para evitar dependencias de servicios externos (MariaDB, Redis).
* **Recomendado:** Usar fixtures para configuración común de variables de entorno.

#### Verificación de tests:

```bash
# Ejecutar todos los tests con entornos correctos
./full_test.sh

# Verificar que entornos virtuales están correctamente configurados
./scripts/verify_environments.sh
```

#### Debugging de tests:

Si un test falla de forma inconsistente:
1. Verificar que se ejecuta en el entorno virtual correcto
2. Verificar que todas las dependencias están instaladas (`pip install -r requirements.txt`)
3. Verificar que `STORAGE_MODE=mock` está configurado
4. Verificar que no hay imports cruzados entre aplicaciones

## 5.1 Documentación de base de datos
* **Obligatorio:** Cada cambio en la estructura de tablas debe documentarse en
  `README_DEPLOYMENT.md` (sección "Estructura de base de datos").

## 5.2 Documentación de fmanagement
* **Obligatorio:** Cambios en el contrato de la API `fmanagement` (endpoints,
  headers o permisos) deben documentarse en `README.md` y en `fmanagement/README.md`.
* **Ruta de datos:** Cualquier cambio en la ruta de almacenamiento
  (`/data/files/external`) debe reflejarse en `README.md` y `README_DEPLOYMENT.md`.
* **Endpoints:** La lista de endpoints activos de `fmanagement` debe mantenerse
  actualizada en `README.md` (sección de gestión de ficheros).

### 5.2.1 Sincronización de configuración fmanagement (CRÍTICO)

**OBLIGATORIO:** Los archivos de configuración `fmanagement_paths.yml` deben mantenerse 
**idénticos** entre los dos proyectos para cada entorno.

#### Ubicación de archivos por entorno

| Entorno | Ruta en anewhope | Ruta en fmanagement |
|---------|------------------|---------------------|
| **macbook** | `infrastructure/environments/macbook/fmanagement_paths.yml` | `/Users/administrator/develop/fmanagement/env/macbook/fmanagement_paths.yml` |
| **dev** | `infrastructure/environments/dev/fmanagement_paths.yml` | `/Users/administrator/develop/fmanagement/env/dev/fmanagement_paths.yml` |
| **pre** | `infrastructure/environments/pre/fmanagement_paths.yml` | `/Users/administrator/develop/fmanagement/env/pre/fmanagement_paths.yml` |
| **pro** | `infrastructure/environments/pro/fmanagement_paths.yml` | `/Users/administrator/develop/fmanagement/env/pro/fmanagement_paths.yml` |

#### Contenido del archivo fmanagement_paths.yml

El archivo contiene la configuración completa de operaciones de fmanagement:

```yaml
# Configuración de permisos
permissions_source: mock | db_only
middleware_base_url: http://...
core_backend_base_url: http://...

# Rutas de almacenamiento
backend_core_base_storage: ~/data/files/external | /data/files/external
backend_ia_base_storage: ~/data/files/trainer | /data/files/trainer

# Configuración de transferencia
transfer_mode: local | remote

# SSH (solo si transfer_mode=remote)
trainer_ssh_host: trainer.example.com
trainer_ssh_user: rsync_user
trainer_ssh_key_path: /opt/anewhope/keys/rsync_key
trainer_ssh_port: 22
core_ssh_host: backend.example.com
core_ssh_user: rsync_user
core_ssh_key_path: /opt/anewhope/keys/rsync_key
core_ssh_port: 22
```

#### Reglas de sincronización

1. ✅ **Sincronización bidireccional:** Cualquier cambio en un archivo debe replicarse 
   inmediatamente en su contraparte del otro proyecto.

2. ✅ **Validación antes de commit:** Antes de hacer commit en cualquiera de los dos proyectos,
   verificar que ambos archivos del mismo entorno son idénticos.

3. ✅ **Script de verificación:** Usar el script automatizado para verificar sincronización:
   ```bash
   # Verificar todos los entornos
   ./scripts/verify_fmanagement_sync.sh
   
   # Verificar un entorno específico
   ./scripts/verify_fmanagement_sync.sh macbook
   
   # El script ignora automáticamente los comentarios de sincronización
   # (que intencionalmente son diferentes en cada archivo)
   ```
   
   Salida esperada:
   ```
   ✅ SINCRONIZADO   - Archivos idénticos (correcto)
   ❌ DESINCRONIZADO - Archivos diferentes (corregir inmediatamente)
   ```

4. ✅ **Comentarios de sincronización:** Cada archivo incluye un comentario en la cabecera
   indicando la ruta del archivo gemelo:
   ```yaml
   # SINCRONIZACIÓN: Este archivo debe mantenerse sincronizado con
   # /ruta/al/archivo/gemelo/fmanagement_paths.yml
   ```

5. ✅ **Deploy en producción:** En entornos `pre` y `pro`, verificar sincronización antes
   de cualquier deploy de fmanagement o anewhope.

#### Configuración por entorno

| Entorno | `permissions_source` | `transfer_mode` | Rutas base | SSH |
|---------|---------------------|-----------------|------------|-----|
| **macbook** | `mock` | `local` | `~/data/files/*` | No usado |
| **dev** | `db_only` | `remote` | `/data/files/*` | `*.house.loc` |
| **pre** | `db_only` | `remote` | `/data/files/*` | `*.anewhope.aws` |
| **pro** | `db_only` | `remote` | `/data/files/*` | `*.anewhope.aws` |

#### Motivo de sincronización

fmanagement se ejecuta dockerizado y necesita leer la configuración desde su propio 
entorno (`/Users/administrator/develop/fmanagement/env/{entorno}/fmanagement_paths.yml`), 
pero los valores deben coincidir exactamente con los configurados en anewhope para 
garantizar coherencia en:

- Rutas de almacenamiento (`backend_core_base_storage`, `backend_ia_base_storage`)
- URLs de servicios (`middleware_base_url`, `core_backend_base_url`)
- Configuración SSH para transferencias remotas
- Modo de transferencia de versiones

#### Flujo de trabajo recomendado

1. **Modificar** configuración en anewhope:
   ```bash
   vim infrastructure/environments/dev/fmanagement_paths.yml
   ```

2. **Copiar** inmediatamente a fmanagement:
   ```bash
   cp infrastructure/environments/dev/fmanagement_paths.yml \
      /Users/administrator/develop/fmanagement/env/dev/fmanagement_paths.yml
   ```

3. **Verificar** sincronización:
   ```bash
   diff infrastructure/environments/dev/fmanagement_paths.yml \
        /Users/administrator/develop/fmanagement/env/dev/fmanagement_paths.yml
   ```

4. **Commit** en ambos proyectos con mensaje descriptivo del cambio.

## 5.3 Nomenclatura de carpetas en storage
* **Obligatorio:** Para construir nombres de carpeta por organización y proyecto
  se deben usar los helpers de `src/2_shared_application/storage_access_structure.py`
  (`get_folder_by_id_organization`, `get_folder_by_id_project`). No se permite
  formatear manualmente los strings `ORGXXXX` o `PRJXXXX` en código de aplicación.

### 5.3.1 Infraestructura de almacenamiento por entorno (CRÍTICO)

**OBLIGATORIO:** El proyecto utiliza una estructura de carpetas específica que varía
según el entorno (macbook, dev, pre, pro) y el tipo de servidor (backend, frontend, trainer).

#### Estructura base por entorno

| Entorno | Ruta base | Descripción |
|---------|-----------|-------------|
| **macbook** | `~/data/anewhope/files/` | Desarrollo local con subdirectorios por servidor |
| **dev/pre/pro** | `/data/` | Producción - cada servidor tiene su propia estructura |

#### Organización por servidor

**En macbook (desarrollo):**
```
~/data/anewhope/
├── docs/                    # Documentación del proyecto (no para Docker)
└── files/
    ├── backend_server/      # Backend Core, Service Backend, fmanagement
    ├── frontend_server/     # Frontend, Backoffice, Middleware
    └── trainer_server/      # Backend IA (trainer)
```

**En dev/pre/pro (producción):**
Cada servidor físico tiene su contenido directamente en `/data/`:
- Backend server: `/data/backend_core/`, `/data/service_backend/`, `/data/fmanagement/`, `/data/external/`, `/data/internal/`
- Frontend server: `/data/frontend/`, `/data/backoffice/`, `/data/middleware/`, `/data/persistence/redis/`
- Trainer server: `/data/backend_ia/`, `/data/external/`, `/data/internal/`, `/data/persistence/chroma/`

#### Estructura detallada

**Backend Server:**
```
/data/                       # En producción (~/data/anewhope/files/backend_server/ en macbook)
├── backend_core/logs/       # Logs de backend_core (puerto 8003)
├── service_backend/logs/    # Logs de broker (puerto 8008)
├── fmanagement/logs/        # Logs de fmanagement (puerto 1666)
├── external/                # Contenido de clientes (organizaciones/proyectos/versiones)
│   └── ORG0001/PRJ00001/v001/
│       ├── images/
│       └── text/
├── internal/                # Contenido generado por el sistema
│   ├── models/              # Modelos LLM generados por trainer
│   └── reports/             # Informes generados por trainer
├── Mariadb/                 # Persistencia de MariaDB (volumen Docker)
└── images/                  # Imágenes Docker en tar.gz
```

**Frontend Server:**
```
/data/                       # En producción (~/data/anewhope/files/frontend_server/ en macbook)
├── frontend/logs/           # Logs de frontend (puerto 8005)
├── backoffice/logs/         # Logs de backoffice (puerto 8006)
├── middleware/logs/         # Logs de middleware (puerto 8007)
├── persistence/redis/       # Persistencia de Redis (volumen Docker)
└── images/                  # Imágenes Docker en tar.gz
```

**Trainer Server:**
```
/data/                       # En producción (~/data/anewhope/files/trainer_server/ en macbook)
├── backend_ia/logs/         # Logs de backend_ia (puerto 8004)
├── external/                # Contenido sincronizado desde backend (solo lectura)
├── internal/                # Contenido generado y sincronizado a backend
│   ├── models/              # Modelos LLM generados
│   └── reports/             # Informes generados
├── persistence/chroma/      # Persistencia de Chroma DB (volumen Docker)
└── images/                  # Imágenes Docker en tar.gz
```

#### Diferencias: external vs internal

| Carpeta | Propósito | Contenido | Sincronización |
|---------|-----------|-----------|----------------|
| **external** | Contenido de clientes | Documentos, imágenes, textos subidos por usuarios | Backend → Trainer (rsync bajo demanda) |
| **internal** | Contenido generado | Modelos LLM y reportes generados por el sistema | Trainer → Backend (rsync automático) |

**Reglas de external:**
- ✅ Estructura: `ORG####/PRJ#####/v###/` (flexible dentro de cada versión)
- ✅ Los usuarios pueden crear cualquier estructura de carpetas dentro de cada versión
- ✅ Se sincroniza desde backend a trainer cuando se ejecuta `transferversion`
- ✅ Corresponde a la variable `backend_core_base_storage` y `backend_ia_base_storage`

**Reglas de internal:**
- ✅ Estructura fija: `models/` y `reports/` con jerarquía `ORG####/PRJ#####/v###/`
- ✅ Solo la aplicación puede escribir aquí (usuarios no tienen acceso directo)
- ✅ Se sincroniza bidireccionalmente entre backend y trainer
- ✅ Models: Trainer genera → Backend sirve para descarga
- ✅ Reports: Trainer genera → Backend sirve al visor (frontend/backoffice)

#### Variables de entorno

Todas las rutas se configuran en `fmanagement_paths.yml` por entorno:

```yaml
# External (contenido de clientes)
backend_core_base_storage: ~/data/anewhope/files/backend_server/external  # macbook
backend_core_base_storage: /data/external  # dev/pre/pro

# Internal (contenido generado)
backend_core_internal_storage: ~/data/anewhope/files/backend_server/internal  # macbook
backend_core_internal_storage: /data/internal  # dev/pre/pro

# Logs por servicio
backend_core_logs_path: ~/data/anewhope/files/backend_server/backend_core/logs  # macbook
backend_core_logs_path: /data/backend_core/logs  # dev/pre/pro

# Persistencia de bases de datos
mariadb_data_path: ~/data/anewhope/files/backend_server/Mariadb  # macbook
mariadb_data_path: /data/Mariadb  # dev/pre/pro

# Versiones de imágenes Docker
backend_core_image_version: 1.0.0
```

#### Scripts de gestión

| Script | Propósito | Uso |
|--------|-----------|-----|
| `scripts/setup_data_structure.sh` | Crear toda la jerarquía de carpetas | `./scripts/setup_data_structure.sh macbook` |
| `scripts/generate_docker_env.sh` | Generar .env desde YAML para docker-compose | `./scripts/generate_docker_env.sh dev backend` |
| `scripts/verify_fmanagement_sync.sh` | Verificar sincronización de configuración | `./scripts/verify_fmanagement_sync.sh` |

#### Flujo de trabajo Docker

1. **Desarrollo (macbook)**: Usar `run.sh` de cada aplicación sin Docker
2. **Producción (dev/pre/pro)**:
   - Cada Dockerfile genera una imagen Docker versionada
   - Las imágenes se guardan en `/data/images/` como tar.gz
   - El `docker-compose.yml` de cada servidor usa las imágenes y monta volúmenes
   - Generar `.env` automáticamente: `./scripts/generate_docker_env.sh dev backend`

#### Sincronización rsync (dev/pre/pro)

**Configuración híbrida:**
- **Automática**: `internal/models/` y `internal/reports/` se sincronizan cada 5 minutos (Trainer → Backend)
- **Bajo demanda**: `external/` se sincroniza solo cuando fmanagement ejecuta `transferversion` (Backend → Trainer)
- **Full replication**: Disponible manualmente con script para recuperación ante fallas

```yaml
# En fmanagement_paths.yml
rsync_enabled: true
rsync_models_direction: trainer_to_backend
rsync_models_trigger: automatic
rsync_automatic_interval: 300  # 5 minutos
```

#### Reglas obligatorias

1. ✅ **Rutas fijas en Dockerfiles**: Los contenedores siempre usan `/app/` internamente
2. ✅ **Volúmenes en docker-compose**: Mapear desde variables de entorno (generadas desde YAML)
3. ✅ **No sincronizar**: logs/, persistence/, images/ (cada servidor tiene lo suyo)
4. ✅ **Sincronizar**: external/ (bajo demanda), internal/ (automático)
5. ✅ **Scripts como fuente de verdad**: No editar `.env` manualmente, regenerar desde YAML
6. ✅ **Validar estructura**: Ejecutar `setup_data_structure.sh` antes de primer deploy

#### Adaptación por entorno

Al desarrollar en macbook, la IA debe saber cómo adaptar rutas para producción:

| Aspecto | Macbook | Dev/Pre/Pro |
|---------|---------|-------------|
| Ruta base | `~/data/anewhope/files/{servidor}/` | `/data/` |
| Organización | Por subdirectorio `*_server/` | Por servidor físico |
| Docker | No se usa (run.sh) | docker-compose.yml por servidor |
| Sincronización | No necesaria (mismo filesystem) | rsync over SSH entre servidores |

**Documentación relacionada:**
- Configuración completa: `infrastructure/environments/{entorno}/fmanagement_paths.yml`
- Sincronización: `infrastructure/environments/README_FMANAGEMENT_SYNC.md`
- Scripts: `scripts/setup_data_structure.sh`, `scripts/generate_docker_env.sh`

## 5.4 Base de datos de proyectos (sin mocks)
* **Obligatorio:** La base `myllm_projects_db` no tiene espejo en JSON. Cualquier
  operación debe consultarse directamente en MariaDB, sin fallback a mocks.

### Tabla `flujos` (catálogo de pasos del flujo de trabajo)

La tabla `flujos` es un catálogo con los 12 pasos del flujo de trabajo para la generación
de modelos LLM. Cada proyecto tiene un campo `id_flujo` que indica su paso actual.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_flujo` | INT PK | Identificador único del paso |
| `clave` | VARCHAR(50) UNIQUE | Identificador interno (snake_case) |
| `nombre` | VARCHAR(100) | Nombre visible del paso |
| `descripcion` | VARCHAR(255) | Descripción del paso |
| `emoji` | VARCHAR(10) | Emoji representativo |
| `color` | VARCHAR(20) | Color hexadecimal para UI |
| `orden` | INT | Orden secuencial (1-12) |
| `es_bloque_inicio` | TINYINT(1) | Pertenece al bloque inicial |
| `es_bloque_iteracion` | TINYINT(1) | Pertenece al bloque de iteración |

**Relación con `proyectos`:**
- Campo `proyectos.id_flujo` → FK a `flujos.id_flujo`
- Valor por defecto: 1 (propuesta_cliente)
- ON DELETE SET NULL, ON UPDATE CASCADE

**Vista útil:** `view_proyectos_flujo` - consulta proyectos con información del flujo actual.

**Migración:** `infrastructure/database/migrations/001_create_flujos_table.sql`

### Tipos de cambio en proyectos (OBLIGATORIO)

La tabla `tipos_cambio` define los tipos de cambio que se registran en la tabla `cambios`.
Los triggers y la lógica del Backend Core usan estos tipos para auditoría.

| Clave | Nombre | Descripción | Origen |
|-------|--------|-------------|--------|
| `alta_proyecto` | Alta proyecto | Creación de un nuevo proyecto | Trigger INSERT |
| `modificacion_proyecto` | Modificación proyecto | Cambio de nombre/descripción | Trigger UPDATE |
| `cambio_flujo` | Cambio de flujo | Cambio de paso en el flujo | Trigger UPDATE |
| `borrado_proyecto` | Borrado de proyecto | Eliminación del proyecto | Trigger DELETE |
| `bloquear_proyecto` | Bloquear proyecto | Bloqueo del proyecto | Trigger UPDATE |
| `desbloquear_proyecto` | Desbloquear proyecto | Desbloqueo del proyecto | Trigger UPDATE |
| `asignacion_usuario` | Asignación usuario | Asignación de usuario | Backend Core |
| `quitar_usuario` | Quitar usuario | Eliminación de usuario | Backend Core |
| `solicitud_soporte` | Solicitud soporte proyecto | Solicitud de soporte | Backend Core |
| `respuesta_soporte` | Respuesta soporte proyecto | Respuesta a soporte | Backend Core |

**Triggers automáticos en tabla `proyectos`:**
- `tr_proyecto_after_insert`: Crea registro en `estado` (v1) + `cambios` (alta)
- `tr_proyecto_flujo_update`: Actualiza `estado` + registra cambio de flujo
- `tr_proyecto_before_delete`: Registra borrado antes de eliminar

**Función auxiliar:**
- `fn_get_estado_por_flujo(id_flujo, campo)`: Retorna TRUE/FALSE según orden del flujo

**Procedimiento para cambios manuales:**
```sql
CALL sp_registrar_cambio_proyecto(
    p_id_proyecto,
    p_id_organizacion,
    'Asignación usuario',
    'Usuario X asignado al proyecto',
    p_id_usuario
);
```

**Flujo de alta de proyecto:**
1. Frontend: Modal "Crear proyecto" → `save_new_project()`
2. API Client: `create_organization_project()` → POST /projects
3. Middleware: Valida permisos → Broker → Backend Core
4. Backend Core: INSERT en `proyectos` (nombre, descripcion, id_organizacion, active=1, id_flujo=1)
5. Trigger BD: 
   - Crea registro en `estado` (versión 1, campos booleanos según id_flujo=1)
   - Crea registro en `cambios` (tipo="Alta proyecto")

**Migración:** `infrastructure/database/migrations/003_triggers_proyecto_estado_cambios.sql`

### Endpoints de API para proyectos (OBLIGATORIO)

Los endpoints de proyectos siguen el flujo arquitectónico completo:

```
Frontend → Middleware → Broker → Backend Core → MariaDB
```

**Endpoints disponibles:**

| Endpoint | Método | Permiso | Descripción |
|----------|--------|---------|-------------|
| `/projects/organization/{org_id}` | GET | `project_read` | Listar proyectos |
| `/projects` | POST | `project_create` | Crear proyecto |
| `/projects/{id}` | PATCH | `project_update` | Actualizar proyecto |
| `/projects/{id}` | DELETE | `project_delete` | Eliminar proyecto |
| `/projects/{id}/support` | POST | - | Solicitar soporte |

**Archivos por capa:**

| Capa | API | Router/Lógica | Cliente |
|------|-----|---------------|---------|
| **Frontend** | - | `web_frontend.py` | `adapters/api_client.py` |
| **Middleware** | `apife.py` | `routermiddleware.py` | `broker_backend_client.py` |
| **Broker** | `apibe.py` | `routerbroker.py` | `interfacetocore.py` |
| **Backend Core** | `apicore.py` | `routercore.py` | - |

**Reglas obligatorias:**
1. ✅ Toda operación de proyecto debe validar permisos en el Middleware (HTTP 403 si no tiene permiso)
2. ✅ Los headers `Authorization`, `X-Session-Token` y `X-Client-App` deben propagarse en cada capa
3. ✅ Las operaciones CREATE/UPDATE/DELETE activan triggers que actualizan `estado` y `cambios`
4. ✅ La operación de soporte usa `sp_registrar_cambio_proyecto` en Backend Core
5. ✅ Los métodos de UI (`rx.button`) deben usar `rx.cond()` para mostrar/ocultar según permisos

**Ejemplo de validación en Middleware (Security by Design):**
```python
# En apife.py - OBLIGATORIO para endpoints que modifican datos
@app.post("/projects", response_model=ProjectCreateResponse)
def create_project_endpoint(...):
    # SECURITY BY DESIGN: Validar permiso antes de ejecutar
    if not router.has_low_level_permission(session, "project_create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos para crear proyectos",
        )
    # ... resto de la lógica
```

**Ejemplo de validación en UI (Reflex):**
```python
# En web_frontend.py - OBLIGATORIO para botones de acción
rx.cond(
    State.can_project_create,  # Permiso desde SharedSessionState
    rx.button(
        "Crear proyecto",
        on_click=State.create_project,
    ),
    rx.fragment(),  # No mostrar si no tiene permiso
)
```

### Sistema de Conversaciones Cliente-Interno (OBLIGATORIO)

El sistema de conversaciones permite comunicación bidireccional entre usuarios cliente (frontend)
y usuarios internos (backoffice) sobre proyectos y tickets de soporte.

**Arquitectura Cross-Database:**

El sistema presenta un desafío arquitectónico único: las tablas de conversaciones están en
`myllm_projects_db`, pero referencian usuarios y organizaciones que están en `myllm_core_db`.
MariaDB/MySQL **NO permite crear Foreign Keys entre bases de datos diferentes**.

**Decisión arquitectónica:** (Ver ADR 008: `docs/adr/008_conversaciones_cross_database.md`)
- ✅ Todas las tablas de conversaciones están en `myllm_projects_db`
- ✅ Las FKs a `users` y `organizations` **NO existen** (imposibilidad técnica)
- ✅ La integridad referencial se valida **en la capa de aplicación**
- ✅ Las FKs locales (a `tickets`, `proyectos_roles_base`) **SÍ existen**

**Tablas del sistema:**

1. `asignaciones_organizaciones_internas` - Asignación de usuarios internos a organizaciones
2. `conversaciones` - Registro de cada conversación
3. `participantes_conversacion` - Participantes de cada conversación
4. `mensajes_conversacion` - Todos los mensajes
5. `conversaciones_tickets_relacionados` - Relación N:M con tickets

**Migración:** `infrastructure/database/migrations/007_conversaciones_sistema_final.sql`

**REGLA CRÍTICA: Validación Cross-Database Obligatoria**

Cuando crees o modifiques conversaciones, mensajes o participantes, **SIEMPRE** debes:

1. **Usar dos engines separados:**
   ```python
   from sqlalchemy import create_engine

   # Engine para myllm_core_db (users, organizations)
   engine_core = create_engine("mysql+pymysql://user:pass@localhost/myllm_core_db")

   # Engine para myllm_projects_db (conversaciones, tickets, proyectos)
   engine_projects = create_engine("mysql+pymysql://user:pass@localhost/myllm_projects_db")
   ```

2. **Validar existencia ANTES de insertar:**
   ```python
   # ❌ INCORRECTO - Insertar sin validar
   result = engine_projects.execute(
       text("INSERT INTO conversaciones (id_organizacion, id_usuario_cliente, ...) VALUES (:org, :user, ...)"),
       {"org": org_id, "user": user_id}
   )

   # ✅ CORRECTO - Validar primero en myllm_core_db
   with engine_core.connect() as conn:
       # Validar organización
       org = conn.execute(
           text("SELECT id FROM organizations WHERE id = :org_id"),
           {"org_id": org_id}
       ).fetchone()
       if not org:
           raise ValueError(f"Organización {org_id} no existe")

       # Validar usuario
       user = conn.execute(
           text("SELECT id FROM users WHERE id = :user_id"),
           {"user_id": user_id}
       ).fetchone()
       if not user:
           raise ValueError(f"Usuario {user_id} no existe")

   # Ahora sí, insertar en myllm_projects_db
   with engine_projects.connect() as conn:
       result = conn.execute(
           text("INSERT INTO conversaciones (id_organizacion, id_usuario_cliente, ...) VALUES (:org, :user, ...)"),
           {"org": org_id, "user": user_id}
       )
   ```

3. **Campos que requieren validación cross-database:**
   - `conversaciones.id_organizacion` → `myllm_core_db.organizations.id`
   - `conversaciones.id_usuario_cliente` → `myllm_core_db.users.id`
   - `conversaciones.cerrada_por` → `myllm_core_db.users.id`
   - `asignaciones_organizaciones_internas.id_usuario_interno` → `myllm_core_db.users.id`
   - `asignaciones_organizaciones_internas.id_organizacion` → `myllm_core_db.organizations.id`
   - `participantes_conversacion.id_usuario` → `myllm_core_db.users.id`
   - `mensajes_conversacion.id_usuario_emisor` → `myllm_core_db.users.id`

**Adapter disponible:**

El adapter `src/2_shared_application/adapters/conversaciones_adapter.py` implementa todas las
validaciones necesarias. **SIEMPRE úsalo en lugar de queries directas.**

**Funciones principales del adapter:**

| Función | Descripción | Validación Cross-DB |
|---------|-------------|---------------------|
| `asignar_usuario_interno_a_organizacion()` | Asigna interno a organización | ✅ Valida user y org |
| `crear_conversacion()` | Crea nueva conversación | ✅ Valida user_cliente y org |
| `enviar_mensaje()` | Envía mensaje en conversación | ✅ Valida user_emisor |
| `unirse_a_conversacion()` | Usuario interno se une | ✅ Valida user_interno |
| `cerrar_conversacion()` | Cierra conversación | ✅ Valida cerrada_por |
| `obtener_conversaciones_organizacion()` | Lista conversaciones | - |
| `obtener_mensajes()` | Obtiene mensajes | - |
| `marcar_mensajes_como_leidos()` | Marca mensajes leídos | - |

**Ejemplo de uso del adapter:**

```python
from src.2_shared_application.adapters import conversaciones_adapter
from sqlalchemy import create_engine

# Crear engines
engine_core = create_engine("mysql+pymysql://user:pass@localhost/myllm_core_db")
engine_projects = create_engine("mysql+pymysql://user:pass@localhost/myllm_projects_db")

# Crear conversación (validación automática incluida)
id_conv = conversaciones_adapter.crear_conversacion(
    engine=engine_projects,
    id_organizacion=1,
    id_usuario_cliente=5,
    asunto="Consulta sobre proyecto X",
    id_ticket_principal=123,
    prioridad="media"
)

# Enviar mensaje
id_msg = conversaciones_adapter.enviar_mensaje(
    engine=engine_projects,
    id_conversacion=id_conv,
    id_usuario_emisor=5,
    tipo_emisor="cliente",
    texto_mensaje="Necesito ayuda con la configuración"
)
```

**Sistema de triggers automáticos:**

El sistema usa triggers para mantener contadores actualizados automáticamente. **NO los modifiques manualmente.**

| Trigger | Acción | Efecto |
|---------|--------|--------|
| `after_mensaje_insert` | Nuevo mensaje | Actualiza `total_mensajes`, `mensajes_sin_leer_*`, `ultimo_mensaje_*` |
| `after_mensaje_leido_cliente` | Marca leído cliente | Decrementa `mensajes_sin_leer_cliente` |
| `after_mensaje_leido_interno` | Marca leído interno | Decrementa `mensajes_sin_leer_interno` |

**Distinción Cliente/Interno:**

El sistema distingue dos tipos de participantes mediante el enum `TipoParticipante`:

- **`cliente`**: Usuarios del frontend (usuarios cliente de organizaciones)
- **`interno`**: Usuarios del backoffice (equipo interno que da soporte)

**Reglas de visibilidad:**
- Los mensajes de tipo `interno` incrementan `mensajes_sin_leer_cliente`
- Los mensajes de tipo `cliente` incrementan `mensajes_sin_leer_interno`
- Cada tipo solo puede marcar como leídos sus propios mensajes

**Entidades de dominio:**

Las entidades están en `src/1_shared_domain/conversacion.py`:

- `Conversacion` - Entidad principal con métodos: `esta_activa()`, `es_urgente()`, `cambiar_estado()`
- `MensajeConversacion` - Mensaje con métodos: `es_de_cliente()`, `marcar_como_leido_por_cliente()`, `editar()`
- `ParticipanteConversacion` - Participante con métodos: `es_cliente()`, `actualizar_ultimo_acceso()`
- `AsignacionOrganizacionInterna` - Asignación con métodos: `desactivar()`, `reactivar()`

**Tests:**

```bash
# Tests unitarios (sin base de datos)
pytest tests/unit/test_conversacion_entities.py -v

# Tests de integración (con base de datos)
pytest tests/integration/test_conversaciones_adapter.py -v
```

**Vista útil:**

`v_conversaciones_activas` - Conversaciones abiertas o en curso con información consolidada

**Documentación completa:**

- Arquitectura y uso: `README.md` → "Sistema de Conversaciones Cliente-Interno"
- ADR completo: `docs/adr/008_conversaciones_cross_database.md`
- Documentación técnica: `docs/SISTEMA_CONVERSACIONES.md`

**Reglas de diseño obligatorias:**

1. ✅ **NUNCA** intentes crear FKs entre `myllm_core_db` y `myllm_projects_db`
2. ✅ **SIEMPRE** usa dos engines separados para operaciones cross-database
3. ✅ **SIEMPRE** valida users/organizations en `myllm_core_db` antes de insertar en `myllm_projects_db`
4. ✅ **SIEMPRE** usa el adapter en lugar de queries directas
5. ✅ **NUNCA** modifiques manualmente los contadores (`total_mensajes`, `mensajes_sin_leer_*`) - los triggers lo hacen
6. ✅ Respeta la distinción `cliente`/`interno` en tipos de emisor y participante
7. ✅ Las conversaciones están fuertemente acopladas a proyectos/tickets, por eso viven en `myllm_projects_db`

## 5.5 Transferencia de versiones (Backend Core ↔ Trainer)

La transferencia de versiones permite replicar proyectos entre el servidor backend y el 
servidor trainer para entrenamiento de modelos de IA.

**Arquitectura:**
```
Backend Core → fmanagement → rsync/SSH → Servidor Trainer
                              (o copia local en macbook)
```

**Modos de transferencia:**
| Modo | Variable | Uso | Mecanismo |
|------|----------|-----|-----------|
| Local | `transfer_mode: local` | Desarrollo (macbook) | Copia recursiva |
| Remoto | `transfer_mode: remote` | Producción (dev/pre/pro) | rsync over SSH |

**Variables de entorno requeridas (env.yaml):**
```yaml
# Rutas de almacenamiento
backend_core_base_storage: /data/files/external  # Servidor backend
backend_ia_base_storage: /data/files/trainer     # Servidor trainer

# Configuración de transferencia
transfer_mode: local  # "local" o "remote"

# SSH (solo modo remote)
trainer_ssh_host: trainer.internal
trainer_ssh_user: rsync_user
trainer_ssh_key_path: /opt/anewhope/keys/rsync_key
trainer_ssh_port: "22"
```

**Endpoints:**
- **Backend Core:** `POST /fmo/transferversion`
- **fmanagement:** `POST /fmo/transferversion`

**Permisos requeridos:** `version_create`

**Reglas obligatorias:**
1. ✅ Toda transferencia requiere permiso `version_create` validado en cada capa
2. ✅ Los headers `Authorization` y `X-Session-Token` deben propagarse hasta fmanagement
3. ✅ Las rutas de almacenamiento deben configurarse en `env.yaml` por entorno
4. ✅ En macbook, usar `transfer_mode: local` para emulación
5. ✅ En producción, configurar claves SSH y usar `transfer_mode: remote`

**Script de configuración (macbook):**
```bash
./scripts/setup_transfer_environment.sh
```

**Tests:**
- fmanagement: `go test -v -run TestTransferVersion`
- Backend Core: `pytest src/apps/3_backend/tests/test_version_transfer.py`

### Scripts de mantenimiento
- `clear_caches.sh`: limpia caches de Reflex (`.web`, `.states`) y caches de tooling
  (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `.hypothesis`).

### Modos de almacenamiento (storage_mode)

**Variable:** `storage_mode` en `env.yaml`

| Modo | Descripción | Uso |
|------|-------------|-----|
| `mock` | Solo archivos JSON | Pruebas sin base de datos |
| `mock_and_db` | JSON + sincronización con MariaDB | Desarrollo híbrido |
| `db_only` | **Solo MariaDB** | Desarrollo normal y **producción** |

**Reglas obligatorias:**
1. ✅ **En desarrollo (macbook):** Usar preferiblemente `db_only` para reflejar producción
2. ✅ **En producción (pro):** OBLIGATORIO `db_only` - el código lo fuerza automáticamente
3. ✅ **Todas las operaciones CRUD** deben ir contra MariaDB cuando `storage_mode=db_only`
4. ❌ **Prohibido:** Usar `mock` o `mock_and_db` en producción

### Sincronización DB → JSON (active_sync_db_jsons)

**Variable:** `active_sync_db_jsons` en `env.yaml`

- `"1"` = Habilitada (copia datos de MariaDB a JSON periódicamente)
- `"0"` = Deshabilitada (**OBLIGATORIO en producción**)

**Reglas obligatorias:**
1. ✅ **En desarrollo:** Puede estar habilitada para tener backup en JSON
2. ✅ **En producción (pro):** OBLIGATORIO `"0"` - el código bloquea sincronización
3. ❌ **Prohibido:** Habilitar sincronización en producción (expone datos en JSON)

### Seguridad en producción (entorno pro)

**CRÍTICO:** El entorno de producción tiene restricciones de seguridad automáticas:

1. **storage_mode forzado:** Si se detecta otro modo, se fuerza a `db_only`
2. **Sincronización bloqueada:** No se ejecuta aunque esté configurada
3. **Sin archivos moks:** Los Dockerfiles eliminan la carpeta automáticamente

**Build de Docker para producción:**
```bash
docker build --build-arg ENVIRONMENT=pro -t mi-app:pro .
```

**Verificaciones automáticas en código (routermiddleware.py):**
- `_get_storage_mode()`: Fuerza `db_only` si `ENVIRONMENT=pro`
- `run_periodic_sync()`: Bloquea ejecución si `ENVIRONMENT=pro`

### Archivos moks (datos de prueba)

**Ubicación:** `src/2_shared_application/moks/`

**Reglas obligatorias:**
1. ✅ **Solo para desarrollo/pruebas** sin base de datos disponible
2. ✅ **En producción:** La carpeta se elimina automáticamente en el build de Docker
3. ❌ **Prohibido:** Incluir archivos moks en imágenes de producción
4. ❌ **Prohibido:** Usar archivos moks como fuente de datos en producción

### Configuración por entorno

**Archivo de entorno global:** `.envglobal` en la raíz del proyecto define el entorno activo.

```
# .envglobal
current_environment: macbook
```

**Valores válidos:** `macbook`, `dev`, `pre`, `pro`

**Orden de carga:**
1. `.envglobal` (define el entorno base)
2. `.env` (puede sobrescribir con `ENVIRONMENT=<entorno>`)
3. `env.yaml` del entorno activo
4. `protected_values.py` del entorno activo

**Rutas de configuración por entorno:**
- Variables públicas: `infrastructure/environments/<entorno>/env.yaml`
- Variables protegidas: `infrastructure/environments/<entorno>/protected_values.py`

### Endpoint de Consulta de Entorno Activo (OBLIGATORIO)

**CRÍTICO:** El sistema expone endpoints para consultar el entorno activo en tiempo de ejecución.
Esto es **obligatorio** para servicios que necesitan configurarse dinámicamente (especialmente fmanagement).

#### Endpoints disponibles

| Servicio | Endpoint | Puerto | Uso principal |
|----------|----------|--------|---------------|
| **Broker** | `GET /config/environment` | 8008 | Fuente primaria |
| **Backend Core** | `GET /config/environment` | 8003 | Usado por fmanagement |

#### Respuesta

```json
{
    "environment": "macbook",  // Valores: macbook, dev, pre, pro
    "source": "ENVIRONMENT"
}
```

#### Flujo para fmanagement

```
fmanagement (Go:1666) → GET /config/environment → Backend Core (Python:8003)
                      ←─── {"environment": "macbook"} ───┘
```

**REGLA:** fmanagement debe consultar este endpoint en su inicialización para configurar:
- Rutas base del sistema de archivos
- Configuración de conexiones a bases de datos
- URLs de servicios externos

#### Implementación obligatoria en servicios externos (Go, etc.)

```go
// OBLIGATORIO en fmanagement durante inicialización
func getActiveEnvironment() string {
    resp, err := http.Get("http://localhost:8003/config/environment")
    if err != nil {
        log.Printf("WARN: No se pudo obtener entorno, usando 'unknown'")
        return "unknown"
    }
    defer resp.Body.Close()
    
    var result struct {
        Environment string `json:"environment"`
    }
    json.NewDecoder(resp.Body).Decode(&result)
    return result.Environment
}
```

### Variables de aplicaciones en servidores

Cada `env.yaml` define variables de host y puerto para cada aplicación. Esto permite configurar
la comunicación entre servicios según el entorno de despliegue.

**Regla obligatoria de puertos:** `8000 + primer dígito del nombre de la carpeta`

| Aplicación | Puerto | Variables |
|------------|--------|-----------|
| Backend Core | 8003 | `backend_core_host`, `backend_core_port` |
| Trainer | 8004 | `trainer_host`, `trainer_port` |
| Frontend | 8005 | `frontend_host`, `frontend_port` |
| Backoffice | 8006 | `backoffice_host`, `backoffice_port` |
| Middleware | 8007 | `middleware_host`, `middleware_port` |
| Broker | 8008 | `broker_host`, `broker_port` |
| Fmanagement | 1666 | `fmanagement_host`, `fmanagement_port` |

**Dominios por entorno:**

| Entorno | Dominio interno | Dominio público | Formato FQDN interno |
|---------|-----------------|-----------------|----------------------|
| macbook | localhost | localhost | `localhost` |
| dev | house.loc | house.loc | `<servidor>.house.loc` |
| pre | anewhope.aws | getmyllm.com | `<servidor>.anewhope.aws` |
| pro | anewhope.aws | getmyllm.com | `<servidor>.anewhope.aws` |

**Nota pre/pro:** El dominio público `getmyllm.com` solo lo usa nginx para exponer el frontend.
Los servicios internos se comunican usando el dominio interno `anewhope.aws`.

### Patrón de carga de URLs de servicio en código

**CRÍTICO:** Las aplicaciones deben usar `get_env_value()` de `env_settings.py` para obtener URLs de servicios.
Esto asegura que las variables de `env.yaml` se cargan correctamente antes de leer de `os.environ`.

**Patrón correcto:**

```python
# ✅ CORRECTO: Usa get_env_value() que carga env.yaml primero
from src.2_shared_application.config import env_settings

def _get_middleware_base_url() -> str:
    return env_settings.get_env_value("MIDDLEWARE_BASE_URL", "http://localhost:8007")
```

**Patrón incorrecto:**

```python
# ❌ INCORRECTO: No carga env.yaml, solo lee os.environ directamente
import os

def _get_middleware_base_url() -> str:
    return os.environ.get("MIDDLEWARE_BASE_URL", "http://localhost:8007")
```

**Orden de prioridad de valores:**
1. Variable de entorno explícita (ej: `export MIDDLEWARE_BASE_URL=...`)
2. Valor de `env.yaml` del entorno activo
3. Valor de `protected_values.py` (solo como fallback adicional)
4. Valor por defecto hardcodeado

**Archivos que implementan este patrón:**
- `src/apps/5_web_frontend/adapters/api_client.py` → `_get_middleware_base_url()`
- `src/apps/6_web_backoffice/adapters/api_client.py` → `_get_middleware_base_url()`
- `src/apps/7_service_frontend/apife.py` → `_get_broker_base_url()`
- `src/apps/8_service_backend/apibe.py` → `_get_core_base_url()`, `_get_trainer_base_url()`
- `src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py` → `load_fmanagement_settings()`

**Distribución en servidores:**
- **frontend.***: Frontend, Backoffice, Middleware, Redis
- **backend.***: Backend Core, Broker, Fmanagement, MariaDB
- **trainer.***: Trainer (Backend IA), Ollama, BD Vectorial

### Servidor Trainer - Servicios planificados

El servidor trainer albergará servicios de IA con la siguiente arquitectura:

| Servicio | Puerto | Función |
|----------|--------|---------|
| `4_trainer` | 8004 | API FastAPI que recibe peticiones del Broker |
| Ollama | 11434 | Servidor de modelos LLM locales (llama3, mistral, etc.) |
| BD Vectorial | Por definir | Almacenamiento de embeddings para RAG |

**Flujo de comunicación:**
```
Broker → 4_trainer → Ollama (inferencia LLM)
              ↓
         BD Vectorial (búsqueda semántica)
```

**Regla de diseño:** `4_trainer` se comunica **directamente** con Ollama (sin intermediarios como N8N)
para minimizar latencia y complejidad en el MVP.

### Variables protegidas (protected_values.py)

Cada entorno define hosts de servicios en su `protected_values.py`:

| Entorno | Host MariaDB/Broker/Core | CLI MariaDB |
|---------|--------------------------|-------------|
| macbook | `localhost` | `/usr/local/opt/mariadb@10.6/bin/mysql` |
| dev | `backend.house.loc` | `/usr/bin/mariadb` |
| pre/pro | `backend.anewhope.aws` | `/usr/bin/mariadb` |

**Obligatorio en producción:** Cambiar todas las contraseñas y claves JWT antes del despliegue.

**Uso obligatorio:**
```python
from src.2_shared_application.config.env_settings import (
    get_environment_name,
    get_env_value,
    get_protected_value,
    get_environment_paths,
)

# Obtener entorno activo
env = get_environment_name()  # "macbook", "dev", "pre" o "pro"

# Obtener valor de env.yaml
api_url = get_env_value("api_base_url", "http://localhost:8007")

# Obtener valor de protected_values.py
db_password = get_protected_value("mariadb_password")
```

**Prohibido:** importar `protected_values.py` directamente en código de aplicación.

**Plataformas:** `macbook` usa macOS 14.8.1; `dev/pre/pro` usan Oracle Linux 10.

### Entornos virtuales dedicados

**OBLIGATORIO:** Cada aplicación usa su propio entorno virtual dedicado. Esta regla es crítica para:
- Aislar dependencias entre servicios
- Evitar conflictos de versiones de librerías
- Garantizar que los tests reflejan el comportamiento real en producción
- Facilitar debugging y troubleshooting

#### Matriz de asignación entorno virtual → aplicación:

| Entorno Virtual | Puerto | Aplicaciones | Script run.sh | Script entrypoint.sh |
|-----------------|--------|--------------|---------------|----------------------|
| `.venv_backend313` | 8003 | `3_backend` | ✅ Usa entorno | ❌ Docker (deps en imagen) |
| `.venv_trainer312` | 8004 | `4_trainer` | ✅ Usa entorno | ❌ Docker (deps en imagen) |
| `.venv_frontend313` | 8005 | `5_web_frontend`, `2_shared_application` | ✅ Usa entorno | ❌ Docker (deps en imagen) |
| `.venv_backoffice313` | 8006 | `6_web_backoffice` | ✅ Usa entorno | ❌ Docker (deps en imagen) |
| `.venv_middleware313` | 8007 | `7_service_frontend` | ✅ Usa entorno | ❌ Docker (deps en imagen) |
| `.venv_broker313` | 8008 | `8_service_backend` | ✅ Usa entorno | ❌ Docker (deps en imagen) |

**NOTA IMPORTANTE sobre Python 3.12 en 4_trainer:**
El Backend IA (`4_trainer`) usa **Python 3.12** (no 3.13) debido a requisitos de compatibilidad
con dependencias de IA como TensorFlow y Keras. Ver `src/docs/stack_of_technologies.adr` para más detalles.

#### Reglas de diseño de entornos:

1. ✅ **Aislamiento total:** Ningún entorno virtual es compartido por más de una aplicación
2. ✅ **Scripts `run.sh`:** Cada `src/apps/*/run.sh` activa automáticamente su entorno dedicado
3. ✅ **Scripts `entrypoint.sh`:** Usan Python del contenedor Docker (dependencias en imagen)
4. ✅ **Tests:** El script `full_test.sh` activa el entorno correcto según el módulo testeado
5. ✅ **Verificación:** El script `./scripts/verify_environments.sh` valida la configuración

#### Verificación de entornos:

```bash
# Verificar que cada aplicación usa su entorno dedicado
./scripts/verify_environments.sh

# Resultado esperado:
# ✅ 16 verificaciones exitosas
# ❌ 0 errores
# ⚠️  1 warning (trainer pendiente)
```

#### Consecuencias de compartir entornos (❌ PROHIBIDO):

Si dos aplicaciones comparten el mismo entorno virtual:
- ❌ Conflictos de versiones de dependencias
- ❌ Tests que pasan localmente pero fallan en producción
- ❌ Comportamiento impredecible entre entornos (dev/pre/pro)
- ❌ Debugging complejo y pérdida de tiempo

#### Documentación relacionada:

- Auditoría completa: `docs/VIRTUAL_ENVIRONMENTS_AUDIT.md`
- Script de verificación: `scripts/verify_environments.sh`
- Asignaciones en `README.md` (sección "Entornos virtuales dedicados")

### Redis para sesión compartida
- **Obligatorio:** Redis 8.x+ instalado y corriendo para compartir state entre frontend y backoffice.
- **Configuración:**
  - Host: `localhost` (desarrollo) o IP interna (producción)
  - Puerto: `6379` (estándar)
  - Password: almacenado en `protected_values.py` (variable `redis_password`)
  - Base de datos: `0` (compartida entre todas las apps Reflex)
  - TTL sesiones: configurable en `env.yaml` (`redis_token_expiration`)
- **Gestión:** Usar `./scripts/manage_redis.sh {install|start|stop|status|sessions}`
- **Monitoreo:** `./scripts/monitor_redis_sessions.py` muestra sesiones activas en tiempo real
- **State manager:** Reflex apps deben usar `state_manager_mode=rx.StateManagerMode.REDIS` en `rxconfig.py`
- **Arquitectura:**
  - Frontend (8005) y Backoffice (8006) comparten automáticamente el mismo state vía Redis
  - Logout en una app invalida sesión en todas
  - Permisos y datos de usuario sincronizados en tiempo real
- **Variables en env.yaml:**
  ```yaml
  redis_host: localhost
  redis_port: "6379"
  redis_db: "0"
  redis_token_expiration: "3600"  # 1 hora
  redis_lock_expiration: "10000"
  redis_lock_warning_threshold: "1000"
  ```
- **Variable en protected_values.py:**
  ```python
  redis_password = "PassRedis2025"
  ```
- **Documentación:** `docs/REDIS_IMPLEMENTATION.md` y `docs/SWITCHING_DESIGN.md`

### Dockerfiles y despliegues

**Reglas de Dockerfiles:**
- **ARG ENVIRONMENT:** Cada Dockerfile debe aceptar `ARG ENVIRONMENT=dev` para configuración por entorno.
- **Limpieza en producción:** Si `ENVIRONMENT=pro`, eliminar `/app/src/2_shared_application/moks`.
- **Puerto fijo:** Exponer puerto según regla `8000 + primer_dígito_carpeta`.

**Estructura de Dockerfile estándar:**

```dockerfile
FROM python:3.13-slim
WORKDIR /app

ARG ENVIRONMENT=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=${ENVIRONMENT}

COPY src/apps/<app>/requirements.txt /app/requirements.txt
COPY src/apps/<app>/entrypoint.sh /app/entrypoint.sh

RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app

# SEGURIDAD: En producción, eliminar moks
RUN if [ "$ENVIRONMENT" = "pro" ]; then \
        rm -rf /app/src/2_shared_application/moks; \
    fi

EXPOSE <puerto>
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
```

**Compose por servidor:** usar `infrastructure/servers/*/docker-compose.yml`.

| Servidor | Servicios | Archivo `.env.example` |
|----------|-----------|------------------------|
| frontend | Redis, Nginx, web_frontend, web_backoffice, service_frontend | Sí |
| backend | MariaDB, backend_core, service_backend, fmanagement | Sí |
| trainer | trainer_api, ollama (planificado), keras_service (placeholder) | Sí |
| macbook | Todos (para desarrollo local en contenedores) | Sí |

**Variables de entorno críticas en docker-compose:**

```yaml
environment:
  ENVIRONMENT: ${ENVIRONMENT:-dev}          # Entorno activo
  STORAGE_MODE: ${STORAGE_MODE:-db_only}    # Modo de almacenamiento
  REDIS_HOST: redis                          # Nombre del servicio Redis
  REDIS_PASSWORD: ${REDIS_PASSWORD:-}        # Desde protected_values.py
  MIDDLEWARE_BASE_URL: http://service_frontend:8007  # Dentro del compose
```

**Macbook:** MariaDB, Redis y Fmanagement se ejecutan nativamente; el docker-compose usa
`host.docker.internal` para acceder a servicios del host.

**Linux (dev/pre/pro):** Todos los servicios se despliegan en Docker con redes dedicadas.

### Sincronización OTP (frontend)
- **Obligatorio:** Al actualizar OTP, el cambio debe persistirse en JSON y MariaDB
  de forma sincrónica (modo `mock_and_db` o `db_only`).
- **Validación:** Debe existir verificación de consistencia entre `users.json` y la
  tabla `users`, con registro en `src/apps/5_web_frontend/logs/frontend_secure.log`.

### Orden de persistencia en Backend Core (CRÍTICO)
- **Obligatorio:** En `store_users()` de `storage_adapter.py`, la sincronización con
  MariaDB **debe ejecutarse ANTES** de escribir el JSON local.
- **Razón:** Si la BD falla, el JSON local no debe quedar actualizado para evitar
  desincronización del OTP.
- **Flujo correcto:**
  1. Sincronizar con MariaDB (si `STORAGE_MODE` es `mock_and_db` o `db_only`)
  2. Si la sincronización falla → lanzar excepción, NO actualizar JSON
  3. Solo si la BD se actualizó correctamente → escribir JSON local
- **Archivo:** `src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py`

### Agentes automáticos por proyecto
- **Obligatorio:** Al crear un proyecto se generan 4 agentes automáticos con el
  patrón `agente_rol_organizacion_proyecto` y roles `identity_type_id` 10-13.
- **Persistencia:** Los agentes deben guardarse en `users.json` y en la tabla `users`.

### Borrado lógico de usuarios (OBLIGATORIO)

**CRÍTICO:** El sistema usa **borrado LÓGICO**, nunca físico. Los usuarios NUNCA se eliminan de la base de datos.

#### Reglas de implementación:

1. **Borrar usuario** = `UPDATE users SET active = 0 WHERE user_id = ?`
2. **Habilitar usuario** = `UPDATE users SET active = 1 WHERE user_id = ?`
3. **NUNCA usar** `DELETE FROM users`

#### Diferencia entre Frontend y Backoffice:

| Aplicación | Consulta | Propósito |
|------------|----------|-----------|
| **Frontend** | `active_only=true` | Solo muestra usuarios activos |
| **Backoffice** | `active_only=false` | Muestra todos para reactivar inactivos |

#### Flujo arquitectónico:

```
UI (Frontend/Backoffice) → Middleware → Broker → Backend Core → MariaDB
     update_user_status()    PUT /users/{id}/status    UPDATE users SET active = ?
```

#### Indicadores visuales obligatorios:

- **Badge "Activo"** (verde): `active = true`
- **Badge "Inactivo"** (rojo): `active = false`

#### Permisos requeridos (Security by Design):

Solo `identity_type_id` en `(1, 2, 10)` pueden gestionar usuarios:
- Validar en UI con `rx.cond(State.can_manage_org_users, ...)`
- Validar en Middleware antes de ejecutar (HTTP 403 si no tiene permiso)

#### Archivos involucrados:

| Capa | Archivo | Método |
|------|---------|--------|
| Frontend State | `web_frontend.py` | `delete_user()` |
| Backoffice State | `web_backoffice.py` | `enable_user()`, `disable_user()`, `delete_user()` |
| API Client | `api_client.py` | `update_user_status()` |
| Middleware API | `apife.py` | `PUT /users/{user_id}/status` |
| Middleware Router | `routermiddleware.py` | `update_user_status()` |
| Backend Core | `routercore.py` | `update_user_status()` |

### SharedSessionState (estado compartido Reflex)
- **Ubicación:** `src/2_shared_application/reflex_shared/shared_session_state.py`
- **Obligatorio:** Heredar de `SharedSessionState` en `FrontendState` y `BackofficeState`
- **Campos automáticos:**
  - 9 campos de usuario (`user_id`, `organization_id`, `identity_type_id`, `user_name`, `user_email`, `user_mobile`, `is_logged_in`, `is_active`, `is_blocked`)
  - 2 tokens JWT (`access_token`, `session_token`)
  - 4 campos de metadata (`session_id`, `login_time`, `last_activity`, `current_app`)
  - **38 permisos de bajo nivel** alineados con `low_level_permissions.json`:
    - Carpetas: `can_folder_create`, `can_folder_delete`, `can_folder_rename`, `can_folder_read`, `can_folder_list`
    - Ficheros: `can_file_create`, `can_file_read`, `can_file_update`, `can_file_delete`, `can_file_list`
    - Proyectos: `can_project_create`, `can_project_read`, `can_project_update`, `can_project_delete`, `can_project_list`
    - Versiones: `can_version_create`, `can_version_read`, `can_version_update`, `can_version_delete`, `can_version_list`
    - Entrenamiento: `can_training_create`, `can_training_read`, `can_training_update`, `can_training_delete`, `can_training_start`, `can_training_stop`
    - Parámetros: `can_parameters_create`, `can_parameters_read`, `can_parameters_update`, `can_parameters_delete`
    - Notificaciones: `can_notifications_create`, `can_notifications_read`, `can_notifications_update`, `can_notifications_delete`
    - Usuarios: `can_user_create`, `can_user_read`, `can_user_update`, `can_user_delete`, `can_user_enable`, `can_user_disable`
- **Métodos obligatorios:**
  - `load_user_data()`: Cargar datos después del login (solo frontend)
  - `clear_session()`: Limpiar datos en logout
  - `go_to_backoffice()`: Navegar al backoffice con tokens en URL
  - `go_to_frontend()`: Regresar al frontend con tokens en URL
  - `logout()`: Cerrar sesión en ambas apps
- **Navegación entre apps (CRÍTICO):**
  - Ambos métodos (`go_to_backoffice`, `go_to_frontend`) pasan tokens en la URL
  - Los parámetros incluyen: `access_token`, `session_token`, `user_id`, `org_id`
  - El `on_page_load` de cada app lee estos parámetros y restaura la sesión
  - Si los tokens son válidos, se cargan los permisos desde el middleware
  - Esto es necesario porque son apps separadas con diferentes websockets
- **Métodos de validación de permisos:**
  - `has_permission("folder_rename")`: Validar permiso por nombre
  - `has_any_permission([...])`: Validar si tiene al menos uno
  - `has_all_permissions([...])`: Validar si tiene todos
  - `get_all_permissions()`: Obtener todos como diccionario
- **Propiedades computadas:**
  - `can_access_backoffice`: Verifica `is_logged_in and training_create`
  - `can_manage_folders`, `can_manage_files`, `can_manage_projects`, `can_manage_training`, `can_manage_users`
  - `user_display_name`, `user_display_email`
- **Sincronización:** Automática vía Redis (ambas apps usan `redis_db: "0"`)
- **Login:** Solo se hace en frontend; backoffice solo lee datos
- **Protección:** Todas las páginas de backoffice deben usar `backoffice_guard()`
- **Ejemplos:**
  - Frontend: `docs/examples/frontend_state_with_shared_session.py`
  - Backoffice: `docs/examples/backoffice_state_with_shared_session.py`
  - **Validación de permisos desde sesión:** `docs/examples/permission_validation_from_session.py`

### Security by Design: Validación de Permisos como Principio Fundamental

**CRÍTICO:** La tabla `low_level_permissions` es el **CORE del concepto Security by Default**.
Cada operación en cualquier capa del sistema debe validar permisos antes de ejecutarse.

#### Modelo de Datos de Permisos (OBLIGATORIO entender)

El sistema de permisos usa una relación **1 a 1** entre el rol del usuario y sus permisos:

```
┌─────────────────────────────────────────────────────────────────────────┐
│              MODELO DE DATOS: SESIÓN → PERMISOS                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   SESIÓN (JWT)             TABLA users              TABLA low_level_permissions
│   ┌──────────┐             ┌──────────────────┐     ┌────────────────────┐
│   │ user_id  │─────────────│ user_id          │     │ id_permissions     │
│   └──────────┘             │ identity_type_id │─────│ folder_create=1/0  │
│                            └──────────────────┘     │ folder_delete=1/0  │
│                                   │                 │ user_create=1/0    │
│                                   │                 │ training_start=1/0 │
│                                   ▼                 │ ... (40 campos)    │
│                          identity_type_id           └────────────────────┘
│                                 =                             │
│                          id_permissions ◄─────────────────────┘
│                            (JOIN 1:1)
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Regla de relación:**
- `users.identity_type_id` = `low_level_permissions.id_permissions`
- Cada campo de `low_level_permissions` es un permiso booleano (`1=true`, `0=false`)

#### Consulta SQL de Permisos (CRÍTICO)

**Para obtener TODOS los permisos de un usuario desde su `user_id` de sesión:**

```sql
-- Consulta completa de permisos
SELECT llp.*
FROM users u
INNER JOIN low_level_permissions llp 
    ON u.identity_type_id = llp.id_permissions
WHERE u.user_id = :user_id_from_session;
```

**Para verificar UN permiso específico:**

```sql
-- ¿El usuario puede crear usuarios?
SELECT llp.user_create
FROM users u
INNER JOIN low_level_permissions llp ON u.identity_type_id = llp.id_permissions
WHERE u.user_id = :user_id;
-- Resultado: 1 (tiene permiso) o 0 (no tiene permiso)
```

**Ejemplo con datos reales:**

```sql
-- Usuario con user_id=42, identity_type_id=2 (Admin)
SELECT u.user_id, u.identity_type_id, llp.folder_create, llp.user_create, llp.training_start
FROM users u
INNER JOIN low_level_permissions llp ON u.identity_type_id = llp.id_permissions
WHERE u.user_id = 42;

-- Resultado:
-- user_id | identity_type_id | folder_create | user_create | training_start
-- 42      | 2                | 1             | 1           | 1
```

#### Interpretación de valores de permisos

| Valor en BD | Valor Python | Significado |
|-------------|--------------|-------------|
| `1` | `True` | Usuario **TIENE** el permiso |
| `0` | `False` | Usuario **NO TIENE** el permiso |

#### Uso en código (todas las capas)

**En Frontend/Backoffice (Reflex UI):**
```python
# Los permisos están en SharedSessionState como campos booleanos
rx.cond(
    state.can_user_create,  # Viene de low_level_permissions.user_create
    rx.button("Crear usuario"),
    rx.fragment(),
)
```

**En Middleware (FastAPI):**
```python
# Obtener permisos del usuario via broker → core → BD
permissions = router._get_low_level_permissions_for_role(identity_type_id)
if not permissions.get("user_create"):
    raise HTTPException(status_code=403, detail="Sin permiso user_create")
```

**En Backend Core (validación final):**
```python
# Consulta directa a MariaDB
def validate_permission(self, user_id: int, permission_key: str) -> bool:
    query = """
        SELECT llp.{permission}
        FROM users u
        INNER JOIN low_level_permissions llp ON u.identity_type_id = llp.id_permissions
        WHERE u.user_id = %s
    """.format(permission=permission_key)
    result = self._execute_query(query, (user_id,))
    return bool(result[0][0]) if result else False
```

#### Principios de Security by Design

1. **Validación en TODAS las capas:**
   - ✅ **Frontend/Backoffice (UI):** Mostrar solo elementos para los que el usuario tiene permisos
   - ✅ **Middleware (API):** Validar permisos antes de procesar cualquier request
   - ✅ **Broker:** Verificar permisos antes de enrutar a Backend Core o Trainer
   - ✅ **Backend Core:** Validar permisos antes de operaciones en DB o fmanagement
   - ✅ **Trainer/Backend IA:** Validar permisos antes de operaciones de entrenamiento

2. **Defense in Depth:** Aunque el frontend oculte una opción, el backend DEBE rechazarla si no tiene permiso

3. **Principio de mínimo privilegio:** Los usuarios solo ven y pueden ejecutar lo que necesitan

4. **Fail-safe defaults:** Sin permiso explícito = denegación por defecto

#### Control de acceso por identity_type_id (CRÍTICO)

**REGLA OBLIGATORIA:** Además de los permisos de bajo nivel, el sistema usa `identity_type_id` 
para determinar qué operaciones de gestión puede realizar cada usuario.

##### Matriz de permisos por identity_type_id

| identity_type_id | Rol | Gestionar usuarios | Gestionar proyectos |
|------------------|-----|-------------------|-------------------|
| 1 | SuperAdmin | ✅ Sí | ✅ Sí |
| 2 | Admin de Organización | ✅ Sí | ✅ Sí |
| 3 | Editor | ❌ No | ✅ Editar |
| 4 | Lector | ❌ No | ❌ No |
| 5 | Auditor | ❌ No | ❌ No |
| 10 | Agente Admin | ✅ Sí | ✅ Sí |
| 11 | Agente Editor | ❌ No | ✅ Editar |
| 12 | Agente Lector | ❌ No | ❌ No |
| 13 | Agente Auditor | ❌ No | ❌ No |

##### Implementación en UI (Reflex)

**OBLIGATORIO:** Usar propiedades computadas `@rx.var` en el State:

```python
@rx.var
def can_manage_org_users(self) -> bool:
    """Solo SuperAdmin, Admin Org, y Agente Admin pueden gestionar usuarios."""
    if self.identity_type_id <= 0:
        return False
    return self.identity_type_id in (1, 2, 10)

# En el componente
rx.cond(
    State.can_manage_org_users,
    rx.button("Eliminar usuario", on_click=State.delete_user(user_id)),
    rx.fragment(),  # No mostrar nada
)
```

##### Implementación en API (Middleware)

**OBLIGATORIO:** Validar ANTES de ejecutar cualquier operación restringida:

```python
@app.patch("/users/{user_id}/status")
async def update_user_status_endpoint(
    user_id: int,
    session: SessionContext = Depends(get_session_context),
):
    # ⚠️ VALIDACIÓN OBLIGATORIA
    allowed_identity_types = (1, 2, 10)  # SuperAdmin, Admin Org, Agente Admin
    if session.identity_type_id not in allowed_identity_types:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Sin permisos (identity_type_id={session.identity_type_id})",
        )
    # ... ejecutar operación
```

##### Checklist para nuevas operaciones restringidas

- [ ] ¿Definido qué `identity_type_id` pueden realizar la operación?
- [ ] ¿Añadida propiedad computada `can_<operacion>` en State (frontend/backoffice)?
- [ ] ¿Usada `rx.cond()` en UI para mostrar/ocultar elementos?
- [ ] ¿Añadida validación en endpoint del middleware ANTES de ejecutar?
- [ ] ¿Retorna HTTP 403 si no tiene permisos?
- [ ] ¿Documentado en README.md (sección "Control de acceso por identity_type_id")?

#### Flujo de obtención de permisos

```
Usuario → Login → JWT (contiene identity_type_id)
                       ↓
                 Middleware consulta
                       ↓
          roles.json → identity_type_group_permissions
                       ↓
          low_level_permissions.json → permisos específicos
                       ↓
          SharedSessionState (frontend/backoffice)
                       ↓
          Validación en cada operación
```

#### Estructura de permisos (alineada con low_level_permissions.json)

Los nombres de campos en `SharedSessionState` coinciden **EXACTAMENTE** con `low_level_permissions.json`.
Esto permite validar permisos directamente desde la sesión sin transformaciones.

| Categoría | Permisos disponibles |
|-----------|---------------------|
| **Carpetas** | `folder_create`, `folder_delete`, `folder_rename`, `folder_read`, `folder_list` |
| **Ficheros** | `file_create`, `file_read`, `file_update`, `file_delete`, `file_list` |
| **Proyectos** | `project_create`, `project_read`, `project_update`, `project_delete`, `project_list` |
| **Versiones** | `version_create`, `version_read`, `version_update`, `version_delete`, `version_list` |
| **Entrenamiento** | `training_create`, `training_read`, `training_update`, `training_delete`, `training_start`, `training_stop` |
| **Parámetros** | `parameters_create`, `parameters_read`, `parameters_update`, `parameters_delete` |
| **Notificaciones** | `notifications_create`, `notifications_read`, `notifications_update`, `notifications_delete` |
| **Usuarios** | `user_create`, `user_read`, `user_update`, `user_delete`, `user_enable`, `user_disable` |

#### Validación en Frontend/Backoffice (Reflex UI)

**Regla 1:** Usar `rx.cond()` para mostrar/ocultar elementos según permisos

```python
# Menú contextual de carpeta - mostrar "Renombrar" solo si tiene permiso
rx.cond(
    state.can_folder_rename,
    rx.menu.item("Renombrar", on_click=state.rename_folder),
)
```

**Regla 2:** Usar `state.has_permission("nombre")` para validación dinámica

```python
# Validación dinámica por nombre
if state.has_permission("folder_rename"):
    mostrar_opcion_renombrar()
```

**Regla 3:** Deshabilitar (no solo ocultar) opciones sin permisos cuando sea apropiado

```python
# Botón deshabilitado en lugar de oculto
rx.button(
    "Eliminar proyecto",
    disabled=~state.can_project_delete,
    color_scheme="red" if state.can_project_delete else "gray",
)
```

#### Validación en Middleware (API REST)

**Regla 1:** OBLIGATORIO validar en backend aunque el frontend los oculte

```python
# En routermiddleware.py
def rename_folder(self, session: SessionContext, folder_id: int, new_name: str):
    # SIEMPRE validar permiso antes de ejecutar
    if not self.has_low_level_permission(session, "folder_rename"):
        raise BusinessRuleError("Sin permisos para renombrar carpetas")
    # ... ejecutar la operación
```

**Regla 2:** Retornar HTTP 403 Forbidden si no tiene permiso

```python
# En apife.py
@app.post("/folders/{folder_id}/rename")
async def rename_folder(folder_id: int, request: RenameRequest, session: SessionContext = Depends(get_session)):
    if not router.has_low_level_permission(session, "folder_rename"):
        raise HTTPException(status_code=403, detail="Permiso denegado: folder_rename")
    # ...
```

**Regla 3:** Loggear intentos de acceso sin permisos (auditoría de seguridad)

```python
self._logger.warning(
    "Intento de operación sin permiso user_id=%s org_id=%s permission=%s",
    session.user_id,
    session.organization_id,
    "folder_rename",
)
```

#### Métodos de validación disponibles en SharedSessionState

```python
# Validar un permiso específico
state.has_permission("folder_rename")  # → bool

# Validar múltiples permisos (cualquiera)
state.has_any_permission(["folder_create", "folder_rename"])  # → bool

# Validar múltiples permisos (todos)
state.has_all_permissions(["project_create", "folder_create"])  # → bool

# Obtener todos los permisos como diccionario
state.get_all_permissions()  # → {"folder_rename": True, "file_create": False, ...}

# Propiedades compuestas
state.can_manage_folders  # → True si tiene algún permiso de carpetas
state.can_manage_files    # → True si tiene algún permiso de ficheros
state.can_manage_training # → True si tiene algún permiso de entrenamiento
```

#### Checklist de Security by Design para nuevas funcionalidades

Al añadir una nueva funcionalidad:

- [ ] ¿Existe permiso en `low_level_permissions.json` para esta operación?
- [ ] ¿Está el campo `can_<permiso>` en `SharedSessionState`?
- [ ] ¿La UI usa `rx.cond(state.can_<permiso>, ...)` o `state.has_permission()`?
- [ ] ¿El endpoint del middleware valida el permiso con `has_low_level_permission()`?
- [ ] ¿Se retorna HTTP 403 si no tiene permiso?
- [ ] ¿Se loggean intentos de acceso sin permisos?
- [ ] ¿Los tests verifican tanto casos con permiso como sin permiso?

#### Documentación de referencia

- **Ejemplo completo de validación:** `docs/examples/permission_validation_from_session.py`
- **Tests de permisos:** `src/2_shared_application/tests/test_shared_session_state.py`
- **SharedSessionState:** `src/2_shared_application/reflex_shared/shared_session_state.py`
- **PermissionValidationService:** `src/2_shared_application/services/permission_validation_service.py`
- **low_level_permissions.json:** `src/2_shared_application/moks/low_level_permisions.json`
- **roles.json:** `src/2_shared_application/moks/roles.json`

### PermissionValidationService: Servicio Centralizado de Permisos

El proyecto incluye un servicio centralizado para validar permisos que puede usarse en todas las capas.

**Ubicación:** `src/2_shared_application/services/permission_validation_service.py`

#### Uso del servicio

```python
from src.2_shared_application.services.permission_validation_service import (
    PermissionValidationService,
    PermissionContext,
    get_permission_service,
)

# Obtener instancia singleton
service = get_permission_service()

# Validar un permiso específico
if service.can_perform_action(identity_type_id=2, permission_key="folder_rename"):
    permitir_renombrar_carpeta()

# Validar con contexto completo (para auditoría)
context = PermissionContext(
    user_id=1,
    organization_id=5,
    identity_type_id=2,
    project_id=10,
)
result = service.validate_permission(context, "folder_rename")
if not result.allowed:
    logger.warning(result.reason)

# Métodos de conveniencia
service.can_manage_folders(identity_type_id)    # folder_create OR folder_rename OR folder_delete
service.can_manage_files(identity_type_id)      # file_create OR file_update OR file_delete
service.can_manage_training(identity_type_id)   # training_create OR training_start OR training_stop
service.can_access_backoffice(identity_type_id) # training_create == True
```

#### Uso en Backend Core (validación obligatoria)

```python
# En src/apps/3_backend/routercore.py
from src.2_shared_application.services.permission_validation_service import PermissionValidationService

class BackendCoreRouter:
    def __init__(self, storage, fmanagement_client, permission_service=None):
        self._permission_service = permission_service or PermissionValidationService()
    
    def fmo_operation(self, payload, headers):
        """SECURITY BY DESIGN: Valida permisos antes de ejecutar."""
        identity_type_id = int(payload.get("identity_type_id", 0))
        operation = payload.get("operation", "")
        
        if identity_type_id > 0 and operation:
            self.validate_permission(identity_type_id, f"{operation}")
        
        # ... ejecutar operación
```

### Reglas de Creación de Usuarios de Organización

**REGLA CRÍTICA**: Los usuarios creados desde el panel "Gestión de Usuarios" de la página Organización
**SIEMPRE** deben tener `identity_type_id = 5` (auditor).

#### Reglas obligatorias

1. **Un administrador por organización**: Solo puede existir UN usuario con `identity_type_id = 2`
   (Administrador de Organización) por cada `organization_id`. Este rol se asigna automáticamente
   al primer usuario que crea la organización.

2. **Usuarios adicionales son auditores**: Todos los usuarios creados posteriormente desde el panel
   de organización reciben `identity_type_id = 5` (auditor) por defecto.

3. **Roles por proyecto**: Los usuarios pueden tener roles adicionales (editor, lector) asignados
   en tablas relacionadas con proyectos específicos (`manage_roles_by_project`), pero su rol base
   en la organización permanece como auditor.

4. **Principio de mínimo privilegio**: Los usuarios nuevos comienzan con permisos restringidos
   (auditor) y se les asignan permisos adicionales según necesidad en proyectos específicos.

#### Implementación en código

```python
# En api_client.py - SIEMPRE enviar identity_type_id = 5
payload = {
    "organization_id": organization_id,
    "identity_type_id": 5,  # OBLIGATORIO: Usuario auditor
    ...
}

# En routermiddleware.py - SIEMPRE respetar identity_type_id = 5
def _get_manage_roles_identity_type_id(self, organization_id, requested_identity_type_id):
    # Si se solicita explícitamente 5 (auditor), SIEMPRE se respeta
    if requested_identity_type_id == 5:
        return 5
    # Solo el primer usuario puede ser admin (2)
    ...
```

#### Validación en tests

Los tests de creación de usuarios deben verificar que:
- `identity_type_id` del usuario creado es `5`
- No se puede crear un segundo administrador en la misma organización
- El usuario tiene permisos de auditor (solo lectura)

### Jerarquía de Trabajo y Roles de Proyecto (CRÍTICO)

**IMPORTANTE:** La jerarquía de trabajo determina qué puede ver y hacer un usuario en el sistema.

#### Jerarquía de acceso

```
Organización → Proyectos → Versiones → Contenido
```

#### Reglas de visibilidad de proyectos (OBLIGATORIO)

Un usuario **SOLO puede ver** un proyecto si cumple **TODAS** las condiciones:

1. ✅ **Existe registro** en `proyectos_roles` para el usuario y proyecto
2. ✅ **`active = TRUE`** en el registro
3. ✅ **`id_rol > 0`** (NO puede ser "Sin asignar")

**Si cualquier condición falla → El usuario NO VE el proyecto.**

#### Tabla proyectos_roles_base (catálogo maestro)

| ID | Nombre | Visibilidad |
|----|--------|-------------|
| 0 | Sin asignar | ❌ No ve el proyecto |
| 3 | Editor | ✅ Puede modificar |
| 4 | Lector | ✅ Solo lectura |
| 5 | Auditor | ✅ Acceso limitado |

**Ubicación:** `myllm_projects_db.proyectos_roles_base`

#### Endpoint para consultar roles base

```
GET /project-roles-base
Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
```

#### Reglas de implementación

1. **Controladores y adaptadores:** Esta información debe ser accesible desde todas las capas
   - Backend Core: `routercore.get_project_roles_base()`
   - Broker: `routerbroker.get_project_roles_base()`
   - Middleware: `routermiddleware.get_project_roles_base()`
   - Frontend: `api_client.get_project_roles_base()`

2. **Selectores de UI:** Excluir "Sin asignar" (id=0) en selectores de asignación
   ```python
   roles_para_selector = [r["nombre_rol"] for r in roles if r["id"] > 0]
   ```

3. **Validación de acceso:** Al cargar proyectos de un usuario, filtrar por:
   ```sql
   WHERE pr.id_usuario = :user_id
     AND pr.active = TRUE
     AND pr.id_rol > 0
   ```

4. **Migración:** `infrastructure/database/migrations/005_proyectos_roles_base_table.sql`

### Roles y Permisos por Defecto

El sistema define roles con permisos predefinidos. Usa `low_level_permissions.json` como referencia única.

| identity_type_id | Rol | Permisos característicos |
|------------------|-----|--------------------------|
| 1 | SuperAdmin | Todos los permisos = `true` |
| 2 | Administrador Org | CRUD completo en proyectos, versiones, carpetas, archivos. **ÚNICO por organización** |
| 3 | Editor | Crear/editar proyectos y archivos, sin eliminar |
| 4 | Lector | Solo lectura (read, list) |
| 5 | Auditor | **ROL BASE para usuarios creados desde panel**. Solo lectura de logs y configuración |
| 10-13 | Agentes automáticos | Permisos según rol del agente (admin/editor/lector/auditor) |

#### Ejemplo: Configurar permisos de notificaciones por rol

**Caso de uso:** Chat compartido entre usuarios de cliente y personal myllm donde:
- Administradores de org, editores y personal myllm pueden **crear** notificaciones
- Lectores solo pueden **ver** notificaciones
- Auditores no ven las notificaciones (ocultas)

**Paso 1:** Verificar los campos en `low_level_permissions.json`:

```json
{
  "id_permissions": 2,  // Administrador
  "notifications_create": true,
  "notifications_read": true,
  "notifications_update": true,
  "notifications_delete": false
},
{
  "id_permissions": 3,  // Editor
  "notifications_create": true,
  "notifications_read": true,
  "notifications_update": false,
  "notifications_delete": false
},
{
  "id_permissions": 4,  // Lector
  "notifications_create": false,
  "notifications_read": true,
  "notifications_update": false,
  "notifications_delete": false
},
{
  "id_permissions": 5,  // Auditor
  "notifications_create": false,
  "notifications_read": false,  // ← OCULTAS para auditor
  "notifications_update": false,
  "notifications_delete": false
}
```

**Paso 2:** Validar en UI (Frontend/Backoffice):

```python
# Chat de notificaciones
def chat_notifications(state):
    return rx.box(
        # Solo mostrar el chat si tiene permiso de lectura
        rx.cond(
            state.can_notifications_read,
            rx.vstack(
                # Lista de notificaciones
                rx.foreach(state.notifications, notification_item),
                
                # Input de nueva notificación - solo si puede crear
                rx.cond(
                    state.can_notifications_create,
                    rx.hstack(
                        rx.input(value=state.new_message, on_change=state.set_message),
                        rx.button("Enviar", on_click=state.send_notification),
                    ),
                    rx.fragment(),  # No muestra nada si no puede crear
                ),
            ),
            rx.fragment(),  # Chat completamente oculto si no puede leer
        ),
    )
```

**Paso 3:** Validar en Middleware (API):

```python
# En routermiddleware.py
@app.post("/notifications")
async def create_notification(request: NotificationRequest, session: SessionContext):
    # SIEMPRE validar permiso en backend
    if not router.has_low_level_permission(session, "notifications_create"):
        raise HTTPException(status_code=403, detail="Sin permiso: notifications_create")
    
    # ... crear notificación

@app.get("/notifications")
async def list_notifications(session: SessionContext):
    # Validar permiso de lectura
    if not router.has_low_level_permission(session, "notifications_read"):
        raise HTTPException(status_code=403, detail="Sin permiso: notifications_read")
    
    # ... retornar notificaciones
```

**Paso 4:** Validar en Backend Core:

```python
# En routercore.py
def create_notification(self, payload, identity_type_id):
    self.validate_permission(identity_type_id, "notifications_create")
    # ... persistir notificación
```

#### Reglas para definir nuevos permisos

1. **Añadir campo en `low_level_permissions.json`** para cada `id_permissions`
2. **Añadir campo en `SharedSessionState`** con prefijo `can_`:
   ```python
   can_nuevo_permiso: bool = False
   ```
3. **Añadir a `ALL_PERMISSION_KEYS`** en `permission_validation_service.py`
4. **Actualizar `_load_permissions()` y `_reset_permissions()`** en SharedSessionState
5. **Crear tests** que validen el nuevo permiso

### Entidades de Dominio: Project y Version

El dominio incluye entidades para proyectos y versiones que soportan el flujo de trabajo completo.

**Archivos:**
- `src/1_shared_domain/entities/project.py`
- `src/1_shared_domain/entities/version.py`
- `src/2_shared_application/dtos/project_dtos.py`
- `src/2_shared_application/interfaces/project_repository.py`
- `src/2_shared_application/interfaces/version_repository.py`

#### Estados de proyecto (ProjectStatus)

| Estado | Descripción | can_create_version |
|--------|-------------|-------------------|
| `draft` | En borrador | ✅ Sí |
| `active` | Activo | ✅ Sí |
| `paused` | Pausado | ❌ No |
| `completed` | Completado | ❌ No |
| `archived` | Archivado | ❌ No |

#### Estados de versión (VersionStatus)

| Estado | Descripción | can_be_modified | can_start_training |
|--------|-------------|-----------------|-------------------|
| `draft` | En borrador | ✅ | ❌ |
| `in_review` | En revisión | ✅ | ❌ |
| `approved_client` | Aprobado por cliente | ❌ | ❌ |
| `approved_myllm` | Aprobado por myllm | ❌ | ❌ |
| `ready_for_training` | Listo para entrenar | ❌ | ✅ (si aprobado por ambos) |
| `training` | En entrenamiento | ❌ | ❌ |
| `trained` | Entrenado | ❌ | ❌ |
| `archived` | Archivado | ❌ | ❌ |

#### Uso de entidades en código

```python
from src.1_shared_domain.entities.project import Project, ProjectStatus, Projects
from src.1_shared_domain.entities.version import Version, VersionStatus, Versions

# Crear proyecto
project = Project.from_dict({
    "project_id": 1,
    "organization_id": 5,
    "project_name": "Mi Proyecto LLM",
    "created_by_user_id": 10,
    "status": "active",
})

# Verificar si se puede crear versión
if project.can_create_version():
    # Crear versión
    version = Version.from_dict({
        "version_id": 1,
        "project_id": project.project_id,
        "version_name": "V001",
        "status": "draft",
        "created_by_user_id": 10,
    })

# Verificar si se puede iniciar entrenamiento
if version.can_start_training():
    iniciar_entrenamiento(version)
```

### Adaptadores de Repositorio

**Archivos:**
- `src/2_shared_application/adapters/json_user_repository.py`
- `src/2_shared_application/adapters/json_organization_repository.py`

Estos adaptadores implementan los contratos de repositorio usando JSON como almacenamiento,
siguiendo el principio de Clean Architecture de separar el dominio de la infraestructura.

```python
from src.2_shared_application.adapters import JsonUserRepository, JsonOrganizationRepository

# Uso
user_repo = JsonUserRepository()
user = user_repo.get_by_email("admin@example.com")

org_repo = JsonOrganizationRepository()
org = org_repo.get_by_id(1)
```

### Configuración de Vite (allowedHosts)

**IMPORTANTE:** Reflex usa Vite como servidor de desarrollo. A partir de Vite 6.0.9+, los hosts 
están restringidos por seguridad (CVE-2025-30208). El dominio `tfmmyllm.ai` debe estar 
explícitamente permitido.

- **Script de parche:** `patch_vite_config.py` en cada app Reflex (frontend/backoffice)
- **Ejecución automática:** Los `run.sh` de cada app ejecutan el parche antes de `reflex run`
- **Hosts permitidos:** `tfmmyllm.ai`, `.tfmmyllm.ai` (subdominios), `localhost`
- **Archivo afectado:** `.web/vite.config.js` (auto-generado por Reflex)

**Reglas:**
1. Si se ejecuta `reflex init` y se regenera `.web/`, el parche se aplica en el siguiente `./run.sh`
2. Si añades nuevos hosts (otros dominios), actualiza `patch_vite_config.py` en ambas apps
3. Nunca editar `.web/vite.config.js` manualmente sin usar el script de parche
4. Documentar nuevos hosts en `README.md` (sección Troubleshooting, Problema 8)

### Verificación de permisos en MariaDB (OBLIGATORIO)

**CRÍTICO:** Cada vez que se diseñe una nueva consulta SQL (SELECT, INSERT, UPDATE, DELETE, CALL) 
se DEBE verificar y documentar los permisos necesarios en MariaDB.

#### Proceso obligatorio tras diseñar consultas SQL:

1. **Identificar el usuario de conexión:**
   - Operaciones de lectura (SELECT): `myllm_reader`
   - Operaciones de escritura (INSERT, UPDATE, DELETE): `myllm_writer`
   - Stored Procedures (CALL): `myllm_writer` con permiso EXECUTE

2. **Verificar permisos existentes:**
   ```sql
   SHOW GRANTS FOR 'myllm_writer'@'localhost';
   SHOW GRANTS FOR 'myllm_reader'@'localhost';
   ```

3. **Otorgar permisos faltantes:**
   ```sql
   -- Para tablas
   GRANT SELECT, INSERT, UPDATE, DELETE ON <database>.<table> TO '<user>'@'localhost';
   
   -- Para stored procedures
   GRANT EXECUTE ON PROCEDURE <database>.<procedure_name> TO '<user>'@'localhost';
   
   FLUSH PRIVILEGES;
   ```

4. **Documentar en README.md:**
   - Añadir la consulta GRANT a la sección "Configuración de permisos MariaDB"
   - Indicar qué funcionalidad requiere el permiso

5. **Verificar que el SP existe** (si se usa CALL):
   ```sql
   SHOW PROCEDURE STATUS WHERE Db = '<database>' AND Name = '<procedure_name>';
   ```
   Si no existe, crearlo y documentar en la migración correspondiente.

#### Matriz de permisos por usuario:

| Usuario | Base de datos | Permisos |
|---------|---------------|----------|
| `myllm_reader` | `myllm_core_db` | SELECT en todas las tablas |
| `myllm_reader` | `myllm_projects_db` | SELECT en todas las tablas |
| `myllm_writer` | `myllm_core_db` | SELECT, UPDATE en `users` |
| `myllm_writer` | `myllm_projects_db` | SELECT, INSERT, UPDATE, DELETE en tablas de datos |
| `myllm_writer` | `myllm_projects_db` | EXECUTE en stored procedures |

#### Checklist para nuevas funcionalidades con SQL:

- [ ] ¿Qué usuario de MariaDB ejecutará la consulta?
- [ ] ¿Tiene permisos en la tabla/procedimiento?
- [ ] ¿Se ha ejecutado el GRANT correspondiente?
- [ ] ¿Se ha documentado en README.md (sección "Configuración de permisos MariaDB")?
- [ ] ¿Se ha probado la funcionalidad después de otorgar permisos?

#### Errores comunes y soluciones:

| Error | Causa | Solución |
|-------|-------|----------|
| `INSERT command denied` | Falta permiso INSERT | `GRANT INSERT ON db.table TO 'user'@'localhost';` |
| `UPDATE command denied` | Falta permiso UPDATE | `GRANT UPDATE ON db.table TO 'user'@'localhost';` |
| `execute command denied for routine` | Falta permiso EXECUTE | `GRANT EXECUTE ON PROCEDURE db.sp_name TO 'user'@'localhost';` |
| `Unknown column 'X' in 'INSERT INTO'` | Columna no existe en tabla | Verificar estructura con `DESCRIBE table;` |
| `FUNCTION or PROCEDURE does not exist` | SP no creado | Ejecutar migración SQL que crea el SP |

## 6. Performance & Security
* **Complexity:** Avoid $O(n^2)$ operations on large datasets. Use `set` for $O(1)$ lookups.
* **Secrets:** Never hardcode API keys or credentials. Use `.env` files and `python-dotenv` or Pydantic `BaseSettings`.
* **Environment:** Prefer `pathlib` over `os.path` for filesystem operations.

# Agent Playbook & Ownership Matrix

This document assigns ownership of each major area in the repo to a virtual
agent. When working in Cursor, use `@<agent>` in your prompts to get targeted
assistance.

## Shared Domain & Application Layer

| Path / Responsibility | Agent | Purpose |
| --- | --- | --- |
| `src/1_shared_domain/` (entities, business rules) | `@domain-guru` | Define domain models, validations and ubiquitous language. |
| `src/2_shared_application/` (DTOs, interfaces, security) | `@application-architect` | Design service contracts, DTO schemas, inter-module APIs and cryptographic utilities. |
| `src/2_shared_application/security/` (cryptographic utilities) | `@security-sentinel` | Maintain encryption helpers, secret storage and key-rotation flows. |
| `src/config/` (shared configuration) | `@application-architect` | Manage shared configuration files and settings. |
| `src/tests/` (shared tests) | `@domain-guru` | Define common test utilities and fixtures. |

## Application Services

All application folders (numbered folders in `src/apps/`) follow a standard structure:
- **`logs/`**: Directory for application-specific log files (e.g., security logs, error logs).
- **`tests/`**: Directory for unit tests and integration tests specific to the application.

| Path / Responsibility | Agent | Purpose |
| --- | --- | --- |
| `src/apps/3_backend/` (API + persistence) | `@backend-conductor` | Implement application services, adapters, controllers and database integration. Contains `logs/` and `tests/` directories. |
| `src/apps/4_trainer/` (fine-tuning pipelines) | `@trainer-maestro` | Manage training jobs, GPU orchestration and experiment tracking. Contains `logs/` and `tests/` directories. |
| `src/apps/5_web_frontend/` (Reflex UI) | `@frontend-visionary` | Build Reflex components, pages and API clients for end users. Contains `logs/` (e.g., `frontend_secure.log`) and `tests/` directories. |
| `src/apps/6_web_backoffice/` (Reflex UI) | `@frontend-visionary` | Build Reflex components, pages and API clients for administrative users. Contains `logs/` and `tests/` directories. |
| `src/apps/7_service_frontend/` (service frontend) | `@frontend-visionary` | Build service-specific frontend components and interfaces. Contains `logs/` and `tests/` directories. |
| `src/apps/8_service_backend/` (service backend) | `@backend-conductor` | Implement service-specific backend logic and APIs. Contains `logs/` and `tests/` directories. |

## Infrastructure & Root

| Path / Responsibility | Agent | Purpose |
| --- | --- | --- |
| `infrastructure/` (deployment scripts) | `@ops-pilot` | Provision infrastructure, automate deployments and manage environments. |
| `main.py` (root entry point) | `@backend-conductor` | Main application entry point and orchestration. |
| `src/main.py` (src entry point) | `@backend-conductor` | Source-level entry point for services. |
| `infrastructure/environments/<entorno>/protected_values.py` (sensitive config) | `@security-sentinel` | Manage sensitive configuration values and secrets per environment. |

## Standard Directory Structure

All numbered application folders in `src/apps/` (e.g., `3_backend/`, `4_trainer/`, `5_web_frontend/`, `6_web_backoffice/`, `7_service_frontend/`, `8_service_backend/`) must include:

- **`logs/`**: Application-specific log files directory
  - Contains log files for security events, errors, and application-specific logging
  - Example: `5_web_frontend/logs/frontend_secure.log`
  - Example (middleware activity): `7_service_frontend/logs/middleware_activiy.log`
  - Includes `.gitkeep` file to ensure the directory is tracked in git (when empty)

- **`tests/`**: Application-specific test directory
  - Contains unit tests and integration tests for the application
  - Must include `__init__.py` to make it a Python package
  - Uses `pytest` as the testing framework
  - Example: `5_web_frontend/tests/test_user_creation.py`

**Note:** When creating new numbered application folders, ensure both `logs/` and `tests/` directories are created with appropriate initialization files.

## Estilos visuales diferenciados (Frontend vs Backoffice)

**CRÍTICO:** Las aplicaciones `5_web_frontend` y `6_web_backoffice` tienen estilos de renderizado
markdown **intencionalmente diferenciados** para proporcionar identidad visual única a cada aplicación.

### Regla de diferenciación visual

| Aplicación | Estilo | Tamaños de fuente | Propósito |
|------------|--------|-------------------|-----------|
| `5_web_frontend` | **Zoom aumentado** | h1:9, h2:7, h3:5, p/li:1.15em | Usuarios finales - legibilidad |
| `6_web_backoffice` | **Tamaño estándar** | h1:7, h2:5, h3:4, p/li:1em | Administradores - densidad |

### Archivos de contenido markdown

Las secciones públicas usan archivos `.md` (no `.txt`):

- `presentation.md` - Presentación de la empresa
- `services.md` - Catálogo de servicios
- `proyectos.md` - Metodología de proyectos
- `contacto.md` - Información de contacto
- `soporte.md` - Servicios de soporte

**Reglas obligatorias:**

1. ✅ **No unificar estilos**: La diferenciación es intencional y no debe igualarse
2. ✅ **Usar archivos .md**: Los contenidos públicos deben estar en formato markdown
3. ✅ **Fallback a .txt**: La función `load_menu_content()` carga `.md` primero, luego `.txt`
4. ✅ **component_map diferenciado**: Cada app mantiene su propio `component_map` en `rx.markdown()`
5. ✅ **Contenido compartido**: Ambas apps usan el mismo contenido markdown, solo difiere el estilo

### Implementación técnica

```python
# Frontend (zoom aumentado) - src/apps/5_web_frontend/web_frontend/web_frontend.py
rx.markdown(
    content_text,
    component_map={
        "h1": lambda text: rx.heading(text, size="9", ...),  # Más grande
        "h2": lambda text: rx.heading(text, size="7", ...),
        "p": lambda text: rx.text(text, font_size="1.15em", ...),  # +15%
    },
)

# Backoffice (tamaño estándar) - src/apps/6_web_backoffice/web_backoffice/web_backoffice.py
rx.markdown(
    content_text,
    component_map={
        "h1": lambda text: rx.heading(text, size="7", ...),  # Estándar
        "h2": lambda text: rx.heading(text, size="5", ...),
        "p": lambda text: rx.text(text, font_size="1em", ...),  # Normal
    },
)
```

### Archivos de configuración

- Frontend: `src/apps/5_web_frontend/web_frontend/web_frontend.py` (función `info_panel()`)
- Backoffice: `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py` (función `info_panel()`)

## Estilos de botones en Reflex (OBLIGATORIO)

**Regla fundamental:** Todos los botones en aplicaciones Reflex deben seguir un estilo consistente
para mantener la coherencia visual en toda la aplicación.

### Estilo estándar de botones

| Propiedad | Valor | Propósito |
|-----------|-------|-----------|
| `color` | `"black"` | Fuente siempre en negro para legibilidad |
| `font_weight` | `"bold"` | Texto en negrita para destacar acciones |
| `size` | `"3"` | Tamaño medio estándar (salvo excepciones) |
| `color_scheme` | Según app | `"green"` (frontend) / `"orange"` (backoffice) |

### Implementación obligatoria

```python
# ✅ CORRECTO - Botón con estilo estándar
rx.button(
    "Crear nueva versión",
    on_click=State.create_new_version,
    color_scheme="green",  # o "orange" en backoffice
    size="3",
    style={"font_weight": "bold", "color": "black"},
)

# ✅ CORRECTO - Botón con icono
rx.button(
    rx.icon("plus", size=18),
    "Crear nueva versión",
    on_click=State.create_new_version,
    color_scheme="green",
    size="3",
    style={"font_weight": "bold", "color": "black"},
)

# ❌ INCORRECTO - Sin estilo de fuente
rx.button(
    "Crear nueva versión",
    on_click=State.create_new_version,
    color_scheme="green",
    # Falta: style={"font_weight": "bold", "color": "black"}
)

# ❌ INCORRECTO - Color de fuente inconsistente
rx.button(
    "Crear nueva versión",
    on_click=State.create_new_version,
    color_scheme="green",
    style={"font_weight": "bold", "color": "white"},  # Debe ser "black"
)
```

### Excepciones permitidas

| Caso | Excepción | Ejemplo |
|------|-----------|---------|
| Botones de acción crítica | `color_scheme="red"` | Eliminar, Cancelar |
| Botones secundarios | `variant="soft"` o `variant="outline"` | Opciones menos prioritarias |
| Botones deshabilitados | `disabled=True` | Mantener estilo base |

### Color scheme por aplicación

| Aplicación | Color Principal | Botones de Acción | Botones Secundarios |
|------------|----------------|-------------------|---------------------|
| Frontend (8005) | `"green"` | `color_scheme="green"` | `color_scheme="gray"` |
| Backoffice (8006) | `"orange"` | `color_scheme="orange"` | `color_scheme="gray"` |

**Nota:** El `color_scheme` define el color de fondo del botón. El texto siempre debe ser negro (`color: "black"`).

## Regla de puertos (estándar)

Cada aplicación usa **puerto fijo 8000 + el primer número del nombre de su carpeta**:

- `3_backend` → **8003** (Backend Core - datos, usuarios, permisos, fmanagement)
- `4_trainer` → **8004** (Backend IA - entrenamiento, modelos, métricas)
- `5_web_frontend` → **8005**
- `6_web_backoffice` → **8006** (reservado)
- `7_service_frontend` → **8007**
- `8_service_backend` → **8008** (Broker - enruta entre Backend Core y Backend IA)

La intención es identificar servicios por puerto en el host, manteniendo una asignación estable.

## Diagrama de arquitectura (Mermaid)

El esquema de arquitectura del sistema se encuentra en `context/schemas/mermaid-ai-diagram-myllm.mmd`.
Incluye roles de usuario, servidores frontend/backend/trainer, el flujo entre `5_web_frontend`,
`6_web_backoffice`, `7_service_frontend`, `8_service_backend`, `3_backend`, y los componentes compartidos.

### Reglas de integración entre servicios

- **Entradas web**: `5_web_frontend` y `6_web_backoffice` consumen el middleware `7_service_frontend`.
- **Broker backend**: `7_service_frontend` delega en `8_service_backend` para enrutar operaciones.
  El broker reparte peticiones entre el backend core (datos) y el backend IA (entrenamiento/uso interno).
- **Destino por tipo de operación**:
  - Datos (MariaDB/MySQL y sistema de ficheros) → `3_backend` en servidor backend.
  - IA (uso interno y entrenamiento) → `4_trainer` en servidor trainer (API REST + BD vectorial Keras).
- **Capas compartidas**:
  - Dominio común → `src/1_shared_domain/`.
  - Aplicación común → `src/2_shared_application/`.

### Flujo obligatorio de peticiones (CRÍTICO)

**REGLA FUNDAMENTAL:** El middleware NUNCA debe acceder directamente a MariaDB. Todas las 
operaciones de datos deben pasar por el broker y el backend core.

#### Flujo correcto para operaciones de datos

```
Frontend/Backoffice → Middleware → Broker → Backend Core → MariaDB
     (8005/8006)        (8007)     (8008)      (8003)       (3306)
```

#### Flujo correcto para operaciones de IA

```
Frontend/Backoffice → Middleware → Broker → Trainer
     (8005/8006)        (8007)     (8008)    (8004)
```

#### Reglas de implementación

1. **Frontend/Backoffice (`api_client.py`):**
   - Solo pueden llamar al middleware (puerto 8007)
   - Usar funciones dedicadas para cada operación
   - Propagar tokens de autenticación en headers

2. **Middleware (`routermiddleware.py`):**
   - Usar `_broker_client` para enviar operaciones al broker
   - PROHIBIDO importar SQLAlchemy o acceder directamente a MariaDB
   - Solo modo `mock` (JSON) puede saltarse el broker

3. **Broker (`routerbroker.py`):**
   - Decidir si enviar al backend core o al trainer
   - Usar `_core_client` para operaciones de datos
   - Usar `_trainer_client` para operaciones de IA

4. **Backend Core (`routercore.py`):**
   - Única capa autorizada para acceder a MariaDB
   - Usar SQLAlchemy para operaciones de base de datos
   - Mantener sincronización con JSON si `storage_mode` lo requiere

#### Checklist para nuevas operaciones

Al implementar una nueva operación (ej: actualizar usuario, crear proyecto):

- [ ] **api_client.py** (frontend/backoffice): Nueva función que llama al middleware
- [ ] **apife.py** (middleware): Nuevo endpoint que recibe la petición
- [ ] **routermiddleware.py**: Nuevo método que llama al broker client
- [ ] **broker_backend_client.py**: Nuevo método que hace la petición HTTP al broker
- [ ] **apibe.py** (broker): Nuevo endpoint que recibe del middleware
- [ ] **routerbroker.py**: Nuevo método que llama al core client (o trainer client)
- [ ] **interfacetocore.py**: Nuevo método que hace la petición HTTP al backend core
- [ ] **apicore.py** (backend core): Nuevo endpoint que recibe del broker
- [ ] **routercore.py**: Nuevo método que ejecuta la operación en MariaDB

#### Ejemplo de implementación: Actualizar estado de usuario

```python
# 1. Frontend: adapters/api_client.py
def update_user_status(user_id, active, access_token, session_token):
    return _request_middleware("PATCH", f"/users/{user_id}/status", ...)

# 2. Middleware: apife.py
@app.patch("/users/{user_id}/status")
async def update_user_status_endpoint(user_id, request, router, session):
    return router.update_user_active_status(user_id, request.active, session.organization_id)

# 3. Middleware: routermiddleware.py
def update_user_active_status(self, user_id, active, requester_org_id):
    return self._broker_client.update_user_status(user_id, active, requester_org_id)

# 4. Broker Client: broker_backend_client.py
def update_user_status(self, user_id, active, requester_org_id):
    return self._request("PATCH", f"/users/{user_id}/status", payload={...})

# 5. Broker: apibe.py
@app.patch("/users/{user_id}/status")
def update_user_status(user_id, payload, router):
    return router.update_user_status(user_id, payload.active, payload.requester_org_id)

# 6. Broker: routerbroker.py
def update_user_status(self, user_id, active, requester_org_id):
    return self._core_client.update_user_status(user_id, active, requester_org_id)

# 7. Core Interface: interfacetocore.py
def update_user_status(self, user_id, active, requester_org_id):
    return self._request("PATCH", f"/users/{user_id}/status", payload={...})

# 8. Backend Core: apicore.py
@app.patch("/users/{user_id}/status")
def update_user_status(user_id, payload, router):
    return router.update_user_status(user_id, payload.active, payload.requester_org_id)

# 9. Backend Core: routercore.py
def update_user_status(self, user_id, active, requester_org_id):
    # Aquí SÍ se usa SQLAlchemy para actualizar MariaDB
    engine = create_engine(dsn)
    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET active = :active WHERE user_id = :user_id"), {...})
```

### Trazabilidad X-Client-App (regla obligatoria)

**Propósito:** Identificar el origen de cada petición a través de toda la cadena de servicios para
auditoría, debugging y correlación de logs.

**Header:** `X-Client-App`

**Flujo de propagación:**
```
Frontend/Backoffice → Middleware → Broker → Backend Core → fmanagement
     [frontend]        [propaga]    [propaga]  [propaga]    [recibe]

Frontend/Backoffice → Middleware → Broker → Backend IA → fmanagement
     [frontend]        [propaga]    [propaga]  [propaga]   [recibe]
```

**Valores estándar por servicio:**
| Servicio | Valor X-Client-App | Archivo de implementación |
|----------|-------------------|---------------------------|
| `5_web_frontend` | `frontend` | `adapters/api_client.py` |
| `6_web_backoffice` | `backoffice` | `adapters/api_client.py` |
| `7_service_frontend` | `middleware` (origen) | `broker_backend_client.py` |
| `8_service_backend` | propaga origen | `interfacetocore.py`, `interfacetotrainer.py` |
| `3_backend` | propaga origen | `apicore.py` |
| `4_trainer` | propaga origen | `apitrainer.py` |

**Reglas de implementación:**

1. **Clientes HTTP** (Frontend/Backoffice):
   ```python
   request_headers = {
       "Content-Type": "application/json",
       "X-Client-App": "frontend",  # o "backoffice"
   }
   ```

2. **APIs FastAPI** (extracción del header):
   ```python
   def get_client_app(
       client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
   ) -> str:
       return client_app or "unknown"
   ```

3. **Middleware** (inyección y propagación en `apife.py`):
   ```python
   def get_router_middleware(
       interface: Annotated[InterfaceToBackend, Depends(get_interface_client)],
       broker_client: Annotated[BrokerBackendClient, Depends(get_broker_client)],
       client_app: Annotated[str, Depends(get_client_app)],
   ) -> RouterMiddleware:
       broker_client.set_client_app(client_app)  # Configura el header para propagación
       return RouterMiddleware(interface=interface, jwt_settings=get_jwt_settings(), broker_client=broker_client)
   ```

4. **Clientes intermedios** (propagación):
   ```python
   headers = {"X-Client-App": client_app}
   response = self._client.request(method, url, headers=headers, ...)
   ```

5. **Logging** (incluir origen en logs):
   ```python
   self._logger.info("[%s] Consulta permisos role_id=%s", self._client_app, identity_type_id)
   ```

**Formato de logs esperado:**
```
2026-01-27 10:30:45 | INFO | [frontend] | user_id=1 | action=login
2026-01-27 10:30:46 | INFO | [backoffice] | user_id=2 | action=create_training
```

## ADRs

- `src/docs/stack_of_technologies.adr`: decisión de bajar a Python 3.13 por compatibilidad de dependencias.

### Guía para ubicación de cambios

- Si el cambio afecta a reglas de negocio o entidades compartidas, debe estar en `src/1_shared_domain/`.
- Si el cambio afecta a contratos, DTOs o utilidades compartidas, debe estar en `src/2_shared_application/`.
- Si el cambio afecta a flujos web o UX, debe estar en `src/apps/5_web_frontend/` o `src/apps/6_web_backoffice/`.
- Si el cambio afecta a la orquestación entre servicios web y backend, debe estar en `src/apps/7_service_frontend/`.
- Si el cambio afecta a persistencia, API core o acceso a MariaDB/sistema de ficheros, debe estar en `src/apps/3_backend/`.
- Si el cambio afecta a entrenamiento/IA, debe estar en `src/apps/4_trainer/`.

### Impacto en tests

- Cambios en `7_service_frontend` deben considerar tests de integración con `5_web_frontend` y `6_web_backoffice`.
- Cambios en `8_service_backend` deben considerar integración con `3_backend` y `4_trainer`.
- Cambios en `1_shared_domain` o `2_shared_application` pueden impactar en todas las apps y requieren tests de contrato.
- El middleware gestiona sesiones temporales en `src/2_shared_application/moks/sessions.json` (`sessions`, `auth_logs`).
  Los JWT incluyen `jti` y `session_id`, y se valida estado (`active`, `inactive`, `revoked`, `expired`).
  Tres intentos fallidos consecutivos en 10 minutos bloquean el usuario (`blocked=true` en `users.json`), por lo que
  se deben añadir tests de login, logout y validación de sesión cuando se amplíe la cobertura.

Las entidades compartidas de sesión viven en `src/1_shared_domain/entities/session.py` y sus DTOs en
`src/2_shared_application/dtos/session_dtos.py`, para reutilizar la validación de permisos entre apps.

### Directiva Security by Design

- Los tokens JWT solo son válidos si están vinculados a una sesión **activa** en `sessions.json`
  con `session_id` y `jti` coincidentes; cualquier logout invalida la sesión y hace que esos tokens
  dejen de ser aceptados, mitigando el uso indebido por filtración o replay.

### Directiva Security by Default

- Tras logout los tokens emitidos quedan inválidos y solo se generan nuevos tokens cuando el usuario
  vuelve a autenticarse con credenciales y OTP válidos.

### Logging de actividad (broker y core)

- `8_service_backend` registra actividad en `src/apps/8_service_backend/logs/broker_backend_activity.log`.
- `3_backend` registra actividad en `src/apps/3_backend/logs/backend_core_activity.log`.

### Sistema de logging unificado (console.log)

**OBLIGATORIO:** Todas las aplicaciones deben escribir logs a un archivo `console.log` en su 
directorio `logs/` para facilitar la trazabilidad y diagnóstico de incidencias.

**Archivos console.log:**
- `src/apps/3_backend/logs/console.log` (Backend Core)
- `src/apps/4_trainer/logs/console.log` (Trainer/Backend IA)
- `src/apps/5_web_frontend/logs/console.log` (Frontend)
- `src/apps/6_web_backoffice/logs/console.log` (Backoffice)
- `src/apps/7_service_frontend/logs/console.log` (Middleware)
- `src/apps/8_service_backend/logs/console.log` (Broker)

**Formato estándar:**
```
YYYY-MM-DD HH:MM:SS | LEVEL    | APP_NAME        | MENSAJE
```

**Módulo compartido:** `src/2_shared_application/console_logger.py`

**Uso obligatorio:**
```python
from src.2_shared_application.console_logger import create_console_logger

# En main.py de cada aplicación
logger = create_console_logger("app_name", logs_dir)
logger.startup(host=host, port=port)
```

**Características:**
- Rotación automática: 10MB máx, 5 backups
- Formato legible para técnicos de soporte
- Escritura simultánea a consola y archivo

**Reglas para nuevas funcionalidades:**
1. Todo startup de aplicación debe loguear `APPLICATION STARTUP`
2. Toda operación de negocio relevante debe loguearse
3. Todo error debe incluir contexto suficiente para diagnóstico
4. Los logs deben ser útiles para técnicos de soporte, no solo desarrolladores

## Interfaces compartidas (aplicación)

Los contratos en `src/2_shared_application/interfaces/` definen acceso a entidades
de dominio sin acoplarse a la infraestructura. Úsalos en adaptadores y
controladores para soportar JSON hoy y MariaDB mañana.

- `basic_permissions_repository.py`: `BasicPermissionsRepository`
- `manage_roles_by_org_repository.py`: `ManageRolesByOrgRepository`
- `roles_repository.py`: `RolesRepository`
- `user_repository.py`: `UserRepository`
- `organization_repository.py`: `OrganizationRepository`
- `identity_global_repository.py`: `IdentityGlobalRepository`
- `permissions_repository.py`: `PermissionsRepository`
- `tenant_repository.py`: `TenantRepository`
- `dataset_repository.py`: `DatasetRepository`
- `model_version_repository.py`: `ModelVersionRepository`
- `session_repository.py`: `SessionRepository`

### Ejemplos de implementación en adaptadores

Ejemplos simplificados (sin datos reales) para implementar repositorios desde
JSON o desde MariaDB usando DTOs. Los adaptadores viven en infraestructura y
transforman datos externos a entidades de dominio.

```python
from __future__ import annotations

import json
from pathlib import Path

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

## Coding Standards & Language Rules

### Language Usage Guidelines

All agents must follow these language conventions:

| Element Type | Language | Examples |
| --- | --- | --- |
| **Class names** | English | `User`, `Organization`, `IdentityGlobal` |
| **Function names** | English | `get_organization_by_name()`, `create_user()`, `validate_email()` |
| **Variable names** | English | `user_id`, `organization_name`, `is_active` |
| **Code comments** | Spanish | `# Verifica si el usuario está activo`, `# Crea una nueva organización` |
| **User-facing text** | Spanish | Labels, buttons, messages, component names visible in web interface |
| **Error messages** | Spanish | Messages shown to end users in the application |
| **Documentation strings** | Spanish | Docstrings explaining functionality to developers |

**Rationale:**
- Code identifiers in English ensure consistency with standard Python conventions and international collaboration.
- User-facing content in Spanish serves the target audience and improves user experience.
- Comments and documentation in Spanish facilitate understanding for the development team.

**Examples:**

```python
# ✅ Correct
class User:
    def activate_user(self) -> bool:
        """Activa el usuario en el sistema"""
        self.is_active = True
        return True

# ❌ Incorrect
class Usuario:  # Should be User
    def activar_usuario(self) -> bool:  # Should be activate_user
        """Activate user in system"""  # Should be in Spanish
```

```python
# ✅ Correct - User interface text
button_label = "Crear Usuario"
error_message = "El email ingresado no es válido"
success_message = "Usuario creado exitosamente"

# ✅ Correct - Code identifiers
def create_user(user_data: dict) -> User:
    """Crea un nuevo usuario en el sistema"""
    # Validación del email
    if not validate_email(user_data["email"]):
        raise ValueError("El email no es válido")
    return User(**user_data)
```

Use this matrix as the single source of truth when routing tasks in Cursor.


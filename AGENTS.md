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
│   └── ORG00001/PRJ00001/v001/
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
- ✅ Estructura: `ORG#####/PRJ#####/v###/` (flexible dentro de cada versión)
- ✅ Los usuarios pueden crear cualquier estructura de carpetas dentro de cada versión
- ✅ Se sincroniza desde backend a trainer cuando se ejecuta `transferversion`
- ✅ Corresponde a la variable `backend_core_base_storage` y `backend_ia_base_storage`

**Reglas de internal:**
- ✅ Estructura fija: `models/` y `reports/` con jerarquía `ORG#####/PRJ#####/v###/`
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

### Servidor Trainer - Servicios y dependencias de IA

El servidor trainer alberga los servicios de IA con la siguiente arquitectura:

| Servicio | Puerto | Función | Estado |
|----------|--------|---------|--------|
| `4_trainer` | 8004 | API FastAPI que recibe peticiones del Broker | Operativo |
| Ollama | 11434 | Servidor de modelos LLM locales (llama3, mistral, etc.) | Operativo |
| ChromaDB | 8100 | Base de datos vectorial para embeddings (RAG) | Operativo |

**Dependencias de IA en `.venv_trainer312` (Python 3.12):**

| Paquete | Versión | Uso | Notas |
|---------|---------|-----|-------|
| TensorFlow | 2.16.2 | Framework de deep learning | Requiere protobuf <5.0 |
| Keras | 3.13.2 | API de alto nivel para redes neuronales | Independiente de TF desde v3 |
| ChromaDB | 1.5.0 | BD vectorial con servidor HTTP autónomo | CLI nativo Rust (`chroma run`) |
| Ollama | 0.4.7 | Cliente Python para modelos LLM locales | `OllamaAdapter` encapsula |

**Flujo de comunicación:**
```
Broker (8008) → 4_trainer (8004) → Ollama (11434) → Inferencia LLM
                     ↓
              ChromaDB (8100) → Búsqueda semántica (embeddings)
```

**Regla de diseño:** `4_trainer` se comunica **directamente** con Ollama y ChromaDB
(sin intermediarios como N8N) para minimizar latencia y complejidad.

### ChromaDB - Base de datos vectorial (OBLIGATORIO)

**Arquitectura del servidor:**
```
Trainer (FastAPI:8004) ──arranca──► ChromaDB Server (HTTP:8100)
Trainer (HttpClient)   ──opera───► ChromaDB Server
```

**Ciclo de vida:**
1. El trainer arranca ChromaDB como subproceso en su `lifespan` (startup)
2. ChromaDB funciona como servidor HTTP autónomo en puerto 8100
3. El trainer opera sobre ChromaDB vía `chromadb.HttpClient`
4. Al detenerse el trainer, ChromaDB se detiene automáticamente (shutdown)

**Módulo gestor:** `src/apps/4_trainer/chroma_server.py`

**Funciones principales:**

| Función | Descripción |
|---------|-------------|
| `start_chroma_server()` | Arranca el servidor como subproceso, espera heartbeat |
| `stop_chroma_server()` | Detiene el servidor enviando SIGTERM |
| `get_chroma_client()` | Singleton de `chromadb.HttpClient` para operaciones |
| `get_or_create_collection()` | Obtiene o crea una colección vectorial |
| `is_server_running()` | Verifica si el servidor responde al heartbeat |
| `get_server_info()` | Información completa del estado del servidor |
| `get_chroma_settings()` | Lee configuración desde env.yaml + protected_values.py |

**Variables de configuración por entorno:**

| Variable | Fichero | macbook | dev/pre/pro |
|----------|---------|---------|-------------|
| `chroma_host` | env.yaml | localhost | trainer.*.loc/aws |
| `chroma_port` | env.yaml | 8100 | 8100 |
| `chroma_persist_directory` | env.yaml | ~/data/.../persistence/chroma | /data/persistence/chroma |
| `chroma_collection_name` | env.yaml | myllm_embeddings | myllm_embeddings |
| `chroma_anonymized_telemetry` | env.yaml | false | false |
| `chroma_log_level` | env.yaml | INFO | WARNING/ERROR |
| `chroma_auth_token` | protected_values.py | token-dev | CAMBIAR EN PRODUCCIÓN |
| `chroma_auth_provider` | protected_values.py | TokenAuth... | TokenAuth... |

**Endpoints del trainer para ChromaDB:**

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/trainer/chroma/health` | GET | Estado del servidor ChromaDB |

**Reglas obligatorias de ChromaDB:**

1. ✅ **NUNCA** acceder a ChromaDB directamente desde otras aplicaciones; siempre a través del trainer
2. ✅ **SIEMPRE** usar `chroma_server.get_chroma_client()` para obtener el cliente HTTP
3. ✅ **SIEMPRE** usar `chroma_server.get_or_create_collection()` para operar con colecciones
4. ✅ **NUNCA** cambiar el puerto 8100 sin actualizar todos los entornos
5. ✅ **SIEMPRE** configurar `chroma_auth_token` en producción (protected_values.py)
6. ✅ El directorio de persistencia debe existir antes del arranque (se crea automáticamente)
7. ✅ ChromaDB 1.5.0 usa API v2 (`/api/v2/heartbeat`); la v1 está deprecada
8. ✅ El CLI nativo es `chroma run` (binario Rust), NO `python -m chromadb.cli.cli`

**Nota sobre conflicto de protobuf:**
TensorFlow 2.16.2 requiere `protobuf <5.0.0` y ChromaDB (vía opentelemetry-proto) prefiere
`protobuf >=5.0`. Se usa `protobuf==4.25.8` como compromiso estable. Ambas librerías funcionan
correctamente con esta versión. **NO actualizar protobuf sin verificar compatibilidad con ambas.**

**Logging de ChromaDB:**
- Prefijo de log: `[CHROMADB]`
- Log del servidor: `src/apps/4_trainer/logs/chroma_server.log`
- Log integrado en: `src/apps/4_trainer/logs/console.log`

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

**Dependencias de IA instaladas en `.venv_trainer312`:**
- `tensorflow==2.16.2` (deep learning)
- `keras==3.13.2` (API de alto nivel para redes neuronales)
- `chromadb==1.5.0` (base de datos vectorial con servidor HTTP)
- `ollama==0.4.7` (cliente para modelos LLM locales)
- `protobuf==4.25.8` (versión de compromiso TF + ChromaDB)

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
| trainer | trainer_api, ollama, chromadb (puerto 8100) | Sí |
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

### Sistema de Asignaciones Jerárquicas (CRÍTICO)

**REGLA FUNDAMENTAL:** El sistema implementa asignaciones de usuarios internos a dos niveles: organización y proyecto. La asignación a organización es **PREREQUISITO OBLIGATORIO** para cualquier asignación a proyectos.

#### Estructura jerárquica (OBLIGATORIO)

```
Nivel 1: ORGANIZACIÓN (prerequisito)
    ├─ Tabla: asignaciones_organizaciones_internas
    ├─ Campos: id_usuario, id_organizacion, id_rol, active
    └─ DEBE EXISTIR para poder asignar a proyectos
        ↓
Nivel 2: PROYECTOS (opcional, depende de Nivel 1)
    ├─ Tabla: proyectos_roles
    ├─ Campos: id_usuario, id_organizacion, id_proyecto, id_rol, active
    └─ SOLO si usuario tiene rol activo en organización
```

#### Reglas de validación (OBLIGATORIO implementar)

1. **Prerequisito de organización:**
   ```python
   # ANTES de asignar a proyecto, validar:
   SELECT COUNT(*) FROM asignaciones_organizaciones_internas
   WHERE id_usuario = :user_id
     AND id_organizacion = :org_id
     AND active = TRUE
   # Si COUNT = 0 → RECHAZAR asignación a proyecto
   ```

2. **Usuarios internos únicamente:**
   ```sql
   -- Solo usuarios con permiso training_create pueden ser asignados
   SELECT u.user_id, u.user_name
   FROM users u
   INNER JOIN low_level_permissions llp ON u.identity_type_id = llp.id_permissions
   WHERE llp.training_create = TRUE
   ```

3. **No duplicados:**
   ```sql
   -- Para organizaciones:
   UNIQUE KEY (id_usuario, id_organizacion, id_rol)

   -- Para proyectos:
   UNIQUE KEY (id_usuario, id_organizacion, id_proyecto, id_rol)
   ```

4. **Conversión de IDs a nombres en UI:**
   ```python
   # OBLIGATORIO: Los visores DEBEN mostrar nombres, NO IDs
   # Hacer JOIN con:
   # - users (user_name)
   # - organizations (organization_name)
   # - proyectos (project_name)
   # - roles_base (role_name)
   ```

#### Operaciones CRUD (endpoints obligatorios)

**Nivel Organización:**
```
GET    /internal-users              # Usuarios con training_create=true
GET    /organizations/roles         # Catálogo de roles de organización
GET    /organizations/{org_id}/assignments  # Ver asignaciones actuales
POST   /organizations/assignments   # Asignar: INSERT con active=true
PATCH  /organizations/assignments/{id}  # Habilitar/deshabilitar: UPDATE active
DELETE /organizations/assignments/{id}  # Desasignar: DELETE físico
```

**Nivel Proyecto:**
```
GET    /projects/roles              # Catálogo de roles (proyectos_roles_base)
GET    /organizations/{org_id}/projects  # Proyectos de una organización
GET    /projects/{proj_id}/assignments   # Ver asignaciones actuales
POST   /projects/assignments        # Asignar: INSERT con active=true
PATCH  /projects/assignments/{id}   # Habilitar/deshabilitar: UPDATE active
DELETE /projects/assignments/{id}   # Desasignar: DELETE físico
```

#### Flujo arquitectónico (OBLIGATORIO seguir)

```
Backoffice (SuperAdmin ONLY)
    ↓ Authorization + X-Session-Token
Middleware (apife.py, routermiddleware.py)
    ↓ Validar identity_type_id == 1
Broker (routerbroker.py)
    ↓ Routing
Backend Core (routercore.py, assignments_service.py)
    ↓ Validaciones + Business Logic
MariaDB (myllm_projects_db)
    - asignaciones_organizaciones_internas
    - proyectos_roles
```

#### Estructura de UI (tabs obligatorios)

**Tab 1: Roles por Organización**
- Selectores:
  - Usuario (filtrado: `training_create=true`)
  - Organización
  - Rol de Organización
- Botones:
  - **Asignar**: `POST /organizations/assignments`
  - **Desasignar**: `DELETE /organizations/assignments/{id}`
  - **Habilitar**: `PATCH .../{id}` con `{active: true}`
  - **Deshabilitar**: `PATCH .../{id}` con `{active: false}`
- Visor: Tabla mostrando asignaciones con nombres legibles

**Tab 2: Roles por Proyecto**
- **PREREQUISITO UI**: Deshabilitar tab si usuario no tiene rol en org
- Selectores:
  - Usuario (filtrado: `training_create=true`)
  - Organización
  - Proyecto (solo de org seleccionada)
  - Rol de Proyecto
- Botones: Igual estructura que Tab 1
- Visor: Tabla mostrando asignaciones con nombres legibles

#### DTOs requeridos (crear en 2_shared_application/dtos/)

```python
# assignments_dtos.py

class InternalUserDto(BaseModel):
    user_id: int
    user_name: str
    user_email: str

class OrganizationAssignmentDto(BaseModel):
    id: int
    user_id: int
    user_name: str
    organization_id: int
    organization_name: str
    role_id: int
    role_name: str
    active: bool

class ProjectAssignmentDto(BaseModel):
    id: int
    user_id: int
    user_name: str
    organization_id: int
    organization_name: str
    project_id: int
    project_name: str
    role_id: int
    role_name: str
    active: bool

class CreateOrgAssignmentDto(BaseModel):
    user_id: int
    organization_id: int
    role_id: int

class CreateProjectAssignmentDto(BaseModel):
    user_id: int
    organization_id: int
    project_id: int
    role_id: int
```

#### Validación de permisos (Security by Design)

```python
# OBLIGATORIO en TODOS los endpoints de asignaciones:

@app.post("/organizations/assignments")
async def create_org_assignment(
    request: CreateOrgAssignmentDto,
    session: SessionContext = Depends(get_session_context),
):
    # VALIDACIÓN CRÍTICA: Solo SuperAdmin
    if session.identity_type_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo SuperAdmin puede gestionar asignaciones",
        )
    # ... resto de lógica
```

#### Archivos a implementar (checklist)

**Backend Core:**
- [ ] `src/apps/3_backend/3_adapters/controllers/assignments_controller.py`
- [ ] `src/apps/3_backend/2_application/services/assignments_service.py`
- [ ] `src/apps/3_backend/4_infrastructure/persistence/assignments_repository.py`
- [ ] `src/apps/3_backend/apibe.py` - Registrar endpoints

**Broker:**
- [ ] `src/apps/8_service_backend/routerbroker.py` - Routing de asignaciones
- [ ] `src/apps/8_service_backend/interfacetocore.py` - Cliente HTTP a core

**Middleware:**
- [ ] `src/apps/7_service_frontend/apife.py` - Endpoints
- [ ] `src/apps/7_service_frontend/routermiddleware.py` - Lógica de middleware
- [ ] `src/apps/7_service_frontend/interfacetobackend.py` - Cliente HTTP a broker

**Backoffice:**
- [ ] `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py` - UI con tabs
- [ ] `src/apps/6_web_backoffice/adapters/api_client.py` - Cliente HTTP

**Shared:**
- [ ] `src/2_shared_application/dtos/assignments_dtos.py` - DTOs compartidos

#### Casos de uso obligatorios

**Caso 1: Asignar usuario a organización**
1. SuperAdmin selecciona usuario interno
2. Selecciona organización
3. Selecciona rol
4. Sistema valida: no duplicado
5. Sistema crea registro con `active=true`

**Caso 2: Asignar usuario a proyecto (con validación)**
1. SuperAdmin selecciona usuario
2. Selecciona organización
3. **Sistema valida**: ¿usuario tiene rol activo en org?
4. Si NO → Mostrar error y BLOQUEAR asignación
5. Si SÍ → Permitir seleccionar proyecto y rol
6. Sistema crea registro con `active=true`

**Caso 3: Deshabilitar acceso temporal (borrado lógico)**
1. SuperAdmin clic en "Deshabilitar"
2. Sistema actualiza `active=false`
3. Usuario pierde acceso PERO registro se mantiene
4. Se puede reactivar con "Habilitar"

**Caso 4: Eliminar asignación permanente (borrado físico)**
1. SuperAdmin clic en "Desasignar"
2. Sistema elimina registro (DELETE)
3. NO se puede recuperar, debe crearse de nuevo

#### Reglas de seguridad (CRÍTICO)

1. **Solo SuperAdmin**: `identity_type_id == 1` puede acceder al módulo
2. **Auditoría**: Registrar en logs TODAS las operaciones de asignaciones
3. **Validación doble**:
   - UI: Deshabilitar controles según prerequisitos
   - API: Validar prerequisitos en backend
4. **Transacciones**: Usar transacciones SQL para mantener consistencia

#### Consultas SQL de ejemplo

**Obtener usuarios internos:**
```sql
SELECT u.user_id, u.user_name, u.user_email
FROM myllm_core_db.users u
INNER JOIN myllm_core_db.low_level_permissions llp
    ON u.identity_type_id = llp.id_permissions
WHERE llp.training_create = TRUE
ORDER BY u.user_name;
```

**Validar prerequisito de organización:**
```sql
SELECT COUNT(*) as has_org_role
FROM asignaciones_organizaciones_internas
WHERE id_usuario = :user_id
  AND id_organizacion = :org_id
  AND active = TRUE;
```

**Obtener asignaciones de organización (con nombres):**
```sql
SELECT
    aoi.id,
    aoi.id_usuario,
    u.user_name,
    aoi.id_organizacion,
    o.organization_name,
    aoi.id_rol,
    r.nombre_rol as role_name,
    aoi.active
FROM asignaciones_organizaciones_internas aoi
INNER JOIN myllm_core_db.users u ON aoi.id_usuario = u.user_id
INNER JOIN myllm_core_db.organizations o ON aoi.id_organizacion = o.organization_id
INNER JOIN roles_organizacion_base r ON aoi.id_rol = r.id
WHERE aoi.id_organizacion = :org_id
ORDER BY u.user_name, r.nombre_rol;
```

**Obtener asignaciones de proyecto (con nombres):**
```sql
SELECT
    pr.id,
    pr.id_usuario,
    u.user_name,
    pr.id_organizacion,
    o.organization_name,
    pr.id_proyecto,
    p.nombre as project_name,
    pr.id_rol,
    prb.nombre_rol as role_name,
    pr.active
FROM proyectos_roles pr
INNER JOIN myllm_core_db.users u ON pr.id_usuario = u.user_id
INNER JOIN myllm_core_db.organizations o ON pr.id_organizacion = o.organization_id
INNER JOIN proyectos p ON pr.id_proyecto = p.id_proyecto
INNER JOIN proyectos_roles_base prb ON pr.id_rol = prb.id
WHERE pr.id_proyecto = :project_id
ORDER BY u.user_name, prb.nombre_rol;
```

#### Migración de base de datos (si es necesaria)

```sql
-- Verificar que existen las tablas
-- Si no existen, crear con esta estructura:

CREATE TABLE IF NOT EXISTS asignaciones_organizaciones_internas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    id_usuario INT NOT NULL,
    id_organizacion INT NOT NULL,
    id_rol INT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_org_role (id_usuario, id_organizacion, id_rol),
    INDEX idx_usuario (id_usuario),
    INDEX idx_organizacion (id_organizacion),
    INDEX idx_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verificar proyectos_roles tiene los campos necesarios
ALTER TABLE proyectos_roles
ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE AFTER id_rol;
```

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

## Estilos de botones en Reflex (OBLIGATORIO EN AMBAS APPS)

**Regla fundamental:** Todos los botones con fondo de color identidad (`color_scheme="green"` en
frontend, `color_scheme="orange"` en backoffice) **DEBEN** tener el texto en **negro** y en
**negrita**. Esto es obligatorio para garantizar la legibilidad sobre fondos coloreados.
Un botón con fondo verde o naranja y texto blanco es **INACEPTABLE**.

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

## Colores estándar para badges de estado y prioridad (OBLIGATORIO EN AMBAS APPS)

**Regla fundamental:** Los badges que representan **estado** y **prioridad** de tickets (y cualquier
otra entidad con los mismos conceptos) deben usar un código de colores **homogéneo** en todas las
aplicaciones. Esto garantiza que el usuario perciba la misma información visual en frontend y backoffice.

### Componente obligatorio

Usar siempre `rx.badge` con `variant="solid"` y texto en **negro** para máximo contraste y legibilidad:

```python
rx.badge(
    ticket["estado"],
    color_scheme="blue",
    variant="solid",
    size="2",
    style={"fontSize": "14px", "padding": "6px 12px", "fontWeight": "600", "color": "black"},
)
```

### Colores de estado de tickets

| Estado | `color_scheme` | Significado |
|--------|---------------|-------------|
| `abierto` | `"blue"` | Ticket nuevo, requiere atención |
| `en_espera` | `"amber"` | Esperando respuesta del cliente o del equipo |
| `resuelto` | `"green"` | Resuelto satisfactoriamente |
| `cerrado` | `"gray"` | Cerrado / archivado |

### Colores de prioridad de tickets

| Prioridad | `color_scheme` | Significado |
|-----------|---------------|-------------|
| `baja` | `"gray"` | Baja prioridad, sin urgencia |
| `media` | `"cyan"` | Prioridad normal |
| `alta` | `"orange"` | Requiere atención pronta |
| `urgente` | `"red"` | Crítico, atención inmediata |

### Implementación estándar (CRÍTICO: usar rx.match)

**IMPORTANTE:** Dentro de `rx.foreach`, los valores como `ticket["estado"]` son `Var` reactivos de
Reflex, NO strings de Python. Esto significa que `dict.get(ticket["estado"], "gray")` **SIEMPRE**
retorna `"gray"` porque Python no puede comparar un `Var` con claves de diccionario en tiempo de
compilación. Se **DEBE** usar `rx.match` para que la evaluación ocurra en el cliente (JavaScript).

```python
# ✅ CORRECTO - Usar rx.match para color_scheme dinámico en rx.foreach
# Texto SIEMPRE en negro ("color": "black") para legibilidad sobre fondo coloreado
rx.badge(
    ticket["estado"],
    color_scheme=rx.match(
        ticket["estado"],
        ("abierto", "blue"),
        ("en_espera", "amber"),
        ("resuelto", "green"),
        ("cerrado", "gray"),
        "gray",  # default
    ),
    variant="solid",
    size="2",
    style={"fontSize": "14px", "padding": "6px 12px", "fontWeight": "600", "color": "black"},
)

rx.badge(
    ticket["prioridad"],
    color_scheme=rx.match(
        ticket["prioridad"],
        ("baja", "gray"),
        ("media", "cyan"),
        ("alta", "orange"),
        ("urgente", "red"),
        "gray",  # default
    ),
    variant="solid",
    size="2",
    style={"fontSize": "14px", "padding": "6px 12px", "fontWeight": "600", "color": "black"},
)
```

```python
# ❌ INCORRECTO - dict.get() NO funciona con Var reactivos en rx.foreach
estado_colors = {"abierto": "blue", "en_espera": "amber", ...}
rx.badge(
    ticket["estado"],
    color_scheme=estado_colors.get(ticket["estado"], "gray"),  # Siempre retorna "gray"
)

# ❌ INCORRECTO - Usar rx.box con hexadecimales en lugar de rx.badge
rx.box(
    rx.text(ticket["estado"], color="#ffffff"),
    background_color="#52525b",  # No usar hexadecimales, usar rx.badge + rx.match
)

# ❌ INCORRECTO - Usar variant="soft" (poco contraste)
rx.badge(ticket["estado"], variant="soft")  # Debe ser variant="solid"
```

### Archivos afectados

| Archivo | Componente | Descripción |
|---------|-----------|-------------|
| `src/apps/5_web_frontend/components/seguimiento.py` | `ticket_row()` | Visor de tickets del frontend |
| `src/apps/6_web_backoffice/components/seguimiento.py` | `ticket_row()` | Visor de tickets de Seguimiento |
| `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py` | `ticket_row()` | Visor de tickets de Soporte |

### Extensión a otras entidades

Si en el futuro se añaden badges para conversaciones, proyectos u otras entidades con estados/prioridades,
deben seguir la misma paleta. Por ejemplo, el estado de conversación (`abierta`, `en_curso`, `resuelta`,
`cerrada`) debería mapear a los mismos colores conceptuales (`blue`, `amber`, `green`, `gray`).

## Estilos visuales — Títulos, Labels y Selectores (OBLIGATORIO EN AMBAS APPS)

**Regla fundamental:** Todas las páginas de **ambas aplicaciones** (frontend y backoffice)
deben seguir un estilo visual uniforme para títulos de página, títulos de paneles, títulos
de diálogos/modales, etiquetas de selectores y selectores. El color de identidad de cada
aplicación debe usarse consistentemente en **TODOS** los `rx.heading` de la UI.

**PROHIBIDO:** Usar `COLORS["foreground"]` (blanco), `"white"` o cualquier gris en títulos.

| Aplicación | Color identidad | Variable | Hex |
|------------|----------------|----------|-----|
| **Frontend** (8005) | Verde | `COLORS["primary"]` | `#22c55e` |
| **Backoffice** (8006) | Naranja | `COLORS["primary"]` | `#FF8C00` |

### Títulos de página (fuera de paneles)

Son los títulos principales que identifican la página actual (ej: "Gestión de Organización",
"Estado de Proyectos", "Informes"). Aparecen en la parte superior del contenido.

| Propiedad | Valor | Descripción |
|-----------|-------|-------------|
| Componente | `rx.heading` | Título de nivel página |
| `size` | `"8"` | Tamaño grande para destacar |
| `color` | `COLORS["primary"]` | Color identidad de la app |
| `margin_bottom` | `"0.5em"` | Separación inferior |

```python
# ✅ CORRECTO - Título de página (ambas apps)
rx.heading("Gestión de Organización", size="8", color=COLORS["primary"], margin_bottom="0.5em")

# ❌ INCORRECTO - Blanco/gris en títulos
rx.heading("Gestión de Organización", size="8", color=COLORS["foreground"])
rx.heading("Gestión de Organización", size="8", color="white")
```

### Títulos de paneles (dentro de secciones/cards)

Son los títulos de secciones dentro de una página (ej: "Gestión de Usuarios",
"Gestión de Proyectos", "Gestión de Tickets", "Resumen General").
También incluye títulos de diálogos/modales (ej: "Requisitos de Contraseña",
"Error de Contraseña", "Crear Nueva Organización").

| Propiedad | Valor | Descripción |
|-----------|-------|-------------|
| Componente | `rx.heading` | Título de sección/diálogo |
| `size` | `"6"` | Tamaño estándar para paneles |
| `color` | `COLORS["primary"]` | Color identidad de la app |

```python
# ✅ CORRECTO - Título de panel (ambas apps)
rx.heading("Gestión de Usuarios", size="6", color=COLORS["primary"])

# ✅ CORRECTO - Con icono
rx.hstack(
    rx.icon("users", size=28, color=COLORS["primary"]),
    rx.heading("Gestión de Usuarios", size="6", color=COLORS["primary"]),
    spacing="3",
    align_items="center",
)

# ✅ CORRECTO - Título de diálogo/modal
rx.heading("Requisitos de Contraseña", size="6", color=COLORS["primary"])

# ❌ INCORRECTO - Usar blanco en lugar del color identidad
rx.heading("Gestión de Usuarios", size="6", color=COLORS["foreground"])
rx.heading("Requisitos de Contraseña", size="6", color="white")
```

### Etiquetas de selectores (labels)

Son los textos que acompañan a los selectores (`rx.select`) indicando qué campo es
(ej: "Organización", "Proyecto", "Versión", "Rol", "Usuario").

| Propiedad | Valor | Descripción |
|-----------|-------|-------------|
| Componente | `rx.text` | Etiqueta del selector |
| `font_size` | `"1.1em"` | Tamaño legible, consistente |
| `color` | `COLORS["primary"]` (`#FF8C00`) | Naranja identidad backoffice |
| `font_weight` | `"bold"` | Negrita para destacar |

```python
# ✅ CORRECTO - Etiqueta de selector
rx.text("Organización", font_size="1.1em", color=COLORS["primary"], font_weight="bold")
rx.text("Proyecto:", font_size="1.1em", color=COLORS["primary"], font_weight="bold")

# ❌ INCORRECTO - Tamaño pequeño o color blanco
rx.text("Organización", font_size="0.9em", color=COLORS["foreground"])
rx.text("Organización", font_size="1em", color="#f97316", font_weight="600")
```

### Selectores (`rx.select`)

| Propiedad | Valor | Descripción |
|-----------|-------|-------------|
| Componente | `rx.select` | Selector desplegable |
| `size` | `"3"` | Tamaño medio estándar |
| `width` | `"100%"` | Ancho completo dentro de su contenedor |
| `background_color` | `COLORS["input"]` (`#3a3a3a`) | Fondo oscuro legible |
| `color` | `COLORS["foreground"]` (`#f2f2f5`) | Texto claro sobre fondo oscuro |
| `border_color` | `COLORS["border"]` (`#404040`) | Borde visible |

**CRÍTICO:** El backoffice usa tema oscuro. Los selectores **DEBEN** tener `background_color`,
`color` y `border_color` explícitos para garantizar que el texto seleccionado sea legible.
Sin estos estilos, el contenido del selector puede ser ilegible sobre el fondo oscuro.

```python
# ✅ CORRECTO - Selector con estilo para tema oscuro
rx.select(
    items,
    value=selected_value,
    on_change=on_change_handler,
    placeholder="Seleccione organización",
    size="3",
    width="100%",
    background_color=COLORS["input"],
    color=COLORS["foreground"],
    border_color=COLORS["border"],
)

# ✅ CORRECTO - rx.select.root con estilo en trigger
rx.select.root(
    rx.select.trigger(
        placeholder="Selecciona usuario...",
        style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"], "borderColor": COLORS["border"]},
    ),
    rx.select.content(...),
    size="3",
    width="100%",
)

# ❌ INCORRECTO - Selector sin colores explícitos (ilegible en tema oscuro)
rx.select(
    items,
    value=selected_value,
    on_change=on_change_handler,
    size="3",
    width="100%",
)
```

### Constantes de estilo para componentes compartidos

Los componentes reutilizables que no tienen acceso al diccionario `COLORS` deben usar
directamente los valores hexadecimales:

```python
# En components/org_selector.py
LABEL_COLOR = "#FF8C00"        # Alineado con COLORS["primary"]
LABEL_FONT_SIZE = "1.1em"      # Tamaño legible
LABEL_FONT_WEIGHT = "bold"     # Negrita
SELECT_SIZE = "3"              # Tamaño medio estándar

# Estilo estándar para selectores en fondo oscuro (garantiza legibilidad)
SELECT_STYLE = {
    "backgroundColor": "#3a3a3a",  # Alineado con COLORS["input"]
    "color": "#f2f2f5",            # Alineado con COLORS["foreground"]
    "borderColor": "#555",         # Borde visible
}
```

### Diccionario COLORS obligatorio en componentes

Todos los archivos de componentes del backoffice que definan un diccionario `COLORS` local
**DEBEN** incluir la clave `"input"` para garantizar la legibilidad de los selectores:

```python
# ✅ CORRECTO - COLORS con clave "input"
COLORS = {
    "background": "#1a1a1a",
    "card": "#2d2d2d",
    "foreground": "#f2f2f5",
    "primary": "#FF8C00",
    "border": "#404040",
    "input": "#3a3a3a",      # OBLIGATORIO para selectores
    "muted_foreground": "#E0E0E0",
}
```

### Headings en markdown (component_map)

Los `component_map` de `rx.markdown()` deben usar `COLORS["primary"]` en TODOS los niveles
de heading (h1, h2, h3). **PROHIBIDO** usar `COLORS["foreground"]` en headings de markdown.

```python
# ✅ CORRECTO - Todos los headings del markdown usan color identidad
component_map={
    "h1": lambda text: rx.heading(text, size="7", color=COLORS["primary"], ...),
    "h2": lambda text: rx.heading(text, size="6", color=COLORS["primary"], ...),
    "h3": lambda text: rx.heading(text, size="5", color=COLORS["primary"], ...),
    # párrafos y listas SÍ pueden usar foreground/muted_foreground
    "p": lambda text: rx.text(text, color=COLORS["muted_foreground"], ...),
}

# ❌ INCORRECTO - h1 y h3 en blanco, h2 en color identidad (inconsistente)
component_map={
    "h1": lambda text: rx.heading(text, size="7", color=COLORS["foreground"], ...),
    "h2": lambda text: rx.heading(text, size="6", color=COLORS["primary"], ...),
    "h3": lambda text: rx.heading(text, size="5", color=COLORS["foreground"], ...),
}
```

### Resumen de jerarquía visual

**Backoffice (naranja `#FF8C00`):**

| Elemento | size/font_size | color | font_weight | bg/border |
|----------|---------------|-------|-------------|-----------|
| Título de página | `size="8"` | `COLORS["primary"]` | - | - |
| Título de panel/diálogo | `size="6"` | `COLORS["primary"]` | - | - |
| Subtítulo/sección | `size="5"` | `COLORS["primary"]` | - | - |
| Etiqueta selector | `font_size="1.1em"` | `COLORS["primary"]` | `bold` | - |
| Selector | `size="3"` | `COLORS["foreground"]` | - | bg: `COLORS["input"]`, border |

**Frontend (verde `#22c55e`):**

| Elemento | size/font_size | color | font_weight | bg/border |
|----------|---------------|-------|-------------|-----------|
| Título de página | `size="8"` | `COLORS["primary"]` / `COLORS["accent"]` | - | - |
| Título de panel/diálogo | `size="6"`-`"7"` | `COLORS["primary"]` | - | - |
| Subtítulo/sección | `size="5"` | `COLORS["primary"]` | - | - |
| Selector | `size="3"` | `COLORS["foreground"]` | - | bg: `COLORS["input"]`, border |

**Estas reglas aplican a TODAS las páginas de AMBAS aplicaciones sin excepción.**

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
  - IA (uso interno y entrenamiento) → `4_trainer` en servidor trainer (API REST + ChromaDB vectorial + Ollama LLM).
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

---

## Prompt Family Recognition Rules

### Overview

The system uses a **four-category prompt library** to normalize AI interactions with Ollama. Agents must recognize and correctly classify prompts into these families when creating, editing, or combining prompts for AI queries.

### The 4 Prompt Families

#### 1. **Identidades** (Identities)

**Purpose:** Define the AI assistant's role, personality, expertise, and behavioral traits.

**Recognition Keywords:**
- "Eres", "Actúas como", "Tu rol es", "Tu misión es"
- "Asistente", "Experto", "Especialista", "Consultor", "Auditor"
- "Personalidad", "Tono", "Estilo de comunicación"
- "Experiencia en", "Conocimientos en", "Habilidades"

**Examples:**

```
✅ Identity Prompt:
"Eres un asistente experto en análisis de datos de proyectos educativos con más de 10 años de experiencia. Tu tono es profesional pero cercano, y siempre buscas proporcionar insights accionables basados en datos objetivos."

✅ Identity Prompt:
"Actúas como un auditor de cumplimiento normativo especializado en regulaciones educativas españolas. Tu misión es garantizar que todas las recomendaciones se alineen con la normativa vigente."

❌ Not Identity:
"El proyecto tiene 50 participantes" (this is context, not identity)
```

**Anti-patterns:**
- Including data or statistics about projects (belongs to Context)
- Describing output format requirements (belongs to Modality)
- Listing specific tasks to perform (belongs to Solicitudes)

---

#### 2. **Contexto** (Context)

**Purpose:** Provide domain-specific context, business rules, constraints, and operational environment.

**Recognition Keywords:**
- "Contexto", "Entorno", "Dominio", "Ámbito"
- "Organización", "Proyecto", "Normativa", "Regulación"
- "Restricciones", "Políticas", "Procedimientos", "Estándares"
- "Estructura organizativa", "Roles", "Permisos"
- "Datos relevantes", "KPIs", "Métricas"

**Examples:**

```
✅ Context Prompt:
"Trabajas en una organización multi-tenant que gestiona proyectos de formación profesional. Cada proyecto tiene roles jerárquicos: SuperAdmin, OrgAdmin, Trainer, Lector. Los datos personales deben tratarse con estricta confidencialidad según GDPR."

✅ Context Prompt:
"El proyecto actual tiene 3 fases: inicial (50 horas), desarrollo (200 horas) y cierre (30 horas). Los KPIs clave son: tasa de asistencia (objetivo >85%), satisfacción (objetivo >4.2/5) y tasa de finalización (objetivo >90%)."

❌ Not Context:
"Genera un informe ejecutivo" (this is a request, not context)
```

**Anti-patterns:**
- Including instructions about what to do (belongs to Solicitudes)
- Defining the AI's role (belongs to Identidades)
- Specifying response format (belongs to Modality)

---

#### 3. **Solicitudes** (Requests)

**Purpose:** Define specific tasks, requests, or operations the user can ask the AI to perform.

**Recognition Keywords:**
- "Analiza", "Genera", "Crea", "Produce", "Elabora"
- "Identifica", "Detecta", "Encuentra", "Busca"
- "Compara", "Evalúa", "Calcula", "Estima"
- "Recomienda", "Sugiere", "Propone", "Aconseja"
- "Informe", "Reporte", "Dashboard", "Resumen"

**Examples:**

```
✅ Request Prompt:
"Analiza el rendimiento del proyecto comparando los KPIs actuales con los objetivos establecidos. Identifica desviaciones significativas (>10%) y proporciona recomendaciones accionables para corregir el rumbo."

✅ Request Prompt:
"Genera un informe ejecutivo que resuma el estado del proyecto, incluyendo: progreso general, riesgos identificados, hitos alcanzados y próximos pasos críticos."

❌ Not Request:
"Responde en formato JSON" (this is modality, not a request)
```

**Anti-patterns:**
- Describing how the response should be formatted (belongs to Modality)
- Providing background information (belongs to Context)
- Defining who the AI is (belongs to Identidades)

---

#### 4. **Modalidad** (Modality)

**Purpose:** Specify the format, style, structure, and presentation of the AI's response.

**Recognition Keywords:**
- "Formato", "Estructura", "Plantilla", "Layout"
- "JSON", "Markdown", "HTML", "Tabla", "Lista", "Bullet points"
- "Secciones", "Párrafos", "Títulos", "Subtítulos"
- "Longitud", "Brevedad", "Detalle", "Nivel de profundidad"
- "Visualización", "Gráficos sugeridos", "Dashboard"
- "Idioma", "Estilo de escritura", "Tono formal/informal"

**Examples:**

```
✅ Modality Prompt:
"Responde en formato JSON estructurado con las siguientes claves:
{
  'análisis': string,
  'conclusiones': array de strings,
  'recomendaciones': array de objetos con {prioridad, acción, impacto}
}
Máximo 500 palabras por sección."

✅ Modality Prompt:
"Presenta tu respuesta como un informe narrativo con bullet points. Estructura:
1. Resumen Ejecutivo (máximo 3 párrafos)
2. Análisis Detallado (5-7 bullet points)
3. Conclusiones (lista numerada)
4. Próximos Pasos (tabla con columnas: Acción, Responsable, Fecha)
Usa un tono profesional pero accesible."

❌ Not Modality:
"Analiza los KPIs del proyecto" (this is a request, not format specification)
```

**Anti-patterns:**
- Including task instructions (belongs to Solicitudes)
- Describing the AI's expertise (belongs to Identidades)
- Providing data or constraints (belongs to Context)

---

### Combining Prompts: The Full Query Pattern

When building a complete Ollama query, agents must combine prompts from all 4 families in this order:

```
[Identidad] + [Contexto] + [Solicitud] + [Entrada del Usuario] + [Modalidad]
```

**Example of Complete Query:**

```python
# Identity
identity_prompt = "Eres un asistente experto en análisis de proyectos educativos."

# Context
context_prompt = "Trabajas en una organización que gestiona proyectos de formación. Los KPIs clave son: asistencia (>85%), satisfacción (>4.2/5), finalización (>90%)."

# Request
request_prompt = "Analiza el rendimiento del proyecto comparando KPIs actuales con objetivos. Identifica desviaciones >10% y proporciona recomendaciones."

# User Input
user_input = "¿Cómo está el rendimiento del proyecto X en el Q4?"

# Modality
modality_prompt = "Responde en formato JSON con claves: {análisis, desviaciones, recomendaciones}. Máximo 500 palabras."

# Combined Query
full_query = f"""
{identity_prompt}

{context_prompt}

{request_prompt}

Entrada del usuario: {user_input}

{modality_prompt}
"""
```

**Result sent to Ollama:**
```
Eres un asistente experto en análisis de proyectos educativos.

Trabajas en una organización que gestiona proyectos de formación. Los KPIs clave son: asistencia (>85%), satisfacción (>4.2/5), finalización (>90%).

Analiza el rendimiento del proyecto comparando KPIs actuales con objetivos. Identifica desviaciones >10% y proporciona recomendaciones.

Entrada del usuario: ¿Cómo está el rendimiento del proyecto X en el Q4?

Responde en formato JSON con claves: {análisis, desviaciones, recomendaciones}. Máximo 500 palabras.
```

---

### Classification Decision Tree

When an agent needs to classify a new prompt, use this decision tree:

```
1. Does it define WHO the AI is or its expertise?
   ├─ YES → **Identidades**
   └─ NO → Continue

2. Does it provide background information, constraints, or business rules?
   ├─ YES → **Contexto**
   └─ NO → Continue

3. Does it ask the AI to DO something or perform a task?
   ├─ YES → **Solicitudes**
   └─ NO → Continue

4. Does it specify HOW the response should be formatted or structured?
   ├─ YES → **Modalidad**
   └─ NO → Ambiguous - Request clarification
```

---

### Common Misclassification Pitfalls

| Prompt Fragment | ❌ Wrong Category | ✅ Correct Category | Explanation |
|----------------|------------------|-------------------|-------------|
| "Eres experto y debes generar un informe" | Identidades | **Split:** Identity + Request | Contains both role and task - must separate |
| "El proyecto tiene KPIs: analízalos" | Contexto | **Split:** Context + Request | Contains both data and instruction |
| "Responde como un auditor en formato JSON" | Modalidad | **Split:** Identity + Modality | Contains both role and format |
| "Genera un informe ejecutivo bien estructurado" | Solicitudes | **Split:** Request + Modality | Contains both task and format expectation |

**Rule:** If a prompt mixes multiple intents, agents should **suggest splitting** into multiple prompts (one per category).

---

### Validation Rules for Agents

When creating or editing prompts, agents must:

1. **Verify Category Fit:**
   - Run the prompt through the decision tree
   - Ensure it fits cleanly into ONE category
   - If ambiguous, flag for user review

2. **Check for Cross-Contamination:**
   - Identity prompts should NOT contain tasks
   - Context prompts should NOT contain format instructions
   - Request prompts should NOT define the AI's role
   - Modality prompts should NOT include business data

3. **Ensure Active Status:**
   - Only active prompts (`active=TRUE`) should be used in queries
   - Warn if trying to combine a disabled prompt

4. **Validate Uniqueness:**
   - Prompt names must be unique within their category
   - Suggest alternative names if duplicates detected

5. **Preserve Hierarchy:**
   - Always combine prompts in order: Identity → Context → Request → Modality
   - Never skip a category (use empty string if category not needed)

---

### Example Recognition Exercises

**Exercise 1:**
```
"Eres un consultor estratégico especializado en educación profesional con experiencia en análisis de métricas de rendimiento."
```
**Category:** Identidades
**Reason:** Defines role, expertise, and domain knowledge

---

**Exercise 2:**
```
"La organización gestiona proyectos multi-tenant con roles SuperAdmin, OrgAdmin, Trainer. Datos GDPR-compliant."
```
**Category:** Contexto
**Reason:** Describes organizational structure and constraints

---

**Exercise 3:**
```
"Detecta anomalías en los KPIs de asistencia y satisfacción. Proporciona alertas tempranas si la desviación supera el 15%."
```
**Category:** Solicitudes
**Reason:** Defines specific task (detect anomalies) and criteria

---

**Exercise 4:**
```
"Responde en tabla markdown con columnas: KPI, Valor Actual, Objetivo, Desviación (%), Estado (OK/Alerta/Crítico)."
```
**Category:** Modalidad
**Reason:** Specifies exact output format and structure

---

### Agent Responsibilities

#### When Creating Prompts:
1. Ask user which category they're targeting
2. Validate prompt content matches category intent
3. Suggest refinements if cross-contamination detected
4. Ensure name is unique within category
5. Default `active=TRUE` for new prompts

#### When Editing Prompts:
1. Preserve original category
2. Alert if edits introduce cross-contamination
3. Update `updated_by` and `updated_at` automatically
4. Maintain audit trail

#### When Combining Prompts:
1. Verify all 4 categories are covered (or explicitly state which are omitted)
2. Check all selected prompts are active
3. Combine in correct order: Identity → Context → Request → Modality
4. Insert user input between Request and Modality
5. Log combined query for debugging

---

### Database Mapping

| Category | Table Name | Primary Key |
|----------|-----------|-------------|
| Identidades | `prompts_identidades` | `id_prompt` |
| Contexto | `prompts_contexto` | `id_prompt` |
| Solicitudes | `prompts_solicitudes` | `id_prompt` |
| Modalidad | `prompts_modalidad` | `id_prompt` |

All tables share the same schema:
- `id_prompt` (INT, AUTO_INCREMENT, PK)
- `name` (VARCHAR(255), UNIQUE per table)
- `description` (TEXT, optional)
- `prompt` (MEDIUMTEXT, required)
- `active` (BOOLEAN, default TRUE)
- `created_at`, `updated_at`, `created_by`, `updated_by` (audit fields)

---

### Integration with Ollama (Future)

When the Ollama integration is implemented, agents will:

1. **Receive user query** with category IDs:
   ```python
   query_params = {
       "identity_id": 1,
       "context_id": 2,
       "request_id": 3,
       "modality_id": 4,
       "user_input": "¿Cómo está el proyecto X?"
   }
   ```

2. **Fetch active prompts** from database:
   ```python
   identity = get_prompt("identidades", 1)
   context = get_prompt("contexto", 2)
   request = get_prompt("solicitudes", 3)
   modality = get_prompt("modalidad", 4)
   ```

3. **Validate all prompts are active:**
   ```python
   if not all(p["active"] for p in [identity, context, request, modality]):
       raise ValueError("All prompts must be active")
   ```

4. **Build normalized query:**
   ```python
   full_query = f"{identity['prompt']}\n\n{context['prompt']}\n\n{request['prompt']}\n\nEntrada: {user_input}\n\n{modality['prompt']}"
   ```

5. **Send to Ollama** and return response

---

### Summary of Recognition Rules

| If the prompt... | Then classify as... |
|-----------------|-------------------|
| Defines AI's role, personality, or expertise | **Identidades** |
| Provides background, constraints, or business rules | **Contexto** |
| Instructs AI to perform a specific task | **Solicitudes** |
| Specifies response format or structure | **Modalidad** |
| Contains elements from multiple categories | **Split into separate prompts** |

**Golden Rule:** One prompt = One category. If a prompt tries to do multiple things, it should be split into multiple prompts (one per category).

---

Use these rules consistently when working with the Gestión de Prompts feature to ensure proper categorization and effective AI query construction.

## 23. Gestión de Sesiones y JWT - Reglas Críticas

**ADVERTENCIA**: El sistema de gestión de sesiones y tokens JWT es CRÍTICO para la seguridad y estabilidad del sistema. Las siguientes reglas DEBEN respetarse SIEMPRE.

### 23.1. Arquitectura de Sesiones

```
Frontend/Backoffice → Middleware → Broker → Backend Core/IA
     (cliente)      (validación)  (proxy)    (confían)
```

**Responsabilidades por capa**:

| Capa | Responsabilidad | ¿Valida tokens? |
|------|----------------|----------------|
| **Frontend/Backoffice** | Renovación automática, sincronización Redis | ❌ No |
| **Middleware** | Validación JWT, gestión de sesiones | ✅ Sí |
| **Broker** | Propagación transparente de headers | ❌ No |
| **Backend Core/IA** | Lógica de negocio | ❌ No (confía en middleware) |

### 23.2. Reglas OBLIGATORIAS de Tokens JWT

#### 23.2.1. Estructura de Tokens

```python
# ✅ CORRECTO: Tokens con todos los campos requeridos
access_payload = {
    "user_id": int,
    "organization_id": int,
    "identity_type_id": int,
    "iat": int,           # Issued At (timestamp Unix)
    "exp": int,           # Expiration (timestamp Unix)
    "jti": str,           # JWT ID (UUID único para ESTE token)
    "session_id": str,    # Session ID (estable durante toda la sesión)
}

session_payload = {
    # ... mismos campos con jti DIFERENTE
}
```

**Regla #1**: `jti` DEBE ser único para cada token generado (usar `uuid.uuid4()`)

**Regla #2**: `session_id` DEBE mantenerse constante durante toda la sesión

**Regla #3**: Cada renovación genera NUEVOS `jti`, pero mantiene el mismo `session_id`

#### 23.2.2. TTLs Obligatorios

| Token | TTL | Uso |
|-------|-----|-----|
| **access_token** | 15 minutos (900 seg) | Autenticación de peticiones |
| **session_token** | 45 minutos (2700 seg) | Renovación de access_token |

**Regla #4**: NUNCA cambiar estos TTLs sin revisar el impacto en el loop de renovación

#### 23.2.3. Renovación de Tokens

```python
# ✅ CORRECTO: Flujo de renovación en middleware
def refresh_tokens(self, session_token: str, ...) -> TokenPair:
    # 1. Validar token antiguo
    session_payload = _decode_jwt(session_token, ...)
    old_jti = session_payload.get("jti")
    session_id = session_payload.get("session_id")

    # 2. Buscar sesión por JTI ANTIGUO
    session_record = find_by_jti(old_jti, session_id)

    # 3. Generar NUEVOS tokens (con nuevos JTIs)
    tokens = self.issue_tokens(..., session_id=session_id)  # Reutiliza session_id

    # 4. ❌ NO GUARDAR sessions.json aquí
    # issue_tokens() ya lo guarda internamente con los JTIs nuevos

    return tokens


# ❌ INCORRECTO: Guardar sessions.json después de issue_tokens()
def refresh_tokens_WRONG(self, session_token: str, ...) -> TokenPair:
    sessions_data = load_sessions()  # V1 con JTIs antiguos
    tokens = self.issue_tokens(...)  # Genera JTIs nuevos y guarda (V2)
    store_sessions(sessions_data)    # ⚠️ SOBRESCRIBE V2 con V1 antigua
    return tokens
```

**Regla #5**: NUNCA guardar `sessions.json` después de llamar a `issue_tokens()` - causa race condition

**Regla #6**: `issue_tokens()` DEBE ser la única función que guarde `sessions.json` durante renovaciones

### 23.3. Gestión de Sesiones en sessions.json

**Ubicación**: `/Users/administrator/develop/anewhope/src/2_shared_application/moks/sessions.json`

**Estructura**:
```json
{
  "sessions": [
    {
      "session_id": "uuid-estable",
      "user_id": 1,
      "tokens": {
        "access_token_jti": "jti-actual-access",
        "session_token_jti": "jti-actual-session"
      },
      "status": "active",  # active | inactive | revoked | expired
      "expires_at": "2026-02-07T14:30:00Z",
      "created_at": "2026-02-07T14:00:00Z",
      "last_activity": "2026-02-07T14:15:00Z"
    }
  ]
}
```

**Regla #7**: Al renovar tokens, `_upsert_session_record()` DEBE actualizar los JTIs manteniendo el mismo `session_id`

**Regla #8**: La validación de tokens (`_find_session_record()`) busca por coincidencia EXACTA de JTIs

### 23.4. Renovación Automática en Cliente

**Frontend y Backoffice** ejecutan un loop en background que:

```python
@rx.event(background=True)
async def auto_renew_tokens_loop(self):
    while True:
        async with self:
            # 1. Sincronizar con Redis (tokens renovados por otra app)
            self._load_tokens_from_redis()

            # 2. Verificar expiración
            check_result = self.check_token_expiration()

            # 3. Renovar si es necesario
            if check_result["needs_renewal"]:
                success = self.ensure_tokens_valid()
                if not success:
                    # ✅ CORRECTO: Distinguir errores fatales de temporales
                    if "expirado" in self.login_error.lower():
                        self.clear_session()  # Error FATAL
                        break
                    else:
                        self.login_error = ""  # Error TEMPORAL, continuar

        await asyncio.sleep(120)  # Check cada 2 minutos
```

**Regla #9**: El loop de renovación DEBE ejecutarse cada 2 minutos (120 segundos)

**Regla #10**: Umbral de renovación: 3 minutos (180 segundos) antes de expiración

**Regla #11**: Si la renovación falla pero el token AÚN es válido, NO cerrar sesión

**Regla #12**: Solo cerrar sesión si el `session_token` realmente expiró (no por errores temporales)

### 23.5. Sincronización Redis entre Apps

**Clave**: `session_tokens:{session_id}`

**TTL**: 2700 segundos (45 minutos, igual que session_token)

**Payload**:
```json
{
  "access_token": "eyJ...",
  "session_token": "eyJ...",
  "access_expires_at": 1707234567,
  "session_expires_at": 1707236367,
  "updated_at": "2026-02-07T10:30:15",  # ISO timestamp
  "user_id": 123,
  "organization_id": 45
}
```

**Regla #13**: `_save_tokens_to_redis()` DEBE llamarse después de cada renovación

**Regla #14**: `_load_tokens_from_redis()` DEBE comparar timestamps `updated_at` y actualizar solo si son más recientes

**Regla #15**: Si `last_activity` está vacío (primera carga), SIEMPRE cargar desde Redis

### 23.6. Propagación de Headers en Broker

```python
# ✅ CORRECTO: Propagación transparente
def set_security_context(self, authorization=None, session_token=None):
    self._authorization = authorization
    self._session_token = session_token

    # Propagar a backends
    self._core_client.set_security_context(authorization, session_token)
    self._trainer_client.set_security_context(authorization, session_token)
```

**Regla #16**: El broker NUNCA valida tokens, solo los propaga

**Regla #17**: Los backends (core, IA) confían en que el middleware ya validó

### 23.7. Logging Obligatorio

**En middleware**:
```python
# En refresh_tokens():
self._logger.info(
    "Renovación: session_id=%s user_id=%s old_jti=%s",
    session_id, user_id, old_jti
)

# En issue_tokens():
self._logger.info(
    "Generando tokens: session_id=%s access_jti=%s session_jti=%s",
    session_id, access_jti, session_jti
)

# En _validate_tokens() (fallo):
self._logger.error(
    "Sesión no encontrada: session_id=%s access_jti=%s session_jti=%s",
    session_id, access_jti, session_jti
)
```

**Regla #18**: TODO evento de sesión (login, refresh, validate, logout) DEBE loguearse con `session_id` y `jti`

**Regla #19**: Errores de validación DEBEN loguear las sesiones registradas (primeras 5) para debugging

### 23.8. Casos de Uso Críticos

#### 23.8.1. Entrenamientos Largos de Modelos LLM

**Problema**: Entrenamiento puede durar horas, tokens expiran cada 15 min

**Solución**:
- ✅ Loop de renovación continúa en background
- ✅ Tokens se renuevan automáticamente cada ~12 minutos
- ✅ Si el middleware falla, el cliente NO se expulsa inmediatamente
- ✅ El usuario puede seguir trabajando con los tokens actuales

**Regla #20**: NUNCA bloquear el loop de renovación durante operaciones largas

#### 23.8.2. Alternancia entre Frontend y Backoffice

**Problema**: Usuario cambia entre apps, pierde sesión

**Solución**:
- ✅ Tokens se guardan en Redis al cambiar de app
- ✅ La app destino carga tokens desde Redis (no desde URL)
- ✅ Solo se pasa `session_id` en URL (seguro)

**Regla #21**: Al alternar apps, llamar `_save_tokens_to_redis()` ANTES del redirect

**Regla #22**: En `on_page_load()`, si viene `session_id`, cargar tokens desde Redis

### 23.9. Checklist de Modificaciones

Antes de modificar código de sesiones/tokens, verificar:

- [ ] ¿Se mantiene el `session_id` estable durante toda la sesión?
- [ ] ¿Se generan nuevos `jti` únicos para cada token?
- [ ] ¿Se llama a `_save_tokens_to_redis()` después de renovar?
- [ ] ¿NO se guarda `sessions.json` después de `issue_tokens()`?
- [ ] ¿Se loguean todos los eventos de sesión?
- [ ] ¿Se manejan errores temporales sin expulsar al usuario?
- [ ] ¿El loop de renovación no se bloquea?
- [ ] ¿Se respetan los TTLs de 15/45 minutos?

### 23.10. Tests Obligatorios

Cualquier cambio en sesiones/tokens DEBE incluir tests para:

1. ✅ Renovación única exitosa
2. ✅ Renovaciones consecutivas (3+) exitosas
3. ✅ Validación con JTIs renovados
4. ✅ Sincronización Redis entre apps
5. ✅ Manejo de errores temporales vs fatales
6. ✅ Expiración de tokens (access y session)
7. ✅ Race conditions en `sessions.json`

**Comando**: `pytest src/apps/7_service_frontend/tests/test_session_management.py -v`

### 23.11. Referencias

**Documentación completa**: Ver README.md sección "Corrección de race condition en renovación de tokens"

**Archivos críticos**:
- Middleware: `src/apps/7_service_frontend/routermiddleware.py`
- Shared state: `src/2_shared_application/reflex_shared/shared_session_state.py`
- API clients: `src/apps/*/adapters/api_client.py`

### 23.12. Arquitectura DDD para Sesiones y JWT

**NUEVA REGLA CRÍTICA**: A partir de ahora, TODA gestión de sesiones y JWT DEBE usar los servicios DDD centralizados.

#### 23.12.1. Servicios DDD Obligatorios

**Ubicaciones**:
- **Domain Layer**: `src/1_shared_domain/entities/session.py`
- **Application Layer**: `src/2_shared_application/services/`
  - `jwt_service.py` - Generación y validación de tokens
  - `session_service.py` - Orquestación de sesiones
- **Repository**: `src/2_shared_application/interfaces/session_repository.py`

#### 23.12.2. Value Objects Inmutables

```python
# ✅ CORRECTO: Usar Value Objects del dominio
from src.shared_domain.entities.session import (
    Jti,           # Value Object con validación UUID
    JwtPayload,    # Value Object inmutable (frozen=True)
    TokenPair,     # Value Object inmutable (frozen=True)
    TokenType,     # Enum: ACCESS, SESSION
    JwtAlgorithm,  # Enum: HS256, HS384, etc.
)

# Generar JTI único
jti = Jti(str(uuid.uuid4()))  # Valida UUID en construcción

# Crear payload (inmutable)
payload = JwtPayload(
    session_id="abc-123",
    user_id=5,
    organization_id=2,
    identity_type_id=1,
    jti=jti.value,
    iat=int(time.time()),
    exp=int(time.time()) + 900,
    token_type=TokenType.ACCESS,
)

# ❌ NO SE PUEDE modificar después de creado
payload.user_id = 10  # ERROR: FrozenInstanceError
```

**Regla #23**: NUNCA crear payloads JWT manualmente. Usar `JwtPayload` con validación automática.

**Regla #24**: NUNCA modificar Value Objects después de su creación (son inmutables por diseño).

#### 23.12.3. JwtService - Servicio de Tokens

```python
# ✅ CORRECTO: Usar JwtService para operaciones de tokens
from src.shared_application.services.jwt_service import (
    JwtService,
    JwtSettings,
    TokenExpiredError,
    TokenValidationError,
)

# Inicializar servicio (una vez al arrancar middleware)
jwt_settings = JwtSettings(
    access_secret=env_settings.jwt_access_secret,
    session_secret=env_settings.jwt_session_secret,
    access_ttl_seconds=900,   # 15 min
    session_ttl_seconds=2700, # 45 min
    algorithm=JwtAlgorithm.HS256,
)
jwt_service = JwtService(jwt_settings)

# Generar par de tokens
token_pair = jwt_service.create_token_pair(
    session_id="abc-123",
    user_id=5,
    organization_id=2,
    identity_type_id=1,
)
# Retorna TokenPair inmutable con ambos tokens y metadatos

# Validar access token
try:
    payload = jwt_service.validate_access_token(access_token)
    # payload es JwtPayload validado
except TokenExpiredError:
    # Token expiró
except TokenValidationError:
    # Token inválido (firma, formato, etc.)

# Extraer JTI sin validar (para blacklist check)
jti = jwt_service.extract_jti_without_validation(token)
```

**Regla #25**: NUNCA llamar directamente a `jwt.encode()` o `jwt.decode()`. Usar siempre `JwtService`.

**Regla #26**: SIEMPRE capturar excepciones específicas (`TokenExpiredError`, `TokenValidationError`).

#### 23.12.4. SessionService - Orquestación de Sesiones

```python
# ✅ CORRECTO: Usar SessionService para lógica de negocio
from src.shared_application.services.session_service import (
    SessionService,
    CreateSessionRequest,
    SessionResponse,
    SessionNotFoundError,
    SessionExpiredError,
    InvalidTokenError,
)

# Inicializar servicio (inyección de dependencias)
session_service = SessionService(
    jwt_service=jwt_service,
    session_repository=json_session_repository,  # Adaptador
)

# FLUJO 1: Crear nueva sesión (login)
request = CreateSessionRequest(
    user_id=5,
    organization_id=2,
    identity_type_id=1,
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
)

response = session_service.create_session(request)
# response.session: Entidad Session
# response.token_pair: TokenPair con ambos tokens

# FLUJO 2: Renovar access token
try:
    new_token_pair = session_service.refresh_access_token(
        session_token=old_session_token
    )
    # new_token_pair tiene nuevos JTIs
except SessionExpiredError:
    # Sesión expiró en BD
except InvalidTokenError:
    # Token inválido o JTI no coincide

# FLUJO 3: Obtener contexto para permisos
try:
    context = session_service.get_session_context(access_token)
    # context es UserSessionContext con user_id, org_id, etc.
except SessionExpiredError:
    # Sesión no activa
except InvalidTokenError:
    # Token inválido

# FLUJO 4: Logout (invalidar sesión)
success = session_service.invalidate_session(
    session_id="abc-123",
    reason="logout",  # "logout", "expired", "revoked"
)

# FLUJO 5: Logout global (cambio de contraseña)
count = session_service.invalidate_all_user_sessions(
    user_id=5,
    reason="password_change",
)
```

**Regla #27**: NUNCA duplicar lógica de `create_session()` o `refresh_access_token()`. Usar `SessionService`.

**Regla #28**: SIEMPRE pasar `CreateSessionRequest` (no argumentos sueltos).

**Regla #29**: SIEMPRE capturar excepciones específicas del servicio.

#### 23.12.5. SessionRepository - Contrato de Persistencia

```python
# ✅ CORRECTO: Implementar SessionRepository como Protocol
from src.shared_application.interfaces.session_repository import SessionRepository
from src.shared_domain.entities.session import Session, SessionStatus

class JsonSessionRepository:
    """Implementación JSON del SessionRepository."""

    def get_by_session_id(self, session_id: str) -> Session | None:
        # Leer sessions.json
        # Convertir a entidad Session
        return session

    def save(self, session: Session) -> Session:
        # Guardar sessions.json
        # Retornar sesión guardada
        return session

    def update_status(
        self, session_id: str, status: SessionStatus, updated_at: datetime | None
    ) -> bool:
        # Actualizar estado de sesión
        return True

    def update_activity(self, session_id: str, last_activity: datetime) -> bool:
        # Actualizar última actividad
        return True

    def list_by_user_id(self, user_id: int) -> tuple[Session, ...]:
        # Listar sesiones del usuario
        return tuple(sessions)
```

**Regla #30**: NUNCA acceder directamente a `sessions.json`. Usar `SessionRepository`.

**Regla #31**: TODA implementación de `SessionRepository` DEBE implementar TODOS los métodos del Protocol.

**Regla #32**: `SessionRepository.save()` DEBE ser atómico (evitar race conditions).

#### 23.12.6. Refactorización del Middleware

**ANTES (Manual):**
```python
# ❌ NO HACER: Lógica manual de tokens
def issue_tokens(self, user_id, org_id, identity_type_id):
    session_id = str(uuid.uuid4())
    now = int(time.time())

    access_jti = str(uuid.uuid4())
    access_token = jwt.encode({
        "user_id": user_id,
        "jti": access_jti,
        "exp": now + 900,
        # ... más campos manualmente
    }, secret, algorithm="HS256")

    # ... código duplicado para session_token
    # ... guardar manualmente en sessions.json
```

**DESPUÉS (DDD):**
```python
# ✅ HACER: Delegar a SessionService
def __init__(self):
    # Inicializar servicios DDD una vez
    jwt_settings = JwtSettings(...)
    self._jwt_service = JwtService(jwt_settings)
    self._session_repository = JsonSessionRepository()
    self._session_service = SessionService(
        self._jwt_service,
        self._session_repository,
    )

def issue_tokens(self, user_id, org_id, identity_type_id):
    # Delegar toda la lógica a SessionService
    request = CreateSessionRequest(
        user_id=user_id,
        organization_id=org_id,
        identity_type_id=identity_type_id,
    )

    response = self._session_service.create_session(request)

    return {
        "access_token": response.token_pair.access_token,
        "session_token": response.token_pair.session_token,
        "access_expires_at": response.token_pair.access_expires_at,
        "session_expires_at": response.token_pair.session_expires_at,
        "session_id": response.session.session_id,
    }

def refresh_tokens(self, session_token):
    # Delegar a SessionService
    try:
        token_pair = self._session_service.refresh_access_token(session_token)

        return {
            "access_token": token_pair.access_token,
            "session_token": token_pair.session_token,
            # ... metadatos
        }
    except SessionExpiredError as exc:
        raise MiddlewareAuthError(f"Sesión expirada: {exc}")
    except InvalidTokenError as exc:
        raise MiddlewareAuthError(f"Token inválido: {exc}")
```

**Regla #33**: Al refactorizar, ELIMINAR toda lógica manual de JWT del middleware.

**Regla #34**: Al refactorizar, NO cambiar interfaces públicas del middleware (solo internals).

#### 23.12.7. Beneficios de la Arquitectura DDD

**Eliminación de Race Conditions:**
- `SessionRepository.save()` es atómico
- No más lecturas/escritas manuales de JSON
- Un solo punto de persistencia

**Eliminación de Código Duplicado:**
- `issue_tokens()` y `refresh_tokens()` comparten `JwtService.create_token_pair()`
- Validaciones centralizadas en `JwtPayload.__post_init__`

**Mejor Testabilidad:**
```python
def test_create_session():
    # Mock de dependencias
    mock_jwt_service = Mock(spec=JwtService)
    mock_repository = Mock(spec=SessionRepository)

    session_service = SessionService(mock_jwt_service, mock_repository)

    # Test aislado sin filesystem
    request = CreateSessionRequest(...)
    response = session_service.create_session(request)

    assert response.token_pair.access_token
    mock_jwt_service.create_token_pair.assert_called_once()
```

**Inmutabilidad Garantizada:**
- `JwtPayload` y `TokenPair` son `frozen=True`
- No hay forma de corromper el estado después de creación
- Validaciones en construcción (no en uso)

**Excepciones Específicas:**
- `TokenExpiredError` vs `TokenValidationError` vs `SessionExpiredError`
- Stack traces claros y debuggables
- Manejo de errores preciso

#### 23.12.8. Checklist de Migración a DDD

Antes de refactorizar código legacy a DDD:

- [ ] ¿Se importan Value Objects del dominio (`Jti`, `JwtPayload`, `TokenPair`)?
- [ ] ¿Se usa `JwtService` en lugar de `jwt.encode()`/`jwt.decode()`?
- [ ] ¿Se usa `SessionService` para toda lógica de sesiones?
- [ ] ¿Se implementa `SessionRepository` como adaptador?
- [ ] ¿Se inyectan dependencias en constructor (no variables globales)?
- [ ] ¿Se capturan excepciones específicas de los servicios?
- [ ] ¿Se eliminan manipulaciones directas de `sessions.json`?
- [ ] ¿Se mantienen las interfaces públicas existentes?
- [ ] ¿Se agregan tests con mocks?

#### 23.12.9. Archivos DDD

**Domain Layer:**
- `src/1_shared_domain/entities/session.py`
  - Value Objects: `Jti`, `JwtPayload`, `TokenPair`
  - Entidad: `Session`
  - Enums: `TokenType`, `JwtAlgorithm`, `SessionStatus`

**Application Layer:**
- `src/2_shared_application/services/jwt_service.py`
  - Servicio: `JwtService`
  - Config: `JwtSettings`
  - Excepciones: `JwtServiceError`, `TokenValidationError`, `TokenExpiredError`

- `src/2_shared_application/services/session_service.py`
  - Servicio: `SessionService`
  - DTOs: `CreateSessionRequest`, `SessionResponse`
  - Excepciones: `SessionServiceError`, `SessionNotFoundError`, `SessionExpiredError`, `InvalidTokenError`

- `src/2_shared_application/interfaces/session_repository.py`
  - Protocol: `SessionRepository`

**Regla #35**: SIEMPRE consultar estos archivos antes de modificar lógica de sesiones/JWT.

**Regla #36**: NUNCA duplicar lógica que ya existe en los servicios DDD.

#### 23.12.10. Documentación Completa

Para arquitectura DDD detallada, ver README.md sección "Arquitectura DDD para Gestión de Sesiones y JWT":

- Estructura de capas completa
- Diagramas de flujo (create_session, refresh_tokens, get_context)
- Ejemplos de uso
- Patrones aplicados (Value Object, Service Layer, Repository, DI)
- Principios SOLID

---

**⚠️ ADVERTENCIA FINAL**: Modificaciones incorrectas en este sistema pueden causar:
- Expulsión masiva de usuarios
- Pérdida de trabajo en operaciones largas
- Vulnerabilidades de seguridad
- Corrupción de `sessions.json`

**Siempre consultar con el equipo antes de modificar el sistema de sesiones.**

---

## 24. Estado de Proyectos - Domain-Driven Design Architecture

**DESCRIPCIÓN**: El sistema "Estado de Proyectos" es una implementación DDD completa que gestiona el ciclo de vida de versiones de modelos LLM a través de 5 fases interconectadas con validaciones automáticas a nivel de base de datos.

### 24.1. Arquitectura General DDD

```
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer (1_shared_domain)          │
│  - Entities: ProjectVersionState (Aggregate Root)           │
│  - Value Objects: ProposalPhase, TrainingPhase, etc.        │
│  - Enums: ExplorerState, StateInternal                      │
│  - Business Logic: Métodos de transición de estado          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer (2_shared_application)    │
│  - Service: ProjectVersionStateService                       │
│  - Repository Protocol: ProjectVersionStateRepository        │
│  - DTOs: UpdateProposalPhaseDto, PhaseDetailsDto, etc.      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Layer (2_shared_application)     │
│  - Adapter: MariaDBProjectVersionStateRepository             │
│  - Database: estado_version table (24 nuevos campos)        │
│  - Triggers: 6 triggers automáticos (sincronización, etc.)  │
└─────────────────────────────────────────────────────────────┘
```

### 24.2. Ciclo de Vida de 5 Fases

Cada versión de modelo LLM pasa por 5 fases obligatorias:

| Fase | Campos DB | Estados Internos | Transiciones |
|------|-----------|------------------|--------------|
| **1. Propuesta** | `final_c`, `final_i` | `propuesta_cliente`, `revision_interna`, `propuesta_aprobada` | Cliente/Interno aprueban |
| **2. Entrenamiento** | `entrenamiento_inicial_solicitado`, `entrenamiento_inicial_completado` | `entrenamiento_inicial`, `entrenamiento_completado` | Trigger auto → Trainer completa |
| **3. Evaluación** | `control_calidad_aprobado` | `control_calidad` | Editor/SuperAdmin aprueba |
| **4. Generación** | `generacion_llm_solicitada`, `generacion_llm_completada` | `generacion_llm`, `generacion_completada` | Trigger auto → Trainer completa |
| **5. Notificación** | `notificacion_descarga_enviada` | `notificacion_descarga` | Backend Core envía email |

**Regla #1**: Las fases DEBEN ejecutarse en orden secuencial - no se puede saltar de Propuesta a Evaluación.

**Regla #2**: `state_internal` se actualiza AUTOMÁTICAMENTE mediante triggers (ver 24.6).

### 24.3. Entidades y Value Objects (Domain Layer)

#### 24.3.1. Aggregate Root: ProjectVersionState

**Ubicación**: `/src/1_shared_domain/entities/project_version_state.py`

```python
@dataclass
class ProjectVersionState:
    """Aggregate Root - Gestiona todo el ciclo de vida de una versión."""
    id: int
    organization_id: int
    project_id: int
    version_id: int
    state: ExplorerState  # Estado explorer (visible en UI)
    state_internal: StateInternal  # Estado interno (15 opciones)

    # Value Objects para cada fase
    proposal: ProposalPhase
    training: TrainingPhase
    evaluation: EvaluationPhase
    generation: GenerationPhase
    notification: NotificationPhase

    updated_by: int | None = None
    updated_at: datetime | None = None
```

**Regla #3**: `ProjectVersionState` es el ÚNICO punto de entrada para modificar el estado de una versión.

**Regla #4**: Toda la lógica de negocio está en los métodos del Aggregate Root o Value Objects.

#### 24.3.2. Value Objects (Inmutables)

**ProposalPhase** (`@dataclass(frozen=True)`):
```python
@dataclass(frozen=True)
class ProposalPhase:
    propuesta_cliente: bool = True
    revision_interna: bool = False

    def approve_by_client(self, user_id: int) -> ProposalPhase:
        """Retorna NUEVO objeto con propuesta_cliente=True."""
        return ProposalPhase(
            propuesta_cliente=True,
            revision_interna=self.revision_interna,
        )

    def approve_by_internal(self, user_id: int) -> ProposalPhase:
        """Retorna NUEVO objeto con revision_interna=True."""
        return ProposalPhase(
            propuesta_cliente=self.propuesta_cliente,
            revision_interna=True,
        )
```

**Regla #5**: Los Value Objects son **inmutables** (`frozen=True`).

**Regla #6**: Los métodos de Value Objects SIEMPRE retornan un NUEVO objeto (no modifican `self`).

**Regla #7**: Los métodos de transición reciben `user_id` para auditoría.

**TrainingPhase**, **EvaluationPhase**, **GenerationPhase**, **NotificationPhase**:
- Misma estructura inmutable
- Métodos específicos para cada fase (`request_training()`, `complete_training()`, etc.)
- Campos booleanos que mapean a columnas DB

### 24.4. Application Service

**Ubicación**: `/src/2_shared_application/services/project_version_state_service.py`

```python
class ProjectVersionStateService:
    """Servicio de aplicación - orquesta entidades y repositorio."""

    def __init__(self, repository: ProjectVersionStateRepository):
        self._repository = repository

    def approve_proposal_by_client(
        self,
        state_id: int,
        user_id: int,
        identity_type_id: int,
    ) -> ProjectVersionState:
        """Aprueba propuesta por cliente (validando permisos)."""
        # 1. Validar permisos
        if identity_type_id not in (1, 2, 3):  # SuperAdmin, Admin, Editor
            raise PermissionError("Sin permisos para aprobar propuesta")

        # 2. Obtener entidad
        state = self._repository.get_by_id(state_id)
        if not state:
            raise ValueError("Estado no encontrado")

        # 3. Delegar lógica de negocio a la entidad
        updated_proposal = state.proposal.approve_by_client(user_id)
        state.proposal = updated_proposal
        state.updated_by = user_id
        state.updated_at = datetime.now(timezone.utc)

        # 4. Persistir
        return self._repository.save(state)
```

**Regla #8**: El Service SOLO orquesta - NO contiene lógica de negocio.

**Regla #9**: El Service valida permisos ANTES de delegar a la entidad.

**Regla #10**: El Service usa el Repository para persistencia (nunca SQL directo).

### 24.5. Repository Pattern

#### 24.5.1. Protocol (Interfaz)

**Ubicación**: `/src/2_shared_application/interfaces/project_version_state_repository.py`

```python
from typing import Protocol

class ProjectVersionStateRepository(Protocol):
    """Interfaz del repositorio - permite múltiples implementaciones."""

    def get_by_id(self, state_id: int) -> ProjectVersionState | None:
        """Obtiene estado por ID."""
        ...

    def save(self, state: ProjectVersionState) -> ProjectVersionState:
        """Guarda estado (INSERT o UPDATE)."""
        ...

    def list_by_project(self, project_id: int) -> list[ProjectVersionState]:
        """Lista estados por proyecto."""
        ...
```

**Regla #11**: NUNCA acceder directamente a la base de datos desde el Service.

**Regla #12**: El Repository abstrae la persistencia - permite cambiar de MariaDB a PostgreSQL sin tocar el Service.

#### 24.5.2. Implementación MariaDB

**Ubicación**: `/src/2_shared_application/adapters/mariadb_project_version_state_repository.py`

```python
class MariaDBProjectVersionStateRepository:
    """Implementación del Repository para MariaDB."""

    def __init__(self, engine: Engine):
        self._engine = engine

    def get_by_id(self, state_id: int) -> ProjectVersionState | None:
        """Convierte row SQL a entidad de dominio."""
        with self._engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM estado_version WHERE id = :id
            """), {"id": state_id})
            row = result.fetchone()

            if not row:
                return None

            return self._row_to_entity(row)

    def _row_to_entity(self, row) -> ProjectVersionState:
        """Construye Value Objects desde row SQL."""
        proposal = ProposalPhase(
            propuesta_cliente=bool(row.final_c),
            revision_interna=bool(row.final_i),
        )
        training = TrainingPhase(
            entrenamiento_solicitado=bool(row.entrenamiento_inicial_solicitado),
            entrenamiento_completado=bool(row.entrenamiento_inicial_completado),
        )
        # ... construir otros Value Objects

        return ProjectVersionState(
            id=row.id,
            proposal=proposal,
            training=training,
            # ...
        )
```

**Regla #13**: `_row_to_entity()` DEBE construir todos los Value Objects correctamente.

**Regla #14**: `save()` DEBE actualizar TODOS los campos de las 5 fases.

### 24.6. Database Triggers (Automatización Crítica)

**Ubicación**: `/infrastructure/database/migrations/009_estado_triggers.sql`

El sistema tiene 6 triggers automáticos que DEBEN entenderse:

#### 24.6.1. Trigger de Auto-Entrenamiento

```sql
CREATE TRIGGER trg_estado_version_auto_entrenamiento
BEFORE UPDATE ON estado_version
FOR EACH ROW
BEGIN
    -- Si ambas aprobaciones están activadas, solicitar entrenamiento
    IF NEW.final_c = 1 AND NEW.final_i = 1 THEN
        SET NEW.entrenamiento_inicial_solicitado = 1;
    END IF;

    -- Si alguna aprobación se revoca, cancelar entrenamiento
    IF NEW.final_c = 0 OR NEW.final_i = 0 THEN
        SET NEW.entrenamiento_inicial_solicitado = 0;
        SET NEW.entrenamiento_inicial_completado = 0;
    END IF;
END
```

**Regla #15**: NO intentar activar `entrenamiento_inicial_solicitado` manualmente - el trigger lo hace.

**Regla #16**: Revocar `final_c` o `final_i` RESETEA automáticamente el entrenamiento.

#### 24.6.2. Trigger de Auto-Generación

```sql
CREATE TRIGGER trg_estado_version_auto_generacion
BEFORE UPDATE ON estado_version
FOR EACH ROW
BEGIN
    -- Si control de calidad aprobado, solicitar generación
    IF NEW.control_calidad_aprobado = 1 THEN
        SET NEW.generacion_llm_solicitada = 1;
    END IF;

    -- Si se revoca control de calidad, cancelar generación
    IF NEW.control_calidad_aprobado = 0 THEN
        SET NEW.generacion_llm_solicitada = 0;
        SET NEW.generacion_llm_completada = 0;
    END IF;
END
```

**Regla #17**: La generación LLM se dispara AUTOMÁTICAMENTE al aprobar control de calidad.

#### 24.6.3. Trigger de Sincronización estado_internal

```sql
CREATE TRIGGER trg_estado_version_sync_state_internal
BEFORE UPDATE ON estado_version
FOR EACH ROW
BEGIN
    DECLARE new_state_internal VARCHAR(50);

    -- Lógica de prioridad (de más específico a más general)
    IF NEW.notificacion_descarga_enviada = 1 THEN
        SET new_state_internal = 'notificacion_descarga';
    ELSEIF NEW.generacion_llm_completada = 1 THEN
        SET new_state_internal = 'generacion_completada';
    ELSEIF NEW.generacion_llm_solicitada = 1 THEN
        SET new_state_internal = 'generacion_llm';
    -- ... más condiciones
    ELSEIF NEW.final_c = 1 AND NEW.final_i = 0 THEN
        SET new_state_internal = 'revision_interna';
    ELSE
        SET new_state_internal = 'propuesta_cliente';
    END IF;

    SET NEW.state_internal = new_state_internal;
END
```

**Regla #18**: `state_internal` se calcula AUTOMÁTICAMENTE - NUNCA modificarlo manualmente.

**Regla #19**: La prioridad va de fases finales a iniciales (notificación > generación > evaluación > entrenamiento > propuesta).

#### 24.6.4. Trigger de Updated At

```sql
CREATE TRIGGER trg_estado_version_updated_at
BEFORE UPDATE ON estado_version
FOR EACH ROW
BEGIN
    SET NEW.updated_at = NOW();
END
```

**Regla #20**: `updated_at` se actualiza AUTOMÁTICAMENTE en cada UPDATE.

#### 24.6.5. Trigger de Sincronización con estado (legacy)

```sql
CREATE TRIGGER trg_estado_version_sync_estado
AFTER UPDATE ON estado_version
FOR EACH ROW
BEGIN
    UPDATE estado
    SET
        estado_propuesta = IF(NEW.final_c = 1 AND NEW.final_i = 1, TRUE, FALSE),
        estado_entrenamiento = IF(NEW.entrenamiento_inicial_completado = 1, TRUE, FALSE),
        estado_control_calidad = IF(NEW.control_calidad_aprobado = 1, TRUE, FALSE),
        estado_generacion_llm = IF(NEW.generacion_llm_completada = 1, TRUE, FALSE),
        estado_notificacion_descarga = IF(NEW.notificacion_descarga_enviada = 1, TRUE, FALSE)
    WHERE id_proyecto = NEW.id_proyecto AND id_version = NEW.id_version;
END
```

**Regla #21**: La tabla `estado` (legacy) se sincroniza AUTOMÁTICAMENTE desde `estado_version`.

**Regla #22**: NO escribir directamente a `estado` - usar `estado_version` como fuente de verdad.

### 24.7. API Endpoints (Backend Core)

**Ubicación**: `/src/apps/3_backend/apicore.py`

#### 24.7.1. Estructura de Endpoints

```python
# GET - Obtener estado completo
@app.get("/project-version-states/{state_id}")
def get_state_endpoint(
    state_id: int,
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Retorna estado completo con las 5 fases."""
    return router.get_project_version_state(state_id, user_id, identity_type_id)


# PATCH - Actualizar fase de propuesta
@app.patch("/project-version-states/{state_id}/proposal")
def update_proposal_phase_endpoint(
    state_id: int,
    payload: UpdateProposalPhaseDto,
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Actualiza aprobaciones de cliente e interna."""
    return router.update_proposal_phase(
        state_id=state_id,
        aceptacion_cliente=payload.aceptacion_cliente,
        aceptacion_interna=payload.aceptacion_interna,
        user_id=user_id,
        identity_type_id=identity_type_id,
    )


# PATCH - Actualizar fase de evaluación
@app.patch("/project-version-states/{state_id}/evaluation")
def update_evaluation_phase_endpoint(
    state_id: int,
    payload: UpdateEvaluationPhaseDto,
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Actualiza control de calidad."""
    return router.update_evaluation_phase(...)
```

**Regla #23**: Cada fase tiene su propio endpoint PATCH (`/proposal`, `/training`, `/evaluation`, `/generation`, `/notification`).

**Regla #24**: Los endpoints reciben `user_id` e `identity_type_id` para auditoría y permisos.

#### 24.7.2. DTOs de Request

**Ubicación**: `/src/apps/3_backend/apicore.py` (al inicio del archivo)

```python
class UpdateProposalPhaseDto(BaseModel):
    """DTO para actualizar fase de propuesta."""
    aceptacion_cliente: bool
    aceptacion_interna: bool


class UpdateEvaluationPhaseDto(BaseModel):
    """DTO para actualizar fase de evaluación."""
    control_calidad_aprobado: bool


# ... otros DTOs para Training, Generation, Notification
```

**Regla #25**: Los DTOs usan Pydantic v2 para validación automática.

**Regla #26**: Los nombres de campos en DTOs deben ser descriptivos (no abreviaturas).

### 24.8. Propagación a través de Capas

```
Backoffice UI → Middleware → Broker → Backend Core
     (Reflex)      (apife.py)  (apibe.py)  (apicore.py)
```

#### 24.8.1. Middleware Layer

**Archivos**:
- `/src/apps/7_service_frontend/routermiddleware.py`: Métodos del router
- `/src/apps/7_service_frontend/broker_backend_client.py`: Cliente HTTP al Broker
- `/src/apps/7_service_frontend/apife.py`: Endpoints FastAPI

**Patrón**: Propagación transparente de headers (`Authorization`, `X-Session-Token`).

```python
# En routermiddleware.py
def update_proposal_phase(
    self,
    state_id: int,
    aceptacion_cliente: bool,
    aceptacion_interna: bool,
) -> dict[str, Any]:
    """Delega al broker."""
    return self._broker_client.update_proposal_phase(
        state_id, aceptacion_cliente, aceptacion_interna
    )
```

**Regla #27**: Middleware NO valida permisos - solo propaga headers al Broker.

#### 24.8.2. Broker Layer

**Archivos**:
- `/src/apps/8_service_backend/routerbroker.py`: Métodos del router
- `/src/apps/8_service_backend/interfacetocore.py`: Cliente HTTP al Backend Core
- `/src/apps/8_service_backend/apibe.py`: Endpoints FastAPI

**Patrón**: Igual que Middleware - propagación transparente.

**Regla #28**: Broker NO valida permisos - confía en Backend Core.

#### 24.8.3. Backend Core (Validación de Permisos)

**Archivo**: `/src/apps/3_backend/routercore.py`

```python
def update_proposal_phase(
    self,
    state_id: int,
    aceptacion_cliente: bool,
    aceptacion_interna: bool,
    user_id: int,
    identity_type_id: int,
) -> dict[str, Any]:
    """Actualiza fase de propuesta (con validación de permisos)."""
    # 1. Validar permisos
    if identity_type_id not in (1, 2, 3):  # SuperAdmin, Admin, Editor
        raise BackendCorePermissionError(
            "Sin permisos para aprobar propuesta",
            identity_type_id,
        )

    # 2. Usar Service para aplicar cambios
    service = ProjectVersionStateService(self._repository)
    updated_state = service.approve_proposal_by_client(
        state_id, user_id, identity_type_id
    )

    # 3. Convertir entidad a dict para respuesta
    return self._state_to_dict(updated_state)
```

**Regla #29**: Backend Core es el ÚNICO lugar donde se validan permisos.

**Regla #30**: Backend Core usa el Service DDD (no SQL directo).

### 24.9. Backoffice UI (Reflex)

**Ubicación**: `/src/apps/6_web_backoffice/pages/estado_proyectos.py`

#### 24.9.1. State Class

```python
class EstadoProyectosState(rx.State):
    """Estado de Reflex para gestión de estado de proyectos."""

    # Contexto del usuario
    user_id: int
    organization_id: int
    identity_type_id: int

    # Selección
    selected_org_id: int
    selected_project_id: int
    selected_version_id: int

    # Estado actual
    current_state: dict[str, Any]

    @rx.var
    def can_edit(self) -> bool:
        """Computed property - puede editar si es SuperAdmin/Admin/Editor."""
        if self.identity_type_id == 1:  # SuperAdmin
            return True
        if self.identity_type_id in (4, 5):  # Auditor, Lector
            return False
        return True  # Admin, Editor

    def toggle_field(self, field_name: str):
        """Alterna valor de un campo booleano."""
        from adapters.api_client import update_proposal_phase

        current_value = self.current_state.get(field_name, False)

        # Determinar qué fase actualizar
        if field_name in ("final_c", "final_i"):
            # Actualizar fase de propuesta
            result = update_proposal_phase(
                state_id=self.current_state["id"],
                aceptacion_cliente=(field_name == "final_c" and not current_value),
                aceptacion_interna=(field_name == "final_i" and not current_value),
                access_token=self.access_token,
                session_token=self.session_token,
            )
        # ... manejar otras fases

        # Recargar estado
        self.load_current_state()
```

**Regla #31**: La UI usa `computed properties` (@rx.var) para permisos.

**Regla #32**: Los cambios se hacen vía API client (NUNCA SQL directo desde Reflex).

#### 24.9.2. UI Components

```python
def proposal_phase_card(state: EstadoProyectosState) -> rx.Component:
    """Card para la fase de propuesta."""
    return rx.box(
        rx.heading("Fase 1: Propuesta", size="5"),

        # Aprobación del cliente
        rx.hstack(
            rx.switch(
                checked=state.current_state["final_c"],
                on_change=lambda: state.toggle_field("final_c"),
                disabled=~state.can_edit,  # Deshabilitado si no puede editar
            ),
            rx.text("Aprobación del Cliente"),
        ),

        # Revisión interna
        rx.hstack(
            rx.switch(
                checked=state.current_state["final_i"],
                on_change=lambda: state.toggle_field("final_i"),
                disabled=~state.can_edit,
            ),
            rx.text("Revisión Interna"),
        ),

        # Indicador de estado interno
        rx.badge(
            state.current_state["state_internal"],
            color_scheme=_get_color_for_state(state.current_state["state_internal"]),
        ),

        padding="1em",
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
    )
```

**Regla #33**: Los switches deben estar deshabilitados (`disabled`) si el usuario no tiene permisos.

**Regla #34**: Mostrar `state_internal` con badges de colores para visualización.

### 24.10. Control de Permisos

| Rol | identity_type_id | Puede aprobar propuesta | Puede aprobar control calidad | Puede ver estados |
|-----|------------------|------------------------|-------------------------------|-------------------|
| **SuperAdmin** | 1 | ✅ | ✅ | ✅ |
| **Admin** | 2 | ✅ | ✅ | ✅ |
| **Editor** | 3 | ✅ | ✅ | ✅ |
| **Auditor** | 4 | ❌ | ❌ | ✅ (solo lectura) |
| **Lector** | 5 | ❌ | ❌ | ✅ (solo lectura) |

**Regla #35**: Validar permisos en Backend Core ANTES de aplicar cambios.

**Regla #36**: Usar `BackendCorePermissionError` para errores de permisos.

### 24.11. Testing Guidelines

#### 24.11.1. Tests de Domain Layer

```python
# tests/domain/test_project_version_state.py

def test_proposal_phase_approve_by_client():
    """Test Value Object inmutable."""
    phase = ProposalPhase(propuesta_cliente=False, revision_interna=False)

    # Aprobar por cliente retorna NUEVO objeto
    approved = phase.approve_by_client(user_id=1)

    assert approved.propuesta_cliente is True
    assert approved.revision_interna is False

    # Original NO se modifica (inmutabilidad)
    assert phase.propuesta_cliente is False
```

**Regla #37**: Tests de Value Objects verifican inmutabilidad.

#### 24.11.2. Tests de Application Service

```python
# tests/application/test_project_version_state_service.py

def test_approve_proposal_validates_permissions():
    """Test que Service valida permisos."""
    mock_repo = Mock(spec=ProjectVersionStateRepository)
    service = ProjectVersionStateService(mock_repo)

    with pytest.raises(PermissionError):
        service.approve_proposal_by_client(
            state_id=1,
            user_id=10,
            identity_type_id=5,  # Lector - sin permisos
        )
```

**Regla #38**: Tests de Service usan mocks del Repository (no base de datos real).

#### 24.11.3. Tests de Repository

```python
# tests/infrastructure/test_mariadb_repository.py

def test_row_to_entity_conversion():
    """Test conversión de row SQL a entidad."""
    mock_row = Mock(
        id=1,
        final_c=1,
        final_i=0,
        entrenamiento_inicial_solicitado=1,
        # ... todos los campos
    )

    repo = MariaDBProjectVersionStateRepository(engine)
    entity = repo._row_to_entity(mock_row)

    assert isinstance(entity, ProjectVersionState)
    assert entity.proposal.propuesta_cliente is True
    assert entity.proposal.revision_interna is False
```

**Regla #39**: Tests de Repository verifican conversión row ↔ entity.

### 24.12. Migrations y Database Schema

#### 24.12.1. Extensión de estado_version

**Archivo**: `/infrastructure/database/migrations/008_estado_version_extension.sql`

**Campos añadidos** (24 nuevos):

```sql
ALTER TABLE estado_version
-- Control de estado interno
ADD COLUMN IF NOT EXISTS state_internal VARCHAR(50) DEFAULT 'propuesta_cliente',

-- Fase 1: Propuesta
ADD COLUMN IF NOT EXISTS final_c TINYINT(1) DEFAULT 0,
ADD COLUMN IF NOT EXISTS final_i TINYINT(1) DEFAULT 0,

-- Fase 2: Entrenamiento
ADD COLUMN IF NOT EXISTS entrenamiento_inicial_solicitado TINYINT(1) DEFAULT 0,
ADD COLUMN IF NOT EXISTS entrenamiento_inicial_completado TINYINT(1) DEFAULT 0,

-- Fase 3: Evaluación
ADD COLUMN IF NOT EXISTS control_calidad_aprobado TINYINT(1) DEFAULT 0,

-- Fase 4: Generación LLM
ADD COLUMN IF NOT EXISTS generacion_llm_solicitada TINYINT(1) DEFAULT 0,
ADD COLUMN IF NOT EXISTS generacion_llm_completada TINYINT(1) DEFAULT 0,

-- Fase 5: Notificación
ADD COLUMN IF NOT EXISTS notificacion_descarga_enviada TINYINT(1) DEFAULT 0,

-- Auditoría
ADD COLUMN IF NOT EXISTS updated_by INT NULL,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL,

-- Campos adicionales para tracking
ADD COLUMN IF NOT EXISTS fecha_entrenamiento_inicio TIMESTAMP NULL,
ADD COLUMN IF NOT EXISTS fecha_entrenamiento_fin TIMESTAMP NULL,
ADD COLUMN IF NOT EXISTS fecha_control_calidad TIMESTAMP NULL,
ADD COLUMN IF NOT EXISTS fecha_generacion_inicio TIMESTAMP NULL,
ADD COLUMN IF NOT EXISTS fecha_generacion_fin TIMESTAMP NULL,
ADD COLUMN IF NOT EXISTS fecha_notificacion TIMESTAMP NULL,
ADD COLUMN IF NOT EXISTS url_descarga VARCHAR(512) NULL,
ADD COLUMN IF NOT EXISTS tamano_modelo_mb DECIMAL(10,2) NULL,
ADD COLUMN IF NOT EXISTS metricas_calidad JSON NULL,
ADD COLUMN IF NOT EXISTS logs_entrenamiento TEXT NULL,
ADD COLUMN IF NOT EXISTS notas_internas TEXT NULL;
```

**Regla #40**: NO eliminar estos campos - son parte integral del sistema.

**Regla #41**: Los campos `fecha_*` se actualizan desde Backend IA (Trainer) cuando completa tareas.

#### 24.12.2. Triggers

**Archivo**: `/infrastructure/database/migrations/009_estado_triggers.sql`

**Triggers creados** (6):
1. `trg_estado_version_auto_entrenamiento` - Dispara entrenamiento al aprobar propuesta
2. `trg_estado_version_auto_generacion` - Dispara generación al aprobar control calidad
3. `trg_estado_version_sync_state_internal` - Sincroniza state_internal automáticamente
4. `trg_estado_version_updated_at` - Actualiza updated_at en cada UPDATE
5. `trg_estado_version_sync_estado` - Sincroniza con tabla estado (legacy)
6. `trg_estado_version_validate_transitions` - Valida transiciones de estado (opcional)

**Regla #42**: NO modificar triggers sin entender el impacto en TODA la cadena de estados.

**Regla #43**: Al hacer debugging, revisar triggers ANTES de buscar errores en código Python.

### 24.13. Data Flow Completo

```
┌────────────────────────────────────────────────────────────────┐
│ 1. Usuario aprueba propuesta en Backoffice (toggle switch)    │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│ 2. API call: PATCH /project-version-states/{id}/proposal      │
│    Middleware → Broker → Backend Core                         │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│ 3. Backend Core valida permisos (identity_type_id)            │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│ 4. Service llama a entidad: state.proposal.approve_by_client()│
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│ 5. Repository persiste: UPDATE estado_version SET final_c=1   │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│ 6. TRIGGER detecta: final_c=1 AND final_i=1                   │
│    → SET entrenamiento_inicial_solicitado=1                   │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│ 7. TRIGGER sincroniza: state_internal='entrenamiento_inicial' │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│ 8. TRIGGER actualiza: updated_at=NOW()                        │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│ 9. TRIGGER sincroniza tabla estado (legacy) automáticamente   │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│ 10. Backend IA (Trainer) detecta entrenamiento_solicitado=1   │
│     (polling cada 5 minutos)                                   │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│ 11. Trainer ejecuta entrenamiento y actualiza:                │
│     UPDATE estado_version SET                                  │
│         entrenamiento_inicial_completado=1,                    │
│         fecha_entrenamiento_fin=NOW(),                         │
│         logs_entrenamiento='...'                               │
└────────────────────────────────────────────────────────────────┘
```

**Regla #44**: Entender el flujo completo ANTES de modificar cualquier parte.

### 24.14. Archivos Críticos del Sistema

| Archivo | Líneas | Propósito | Capa |
|---------|--------|-----------|------|
| `src/1_shared_domain/entities/project_version_state.py` | ~850 | Entidades y Value Objects | Domain |
| `src/2_shared_application/services/project_version_state_service.py` | ~400 | Application Service | Application |
| `src/2_shared_application/adapters/mariadb_project_version_state_repository.py` | ~670 | Repository MariaDB | Infrastructure |
| `src/apps/3_backend/apicore.py` | ~300 (nuevas líneas) | API endpoints | API |
| `src/apps/6_web_backoffice/pages/estado_proyectos.py` | ~850 | Backoffice UI | UI |
| `infrastructure/database/migrations/008_estado_version_extension.sql` | ~150 | Schema extension | Database |
| `infrastructure/database/migrations/009_estado_triggers.sql` | ~350 | Database triggers | Database |

**Regla #45**: Consultar SIEMPRE estos archivos antes de modificar el sistema Estado de Proyectos.

### 24.15. Common Pitfalls (Errores Comunes)

#### 24.15.1. Modificar state_internal manualmente

```python
# ❌ INCORRECTO
UPDATE estado_version SET state_internal = 'generacion_llm' WHERE id = 1;

# ✅ CORRECTO
# state_internal se actualiza AUTOMÁTICAMENTE mediante trigger
# Solo actualizar los campos de las fases (final_c, control_calidad_aprobado, etc.)
UPDATE estado_version SET control_calidad_aprobado = 1 WHERE id = 1;
```

#### 24.15.2. Saltar validación de permisos

```python
# ❌ INCORRECTO - SQL directo desde UI
def toggle_field(self, field_name: str):
    execute_sql(f"UPDATE estado_version SET {field_name} = 1 WHERE id = ...")

# ✅ CORRECTO - Usar API con permisos
def toggle_field(self, field_name: str):
    api_client.update_proposal_phase(
        state_id=...,
        access_token=self.access_token,  # Headers con permisos
        session_token=self.session_token,
    )
```

#### 24.15.3. Mutar Value Objects

```python
# ❌ INCORRECTO - Intentar mutar objeto frozen
phase = ProposalPhase(propuesta_cliente=False, revision_interna=False)
phase.propuesta_cliente = True  # ERROR: dataclass is frozen

# ✅ CORRECTO - Crear nuevo objeto
phase = ProposalPhase(propuesta_cliente=False, revision_interna=False)
updated_phase = phase.approve_by_client(user_id=1)  # Retorna NUEVO objeto
```

#### 24.15.4. Olvidar triggers al hacer cambios

```python
# ❌ INCORRECTO - Esperar que entrenamiento se active manualmente
UPDATE estado_version SET entrenamiento_inicial_solicitado = 1;

# ✅ CORRECTO - Activar aprobaciones y dejar que trigger lo haga
UPDATE estado_version SET final_c = 1, final_i = 1;
# Trigger automáticamente: entrenamiento_inicial_solicitado = 1
```

### 24.16. Debugging Checklist

Cuando debuggear problemas con Estado de Proyectos:

1. [ ] Verificar que los triggers están creados: `SHOW TRIGGERS FROM myllm_projects_db;`
2. [ ] Revisar logs de Backend Core: `/data/backend_core/logs/`
3. [ ] Verificar permisos del usuario: `SELECT identity_type_id FROM users WHERE user_id = ?`
4. [ ] Inspeccionar `state_internal` vs campos de fases (deben ser coherentes)
5. [ ] Revisar `updated_by` y `updated_at` para auditoría
6. [ ] Verificar sincronización con tabla `estado`: `SELECT * FROM estado WHERE id_proyecto = ?`
7. [ ] Revisar que Repository convierte correctamente row → entity
8. [ ] Verificar que Value Objects son inmutables (frozen=True)
9. [ ] Comprobar que Service valida permisos ANTES de delegar a entidad
10. [ ] Revisar que UI desactiva switches si usuario no tiene permisos

### 24.17. Documentación Relacionada

- **README.md** - Sección "Estado de Proyectos (Project Status Management)" con:
  - Arquitectura DDD detallada
  - Diagramas de flujo de las 5 fases
  - Esquema de base de datos
  - API endpoints completos
  - Permisos por rol
  - Descripción de UI
  - Data flow diagrams

- **Database Migrations**:
  - `008_estado_version_extension.sql` - Extensión de schema
  - `009_estado_triggers.sql` - Triggers automáticos

- **Tests** (pendiente de implementación):
  - `tests/domain/test_project_version_state.py`
  - `tests/application/test_project_version_state_service.py`
  - `tests/infrastructure/test_mariadb_repository.py`

---

**⚠️ ADVERTENCIA CRÍTICA**: El sistema Estado de Proyectos gestiona el ciclo de vida completo de generación de modelos LLM. Modificaciones incorrectas pueden:
- Disparar entrenamientos no solicitados (costosos en recursos GPU)
- Corromper el estado de versiones en producción
- Romper sincronización entre `estado_version` y `estado` (legacy)
- Causar inconsistencias en triggers automáticos
- Bloquear workflows de clientes

**Regla #46 (OBLIGATORIA)**: NUNCA modificar triggers, schema o Value Objects sin:
1. Entender el flujo completo de las 5 fases
2. Revisar impacto en sincronización con tabla `estado`
3. Consultar documentación en README.md
4. Crear tests que validen el cambio
5. Obtener aprobación del equipo

**Para modificaciones mayores, consultar primero la documentación completa en README.md sección "Estado de Proyectos".**

---

## 25. Gestión de Estados de Versiones en Explorador

**DESCRIPCIÓN**: El sistema de gestión de estados de versiones controla el ciclo de vida de las versiones en el explorador con flujos diferenciados para clientes (frontend) y usuarios internos (backoffice). Implementa "Security by Design" con estados terminales y protección automática.

### 25.1. Estados Disponibles

| Estado | Vista Frontend | Vista Backoffice | Campos DB | Descripción |
|--------|---------------|------------------|-----------|-------------|
| **Abierta** | (Abierta) - Verde | (Abierta) - Verde | `state="Abierta"`, `protected=false`, `final_c=false`, `final_i=false` | Versión en desarrollo activo. Cliente y equipo pueden modificar. |
| **Bloqueada** | (Bloqueada) - Naranja | (Bloqueada) - Naranja | `state="Bloqueada"`, `protected=true`, `final_c=false`, `final_i=false` | Versión temporalmente bloqueada. Solo lectura. |
| **Entrenar** | (Entrenamiento solicitado) - Azul | (Entrenamiento solicitado) - Azul | `state="Entrenar"`, `protected=true`, `final_c=true`, `final_i=false` | Cliente solicita entrenamiento. Terminal para cliente. |
| **Final** | (Final) - Rojo | (Final) - Rojo | `state="Final"`, `protected=true`, `final_c=true`, `final_i=true` | Versión confirmada por backoffice. Trigger automático activa entrenamiento. |

### 25.2. Flujos de Estado

#### 25.2.1. Frontend (Cliente)

```
Abierta ⟷ Bloqueada → Entrenar (TERMINAL)
    ↑                     ↓
    └─── (Solo Backoffice puede cambiar)
```

**Reglas:**
- Cliente puede cambiar entre "Abierta" y "Bloqueada" libremente
- Cliente puede solicitar "Entrenar" desde cualquier estado
- Una vez en "Entrenar", el cliente NO puede cambiar el estado
- Para cambios posteriores, debe contactar por notificaciones o tickets

#### 25.2.2. Backoffice (Usuario Interno)

```
Abierta ⟷ Bloqueada ⟷ Entrenar ⟷ Final
    ↑                              ↓
    └────────────────────────────────┘
(Puede cambiar entre TODOS los estados)
```

**Reglas:**
- Backoffice puede cambiar entre cualquier estado
- Permite deshacer estados terminales del cliente
- Responsable de confirmar versiones con estado "Final"

### 25.3. Registro Automático en Tabla `cambios`

**Ubicación**: `src/apps/3_backend/routercore.py:update_version_state()`

Todos los cambios de estado se registran automáticamente en la tabla `cambios`:

```python
# Mapeo de estados a registros
state_mapping = {
    "Abierta": {
        "tipo": "Abrir",
        "descripcion": "Versión v001 del proyecto 'Proyecto X' abierta para edición"
    },
    "Bloqueada": {
        "tipo": "Bloquear",
        "descripcion": "Versión v001 del proyecto 'Proyecto X' bloqueada temporalmente"
    },
    "Entrenar": {
        "tipo": "Entrenar",
        "descripcion": "El cliente solicita entrenamiento para versión v001 del proyecto 'Proyecto X'"
    },
    "Final": {
        "tipo": "Finalizar",
        "descripcion": "Versión v001 del proyecto 'Proyecto X' lista para entrenar"
    }
}
```

**Beneficios**:
- Trazabilidad completa de cambios de estado
- Visible en componente Calendario (frontend y backoffice)
- Incluye nombre de proyecto y versión para contexto
- Auditoría automática sin código adicional

### 25.4. Protección Automática (Security by Design)

Cuando `protected=true` (estados Bloqueada, Entrenar, Final):

**En Explorador:**
1. Todos los descendientes de la versión se marcan como `is_blocked=true`
2. Menús contextuales desaparecen en elementos bloqueados
3. Opacidad reducida (`opacity: 0.5`) para feedback visual
4. Solo lectura en todos los archivos y carpetas

**Excepción:**
- La carpeta de versión MISMA no se bloquea
- Permite acceso al menú contextual para cambiar estado
- Solo aplica a contenido dentro de la versión

### 25.5. Trigger Automático de Entrenamiento

**Ubicación**: `infrastructure/database/migrations/009_estado_triggers.sql`

```sql
CREATE TRIGGER trg_estado_version_auto_entrenamiento
AFTER UPDATE ON version_states
FOR EACH ROW
BEGIN
    IF NEW.final_c = 1 AND NEW.final_i = 1 THEN
        SET NEW.entrenamiento_inicial_solicitado = 1;
    END IF;
END;
```

**Funcionamiento:**
- Se activa cuando `final_c=1 AND final_i=1` (estado "Final")
- Automáticamente actualiza `entrenamiento_inicial_solicitado=1`
- Sistema de entrenamiento detecta versiones con esta flag
- Inicia proceso de fine-tuning del modelo LLM

### 25.6. Implementación en Frontend

**Archivo**: `src/apps/5_web_frontend/components/explorador.py`

#### 25.6.1. Labels de Estado

```python
state_labels = {
    "Abierta": ("(Abierta)", "#228B22"),  # Verde bosque
    "Bloqueada": ("(Bloqueada)", "#FF8C00"),  # Naranja oscuro
    "Entrenar": ("(Entrenamiento solicitado)", "#00008B"),  # Azul oscuro
    "Final": ("(Final)", "#8B0000"),  # Rojo oscuro
}
```

#### 25.6.2. Métodos de Cambio de Estado

```python
# Línea 546
def abrir_version(self, item: FolderItem):
    """Cambia estado a Abierta (protected=False)."""
    update_version_state(
        project_id=self.id_proyecto,
        version_id=version_id,
        state="Abierta",
        protected=False,
        updated_by_user_id=self.user_id
    )

# Línea 589
def bloquear_version(self, item: FolderItem):
    """Cambia estado a Bloqueada (protected=True)."""
    update_version_state(
        project_id=self.id_proyecto,
        version_id=version_id,
        state="Bloqueada",
        protected=True,
        updated_by_user_id=self.user_id
    )

# Línea 631 (NUEVO)
def entrenar_version(self, item: FolderItem):
    """Cambia estado a Entrenar (protected=True, final_c=True).

    Estado terminal para el cliente. Solo backoffice puede cambiar.
    """
    update_version_state(
        project_id=self.id_proyecto,
        version_id=version_id,
        state="Entrenar",
        protected=True,
        final_c=True,
        updated_by_user_id=self.user_id
    )
```

#### 25.6.3. Menú Contextual Condicional

```python
# Línea 1757
# SECCIÓN VERSIÓN: Abrir / Bloquear / Entrenar
# REGLA: Ocultar opciones cuando estado = "Entrenar" o "Final"
rx.cond(
    item.depth == 1,
    rx.fragment(
        # Abrir - Solo si NO está en Entrenar/Final
        rx.cond(
            ~item.version_state_label.contains("Entrenamiento") &
            ~item.version_state_label.contains("Final"),
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="folder-open"), rx.text("Abrir")),
                on_click=lambda: ExploradorState.abrir_version(item)
            )
        ),
        # Bloquear - Solo si NO está en Entrenar/Final
        rx.cond(
            ~item.version_state_label.contains("Entrenamiento") &
            ~item.version_state_label.contains("Final"),
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="lock"), rx.text("Bloquear")),
                on_click=lambda: ExploradorState.bloquear_version(item)
            )
        ),
        # Entrenar - Solo si NO está en Entrenar/Final
        rx.cond(
            ~item.version_state_label.contains("Entrenamiento") &
            ~item.version_state_label.contains("Final"),
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="graduation-cap"), rx.text("Entrenar")),
                on_click=lambda: ExploradorState.entrenar_version(item)
            )
        )
    )
)
```

### 25.7. Implementación en Backoffice

**Archivo**: `src/apps/6_web_backoffice/components/explorador.py`

#### 25.7.1. Estados Disponibles

```python
# Línea 152
@rx.var
def available_status_options(self) -> list[str]:
    """Backoffice: Abierta, Bloqueada, Entrenar, Final."""
    return ["Abierta", "Bloqueada", "Entrenar", "Final"]
```

#### 25.7.2. Métodos Adicionales

```python
# Línea 603 (RENOMBRADO de proteger_version)
def entrenar_version(self, item_or_id):
    """Cambia estado a Entrenar."""
    update_version_state(
        project_id=self.id_proyecto,
        version_id=int(version_key.replace("v", "")),
        state="Entrenar",
        protected=True,
        final_c=True
    )

# Línea 645
def finalizar_version(self, item_or_id):
    """Cambia estado a Final (protected=True, final_c=True, final_i=True).

    DISPARA TRIGGER: entrenamiento_inicial_solicitado=1
    """
    update_version_state(
        project_id=self.id_proyecto,
        version_id=int(version_key.replace("v", "")),
        state="Final",
        protected=True,
        final_c=True,
        final_i=True  # SOLO backoffice puede activar
    )
```

#### 25.7.3. Menú Contextual (Todas las opciones visibles)

```python
# Línea 1450
rx.context_menu.item(
    rx.hstack(rx.icon(tag="folder-open"), rx.text("Abrir")),
    on_click=lambda id=item_id: ExploradorState.abrir_version(id)
),
rx.context_menu.item(
    rx.hstack(rx.icon(tag="lock"), rx.text("Bloquear")),
    on_click=lambda id=item_id: ExploradorState.bloquear_version(id)
),
rx.context_menu.item(
    rx.hstack(rx.icon(tag="graduation-cap"), rx.text("Entrenar")),
    on_click=lambda id=item_id: ExploradorState.entrenar_version(id)
),
rx.context_menu.item(
    rx.hstack(rx.icon(tag="check-circle"), rx.text("Finalizar")),
    on_click=lambda id=item_id: ExploradorState.finalizar_version(id)
)
```

### 25.8. API Backend Core

**Archivo**: `src/apps/3_backend/routercore.py`

#### 25.8.1. Método de Actualización

```python
# Línea 2852
def update_version_state(
    self,
    project_id: int,
    version_id: int,
    org_id: int,
    update_data: dict[str, Any],
) -> dict[str, Any]:
    """Actualiza estado de versión y registra cambio."""

    # 1. Construir UPDATE dinámico
    update_fields = []
    if "state" in update_data:
        update_fields.append("state = :state")
    if "protected" in update_data:
        update_fields.append("protected = :protected")
    if "final_c" in update_data:
        update_fields.append("final_c = :final_c")
    if "final_i" in update_data:
        update_fields.append("final_i = :final_i")

    # 2. Ejecutar UPDATE
    conn.execute(text(f"UPDATE version_states SET {', '.join(update_fields)}..."))

    # 3. Registrar en tabla cambios (AUTOMÁTICO)
    if "state" in update_data:
        state_mapping = {
            "Abierta": ("Abrir", "Versión v{version:03d} del proyecto '{project}' abierta para edición"),
            "Bloqueada": ("Bloquear", "Versión v{version:03d} del proyecto '{project}' bloqueada"),
            "Entrenar": ("Entrenar", "Cliente solicita entrenamiento para v{version:03d}..."),
            "Final": ("Finalizar", "Versión v{version:03d} del proyecto '{project}' lista para entrenar")
        }
        tipo, descripcion = state_mapping[update_data["state"]]
        conn.execute(text("""
            INSERT INTO cambios (id_organizacion, id_proyecto, id_version, fecha_cambio, tipo_cambio, descripcion)
            VALUES (:org_id, :project_id, :version_db_id, CURDATE(), :tipo, :descripcion)
        """))

    return self.get_version_state(project_id, version_id, org_id)
```

### 25.9. Reglas de Negocio

**Regla #46**: Estados terminales para el cliente

- Cliente NO puede cambiar estado desde "Entrenar" o "Final"
- Debe contactar a backoffice por:
  - Sistema de notificaciones (componente existente)
  - Tickets de soporte (botón "Solicitud de soporte" en Organizacion)
- Backoffice puede revertir cualquier estado

**Regla #47**: Registro automático de cambios

- TODOS los cambios de estado se registran en tabla `cambios`
- Descripción incluye proyecto y versión para contexto
- Visible en Calendario para cliente y backoffice
- Auditoría completa sin código adicional del desarrollador

**Regla #48**: Trigger de entrenamiento

- Se activa SOLO cuando `final_c=1 AND final_i=1`
- `final_i` SOLO puede ser activado por backoffice
- Cliente activa `final_c` con estado "Entrenar"
- Backoffice confirma con `final_i` en estado "Final"

**Regla #49**: Protección automática

- Cuando `protected=true`, versión es solo lectura
- Contenido recursivo bloqueado (archivos y carpetas)
- Carpeta de versión misma NO bloqueada (permite menú)
- Feedback visual: opacidad 0.5, sin menús contextuales

**Regla #50**: Compatibilidad con estado "Protegida"

- Estado "Protegida" DEPRECADO pero mantenido
- Alias de "Entrenar" para compatibilidad
- Código nuevo debe usar "Entrenar"
- Base de datos acepta ambos nombres

### 25.10. Testing

#### 25.10.1. Tests Unitarios

```python
# tests/frontend/test_explorador_estados.py

def test_entrenar_version_updates_state():
    """Verifica que entrenar_version actualiza correctamente."""
    state = ExploradorState()
    item = FolderItem(name="v001", depth=1)

    state.entrenar_version(item)

    assert state.version_states["v001"]["state"] == "Entrenar"
    assert state.version_states["v001"]["protected"] is True
    assert state.version_states["v001"]["final_c"] is True
```

#### 25.10.2. Tests de Integración

```python
# tests/integration/test_version_state_flow.py

def test_full_client_flow():
    """Test flujo completo: Abierta → Entrenar → Backoffice Finaliza."""
    # 1. Cliente: Abrir versión
    response = client.patch("/version-state", json={"state": "Abierta"})
    assert response.json()["state"]["protected"] is False

    # 2. Cliente: Solicitar entrenamiento
    response = client.patch("/version-state", json={"state": "Entrenar"})
    assert response.json()["state"]["final_c"] is True

    # 3. Backoffice: Finalizar
    response = admin_client.patch("/version-state", json={"state": "Final"})
    assert response.json()["state"]["final_i"] is True

    # 4. Verificar trigger ejecutado
    db_state = query_db("SELECT entrenamiento_inicial_solicitado FROM version_states...")
    assert db_state["entrenamiento_inicial_solicitado"] is True

    # 5. Verificar registro en cambios
    cambios = query_db("SELECT * FROM cambios WHERE tipo_cambio='Finalizar'...")
    assert len(cambios) == 1
    assert "lista para entrenar" in cambios[0]["descripcion"]
```

### 25.11. Archivos Críticos

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `src/apps/5_web_frontend/components/explorador.py` | 631-686 | Método `entrenar_version()` frontend |
| `src/apps/6_web_backoffice/components/explorador.py` | 603-655 | Métodos `entrenar_version()` y `finalizar_version()` |
| `src/apps/3_backend/routercore.py` | 2852-3050 | Método `update_version_state()` con registro automático |
| `infrastructure/database/migrations/009_estado_triggers.sql` | 50-75 | Trigger `trg_estado_version_auto_entrenamiento` |
| `README.md` | 2535-2580 | Documentación de estados de versiones |

### 25.12. Debugging Checklist

Cuando depurar problemas con estados de versiones:

1. [ ] Verificar que estado se refleja en DB: `SELECT state, protected, final_c, final_i FROM version_states WHERE id_proyecto=X AND id_version=Y`
2. [ ] Verificar trigger activo: `SHOW TRIGGERS FROM myllm_projects_db LIKE 'trg_estado_version_auto_entrenamiento'`
3. [ ] Verificar registro en cambios: `SELECT * FROM cambios WHERE id_proyecto=X AND id_version=Y ORDER BY fecha_cambio DESC`
4. [ ] Revisar logs backend: `grep "Actualizando estado versión" /data/backend_core/logs/`
5. [ ] Verificar permisos usuario: `identity_type_id` en sesión
6. [ ] Comprobar menú contextual renderizado: Inspeccionar condiciones `rx.cond()` en navegador

### 25.13. Common Pitfalls

**❌ INCORRECTO**:
```python
# Activar final_i desde frontend (PROHIBIDO)
update_version_state(state="Final", final_i=True)  # Frontend NO puede
```

**✅ CORRECTO**:
```python
# Frontend solo puede activar final_c
update_version_state(state="Entrenar", final_c=True)

# Solo Backoffice puede activar final_i
update_version_state(state="Final", final_c=True, final_i=True)  # Solo backoffice
```

---

**❌ INCORRECTO**:
```python
# Cambiar estado sin registrar en cambios
UPDATE version_states SET state='Entrenar' WHERE id=1;
```

**✅ CORRECTO**:
```python
# Usar método que registra automáticamente
router.update_version_state(project_id, version_id, org_id, {"state": "Entrenar"})
```

---

**❌ INCORRECTO**:
```python
# Mostrar siempre todas las opciones en frontend
rx.context_menu.item("Entrenar", on_click=entrenar)  # Sin condición
```

**✅ CORRECTO**:
```python
# Ocultar opciones en estados terminales
rx.cond(
    ~item.version_state_label.contains("Entrenamiento") &
    ~item.version_state_label.contains("Final"),
    rx.context_menu.item("Entrenar", on_click=entrenar)
)
```

### 25.14. Documentación Relacionada

- **README.md**: Sección "Estados de Versiones" (línea 2535) - Tabla de estados y flujos
- **AGENTS.md**: Sección 24 "Estado de Proyectos" - Sistema DDD relacionado
- **Migraciones DB**:
  - `008_estado_version_extension.sql` - Schema de version_states
  - `009_estado_triggers.sql` - Triggers automáticos

---

**⚠️ ADVERTENCIA**: Los estados de versiones controlan el acceso al sistema de entrenamiento de modelos LLM. Cambios incorrectos pueden:
- Bloquear acceso del cliente a versiones en producción
- Disparar entrenamientos costosos no autorizados
- Romper auditoría de cambios en calendario
- Corromper sincronización de estados entre tablas

**Antes de modificar**:
1. Revisar tabla de estados y transiciones permitidas
2. Verificar que registro en `cambios` funciona correctamente
3. Comprobar que trigger de entrenamiento no se dispara prematuramente
4. Validar permisos frontend vs backoffice
5. Crear tests que cubran el nuevo caso



---

## 26. Sistema de Permisos del Explorador

### 26.1. Arquitectura del Sistema de Permisos

El explorador de archivos implementa un sistema de permisos basado en **Security by Design** que:
- Carga permisos desde MariaDB al iniciar (modo db_only)
- Almacena permisos en memoria durante la sesión
- Valida permisos en frontend Y backend
- Muestra acciones deshabilitadas (no las oculta)
- Loggea todas las validaciones en logs/activity.log

### 26.2. Flujo de Carga de Permisos

```
1. Usuario inicia explorador con user_id (desde JWT/sesión)
   ↓
2. _load_permissions_from_database()
   ↓
3. SELECT identity_type_id FROM users WHERE user_id=X
   ↓
4. SELECT * FROM low_level_permissions WHERE id_permissions=identity_type_id
   ↓
5. Almacenar 40 permisos en State.permisos (diccionario en memoria)
   ↓
6. Permisos disponibles para toda la sesión
```

### 26.3. Tabla low_level_permissions (MariaDB myllm_core_db)

**Estructura:**
```sql
CREATE TABLE low_level_permissions (
    id_permissions INT PRIMARY KEY,  -- Mapea a users.identity_type_id
    -- Carpetas (5 campos)
    folder_create BOOLEAN,
    folder_delete BOOLEAN,
    folder_rename BOOLEAN,
    folder_read BOOLEAN,
    folder_list BOOLEAN,
    -- Archivos (5 campos)
    file_create BOOLEAN,
    file_read BOOLEAN,
    file_update BOOLEAN,
    file_delete BOOLEAN,
    file_list BOOLEAN,
    -- Proyectos, versiones, training, parameters, notifications, users...
    -- Total: 40 campos boolean
);
```

**Roles importantes:**
- `id_permissions=1`: SuperAdmin (todos TRUE)
- `id_permissions=2`: OrgAdmin (casi todos)
- `id_permissions=3`: Editor
- `id_permissions=4`: Lector (solo read/list)

### 26.4. Mapeo: Acciones → Permisos

**Archivo:** `src/2_shared_application/explorador_permissions_mapping.py`

| Acción del Menú | Tipo Item | Permiso Requerido | Notas |
|-----------------|-----------|-------------------|-------|
| Crear Carpeta | Carpeta | `folder_create` | Crea subcarpeta |
| Subir Archivo | Carpeta | `file_create` | Upload a carpeta |
| Renombrar | Carpeta | `folder_rename` | Renombrar carpeta |
| Renombrar | Archivo | `file_update` | Renombrar archivo (es update porque ya existe) |
| Eliminar | Carpeta | `folder_delete` | Eliminar carpeta |
| Eliminar | Archivo | `file_delete` | Eliminar archivo |
| Descargar | Carpeta | `folder_read` | Descargar como ZIP |
| Descargar | Archivo | `file_read` | Descargar archivo |
| Propiedades | Ambos | `folder_read` / `file_read` | Según tipo |

### 26.5. Validación de Permisos en acciones()

**CRÍTICO:** El método `acciones()` debe:

1. **Validar permiso base** (del usuario)
2. **Validar restricciones de versión** (solo identity_type_id 1 o 2)
3. **Validar protección de contenido** (db_protected)
4. **Loggear TODA validación** (éxito y fallo)
5. **Retornar error común:** "Operación no permitida"

```python
def acciones(self, accion: str, item: FolderItem):
    # 1. Obtener permiso requerido
    required_permission = get_required_permission(accion, item.item_type)
    
    # 2. Validar permiso del usuario
    if not self.permisos.get(required_permission, False):
        logger.warning(
            f"[PERMISSION DENIED] user_id={self.user_id} "
            f"accion={accion} permiso={required_permission} item={item.name}"
        )
        return rx.toast.error("Operación no permitida")
    
    # 3. Validar restricciones especiales de versión
    # Solo identity_type_id 1 o 2 pueden operar con versiones
    if accion in ["block_version", "unblock_version", "review_version"]:
        if self.user_identity_type_id not in (1, 2):
            logger.warning(
                f"[VERSION OPERATION DENIED] user_id={self.user_id} "
                f"identity_type_id={self.user_identity_type_id} accion={accion}"
            )
            return rx.toast.error("Operación no permitida")
    
    # 4. Validar protección de contenido (db_protected)
    if accion in ["create_folder", "upload_file"]:
        version_item = self._find_version_ancestor(item)
        if version_item and version_item.db_protected:
            logger.warning(
                f"[PROTECTED VERSION] accion={accion} version={version_item.name}"
            )
            return rx.toast.error("Operación no permitida")
    
    # 5. Loggear acción permitida
    logger.info(
        f"[ACTION ALLOWED] user_id={self.user_id} "
        f"accion={accion} permiso={required_permission} item={item.name}"
    )
    
    # 6. Ejecutar acción
    if accion == "create_folder":
        return self.abrir_dialogo_crear_carpeta(item)
    # ...
```

### 26.6. Refrescar Explorador Después de Acciones

**IMPORTANTE:** Después de CADA acción (crear, renombrar, eliminar):

1. **Esperar ACK de fmanagement** (response.get("success"))
2. **Si success=True:** Llamar `self.load_from_api()`
3. **Si success=False:** Mostrar error, NO refrescar

```python
response = fmanagement_create_folder(...)

if response.get("success") or response.get("status") == "success":
    logger.info(f"Carpeta creada: {folder_name}")
    # ✅ Refrescar desde fmanagement (/fmo/list)
    self.load_from_api()
    return rx.toast.success(f"Carpeta '{folder_name}' creada")
else:
    # ❌ Error, no refrescar
    error_msg = response.get("mensaje", "Error desconocido")
    return rx.toast.error(f"Error: {error_msg}")
```

**Razón:** El contenido del explorador SIEMPRE debe reflejar lo que fmanagement ve (`/fmo/list`).

### 26.7. Logging de Validaciones

**Archivo:** `logs/activity.log` (frontend y backoffice)

**Formato:**
```
2026-02-08 10:30:15 | INFO | [ACTION ALLOWED] user_id=5 accion=create_folder permiso=folder_create item=v001
2026-02-08 10:30:20 | WARNING | [PERMISSION DENIED] user_id=7 accion=delete permiso=folder_delete item=test
2026-02-08 10:30:25 | WARNING | [VERSION OPERATION DENIED] user_id=8 identity_type_id=3 accion=block_version
2026-02-08 10:30:30 | WARNING | [PROTECTED VERSION] accion=create_folder version=v002
```

**LOGGEAR TODO:**
- ✅ Acciones permitidas (INFO)
- ❌ Permisos denegados (WARNING)
- ❌ Restricciones de versión (WARNING)
- ❌ Versiones protegidas (WARNING)

### 26.8. Restricción Especial: Operaciones con Versiones

**REGLA CRÍTICA:** Solo `identity_type_id = 1 (SuperAdmin)` o `2 (OrgAdmin)` pueden:
- Crear versiones (`version_create`)
- Bloquear versiones (`block_version`)
- Desbloquear versiones (`unblock_version`)
- Eliminar versiones (`version_delete`)
- Cambiar estado de versión

**Validación:**
```python
if self.user_identity_type_id not in (1, 2):
    return rx.toast.error("Operación no permitida")
```

### 26.9. UI: Mostrar Acciones Deshabilitadas

**IMPORTANTE:** NO ocultar acciones sin permiso. Mostrarlas deshabilitadas (gris).

```python
# ❌ INCORRECTO: Ocultar acción
rx.cond(
    self.permisos.get("folder_create"),
    rx.context_menu.item("Crear Carpeta", on_click=...)
)

# ✅ CORRECTO: Mostrar deshabilitada
rx.context_menu.item(
    "Crear Carpeta",
    on_click=...,
    disabled=~self.permisos.get("folder_create"),  # Gris si no tiene permiso
)
```

**Razón:** Más elegante y el usuario ve qué funcionalidades existen (aunque no pueda usarlas).

### 26.10. Archivos Críticos

1. `src/2_shared_application/adapters/user_permissions_adapter.py`
   - Obtiene permisos desde MariaDB
   - Función: `get_user_permissions(user_id)`

2. `src/2_shared_application/explorador_permissions_mapping.py`
   - Mapeo acciones → permisos
   - Funciones: `get_required_permission()`, `is_action_allowed()`

3. `src/apps/5_web_frontend/components/explorador.py`
   - State con permisos en memoria
   - Método: `_load_permissions_from_database()`
   - Método: `acciones()` con validación

4. `src/apps/6_web_backoffice/components/explorador.py`
   - Réplica idéntica del frontend

### 26.11. Ejemplo Completo de Flujo

```
Usuario hace clic en "Crear Carpeta" en v001/docs
  ↓
acciones("create_folder", item)
  ↓
Validar: get_required_permission("create_folder", "folder") → "folder_create"
  ↓
Validar: self.permisos["folder_create"] == True? → ✅ Sí
  ↓
Validar: v001.db_protected == True? → ❌ No
  ↓
Loggear: [ACTION ALLOWED] user_id=5 accion=create_folder permiso=folder_create
  ↓
abrir_dialogo_crear_carpeta(item)
  ↓
Usuario ingresa nombre "test"
  ↓
ejecutar_crear_carpeta()
  ↓
fmanagement_create_folder(...) → {"success": true}
  ↓
load_from_api() → /fmo/list → Refrescar explorador
  ↓
rx.toast.success("Carpeta 'test' creada")
```

### 26.12. Errores Comunes

❌ **NO usar permisos de proyectos_roles directamente**
- Los permisos vienen de `users.identity_type_id`, NO de `proyectos_roles.id_rol`
- Ambos mapean a `low_level_permissions.id_permissions`

❌ **NO refrescar antes del ACK**
```python
# MAL
fmanagement_create_folder(...)
self.load_from_api()  # ❌ No espera respuesta
```

❌ **NO usar JSON en db_only**
```python
# MAL
permissions = json.load("low_level_permisions.json")
# BIEN
permissions = get_user_permissions(user_id)  # Desde MariaDB
```

❌ **NO loggear solo errores**
- Loggear TODAS las validaciones (éxito y fallo)

---

## 27. Sistema de Plantillas de Jobs y Ejecución de Trabajos

**DESCRIPCIÓN**: El sistema de plantillas de jobs define un modelo reutilizable para crear, programar y ejecutar trabajos de IA (análisis documental, entrenamiento, evaluación de resultados, generación de modelos LLM). Se basa en tablas catálogo, una tabla central de plantillas (`jobs_templates`) y tablas de ejecución (`jobs`, `jobs_eventos`, `jobs_entradas`) con soporte de encadenamiento padre-hijo.

### 27.1. Arquitectura General

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                        CATÁLOGOS (solo lectura en runtime)                    │
│  jobs_tipos │ jobs_estados │ jobs_modelos │ jobs_salidas │ jobs_documentacion │
│  jobs_entrenamientos │ jobs_resultados │ jobs_generacion                      │
└───────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌───────────────────────────────────────────────────────────────────────────────┐
│                     PLANTILLAS (configuradas por SuperAdmin)                  │
│                              jobs_templates                                  │
└───────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌───────────────────────────────────────────────────────────────────────────────┐
│                     EJECUCIÓN (instancias en runtime)                         │
│              jobs │ jobs_eventos │ jobs_entradas                              │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Base de datos:** `myllm_projects_db`

**Migración:** `infrastructure/database/migrations/011_jobs_templates_system.sql`

### 27.2. Tablas Catálogo (OBLIGATORIO entender)

Las tablas catálogo contienen registros fijos que se usan como referencia. NO deben modificarse
desde el código de aplicación salvo por scripts de migración o el SuperAdmin desde backoffice.

#### 27.2.1. `jobs_tipos` — Tipos de job

Define en qué página del backoffice se puede usar cada plantilla.

| `clave` | `nombre` | `pagina_backoffice` | Descripción |
|---------|----------|---------------------|-------------|
| `analisis_documentacion` | Análisis de Documentación | `Documentacion` | Analiza documentos subidos por clientes |
| `entrenamiento` | Entrenamiento | `Entrenamientos` | Entrena modelo con parámetros RAG |
| `analisis_resultados` | Análisis de Resultados | `Resultados` | Evalúa métricas y genera informes |
| `crear_modelo_llm` | Crear Modelo LLM | `Generacion` | Genera modelo LLM fine-tuned |

**Regla #1**: Cada plantilla (`jobs_templates`) tiene EXACTAMENTE un `id_tipo` que determina su página.

**Regla #2**: Al crear nuevas páginas en backoffice, PRIMERO crear el registro en `jobs_tipos`.

#### 27.2.2. `jobs_estados` — Estados de un job

| `clave` | `nombre` | `color` | `es_final` | Descripción |
|---------|----------|---------|------------|-------------|
| `programado` | Programado | `blue` | 0 | Job creado, esperando ejecución |
| `en_ejecucion` | En ejecución | `amber` | 0 | Job ejecutándose activamente |
| `error` | Error | `red` | 1 | Job terminó con error |
| `finalizado` | Finalizado | `green` | 1 | Job completado exitosamente |

**Regla #3**: Los badges de estado en UI DEBEN usar `rx.match` con los colores definidos aquí.

**Regla #4**: Un job solo puede transicionar a un estado `es_final=1` como último paso. Una vez en estado final, NO puede cambiar.

**Transiciones válidas:**
```
programado → en_ejecucion → finalizado
programado → en_ejecucion → error
programado → error (si falla antes de ejecutarse)
```

#### 27.2.3. `jobs_modelos` — Modelos LLM disponibles

Refleja la salida de `ollama list`. Cada registro representa un modelo disponible para su uso
en jobs de tipo `entrenamiento` o `crear_modelo_llm`.

**Regla #5**: La tabla `jobs_modelos` se actualiza periódicamente desde el Trainer (sincronización con Ollama).

**Regla #6**: NUNCA crear registros manualmente; usar el endpoint de sincronización del Trainer.

#### 27.2.4. `jobs_salidas` — Tipos de salida

Define qué produce un job al terminar. Cada tipo tiene un `campo_referencia` diferente.

| `clave` | `nombre` | `campo_referencia` | Descripción |
|---------|----------|--------------------|-------------|
| `nuevo_job` | Nuevo Job | `id_job` | El resultado dispara otro job hijo |
| `informe` | Informe | `path_fichero` | Genera un fichero (markdown, PDF, etc.) |
| `notificacion` | Notificación | `id_conversacion` | Envía notificación al sistema de conversaciones |
| `ticket` | Ticket | `id_ticket` | Crea o responde un ticket de soporte |

**Regla #7**: Al completarse un job, el campo `referencia_salida` en la tabla `jobs` se rellena
con el valor correspondiente al `campo_referencia` del tipo de salida seleccionado.

#### 27.2.5. `jobs_documentacion` — Plantillas Jinja2 para informes

Almacena las plantillas Jinja2 (`.j2`) que se usan para generar informes de salida.

**Regla #8**: Las plantillas Jinja2 residen en el filesystem (campo `template_path`), NO en base de datos.

**Regla #9**: El campo `variables_requeridas` (JSON) documenta qué variables necesita la plantilla.
Ejemplo:
```json
["nombre_proyecto", "version", "fecha_analisis", "metricas", "conclusiones"]
```

**Regla #10**: Verificar que TODAS las variables requeridas están disponibles antes de renderizar.

#### 27.2.6. `jobs_entrenamientos` — Configuraciones de parámetros RAG

Almacena perfiles de configuración reutilizables para entrenamientos. Cada perfil tiene
parámetros de hiperparámetros (learning_rate, epochs, etc.), ChromaDB (collection, chunk_size)
y generación (temperature, max_tokens).

**Regla #11**: Los perfiles se seleccionan en la plantilla (`jobs_templates.configuracion_defecto`)
y pueden sobrescribirse a nivel de job individual (`jobs.configuracion`).

**Regla #12**: Los valores por defecto de la tabla son los estándar del proyecto. NUNCA modificar
los defaults de la tabla sin consultar al equipo.

#### 27.2.7. `jobs_resultados` — Resultados de ejecución

Almacena métricas, informes generados y cualquier salida de un job. El campo `datos_resultado`
(JSON) permite flexibilidad total.

**Regla #13**: Cada resultado tiene un `tipo_resultado` que indica su naturaleza:
- `metricas_entrenamiento`: Métricas de loss, accuracy, etc.
- `informe_generado`: Informe renderizado desde plantilla Jinja2
- `evaluacion_modelo`: Resultados de evaluación (perplexity, BLEU, etc.)

**Regla #14**: Si el resultado genera un fichero, rellenar `path_fichero` y `nombre_fichero`.
La FK opcional `id_documentacion` indica qué plantilla Jinja2 se usó.

#### 27.2.8. `jobs_generacion` — Modelos LLM generados

Registra cada modelo LLM producido. Vinculado a organización, proyecto y versión.

**Regla #15**: `id_modelo_base` referencia a `jobs_modelos` (modelo base usado para fine-tuning).

**Regla #16**: `path_modelo` sigue la estructura estándar de almacenamiento:
```
internal/models/ORG{id}/PRJ{id}/v{version}/{nombre_modelo}
```

### 27.3. Tabla Central: `jobs_templates` — Plantillas de Jobs

**CONCEPTO CLAVE:** Una plantilla es una receta reutilizable que define los valores por defecto
de un job. Cuando se crea un job desde una plantilla, hereda todos los valores pero permite
sobreescribirlos individualmente.

#### 27.3.1. Campos y semántica

| Campo | Propósito | Heredable por job |
|-------|-----------|-------------------|
| `nombre` | Nombre visible de la plantilla | ✅ Sí (campo `nombre` del job) |
| `descripcion` | Descripción detallada | ✅ Sí |
| `id_tipo` | FK a `jobs_tipos` (determina página) | ✅ Sí (obligatorio) |
| `es_programable` | Si los jobs soportan ejecución diferida | ✅ Sí |
| `id_estado_inicial` | FK a `jobs_estados` (estado al crear job) | ✅ Sí (default: `programado`) |
| `id_modelo` | FK a `jobs_modelos` (modelo LLM por defecto) | ✅ Sí (puede ser NULL) |
| `id_salida` | FK a `jobs_salidas` (tipo de salida) | ✅ Sí |
| `acepta_entrada` | Si puede ser job hijo | ✅ Sí |
| `permite_hijos` | Si puede ser job padre | ✅ Sí |
| `configuracion_defecto` | JSON con configuración flexible | ✅ Sí (a campo `configuracion`) |
| `activo` | Si la plantilla está disponible | ❌ No |

**Regla #17**: Una plantilla con `activo=0` NO puede usarse para crear nuevos jobs, pero los
jobs existentes que la referencian siguen siendo válidos.

**Regla #18**: El campo `configuracion_defecto` (JSON) puede contener CUALQUIER configuración
específica del tipo de job. Ejemplo para un job de análisis documental:
```json
{
  "formatos_aceptados": ["pdf", "docx", "txt"],
  "max_paginas": 100,
  "idioma": "es",
  "id_entrenamiento": 1,
  "id_documentacion": 2
}
```

#### 27.3.2. Relación tipo → página del backoffice

```
jobs_templates.id_tipo → jobs_tipos.id → jobs_tipos.pagina_backoffice
```

| Página Backoffice | Tipo de plantilla | Ejemplo de plantilla |
|-------------------|-------------------|----------------------|
| **Documentación** | `analisis_documentacion` | "Análisis de contratos PDF" |
| **Entrenamientos** | `entrenamiento` | "Fine-tuning Llama3 con RAG" |
| **Resultados** | `analisis_resultados` | "Informe de evaluación de modelo" |
| **Generación** | `crear_modelo_llm` | "Generar modelo Llama3 fine-tuned" |

**Regla #19**: Cada página del backoffice SOLO muestra plantillas cuyo `id_tipo` corresponde
a esa página. Usar filtro SQL:
```sql
SELECT t.*
FROM jobs_templates t
INNER JOIN jobs_tipos jt ON t.id_tipo = jt.id
WHERE jt.pagina_backoffice = :pagina
  AND t.activo = 1
ORDER BY t.nombre;
```

#### 27.3.3. Encadenamiento: `acepta_entrada` y `permite_hijos`

| `acepta_entrada` | `permite_hijos` | Comportamiento |
|-------------------|-----------------|----------------|
| 0 | 0 | Job independiente (sin padre ni hijos) |
| 0 | 1 | Job padre (puede disparar hijos al completarse) |
| 1 | 0 | Job hijo (recibe datos de un padre) |
| 1 | 1 | Job intermedio (recibe datos y produce hijos) |

**Regla #20**: Un job creado desde una plantilla con `acepta_entrada=1` DEBE tener un `id_job_padre`
válido. Sin padre, no tiene datos de entrada.

**Regla #21**: Un job creado desde una plantilla con `permite_hijos=1` puede (opcionalmente)
crear jobs hijos al completarse. Los hijos se crean via `jobs_entradas`.

### 27.4. Creación de Plantillas desde Backoffice (OBLIGATORIO)

**Acceso:** Solo SuperAdmin (`identity_type_id=1`)

#### 27.4.1. Flujo de creación

```
1. SuperAdmin navega a "Gestión de Plantillas" en Backoffice
   ↓
2. Selecciona tipo de job (determina página y contexto)
   ↓
3. Rellena formulario:
   - Nombre y descripción
   - Modelo LLM (selector desde jobs_modelos)
   - Tipo de salida (selector desde jobs_salidas)
   - Es programable (toggle)
   - Acepta entrada / Permite hijos (toggles)
   - Configuración por defecto (editor JSON)
   ↓
4. Backoffice → Middleware → Broker → Backend Core
   ↓
5. Backend Core valida permisos (identity_type_id=1)
   ↓
6. INSERT en jobs_templates
   ↓
7. Retorna plantilla creada con ID
```

#### 27.4.2. Validación de permisos (Security by Design)

```python
# OBLIGATORIO en TODOS los endpoints de plantillas
@app.post("/job-templates")
async def create_job_template(
    request: CreateJobTemplateDto,
    session: SessionContext = Depends(get_session_context),
):
    # VALIDACIÓN CRÍTICA: Solo SuperAdmin
    if session.identity_type_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo SuperAdmin puede gestionar plantillas de jobs",
        )
    # ... resto de lógica
```

**Regla #22**: SOLO `identity_type_id=1` (SuperAdmin) puede crear, editar o desactivar plantillas.

**Regla #23**: Las operaciones de lectura (listar, consultar) requieren `training_read=true`.

#### 27.4.3. Endpoints de plantillas

| Endpoint | Método | Permiso | Descripción |
|----------|--------|---------|-------------|
| `/job-templates` | GET | `training_read` | Listar plantillas (con filtro por tipo) |
| `/job-templates/{id}` | GET | `training_read` | Obtener plantilla por ID |
| `/job-templates` | POST | SuperAdmin only | Crear plantilla |
| `/job-templates/{id}` | PATCH | SuperAdmin only | Actualizar plantilla |
| `/job-templates/{id}/deactivate` | PATCH | SuperAdmin only | Desactivar plantilla |

#### 27.4.4. Flujo arquitectónico completo

```
Backoffice UI → Middleware → Broker → Backend Core → MariaDB
  (Reflex)      (apife.py)  (apibe.py) (apicore.py)  (myllm_projects_db)
```

**Archivos a implementar:**

| Capa | Archivo | Método |
|------|---------|--------|
| Backoffice UI | `web_backoffice.py` o `pages/job_templates.py` | Formulario CRUD |
| API Client | `adapters/api_client.py` | `create_job_template()`, `list_job_templates()` |
| Middleware API | `apife.py` | `POST /job-templates`, `GET /job-templates` |
| Middleware Router | `routermiddleware.py` | `create_job_template()`, `list_job_templates()` |
| Broker Client | `broker_backend_client.py` | `create_job_template()` |
| Broker API | `apibe.py` | `POST /job-templates` |
| Broker Router | `routerbroker.py` | `create_job_template()` |
| Core Interface | `interfacetocore.py` | `create_job_template()` |
| Core API | `apicore.py` | `POST /job-templates` |
| Core Router | `routercore.py` | `create_job_template()` |

### 27.5. Instanciación de Jobs desde Plantillas (OBLIGATORIO)

**CONCEPTO CLAVE:** Un "job" es una instancia concreta de una plantilla, asociada a una
organización, proyecto y versión específica. Hereda los valores de la plantilla pero puede
sobrescribirlos.

#### 27.5.1. Flujo de instanciación

```
1. Usuario (con permiso training_create) selecciona plantilla
   ↓
2. Sistema pre-rellena formulario con valores heredados de la plantilla
   ↓
3. Usuario puede modificar: nombre, modelo, configuración, fecha programada
   ↓
4. Sistema establece:
   - id_template = plantilla seleccionada
   - id_organizacion, id_proyecto, id_version = contexto actual
   - id_estado = id_estado_inicial de la plantilla (default: "programado")
   - id_tipo = heredado de plantilla
   - id_salida = heredado de plantilla (modificable)
   - configuracion = merge(plantilla.configuracion_defecto, modificaciones_usuario)
   ↓
5. INSERT en tabla jobs
   ↓
6. INSERT en tabla cambios (auditoría automática)
   ↓
7. Si id_estado = "programado" y programado_para IS NULL:
   → Ejecución inmediata (cambiar a "en_ejecucion")
   ↓
8. Si programado_para IS NOT NULL:
   → Encolar para ejecución futura
```

#### 27.5.2. Herencia de valores plantilla → job

```python
def create_job_from_template(template_id: int, overrides: dict) -> Job:
    """Crea un job heredando valores de la plantilla con sobreescrituras opcionales."""
    template = repository.get_template(template_id)

    job = Job(
        id_template=template.id,
        nombre=overrides.get("nombre", template.nombre),
        descripcion=overrides.get("descripcion", template.descripcion),
        id_tipo=template.id_tipo,  # NUNCA sobrescribir
        id_estado=template.id_estado_inicial or get_estado_by_clave("programado").id,
        id_modelo=overrides.get("id_modelo", template.id_modelo),
        id_salida=overrides.get("id_salida", template.id_salida),
        programado_para=overrides.get("programado_para"),
        configuracion=_merge_config(
            template.configuracion_defecto,
            overrides.get("configuracion", {}),
        ),
        id_organizacion=overrides["id_organizacion"],  # OBLIGATORIO
        id_proyecto=overrides["id_proyecto"],            # OBLIGATORIO
        id_version=overrides["id_version"],              # OBLIGATORIO
    )
    return repository.save_job(job)


def _merge_config(base: dict | None, overrides: dict) -> dict:
    """Merge configuración plantilla + sobreescrituras del usuario."""
    merged = dict(base or {})
    merged.update(overrides)
    return merged
```

**Regla #24**: `id_tipo` NUNCA puede sobrescribirse al crear un job. Se hereda de la plantilla.

**Regla #25**: `id_organizacion`, `id_proyecto` e `id_version` son OBLIGATORIOS y vienen del
contexto del usuario (proyecto y versión seleccionados en la UI).

**Regla #26**: La configuración del job es el resultado del merge entre `configuracion_defecto`
de la plantilla y las modificaciones del usuario. Las claves del usuario sobrescriben las de
la plantilla.

#### 27.5.3. Permisos para instanciar jobs

| Operación | Permiso requerido | identity_type_id permitidos |
|-----------|-------------------|-----------------------------|
| Crear job | `training_create` | 1 (SuperAdmin), 2 (Admin), 3 (Editor) |
| Ver jobs | `training_read` | 1, 2, 3, 4, 5 |
| Cancelar job | `training_stop` | 1, 2 |
| Ver resultados | `training_read` | 1, 2, 3, 4, 5 |

**Regla #27**: Validar permiso `training_create` en Middleware Y Backend Core antes de crear un job.

#### 27.5.4. Endpoints de jobs

| Endpoint | Método | Permiso | Descripción |
|----------|--------|---------|-------------|
| `/jobs` | POST | `training_create` | Crear job desde plantilla |
| `/jobs` | GET | `training_read` | Listar jobs (filtros: org, proyecto, versión, estado) |
| `/jobs/{id}` | GET | `training_read` | Obtener job con detalle |
| `/jobs/{id}/cancel` | PATCH | `training_stop` | Cancelar job en ejecución |
| `/jobs/{id}/events` | GET | `training_read` | Obtener eventos del job |
| `/jobs/{id}/results` | GET | `training_read` | Obtener resultados del job |

#### 27.5.5. Registro automático en tabla `cambios`

Al crear un job, registrar automáticamente en la tabla `cambios`:

```python
# En routercore.py - al crear job
conn.execute(text("""
    INSERT INTO cambios
        (id_organizacion, id_proyecto, id_version, fecha_cambio, tipo_cambio, descripcion)
    VALUES
        (:org_id, :project_id, :version_id, CURDATE(), :tipo, :descripcion)
"""), {
    "org_id": job.id_organizacion,
    "project_id": job.id_proyecto,
    "version_id": job.id_version,
    "tipo": "Crear job",
    "descripcion": f"Job '{job.nombre}' creado desde plantilla '{template.nombre}'"
})
```

**Regla #28**: TODOS los eventos significativos de jobs (creación, inicio, error, finalización)
deben registrarse en la tabla `cambios` para visibilidad en el Calendario.

### 27.6. Ejecución de Jobs y Eventos (OBLIGATORIO)

#### 27.6.1. Ciclo de vida de un job

```
         ┌──────────┐
         │ CREACIÓN │
         └────┬─────┘
              ↓
  ┌───────────────────────┐
  │  estado = programado  │──── programado_para != NULL → Encolar
  └───────────┬───────────┘
              ↓ (ejecución inmediata o al llegar la hora)
  ┌───────────────────────┐
  │ estado = en_ejecucion │──── Evento: tipo_evento="inicio"
  │ iniciado_en = NOW()   │
  └───────────┬───────────┘
              ↓
      ┌───────┴────────┐
      ↓                ↓
  ┌────────┐     ┌──────────┐
  │ ERROR  │     │ ÉXITO    │
  │ error= │     │ datos_   │
  │ "msg"  │     │ salida=  │
  └────┬───┘     │ {JSON}   │
       ↓         └────┬─────┘
  ┌─────────┐    ┌──────────────┐
  │ estado= │    │ estado=      │
  │ error   │    │ finalizado   │
  │         │    │ completado_  │
  │         │    │ en=NOW()     │
  └─────────┘    └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │ Crear hijos  │ (si permite_hijos=1 y hay plantillas hijo)
                 │ via jobs_    │
                 │ entradas     │
                 └──────────────┘
```

#### 27.6.2. Tabla `jobs_eventos` — Log cronológico

Cada job produce eventos durante su ejecución. Son inmutables (solo INSERT, nunca UPDATE/DELETE).

**Formato de `referencia_compuesta`:**
```
ORG{id_organizacion}-PRJ{id_proyecto}-VER{id_version}-JOB{id_job}
```

Ejemplo: `ORG1-PRJ3-VER2-JOB45`

**Tipos de evento estándar:**

| `tipo_evento` | Cuándo se genera | `datos_evento` (JSON) típico |
|---------------|------------------|------------------------------|
| `inicio` | Job comienza ejecución | `{"modelo": "llama3:latest"}` |
| `progreso` | Actualización de progreso | `{"porcentaje": 45, "paso": "embedding"}` |
| `metricas` | Métricas parciales | `{"loss": 0.234, "epoch": 3}` |
| `error` | Error durante ejecución | `{"error": "OOM", "detalle": "..."}` |
| `fin` | Job completa exitosamente | `{"duracion_segundos": 3600}` |
| `hijo_creado` | Se crea un job hijo | `{"id_job_hijo": 46, "tipo": "notificacion"}` |

**Regla #29**: Los eventos son INMUTABLES. NUNCA hacer UPDATE ni DELETE sobre `jobs_eventos`.

**Regla #30**: Todo evento debe incluir `referencia_compuesta` para búsqueda rápida por contexto.

**Regla #31**: El Trainer (Backend IA) es el principal productor de eventos. Los envía vía
el Broker al Backend Core para persistencia.

### 27.7. Encadenamiento Padre-Hijo (OBLIGATORIO)

El encadenamiento permite que un job, al completarse, dispare automáticamente uno o más
jobs hijos, transfiriendo datos de salida como datos de entrada.

#### 27.7.1. Flujo de encadenamiento

```
┌───────────────────────────────────────────────────────────────┐
│ Job Padre (permite_hijos=1) completa exitosamente             │
│ → datos_salida = {"metricas": {...}, "path_informe": "/..."}  │
│ → referencia_salida = "/data/internal/reports/ORG1/..."       │
└───────────────────────────────┬───────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────┐
│ Sistema busca plantillas hijo configuradas                    │
│ (jobs_templates con acepta_entrada=1 y tipo compatible)       │
└───────────────────────────────┬───────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────┐
│ Para cada hijo configurado:                                   │
│ 1. Crear job hijo (id_job_padre = padre.id)                   │
│ 2. Crear registro en jobs_entradas:                           │
│    - id_job_padre, id_job_hijo                                │
│    - datos = padre.datos_salida (total o parcial)             │
│    - id_resultado (si hay resultado asociado)                 │
│ 3. Job hijo recibe datos en datos_entrada (copiados)          │
│ 4. Job hijo inicia ejecución                                  │
└───────────────────────────────────────────────────────────────┘
```

#### 27.7.2. Tabla `jobs_entradas` — Transferencia de datos

Cada registro representa una transferencia de datos de un padre a un hijo.

**Regla #32**: `id_job_padre` y `id_job_hijo` DEBEN referenciar jobs existentes en la tabla `jobs`.

**Regla #33**: El campo `datos` (JSON) contiene el payload flexible que el padre envía al hijo.
Es una copia (no referencia) de los datos para garantizar inmutabilidad.

**Regla #34**: Si el padre produjo un resultado (`jobs_resultados`), se puede vincular via
`id_resultado` para trazabilidad.

#### 27.7.3. Ejemplo completo de encadenamiento

```
Escenario: Análisis documental → Genera informe → Notifica al cliente

Job 1 (Padre): "Análisis de contratos PDF"
  - id_tipo: analisis_documentacion
  - permite_hijos: 1
  - Al completar:
    - datos_salida: {"paginas_analizadas": 45, "entidades": [...], "resumen": "..."}
    - referencia_salida: null
    - Crea resultado en jobs_resultados con tipo "metricas_entrenamiento"

Job 2 (Hijo intermedio): "Generar informe de análisis"
  - id_tipo: analisis_resultados
  - acepta_entrada: 1
  - permite_hijos: 1
  - id_job_padre: Job1.id
  - datos_entrada: (copiado de Job1.datos_salida)
  - Al completar:
    - Renderiza plantilla Jinja2 con los datos
    - datos_salida: {"path_informe": "/data/internal/reports/..."}
    - referencia_salida: "/data/internal/reports/ORG1/PRJ3/v001/analisis_20260210.md"

Job 3 (Hijo final): "Notificar resultado al cliente"
  - id_tipo: analisis_resultados (subtipo notificación)
  - acepta_entrada: 1
  - permite_hijos: 0
  - id_job_padre: Job2.id
  - datos_entrada: (copiado de Job2.datos_salida)
  - Al completar:
    - Crea conversación o mensaje en sistema de notificaciones
    - referencia_salida: "conv-uuid-1234" (id_conversacion)
```

#### 27.7.4. Registro en `jobs_entradas` para el ejemplo

```sql
-- Transferencia Job1 → Job2
INSERT INTO jobs_entradas (id_job_padre, id_job_hijo, id_tipo_salida, id_resultado, datos)
VALUES (1, 2, NULL, 1, '{"paginas_analizadas": 45, "entidades": [...], "resumen": "..."}');

-- Transferencia Job2 → Job3
INSERT INTO jobs_entradas (id_job_padre, id_job_hijo, id_tipo_salida, id_resultado, datos)
VALUES (2, 3, 2, 2, '{"path_informe": "/data/internal/reports/ORG1/PRJ3/v001/analisis.md"}');
```

#### 27.7.5. Implementación del encadenamiento en Backend Core

```python
def complete_job(self, job_id: int, datos_salida: dict, referencia_salida: str | None) -> dict:
    """Completa un job y dispara hijos si aplica."""
    with self._engine.begin() as conn:
        # 1. Actualizar job padre
        conn.execute(text("""
            UPDATE jobs
            SET id_estado = (SELECT id FROM jobs_estados WHERE clave = 'finalizado'),
                completado_en = NOW(),
                datos_salida = :datos_salida,
                referencia_salida = :referencia_salida
            WHERE id = :job_id
        """), {
            "job_id": job_id,
            "datos_salida": json.dumps(datos_salida),
            "referencia_salida": referencia_salida,
        })

        # 2. Registrar evento de fin
        self._create_event(conn, job_id, "fin", {"duracion": "..."})

        # 3. Si permite_hijos, crear jobs hijos
        job = self._get_job(conn, job_id)
        template = self._get_template(conn, job["id_template"])

        if template["permite_hijos"]:
            self._create_child_jobs(conn, job, datos_salida)

    return self.get_job(job_id)


def _create_child_jobs(
    self,
    conn,
    parent_job: dict,
    parent_output: dict,
) -> list[int]:
    """Crea jobs hijos configurados para el padre."""
    child_job_ids = []

    # Buscar plantillas hijas configuradas en configuracion del padre
    child_templates = parent_job.get("configuracion", {}).get("hijos", [])

    for child_config in child_templates:
        child_template_id = child_config["id_template"]
        child_template = self._get_template(conn, child_template_id)

        if not child_template or not child_template["acepta_entrada"]:
            continue

        # Crear job hijo
        child_job_id = self._insert_job(
            conn,
            template=child_template,
            id_organizacion=parent_job["id_organizacion"],
            id_proyecto=parent_job["id_proyecto"],
            id_version=parent_job["id_version"],
            id_job_padre=parent_job["id"],
            datos_entrada=parent_output,
        )

        # Crear registro en jobs_entradas
        conn.execute(text("""
            INSERT INTO jobs_entradas
                (id_job_padre, id_job_hijo, datos)
            VALUES
                (:padre, :hijo, :datos)
        """), {
            "padre": parent_job["id"],
            "hijo": child_job_id,
            "datos": json.dumps(parent_output),
        })

        child_job_ids.append(child_job_id)

    return child_job_ids
```

**Regla #35**: La creación de jobs hijos DEBE ser transaccional con la finalización del padre.
Si falla la creación de hijos, el padre NO se marca como finalizado.

**Regla #36**: Los hijos configurados se definen en `jobs.configuracion.hijos` (array de
`{"id_template": N, "datos_filtro": {...}}`).

### 27.8. Configuración de Hijos en Plantillas

Para que una plantilla padre sepa qué hijos crear, se configura en `configuracion_defecto`:

```json
{
  "parametros_analisis": {"max_paginas": 100},
  "hijos": [
    {
      "id_template": 5,
      "descripcion": "Generar informe automático",
      "datos_filtro": ["metricas", "resumen"]
    },
    {
      "id_template": 8,
      "descripcion": "Notificar al cliente",
      "datos_filtro": ["path_informe"]
    }
  ]
}
```

**Regla #37**: `datos_filtro` (opcional) es un array de claves de `datos_salida` del padre
que se envían al hijo. Si está vacío o ausente, se envía TODO `datos_salida`.

**Regla #38**: Al configurar hijos en una plantilla, verificar que las plantillas hijas existen
y tienen `acepta_entrada=1`.

### 27.9. Comunicación con el Trainer (Backend IA)

Los jobs de tipo `entrenamiento` y `crear_modelo_llm` se ejecutan en el servidor Trainer.

#### 27.9.1. Flujo de ejecución en Trainer

```
Backend Core crea job (estado=programado)
  ↓
Broker envía petición al Trainer (POST /jobs/{id}/execute)
  ↓
Trainer cambia estado a en_ejecucion
  ↓
Trainer ejecuta trabajo (Ollama, ChromaDB, etc.)
  ↓
Trainer envía eventos periódicos (POST /jobs/{id}/events → Broker → Core)
  ↓
Trainer completa o falla
  ↓
Trainer notifica resultado (PATCH /jobs/{id}/complete → Broker → Core)
  ↓
Backend Core registra resultado y dispara hijos si aplica
```

**Regla #39**: El Trainer NUNCA escribe directamente en `myllm_projects_db`. Todas las
operaciones de persistencia pasan por el Broker → Backend Core.

**Regla #40**: Los eventos de progreso del Trainer se envían asíncronamente. El Backend Core
los persiste en `jobs_eventos` sin bloquear al Trainer.

### 27.10. Consultas SQL de Referencia

#### 27.10.1. Listar plantillas por página de backoffice

```sql
SELECT
    t.id,
    t.nombre,
    t.descripcion,
    jt.nombre AS tipo_nombre,
    jt.pagina_backoffice,
    je.nombre AS estado_inicial,
    jm.nombre AS modelo_nombre,
    js.nombre AS salida_nombre,
    t.es_programable,
    t.acepta_entrada,
    t.permite_hijos,
    t.activo
FROM jobs_templates t
INNER JOIN jobs_tipos jt ON t.id_tipo = jt.id
LEFT JOIN jobs_estados je ON t.id_estado_inicial = je.id
LEFT JOIN jobs_modelos jm ON t.id_modelo = jm.id
LEFT JOIN jobs_salidas js ON t.id_salida = js.id
WHERE jt.pagina_backoffice = :pagina
  AND t.activo = 1
ORDER BY t.nombre;
```

#### 27.10.2. Listar jobs de un proyecto/versión con estado

```sql
SELECT
    j.id,
    j.nombre,
    j.descripcion,
    jt.nombre AS tipo_nombre,
    je.nombre AS estado_nombre,
    je.color AS estado_color,
    jm.nombre AS modelo_nombre,
    js.nombre AS salida_nombre,
    j.programado_para,
    j.iniciado_en,
    j.completado_en,
    j.error,
    j.id_job_padre,
    t.nombre AS template_nombre
FROM jobs j
INNER JOIN jobs_templates t ON j.id_template = t.id
INNER JOIN jobs_tipos jt ON j.id_tipo = jt.id
INNER JOIN jobs_estados je ON j.id_estado = je.id
LEFT JOIN jobs_modelos jm ON j.id_modelo = jm.id
LEFT JOIN jobs_salidas js ON j.id_salida = js.id
WHERE j.id_organizacion = :org_id
  AND j.id_proyecto = :project_id
  AND j.id_version = :version_id
ORDER BY j.created_at DESC;
```

#### 27.10.3. Obtener cadena padre-hijo completa

```sql
-- Obtener todos los hijos de un job (recursivo con CTE)
WITH RECURSIVE job_chain AS (
    SELECT id, id_job_padre, nombre, id_estado, 0 AS nivel
    FROM jobs
    WHERE id = :root_job_id

    UNION ALL

    SELECT j.id, j.id_job_padre, j.nombre, j.id_estado, jc.nivel + 1
    FROM jobs j
    INNER JOIN job_chain jc ON j.id_job_padre = jc.id
)
SELECT jc.*, je.nombre AS estado_nombre, je.color
FROM job_chain jc
INNER JOIN jobs_estados je ON jc.id_estado = je.id
ORDER BY jc.nivel, jc.id;
```

### 27.11. Permisos en MariaDB (OBLIGATORIO)

```sql
-- Lectura de todas las tablas del sistema de jobs
GRANT SELECT ON myllm_projects_db.jobs_tipos TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_estados TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_modelos TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_salidas TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_documentacion TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_entrenamientos TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_resultados TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_generacion TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_templates TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_eventos TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_entradas TO 'myllm_reader'@'localhost';

-- Escritura para el writer
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_tipos TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_estados TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_modelos TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_salidas TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_documentacion TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_entrenamientos TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_resultados TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_generacion TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_templates TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT ON myllm_projects_db.jobs_eventos TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_entradas TO 'myllm_writer'@'localhost';

FLUSH PRIVILEGES;
```

**Regla #41**: `jobs_eventos` solo tiene permisos `INSERT` (nunca UPDATE ni DELETE) para el writer,
reforzando la inmutabilidad del log.

### 27.12. UI en Backoffice — Gestión de Plantillas

#### 27.12.1. Página principal

La gestión de plantillas se presenta con tabs por tipo de job:

```python
rx.tabs.root(
    rx.tabs.list(
        rx.tabs.trigger("Documentación", value="Documentacion"),
        rx.tabs.trigger("Entrenamientos", value="Entrenamientos"),
        rx.tabs.trigger("Resultados", value="Resultados"),
        rx.tabs.trigger("Generación", value="Generacion"),
    ),
    rx.tabs.content(
        templates_table(state, "Documentacion"),  # Tabla de plantillas filtrada
        value="Documentacion",
    ),
    # ... otros tabs
)
```

**Regla #42**: Cada tab filtra plantillas por `jobs_tipos.pagina_backoffice`.

#### 27.12.2. Formulario de creación/edición

```python
rx.dialog.root(
    rx.dialog.content(
        rx.heading("Nueva Plantilla de Job", size="6", color=COLORS["primary"]),
        # Nombre
        rx.input(value=state.template_nombre, on_change=state.set_template_nombre),
        # Tipo (selector)
        rx.select(
            state.available_tipos,
            value=state.selected_tipo,
            on_change=state.set_selected_tipo,
            size="3",
            background_color=COLORS["input"],
            color=COLORS["foreground"],
        ),
        # Modelo LLM (selector)
        rx.select(state.available_modelos, ...),
        # Tipo de salida (selector)
        rx.select(state.available_salidas, ...),
        # Toggles
        rx.switch(checked=state.es_programable, label="Programable"),
        rx.switch(checked=state.acepta_entrada, label="Acepta entrada (puede ser hijo)"),
        rx.switch(checked=state.permite_hijos, label="Permite hijos (puede ser padre)"),
        # Botón guardar
        rx.button(
            "Guardar",
            on_click=state.save_template,
            color_scheme="orange",
            style={"font_weight": "bold", "color": "black"},
        ),
    ),
)
```

**Regla #43**: Seguir las reglas de estilo de backoffice (sección AGENTS.md "Estilos visuales"):
- Títulos: `COLORS["primary"]` (naranja)
- Selectores: `background_color=COLORS["input"]`, `color=COLORS["foreground"]`
- Botones: `color="black"`, `font_weight="bold"`

### 27.13. Reglas de Seguridad (CRÍTICO)

**Regla #44**: NUNCA exponer `configuracion_defecto` directamente al cliente (puede contener
claves internas). Filtrar campos sensibles antes de enviar al frontend.

**Regla #45**: Los jobs de un proyecto/versión solo son visibles para usuarios con rol activo
en ese proyecto (`proyectos_roles` con `active=true` y `id_rol > 0`).

**Regla #46**: El Trainer (Backend IA) se autentica con un token de servicio (no token de usuario)
para reportar eventos y resultados. Este token se configura en `protected_values.py`.

**Regla #47**: Los datos JSON en `datos_entrada`, `datos_salida` y `datos_evento` NO deben
contener información sensible (contraseñas, tokens, etc.). Validar en Backend Core antes de
persistir.

### 27.14. Testing

#### 27.14.1. Tests unitarios

```python
# tests/unit/test_job_template_creation.py

def test_create_job_from_template(monkeypatch):
    """Verifica herencia de valores plantilla → job."""
    monkeypatch.setenv("STORAGE_MODE", "mock")

    template = {
        "id": 1,
        "nombre": "Análisis PDF",
        "id_tipo": 1,
        "id_estado_inicial": 1,
        "id_modelo": 2,
        "id_salida": 2,
        "configuracion_defecto": {"max_paginas": 100},
    }

    job = create_job_from_template(
        template_id=1,
        overrides={"id_organizacion": 1, "id_proyecto": 3, "id_version": 1},
    )

    assert job["nombre"] == "Análisis PDF"  # Heredado
    assert job["id_tipo"] == 1  # Heredado (no sobrescribible)
    assert job["configuracion"]["max_paginas"] == 100  # Heredado
```

#### 27.14.2. Tests de encadenamiento

```python
# tests/unit/test_job_chaining.py

def test_parent_job_creates_children(monkeypatch):
    """Verifica que un job padre crea hijos al completarse."""
    monkeypatch.setenv("STORAGE_MODE", "mock")

    parent_job = create_test_job(permite_hijos=True, configuracion={
        "hijos": [{"id_template": 5}]
    })

    result = complete_job(
        job_id=parent_job["id"],
        datos_salida={"metricas": {"accuracy": 0.95}},
    )

    # Verificar que se creó el hijo
    children = list_jobs(id_job_padre=parent_job["id"])
    assert len(children) == 1
    assert children[0]["datos_entrada"]["metricas"]["accuracy"] == 0.95


def test_child_job_requires_parent():
    """Verifica que un job hijo necesita padre."""
    with pytest.raises(ValueError, match="requiere id_job_padre"):
        create_job_from_template(
            template_id=5,  # Template con acepta_entrada=1
            overrides={"id_organizacion": 1, "id_proyecto": 1, "id_version": 1},
            # Falta id_job_padre
        )
```

#### 27.14.3. Entornos virtuales para tests

| Test | Entorno virtual | Razón |
|------|-----------------|-------|
| Tests de Backend Core (routercore, apicore) | `.venv_backend313` | Acceso a MariaDB |
| Tests de Middleware (routermiddleware) | `.venv_middleware313` | Propagación HTTP |
| Tests de Backoffice (UI) | `.venv_backoffice313` | Componentes Reflex |
| Tests de Trainer (ejecución) | `.venv_trainer312` | Dependencias IA |

### 27.15. Debugging Checklist

Cuando depurar problemas con el sistema de jobs:

1. [ ] Verificar que las tablas catálogo tienen seed data: `SELECT COUNT(*) FROM jobs_tipos`
2. [ ] Verificar FKs: `SELECT * FROM jobs_templates WHERE id_tipo NOT IN (SELECT id FROM jobs_tipos)`
3. [ ] Verificar permisos MariaDB: `SHOW GRANTS FOR 'myllm_writer'@'localhost'`
4. [ ] Verificar estado del job: `SELECT j.*, je.clave FROM jobs j JOIN jobs_estados je ON j.id_estado = je.id WHERE j.id = ?`
5. [ ] Verificar eventos del job: `SELECT * FROM jobs_eventos WHERE id_job = ? ORDER BY fecha_evento`
6. [ ] Verificar cadena padre-hijo: `SELECT * FROM jobs_entradas WHERE id_job_padre = ?`
7. [ ] Revisar logs del Trainer: `src/apps/4_trainer/logs/console.log`
8. [ ] Revisar logs del Backend Core: `src/apps/3_backend/logs/console.log`
9. [ ] Verificar configuración heredada: comparar `jobs_templates.configuracion_defecto` vs `jobs.configuracion`
10. [ ] Verificar registro en cambios: `SELECT * FROM cambios WHERE tipo_cambio LIKE '%job%' ORDER BY fecha_cambio DESC`

### 27.16. Common Pitfalls (Errores Comunes)

#### 27.16.1. Sobrescribir id_tipo al crear job

```python
# ❌ INCORRECTO - Permitir que usuario cambie el tipo
job = create_job(id_tipo=user_input["tipo"])

# ✅ CORRECTO - Heredar siempre de plantilla
job = create_job(id_tipo=template.id_tipo)
```

#### 27.16.2. Crear hijo sin padre

```python
# ❌ INCORRECTO - Template con acepta_entrada=1 sin padre
create_job(template_id=5, id_job_padre=None)

# ✅ CORRECTO - Validar antes de crear
if template.acepta_entrada and not id_job_padre:
    raise ValueError("Plantilla requiere id_job_padre")
```

#### 27.16.3. Escribir directamente en jobs_eventos

```python
# ❌ INCORRECTO - UPDATE en eventos
UPDATE jobs_eventos SET tipo_evento = 'corregido' WHERE id = 1;

# ✅ CORRECTO - Solo INSERT (inmutable)
INSERT INTO jobs_eventos (id_job, tipo_evento, descripcion) VALUES (1, 'correccion', '...');
```

#### 27.16.4. No registrar en tabla cambios

```python
# ❌ INCORRECTO - Crear job sin auditoría
conn.execute(text("INSERT INTO jobs ..."))

# ✅ CORRECTO - Siempre registrar en cambios
conn.execute(text("INSERT INTO jobs ..."))
conn.execute(text("INSERT INTO cambios ..."))  # Auditoría
```

#### 27.16.5. Trainer escribe directamente en BD

```python
# ❌ INCORRECTO - Trainer accede a myllm_projects_db
engine = create_engine("mysql://...@backend:3306/myllm_projects_db")
engine.execute("UPDATE jobs SET ...")

# ✅ CORRECTO - Trainer notifica via API
requests.patch(
    f"http://broker:8008/jobs/{job_id}/complete",
    json={"datos_salida": {...}},
    headers={"X-Client-App": "trainer"},
)
```

### 27.17. Documentación Relacionada

- **Plan de diseño**: `cursor/plans/job_templates_db_design_*.plan.md`
- **Migración SQL**: `infrastructure/database/migrations/011_jobs_templates_system.sql`
- **README.md**: Sección "Sistema de Plantillas y Jobs" (documentada)
- **Diagrama ER**: Ver plan de diseño para diagrama Mermaid completo

---

**⚠️ ADVERTENCIA CRÍTICA**: El sistema de plantillas y jobs gestiona la ejecución de trabajos
de IA que pueden consumir recursos costosos (GPU, tiempo de cómputo). Modificaciones incorrectas
pueden:
- Disparar entrenamientos no autorizados (coste elevado)
- Crear cadenas infinitas de jobs padre-hijo (loop)
- Perder resultados de ejecución
- Corromper el log de eventos (inmutabilidad violada)
- Exponer datos sensibles en campos JSON

**Regla #48 (OBLIGATORIA)**: Al configurar encadenamiento padre-hijo, verificar que NO exista
un ciclo (job A → hijo B → hijo A). Implementar validación de profundidad máxima (recomendado: 5 niveles).

**Regla #49 (OBLIGATORIA)**: NUNCA crear una plantilla con `permite_hijos=1` y `acepta_entrada=1`
que se referencie a sí misma en `configuracion_defecto.hijos`. Esto crea un loop infinito.

**Regla #50 (OBLIGATORIA)**: Antes de modificar cualquier tabla del sistema de jobs, consultar
el plan de diseño y verificar el impacto en las FKs y el encadenamiento.

---

## 28. Ejecución de Jobs en el Trainer: Flujo Backoffice → Trainer → Backend Core (OBLIGATORIO)

Este módulo describe cómo se ejecutan jobs de IA lanzados desde el Backoffice hacia el Trainer,
y cómo el Trainer notifica al Backend Core cuando el procesamiento finaliza. Actualmente hay
**dos flujos paralelos e independientes** implementados: Análisis de Documentación y Análisis
de Metadatos. Ambos siguen el mismo patrón arquitectónico pero con servicios, plantillas y
prompts de fusión completamente separados.

### 28.1. Arquitectura general

```
Backoffice (8006)
     │
     ├─ _is_metadatos_job() → TRUE  → /training/metadatos  ─┐
     │                                                       │
     └─ _is_metadatos_job() → FALSE → /training/documentacion ─┐
                                                                │
     Middleware (8007) → Broker (8008) → Trainer (8004) ◄───────┘
                                              │
                              [Procesamiento asíncrono en thread]
                                              │
                                   ┌──────────┴──────────┐
                                   │                     │
                           [1/2] Ollama            [2/2] Ollama
                         (análisis IA)         (fusión con plantilla)
                                   │                     │
                                   └──────────┬──────────┘
                                              │
                                   Escribe informe .md
                                              │
                               Backend Core (8003) ← Notificación HTTP
                                   (UPDATE jobs + INSERT cambios)
```

**Patrón de comunicación:**
- La petición sigue el flujo estándar: Backoffice → Middleware → Broker → Trainer
- El Trainer responde con un ACK inmediato (síncrono) y procesa en background (asíncrono)
- El procesamiento incluye DOS llamadas a Ollama: análisis + fusión con plantilla Jinja2
- Al terminar, el Trainer llama directamente al Backend Core para actualizar el estado del job

### 28.2. Detección automática del tipo de job (CRÍTICO)

**Archivo:** `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py`

El método `_is_metadatos_job()` decide a qué endpoint enviar el job:

```python
def _is_metadatos_job(self) -> bool:
    nombre_job = self.ad_modal_job.get("nombre", "").lower()
    prompt_lower = self.ad_prompt_final.lower()

    nombre_tiene_metadatos = "metadatos" in nombre_job
    prompt_menciones = prompt_lower.count("metadatos")

    return nombre_tiene_metadatos and prompt_menciones >= 2
```

**Condiciones para enrutar a `/metadatos`:**
1. El **nombre del job** contiene la palabra "metadatos" (case-insensitive)
2. El **prompt final** contiene **2 o más** menciones a "metadatos"

Si ambas condiciones se cumplen → `send_metadatos_to_trainer()` → `/training/metadatos`
En caso contrario → `send_documentacion_to_trainer()` → `/training/documentacion`

**Regla #59**: Al implementar nuevos tipos de job, seguir este mismo patrón de detección
en `ad_send_to_trainer()` añadiendo una nueva condición antes del `else` final.

### 28.3. Flujos paralelos implementados

| Aspecto | Documentación | Metadatos |
|---------|--------------|-----------|
| **Endpoint Middleware** | `POST /training/documentacion` | `POST /training/metadatos` |
| **Endpoint Trainer** | `POST /trainer/documentacion` | `POST /trainer/metadatos` |
| **Servicio** | `documentacion_service.py` | `metadatos_service.py` |
| **Función principal** | `process_documentacion()` | `process_metadatos()` |
| **Plantilla Jinja2** | `evaluacion_documental.j2` | `evaluacion_metadatos.j2` |
| **Prompt de fusión (BD)** | `formateador_documental_documentos` | `formateador_documental_metadatos` |
| **Prefijo de logs** | `[DOCUMENTACION]` | `[METADATOS]` |
| **Fichero de salida** | `*_analisis_documental.md` | `*_analisis_metadatos.md` |
| **tipo_cambio** | `evaluacion_documental` | `evaluacion_metadatos` |
| **Nombre thread** | `doc-analysis-job-{id}` | `metadata-analysis-job-{id}` |

### 28.4. Propagación por la cadena de servicios

Cada flujo tiene su propia cadena completa de métodos y endpoints:

**Flujo Documentación:**

| Capa | Archivo | Endpoint/Método |
|------|---------|-----------------|
| Backoffice API Client | `6_web_backoffice/adapters/api_client.py` | `send_documentacion_to_trainer()` |
| Middleware API | `7_service_frontend/apife.py` | `POST /training/documentacion` |
| Middleware Router | `7_service_frontend/routermiddleware.py` | `send_documentacion()` |
| Broker Client | `7_service_frontend/broker_backend_client.py` | `send_documentacion()` |
| Broker API | `8_service_backend/apibe.py` | `POST /training/documentacion` |
| Broker Router | `8_service_backend/routerbroker.py` | `send_documentacion()` |
| Trainer Client | `8_service_backend/interfacetotrainer.py` | `send_documentacion()` |
| Trainer API | `4_trainer/apitrainer.py` | `POST /trainer/documentacion` |

**Flujo Metadatos:**

| Capa | Archivo | Endpoint/Método |
|------|---------|-----------------|
| Backoffice API Client | `6_web_backoffice/adapters/api_client.py` | `send_metadatos_to_trainer()` |
| Middleware API | `7_service_frontend/apife.py` | `POST /training/metadatos` |
| Middleware Router | `7_service_frontend/routermiddleware.py` | `send_metadatos()` |
| Broker Client | `7_service_frontend/broker_backend_client.py` | `send_metadatos()` |
| Broker API | `8_service_backend/apibe.py` | `POST /training/metadatos` |
| Broker Router | `8_service_backend/routerbroker.py` | `send_metadatos()` |
| Trainer Client | `8_service_backend/interfacetotrainer.py` | `send_metadatos()` |
| Trainer API | `4_trainer/apitrainer.py` | `POST /trainer/metadatos` |

**Validación de permisos:** Ambos flujos validan `training_create` en el Middleware.

### 28.5. Procesamiento asíncrono en el Trainer (flujo de 6 pasos)

Ambos servicios (`documentacion_service.py` y `metadatos_service.py`) siguen exactamente
el mismo flujo de 6 pasos:

#### Paso 1: Lectura de archivos del storage externo

```
Ruta: {backend_ia_base_storage}/{ORG#####}/{PRJ#####}/{v###}/
```

- Recorre recursivamente todos los archivos de la versión
- Clasifica archivos en **texto** (lee contenido) y **binarios** (solo registra en árbol)
- Extensiones de texto: `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.py`, `.yml`, `.sql`, etc.
- Genera: árbol de directorios, contenido concatenado, estadísticas

#### Paso 2: Construcción del prompt completo

```
{prompt_final del usuario (identidad + contexto + solicitud + modalidad)}

=== ESTRUCTURA DE DIRECTORIOS ===
{árbol de archivos con tamaños}

=== CONTENIDO DE ARCHIVOS ===
{contenido concatenado de archivos de texto}
```

#### Paso 3: Primera llamada a Ollama [1/2] — Análisis

- Modelo: el especificado en el job (ej: `llama3.1:8b`)
- `num_ctx`: calculado dinámicamente (~tokens estimados + 4096, entre 8192 y 65536)
- `num_predict`: -1 (sin límite de tokens de respuesta)
- `temperature`: 0.3
- Usa `OllamaAdapter.generate()` con `GenerateRequestDto`

**Cálculo dinámico de `num_ctx`:**
```python
estimated_tokens = len(prompt_text) // 3
num_ctx = min(65536, max(8192, ((estimated_tokens + 4096) // 2048 + 1) * 2048))
```

#### Paso 4: Enriquecimiento con Jinja2 + segunda llamada a Ollama [2/2]

Este es el paso más complejo. Se realiza en sub-pasos:

**4a. Obtener datos de BD:**
- Nombre de la organización: `SELECT organization_name FROM myllm_core_db.organizations`
- Nombre del proyecto: `SELECT nombre FROM myllm_projects_db.proyectos`
- Usa `pymysql` con credenciales de `mariadb_reader` desde `protected_values.py`

**4b. Calcular ruta de salida:**
- Usa `_compute_output_path()` con `backend_ia_internal_storage`
- Nombre del fichero:
  - Documentación: `{YYYY_MM_DD_HHMM}_analisis_documental.md`
  - Metadatos: `{YYYY_MM_DD_HHMM}_analisis_metadatos.md`

**4c. Renderizar plantilla Jinja2:**
- Plantilla: `evaluacion_documental.j2` o `evaluacion_metadatos.j2`
- Variables: payload del job + nombres de BD + estadísticas + respuesta de Ollama + tiempos
- Resultado: `plantilla_informe` (markdown temporal con estructura formal)

**4d. Obtener prompt de fusión desde BD:**
- `SELECT prompt FROM myllm_projects_db.prompts_identidades WHERE name = :prompt_name`
- Documentación: `formateador_documental_documentos`
- Metadatos: `formateador_documental_metadatos`

**4e. Construir prompt de fusión:**
- Reemplaza `{plantilla_informe}` con el markdown temporal renderizado
- Reemplaza `{analisis_ollama}` con la respuesta del paso 3

**4f. Segunda llamada a Ollama [2/2] — Fusión:**
- `num_ctx`: calculado dinámicamente para el prompt de fusión
- `temperature`: 0.2 (más determinista para preservar formato)
- Fusiona la plantilla formal con el análisis de Ollama en un informe final cohesivo

**Fallbacks:**
- Si no existe el prompt de fusión → escribe la plantilla directamente
- Si Ollama devuelve respuesta vacía → escribe la plantilla como fallback

#### Paso 5: Escritura del informe final

```
Ruta: {backend_ia_internal_storage}/{ORG#####}/{PRJ#####}/{v###}/{fichero}.md
```

#### Paso 6: Notificación al Backend Core

- Llama a `PATCH /jobs/{job_id}/complete` en Backend Core
- Envía: `id_organizacion`, `id_proyecto`, `id_version`, `descripcion`, `referencia_salida`, `tipo_cambio`
- El Backend Core ejecuta una transacción atómica:

```sql
-- Registrar evento en tabla cambios
INSERT INTO cambios
    (id_version, fecha_cambio, tipo_cambio, descripcion, creado_at, id_proyecto, id_organizacion)
VALUES
    (:id_version, NOW(), :tipo_cambio, :descripcion, NOW(), :id_proyecto, :id_organizacion);

-- Actualizar estado del job
UPDATE jobs
SET id_estado = :id_estado,
    completado_en = NOW(),
    referencia_salida = :referencia_salida,
    id_cambio = LAST_INSERT_ID()
WHERE id = :job_id;
```

**Estados de job:**
- `id_estado=4` → Finalizado (éxito)
- `id_estado=3` → Error

### 28.6. Plantillas Jinja2 del Trainer

Las plantillas están en `src/apps/4_trainer/templates/` y definen la estructura formal
del informe que se fusiona con el análisis de Ollama.

**Variables esperadas por ambas plantillas:**

| Categoría | Variables |
|-----------|----------|
| **Payload del job** | `id_job`, `id_organizacion`, `id_proyecto`, `id_version`, `nombre_job`, `descripcion_job`, `id_template`, `template_nombre`, `modelo_nombre`, `salida_nombre`, `estado_nombre` |
| **Datos derivados** | `nombre_organizacion`, `nombre_proyecto`, `org_folder`, `prj_folder`, `ver_folder`, `ruta_external`, `ruta_internal`, `ruta_salida` |
| **Estadísticas** | `num_text`, `num_binary`, `total_files`, `total_kb`, `tree_text` |
| **Ollama** | `ollama_response` |
| **Ejecución** | `fecha_ejecucion`, `hora_ejecucion`, `tiempo_ollama`, `tiempo_total` |

**Secciones de los informes:**

1. Ficha Técnica del Informe (tabla con metadatos)
2. Presentación (contexto y propósito del análisis)
3. Metodología de Evaluación (criterios y preguntas clave)
4. Estadísticas de Archivos (métricas + árbol de directorios)
5. Resultados del Análisis (respuesta de Ollama embebida)
6. Conclusiones y Recomendaciones
7. Trazabilidad de Ejecución (tiempos, rutas, modelo)
8. Referencias de Fuentes

**Diferenciación:**
- `evaluacion_documental.j2`: Orientada a estructura documental, calidad de contenido y optimización RAG
- `evaluacion_metadatos.j2`: Orientada a gobernanza de datos, metadatos embebidos (EXIF, XMP, Dublin Core) y detección de datos sensibles

### 28.7. Prompts de fusión en base de datos

Los prompts de fusión están almacenados en `myllm_projects_db.prompts_identidades` y
definen cómo Ollama debe combinar la plantilla formal con el análisis de IA.

| Prompt (campo `name`) | Propósito |
|------------------------|-----------|
| `formateador_documental_documentos` | Fusión para análisis de documentación (estructura, contenido, RAG) |
| `formateador_documental_metadatos` | Fusión para análisis de metadatos (EXIF, XMP, privacidad, gobernanza) |

**Estructura de los prompts de fusión:**

```
### ROL
Eres un Ingeniero de Documentación/Datos Senior especializado en...

### CONTEXTO
Recibirás dos documentos:
1. PLANTILLA_INFORME: Documento generado por el sistema myllm (estructura formal)
2. ANALISIS_OLLAMA: Resultado de análisis de IA (contenido generado)

### TAREA
Fusiona ambos documentos para producir un INFORME_FINAL...

### REGLAS CRÍTICAS DE FUSIÓN
1-10+ reglas específicas para cada tipo de fusión

### ENTRADA
{plantilla_informe}
{analisis_ollama}

### SALIDA ESPERADA
Un único documento Markdown cohesivo...
```

**Placeholders obligatorios en el prompt:**
- `{plantilla_informe}` → Se reemplaza con el markdown renderizado de la plantilla Jinja2
- `{analisis_ollama}` → Se reemplaza con la respuesta de la primera llamada a Ollama

### 28.8. Logging obligatorio en el Trainer

**CRÍTICO:** Todo el procesamiento asíncrono debe escribir en `logs/console.log`.
Cada flujo usa su propio prefijo:

| Prefijo | Flujo | Indicadores |
|---------|-------|-------------|
| `[DOCUMENTACION]` | Análisis de documentación | `[1/2]` análisis, `[2/2]` fusión |
| `[METADATOS]` | Análisis de metadatos | `[1/2]` análisis, `[2/2]` fusión |

**Eventos a loguear (aplicable a ambos flujos):**

| Evento | Nivel | Ejemplo |
|--------|-------|---------|
| Solicitud recibida | INFO | `[DOCUMENTACION] Solicitud recibida: job_id=5 org=1 prj=3 ver=2` |
| Thread lanzado | INFO | `[DOCUMENTACION] Thread background lanzado para job_id=5` |
| Lectura de archivos | INFO | `[DOCUMENTACION] Leyendo archivos de: /path/to/version` |
| Resultado de lectura | INFO | `[DOCUMENTACION] 12 archivos texto, 3 binarios, 450 KB total` |
| Prompt construido | INFO | `[DOCUMENTACION] Prompt de análisis construido: 25000 caracteres` |
| Ollama análisis [1/2] | INFO | `[DOCUMENTACION] [1/2] Enviando a Ollama: modelo=llama3.1:8b num_ctx=26624` |
| Respuesta análisis | INFO | `[DOCUMENTACION] [1/2] Respuesta recibida: 8500 caracteres en 5m 32s` |
| Datos de BD | INFO | `[DOCUMENTACION] Datos de BD: org='myllm', prj='dptocomercial'` |
| Plantilla renderizada | INFO | `[DOCUMENTACION] Plantilla Jinja2 renderizada: 7078 caracteres` |
| Prompt fusión obtenido | INFO | `[DOCUMENTACION] Prompt de fusión obtenido: 4109 caracteres` |
| Ollama fusión [2/2] | INFO | `[DOCUMENTACION] [2/2] Enviando fusión a Ollama: modelo=llama3.1:8b num_ctx=8192` |
| Respuesta fusión | INFO | `[DOCUMENTACION] [2/2] Respuesta de fusión recibida: 12000 caracteres en 3m 15s` |
| Informe escrito | INFO | `[DOCUMENTACION] Informe FINAL fusionado escrito en: /path/to/output.md` |
| Notificación a Core | INFO | `[DOCUMENTACION] Backend Core actualizado: id_cambio=42` |
| Proceso completado | INFO | `[DOCUMENTACION] Proceso completado exitosamente para job_id=5 en 9m 10s` |
| Error | ERROR | `[DOCUMENTACION][ERROR] descripción del error para job_id=5 (tras 5m 32s)` |

### 28.9. Variables de entorno requeridas

| Variable | Uso | Ejemplo (macbook) |
|----------|-----|-------------------|
| `backend_ia_base_storage` | Ruta de lectura (external) | `~/data/anewhope/files/trainer_server/external` |
| `backend_ia_internal_storage` | Ruta de escritura (internal) | `~/data/anewhope/files/trainer_server/internal` |
| `backend_core_base_url` | URL del Backend Core para notificaciones | `http://localhost:8003` |

**Credenciales de BD (solo lectura, desde `protected_values.py`):**

| Variable | Uso |
|----------|-----|
| `mariadb_host` | Host de MariaDB |
| `mariadb_port` | Puerto de MariaDB |
| `mariadb_reader_user` | Usuario de solo lectura (myllm_reader) |
| `mariadb_reader_password` | Contraseña del reader |

### 28.10. Timeout de Ollama

**CRÍTICO:** El timeout del adaptador de Ollama está configurado en `apitrainer_ollama.py`.
En macbook (CPU, sin GPU) los tiempos de procesamiento pueden ser muy largos.

| Entorno | Timeout | Motivo |
|---------|---------|--------|
| macbook (CPU) | 28800s (8 horas) | Análisis + fusión en CPU pueden tardar 6+ horas |
| dev/pre/pro (GPU) | Ajustar según hardware | Con GPU debería ser mucho más rápido |

**Regla #60**: Nunca reducir el timeout sin verificar primero los tiempos reales de procesamiento
en el entorno objetivo.

### 28.11. DTOs compartidos entre capas

Ambos flujos usan DTOs con la misma estructura base:

```python
class DocumentacionRequest(BaseModel):  # o MetadatosRequest
    id_job: int = 0
    id_organizacion: int
    id_proyecto: int
    id_version: int
    nombre_job: str = ""
    descripcion_job: str = ""
    id_template: int = 0
    template_nombre: str = ""
    modelo_nombre: str = ""
    salida_nombre: str = ""
    estado_nombre: str = ""
    prompt_final: str = ""
    identity_type_id: int | None = None
```

**Regla #57**: Al implementar nuevos tipos de job, usar un DTO equivalente con los mismos
campos base (`id_job`, `id_organizacion`, `id_proyecto`, `id_version`, `prompt_final`,
`modelo_nombre`) más campos específicos del tipo.

### 28.12. Endpoint de completado en Backend Core

```
PATCH /jobs/{job_id}/complete
```

**Payload:**
```python
class JobCompleteRequest(BaseModel):
    job_id: int
    id_organizacion: int
    id_proyecto: int
    id_version: int
    descripcion: str = ""
    referencia_salida: str = ""
    tipo_cambio: str = "evaluacion_documental"  # o "evaluacion_metadatos"
    id_estado: int = 4  # 4=Finalizado, 3=Error
```

**Regla #58**: Este endpoint es reutilizable por TODOS los tipos de job. Solo cambia
`tipo_cambio` y `descripcion` según el tipo de procesamiento.

### 28.13. Reglas para implementar nuevos tipos de job (OBLIGATORIO)

Los siguientes tipos de job seguirán el mismo patrón arquitectónico:

| Tipo de Job | Descripción | Estado |
|-------------|-------------|--------|
| `analisis_documentacion` | Análisis de estructura documental y contenido | **Implementado** |
| `analisis_metadatos` | Análisis de metadatos de ficheros | **Implementado** |
| `entrenamiento` | Fine-tuning de modelos LLM | Pendiente |
| `analisis_resultados` | Evaluación de resultados de entrenamiento | Pendiente |
| `crear_modelo_llm` | Generación final de modelos LLM | Pendiente |

**Regla #51**: Todo nuevo tipo de job DEBE seguir el patrón implementado:
1. Método de detección en el Backoffice (`_is_xxx_job()`) que examina nombre y prompt
2. Función dedicada en `api_client.py` del backoffice (`send_xxx_to_trainer()`)
3. Endpoint dedicado en Middleware, Broker y Trainer (`/training/xxx` → `/trainer/xxx`)
4. Servicio dedicado en el Trainer (`xxx_service.py` con `process_xxx()`)
5. Plantilla Jinja2 dedicada (`evaluacion_xxx.j2`)
6. Prompt de fusión dedicado en BD (`prompts_identidades`)
7. Procesamiento en background thread (daemon=True) con logging `[XXX]`
8. Notificación al Backend Core via `PATCH /jobs/{job_id}/complete`
9. INSERT en tabla `cambios` + UPDATE en tabla `jobs` (transacción atómica)

**Regla #52**: El Trainer accede a la BD SOLO en modo lectura (con `myllm_reader`) para
obtener nombres de organización/proyecto y prompts de fusión. Las escrituras se hacen
siempre via HTTP al Backend Core.

**Regla #53**: Cada tipo de job DEBE crear un servicio COMPLETAMENTE independiente:
- `documentacion_service.py` → Análisis de documentación (**implementado**)
- `metadatos_service.py` → Análisis de metadatos (**implementado**)
- `entrenamiento_service.py` → Entrenamiento de modelos (futuro)
- `resultados_service.py` → Análisis de resultados (futuro)
- `generacion_service.py` → Generación de modelos (futuro)

**Regla #54**: El prompt se construye siempre en 4 partes (identidad + contexto + solicitud + modalidad)
desde el Backoffice, y se envía ya compuesto al Trainer como `prompt_final`.

**Regla #55**: Todo job que lea archivos del storage debe usar las funciones de
`storage_access_structure.py` (`get_folder_by_id_organization`, `get_folder_by_id_project`,
`get_folder_by_id_version`) para construir rutas.

**Regla #56**: El resultado de cada job se escribe en el storage interno
(`backend_ia_internal_storage`) con marca de tiempo en el nombre del fichero.

### 28.14. Checklist para implementar un nuevo tipo de job

Al implementar un nuevo tipo de job (ej: `entrenamiento`):

- [ ] **Backoffice**: Crear `_is_xxx_job()` y `send_xxx_to_trainer()` en `api_client.py`
- [ ] **Backoffice**: Añadir condición en `ad_send_to_trainer()` antes del `else`
- [ ] **Middleware**: Crear `XxxRequest`/`XxxResponse` en `apife.py`
- [ ] **Middleware**: Crear endpoint `POST /training/xxx` en `apife.py`
- [ ] **Middleware**: Crear `send_xxx()` en `routermiddleware.py`
- [ ] **Middleware**: Crear `send_xxx()` en `broker_backend_client.py`
- [ ] **Broker**: Crear DTOs en `apibe.py`
- [ ] **Broker**: Crear endpoint `POST /training/xxx` en `apibe.py`
- [ ] **Broker**: Crear `send_xxx()` en `routerbroker.py`
- [ ] **Broker**: Crear `send_xxx()` en `interfacetotrainer.py`
- [ ] **Trainer**: Crear DTOs en `apitrainer.py`
- [ ] **Trainer**: Crear endpoint `POST /trainer/xxx` con thread background
- [ ] **Trainer**: Crear `xxx_service.py` con `process_xxx()`
- [ ] **Trainer**: Crear plantilla `evaluacion_xxx.j2` en `templates/`
- [ ] **BD**: Crear prompt de fusión en `prompts_identidades`
- [ ] **Docs**: Actualizar esta sección y README.md

### 28.15. Documentación relacionada

**Servicios del Trainer:**
- `src/apps/4_trainer/documentacion_service.py` → Análisis de documentación
- `src/apps/4_trainer/metadatos_service.py` → Análisis de metadatos

**Endpoints del Trainer:**
- `src/apps/4_trainer/apitrainer.py` → `POST /trainer/documentacion` y `POST /trainer/metadatos`

**Plantillas Jinja2:**
- `src/apps/4_trainer/templates/evaluacion_documental.j2`
- `src/apps/4_trainer/templates/evaluacion_metadatos.j2`

**Backend Core:**
- `src/apps/3_backend/apicore.py` → `PATCH /jobs/{job_id}/complete`
- `src/apps/3_backend/routercore.py` → `complete_job()`

**Otros:**
- **Sistema de Plantillas:** Sección 27 de este documento
- **Migración SQL:** `infrastructure/database/migrations/011_jobs_templates_system.sql`

---

## 29. Roadmap: Flujo completo de entrenamiento y generación de modelos LLM (CRÍTICO)

**OBLIGATORIO:** Este roadmap define el orden de implementación de las funcionalidades restantes
para completar el ciclo de vida de un modelo LLM. Cada fase depende de la anterior.

### Flujo completo del sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FLUJO COMPLETO: Entrenamiento → Evaluación → Generación → Descarga        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PÁGINA: Entrenamientos (backoffice)                                       │
│  ┌───────────────────────────────────────────────────────┐                 │
│  │ 1. Visor de versiones pendientes de entrenamiento     │                 │
│  │ 2. Botón "Enviar al Trainer" → ACK                   │                 │
│  │ 3. Panel "Evolución entrenamiento" (fases del trainer)│                 │
│  │    📥 Recepción → 🔍 Validación → 📊 Preparación    │                 │
│  │    → ⚙️ Configuración → 🏋️ Entrenamiento            │                 │
│  └───────────────────────┬───────────────────────────────┘                 │
│                          │ Entrenamiento completado                        │
│                          ▼                                                 │
│  PÁGINA: Análisis Resultados (backoffice)                                  │
│  ┌───────────────────────────────────────────────────────┐                 │
│  │ Evaluación de métricas y calidad del modelo entrenado │                 │
│  │ → Si resultados NO óptimos: volver a Entrenamientos   │                 │
│  │   (reentrenamiento con ajustes)                       │                 │
│  │ → Si resultados ÓPTIMOS: proceder a Crear LLM         │                 │
│  └───────────────────────┬───────────────────────────────┘                 │
│                          │ ◄── BUCLE iterativo ──►                         │
│                          ▼                                                 │
│  PÁGINA: Crear LLM (backoffice)                                            │
│  ┌───────────────────────────────────────────────────────┐                 │
│  │ Generación del modelo LLM definitivo                  │                 │
│  │ Empaquetado y preparación para distribución           │                 │
│  └───────────────────────┬───────────────────────────────┘                 │
│                          │ Modelo generado                                 │
│                          ▼                                                 │
│  PÁGINA: Descargas (backoffice + frontend)                                 │
│  ┌───────────────────────────────────────────────────────┐                 │
│  │ Backoffice: soporte al admin de org para descargas    │                 │
│  │ Frontend: descarga segura para admin de organización  │                 │
│  │ → Procedimiento de seguridad para descarga            │                 │
│  │ → Solo identity_type_id in (1, 2) pueden descargar    │                 │
│  └───────────────────────────────────────────────────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Orden de implementación (roadmap secuencial)

| Orden | Página | Componente | Estado | Descripción |
|-------|--------|------------|--------|-------------|
| **1** | Entrenamientos | Visor versiones pendientes | ✅ Completado | Tabla con versiones donde `entrenamiento_inicial_solicitado=true` |
| **2** | Entrenamientos | Botón "Enviar al Trainer" | ✅ Completado | Endpoint `/entrenamientos` con ACK |
| **3** | Entrenamientos | Panel evolución | ✅ Completado | Timeline de 5 fases del proceso de entrenamiento |
| **4** | Trainer | Proceso de entrenamiento | 🔜 Siguiente | Implementar las 5 fases en el trainer |
| **5** | Análisis Resultados | Evaluación de métricas | ⏳ Pendiente | Visualización de resultados del entrenamiento |
| **6** | Entrenamientos | Reentrenamiento | ⏳ Pendiente | Bucle Entrenamientos ↔ Análisis Resultados |
| **7** | Crear LLM | Generación modelo definitivo | ⏳ Pendiente | Cuando resultados son óptimos |
| **8** | Descargas (backoffice) | Soporte descarga | ⏳ Pendiente | Panel de soporte al admin de org |
| **9** | Descargas (frontend) | Descarga segura | ⏳ Pendiente | Procedimiento de seguridad para admin org |

### Reglas de diseño del roadmap

1. **Separación de responsabilidades por página:**
   - ✅ **Entrenamientos**: Solo el proceso de entrenamiento (5 fases del trainer)
   - ✅ **Análisis Resultados**: Solo evaluación de métricas y calidad
   - ✅ **Crear LLM**: Solo generación del modelo definitivo
   - ✅ **Descargas**: Solo distribución segura del modelo

2. **Bucle iterativo:**
   - El usuario puede ir y venir entre **Entrenamientos** y **Análisis Resultados**
   - Cada iteración puede ajustar hiperparámetros o datos antes de reentrenar
   - El bucle termina cuando el usuario decide que los resultados son óptimos

3. **Flujo entre páginas:**
   - Entrenamientos → trainer procesa → notifica progreso → completa
   - Usuario navega a Análisis Resultados → evalúa métricas
   - Si no satisfecho → vuelve a Entrenamientos (reentrenamiento)
   - Si satisfecho → navega a Crear LLM
   - Modelo generado → disponible en Descargas

4. **Seguridad en Descargas:**
   - Solo `identity_type_id in (1, 2)` (SuperAdmin, Admin Org) pueden descargar
   - La página Descargas estará en **ambas** aplicaciones (frontend + backoffice)
   - Procedimiento de seguridad específico antes de permitir descarga

### Notificaciones del Trainer al Backoffice

El trainer notifica al backoffice el avance de cada fase del entrenamiento.
Estas notificaciones actualizan el panel "Evolución entrenamiento":

| Fase (key) | Notificación | Actualización UI |
|------------|-------------|-----------------|
| `recepcion` | Solicitud recibida (ACK) | Fase completada automáticamente |
| `validacion` | Contenido validado | `ent_evo_advance_to_phase("preparacion")` |
| `preparacion` | Dataset preparado | `ent_evo_advance_to_phase("configuracion")` |
| `configuracion` | Modelo configurado | `ent_evo_advance_to_phase("entrenamiento")` |
| `entrenamiento` | Entrenamiento completado | `ent_evo_complete_all()` |
| (error) | Error en cualquier fase | `ent_evo_update_phase(key, "error")` |

### Archivos clave por funcionalidad

**Entrenamientos (completado):**
- Trainer: `src/apps/4_trainer/apitrainer.py` → `POST /trainer/entrenamientos`
- Broker: `src/apps/8_service_backend/` → routing a trainer
- Middleware: `src/apps/7_service_frontend/` → `POST /training/entrenamientos`
- Backoffice UI: `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py`
- Backoffice API: `src/apps/6_web_backoffice/adapters/api_client.py`

**Proceso de entrenamiento en Trainer (siguiente):**
- `src/apps/4_trainer/apitrainer.py` → endpoint receptor
- `src/apps/4_trainer/entrenamiento_service.py` → servicio de entrenamiento (por crear)

**Análisis Resultados (pendiente):**
- `src/apps/6_web_backoffice/` → página "Análisis Resultados"

**Crear LLM (pendiente):**
- `src/apps/6_web_backoffice/` → página "Crear LLM"
- `src/apps/4_trainer/` → servicio de generación

**Descargas (pendiente):**
- `src/apps/6_web_backoffice/` → página "Descargas" (backoffice)
- `src/apps/5_web_frontend/` → página "Descargas" (frontend)
- Procedimiento de seguridad para descarga

---
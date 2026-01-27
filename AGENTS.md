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

## 5.3 Nomenclatura de carpetas en storage
* **Obligatorio:** Para construir nombres de carpeta por organización y proyecto
  se deben usar los helpers de `src/2_shared_application/storage_access_structure.py`
  (`get_folder_by_id_organization`, `get_folder_by_id_project`). No se permite
  formatear manualmente los strings `ORGXXXX` o `PRJXXXX` en código de aplicación.

## 5.4 Base de datos de proyectos (sin mocks)
* **Obligatorio:** La base `myllm_projects_db` no tiene espejo en JSON. Cualquier
  operación debe consultarse directamente en MariaDB, sin fallback a mocks.

### Scripts de mantenimiento
- `clear_caches.sh`: limpia caches de Reflex (`.web`, `.states`) y caches de tooling
  (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `.hypothesis`).

### Modos de almacenamiento (middleware)
- `STORAGE_MODE`: `mock` (solo JSON), `mock_and_db` (JSON + replica en broker),
  `db_only` (solo broker backend).
- `BROKER_BACKEND_BASE_URL`: URL del broker backend para persistencia.

### Sincronización DB/JSON (middleware)
- **Obligatorio:** El proceso periódico de sincronización DB/JSON debe mantenerse
  operativo y documentado en `README.md`, incluyendo el log
  `src/apps/7_service_frontend/logs/sync_database_and_jsons.log` y el intervalo
  `SYNC_DATABASE_INTERVAL_SECONDS`.
- **Control:** El switch `active_sync_db_jsons` (o `ACTIVE_SYNC_DB_JSONS` en entorno)
  habilita/deshabilita la sincronización. Recomendado `0` en producción.
- **Producción:** `STORAGE_MODE` en `.env` debe estar en `db_only`.

### Configuración por entorno
- **Orden de carga:** primero `.env`, luego `env.yaml`, finalmente `protected_values.py` del entorno activo.
- **Selección de entorno:** `.env` debe definir `environment: <entorno>` o `ENVIRONMENT=<entorno>`.
- **Variables públicas:** `infrastructure/environments/<entorno>/env.yaml`.
- **Ubicación sensibles:** `infrastructure/environments/<entorno>/protected_values.py`.
- **Uso obligatorio:** cargar valores con `src/2_shared_application/config/env_settings.py`.
- **Prohibido:** importar `protected_values` directamente en código de aplicación.
- **Plataformas:** `macbook` usa macOS 14.8.1; `dev/pre/pro` usan Oracle Linux 10.

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
| `.venv_frontend313` | 8005 | `5_web_frontend`, `2_shared_application` | ✅ Usa entorno | ❌ Docker (deps en imagen) |
| `.venv_backoffice313` | 8006 | `6_web_backoffice` | ✅ Usa entorno | ❌ Docker (deps en imagen) |
| `.venv_middleware313` | 8007 | `7_service_frontend` | ✅ Usa entorno | ❌ Docker (deps en imagen) |
| `.venv_broker313` | 8008 | `8_service_backend` | ✅ Usa entorno | ❌ Docker (deps en imagen) |

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
- **Dockerfiles por app:** cada `src/apps/*` debe tener `Dockerfile` y `docker_execution.sh`.
  - `docker_execution.sh` carga `.env` + `env.yaml` del entorno y ejecuta la imagen.
  - Expone el puerto fijo asignado según regla: `8000 + <primer_dígito_carpeta>`.
- **Compose por servidor:** usar `infrastructure/servers/*/docker-compose.yml`.
  - `frontend/`: nginx, 5_web_frontend, 6_web_backoffice, 7_service_frontend
  - `backend/`: 8_service_backend, 3_backend, fmanagement, mariadb
  - `trainer/`: 4_trainer (placeholder), keras_service (placeholder)
  - `macbook/`: solo aplicaciones internas (sin servicios externos dockerizados)
- **Macbook:** MariaDB y Keras no se dockerizan; se usan instalaciones nativas.
- **Linux:** servicios externos (nginx, mariadb, fmanagement) se despliegan en Docker.

### Sincronización OTP (frontend)
- **Obligatorio:** Al actualizar OTP, el cambio debe persistirse en JSON y MariaDB
  de forma sincrónica (modo `mock_and_db` o `db_only`).
- **Validación:** Debe existir verificación de consistencia entre `users.json` y la
  tabla `users`, con registro en `src/apps/5_web_frontend/logs/frontend_secure.log`.

### Agentes automáticos por proyecto
- **Obligatorio:** Al crear un proyecto se generan 4 agentes automáticos con el
  patrón `agente_rol_organizacion_proyecto` y roles `identity_type_id` 10-13.
- **Persistencia:** Los agentes deben guardarse en `users.json` y en la tabla `users`.

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
  - `go_to_backoffice()`: Navegar al backoffice (actualiza `current_app`)
  - `go_to_frontend()`: Regresar al frontend
  - `logout()`: Cerrar sesión en ambas apps
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

### Roles y Permisos por Defecto

El sistema define roles con permisos predefinidos. Usa `low_level_permissions.json` como referencia única.

| identity_type_id | Rol | Permisos característicos |
|------------------|-----|--------------------------|
| 1 | SuperAdmin | Todos los permisos = `true` |
| 2 | Administrador Org | CRUD completo en proyectos, versiones, carpetas, archivos |
| 3 | Editor | Crear/editar proyectos y archivos, sin eliminar |
| 4 | Lector | Solo lectura (read, list) |
| 5 | Auditor | Solo lectura de logs y configuración |
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

## Regla de puertos (estándar)

Cada aplicación usa **puerto fijo 8000 + el primer número del nombre de su carpeta**:

- `3_backend` → **8003**
- `5_web_frontend` → **8005**
- `6_web_backoffice` → **8006** (reservado)
- `7_service_frontend` → **8007**
- `8_service_backend` → **8008** (reservado)

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

### Trazabilidad X-Client-App (regla obligatoria)

**Propósito:** Identificar el origen de cada petición a través de toda la cadena de servicios para
auditoría, debugging y correlación de logs.

**Header:** `X-Client-App`

**Flujo de propagación:**
```
Frontend/Backoffice → Middleware → Broker → Backend Core → fmanagement
     [frontend]        [propaga]    [propaga]  [propaga]    [recibe]
```

**Valores estándar por servicio:**
| Servicio | Valor X-Client-App | Archivo de implementación |
|----------|-------------------|---------------------------|
| `5_web_frontend` | `frontend` | `adapters/api_client.py` |
| `6_web_backoffice` | `backoffice` | `adapters/api_client.py` |
| `7_service_frontend` | `middleware` (origen) | `broker_backend_client.py` |
| `8_service_backend` | propaga origen | `interfacetocore.py` |
| `3_backend` | propaga origen | `apicore.py` |

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


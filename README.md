# Anewhope

Proyecto para gestionar infraestructura, aplicaciones y flujos de personalización de modelos LLM.

## Estructura principal

- `info.txt`: guía rápida para crear y activar el entorno virtual, además de notas de operación.
- `protected_values.py`: variables sensibles requeridas por los procesos de cifrado.
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

## ADRs

- `src/docs/stack_of_technologies.adr`: justifica el uso de Python 3.13 y el downgrade temporal desde 3.14.

## Entorno virtual

El proyecto usa **Python 3.13** como versión base. Para evitar conflictos de dependencias, se mantienen
entornos separados:

- Frontend: `.venv_frontend313`
- Middleware: `.venv_middleware313`

Ejemplo en macOS / Linux:

```bash
python3.13 -m venv .venv_frontend313
source .venv_frontend313/bin/activate
```

## Scripts útiles

- `clear_caches.sh`: limpia caches de Reflex (`.web`, `.states`) y caches de tooling
  (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `.hypothesis`).

Uso:

```bash
./clear_caches.sh
```

## Servicio frontend en contenedor

El servicio `7_service_frontend` puede ejecutarse de forma independiente en Docker.
Los `Dockerfile` del frontend y middleware usan **Python 3.13** (`python:3.13-slim`) para
mantener compatibilidad con dependencias.

```bash
cp src/apps/7_service_frontend/.env.example src/apps/7_service_frontend/.env
docker compose -f src/apps/7_service_frontend/docker-compose.yml up --build
```

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

Dependencias del servicio (pip):
- `src/apps/7_service_frontend/requirements.txt`

### Modos de almacenamiento (middleware)

El middleware puede operar con tres modos configurables mediante `STORAGE_MODE`:

- `mock`: usa únicamente los ficheros JSON mockeados.
- `mock_and_db`: usa mocks y replica las escrituras hacia el broker backend.
- `db_only`: usa exclusivamente el broker backend para lectura/escritura.

Cuando el modo es `mock_and_db` o `db_only`, el middleware delega persistencia en el
broker backend (`8_service_backend`) mediante `BROKER_BACKEND_BASE_URL`.

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

- `3_backend` → **8003**
- `5_web_frontend` → **8005**
- `6_web_backoffice` → **8006** (reservado)
- `7_service_frontend` → **8007**
- `8_service_backend` → **8008** (reservado)

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

## Roles y permisos (mock)

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

## Interfaces compartidas (aplicación)

Los contratos en `src/2_shared_application/interfaces/` desacoplan el acceso a
las entidades de dominio de la infraestructura (JSON hoy, MariaDB mañana).

- `basic_permissions_repository.py`: `BasicPermissionsRepository`
- `low_level_permissions_repository.py`: `LowLevelPermissionsRepository`
- `manage_roles_by_org_repository.py`: `ManageRolesByOrgRepository`
- `roles_repository.py`: `RolesRepository`
- `user_repository.py`: `UserRepository`
- `organization_repository.py`: `OrganizationRepository`
- `identity_global_repository.py`: `IdentityGlobalRepository`
- `permissions_repository.py`: `PermissionsRepository`
- `tenant_repository.py`: `TenantRepository`
- `dataset_repository.py`: `DatasetRepository`
- `model_version_repository.py`: `ModelVersionRepository`

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

## Roles y automatización (referencia)

Los roles Ansible importados se encuentran en el repositorio `anh_ansible`. Incluyen BIND, NTPD, NTPDATE, MariaDB, Nginx, Postfix, entre otros, y sirven como apoyo para el despliegue de la plataforma.

# Anewhope

Proyecto para gestionar infraestructura, aplicaciones y flujos de personalización de modelos LLM.

## Estructura principal

- `info.txt`: guía rápida para crear y activar el entorno virtual, además de notas de operación.
- `protected_values.py`: variables sensibles requeridas por los procesos de cifrado.
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

## Entorno virtual

El entorno Python se ubica en `.venv/`. Para activarlo:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\Activate.ps1 # Windows PowerShell
```

## Servicio frontend en contenedor

El servicio `7_service_frontend` puede ejecutarse de forma independiente en Docker.

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
- `FERNET_KEY_PATH`

Dependencias del servicio (pip):
- `src/apps/7_service_frontend/requirements.txt`

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
  `identity_type_group_permissions` contiene una lista de permisos básicos.
- `src/2_shared_application/moks/basic_permissions.json`: catálogo de permisos básicos.
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

## Logging de seguridad

Las escrituras de logs de seguridad se realizan en el middleware (`7_service_frontend`).
El frontend solo envía la acción al endpoint `/security/log`.

Archivo de log (middleware):
- `src/apps/7_service_frontend/logs/middleware_secure.log`

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

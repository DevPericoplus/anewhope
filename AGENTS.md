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

### Scripts de mantenimiento
- `clear_caches.sh`: limpia caches de Reflex (`.web`, `.states`) y caches de tooling
  (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `.hypothesis`).

### Modos de almacenamiento (middleware)
- `STORAGE_MODE`: `mock` (solo JSON), `mock_and_db` (JSON + replica en broker),
  `db_only` (solo broker backend).
- `BROKER_BACKEND_BASE_URL`: URL del broker backend para persistencia.

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
| `protected_values.py` (sensitive config) | `@security-sentinel` | Manage sensitive configuration values and secrets. |

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


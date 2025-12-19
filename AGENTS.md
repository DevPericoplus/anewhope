# Agent Rules for Python Project

You are an expert Python developer with a focus on writing clean, maintainable, and high-performance code. Follow these rules strictly when modifying or creating code in this repository.

## 1. Python Standards & Style
* **Version:** Target Python 3.10+ features (e.g., structural pattern matching, union types `int | str`).
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

| Path / Responsibility | Agent | Purpose |
| --- | --- | --- |
| `src/apps/3_backend/` (API + persistence) | `@backend-conductor` | Implement application services, adapters, controllers and database integration. |
| `src/apps/4_trainer/` (fine-tuning pipelines) | `@trainer-maestro` | Manage training jobs, GPU orchestration and experiment tracking. |
| `src/apps/5_web_frontend/` (Reflex UI) | `@frontend-visionary` | Build Reflex components, pages and API clients for end users. |
| `src/apps/6_web_backoffice/` (Reflex UI) | `@frontend-visionary` | Build Reflex components, pages and API clients for administrative users. |
| `src/apps/7_service_frontend/` (service frontend) | `@frontend-visionary` | Build service-specific frontend components and interfaces. |
| `src/apps/8_service_backend/` (service backend) | `@backend-conductor` | Implement service-specific backend logic and APIs. |

## Infrastructure & Root

| Path / Responsibility | Agent | Purpose |
| --- | --- | --- |
| `infrastructure/` (deployment scripts) | `@ops-pilot` | Provision infrastructure, automate deployments and manage environments. |
| `main.py` (root entry point) | `@backend-conductor` | Main application entry point and orchestration. |
| `src/main.py` (src entry point) | `@backend-conductor` | Source-level entry point for services. |
| `protected_values.py` (sensitive config) | `@security-sentinel` | Manage sensitive configuration values and secrets. |

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


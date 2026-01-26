# 🧪 Guía de Tests y Entornos Virtuales

**Fecha:** 2026-01-26  
**Estado:** ✅ Implementado y verificado  
**Versión:** 1.0  

---

## 📋 Tabla de Contenidos

1. [Principios Fundamentales](#principios-fundamentales)
2. [Matriz de Entornos Virtuales](#matriz-de-entornos-virtuales)
3. [Reglas Obligatorias](#reglas-obligatorias)
4. [Script full_test.sh](#script-full_testsh)
5. [Estructura de Tests](#estructura-de-tests)
6. [Buenas Prácticas](#buenas-prácticas)
7. [Errores Comunes](#errores-comunes)
8. [Troubleshooting](#troubleshooting)
9. [Verificación y Auditoría](#verificación-y-auditoría)

---

## 🎯 Principios Fundamentales

### ¿Por qué entornos virtuales dedicados en tests?

Los tests deben ejecutarse en el mismo entorno virtual que usará la aplicación en producción para garantizar:

1. ✅ **Fidelidad:** Los tests reflejan el comportamiento real de la aplicación
2. ✅ **Aislamiento:** Las dependencias de una aplicación no afectan a otra
3. ✅ **Reproducibilidad:** Los tests pasan o fallan de forma consistente
4. ✅ **Debugging:** Los errores son más fáciles de diagnosticar
5. ✅ **Confianza:** Los tests que pasan localmente también pasan en CI/CD

### ¿Qué sucede si usamos el entorno equivocado?

❌ **Falsos positivos:**
- Test pasa localmente pero falla en producción
- Dependencias faltantes no detectadas

❌ **Falsos negativos:**
- Test falla localmente pero funcionaría en producción
- Conflictos de versiones de librerías

❌ **Comportamiento impredecible:**
- Tests que pasan de forma intermitente
- Errores difíciles de reproducir

---

## 📊 Matriz de Entornos Virtuales

### Asignación entorno → aplicación → tests

| Entorno Virtual | Puerto | Aplicaciones | Tests |
|-----------------|--------|--------------|-------|
| `.venv_frontend313` | 8005 | `5_web_frontend`, `2_shared_application` | `5_web_frontend/tests/`, `2_shared_application/tests/` |
| `.venv_backoffice313` | 8006 | `6_web_backoffice` | `6_web_backoffice/tests/` |
| `.venv_middleware313` | 8007 | `7_service_frontend`, `8_service_backend`, `3_backend` | `7_service_frontend/tests/`, `8_service_backend/tests/`, `3_backend/tests/` |
| `.venv_backend313` | 8003 | `3_backend` (alternativa) | `3_backend/tests/` (desarrollo aislado) |
| `.venv_broker313` | 8008 | `8_service_backend` (alternativa) | `8_service_backend/tests/` (desarrollo aislado) |

### Dependencias clave por entorno

**`.venv_frontend313`:**
- `reflex==0.8.25` (UI framework)
- `redis==5.2.1` (state manager)
- `pydantic==2.10.6` (validación)
- `pytest==8.3.4` (testing)

**`.venv_backoffice313`:**
- `reflex==0.8.25` (UI framework)
- `redis==5.2.1` (state manager)
- `pydantic==2.10.6` (validación)
- `pytest==8.3.4` (testing)

**`.venv_middleware313`:**
- `fastapi==0.115.12` (API framework)
- `uvicorn==0.35.0` (ASGI server)
- `pydantic==2.10.6` (validación)
- `pytest==8.3.4` (testing)
- `httpx==0.28.1` (HTTP client)

---

## ✅ Reglas Obligatorias

### 1. Activar el entorno virtual correcto

**Cada test DEBE ejecutarse en el entorno virtual de su aplicación.**

```bash
# ✅ CORRECTO: Test de frontend
source .venv_frontend313/bin/activate
pytest src/apps/5_web_frontend/tests/test_user_creation.py

# ✅ CORRECTO: Test de middleware
source .venv_middleware313/bin/activate
pytest src/apps/7_service_frontend/tests/test_user_creation_middleware.py

# ❌ INCORRECTO: Test de frontend con entorno de middleware
source .venv_middleware313/bin/activate
pytest src/apps/5_web_frontend/tests/test_user_creation.py
# ↑ Puede fallar por falta de reflex o versiones incompatibles
```

### 2. Aislar servicios externos con mocks

**Los tests NO deben depender de servicios externos (MariaDB, Redis, APIs).**

```python
# ✅ CORRECTO: Mock de servicios externos
def test_user_creation(monkeypatch):
    """Test aislado sin dependencias externas"""
    # Configurar modo mock para evitar llamadas a MariaDB
    monkeypatch.setenv("STORAGE_MODE", "mock")
    
    # Mock de Redis
    monkeypatch.setenv("REDIS_HOST", "localhost")
    
    # Test logic here
    pass
```

```python
# ❌ INCORRECTO: Dependencia de servicios reales
def test_user_creation():
    """Test que requiere MariaDB corriendo"""
    # Esto fallará en CI/CD si MariaDB no está disponible
    response = requests.post("http://localhost:8003/users")
    assert response.status_code == 200
```

### 3. No importar módulos de otras aplicaciones

**Los tests SOLO deben importar módulos de su aplicación y de capas compartidas.**

```python
# ✅ CORRECTO: Test de frontend importa módulos de frontend y shared
# src/apps/5_web_frontend/tests/test_user_creation.py
from pages.user_creation import UserCreationState  # ✅ Frontend
from src.1_shared_domain.entities.domain_models import User  # ✅ Shared
from src.2_shared_application.dtos.user_dtos import UserDto  # ✅ Shared
```

```python
# ❌ INCORRECTO: Test de frontend importa módulos de middleware
# src/apps/5_web_frontend/tests/test_user_creation.py
from pages.user_creation import UserCreationState  # ✅ Frontend
from src.apps.7_service_frontend.routermiddleware import MiddlewareRouter  # ❌ Middleware
# ↑ Acoplamiento incorrecto entre aplicaciones
```

### 4. Usar fixtures para configuración común

**Centralizar configuración común en fixtures reutilizables.**

```python
# ✅ CORRECTO: Fixtures reutilizables
import pytest

@pytest.fixture
def mock_environment(monkeypatch):
    """Configura entorno de test aislado"""
    monkeypatch.setenv("STORAGE_MODE", "mock")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    return monkeypatch

@pytest.fixture
def temp_users_file(tmp_path):
    """Crea archivo temporal de usuarios"""
    users_file = tmp_path / "users.json"
    users_file.write_text("[]", encoding="utf-8")
    return users_file

def test_user_creation(mock_environment, temp_users_file):
    """Test que usa fixtures"""
    # Configuration ya aplicada por fixtures
    pass
```

### 5. Ejecutar tests con `full_test.sh`

**Usar el script oficial para ejecutar toda la suite de tests.**

```bash
# ✅ CORRECTO: Ejecutar todos los tests
./full_test.sh

# ✅ CORRECTO: Ejecutar tests de una aplicación específica
source .venv_frontend313/bin/activate
pytest src/apps/5_web_frontend/tests/

# ❌ INCORRECTO: Ejecutar tests sin activar entorno
pytest src/apps/5_web_frontend/tests/
# ↑ Puede usar Python del sistema o entorno equivocado
```

---

## 🔧 Script full_test.sh

### Estructura del script

El script `full_test.sh` automatiza la ejecución de todos los tests con los entornos virtuales correctos:

```bash
#!/bin/bash
# Ejecuta tests de frontend, backoffice y middleware desde la raíz

set -e

# ============================================
# TESTS DE CAPA COMPARTIDA + FRONTEND
# ============================================
source .venv_frontend313/bin/activate

echo "TESTS: src/2_shared_application/tests"
pytest -v --rootdir=src/2_shared_application src/2_shared_application/tests

echo "TESTS: src/apps/5_web_frontend/tests"
pytest -v --rootdir=src/apps/5_web_frontend src/apps/5_web_frontend/tests

deactivate

# ============================================
# TESTS DE BACKOFFICE
# ============================================
source .venv_backoffice313/bin/activate

echo "TESTS: src/apps/6_web_backoffice/tests"
pytest -v --rootdir=src/apps/6_web_backoffice src/apps/6_web_backoffice/tests

deactivate

# ============================================
# TESTS DE MIDDLEWARE
# ============================================
source .venv_middleware313/bin/activate

echo "TESTS: src/apps/7_service_frontend/tests"
pytest -v --rootdir=src/apps/7_service_frontend src/apps/7_service_frontend/tests

echo "TESTS: src/apps/8_service_backend/tests"
pytest -v --rootdir=src/apps/8_service_backend src/apps/8_service_backend/tests

echo "TESTS: src/apps/3_backend/tests"
pytest -v --rootdir=src/apps/3_backend src/apps/3_backend/tests

deactivate

echo "✅ TODOS LOS TESTS COMPLETADOS CON ÉXITO"
```

### Características del script

1. ✅ **Activación automática:** Activa el entorno virtual correcto para cada módulo
2. ✅ **Salida verbose:** Usa `-v` para mostrar cada test individual
3. ✅ **Rootdir explícito:** Usa `--rootdir` para evitar ambigüedades de pytest
4. ✅ **Desactivación limpia:** Desactiva entornos entre grupos de tests
5. ✅ **Exit on error:** Usa `set -e` para detener en el primer error

### Módulos testeados

| Módulo | Entorno Virtual | Cantidad Tests |
|--------|-----------------|----------------|
| `2_shared_application/tests` | `.venv_frontend313` | ~14 tests |
| `5_web_frontend/tests` | `.venv_frontend313` | ~23 tests |
| `6_web_backoffice/tests` | `.venv_backoffice313` | ~7 tests |
| `7_service_frontend/tests` | `.venv_middleware313` | ~8 tests |
| `8_service_backend/tests` | `.venv_middleware313` | ~1 test |
| `3_backend/tests` | `.venv_middleware313` | ~1 test |

**Total:** ~54 tests

---

## 📁 Estructura de Tests

### Organización de directorios

Cada aplicación numerada en `src/apps/` debe tener un directorio `tests/`:

```
src/apps/
├── 3_backend/
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_core_api.py
│   ├── run.sh
│   └── entrypoint.sh
├── 5_web_frontend/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_user_creation.py
│   │   ├── test_change_password.py
│   │   └── test_redis_integration.py
│   ├── run.sh
│   └── entrypoint.sh
├── 6_web_backoffice/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_user_creation.py
│   │   └── test_redis_integration.py
│   ├── run.sh
│   └── entrypoint.sh
├── 7_service_frontend/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_user_creation_middleware.py
│   │   └── test_login_db_only_sync.py
│   ├── run.sh
│   └── entrypoint.sh
└── 8_service_backend/
    ├── tests/
    │   ├── __init__.py
    │   └── test_broker_api.py
    ├── run.sh
    └── entrypoint.sh
```

### Nomenclatura de tests

- **Test de funcionalidad:** `test_<feature>.py` (ej: `test_user_creation.py`)
- **Test de integración:** `test_integration_<components>.py` (ej: `test_integration_frontend_middleware.py`)
- **Test de API:** `test_<api_name>_api.py` (ej: `test_core_api.py`)
- **Test de Redis:** `test_redis_integration.py`

---

## ✨ Buenas Prácticas

### 1. Tests atómicos

Cada test debe ser independiente y probar una sola cosa:

```python
# ✅ CORRECTO: Test atómico
def test_user_creation_validates_email():
    """Valida que la creación de usuario rechaza emails inválidos"""
    with pytest.raises(ValueError, match="Email inválido"):
        User(email="invalid_email", ...)

def test_user_creation_validates_password():
    """Valida que la creación de usuario rechaza contraseñas débiles"""
    with pytest.raises(ValueError, match="Contraseña débil"):
        User(password="123", ...)
```

```python
# ❌ INCORRECTO: Test que prueba múltiples cosas
def test_user_creation():
    """Valida creación de usuario"""
    # Prueba email inválido
    with pytest.raises(ValueError):
        User(email="invalid", ...)
    
    # Prueba contraseña débil
    with pytest.raises(ValueError):
        User(password="123", ...)
    
    # Prueba OTP inválido
    with pytest.raises(ValueError):
        User(otp="12345", ...)
    # ↑ Si el primer assert falla, no se ejecutan los demás
```

### 2. Fixtures descriptivos

Usar nombres descriptivos para fixtures:

```python
# ✅ CORRECTO: Nombres descriptivos
@pytest.fixture
def valid_user_data():
    """Datos válidos de usuario para tests"""
    return {
        "user_name": "testuser",
        "email": "test@example.com",
        "password": "securepass123",
        "otp": "1234"
    }

@pytest.fixture
def temp_users_json(tmp_path):
    """Archivo temporal de usuarios para tests"""
    file_path = tmp_path / "users.json"
    file_path.write_text("[]")
    return file_path
```

### 3. Asserts claros

Usar mensajes de error claros en asserts:

```python
# ✅ CORRECTO: Assert con mensaje descriptivo
def test_user_email_validation():
    """Valida formato de email"""
    user = User(email="invalid_email", ...)
    assert "@" in user.email, "Email debe contener @"

# ❌ INCORRECTO: Assert sin contexto
def test_user_email_validation():
    user = User(email="invalid_email", ...)
    assert "@" in user.email
    # ↑ Si falla, no sabemos por qué
```

### 4. Cleanup automático

Usar fixtures con cleanup automático:

```python
# ✅ CORRECTO: Cleanup con yield
@pytest.fixture
def temp_database(tmp_path):
    """Base de datos temporal con cleanup automático"""
    db_path = tmp_path / "test.db"
    
    # Setup
    db = Database(db_path)
    db.create_tables()
    
    yield db
    
    # Cleanup (se ejecuta después del test)
    db.close()
    db_path.unlink(missing_ok=True)
```

---

## ❌ Errores Comunes

### Error 1: Entorno virtual equivocado

**Síntoma:**
```
ImportError: cannot import name 'reflex' from 'reflex'
```

**Causa:**
Test de frontend ejecutado con entorno de middleware.

**Solución:**
```bash
# Activar entorno correcto
source .venv_frontend313/bin/activate
pytest src/apps/5_web_frontend/tests/
```

---

### Error 2: Dependencias de servicios externos

**Síntoma:**
```
ConnectionRefusedError: [Errno 61] Connection refused
```

**Causa:**
Test intenta conectar a MariaDB/Redis real.

**Solución:**
```python
def test_user_creation(monkeypatch):
    # Configurar modo mock
    monkeypatch.setenv("STORAGE_MODE", "mock")
    # Rest of test...
```

---

### Error 3: Imports cruzados

**Síntoma:**
```
ModuleNotFoundError: No module named 'src.apps.7_service_frontend'
```

**Causa:**
Test de frontend importa módulos de middleware.

**Solución:**
```python
# ❌ INCORRECTO
from src.apps.7_service_frontend.routermiddleware import MiddlewareRouter

# ✅ CORRECTO: Usar solo módulos compartidos
from src.2_shared_application.interfaces.user_repository import UserRepository
```

---

### Error 4: Path incorrectos

**Síntoma:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'users.json'
```

**Causa:**
Test asume rutas relativas incorrectas.

**Solución:**
```python
# ✅ CORRECTO: Usar Path absolutos
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
USERS_FILE = PROJECT_ROOT / "src/2_shared_application/moks/users.json"
```

---

## 🔍 Troubleshooting

### Debugging tests fallidos

**Paso 1: Verificar entorno virtual**
```bash
# Ver qué Python está activo
which python
# /Users/administrator/develop/anewhope/.venv_frontend313/bin/python

# Ver dependencias instaladas
pip list | grep -E "(reflex|pytest|pydantic)"
```

**Paso 2: Ejecutar test individual con verbose**
```bash
pytest -vv -s src/apps/5_web_frontend/tests/test_user_creation.py
# -vv: verbose máximo
# -s: mostrar prints
```

**Paso 3: Verificar variables de entorno**
```python
# Agregar al test para debugging
def test_user_creation(monkeypatch):
    import os
    print("STORAGE_MODE:", os.getenv("STORAGE_MODE"))
    print("PYTHONPATH:", os.getenv("PYTHONPATH"))
```

**Paso 4: Ver logs**
```bash
# Ver logs de la aplicación
tail -f src/apps/5_web_frontend/logs/frontend_secure.log
```

---

## ✅ Verificación y Auditoría

### Script de verificación de entornos

```bash
# Verificar que entornos virtuales están correctos
./scripts/verify_environments.sh

# Resultado esperado:
# ✅ 16 verificaciones exitosas
# ❌ 0 errores
# ⚠️  1 warning (trainer pendiente)
```

### Auditoría completa

El documento `docs/VIRTUAL_ENVIRONMENTS_AUDIT.md` contiene:
- Análisis detallado de cada aplicación
- Matriz completa de entornos virtuales
- Problemas identificados y soluciones
- Checklist de implementación

### Checklist de verificación para nuevos tests

Antes de crear un nuevo test, verificar:

- [ ] El test está en el directorio `tests/` de la aplicación correcta
- [ ] El test usa el entorno virtual correcto (verificado en `full_test.sh`)
- [ ] El test configura `STORAGE_MODE=mock` con `monkeypatch.setenv()`
- [ ] El test NO importa módulos de otras aplicaciones (solo shared)
- [ ] El test usa fixtures para configuración común
- [ ] El test es atómico (prueba una sola cosa)
- [ ] El test tiene docstring descriptivo
- [ ] El test usa asserts con mensajes claros
- [ ] El test pasa cuando se ejecuta con `full_test.sh`

---

## 📚 Referencias

### Documentación relacionada

- **Auditoría de entornos:** `docs/VIRTUAL_ENVIRONMENTS_AUDIT.md`
- **Script de verificación:** `scripts/verify_environments.sh`
- **Script de tests:** `full_test.sh`
- **Reglas de agentes:** `AGENTS.md` (sección 5.1)
- **Guía general:** `README.md` (sección "Entornos virtuales dedicados")

### Archivos clave

```
anewhope/
├── full_test.sh                              # Script principal de tests
├── scripts/verify_environments.sh            # Verificación de entornos
├── docs/
│   ├── VIRTUAL_ENVIRONMENTS_AUDIT.md         # Auditoría completa
│   └── TESTING_VIRTUAL_ENVIRONMENTS.md       # Este documento
├── .venv_frontend313/                        # Entorno frontend
├── .venv_backoffice313/                      # Entorno backoffice
├── .venv_middleware313/                      # Entorno middleware
├── .venv_backend313/                         # Entorno backend (alt)
└── .venv_broker313/                          # Entorno broker (alt)
```

---

**Última actualización:** 2026-01-26  
**Autor:** @backend-conductor  
**Revisado por:** @frontend-visionary, @application-architect

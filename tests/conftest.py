"""
Configuración pytest compartida para tests/ (unit, integration, e2e).

Proporciona fixtures para:
- Raíz del proyecto
- Carga dinámica de módulos con prefijos numéricos
- Protected values del entorno activo
- Engines de base de datos (scope=session)
"""

import sys
from pathlib import Path

# Asegurar que el project root está en sys.path para que 'tests.helpers' sea importable
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from tests.helpers import load_module_from_path, load_protected_values, get_db_engine


@pytest.fixture(scope="session")
def project_root():
    """Raíz del proyecto."""
    return _project_root


@pytest.fixture(scope="session")
def protected_values():
    """Carga protected_values del entorno activo."""
    return load_protected_values()


@pytest.fixture(scope="session")
def db_engine_core(protected_values):
    """Engine SQLAlchemy para myllm_core_db."""
    engine = get_db_engine(protected_values, "myllm_core_db")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_engine_projects(protected_values):
    """Engine SQLAlchemy para myllm_projects_db."""
    engine = get_db_engine(protected_values, "myllm_projects_db")
    yield engine
    engine.dispose()

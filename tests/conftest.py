"""
Configuración pytest compartida para tests/ (unit, integration, e2e).

Fixtures multi-entorno (silicon, macbook, dev, pre, pro):
- Entorno activo, env.yaml, URLs de servicios
- Protected values del entorno activo
- Engines de base de datos (scope=session)
"""

import sys
from pathlib import Path

_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from tests.import_aliases import bootstrap_test_imports

bootstrap_test_imports(_project_root)

import pytest
from tests.helpers import (
    get_active_test_environment,
    get_db_engine,
    get_service_urls,
    load_env_yaml,
    load_protected_values,
)


@pytest.fixture(scope="session")
def project_root():
    """Raíz del proyecto."""
    return _project_root


@pytest.fixture(scope="session")
def test_environment():
    """Entorno activo de la suite (ANEWHOPE_ENV / ENVIRONMENT / .envglobal)."""
    return get_active_test_environment()


@pytest.fixture(scope="session")
def env_yaml(test_environment):
    """Variables públicas del entorno activo."""
    return load_env_yaml(test_environment)


@pytest.fixture(scope="session")
def service_urls(test_environment):
    """URLs de servicios resueltas desde env.yaml."""
    return get_service_urls(env=test_environment)


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

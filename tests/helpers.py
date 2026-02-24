"""
Utilidades compartidas para tests E2E y standalone.

Proporciona acceso dinámico a protected_values, conexiones a BD,
URLs de servicios y carga de módulos desde rutas con prefijos numéricos.
"""

import os
import sys
import importlib.util
from pathlib import Path


def get_project_root():
    """Retorna la raíz del proyecto (directorio padre de tests/)."""
    return Path(__file__).parent.parent


def load_module_from_path(name, path):
    """Carga un módulo Python desde una ruta arbitraria usando importlib.

    Args:
        name: Nombre con el que registrar el módulo en sys.modules.
        path: Ruta absoluta o relativa al fichero .py.

    Returns:
        El módulo cargado.
    """
    path = Path(path)
    if not path.is_absolute():
        path = get_project_root() / path
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_protected_values(env=None):
    """Carga protected_values.py del entorno indicado.

    Args:
        env: Nombre del entorno (macbook, dev, pre, pro).
             Si es None, usa la variable ANEWHOPE_ENV o 'macbook' por defecto.

    Returns:
        Módulo protected_values cargado.
    """
    if env is None:
        env = os.environ.get("ANEWHOPE_ENV", "macbook")
    pv_path = get_project_root() / "infrastructure" / "environments" / env / "protected_values.py"
    return load_module_from_path("protected_values", pv_path)


def get_service_urls(pv=None):
    """Retorna un dict con las URLs base de todos los servicios.

    Args:
        pv: Módulo protected_values ya cargado. Si es None, lo carga.

    Returns:
        Dict con claves: middleware, backend_core, broker, trainer,
        frontend, backoffice, fmanagement, chromadb.
    """
    if pv is None:
        pv = load_protected_values()

    # Extraer host base desde las URLs de protected_values
    core_url = getattr(pv, "core_backend_base_url", "http://localhost:8003")
    broker_url = getattr(pv, "broker_backend_base_url", "http://localhost:8008")
    trainer_url = getattr(pv, "trainer_backend_base_url", "http://localhost:8004")

    # Derivar host del middleware desde core_url (mismo host que broker, puerto 8007)
    from urllib.parse import urlparse
    parsed_broker = urlparse(broker_url)
    broker_host = parsed_broker.hostname or "localhost"

    # Frontend y middleware están en el servidor frontend
    # En macbook todo es local, en PRE están en frontend.anewhope.aws
    frontend_host = broker_host  # En macbook, todo es el mismo host

    return {
        "backend_core": core_url,
        "broker": broker_url,
        "trainer": trainer_url,
        "middleware": f"http://{broker_host}:8007",
        "frontend": f"http://{frontend_host}:8005",
        "backoffice": f"http://{frontend_host}:8006",
        "fmanagement": f"http://{broker_host}:1666",
        "chromadb": f"http://{urlparse(trainer_url).hostname or 'localhost'}:8100",
    }


def get_db_connection(pv=None, database="myllm_core_db"):
    """Crea una conexión pymysql usando credenciales de protected_values.

    Args:
        pv: Módulo protected_values. Si es None, lo carga.
        database: Nombre de la base de datos (myllm_core_db o myllm_projects_db).

    Returns:
        Conexión pymysql.
    """
    import pymysql

    if pv is None:
        pv = load_protected_values()

    return pymysql.connect(
        host=pv.mariadb_host,
        port=int(pv.mariadb_port),
        user=pv.mariadb_admin_user,
        password=pv.mariadb_admin_password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_db_engine(pv=None, database="myllm_core_db"):
    """Crea un SQLAlchemy engine usando credenciales de protected_values.

    Args:
        pv: Módulo protected_values. Si es None, lo carga.
        database: Nombre de la base de datos.

    Returns:
        SQLAlchemy Engine.
    """
    from urllib.parse import quote_plus
    from sqlalchemy import create_engine

    if pv is None:
        pv = load_protected_values()

    password_encoded = quote_plus(pv.mariadb_admin_password)
    dsn = (
        f"mysql+pymysql://{pv.mariadb_admin_user}:{password_encoded}"
        f"@{pv.mariadb_host}:{pv.mariadb_port}/{database}"
    )
    return create_engine(dsn)

"""Helper centralizado para acceso a bases de datos MariaDB.

Elimina la duplicación de ``_run_mysql_query``, ``_load_projects_db_settings``
y ``create_engine`` inline que existía en múltiples páginas del backoffice.

Uso típico::

    from src.2_shared_application.db_query_helper import (
        run_projects_db_query,
        run_core_db_query,
        get_projects_db_engine,
        get_core_db_engine,
    )

    # Via CLI (como estado_proyectos.py, flujos.py)
    rows = run_projects_db_query("SELECT id, nombre FROM proyectos")

    # Via SQLAlchemy (como informes.py, seguimiento.py)
    engine = get_projects_db_engine()
"""

from __future__ import annotations

import importlib.util
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# Caché para evitar recargar el módulo en cada llamada
_env_settings_module: Any = None
_protected_settings_cache: dict[str, Any] | None = None


# ============================================================================
# Carga de configuración
# ============================================================================


def _get_env_settings_module() -> Any:
    """Carga el módulo env_settings de forma centralizada."""
    global _env_settings_module
    if _env_settings_module is not None:
        return _env_settings_module

    module_path = (
        Path(__file__).resolve().parent / "config" / "env_settings.py"
    )
    spec = importlib.util.spec_from_file_location(
        "db_query_helper_env_settings", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"No se pudo cargar el módulo de configuración: {module_path}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules["db_query_helper_env_settings"] = module
    spec.loader.exec_module(module)
    _env_settings_module = module
    return module


def _get_protected_settings() -> dict[str, Any]:
    """Obtiene la configuración protegida (credenciales, hosts, etc.)."""
    global _protected_settings_cache
    if _protected_settings_cache is not None:
        return _protected_settings_cache

    env_settings = _get_env_settings_module()
    _protected_settings_cache = env_settings.load_protected_settings()
    return _protected_settings_cache


def _get_db_settings(database_key: str = "mariadb_ai_database") -> dict[str, str]:
    """Obtiene la configuración de conexión a una base de datos.

    Args:
        database_key: Clave en protected_values para el nombre de la BD.
            - ``mariadb_ai_database`` → ``myllm_projects_db``
            - ``mariadb_core_database`` → ``myllm_core_db``

    Returns:
        Diccionario con host, port, database, reader_user, reader_password,
        writer_user, writer_password, cli_path.
    """
    protected = _get_protected_settings()

    return {
        "host": os.environ.get(
            "MARIADB_HOST", str(protected.get("mariadb_host", "localhost"))
        ),
        "port": os.environ.get(
            "MARIADB_PORT", str(protected.get("mariadb_port", 3306))
        ),
        "database": os.environ.get(
            "MARIADB_DATABASE",
            str(protected.get(database_key, "myllm_projects_db")),
        ),
        "reader_user": os.environ.get(
            "MARIADB_READER_USER",
            str(protected.get("mariadb_reader_user", "")),
        ),
        "reader_password": os.environ.get(
            "MARIADB_READER_PASSWORD",
            str(protected.get("mariadb_reader_password", "")),
        ),
        "writer_user": os.environ.get(
            "MARIADB_WRITER_USER",
            str(protected.get("mariadb_writer_user", "")),
        ),
        "writer_password": os.environ.get(
            "MARIADB_WRITER_PASSWORD",
            str(protected.get("mariadb_writer_password", "")),
        ),
        "cli_path": os.environ.get(
            "MARIADB_CLI_PATH",
            str(protected.get("mariadb_cli_path", "")),
        ),
    }


# ============================================================================
# Ejecución de queries via CLI (subprocess)
# ============================================================================


def _run_mysql_cli_query(
    query: str,
    database_key: str = "mariadb_ai_database",
    use_writer: bool = False,
) -> list[list[str]]:
    """Ejecuta una consulta SQL via CLI de mysql y devuelve filas tabuladas.

    Args:
        query: Consulta SQL a ejecutar.
        database_key: Clave de BD en protected_values.
        use_writer: Si True, usa credenciales de escritura.

    Returns:
        Lista de filas, cada fila es una lista de strings (columnas separadas
        por tabulador).
    """
    settings = _get_db_settings(database_key)

    user = settings["writer_user"] if use_writer else settings["reader_user"]
    password = settings["writer_password"] if use_writer else settings["reader_password"]

    cmd = [
        settings["cli_path"],
        "-u",
        user,
        f"-p{password}",
        "--database",
        settings["database"],
        "-N",
        "-B",
        "-e",
        query,
    ]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error(
            "Error al consultar BD (%s): %s",
            settings["database"],
            exc.stderr.strip() if exc.stderr else exc,
        )
        return []

    rows: list[list[str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


def run_projects_db_query(query: str) -> list[list[str]]:
    """Ejecuta una consulta SELECT en ``myllm_projects_db`` via CLI.

    Puede referenciar tablas de ``myllm_core_db`` usando notación
    ``myllm_core_db.organizations``.
    """
    return _run_mysql_cli_query(query, database_key="mariadb_ai_database")


def run_core_db_query(query: str) -> list[list[str]]:
    """Ejecuta una consulta SELECT en ``myllm_core_db`` via CLI."""
    return _run_mysql_cli_query(query, database_key="mariadb_core_database")


def run_projects_db_update(query: str) -> bool:
    """Ejecuta un UPDATE/INSERT en ``myllm_projects_db`` via CLI (writer)."""
    _run_mysql_cli_query(
        query, database_key="mariadb_ai_database", use_writer=True
    )
    return True  # Si no lanza excepción, fue exitoso


# ============================================================================
# SQLAlchemy engines
# ============================================================================


def _build_dsn(
    user: str,
    password: str,
    host: str,
    port: str,
    database: str,
) -> str:
    """Construye un DSN válido para SQLAlchemy con URL-encoding."""
    encoded_pass = quote_plus(password)
    return f"mysql+pymysql://{user}:{encoded_pass}@{host}:{port}/{database}"


_SQLALCHEMY_MISSING_MSG = "SQLAlchemy no está instalado en este entorno virtual"


def get_projects_db_engine() -> Any:
    """Crea un engine SQLAlchemy para ``myllm_projects_db``.

    Returns:
        ``sqlalchemy.engine.Engine`` o None si falla la creación.
    """
    try:
        from sqlalchemy import create_engine
    except ImportError:
        logger.error(_SQLALCHEMY_MISSING_MSG)
        return None

    settings = _get_db_settings("mariadb_ai_database")
    dsn = _build_dsn(
        user=settings["reader_user"],
        password=settings["reader_password"],
        host=settings["host"],
        port=settings["port"],
        database=settings["database"],
    )
    try:
        return create_engine(dsn)
    except Exception as exc:
        logger.error("Error creando engine para projects_db: %s", exc)
        return None


def get_core_db_engine() -> Any:
    """Crea un engine SQLAlchemy para ``myllm_core_db``.

    Returns:
        ``sqlalchemy.engine.Engine`` o None si falla la creación.
    """
    try:
        from sqlalchemy import create_engine
    except ImportError:
        logger.error(_SQLALCHEMY_MISSING_MSG)
        return None

    settings = _get_db_settings("mariadb_core_database")
    dsn = _build_dsn(
        user=settings["reader_user"],
        password=settings["reader_password"],
        host=settings["host"],
        port=settings["port"],
        database=settings["database"],
    )
    try:
        return create_engine(dsn)
    except Exception as exc:
        logger.error("Error creando engine para core_db: %s", exc)
        return None


def get_projects_db_writer_engine() -> Any:
    """Crea un engine SQLAlchemy con credenciales de escritura para ``myllm_projects_db``."""
    try:
        from sqlalchemy import create_engine
    except ImportError:
        logger.error(_SQLALCHEMY_MISSING_MSG)
        return None

    settings = _get_db_settings("mariadb_ai_database")
    dsn = _build_dsn(
        user=settings["writer_user"],
        password=settings["writer_password"],
        host=settings["host"],
        port=settings["port"],
        database=settings["database"],
    )
    try:
        return create_engine(dsn)
    except Exception as exc:
        logger.error("Error creando writer engine para projects_db: %s", exc)
        return None

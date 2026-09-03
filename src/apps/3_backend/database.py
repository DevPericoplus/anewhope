"""Conexión MariaDB para el router de análisis de entrenamientos.

En PRE nativo MariaDB escucha en el host. En silicon/docker el host es el
servicio ``mariadb``. Las credenciales y el host se resuelven en runtime
(compose / env.yaml / protected_values), nunca con localhost fijo.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import mysql.connector
from mysql.connector import Error

logger = logging.getLogger(__name__)


def _load_env_settings() -> ModuleType:
    """Carga env_settings sin importar el paquete numerado ``2_shared_application``."""
    module_path = (
        Path(__file__).resolve().parents[2]
        / "2_shared_application"
        / "config"
        / "env_settings.py"
    )
    spec = importlib.util.spec_from_file_location("env_settings_analysis_db", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar env_settings desde {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["env_settings_analysis_db"] = module
    spec.loader.exec_module(module)
    return module


def _first_non_empty(*values: Any) -> str:
    """Devuelve el primer valor no vacío convertido a str."""
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _build_db_config() -> dict[str, Any]:
    """Resuelve host y credenciales en cada conexión.

    Prioridad: ``DB_*`` (override) → ``MARIADB_*`` (compose/env.yaml) →
    ``protected_values.py`` (solo credenciales; el host de PRE no aplica
    dentro de un contenedor).
    """
    env_settings = _load_env_settings()
    env_settings.load_env_file()
    host = _first_non_empty(
        os.environ.get("DB_HOST"),
        env_settings.get_env_value("MARIADB_HOST", ""),
        env_settings.get_protected_value("mariadb_host", "localhost"),
        "localhost",
    )
    port_raw = _first_non_empty(
        os.environ.get("DB_PORT"),
        env_settings.get_env_value("MARIADB_PORT", ""),
        env_settings.get_protected_value("mariadb_port", "3306"),
        "3306",
    )
    user = _first_non_empty(
        os.environ.get("DB_USER"),
        env_settings.get_env_value("MARIADB_WRITER_USER", ""),
        env_settings.get_protected_value("mariadb_writer_user", ""),
    )
    password = _first_non_empty(
        os.environ.get("DB_PASSWORD"),
        env_settings.get_env_value("MARIADB_WRITER_PASSWORD", ""),
        env_settings.get_protected_value("mariadb_writer_password", ""),
    )
    database = _first_non_empty(
        os.environ.get("DB_NAME"),
        env_settings.get_env_value("MARIADB_PROJECTS_DATABASE", ""),
        env_settings.get_protected_value("mariadb_ai_database", "myllm_projects_db"),
        "myllm_projects_db",
    )
    return {
        "host": host,
        "port": int(port_raw),
        "user": user,
        "password": password,
        "database": database,
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
        "autocommit": False,
    }


def get_db_connection() -> Any:
    """Crea y retorna una conexión activa a ``myllm_projects_db``.

    Raises:
        Error: Si la conexión falla.
    """
    config = _build_db_config()
    try:
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            logger.debug(
                "Connected to database: %s@%s",
                config["database"],
                config["host"],
            )
            return connection
        raise Error("Failed to connect to database")
    except Error as exc:
        logger.error(
            "Database connection error host=%s db=%s: %s",
            config["host"],
            config["database"],
            exc,
        )
        raise

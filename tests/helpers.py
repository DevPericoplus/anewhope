"""
Utilidades compartidas para tests E2E, integración y unitarios.

Resuelve el entorno activo (incluido silicon) y lee URLs/hosts desde
``env.yaml``, no desde los hosts replicados de ``protected_values.py``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


VALID_TEST_ENVIRONMENTS = ("macbook", "dev", "pre", "pro", "silicon")


def get_project_root() -> Path:
    """Retorna la raíz del proyecto (directorio padre de tests/)."""
    return Path(__file__).parent.parent


def get_active_test_environment() -> str:
    """Resuelve el entorno de tests (silicon-ready).

    Orden de prioridad:
    1. ``ANEWHOPE_ENV``
    2. ``ENVIRONMENT`` / ``environment``
    3. ``current_environment`` en ``.envglobal``
    4. ``macbook``
    """
    for key in ("ANEWHOPE_ENV", "ENVIRONMENT", "environment"):
        value = str(os.environ.get(key, "")).strip()
        if value in VALID_TEST_ENVIRONMENTS:
            return value

    envglobal = get_project_root() / ".envglobal"
    if envglobal.exists():
        try:
            for raw_line in envglobal.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, raw_value = line.split(":", 1)
                if key.strip() != "current_environment":
                    continue
                value = raw_value.strip().strip("'").strip('"')
                if value in VALID_TEST_ENVIRONMENTS:
                    return value
        except OSError:
            pass
    return "macbook"


def load_module_from_path(name: str, path: str | Path) -> Any:
    """Carga un módulo Python desde una ruta arbitraria usando importlib."""
    import importlib.util

    path = Path(path)
    if not path.is_absolute():
        path = get_project_root() / path
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar el módulo {name} desde {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_protected_values(env: str | None = None) -> Any:
    """Carga protected_values.py del entorno indicado (o el activo)."""
    env_name = env or get_active_test_environment()
    pv_path = (
        get_project_root()
        / "infrastructure"
        / "environments"
        / env_name
        / "protected_values.py"
    )
    if not pv_path.exists():
        raise FileNotFoundError(f"No existe protected_values.py para {env_name}: {pv_path}")
    return load_module_from_path(f"protected_values_{env_name}", pv_path)


def _parse_simple_yaml_scalars(text: str) -> dict[str, Any]:
    """Parser mínimo de claves escalares (fallback si no hay PyYAML)."""
    result: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or line[:1] in {" ", "\t", "-"} or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            result[key] = value
    return result


def load_env_yaml(env: str | None = None) -> dict[str, Any]:
    """Carga ``env.yaml`` del entorno indicado (o el activo)."""
    env_name = env or get_active_test_environment()
    yaml_path = (
        get_project_root()
        / "infrastructure"
        / "environments"
        / env_name
        / "env.yaml"
    )
    if not yaml_path.exists():
        raise FileNotFoundError(f"No existe env.yaml para {env_name}: {yaml_path}")
    text = yaml_path.read_text(encoding="utf-8")
    try:
        import yaml

        data = yaml.safe_load(text) or {}
    except ImportError:
        data = _parse_simple_yaml_scalars(text)
    if not isinstance(data, dict):
        raise ValueError(f"env.yaml de {env_name} debe ser un objeto")
    return data


def _yaml_url(data: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = data.get(key)
        if value:
            return str(value).rstrip("/")
    return default


def get_service_urls(pv: Any | None = None, env: str | None = None) -> dict[str, str]:
    """URLs base de servicios desde ``env.yaml`` (no hosts de protected_values).

    En silicon/dev/pre las URLs son FQDN del entorno. Los hosts ``*.anewhope.aws``
    de ``protected_values.py`` son legado PRE y no deben usarse para tests.
    """
    env_name = env or get_active_test_environment()
    data = load_env_yaml(env_name)

    core_url = _yaml_url(data, "core_backend_base_url", "CORE_BACKEND_BASE_URL")
    broker_url = _yaml_url(data, "broker_backend_base_url", "BROKER_BACKEND_BASE_URL")
    trainer_url = _yaml_url(
        data, "trainer_base_url", "trainer_backend_base_url", "TRAINER_BACKEND_BASE_URL"
    )
    middleware_url = _yaml_url(data, "middleware_base_url", "MIDDLEWARE_BASE_URL")
    fmanagement_url = _yaml_url(data, "fmanagement_base_url", "FMANAGEMENT_BASE_URL")

    if pv is None:
        try:
            pv = load_protected_values(env_name)
        except FileNotFoundError:
            pv = None

    if not core_url and pv is not None:
        core_url = str(getattr(pv, "core_backend_base_url", "") or "")
    if not broker_url and pv is not None:
        broker_url = str(getattr(pv, "broker_backend_base_url", "") or "")
    if not trainer_url and pv is not None:
        trainer_url = str(getattr(pv, "trainer_backend_base_url", "") or "")

    core_url = core_url or "http://localhost:8003"
    broker_url = broker_url or "http://localhost:8008"
    trainer_url = trainer_url or "http://localhost:8004"

    broker_host = urlparse(broker_url).hostname or "localhost"
    trainer_host = urlparse(trainer_url).hostname or "localhost"
    frontend_host = urlparse(middleware_url).hostname if middleware_url else None
    if not frontend_host:
        frontend_host = "frontend.anewhope.silicon.loc" if env_name == "silicon" else broker_host

    if not middleware_url:
        middleware_url = f"http://{frontend_host}:8007"
    if not fmanagement_url:
        fmanagement_url = f"http://{broker_host}:1666"

    redis_host = str(data.get("redis_host") or "")
    if not redis_host or redis_host in {"redis", "localhost", "127.0.0.1"}:
        redis_host = frontend_host
    redis_port = str(data.get("redis_port") or "6379")

    return {
        "backend_core": core_url,
        "broker": broker_url,
        "trainer": trainer_url,
        "middleware": middleware_url,
        "frontend": f"http://{frontend_host}:8005",
        "backoffice": f"http://{frontend_host}:8006",
        "fmanagement": fmanagement_url,
        "chromadb": f"http://{trainer_host}:8100",
        "redis": f"{redis_host}:{redis_port}",
    }


def get_db_connect_kwargs(
    database: str = "myllm_core_db",
    role: str = "admin",
    env: str | None = None,
    pv: Any | None = None,
) -> dict[str, Any]:
    """Parámetros de conexión MariaDB (host/puerto de env.yaml, creds de protected)."""
    env_name = env or get_active_test_environment()
    data = load_env_yaml(env_name)
    if pv is None:
        pv = load_protected_values(env_name)

    host = str(data.get("mariadb_host") or getattr(pv, "mariadb_host", "localhost"))
    port = int(data.get("mariadb_port") or getattr(pv, "mariadb_port", 3306))

    role_map = {
        "admin": ("mariadb_admin_user", "mariadb_admin_password"),
        "writer": ("mariadb_writer_user", "mariadb_writer_password"),
        "reader": ("mariadb_reader_user", "mariadb_reader_password"),
    }
    user_attr, pass_attr = role_map.get(role, role_map["admin"])
    return {
        "host": host,
        "port": port,
        "user": getattr(pv, user_attr),
        "password": getattr(pv, pass_attr),
        "database": database,
    }


def row_value(row: Any, key: str, index: int = 0) -> Any:
    """Lee un campo de fila pymysql (DictCursor o tupla)."""
    if isinstance(row, dict):
        return row[key]
    return row[index]


def get_storage_paths(env: str | None = None) -> dict[str, str]:
    """Rutas de storage desde env.yaml (external/internal del entorno activo)."""
    data = load_env_yaml(env)
    external = str(
        data.get("backend_core_base_storage")
        or data.get("fmanagement_base_path")
        or ""
    )
    internal = str(data.get("backend_core_internal_storage") or "")
    return {
        "external": external,
        "internal": internal,
        "reports": str(data.get("backend_core_reports_storage") or ""),
        "models": str(data.get("backend_core_models_storage") or ""),
    }


def is_local_storage_path(path: str | Path) -> bool:
    """True si la ruta existe en este host (macbook). False en silicon/remoto."""
    if not path:
        return False
    return Path(path).expanduser().exists()


def install_requests_shim() -> None:
    """Expone ``requests`` vía httpx si el paquete no está instalado."""
    if "requests" in sys.modules:
        return
    try:
        import requests as _requests  # noqa: F401

        return
    except ImportError:
        pass

    import types

    try:
        import httpx
    except ImportError as exc:
        raise ImportError(
            "Ni 'requests' ni 'httpx' están disponibles para los tests E2E"
        ) from exc

    def _request(method: str, url: str, **kwargs: Any) -> Any:
        timeout = kwargs.pop("timeout", 10)
        json_body = kwargs.pop("json", None)
        data = kwargs.pop("data", None)
        headers = kwargs.pop("headers", None)
        params = kwargs.pop("params", None)
        follow_redirects = kwargs.pop("allow_redirects", True)
        if "follow_redirects" in kwargs:
            follow_redirects = kwargs.pop("follow_redirects")
        req_kwargs: dict[str, Any] = {
            "headers": headers,
            "params": params,
        }
        if json_body is not None:
            req_kwargs["json"] = json_body
        elif isinstance(data, (bytes, bytearray)):
            req_kwargs["content"] = data
        elif isinstance(data, str):
            req_kwargs["content"] = data.encode()
        elif data is not None:
            req_kwargs["data"] = data
        with httpx.Client(timeout=timeout, follow_redirects=follow_redirects) as client:
            return client.request(method, url, **req_kwargs)

    class RequestException(Exception):
        """Excepción base compatible con requests."""

    class ConnectionError(RequestException):
        """Error de conexión compatible con requests."""

    class HTTPError(RequestException):
        """Error HTTP compatible con requests."""

    class Timeout(RequestException):
        """Timeout compatible con requests."""

    shim = types.ModuleType("requests")
    shim.get = lambda url, **kwargs: _request("GET", url, **kwargs)
    shim.post = lambda url, **kwargs: _request("POST", url, **kwargs)
    shim.put = lambda url, **kwargs: _request("PUT", url, **kwargs)
    shim.patch = lambda url, **kwargs: _request("PATCH", url, **kwargs)
    shim.head = lambda url, **kwargs: _request("HEAD", url, **kwargs)
    shim.delete = lambda url, **kwargs: _request("DELETE", url, **kwargs)
    shim.exceptions = types.SimpleNamespace(
        RequestException=RequestException,
        ConnectionError=ConnectionError,
        HTTPError=HTTPError,
        Timeout=Timeout,
    )
    sys.modules["requests"] = shim


def fetch_user_otp(user_name: str, database: str = "myllm_core_db") -> str:
    """Lee el OTP actual de un usuario (DictCursor)."""
    conn = get_db_connection(database=database)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_otp FROM users WHERE user_name = %s",
                (user_name,),
            )
            row = cursor.fetchone()
        if not row:
            raise ValueError(f"Usuario no encontrado: {user_name}")
        return str(row_value(row, "user_otp", 0))
    finally:
        conn.close()


def get_db_connection(pv: Any | None = None, database: str = "myllm_core_db"):
    """Crea una conexión pymysql usando host de env.yaml y credenciales protegidas."""
    import pymysql

    kwargs = get_db_connect_kwargs(database=database, role="admin", pv=pv)
    return pymysql.connect(
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        **kwargs,
    )


def get_db_engine(pv: Any | None = None, database: str = "myllm_core_db"):
    """Crea un SQLAlchemy engine usando host de env.yaml y credenciales protegidas."""
    from urllib.parse import quote_plus

    from sqlalchemy import create_engine

    kwargs = get_db_connect_kwargs(database=database, role="admin", pv=pv)
    password_encoded = quote_plus(str(kwargs["password"]))
    dsn = (
        f"mysql+pymysql://{kwargs['user']}:{password_encoded}"
        f"@{kwargs['host']}:{kwargs['port']}/{database}"
    )
    return create_engine(dsn)


def emit_shell_exports(env: str | None = None) -> str:
    """Exports bash para ``full_test.sh`` (sin secretos)."""
    env_name = env or get_active_test_environment()
    urls = get_service_urls(env=env_name)
    data = load_env_yaml(env_name)
    mariadb_host = str(data.get("mariadb_host") or "")
    mariadb_port = str(data.get("mariadb_port") or "3306")
    storage = get_storage_paths(env_name)
    lines = [
        f"export ANEWHOPE_ENV={env_name}",
        f"export ENVIRONMENT={env_name}",
        f"export TEST_MIDDLEWARE_URL={urls['middleware']}",
        f"export TEST_BACKEND_CORE_URL={urls['backend_core']}",
        f"export TEST_BROKER_URL={urls['broker']}",
        f"export TEST_TRAINER_URL={urls['trainer']}",
        f"export TEST_FMANAGEMENT_URL={urls['fmanagement']}",
        f"export TEST_FRONTEND_URL={urls['frontend']}",
        f"export TEST_BACKOFFICE_URL={urls['backoffice']}",
        f"export TEST_MARIADB_HOST={mariadb_host}",
        f"export TEST_MARIADB_PORT={mariadb_port}",
        f"export TEST_STORAGE_EXTERNAL={storage['external']}",
        f"export TEST_STORAGE_INTERNAL={storage['internal']}",
    ]
    return "\n".join(lines)

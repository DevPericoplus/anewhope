"""Carga de configuración por entorno desde .env y protected_values."""

from __future__ import annotations

import logging
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

logger = logging.getLogger(__name__)

_ENV_LOADED = False
_PROTECTED_CACHE: ModuleType | None = None


def _get_repo_root() -> Path:
    """Obtiene la ruta raíz del repositorio."""

    return Path(__file__).resolve().parents[3]


def load_env_file(env_path: Path | None = None) -> dict[str, str]:
    """Carga variables desde .env y env.yaml para el entorno activo."""

    global _ENV_LOADED
    if _ENV_LOADED:
        return {}

    env_file = env_path or (_get_repo_root() / ".env")
    if env_file.exists():
        _load_env_lines(env_file)

    # Leer directamente sin llamar a get_environment_name() para evitar recursión
    env_name = os.environ.get("ENVIRONMENT") or os.environ.get("environment") or "macbook"
    env_yaml = (
        _get_repo_root()
        / "infrastructure"
        / "environments"
        / env_name
        / "env.yaml"
    )
    if env_yaml.exists():
        _load_yaml_lines(env_yaml)

    _ENV_LOADED = True
    return {}


def _load_env_lines(env_file: Path) -> None:
    """Carga variables desde un archivo .env."""

    try:
        raw_lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw_line in raw_lines:
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            continue
        _set_env_pair(parsed)


def _load_yaml_lines(env_file: Path) -> None:
    """Carga variables desde un YAML simple (clave: valor)."""

    try:
        raw_lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw_line in raw_lines:
        parsed = _parse_yaml_line(raw_line)
        if parsed is None:
            continue
        _set_env_pair(parsed, include_upper=True)


def _parse_env_line(raw_line: str) -> tuple[str, str] | None:
    """Normaliza una linea del .env."""

    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[7:].strip()
    if "=" in line:
        key, value = line.split("=", 1)
    elif ":" in line:
        key, value = line.split(":", 1)
    else:
        return None
    key = key.strip()
    value = value.strip().strip("'").strip('"')
    if not key:
        return None
    return key, value


def _parse_yaml_line(raw_line: str) -> tuple[str, str] | None:
    """Normaliza una linea de YAML simple."""

    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if ":" not in line:
        return None
    key, value = line.split(":", 1)
    key = key.strip()
    value = value.strip().strip("'").strip('"')
    if not key:
        return None
    return key, value


def _set_env_pair(pair: tuple[str, str], include_upper: bool = False) -> None:
    """Registra un par clave/valor en el entorno."""

    key, value = pair
    os.environ.setdefault(key, value)
    if key.lower() == "environment":
        os.environ.setdefault("ENVIRONMENT", value)
    if include_upper:
        os.environ.setdefault(key.upper(), value)


def get_env_value(name: str, default: str) -> str:
    """Obtiene un valor del entorno asegurando la carga de .env."""

    if not _ENV_LOADED:
        load_env_file()
    return os.environ.get(name, default)


def get_environment_name(default: str = "macbook") -> str:
    """Obtiene el nombre del entorno activo."""

    load_env_file()
    return os.environ.get("ENVIRONMENT") or os.environ.get("environment") or default


def get_protected_values_path(environment: str | None = None) -> Path:
    """Resuelve la ruta del protected_values.py por entorno."""

    env_name = environment or get_environment_name()
    return (
        _get_repo_root()
        / "infrastructure"
        / "environments"
        / env_name
        / "protected_values.py"
    )


def load_protected_values_module() -> ModuleType | None:
    """Carga el módulo protected_values.py del entorno activo."""

    global _PROTECTED_CACHE
    if _PROTECTED_CACHE is not None:
        return _PROTECTED_CACHE

    if not _ENV_LOADED:
        load_env_file()
    env_name = get_environment_name()
    module_path = get_protected_values_path(env_name)
    if not module_path.exists():
        logger.warning(
            "No se encontró protected_values.py en %s", module_path
        )
        return None

    module_name = f"protected_values_{env_name}"
    spec = spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        logger.error("No se pudo cargar protected_values.py desde %s", module_path)
        return None
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    _PROTECTED_CACHE = module
    return module


def get_protected_value(name: str, default: Any | None = None) -> Any:
    """Obtiene un valor de protected_values.py con fallback."""

    module = load_protected_values_module()
    if module is None:
        return default
    return getattr(module, name, default)


def load_protected_settings() -> dict[str, Any]:
    """Devuelve un diccionario con la configuración protegida."""

    module = load_protected_values_module()
    if module is None:
        return {}
    return {
        key: value
        for key, value in module.__dict__.items()
        if not key.startswith("_")
    }

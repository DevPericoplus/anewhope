"""Carga de configuración por entorno desde .envglobal, .env y protected_values."""

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
_CURRENT_ENVIRONMENT: str | None = None

# Constantes
VALID_ENVIRONMENTS = ("macbook", "dev", "pre", "pro", "silicon")
ENV_YAML_FILENAME = "env.yaml"
PROTECTED_VALUES_FILENAME = "protected_values.py"
ENVGLOBAL_FILENAME = ".envglobal"


def _get_repo_root() -> Path:
    """Obtiene la ruta raíz del repositorio."""

    return Path(__file__).resolve().parents[3]


def _load_envglobal() -> str | None:
    """
    Carga el entorno desde .envglobal (archivo global de configuración de entorno).
    
    Returns:
        Nombre del entorno o None si no existe el archivo.
    """
    global _CURRENT_ENVIRONMENT
    
    if _CURRENT_ENVIRONMENT is not None:
        return _CURRENT_ENVIRONMENT
    
    envglobal_path = _get_repo_root() / ".envglobal"
    if not envglobal_path.exists():
        return None
    
    try:
        raw_lines = envglobal_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    
    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key == "current_environment" and value:
                if value in VALID_ENVIRONMENTS:
                    _CURRENT_ENVIRONMENT = value
                    os.environ.setdefault("ENVIRONMENT", value)
                    os.environ.setdefault("environment", value)
                    return value
                else:
                    logger.warning(
                        "Entorno '%s' en .envglobal no es válido. "
                        "Valores permitidos: %s",
                        value,
                        ", ".join(VALID_ENVIRONMENTS),
                    )
    return None


def load_env_file(env_path: Path | None = None) -> dict[str, str]:
    """Carga variables desde .envglobal, .env y env.yaml para el entorno activo."""

    global _ENV_LOADED
    if _ENV_LOADED:
        return {}

    # 1. Primero cargar .envglobal para establecer el entorno
    _load_envglobal()

    # 2. Luego cargar .env (puede sobrescribir ENVIRONMENT si está definido)
    env_file = env_path or (_get_repo_root() / ".env")
    if env_file.exists():
        _load_env_lines(env_file)

    # 3. Determinar el entorno final (prioridad: .env > .envglobal > default)
    env_name = (
        os.environ.get("ENVIRONMENT") 
        or os.environ.get("environment") 
        or _CURRENT_ENVIRONMENT 
        or "macbook"
    )
    
    # 4. Cargar env.yaml del entorno
    env_yaml = (
        _get_repo_root()
        / "infrastructure"
        / "environments"
        / env_name
        / ENV_YAML_FILENAME
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
    """
    Obtiene el nombre del entorno activo.
    
    Orden de prioridad:
    1. Variable de entorno ENVIRONMENT
    2. Variable de entorno environment
    3. Valor de .envglobal (current_environment)
    4. Valor por defecto ("macbook")
    """
    load_env_file()
    return (
        os.environ.get("ENVIRONMENT") 
        or os.environ.get("environment") 
        or _CURRENT_ENVIRONMENT 
        or default
    )


def get_protected_values_path(environment: str | None = None) -> Path:
    """Resuelve la ruta del protected_values.py por entorno."""

    env_name = environment or get_environment_name()
    return (
        _get_repo_root()
        / "infrastructure"
        / "environments"
        / env_name
        / PROTECTED_VALUES_FILENAME
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


# ========================================
# Funciones de utilidad para aplicaciones
# ========================================


def get_env_yaml_path(environment: str | None = None) -> Path:
    """
    Obtiene la ruta al archivo env.yaml del entorno.
    
    Args:
        environment: Nombre del entorno (si no se proporciona, usa el activo)
        
    Returns:
        Path al archivo env.yaml
    """
    env_name = environment or get_environment_name()
    return (
        _get_repo_root()
        / "infrastructure"
        / "environments"
        / env_name
        / ENV_YAML_FILENAME
    )


def get_environment_paths() -> dict[str, Path]:
    """
    Obtiene todas las rutas de configuración del entorno activo.
    
    Returns:
        Diccionario con las rutas de configuración:
        - root: Raíz del repositorio
        - env_yaml: Archivo de variables públicas
        - protected_values: Archivo de variables protegidas
        - envglobal: Archivo de configuración global de entorno
    """
    root = _get_repo_root()
    env_name = get_environment_name()
    env_dir = root / "infrastructure" / "environments" / env_name
    
    return {
        "root": root,
        "env_yaml": env_dir / ENV_YAML_FILENAME,
        "protected_values": env_dir / PROTECTED_VALUES_FILENAME,
        "envglobal": root / ENVGLOBAL_FILENAME,
        "environment": env_name,
    }


def print_environment_info() -> None:
    """
    Imprime información del entorno para diagnóstico.
    Útil para verificar la configuración cargada.
    """
    paths = get_environment_paths()
    print(f"Entorno activo: {paths['environment']}")
    print(f"  Root: {paths['root']}")
    print(f"  env.yaml: {paths['env_yaml']} (existe: {paths['env_yaml'].exists()})")
    print(f"  protected_values: {paths['protected_values']} (existe: {paths['protected_values'].exists()})")
    print(f"  .envglobal: {paths['envglobal']} (existe: {paths['envglobal'].exists()})")

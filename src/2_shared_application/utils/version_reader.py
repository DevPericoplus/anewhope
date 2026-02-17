"""
Módulo para leer versiones de aplicaciones desde versions.yml.

Este módulo proporciona funciones para leer las versiones de todas las aplicaciones
del sistema desde el archivo versions.yml ubicado en la raíz del proyecto.

Uso:
    from utils.version_reader import get_version

    version = get_version("frontend")  # Retorna "0.7.1"
"""

import yaml
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Cache de versiones para evitar lecturas repetidas del archivo
_versions_cache: Optional[dict] = None


def _load_versions_file() -> dict:
    """
    Carga el archivo versions.yml desde la raíz del proyecto.

    Returns:
        dict: Diccionario con las versiones de todas las aplicaciones
    """
    global _versions_cache

    if _versions_cache is not None:
        return _versions_cache

    try:
        # Buscar versions.yml en la raíz del proyecto
        # Asumimos que este archivo está en src/2_shared_application/utils/
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        versions_file = project_root / "versions.yml"

        if not versions_file.exists():
            logger.warning(f"Archivo versions.yml no encontrado en: {versions_file}")
            return {}

        with open(versions_file, 'r', encoding='utf-8') as f:
            versions = yaml.safe_load(f)

        _versions_cache = versions or {}
        logger.info(f"Versiones cargadas desde {versions_file}")
        return _versions_cache

    except Exception as e:
        logger.error(f"Error al cargar versions.yml: {e}")
        return {}


def get_version(app_name: str) -> str:
    """
    Obtiene la versión de una aplicación específica.

    Args:
        app_name: Nombre de la aplicación sin prefijo "version_"
                 Ejemplos: "frontend", "backoffice", "backend_core"

    Returns:
        str: Versión en formato "X.Y.Z" o "unknown" si no se encuentra

    Examples:
        >>> get_version("frontend")
        '0.7.1'
        >>> get_version("backend_core")
        '0.7.1'
    """
    versions = _load_versions_file()
    version_key = f"version_{app_name}"

    version = versions.get(version_key, "unknown")

    if version == "unknown":
        logger.warning(f"Versión no encontrada para: {app_name}")

    return version


def get_all_versions() -> dict:
    """
    Obtiene todas las versiones del sistema.

    Returns:
        dict: Diccionario con todas las versiones
    """
    return _load_versions_file().copy()


def reload_versions() -> None:
    """
    Recarga el archivo versions.yml desde disco.
    Útil si el archivo ha sido modificado durante la ejecución.
    """
    global _versions_cache
    _versions_cache = None
    _load_versions_file()


def get_version_info(app_name: str) -> dict:
    """
    Obtiene información detallada de la versión de una aplicación.

    Args:
        app_name: Nombre de la aplicación

    Returns:
        dict: Diccionario con version, major, minor, patch

    Examples:
        >>> get_version_info("frontend")
        {'version': '0.7.1', 'major': 0, 'minor': 7, 'patch': 1}
    """
    version = get_version(app_name)

    if version == "unknown":
        return {
            'version': version,
            'major': 0,
            'minor': 0,
            'patch': 0
        }

    try:
        parts = version.split('.')
        return {
            'version': version,
            'major': int(parts[0]) if len(parts) > 0 else 0,
            'minor': int(parts[1]) if len(parts) > 1 else 0,
            'patch': int(parts[2]) if len(parts) > 2 else 0
        }
    except (ValueError, IndexError) as e:
        logger.error(f"Error parseando versión {version}: {e}")
        return {
            'version': version,
            'major': 0,
            'minor': 0,
            'patch': 0
        }


if __name__ == "__main__":
    # Test del módulo
    print("=== Test de version_reader ===")
    print(f"Frontend: {get_version('frontend')}")
    print(f"Backoffice: {get_version('backoffice')}")
    print(f"Backend Core: {get_version('backend_core')}")
    print(f"Backend IA: {get_version('backend_ia')}")
    print(f"Middleware: {get_version('middleware')}")
    print(f"Broker: {get_version('broker')}")
    print(f"fmanagement: {get_version('fmanagement')}")
    print("\nTodas las versiones:")
    print(get_all_versions())

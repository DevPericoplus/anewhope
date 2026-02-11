"""Módulo para gestión de archivos de informes markdown.

Este módulo proporciona funciones para:
- Leer configuración de entorno para obtener paths de storage
- Listar archivos markdown de informes por versión
- Leer contenido de archivos markdown
"""

import os
import yaml
import logging
import importlib.util
from pathlib import Path
from typing import Optional


# Configurar logging
logger = logging.getLogger("InformesManager")
logger.setLevel(logging.DEBUG)

# Añadir handler para consola si no existe
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(name)s] %(levelname)s: %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Cache para almacenar valores leídos de configuración
_config_cache: dict[str, str] = {}

# Cache para el módulo storage_access_structure
_storage_module = None


def _get_storage_module():
    """Carga dinámicamente el módulo storage_access_structure."""
    global _storage_module

    if _storage_module is not None:
        return _storage_module

    storage_path = Path(__file__).parent / "storage_access_structure.py"
    spec = importlib.util.spec_from_file_location("storage_access_structure", storage_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar el módulo storage_access_structure")

    _storage_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_storage_module)

    return _storage_module


def _get_project_root() -> Path:
    """Obtiene la raíz del proyecto (donde está .envglobal)."""
    # Desde src/2_shared_application hasta la raíz del proyecto
    return Path(__file__).resolve().parents[2]


def _read_current_environment() -> str:
    """Lee el entorno actual desde .envglobal.

    Returns:
        Nombre del entorno (macbook, dev, pre, pro)
    """
    if "current_environment" in _config_cache:
        return _config_cache["current_environment"]

    envglobal_path = _get_project_root() / ".envglobal"

    try:
        with open(envglobal_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("current_environment:"):
                    env = line.split(":", 1)[1].strip()
                    _config_cache["current_environment"] = env
                    logger.info(f"Entorno leído de .envglobal: {env}")
                    return env
    except Exception as e:
        logger.error(f"No se pudo leer .envglobal: {e}")
        return "macbook"  # Default fallback

    return "macbook"  # Default fallback


def _read_env_yaml(key: str) -> Optional[str]:
    """Lee una variable del archivo env.yaml del entorno actual.

    Args:
        key: Nombre de la variable a leer

    Returns:
        Valor de la variable o None si no existe
    """
    if key in _config_cache:
        return _config_cache[key]

    env = _read_current_environment()
    env_yaml_path = _get_project_root() / "infrastructure" / "environments" / env / "env.yaml"

    try:
        with open(env_yaml_path, "r") as f:
            config = yaml.safe_load(f)
            value = config.get(key)
            if value:
                _config_cache[key] = str(value)
                logger.debug(f"Variable '{key}' leída de env.yaml: {value}")
                return str(value)
    except Exception as e:
        logger.error(f"No se pudo leer env.yaml: {e}")
        return None

    return None


def get_backend_storage_path() -> str:
    """Obtiene el path base de almacenamiento interno del backend core.

    Returns:
        Path expandido del directorio de storage interno (donde se sincronizan los informes)
        Ejemplo: /Users/administrator/data/anewhope/files/backend_server/internal
    """
    storage_path = _read_env_yaml("backend_core_internal_storage")

    if not storage_path:
        logger.error("No se encontró backend_core_internal_storage en configuración")
        return ""

    # Expandir ~ a home directory
    expanded_path = os.path.expanduser(storage_path)
    logger.info(f"Path de storage interno: {expanded_path}")
    return expanded_path


def build_version_path(org_id: int, project_id: int, version_id: int) -> str:
    """Construye el path completo a una carpeta de versión.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión

    Returns:
        Path completo a la carpeta de versión
        Ejemplo: /Users/.../internal/ORG00001/PRJ00001/v001
    """
    storage_module = _get_storage_module()

    base_path = get_backend_storage_path()
    if not base_path:
        logger.error("No se pudo obtener base_path")
        return ""

    org_folder = storage_module.get_folder_by_id_organization(org_id)
    prj_folder = storage_module.get_folder_by_id_project(project_id)
    ver_folder = storage_module.get_folder_by_id_version(version_id)

    full_path = os.path.join(base_path, org_folder, prj_folder, ver_folder)

    logger.info(f"Path construido:")
    logger.info(f"  org_id={org_id} -> {org_folder}")
    logger.info(f"  project_id={project_id} -> {prj_folder}")
    logger.info(f"  version_id={version_id} -> {ver_folder}")
    logger.info(f"  full_path={full_path}")

    return full_path


def list_markdown_files(org_id: int, project_id: int, version_id: int) -> list[dict]:
    """Lista archivos markdown en una carpeta de versión.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión

    Returns:
        Lista de diccionarios con información de archivos, ordenados por fecha (nombre):
        [
            {
                "filename": "2026_01_30_225100_tabla_de_resultados",
                "full_path": "/path/to/file.md",
                "display_name": "2026_01_30_225100_tabla_de_resultados"
            },
            ...
        ]

        Si no hay archivos o la carpeta no existe, retorna lista vacía []
    """
    logger.info(f"=== list_markdown_files llamado ===")
    logger.info(f"Parámetros: org_id={org_id}, project_id={project_id}, version_id={version_id}")

    version_path = build_version_path(org_id, project_id, version_id)

    logger.info(f"Version path: {version_path}")
    logger.info(f"Path exists: {os.path.exists(version_path) if version_path else False}")

    if not version_path:
        logger.error("Version path está vacío")
        return []

    if not os.path.exists(version_path):
        logger.error(f"Path no existe: {version_path}")
        # Intentar listar el path padre para ver qué hay
        parent_path = os.path.dirname(version_path)
        if os.path.exists(parent_path):
            logger.info(f"Contenido del directorio padre ({parent_path}):")
            try:
                for item in os.listdir(parent_path):
                    logger.info(f"  - {item}")
            except Exception as e:
                logger.error(f"Error listando directorio padre: {e}")
        return []

    try:
        files = []
        all_files = os.listdir(version_path)
        logger.info(f"Archivos totales en directorio: {len(all_files)}")
        logger.info(f"Archivos: {all_files}")

        for filename in all_files:
            if filename.endswith(".md"):
                # Quitar extensión .md para display_name
                display_name = filename[:-3]
                full_path = os.path.join(version_path, filename)

                files.append({
                    "filename": filename,
                    "full_path": full_path,
                    "display_name": display_name
                })
                logger.debug(f"Archivo .md encontrado: {filename}")

        # Ordenar por nombre de archivo (que incluye fecha YYYY_MM_DD al inicio)
        files.sort(key=lambda x: x["filename"])

        logger.info(f"Total archivos .md encontrados: {len(files)}")

        return files

    except Exception as e:
        logger.error(f"Error listando archivos en {version_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def read_markdown_file(file_path: str) -> Optional[str]:
    """Lee el contenido de un archivo markdown.

    Args:
        file_path: Path completo al archivo .md

    Returns:
        Contenido del archivo como string, o None si hay error
    """
    logger.debug(f"Intentando leer archivo: {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"Archivo no encontrado: {file_path}")
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            logger.info(f"Archivo leído exitosamente: {len(content)} caracteres")
            return content
    except Exception as e:
        logger.error(f"Error leyendo archivo {file_path}: {e}")
        return None


def get_markdown_content_by_name(
    org_id: int,
    project_id: int,
    version_id: int,
    display_name: str
) -> Optional[str]:
    """Obtiene el contenido markdown dado el display_name del archivo.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        display_name: Nombre sin extensión (ej: "2026_01_30_tabla_de_resultados")

    Returns:
        Contenido del archivo markdown o None si no existe
    """
    logger.info(f"=== get_markdown_content_by_name llamado ===")
    logger.info(f"Parámetros: org_id={org_id}, project_id={project_id}, version_id={version_id}")
    logger.info(f"Display name: {display_name}")

    # Agregar extensión .md
    filename = f"{display_name}.md"
    version_path = build_version_path(org_id, project_id, version_id)

    if not version_path:
        logger.error("Version path está vacío")
        return None

    full_path = os.path.join(version_path, filename)
    logger.info(f"Full path del archivo: {full_path}")

    return read_markdown_file(full_path)

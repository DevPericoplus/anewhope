"""Funciones para gestión de tipos de identidad en el sistema."""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_identity_types_file_path() -> Path:
    """
    Obtiene la ruta del archivo JSON de tipos de identidad (datos mock).

    Returns:
        Ruta al archivo roles.json.
    """
    return (
        Path(__file__).parent.parent.parent
        / "2_shared_application"
        / "moks"
        / "roles.json"
    )


def _load_identity_types() -> list[dict[str, Any]]:
    """
    Carga los tipos de identidad desde el archivo JSON.

    Returns:
        Lista de tipos de identidad como diccionarios.
    """
    data_file = _get_identity_types_file_path()
    if not data_file.exists():
        logger.warning(f"El archivo de tipos de identidad no existe: {data_file}")
        return []

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error al cargar tipos de identidad desde {data_file}: {e}")
        return []


def get_identity_types_dict_id_name_sup_9() -> dict[int, str]:
    """
    Devuelve un diccionario {identity_type_id: identity_type_name} para aquellos
    identity_type_id superiores a 9, ordenado por identity_type_id.

    Returns:
        Diccionario ordenado por identity_type_id > 9.
    """
    identity_types = _load_identity_types()
    if not identity_types:
        return {}

    filtered = {
        identity_type["identity_type_id"]: identity_type["identity_type_name"]
        for identity_type in identity_types
        if isinstance(identity_type.get("identity_type_id"), int)
        and identity_type["identity_type_id"] > 9
    }

    # Ordenar el diccionario por identity_type_id
    result = dict(sorted(filtered.items()))

    # Verificación de tipo
    assert isinstance(result, dict), f"El resultado no es un diccionario, es {type(result)}"
    logger.debug(f"Valores retornados por la función: {result}")
    return result

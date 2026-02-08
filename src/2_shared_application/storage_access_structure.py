"""Utilidades para construir identificadores de carpetas en storage."""

from __future__ import annotations


def get_folder_by_id_organization(id_organization: int) -> str:
    """Devuelve el identificador de carpeta para una organización."""

    return f"ORG{id_organization:04d}"


def get_folder_by_id_project(id_project: int) -> str:
    """Devuelve el identificador de carpeta para un proyecto."""

    return f"PRJ{id_project:05d}"


def get_folder_by_id_version(id_version: int) -> str:
    """Devuelve el identificador de carpeta para una versión.

    Args:
        id_version: ID numérico de la versión (ej: 1, 2, 3)

    Returns:
        String formateado como "v001", "v002", "v003", etc.
    """

    return f"v{id_version:03d}"

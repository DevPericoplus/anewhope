"""Utilidades para construir identificadores de carpetas en storage."""

from __future__ import annotations


def get_folder_by_id_organization(id_organization: int) -> str:
    """Devuelve el identificador de carpeta para una organización."""

    return f"ORG{id_organization:04d}"


def get_folder_by_id_project(id_project: int) -> str:
    """Devuelve el identificador de carpeta para un proyecto."""

    return f"PRJ{id_project:04d}"

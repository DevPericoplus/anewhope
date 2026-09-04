"""Utilidades para construir identificadores de carpetas en storage."""

from __future__ import annotations


def get_folder_by_id_organization(id_organization: int) -> str:
    """Devuelve el identificador de carpeta para una organización."""

    return f"ORG{id_organization:05d}"


def get_folder_by_id_user(id_user: int) -> str:
    """Devuelve el identificador de carpeta para un usuario individual."""

    return f"USER{id_user:05d}"


def get_account_storage_folder(
    organization_id: int | None, user_id: int
) -> str:
    """Carpeta raíz de storage: ORG##### o USER#####."""

    if organization_id and organization_id > 0:
        return get_folder_by_id_organization(organization_id)
    return get_folder_by_id_user(user_id)


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


def build_fmo_path_segments(
    organization_id: int | None,
    user_id: int,
    project_id: int,
    version_id: int | None = None,
    version_path: str = "",
    subfolders: str = "",
) -> dict[str, str]:
    """Segmentos de ruta para fmanagement: cuenta / proyecto / versión.

    `orgpath` es ORG##### si el proyecto pertenece a una organización,
    o USER##### si el dueño es una cuenta individual.
    """

    resolved_version = version_path
    if not resolved_version and version_id is not None:
        resolved_version = get_folder_by_id_version(version_id)

    return {
        "orgpath": get_account_storage_folder(organization_id, user_id),
        "prjpath": get_folder_by_id_project(project_id),
        "versionpath": resolved_version,
        "subfolders": subfolders,
    }

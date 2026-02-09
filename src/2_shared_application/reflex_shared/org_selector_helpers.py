"""Funciones helper para selectores de organización/proyecto en Reflex States.

Diseñado para ser invocado desde cualquier State de Reflex del backoffice
sin necesidad de herencia. Usa composición: cada State llama a estas
funciones pasando sus propios campos.

Uso en un State de Reflex::

    from src.2_shared_application.reflex_shared.org_selector_helpers import (
        load_organizations_for_selector,
        load_projects_for_selector,
        load_versions_for_selector,
        find_org_id_by_name,
        find_project_id_by_name,
        find_version_id_by_number,
    )

    class MiPageState(rx.State):
        organizations: list[dict[str, Any]] = []
        selected_org_id: int = 0

        async def _load_organizations(self) -> None:
            orgs, default_id = load_organizations_for_selector(
                user_id=self.user_id,
                identity_type_id=self.identity_type_id,
                session_org_id=self.organization_id,
            )
            async with self:
                self.organizations = orgs
                if self.selected_org_id == 0 and default_id > 0:
                    self.selected_org_id = default_id
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

# Importar OrganizationAccessService con importlib (directorio padre tiene número)
_service_path = Path(__file__).resolve().parents[1] / "services" / "organization_access_service.py"
_service_spec = importlib.util.spec_from_file_location("organization_access_service", _service_path)
_service_module = importlib.util.module_from_spec(_service_spec)
_service_spec.loader.exec_module(_service_module)
OrganizationAccessService = _service_module.OrganizationAccessService

logger = logging.getLogger(__name__)

# Instancia singleton del servicio (sin estado, seguro para compartir)
_service = OrganizationAccessService()


# ============================================================================
# Funciones de carga de datos
# ============================================================================


def load_organizations_for_selector(
    user_id: int,
    identity_type_id: int,
    session_org_id: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Carga organizaciones y determina la selección por defecto.

    Args:
        user_id: ID del usuario en sesión.
        identity_type_id: Tipo de identidad (1=SuperAdmin, etc.).
        session_org_id: ID de organización de la sesión actual.

    Returns:
        Tupla (lista_organizaciones, org_id_por_defecto).
        Cada organización es un dict con claves ``id`` y ``name``.
    """
    orgs = _service.get_accessible_organizations(user_id, identity_type_id)
    default_id = _service.get_default_organization_id(
        user_id, identity_type_id, session_org_id
    )
    return orgs, default_id


def load_projects_for_selector(
    user_id: int,
    identity_type_id: int,
    organization_id: int,
) -> tuple[list[dict[str, Any]], int]:
    """Carga proyectos de una organización y determina la selección por defecto.

    Args:
        user_id: ID del usuario.
        identity_type_id: Tipo de identidad.
        organization_id: ID de la organización seleccionada.

    Returns:
        Tupla (lista_proyectos, proyecto_id_por_defecto).
        Cada proyecto es un dict con claves ``id`` y ``name``.
    """
    if organization_id <= 0:
        return [], 0

    projects = _service.get_accessible_projects(
        user_id, identity_type_id, organization_id
    )
    default_id = _service.get_default_project_id(
        user_id, identity_type_id, organization_id
    )
    return projects, default_id


def load_versions_for_selector(
    organization_id: int,
    project_id: int,
) -> tuple[list[dict[str, Any]], int]:
    """Carga versiones de un proyecto y determina la selección por defecto.

    Args:
        organization_id: ID de la organización.
        project_id: ID del proyecto.

    Returns:
        Tupla (lista_versiones, version_id_por_defecto).
        Cada versión es un dict con claves ``version_id``, ``state_internal``
        y ``created_at``.
    """
    if organization_id <= 0 or project_id <= 0:
        return [], 0

    versions = _service.get_accessible_versions(organization_id, project_id)
    default_id = versions[0]["version_id"] if versions else 0
    return versions, default_id


# ============================================================================
# Funciones de búsqueda (para on_change de rx.select)
# ============================================================================


def find_org_id_by_name(
    organizations: list[dict[str, Any]],
    name: str,
) -> int:
    """Busca el ID de una organización por su nombre.

    Args:
        organizations: Lista de dicts con ``id`` y ``name``.
        name: Nombre a buscar (valor de ``on_change`` del ``rx.select``).

    Returns:
        ID de la organización encontrada, o 0 si no se encuentra.
    """
    for org in organizations:
        if org.get("name") == name:
            return org["id"]
    return 0


def find_project_id_by_name(
    projects: list[dict[str, Any]],
    name: str,
) -> int:
    """Busca el ID de un proyecto por su nombre.

    Args:
        projects: Lista de dicts con ``id`` y ``name``.
        name: Nombre a buscar.

    Returns:
        ID del proyecto encontrado, o 0 si no se encuentra.
    """
    for proj in projects:
        if proj.get("name") == name:
            return proj["id"]
    return 0


def find_version_id_by_number(
    versions: list[dict[str, Any]],
    version_str: str,
) -> int:
    """Busca el ID de una versión por su número (string).

    Args:
        versions: Lista de dicts con ``version_id``.
        version_str: Número de versión como string.

    Returns:
        ID de la versión encontrada, o 0 si no se encuentra.
    """
    try:
        target_id = int(version_str)
    except (ValueError, TypeError):
        return 0

    for ver in versions:
        if ver.get("version_id") == target_id:
            return target_id
    return 0

"""Servicio centralizado de acceso a organizaciones y proyectos.

Encapsula TODA la lógica de "qué organizaciones/proyectos puede ver
un usuario interno" del backoffice, eliminando la duplicación de queries
SQL que existía en múltiples páginas.

Regla de negocio clave:
- SuperAdmin (identity_type_id=1): Ve TODAS las organizaciones y proyectos
- Otros usuarios internos: Solo ven organizaciones donde tienen asignación
  activa en ``asignaciones_organizaciones_internas``, y solo proyectos
  donde tienen asignación activa en ``proyectos_roles``

Uso::

    from src.2_shared_application.services.organization_access_service import (
        OrganizationAccessService,
    )

    service = OrganizationAccessService()
    orgs = service.get_accessible_organizations(user_id=5, identity_type_id=2)
    projects = service.get_accessible_projects(
        user_id=5, identity_type_id=2, organization_id=1
    )
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

# Importar db_query_helper con importlib (directorio padre tiene número)
_db_helper_path = Path(__file__).resolve().parents[1] / "db_query_helper.py"
_db_helper_spec = importlib.util.spec_from_file_location("db_query_helper", _db_helper_path)
_db_helper_module = importlib.util.module_from_spec(_db_helper_spec)
_db_helper_spec.loader.exec_module(_db_helper_module)
run_projects_db_query = _db_helper_module.run_projects_db_query

logger = logging.getLogger(__name__)

# identity_type_id del SuperAdmin
SUPER_ADMIN_IDENTITY_TYPE_ID = 1


class OrganizationAccessService:
    """Servicio que resuelve qué organizaciones y proyectos puede ver un usuario."""

    def get_accessible_organizations(
        self,
        user_id: int,
        identity_type_id: int,
    ) -> list[dict[str, Any]]:
        """Retorna las organizaciones accesibles para un usuario.

        Args:
            user_id: ID del usuario en sesión.
            identity_type_id: Tipo de identidad del usuario.

        Returns:
            Lista de dicts con claves ``id`` y ``name``, ordenados por nombre.
            Formato compatible con selectores de UI.
        """
        if identity_type_id == SUPER_ADMIN_IDENTITY_TYPE_ID:
            rows = run_projects_db_query(
                "SELECT organization_id, organization_name "
                "FROM myllm_core_db.organizations "
                "ORDER BY organization_name"
            )
        else:
            rows = run_projects_db_query(
                "SELECT DISTINCT o.organization_id, o.organization_name "
                "FROM myllm_core_db.organizations o "
                "INNER JOIN asignaciones_organizaciones_internas aoi "
                "ON o.organization_id = aoi.id_organizacion "
                f"WHERE aoi.id_usuario_interno = {int(user_id)} "
                "AND aoi.activo = 1 "
                "ORDER BY o.organization_name"
            )

        organizations = [
            {"id": int(row[0]), "name": row[1]}
            for row in rows
            if len(row) >= 2
        ]

        logger.debug(
            "Organizaciones accesibles para user_id=%s (identity=%s): %d",
            user_id,
            identity_type_id,
            len(organizations),
        )
        return organizations

    def get_accessible_projects(
        self,
        user_id: int,
        identity_type_id: int,
        organization_id: int,
    ) -> list[dict[str, Any]]:
        """Retorna los proyectos accesibles dentro de una organización.

        Args:
            user_id: ID del usuario en sesión.
            identity_type_id: Tipo de identidad del usuario.
            organization_id: ID de la organización seleccionada.

        Returns:
            Lista de dicts con claves ``id`` y ``name``, ordenados por nombre.
        """
        if organization_id <= 0:
            return []

        if identity_type_id == SUPER_ADMIN_IDENTITY_TYPE_ID:
            rows = run_projects_db_query(
                "SELECT id, nombre "
                "FROM proyectos "
                f"WHERE id_organizacion = {int(organization_id)} "
                "ORDER BY nombre"
            )
        else:
            rows = run_projects_db_query(
                "SELECT DISTINCT p.id, p.nombre "
                "FROM proyectos p "
                "INNER JOIN proyectos_roles pr "
                "ON p.id = pr.id_proyecto "
                f"WHERE p.id_organizacion = {int(organization_id)} "
                f"AND pr.id_usuario = {int(user_id)} "
                "AND pr.active = 1 "
                "AND pr.id_rol > 0 "
                "ORDER BY p.nombre"
            )

        projects = [
            {"id": int(row[0]), "name": row[1]}
            for row in rows
            if len(row) >= 2
        ]

        logger.debug(
            "Proyectos accesibles para user_id=%s org_id=%s: %d",
            user_id,
            organization_id,
            len(projects),
        )
        return projects

    def get_accessible_versions(
        self,
        organization_id: int,
        project_id: int,
    ) -> list[dict[str, Any]]:
        """Retorna las versiones de un proyecto.

        Las versiones no se filtran por asignación (si el usuario puede
        ver el proyecto, puede ver todas sus versiones).

        Args:
            organization_id: ID de la organización.
            project_id: ID del proyecto.

        Returns:
            Lista de dicts con claves ``version_id``, ``state_internal``
            y ``created_at``, ordenados por version_id descendente.
        """
        if organization_id <= 0 or project_id <= 0:
            return []

        rows = run_projects_db_query(
            "SELECT v.id_version, ev.state_internal, ev.created_at "
            "FROM versiones v "
            "INNER JOIN estado_version ev "
            "ON v.id_organizacion = ev.id_organizacion "
            "AND v.id_proyecto = ev.id_proyecto "
            "AND v.id_version = ev.id_version "
            f"WHERE v.id_organizacion = {int(organization_id)} "
            f"AND v.id_proyecto = {int(project_id)} "
            "ORDER BY v.id_version DESC"
        )

        versions = [
            {
                "version_id": int(row[0]),
                "state_internal": row[1] if len(row) > 1 else "",
                "created_at": row[2] if len(row) > 2 else "",
            }
            for row in rows
            if row
        ]

        logger.debug(
            "Versiones para org_id=%s project_id=%s: %d",
            organization_id,
            project_id,
            len(versions),
        )
        return versions

    def get_default_organization_id(
        self,
        user_id: int,
        identity_type_id: int,
        session_org_id: int,
    ) -> int:
        """Determina la organización por defecto al cargar una página.

        Prioridad:
        1. La organización de la sesión del usuario (si es accesible)
        2. La primera organización accesible
        3. 0 si no hay organizaciones accesibles

        Args:
            user_id: ID del usuario.
            identity_type_id: Tipo de identidad del usuario.
            session_org_id: ID de organización de la sesión activa.

        Returns:
            ID de la organización por defecto.
        """
        orgs = self.get_accessible_organizations(user_id, identity_type_id)
        if not orgs:
            return 0

        # Preferir la org de sesión si está en la lista
        if session_org_id > 0:
            for org in orgs:
                if org["id"] == session_org_id:
                    return session_org_id

        # Si no, la primera de la lista
        return orgs[0]["id"]

    def get_default_project_id(
        self,
        user_id: int,
        identity_type_id: int,
        organization_id: int,
    ) -> int:
        """Determina el proyecto por defecto para una organización.

        Returns:
            ID del primer proyecto accesible, o 0 si no hay ninguno.
        """
        projects = self.get_accessible_projects(
            user_id, identity_type_id, organization_id
        )
        if not projects:
            return 0
        return projects[0]["id"]

"""Contrato de acceso a roles por organización para la capa de aplicación."""

from __future__ import annotations

from typing import Protocol

from src.1_shared_domain.security_hierarchy import ManageRolesByOrg


class ManageRolesByOrgRepository(Protocol):
    """Contrato para acceder a asignaciones de roles por organización."""

    def fetch_manage_roles_by_org(self) -> ManageRolesByOrg:
        """Retorna todas las asignaciones de roles por organización."""

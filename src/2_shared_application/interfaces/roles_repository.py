"""Contrato de acceso a roles para la capa de aplicación."""

from __future__ import annotations

from typing import Protocol

from src.1_shared_domain.security_hierarchy import Roles


class RolesRepository(Protocol):
    """Contrato para acceder a roles desde cualquier fuente de datos."""

    def fetch_roles(self) -> Roles:
        """Retorna todos los roles disponibles."""

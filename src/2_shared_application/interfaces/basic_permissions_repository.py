"""Contrato de acceso a permisos básicos para la capa de aplicación."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.1_shared_domain.security_hierarchy import BasicPermissions


class BasicPermissionsRepository(Protocol):
    """Contrato para acceder a permisos básicos desde cualquier fuente."""

    def fetch_basic_permissions(self) -> BasicPermissions:
        """Retorna todos los permisos básicos disponibles."""

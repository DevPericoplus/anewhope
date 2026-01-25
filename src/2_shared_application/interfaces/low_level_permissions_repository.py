"""Contrato de acceso a permisos de bajo nivel para la capa de aplicación."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.1_shared_domain.security_hierarchy import LowLevelPermissions


class LowLevelPermissionsRepository(Protocol):
    """Contrato para acceder a permisos de bajo nivel desde cualquier fuente."""

    def fetch_low_level_permissions(self) -> LowLevelPermissions:
        """Retorna todos los permisos de bajo nivel disponibles."""

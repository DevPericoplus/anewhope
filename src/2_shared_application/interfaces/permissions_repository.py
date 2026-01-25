"""Contrato de acceso a permisos para la capa de aplicación."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.1_shared_domain.entities.domain_models import Permissions


class PermissionsRepository(Protocol):
    """Contrato para acceder a permisos desde cualquier fuente de datos."""

    def get_by_id(self, permission_id: int) -> Permissions | None:
        """Obtiene un permiso por su identificador."""

    def fetch_all(self) -> tuple[Permissions, ...]:
        """Retorna todos los permisos disponibles."""

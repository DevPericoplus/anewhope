"""Contrato de acceso a organizaciones para la capa de aplicación."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.1_shared_domain.entities.domain_models import Organization


class OrganizationRepository(Protocol):
    """Contrato para acceder a organizaciones desde cualquier fuente de datos."""

    def get_by_id(self, organization_id: int) -> Organization | None:
        """Obtiene una organización por su identificador."""

    def get_by_name(self, organization_name: str) -> Organization | None:
        """Obtiene una organización por su nombre."""

    def exists_by_name(self, organization_name: str) -> bool:
        """Verifica si existe una organización por nombre."""

    def save(self, organization: Organization) -> Organization:
        """Crea una organización y devuelve la entidad persistida."""

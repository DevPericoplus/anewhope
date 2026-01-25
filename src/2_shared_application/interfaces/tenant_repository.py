"""Contrato de acceso a tenants para la capa de aplicación."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.1_shared_domain.entities.domain_models import Tenant


class TenantRepository(Protocol):
    """Contrato para acceder a tenants desde cualquier fuente de datos."""

    def get_by_id(self, tenant_id: str) -> Tenant | None:
        """Obtiene un tenant por su identificador."""

    def fetch_all(self) -> tuple[Tenant, ...]:
        """Retorna todos los tenants disponibles."""

    def save(self, tenant: Tenant) -> Tenant:
        """Crea un tenant y devuelve la entidad persistida."""

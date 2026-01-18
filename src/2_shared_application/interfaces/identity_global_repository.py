"""Contrato de acceso a identidades globales para la capa de aplicación."""

from __future__ import annotations

from typing import Protocol

from src.1_shared_domain.entities.domain_models import IdentityGlobal


class IdentityGlobalRepository(Protocol):
    """Contrato para acceder a identidades globales desde cualquier fuente."""

    def get_by_id(self, identity_type_id: int) -> IdentityGlobal | None:
        """Obtiene una identidad global por su identificador."""

    def fetch_all(self) -> tuple[IdentityGlobal, ...]:
        """Retorna todas las identidades globales disponibles."""

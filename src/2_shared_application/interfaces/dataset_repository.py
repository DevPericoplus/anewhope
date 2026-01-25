"""Contrato de acceso a datasets para la capa de aplicación."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.1_shared_domain.entities.domain_models import Dataset


class DatasetRepository(Protocol):
    """Contrato para acceder a datasets desde cualquier fuente de datos."""

    def get_by_id(self, dataset_id: str) -> Dataset | None:
        """Obtiene un dataset por su identificador."""

    def fetch_all(self) -> tuple[Dataset, ...]:
        """Retorna todos los datasets disponibles."""

    def save(self, dataset: Dataset) -> Dataset:
        """Crea un dataset y devuelve la entidad persistida."""

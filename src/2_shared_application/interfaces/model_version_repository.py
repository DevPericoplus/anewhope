"""Contrato de acceso a versiones de modelos para la capa de aplicación."""

from __future__ import annotations

from typing import Protocol

from src.1_shared_domain.entities.domain_models import ModelVersion


class ModelVersionRepository(Protocol):
    """Contrato para acceder a versiones de modelos desde cualquier fuente."""

    def get_by_id(self, model_version_id: str) -> ModelVersion | None:
        """Obtiene una versión de modelo por su identificador."""

    def fetch_all(self) -> tuple[ModelVersion, ...]:
        """Retorna todas las versiones de modelos disponibles."""

    def save(self, model_version: ModelVersion) -> ModelVersion:
        """Crea una versión de modelo y devuelve la entidad persistida."""

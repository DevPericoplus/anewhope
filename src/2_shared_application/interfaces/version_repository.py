"""Contrato de acceso a versiones para la capa de aplicación."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.1_shared_domain.entities.version import Version, Versions


class VersionRepository(Protocol):
    """Contrato para acceder a versiones desde cualquier fuente de datos."""

    def get_by_id(self, version_id: int) -> Version | None:
        """Obtiene una versión por su identificador."""
        ...

    def get_by_project(self, project_id: int) -> Versions:
        """Obtiene todas las versiones de un proyecto."""
        ...

    def get_latest_by_project(self, project_id: int) -> Version | None:
        """Obtiene la versión más reciente de un proyecto."""
        ...

    def get_ready_for_training(self) -> Versions:
        """Obtiene todas las versiones listas para entrenar."""
        ...

    def exists(self, version_id: int) -> bool:
        """Verifica si existe una versión."""
        ...

    def save(self, version: Version) -> Version:
        """Crea o actualiza una versión."""
        ...

    def delete(self, version_id: int) -> bool:
        """Elimina una versión por su identificador."""
        ...

    def clone(
        self,
        source_version_id: int,
        new_version_name: str,
        created_by_user_id: int,
    ) -> Version | None:
        """Clona una versión existente con un nuevo nombre."""
        ...

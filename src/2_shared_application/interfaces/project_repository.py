"""Contrato de acceso a proyectos para la capa de aplicación."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.1_shared_domain.entities.project import Project, Projects


class ProjectRepository(Protocol):
    """Contrato para acceder a proyectos desde cualquier fuente de datos."""

    def get_by_id(self, project_id: int) -> Project | None:
        """Obtiene un proyecto por su identificador."""
        ...

    def get_by_organization(self, organization_id: int) -> Projects:
        """Obtiene todos los proyectos de una organización."""
        ...

    def get_by_user(self, user_id: int) -> Projects:
        """Obtiene todos los proyectos creados por un usuario."""
        ...

    def exists(self, project_id: int) -> bool:
        """Verifica si existe un proyecto."""
        ...

    def save(self, project: Project) -> Project:
        """Crea o actualiza un proyecto."""
        ...

    def delete(self, project_id: int) -> bool:
        """Elimina un proyecto por su identificador."""
        ...

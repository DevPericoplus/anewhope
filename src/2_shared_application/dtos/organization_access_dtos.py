"""DTOs para acceso filtrado a organizaciones y proyectos.

Usados por el ``OrganizationAccessService`` y los selectores del backoffice
para transportar información sobre qué organizaciones y proyectos puede
ver un usuario interno según sus asignaciones.
"""

from pydantic import BaseModel


class AccessibleOrganizationDto(BaseModel):
    """Organización accesible para un usuario interno."""

    organization_id: int
    organization_name: str


class AccessibleProjectDto(BaseModel):
    """Proyecto accesible para un usuario interno dentro de una organización."""

    project_id: int
    project_name: str


class AccessibleVersionDto(BaseModel):
    """Versión de un proyecto accesible."""

    version_id: int
    state_internal: str = ""
    created_at: str = ""

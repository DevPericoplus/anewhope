"""DTOs for Assignments Manager (Gestor de asignaciones)."""

from pydantic import BaseModel


class InternalUserDto(BaseModel):
    """DTO for internal users (filtered by training_create=true)."""
    user_id: int
    user_name: str
    user_email: str


class OrganizationAssignmentDto(BaseModel):
    """DTO for organization-level assignments."""
    id: int
    user_id: int
    user_name: str
    organization_id: int
    organization_name: str
    role_id: int
    role_name: str
    active: bool


class ProjectAssignmentDto(BaseModel):
    """DTO for project-level assignments."""
    id: int
    user_id: int
    user_name: str
    organization_id: int
    organization_name: str
    project_id: int
    project_name: str
    role_id: int
    role_name: str
    active: bool


class CreateOrgAssignmentDto(BaseModel):
    """Request DTO for creating organization assignment."""
    user_id: int
    organization_id: int
    role_id: int


class CreateProjectAssignmentDto(BaseModel):
    """Request DTO for creating project assignment."""
    user_id: int
    organization_id: int
    project_id: int
    role_id: int


class UpdateAssignmentDto(BaseModel):
    """Request DTO for updating assignment active status."""
    active: bool


class PrerequisiteValidationDto(BaseModel):
    """Response DTO for prerequisite validation."""
    valid: bool
    message: str
    has_org_role: bool
    org_role_id: int | None = None

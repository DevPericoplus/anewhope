"""DTOs para proyectos y versiones."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _load_project_entities() -> Any:
    """Carga las entidades de proyecto del dominio."""

    module_path = (
        Path(__file__).resolve().parents[2]
        / "1_shared_domain/entities/project.py"
    )
    module_name = "shared_domain_project_dtos"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar project.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_version_entities() -> Any:
    """Carga las entidades de versión del dominio."""

    module_path = (
        Path(__file__).resolve().parents[2]
        / "1_shared_domain/entities/version.py"
    )
    module_name = "shared_domain_version_dtos"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar version.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_project_entities = _load_project_entities()
_version_entities = _load_version_entities()

Project = _project_entities.Project
ProjectStatus = _project_entities.ProjectStatus
Version = _version_entities.Version
VersionStatus = _version_entities.VersionStatus


class ProjectDto(BaseModel):
    """DTO para proyectos."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    project_id: int
    organization_id: int
    project_name: str
    project_description: str = ""
    created_by_user_id: int
    status: str = "draft"
    created_at: str = ""
    updated_at: str = ""

    def to_domain(self) -> Project:
        """Convierte el DTO a entidad de dominio."""

        return Project(
            project_id=self.project_id,
            organization_id=self.organization_id,
            project_name=self.project_name,
            project_description=self.project_description,
            created_by_user_id=self.created_by_user_id,
            status=ProjectStatus(self.status),
            created_at=self.created_at or _now_iso(),
            updated_at=self.updated_at or _now_iso(),
        )

    @classmethod
    def from_domain(cls, project: Project) -> "ProjectDto":
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            project_id=project.project_id,
            organization_id=project.organization_id,
            project_name=project.project_name,
            project_description=project.project_description,
            created_by_user_id=project.created_by_user_id,
            status=project.status.value,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class ProjectCreateDto(BaseModel):
    """DTO para crear un proyecto."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    organization_id: int
    project_name: str
    project_description: str = ""
    created_by_user_id: int


class ProjectUpdateDto(BaseModel):
    """DTO para actualizar un proyecto."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    project_name: str | None = None
    project_description: str | None = None
    status: str | None = None


class VersionDto(BaseModel):
    """DTO para versiones de proyecto."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    version_id: int
    project_id: int
    version_name: str
    version_description: str = ""
    status: str = "draft"
    created_by_user_id: int
    approved_by_client_user_id: int | None = None
    approved_by_myllm_user_id: int | None = None
    storage_path: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_domain(self) -> Version:
        """Convierte el DTO a entidad de dominio."""

        return Version(
            version_id=self.version_id,
            project_id=self.project_id,
            version_name=self.version_name,
            version_description=self.version_description,
            status=VersionStatus(self.status),
            created_by_user_id=self.created_by_user_id,
            approved_by_client_user_id=self.approved_by_client_user_id,
            approved_by_myllm_user_id=self.approved_by_myllm_user_id,
            storage_path=self.storage_path,
            created_at=self.created_at or _now_iso(),
            updated_at=self.updated_at or _now_iso(),
        )

    @classmethod
    def from_domain(cls, version: Version) -> "VersionDto":
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            version_id=version.version_id,
            project_id=version.project_id,
            version_name=version.version_name,
            version_description=version.version_description,
            status=version.status.value,
            created_by_user_id=version.created_by_user_id,
            approved_by_client_user_id=version.approved_by_client_user_id,
            approved_by_myllm_user_id=version.approved_by_myllm_user_id,
            storage_path=version.storage_path,
            created_at=version.created_at,
            updated_at=version.updated_at,
        )


class VersionCreateDto(BaseModel):
    """DTO para crear una versión."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    project_id: int
    version_name: str
    version_description: str = ""
    created_by_user_id: int


class VersionUpdateDto(BaseModel):
    """DTO para actualizar una versión."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    version_description: str | None = None
    status: str | None = None
    approved_by_client_user_id: int | None = None
    approved_by_myllm_user_id: int | None = None


def _now_iso() -> str:
    """Retorna la fecha/hora actual en formato ISO."""
    from datetime import timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

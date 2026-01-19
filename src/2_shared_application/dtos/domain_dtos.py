"""DTOs de dominio para intercambio de datos entre capas."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import importlib.util
import sys

from pydantic import BaseModel, ConfigDict, Field


def _load_domain_models() -> Any:
    """Carga el módulo de modelos de dominio sin import directo."""

    module_path = (
        Path(__file__).resolve().parents[2]
        / "1_shared_domain/entities/domain_models.py"
    )
    module_name = "shared_domain_models"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar domain_models.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_domain_models = _load_domain_models()
Dataset = _domain_models.Dataset
IdentityGlobal = _domain_models.IdentityGlobal
ModelLifecycleState = _domain_models.ModelLifecycleState
ModelVersion = _domain_models.ModelVersion
Organization = _domain_models.Organization
Permissions = _domain_models.Permissions
Tenant = _domain_models.Tenant
User = _domain_models.User


class OrganizationDto(BaseModel):
    """DTO para Organization."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    organization_id: int
    organization_name: str
    organization_email: str
    organization_tlf: str
    organization_address: str
    organization_country: str
    organization_state: str

    def to_domain(self) -> Organization:
        """Convierte el DTO a entidad de dominio."""

        return Organization(
            organization_id=self.organization_id,
            organization_name=self.organization_name,
            organization_email=self.organization_email,
            organization_tlf=self.organization_tlf,
            organization_address=self.organization_address,
            organization_country=self.organization_country,
            organization_state=self.organization_state,
        )

    @classmethod
    def from_domain(cls, organization: Organization) -> OrganizationDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            organization_id=organization.organization_id,
            organization_name=organization.organization_name,
            organization_email=organization.organization_email,
            organization_tlf=organization.organization_tlf,
            organization_address=organization.organization_address,
            organization_country=organization.organization_country,
            organization_state=organization.organization_state,
        )


class PermissionsDto(BaseModel):
    """DTO para Permissions."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    id_permission: int
    permission_name: str
    permission_description: str
    enable: bool = True
    create: bool = False
    delete: bool = False
    read: bool = False
    write: bool = False
    execute: bool = False
    log: bool = False
    expired: datetime | None = None

    def to_domain(self) -> Permissions:
        """Convierte el DTO a entidad de dominio."""

        return Permissions(
            id_permission=self.id_permission,
            permission_name=self.permission_name,
            permission_description=self.permission_description,
            enable=self.enable,
            create=self.create,
            delete=self.delete,
            read=self.read,
            write=self.write,
            execute=self.execute,
            log=self.log,
            expired=self.expired,
        )

    @classmethod
    def from_domain(cls, permission: Permissions) -> PermissionsDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            id_permission=permission.id_permission,
            permission_name=permission.permission_name,
            permission_description=permission.permission_description,
            enable=permission.enable,
            create=permission.create,
            delete=permission.delete,
            read=permission.read,
            write=permission.write,
            execute=permission.execute,
            log=permission.log,
            expired=permission.expired,
        )


class IdentityGlobalDto(BaseModel):
    """DTO para IdentityGlobal."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    identity_type_id: int
    identity_type_name: str
    identity_type_rol: str
    identity_type_group_permissions: list[PermissionsDto] = Field(
        default_factory=list
    )

    def to_domain(self) -> IdentityGlobal:
        """Convierte el DTO a entidad de dominio."""

        permissions = [perm.to_domain() for perm in self.identity_type_group_permissions]
        return IdentityGlobal(
            identity_type_id=self.identity_type_id,
            identity_type_name=self.identity_type_name,
            identity_type_rol=self.identity_type_rol,
            identity_type_group_permissions=permissions,
        )

    @classmethod
    def from_domain(cls, identity: IdentityGlobal) -> IdentityGlobalDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            identity_type_id=identity.identity_type_id,
            identity_type_name=identity.identity_type_name,
            identity_type_rol=identity.identity_type_rol,
            identity_type_group_permissions=[
                PermissionsDto.from_domain(permission)
                for permission in identity.identity_type_group_permissions
            ],
        )


class TenantDto(BaseModel):
    """DTO para Tenant."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    id: str
    name: str
    contact_email: str

    def to_domain(self) -> Tenant:
        """Convierte el DTO a entidad de dominio."""

        return Tenant(id=self.id, name=self.name, contact_email=self.contact_email)

    @classmethod
    def from_domain(cls, tenant: Tenant) -> TenantDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(id=tenant.id, name=tenant.name, contact_email=tenant.contact_email)


class DatasetDto(BaseModel):
    """DTO para Dataset."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    id: str
    tenant_id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None

    def to_domain(self) -> Dataset:
        """Convierte el DTO a entidad de dominio."""

        return Dataset(
            id=self.id,
            tenant_id=self.tenant_id,
            name=self.name,
            description=self.description,
            tags=self.tags,
            created_at=self.created_at or datetime.now(timezone.utc),
        )

    @classmethod
    def from_domain(cls, dataset: Dataset) -> DatasetDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            id=dataset.id,
            tenant_id=dataset.tenant_id,
            name=dataset.name,
            description=dataset.description,
            tags=dataset.tags,
            created_at=dataset.created_at,
        )


class ModelVersionDto(BaseModel):
    """DTO para ModelVersion."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    id: str
    model_name: str
    tenant_id: str
    lifecycle_state: ModelLifecycleState
    source_dataset_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metrics: dict[str, float] = Field(default_factory=dict)

    def to_domain(self) -> ModelVersion:
        """Convierte el DTO a entidad de dominio."""

        return ModelVersion(
            id=self.id,
            model_name=self.model_name,
            tenant_id=self.tenant_id,
            lifecycle_state=self.lifecycle_state,
            source_dataset_id=self.source_dataset_id,
            created_at=self.created_at or datetime.now(timezone.utc),
            updated_at=self.updated_at or datetime.now(timezone.utc),
            metrics=self.metrics,
        )

    @classmethod
    def from_domain(cls, model_version: ModelVersion) -> ModelVersionDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            id=model_version.id,
            model_name=model_version.model_name,
            tenant_id=model_version.tenant_id,
            lifecycle_state=model_version.lifecycle_state,
            source_dataset_id=model_version.source_dataset_id,
            created_at=model_version.created_at,
            updated_at=model_version.updated_at,
            metrics=model_version.metrics,
        )


class UserDto(BaseModel):
    """DTO para User."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    user_id: int
    organization_id: int
    identity_type_id: int
    user_name: str
    user_password: str
    user_email: str
    user_mobile: str
    user_otp: str
    active: bool = True
    blocked: bool = False
    contact_info: dict[str, Any] = Field(default_factory=dict)
    billing_info: dict[str, Any] = Field(default_factory=dict)

    def to_domain(self) -> User:
        """Convierte el DTO a entidad de dominio."""

        return User(
            user_id=self.user_id,
            organization_id=self.organization_id,
            identity_type_id=self.identity_type_id,
            user_name=self.user_name,
            password=self.user_password,
            email=self.user_email,
            mobile=self.user_mobile,
            otp=self.user_otp,
            active=self.active,
            blocked=self.blocked,
        )

    @classmethod
    def from_domain(cls, user: User) -> UserDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            user_id=user.id,
            organization_id=user.id_org,
            identity_type_id=user.id_type,
            user_name=user.user_name,
            user_password=user.user_password,
            user_email=user.user_email,
            user_mobile=user.user_mobile,
            user_otp=user.user_otp,
            active=user.active,
            blocked=user.blocked,
        )

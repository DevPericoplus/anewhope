"""DTOs de seguridad para roles y permisos básicos."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import importlib.util
import sys

from pydantic import BaseModel, ConfigDict, Field


def _load_security_models() -> Any:
    """Carga el módulo de jerarquía de seguridad sin import directo."""

    module_path = (
        Path(__file__).resolve().parents[2] / "1_shared_domain/security_hierarchy.py"
    )
    module_name = "shared_security_models"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar security_hierarchy.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_security_models = _load_security_models()
BasicPermission = _security_models.BasicPermission
LowLevelPermission = _security_models.LowLevelPermission
ManagedRoleByOrg = _security_models.ManagedRoleByOrg
Role = _security_models.Role


class RoleDto(BaseModel):
    """DTO para roles básicos."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    identity_type_id: int
    identity_type_name: str
    identity_type_rol: str
    identity_type_group_permissions: list[int] = Field(default_factory=list)

    def to_domain(self) -> Role:
        """Convierte el DTO a entidad de dominio."""

        return Role(
            identity_type_id=self.identity_type_id,
            identity_type_name=self.identity_type_name,
            identity_type_rol=self.identity_type_rol,
            identity_type_group_permissions=tuple(self.identity_type_group_permissions),
        )

    @classmethod
    def from_domain(cls, role: Role) -> RoleDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            identity_type_id=role.identity_type_id,
            identity_type_name=role.identity_type_name,
            identity_type_rol=role.identity_type_rol,
            identity_type_group_permissions=list(role.identity_type_group_permissions),
        )


class BasicPermissionDto(BaseModel):
    """DTO para permisos básicos."""

    model_config = ConfigDict(
        extra="ignore", validate_assignment=True, populate_by_name=True
    )

    id: int
    permission_name: str = Field(alias="PermissionName")
    permission_description: str = Field(alias="PermissionDescription")

    def to_domain(self) -> BasicPermission:
        """Convierte el DTO a entidad de dominio."""

        return BasicPermission(
            permission_id=self.id,
            permission_name=self.permission_name,
            permission_description=self.permission_description,
        )

    @classmethod
    def from_domain(cls, permission: BasicPermission) -> BasicPermissionDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            id=permission.permission_id,
            permission_name=permission.permission_name,
            permission_description=permission.permission_description,
        )


class LowLevelPermissionDto(BaseModel):
    """DTO para permisos de bajo nivel."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    id_permissions: int
    folder_create: bool
    folder_delete: bool
    folder_rename: bool
    folder_read: bool
    file_create: bool
    file_read: bool
    file_update: bool
    file_delete: bool
    project_create: bool
    project_read: bool
    project_update: bool
    project_delete: bool
    version_create: bool
    version_read: bool
    version_update: bool
    version_delete: bool
    training_create: bool
    training_read: bool
    training_update: bool
    training_delete: bool
    training_start: bool
    training_stop: bool
    parameters_create: bool
    parameters_read: bool
    parameters_update: bool
    parameters_delete: bool
    notifications_create: bool
    notifications_read: bool
    notifications_update: bool
    notifications_delete: bool
    user_create: bool
    user_read: bool
    user_update: bool
    user_delete: bool
    user_enable: bool
    user_disable: bool
    folder_list: bool
    file_list: bool
    project_list: bool
    version_list: bool

    def to_domain(self) -> LowLevelPermission:
        """Convierte el DTO a entidad de dominio."""

        return LowLevelPermission(
            id_permissions=self.id_permissions,
            folder_create=self.folder_create,
            folder_delete=self.folder_delete,
            folder_rename=self.folder_rename,
            folder_read=self.folder_read,
            file_create=self.file_create,
            file_read=self.file_read,
            file_update=self.file_update,
            file_delete=self.file_delete,
            project_create=self.project_create,
            project_read=self.project_read,
            project_update=self.project_update,
            project_delete=self.project_delete,
            version_create=self.version_create,
            version_read=self.version_read,
            version_update=self.version_update,
            version_delete=self.version_delete,
            training_create=self.training_create,
            training_read=self.training_read,
            training_update=self.training_update,
            training_delete=self.training_delete,
            training_start=self.training_start,
            training_stop=self.training_stop,
            parameters_create=self.parameters_create,
            parameters_read=self.parameters_read,
            parameters_update=self.parameters_update,
            parameters_delete=self.parameters_delete,
            notifications_create=self.notifications_create,
            notifications_read=self.notifications_read,
            notifications_update=self.notifications_update,
            notifications_delete=self.notifications_delete,
            user_create=self.user_create,
            user_read=self.user_read,
            user_update=self.user_update,
            user_delete=self.user_delete,
            user_enable=self.user_enable,
            user_disable=self.user_disable,
            folder_list=self.folder_list,
            file_list=self.file_list,
            project_list=self.project_list,
            version_list=self.version_list,
        )

    @classmethod
    def from_domain(
        cls, permission: LowLevelPermission
    ) -> "LowLevelPermissionDto":
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            id_permissions=permission.id_permissions,
            folder_create=permission.folder_create,
            folder_delete=permission.folder_delete,
            folder_rename=permission.folder_rename,
            folder_read=permission.folder_read,
            file_create=permission.file_create,
            file_read=permission.file_read,
            file_update=permission.file_update,
            file_delete=permission.file_delete,
            project_create=permission.project_create,
            project_read=permission.project_read,
            project_update=permission.project_update,
            project_delete=permission.project_delete,
            version_create=permission.version_create,
            version_read=permission.version_read,
            version_update=permission.version_update,
            version_delete=permission.version_delete,
            training_create=permission.training_create,
            training_read=permission.training_read,
            training_update=permission.training_update,
            training_delete=permission.training_delete,
            training_start=permission.training_start,
            training_stop=permission.training_stop,
            parameters_create=permission.parameters_create,
            parameters_read=permission.parameters_read,
            parameters_update=permission.parameters_update,
            parameters_delete=permission.parameters_delete,
            notifications_create=permission.notifications_create,
            notifications_read=permission.notifications_read,
            notifications_update=permission.notifications_update,
            notifications_delete=permission.notifications_delete,
            user_create=permission.user_create,
            user_read=permission.user_read,
            user_update=permission.user_update,
            user_delete=permission.user_delete,
            user_enable=permission.user_enable,
            user_disable=permission.user_disable,
            folder_list=permission.folder_list,
            file_list=permission.file_list,
            project_list=permission.project_list,
            version_list=permission.version_list,
        )


class ManageRoleByOrgDto(BaseModel):
    """DTO para asignación de roles por organización."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    id_user: int
    id_organization: int
    identity_type_id: int
    create_date: str
    modification_date: str
    id_modifier_user: int
    active: bool

    def to_domain(self) -> ManagedRoleByOrg:
        """Convierte el DTO a entidad de dominio."""

        return ManagedRoleByOrg(
            user_id=self.id_user,
            organization_id=self.id_organization,
            identity_type_id=self.identity_type_id,
            create_date=self.create_date,
            modification_date=self.modification_date,
            modifier_user_id=self.id_modifier_user,
            active=self.active,
        )

    @classmethod
    def from_domain(cls, managed_role: ManagedRoleByOrg) -> ManageRoleByOrgDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            id_user=managed_role.user_id,
            id_organization=managed_role.organization_id,
            identity_type_id=managed_role.identity_type_id,
            create_date=managed_role.create_date,
            modification_date=managed_role.modification_date,
            id_modifier_user=managed_role.modifier_user_id,
            active=managed_role.active,
        )

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
            identity_type_group_permissions=self.identity_type_group_permissions,
        )

    @classmethod
    def from_domain(cls, role: Role) -> RoleDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            identity_type_id=role.identity_type_id,
            identity_type_name=role.identity_type_name,
            identity_type_rol=role.identity_type_rol,
            identity_type_group_permissions=role.identity_type_group_permissions,
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
            id=self.id,
            PermissionName=self.permission_name,
            PermissionDescription=self.permission_description,
        )

    @classmethod
    def from_domain(cls, permission: BasicPermission) -> BasicPermissionDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            id=permission.id,
            permission_name=permission.PermissionName,
            permission_description=permission.PermissionDescription,
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
            id_user=self.id_user,
            id_organization=self.id_organization,
            identity_type_id=self.identity_type_id,
            create_date=self.create_date,
            modification_date=self.modification_date,
            id_modifier_user=self.id_modifier_user,
            active=self.active,
        )

    @classmethod
    def from_domain(cls, managed_role: ManagedRoleByOrg) -> ManageRoleByOrgDto:
        """Crea un DTO desde una entidad de dominio."""

        return cls(
            id_user=managed_role.id_user,
            id_organization=managed_role.id_organization,
            identity_type_id=managed_role.identity_type_id,
            create_date=managed_role.create_date,
            modification_date=managed_role.modification_date,
            id_modifier_user=managed_role.id_modifier_user,
            active=managed_role.active,
        )

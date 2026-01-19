"""Tests de DTOs de seguridad."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def _load_module(module_path: Path, module_name: str) -> Any:
    """Carga un módulo desde ruta absoluta."""

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el módulo {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_ROOT_PATH = Path(__file__).resolve().parents[2]
_security_dtos = _load_module(
    _ROOT_PATH / "2_shared_application/dtos/security_dtos.py",
    "shared_security_dtos_tests",
)

BasicPermissionDto = _security_dtos.BasicPermissionDto
BasicPermission = _security_dtos.BasicPermission
ManageRoleByOrgDto = _security_dtos.ManageRoleByOrgDto
ManagedRoleByOrg = _security_dtos.ManagedRoleByOrg


def test_basic_permission_dto_to_domain_maps_fields() -> None:
    """Verifica el mapeo correcto de DTO a dominio."""

    dto = BasicPermissionDto.model_validate(
        {
            "id": 10,
            "PermissionName": "read_users",
            "PermissionDescription": "Permite leer usuarios",
        }
    )

    domain = dto.to_domain()

    assert isinstance(domain, BasicPermission)
    assert domain.permission_id == 10
    assert domain.permission_name == "read_users"
    assert domain.permission_description == "Permite leer usuarios"


def test_basic_permission_dto_from_domain_maps_fields() -> None:
    """Verifica el mapeo correcto de dominio a DTO."""

    domain = BasicPermission(
        permission_id=20,
        permission_name="write_users",
        permission_description="Permite editar usuarios",
    )

    dto = BasicPermissionDto.from_domain(domain)

    assert dto.id == 20
    assert dto.permission_name == "write_users"
    assert dto.permission_description == "Permite editar usuarios"


def test_manage_role_by_org_dto_to_domain_maps_fields() -> None:
    """Verifica el mapeo correcto de DTO a dominio."""

    dto = ManageRoleByOrgDto.model_validate(
        {
            "id_user": 3,
            "id_organization": 7,
            "identity_type_id": 2,
            "create_date": "2026-01-19",
            "modification_date": "",
            "id_modifier_user": 99,
            "active": True,
        }
    )

    domain = dto.to_domain()

    assert isinstance(domain, ManagedRoleByOrg)
    assert domain.user_id == 3
    assert domain.organization_id == 7
    assert domain.identity_type_id == 2
    assert domain.create_date == "2026-01-19"
    assert domain.modification_date == ""
    assert domain.modifier_user_id == 99
    assert domain.active is True


def test_manage_role_by_org_dto_from_domain_maps_fields() -> None:
    """Verifica el mapeo correcto de dominio a DTO."""

    domain = ManagedRoleByOrg(
        user_id=4,
        organization_id=8,
        identity_type_id=5,
        create_date="2026-01-20",
        modification_date="2026-01-21",
        modifier_user_id=77,
        active=False,
    )

    dto = ManageRoleByOrgDto.from_domain(domain)

    assert dto.id_user == 4
    assert dto.id_organization == 8
    assert dto.identity_type_id == 5
    assert dto.create_date == "2026-01-20"
    assert dto.modification_date == "2026-01-21"
    assert dto.id_modifier_user == 77
    assert dto.active is False

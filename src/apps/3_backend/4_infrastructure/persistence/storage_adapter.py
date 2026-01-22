"""Adaptadores de persistencia para backend core."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any


class StorageAdapterError(Exception):
    """Error al interactuar con la persistencia."""
def load_mariadb_settings() -> dict[str, Any]:
    """Carga configuración de MariaDB desde entorno o protected_values."""

    try:
        from protected_values import (  # type: ignore
            mariadb_host,
            mariadb_port,
            mariadb_core_database,
            mariadb_ai_database,
            mariadb_admin_user,
            mariadb_admin_password,
            mariadb_writer_user,
            mariadb_writer_password,
            mariadb_reader_user,
            mariadb_reader_password,
            mariadb_root_user,
            mariadb_root_password,
            mariadb_admin_dsn,
            mariadb_writer_dsn,
            mariadb_reader_dsn,
            mariadb_root_dsn,
        )
    except Exception as exc:
        raise StorageAdapterError(
            "No se pudo cargar la configuración de MariaDB desde protected_values"
        ) from exc

    return {
        "host": os.environ.get("MARIADB_HOST", mariadb_host),
        "port": int(os.environ.get("MARIADB_PORT", mariadb_port)),
        "core_database": os.environ.get(
            "MARIADB_CORE_DATABASE", mariadb_core_database
        ),
        "projects_database": os.environ.get(
            "MARIADB_PROJECTS_DATABASE", mariadb_ai_database
        ),
        "admin_user": os.environ.get("MARIADB_ADMIN_USER", mariadb_admin_user),
        "admin_password": os.environ.get(
            "MARIADB_ADMIN_PASSWORD", mariadb_admin_password
        ),
        "writer_user": os.environ.get("MARIADB_WRITER_USER", mariadb_writer_user),
        "writer_password": os.environ.get(
            "MARIADB_WRITER_PASSWORD", mariadb_writer_password
        ),
        "reader_user": os.environ.get("MARIADB_READER_USER", mariadb_reader_user),
        "reader_password": os.environ.get(
            "MARIADB_READER_PASSWORD", mariadb_reader_password
        ),
        "root_user": os.environ.get("MARIADB_ROOT_USER", mariadb_root_user),
        "root_password": os.environ.get(
            "MARIADB_ROOT_PASSWORD", mariadb_root_password
        ),
        "admin_dsn": os.environ.get("MARIADB_ADMIN_DSN", mariadb_admin_dsn),
        "writer_dsn": os.environ.get("MARIADB_WRITER_DSN", mariadb_writer_dsn),
        "reader_dsn": os.environ.get("MARIADB_READER_DSN", mariadb_reader_dsn),
        "root_dsn": os.environ.get("MARIADB_ROOT_DSN", mariadb_root_dsn),
    }



def _load_dto_module(module_name: str, filename: str) -> Any:
    """Carga un módulo de DTOs desde el paquete compartido."""

    module_path = (
        Path(__file__).resolve().parents[5]
        / "src/2_shared_application/dtos"
        / filename
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise StorageAdapterError(
            "No se pudo cargar el módulo de DTOs compartidos"
        )
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_domain_dtos = _load_dto_module("shared_domain_dtos_core", "domain_dtos.py")
_security_dtos = _load_dto_module("shared_security_dtos_core", "security_dtos.py")

OrganizationDto = _domain_dtos.OrganizationDto
UserDto = _domain_dtos.UserDto
RoleDto = _security_dtos.RoleDto
BasicPermissionDto = _security_dtos.BasicPermissionDto
LowLevelPermissionDto = _security_dtos.LowLevelPermissionDto
ManageRoleByOrgDto = _security_dtos.ManageRoleByOrgDto


class JsonMockStorageAdapter:
    """Persistencia basada en ficheros JSON."""

    def __init__(
        self,
        users_path: Path,
        organizations_path: Path,
        roles_path: Path,
        basic_permissions_path: Path,
        low_level_permissions_path: Path,
        manage_roles_path: Path,
    ) -> None:
        self._users_path = users_path
        self._organizations_path = organizations_path
        self._roles_path = roles_path
        self._basic_permissions_path = basic_permissions_path
        self._low_level_permissions_path = low_level_permissions_path
        self._manage_roles_path = manage_roles_path

    def load_users(self) -> list[UserDto]:
        """Carga usuarios desde JSON."""

        records = _load_json_list(self._users_path)
        return [UserDto.model_validate(record) for record in records]

    def store_users(self, users: list[UserDto]) -> None:
        """Guarda usuarios en JSON."""

        _write_json_list(self._users_path, [user.model_dump() for user in users])

    def load_organizations(self) -> list[OrganizationDto]:
        """Carga organizaciones desde JSON."""

        records = _load_json_list(self._organizations_path)
        return [OrganizationDto.model_validate(record) for record in records]

    def store_organizations(self, organizations: list[OrganizationDto]) -> None:
        """Guarda organizaciones en JSON."""

        _write_json_list(
            self._organizations_path, [org.model_dump() for org in organizations]
        )

    def load_roles(self) -> list[RoleDto]:
        """Carga roles desde JSON."""

        records = _load_json_list(self._roles_path)
        return [RoleDto.model_validate(record) for record in records]

    def load_basic_permissions(self) -> list[BasicPermissionDto]:
        """Carga permisos básicos desde JSON."""

        records = _load_json_list(self._basic_permissions_path)
        return [BasicPermissionDto.model_validate(record) for record in records]

    def load_low_level_permissions(self) -> list[LowLevelPermissionDto]:
        """Carga permisos de bajo nivel desde JSON."""

        records = _load_json_list(self._low_level_permissions_path)
        return [LowLevelPermissionDto.model_validate(record) for record in records]

    def store_low_level_permissions(
        self, permissions: list[LowLevelPermissionDto]
    ) -> None:
        """Guarda permisos de bajo nivel en JSON."""

        _write_json_list(
            self._low_level_permissions_path,
            [permission.model_dump() for permission in permissions],
        )

    def load_manage_roles(self) -> list[ManageRoleByOrgDto]:
        """Carga roles por organización desde JSON."""

        records = _load_json_list(self._manage_roles_path)
        return [ManageRoleByOrgDto.model_validate(record) for record in records]

    def store_manage_roles(self, entries: list[ManageRoleByOrgDto]) -> None:
        """Guarda roles por organización en JSON."""

        _write_json_list(
            self._manage_roles_path, [entry.model_dump() for entry in entries]
        )


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    """Lee un JSON tipo lista de forma segura."""

    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
    except json.JSONDecodeError as exc:
        raise StorageAdapterError("El archivo JSON no es válido") from exc
    if not isinstance(data, list):
        raise StorageAdapterError("El JSON debe contener una lista")
    return data


def _write_json_list(path: Path, payload: list[dict[str, Any]]) -> None:
    """Escribe un JSON tipo lista de forma segura."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)

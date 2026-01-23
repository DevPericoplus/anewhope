"""Adaptadores de persistencia para backend core."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from src.2_shared_application.storage_access_structure import (
    get_folder_by_id_organization,
    get_folder_by_id_project,
)


class StorageAdapterError(Exception):
    """Error al interactuar con la persistencia."""


@dataclass(frozen=True, slots=True)
class FmanagementSettings:
    """Configuración para la API externa de file management."""

    base_url: str
    base_path: str
    permissions_source: str


def load_fmanagement_settings() -> FmanagementSettings:
    """Carga configuración de fmanagement desde entorno."""

    base_url = os.environ.get("FMANAGEMENT_BASE_URL", "http://localhost:1666")
    base_path = os.environ.get("FMANAGEMENT_BASE_PATH", "/data/files/external")
    permissions_source = os.environ.get("FMANAGEMENT_PERMISSIONS_SOURCE", "mock")
    return FmanagementSettings(
        base_url=base_url.rstrip("/"),
        base_path=base_path,
        permissions_source=permissions_source,
    )


def build_storage_paths(
    id_organization: int, id_project: int, version_path: str, subfolders: str = ""
) -> dict[str, str]:
    """Construye rutas para operaciones de ficheros a partir de IDs."""

    return {
        "orgpath": get_folder_by_id_organization(id_organization),
        "prjpath": get_folder_by_id_project(id_project),
        "versionpath": version_path,
        "subfolders": subfolders,
    }
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
            mariadb_cli_path,
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
        "cli_path": os.environ.get("MARIADB_CLI_PATH", mariadb_cli_path),
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

        if _should_read_users_from_db():
            records = _load_users_from_mariadb()
        else:
            records = _load_json_list(self._users_path)
        return [UserDto.model_validate(record) for record in records]

    def store_users(self, users: list[UserDto]) -> None:
        """Guarda usuarios en JSON."""

        _write_json_list(self._users_path, [user.model_dump() for user in users])
        if _should_sync_users_to_db():
            _sync_users_to_mariadb(users)

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


def _should_sync_users_to_db() -> bool:
    """Determina si se debe sincronizar users hacia MariaDB."""

    try:
        from protected_values import storage_mode  # type: ignore
    except Exception:
        storage_mode = "mock"
    mode = os.environ.get("STORAGE_MODE", str(storage_mode))
    return mode in {"mock_and_db", "db_only"}


def _should_read_users_from_db() -> bool:
    """Determina si se deben leer usuarios desde MariaDB."""

    try:
        from protected_values import storage_mode  # type: ignore
    except Exception:
        storage_mode = "mock"
    mode = os.environ.get("STORAGE_MODE", str(storage_mode))
    return mode == "db_only"


def _load_users_from_mariadb() -> list[dict[str, Any]]:
    """Carga usuarios desde MariaDB (users + contact/billing)."""

    settings = load_mariadb_settings()
    cli_path = settings["cli_path"]
    db_name = settings["core_database"]
    db_user = settings["reader_user"]
    db_password = settings["reader_password"]
    if not cli_path or not db_user:
        raise StorageAdapterError("Faltan credenciales de lectura para MariaDB")

    query = (
        "SELECT u.user_id, u.organization_id, u.identity_type_id, u.user_name, "
        "u.user_password, u.user_email, u.user_mobile, u.user_otp, u.active, u.blocked, "
        "c.first_name, c.sur_name, c.country, c.state, c.zip_code, c.address, "
        "b.first_name, b.sur_name, b.country, b.state, b.zip_code, b.address "
        "FROM users u "
        "LEFT JOIN user_contact_info c ON c.user_id = u.user_id "
        "LEFT JOIN user_billing_info b ON b.user_id = u.user_id "
        "ORDER BY u.user_id"
    )
    cmd = [
        cli_path,
        "-u",
        db_user,
        f"-p{db_password}",
        "--database",
        db_name,
        "-N",
        "-B",
        "-e",
        query,
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise StorageAdapterError(
            f"No se pudo leer usuarios desde MariaDB: {exc}"
        ) from exc
    records: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        row = line.split("\t")
        records.append(
            {
                "user_id": int(row[0]),
                "organization_id": int(row[1]),
                "identity_type_id": int(row[2]),
                "user_name": row[3] or "",
                "user_password": row[4] or "",
                "user_email": row[5] or "",
                "user_mobile": row[6] or "",
                "user_otp": row[7] or "",
                "active": bool(int(row[8])) if row[8] is not None else False,
                "blocked": bool(int(row[9])) if row[9] is not None else False,
                "contact_info": {
                    "first_name": row[10] or "",
                    "sur_name": row[11] or "",
                    "country": row[12] or "",
                    "state": row[13] or "",
                    "zip_code": row[14] or "",
                    "address": row[15] or "",
                },
                "billing_info": {
                    "first_name": row[16] or "",
                    "sur_name": row[17] or "",
                    "country": row[18] or "",
                    "state": row[19] or "",
                    "zip_code": row[20] or "",
                    "address": row[21] or "",
                },
            }
        )
    return records


def _sync_users_to_mariadb(users: list[UserDto]) -> None:
    """Sincroniza usuarios en MariaDB (tabla users y datos asociados)."""

    settings = load_mariadb_settings()
    cli_path = settings["cli_path"]
    db_name = settings["core_database"]
    db_user = settings["writer_user"]
    db_password = settings["writer_password"]
    if not cli_path or not db_user:
        raise StorageAdapterError("Faltan credenciales para MariaDB")

    def sql_escape(value: str) -> str:
        return value.replace("\\\\", "\\\\\\\\").replace("'", "''")

    for user in users:
        payload = user.model_dump()
        cmd = [
            cli_path,
            "-u",
            db_user,
            f"-p{db_password}",
            "--database",
            db_name,
            "-e",
            _build_user_upsert_sql(payload, sql_escape),
        ]
        subprocess.run(cmd, check=True)


def _build_user_upsert_sql(payload: dict[str, Any], escape: Any) -> str:
    """Construye SQL de upsert para users y tablas asociadas."""

    user_id = int(payload.get("user_id", 0))
    org_id = int(payload.get("organization_id", 0))
    identity_id = int(payload.get("identity_type_id", 0))
    user_name = escape(str(payload.get("user_name", "")))
    user_password = escape(str(payload.get("user_password", "")))
    user_email = escape(str(payload.get("user_email", "")))
    user_mobile = escape(str(payload.get("user_mobile", "")))
    user_otp = escape(str(payload.get("user_otp", "")))
    active = 1 if payload.get("active") else 0
    blocked = 1 if payload.get("blocked") else 0
    contact = payload.get("contact_info") or {}
    billing = payload.get("billing_info") or {}

    contact_first = escape(str(contact.get("first_name", "")))
    contact_sur = escape(str(contact.get("sur_name", "")))
    contact_country = escape(str(contact.get("country", "")))
    contact_state = escape(str(contact.get("state", "")))
    contact_zip = escape(str(contact.get("zip_code", "")))
    contact_address = escape(str(contact.get("address", "")))

    billing_first = escape(str(billing.get("first_name", "")))
    billing_sur = escape(str(billing.get("sur_name", "")))
    billing_country = escape(str(billing.get("country", "")))
    billing_state = escape(str(billing.get("state", "")))
    billing_zip = escape(str(billing.get("zip_code", "")))
    billing_address = escape(str(billing.get("address", "")))

    return (
        "INSERT INTO users (user_id, organization_id, identity_type_id, user_name, "
        "user_password, user_email, user_mobile, user_otp, active, blocked) VALUES "
        f"({user_id}, {org_id}, {identity_id}, '{user_name}', '{user_password}', "
        f\"'{user_email}', '{user_mobile}', '{user_otp}', {active}, {blocked}) "
        "ON DUPLICATE KEY UPDATE organization_id=VALUES(organization_id), "
        "identity_type_id=VALUES(identity_type_id), user_name=VALUES(user_name), "
        "user_password=VALUES(user_password), user_email=VALUES(user_email), "
        "user_mobile=VALUES(user_mobile), user_otp=VALUES(user_otp), "
        "active=VALUES(active), blocked=VALUES(blocked); "
        "INSERT INTO user_contact_info (user_id, first_name, sur_name, country, state, "
        "zip_code, address) VALUES "
        f\"({user_id}, '{contact_first}', '{contact_sur}', '{contact_country}', "
        f\"'{contact_state}', '{contact_zip}', '{contact_address}') "
        "ON DUPLICATE KEY UPDATE first_name=VALUES(first_name), sur_name=VALUES(sur_name), "
        "country=VALUES(country), state=VALUES(state), zip_code=VALUES(zip_code), "
        "address=VALUES(address); "
        "INSERT INTO user_billing_info (user_id, first_name, sur_name, country, state, "
        "zip_code, address) VALUES "
        f\"({user_id}, '{billing_first}', '{billing_sur}', '{billing_country}', "
        f\"'{billing_state}', '{billing_zip}', '{billing_address}') "
        "ON DUPLICATE KEY UPDATE first_name=VALUES(first_name), sur_name=VALUES(sur_name), "
        "country=VALUES(country), state=VALUES(state), zip_code=VALUES(zip_code), "
        "address=VALUES(address);"
    )

"""Adaptadores de persistencia para backend core."""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any


def _load_storage_structure_module():
    """Carga el módulo de estructura de almacenamiento compartido."""
    module_path = (
        Path(__file__).resolve().parents[5]
        / "src/2_shared_application/storage_access_structure.py"
    )
    spec = importlib.util.spec_from_file_location("storage_access_structure", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar storage_access_structure")
    module = importlib.util.module_from_spec(spec)
    sys.modules["storage_access_structure_backend"] = module
    spec.loader.exec_module(module)
    return module


def _load_env_settings_module():
    """Carga el módulo de configuración compartida."""
    module_path = (
        Path(__file__).resolve().parents[5]
        / "src/2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location("env_settings_backend_storage", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar env_settings")
    module = importlib.util.module_from_spec(spec)
    sys.modules["env_settings_backend_storage"] = module
    spec.loader.exec_module(module)
    return module


_storage_structure = _load_storage_structure_module()
get_folder_by_id_organization = _storage_structure.get_folder_by_id_organization
get_folder_by_id_project = _storage_structure.get_folder_by_id_project

_env_settings = _load_env_settings_module()


class StorageAdapterError(Exception):
    """Error al interactuar con la persistencia."""


@dataclass(frozen=True, slots=True)
class FmanagementSettings:
    """Configuración para la API externa de file management."""

    base_url: str
    base_path: str


def load_fmanagement_settings() -> FmanagementSettings:
    """Carga configuración de fmanagement desde entorno.
    
    Prioridad:
    1. Variable de entorno FMANAGEMENT_BASE_URL / FMANAGEMENT_BASE_PATH
    2. Valor de env.yaml (fmanagement_base_url / fmanagement_base_path)
    3. Fallback a valores por defecto
    """

    base_url = _env_settings.get_env_value("FMANAGEMENT_BASE_URL", "http://localhost:1666")
    base_path = _env_settings.get_env_value("FMANAGEMENT_BASE_PATH", "/data/external")
    return FmanagementSettings(
        base_url=base_url.rstrip("/"),
        base_path=base_path,
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

    env_settings = _load_env_settings_module("backend_core_env_settings")
    protected = env_settings.load_protected_settings()
    if not protected:
        raise StorageAdapterError(
            "No se pudo cargar la configuración de MariaDB desde protected_values"
        )

    return {
        "host": os.environ.get("MARIADB_HOST", protected.get("mariadb_host", "")),
        "port": int(
            os.environ.get("MARIADB_PORT", protected.get("mariadb_port", 3306))
        ),
        "core_database": os.environ.get(
            "MARIADB_CORE_DATABASE", protected.get("mariadb_core_database", "")
        ),
        "projects_database": os.environ.get(
            "MARIADB_PROJECTS_DATABASE", protected.get("mariadb_ai_database", "")
        ),
        "admin_user": os.environ.get(
            "MARIADB_ADMIN_USER", protected.get("mariadb_admin_user", "")
        ),
        "admin_password": os.environ.get(
            "MARIADB_ADMIN_PASSWORD", protected.get("mariadb_admin_password", "")
        ),
        "writer_user": os.environ.get(
            "MARIADB_WRITER_USER", protected.get("mariadb_writer_user", "")
        ),
        "writer_password": os.environ.get(
            "MARIADB_WRITER_PASSWORD",
            protected.get("mariadb_writer_password", ""),
        ),
        "reader_user": os.environ.get(
            "MARIADB_READER_USER", protected.get("mariadb_reader_user", "")
        ),
        "reader_password": os.environ.get(
            "MARIADB_READER_PASSWORD",
            protected.get("mariadb_reader_password", ""),
        ),
        "root_user": os.environ.get(
            "MARIADB_ROOT_USER", protected.get("mariadb_root_user", "")
        ),
        "root_password": os.environ.get(
            "MARIADB_ROOT_PASSWORD", protected.get("mariadb_root_password", "")
        ),
        "admin_dsn": os.environ.get(
            "MARIADB_ADMIN_DSN", protected.get("mariadb_admin_dsn", "")
        ),
        "writer_dsn": os.environ.get(
            "MARIADB_WRITER_DSN", protected.get("mariadb_writer_dsn", "")
        ),
        "reader_dsn": os.environ.get(
            "MARIADB_READER_DSN", protected.get("mariadb_reader_dsn", "")
        ),
        "root_dsn": os.environ.get(
            "MARIADB_ROOT_DSN", protected.get("mariadb_root_dsn", "")
        ),
        "cli_path": os.environ.get(
            "MARIADB_CLI_PATH", protected.get("mariadb_cli_path", "")
        ),
    }


def load_laim_mariadb_settings() -> dict[str, Any]:
    """Carga configuración de MariaDB para laim_core_db."""

    env_settings = _load_env_settings_module("backend_core_laim_env_settings")
    protected = env_settings.load_protected_settings()
    if not protected:
        raise StorageAdapterError(
            "No se pudo cargar la configuración LAIM desde protected_values"
        )

    database = os.environ.get(
        "LAIM_CORE_DATABASE",
        env_settings.get_env_value("laim_core_database", "laim_core_db"),
    )

    return {
        "host": os.environ.get("MARIADB_HOST", protected.get("mariadb_host", "")),
        "port": int(
            os.environ.get("MARIADB_PORT", protected.get("mariadb_port", 3306))
        ),
        "database": database,
        "writer_user": os.environ.get(
            "LAIM_WRITER_USER", protected.get("laim_writer_user", "")
        ),
        "writer_password": os.environ.get(
            "LAIM_WRITER_PASSWORD", protected.get("laim_writer_password", "")
        ),
        "reader_user": os.environ.get(
            "LAIM_READER_USER", protected.get("laim_reader_user", "")
        ),
        "reader_password": os.environ.get(
            "LAIM_READER_PASSWORD", protected.get("laim_reader_password", "")
        ),
        "writer_dsn": os.environ.get(
            "LAIM_WRITER_DSN", protected.get("laim_writer_dsn", "")
        ),
        "admin_user": os.environ.get(
            "LAIM_ADMIN_USER", protected.get("laim_admin_user", "")
        ),
        "admin_password": os.environ.get(
            "LAIM_ADMIN_PASSWORD", protected.get("laim_admin_password", "")
        ),
        "admin_dsn": os.environ.get(
            "LAIM_ADMIN_DSN", protected.get("laim_admin_dsn", "")
        ),
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


def _load_env_settings_module(module_name: str) -> Any:
    """Carga el módulo de configuración compartida."""

    module_path = (
        Path(__file__).resolve().parents[5]
        / "src/2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise StorageAdapterError("No se pudo cargar el módulo de configuración")
    module = importlib.util.module_from_spec(spec)
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
        """Guarda usuarios en JSON y sincroniza con MariaDB.
        
        IMPORTANTE: Sincroniza primero con MariaDB (si aplica) y luego
        escribe el JSON. Esto garantiza que si la BD falla, el JSON local
        no queda desincronizado.
        """
        _logger = logging.getLogger("backend_core.storage")
        
        # Log de entrada con OTPs relevantes para debugging
        admin_users = [u for u in users if u.user_name == "adminone"]
        if admin_users:
            _logger.info(
                "store_users() llamado - adminone OTP=%s",
                admin_users[0].user_otp
            )

        # Primero sincronizar con MariaDB (si está configurado)
        # Esto garantiza que si falla la BD, no actualizamos el JSON
        should_sync = _should_sync_users_to_db()
        _logger.info("should_sync_users_to_db() = %s", should_sync)
        
        if should_sync:
            _logger.info("Sincronizando %d usuarios con MariaDB...", len(users))
            _sync_users_to_mariadb(users)
            _logger.info("Sincronización con MariaDB completada")
        
        # Solo si la sincronización con BD fue exitosa (o no aplica),
        # actualizamos el JSON local
        _logger.info("Escribiendo JSON a %s", self._users_path)
        _write_json_list(self._users_path, [user.model_dump() for user in users])
        _logger.info("JSON actualizado correctamente")

    def load_organizations(self) -> list[OrganizationDto]:
        """Carga organizaciones desde JSON o MariaDB según storage_mode."""

        if _should_read_users_from_db():  # Usa la misma lógica: db_only
            records = _load_organizations_from_mariadb()
        else:
            records = _load_json_list(self._organizations_path)
        return [OrganizationDto.model_validate(record) for record in records]

    def store_organizations(self, organizations: list[OrganizationDto]) -> None:
        """Guarda organizaciones en JSON y sincroniza con MariaDB si procede."""

        if _should_read_users_from_db():
            _sync_organizations_to_mariadb(organizations)

        _write_json_list(
            self._organizations_path, [org.model_dump() for org in organizations]
        )

    def load_roles(self) -> list[RoleDto]:
        """Carga roles desde JSON o MariaDB según storage_mode."""

        if _should_read_users_from_db():  # Usa la misma lógica: db_only
            records = _load_roles_from_mariadb()
        else:
            records = _load_json_list(self._roles_path)
        return [RoleDto.model_validate(record) for record in records]

    def store_roles(self, roles: list[RoleDto]) -> None:
        """Guarda roles en JSON."""

        _write_json_list(
            self._roles_path, [role.model_dump() for role in roles]
        )

    def load_basic_permissions(self) -> list[BasicPermissionDto]:
        """Carga permisos básicos desde JSON."""

        records = _load_json_list(self._basic_permissions_path)
        return [BasicPermissionDto.model_validate(record) for record in records]

    def store_basic_permissions(self, permissions: list[BasicPermissionDto]) -> None:
        """Guarda permisos básicos en JSON."""

        _write_json_list(
            self._basic_permissions_path,
            [permission.model_dump() for permission in permissions],
        )

    def load_low_level_permissions(self) -> list[LowLevelPermissionDto]:
        """Carga permisos de bajo nivel desde JSON o MariaDB según storage_mode."""

        if _should_read_users_from_db():  # Usa la misma lógica: db_only
            records = _load_low_level_permissions_from_mariadb()
        else:
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

    env_settings = _load_env_settings_module("backend_core_env_settings")
    mode = env_settings.get_env_value("STORAGE_MODE", "mock")
    return mode in {"mock_and_db", "db_only"}


def _should_read_users_from_db() -> bool:
    """Determina si se deben leer usuarios desde MariaDB."""

    env_settings = _load_env_settings_module("backend_core_env_settings")
    mode = env_settings.get_env_value("STORAGE_MODE", "mock")
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


def _load_low_level_permissions_from_mariadb() -> list[dict[str, Any]]:
    """Carga permisos de bajo nivel desde MariaDB."""

    settings = load_mariadb_settings()
    cli_path = settings["cli_path"]
    db_name = settings["core_database"]
    db_user = settings["reader_user"]
    db_password = settings["reader_password"]
    if not cli_path or not db_user:
        raise StorageAdapterError("Faltan credenciales de lectura para MariaDB")

    query = "SELECT * FROM low_level_permissions ORDER BY id_permissions"
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
            f"No se pudo leer low_level_permissions desde MariaDB: {exc}"
        ) from exc
    records: list[dict[str, Any]] = []
    # Campos de la tabla low_level_permissions
    fields = [
        "id_permissions", "folder_create", "folder_delete", "folder_rename",
        "folder_read", "file_create", "file_read", "file_update", "file_delete",
        "project_create", "project_read", "project_update", "project_delete",
        "version_create", "version_read", "version_update", "version_delete",
        "training_create", "training_read", "training_update", "training_delete",
        "training_start", "training_stop", "parameters_create", "parameters_read",
        "parameters_update", "parameters_delete", "notifications_create",
        "notifications_read", "notifications_update", "notifications_delete",
        "user_create", "user_read", "user_update", "user_delete", "user_enable",
        "user_disable", "folder_list", "file_list", "project_list", "version_list"
    ]
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        row = line.split("\t")
        record: dict[str, Any] = {}
        for idx, field in enumerate(fields):
            if idx < len(row):
                if field == "id_permissions":
                    record[field] = int(row[idx]) if row[idx] else 0
                else:
                    # Convertir 0/1 a boolean
                    record[field] = bool(int(row[idx])) if row[idx] else False
        records.append(record)
    return records


def _load_roles_from_mariadb() -> list[dict[str, Any]]:
    """Carga roles desde MariaDB."""

    settings = load_mariadb_settings()
    cli_path = settings["cli_path"]
    db_name = settings["core_database"]
    db_user = settings["reader_user"]
    db_password = settings["reader_password"]
    if not cli_path or not db_user:
        raise StorageAdapterError("Faltan credenciales de lectura para MariaDB")

    query = (
        "SELECT identity_type_id, identity_type_name, identity_type_rol, "
        "identity_type_group_permission FROM roles ORDER BY identity_type_id"
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
            f"No se pudo leer roles desde MariaDB: {exc}"
        ) from exc
    records: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        row = line.split("\t")
        perm_id = int(row[3]) if len(row) > 3 and row[3] else 0
        records.append({
            "identity_type_id": int(row[0]) if row[0] else 0,
            "identity_type_name": row[1] or "",
            "identity_type_rol": row[2] or "",
            "identity_type_group_permissions": [perm_id] if perm_id else [],
        })
    return records


def _load_organizations_from_mariadb() -> list[dict[str, Any]]:
    """Carga organizaciones desde MariaDB."""

    settings = load_mariadb_settings()
    cli_path = settings["cli_path"]
    db_name = settings["core_database"]
    db_user = settings["reader_user"]
    db_password = settings["reader_password"]
    if not cli_path or not db_user:
        raise StorageAdapterError("Faltan credenciales de lectura para MariaDB")

    query = (
        "SELECT organization_id, organization_name, organization_email, "
        "organization_tlf, organization_address, organization_country, "
        "organization_state, active "
        "FROM organizations ORDER BY organization_id"
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
            f"No se pudo leer organizations desde MariaDB: {exc}"
        ) from exc
    records: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        row = line.split("\t")
        if len(row) >= 8:
            records.append({
                "organization_id": int(row[0]) if row[0] else 0,
                "organization_name": row[1] or "",
                "organization_email": row[2] or "",
                "organization_tlf": row[3] if row[3] and row[3] != "NULL" else "",
                "organization_address": row[4] if row[4] and row[4] != "NULL" else "",
                "organization_country": row[5] if row[5] and row[5] != "NULL" else "",
                "organization_state": row[6] if row[6] and row[6] != "NULL" else "",
                "active": bool(int(row[7])) if row[7] else False,
            })
    return records


def _sync_organizations_to_mariadb(organizations: list[OrganizationDto]) -> None:
    """Sincroniza organizaciones en MariaDB (INSERT o UPDATE).

    Usa INSERT ... ON DUPLICATE KEY UPDATE para garantizar que todas las
    organizaciones del listado existen en la tabla organizations de MariaDB.
    """

    settings = load_mariadb_settings()
    cli_path = settings["cli_path"]
    db_name = settings["core_database"]
    db_user = settings["writer_user"]
    db_password = settings["writer_password"]
    if not cli_path or not db_user:
        raise StorageAdapterError(
            "Faltan credenciales de escritura para MariaDB (organizations)"
        )

    def sql_escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "''")

    for org in organizations:
        payload = org.model_dump()
        org_id = int(payload.get("organization_id", 0))
        org_name = sql_escape(str(payload.get("organization_name", "")))
        org_email = sql_escape(str(payload.get("organization_email", "")))
        org_tlf = sql_escape(str(payload.get("organization_tlf", "")))
        org_address = sql_escape(str(payload.get("organization_address", "")))
        org_country = sql_escape(str(payload.get("organization_country", "")))
        org_state = sql_escape(str(payload.get("organization_state", "")))
        active = 1 if payload.get("active", True) else 0

        sql = (
            f"INSERT INTO organizations "
            f"(organization_id, organization_name, organization_email, "
            f"organization_tlf, organization_address, organization_country, "
            f"organization_state, active) "
            f"VALUES ({org_id}, '{org_name}', '{org_email}', "
            f"'{org_tlf}', '{org_address}', '{org_country}', "
            f"'{org_state}', {active}) "
            f"ON DUPLICATE KEY UPDATE "
            f"organization_name='{org_name}', "
            f"organization_email='{org_email}', "
            f"organization_tlf='{org_tlf}', "
            f"organization_address='{org_address}', "
            f"organization_country='{org_country}', "
            f"organization_state='{org_state}', "
            f"active={active};"
        )

        cmd = [
            cli_path,
            "-u",
            db_user,
            f"-p{db_password}",
            "--database",
            db_name,
            "-e",
            sql,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr if exc.stderr else str(exc)
            logging.getLogger("backend_core.storage").error(
                "Error sincronizando org_id=%s a MariaDB: %s",
                org_id,
                error_msg,
            )
            raise StorageAdapterError(
                f"No se pudo sincronizar organización {org_id} a MariaDB: {error_msg}"
            ) from exc


def _sync_users_to_mariadb(users: list[UserDto]) -> None:
    """Sincroniza usuarios en MariaDB (tabla users y datos asociados).
    
    CRÍTICO: Esta función debe completarse exitosamente antes de actualizar
    el JSON local. Si falla, se lanza StorageAdapterError y el OTP quedará
    sincronizado entre ambas fuentes.
    """

    settings = load_mariadb_settings()
    cli_path = settings["cli_path"]
    db_name = settings["core_database"]
    db_user = settings["writer_user"]
    db_password = settings["writer_password"]
    if not cli_path or not db_user:
        raise StorageAdapterError("Faltan credenciales de escritura para MariaDB")

    def sql_escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "''")

    for user in users:
        payload = user.model_dump()
        # Construir un solo comando SQL con todas las operaciones
        sqls = _build_user_upsert_sqls(payload, sql_escape)
        # Unir todos los SQLs en un solo comando
        combined_sql = " ".join(sqls)
        cmd = [
            cli_path,
            "-u",
            db_user,
            f"-p{db_password}",
            "--database",
            db_name,
            "-e",
            combined_sql,
        ]
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            if result.stderr:
                # MariaDB puede enviar warnings a stderr incluso con éxito
                logging.getLogger("backend_core.storage").warning(
                    "MariaDB warning para user_id=%s: %s",
                    payload.get("user_id"),
                    result.stderr.strip(),
                )
        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr if exc.stderr else str(exc)
            logging.getLogger("backend_core.storage").error(
                "Error sincronizando user_id=%s a MariaDB: %s",
                payload.get("user_id"),
                error_msg,
            )
            raise StorageAdapterError(
                f"No se pudo sincronizar usuario {payload.get('user_id')} a MariaDB: {error_msg}"
            ) from exc


def _build_user_upsert_sqls(payload: dict[str, Any], escape: Any) -> list[str]:
    """Construye lista de SQLs de upsert para users y tablas asociadas."""

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

    # Retornar lista de SQLs para ejecutar por separado
    return [
        # 1. REPLACE en users (más seguro que INSERT... ON DUPLICATE KEY)
        (
            "REPLACE INTO users (user_id, organization_id, identity_type_id, user_name, "
            "user_password, user_email, user_mobile, user_otp, active, blocked) VALUES "
            f"({user_id}, {org_id}, {identity_id}, '{user_name}', '{user_password}', "
            f"'{user_email}', '{user_mobile}', '{user_otp}', {active}, {blocked});"
        ),
        # 2. REPLACE en user_contact_info
        (
            "REPLACE INTO user_contact_info (user_id, first_name, sur_name, country, state, "
            "zip_code, address) VALUES "
            f"({user_id}, '{contact_first}', '{contact_sur}', '{contact_country}', "
            f"'{contact_state}', '{contact_zip}', '{contact_address}');"
        ),
        # 3. REPLACE en user_billing_info
        (
            "REPLACE INTO user_billing_info (user_id, first_name, sur_name, country, state, "
            "zip_code, address) VALUES "
            f"({user_id}, '{billing_first}', '{billing_sur}', '{billing_country}', "
            f"'{billing_state}', '{billing_zip}', '{billing_address}');"
        ),
    ]

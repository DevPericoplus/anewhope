"""Capa de orquestación del backend core."""

from __future__ import annotations

import importlib.util
import logging
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


def _load_dto_module(module_name: str, filename: str) -> Any:
    """Carga un módulo de DTOs desde el paquete compartido."""

    module_path = (
        Path(__file__).resolve().parents[3]
        / "src/2_shared_application/dtos"
        / filename
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el módulo de DTOs")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_domain_dtos = _load_dto_module("shared_domain_dtos_core_router", "domain_dtos.py")
_security_dtos = _load_dto_module("shared_security_dtos_core_router", "security_dtos.py")

OrganizationDto = _domain_dtos.OrganizationDto
UserDto = _domain_dtos.UserDto
RoleDto = _security_dtos.RoleDto
BasicPermissionDto = _security_dtos.BasicPermissionDto
LowLevelPermissionDto = _security_dtos.LowLevelPermissionDto
ManageRoleByOrgDto = _security_dtos.ManageRoleByOrgDto


def _load_storage_module(module_name: str) -> Any:
    """Carga el módulo de almacenamiento desde infraestructura."""

    module_path = (
        Path(__file__).resolve().parent
        / "4_infrastructure"
        / "persistence"
        / "storage_adapter.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el módulo de almacenamiento")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_storage_module = _load_storage_module("backend_core_storage")

JsonMockStorageAdapter = _storage_module.JsonMockStorageAdapter
StorageAdapterError = _storage_module.StorageAdapterError
build_storage_paths = _storage_module.build_storage_paths
load_fmanagement_settings = _storage_module.load_fmanagement_settings


def _load_fmanagement_module(module_name: str) -> Any:
    """Carga el cliente de fmanagement desde infraestructura."""

    module_path = (
        Path(__file__).resolve().parent
        / "4_infrastructure"
        / "web"
        / "fmanagement_client.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el cliente de fmanagement")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_fmanagement_module = _load_fmanagement_module("backend_core_fmanagement")

FmanagementClient = _fmanagement_module.FmanagementClient
FmanagementClientError = _fmanagement_module.FmanagementClientError


class BackendCoreBusinessError(Exception):
    """Error de negocio del backend core."""


class BackendCoreRouter:
    """Orquestador de operaciones del backend core."""

    def __init__(
        self,
        storage: JsonMockStorageAdapter,
        fmanagement_client: FmanagementClient | None = None,
    ) -> None:
        self._storage = storage
        self._fmanagement_client = fmanagement_client
        self._logger = logging.getLogger("backend_core.router")

    def list_users(self) -> list[UserDto]:
        """Lista usuarios."""

        try:
            return self._storage.load_users()
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError("No se pudo cargar usuarios") from exc

    def store_users(self, users: list[UserDto]) -> None:
        """Guarda usuarios."""

        try:
            self._storage.store_users(users)
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError("No se pudo guardar usuarios") from exc

    def list_organizations(self) -> list[OrganizationDto]:
        """Lista organizaciones."""

        try:
            return self._storage.load_organizations()
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError(
                "No se pudo cargar organizaciones"
            ) from exc

    def store_organizations(self, organizations: list[OrganizationDto]) -> None:
        """Guarda organizaciones."""

        try:
            self._storage.store_organizations(organizations)
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError(
                "No se pudo guardar organizaciones"
            ) from exc

    def list_roles(self) -> list[RoleDto]:
        """Lista roles."""

        try:
            return self._storage.load_roles()
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError("No se pudo cargar roles") from exc

    def list_basic_permissions(self) -> list[BasicPermissionDto]:
        """Lista permisos básicos."""

        try:
            return self._storage.load_basic_permissions()
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError(
                "No se pudo cargar permisos básicos"
            ) from exc

    def list_low_level_permissions(self) -> list[LowLevelPermissionDto]:
        """Lista permisos de bajo nivel."""

        try:
            return self._storage.load_low_level_permissions()
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError(
                "No se pudo cargar permisos de bajo nivel"
            ) from exc

    def list_manage_roles(self) -> list[ManageRoleByOrgDto]:
        """Lista roles por organización."""

        try:
            return self._storage.load_manage_roles()
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError(
                "No se pudo cargar roles por organización"
            ) from exc

    def store_manage_roles(self, entries: list[ManageRoleByOrgDto]) -> None:
        """Guarda roles por organización."""

        try:
            self._storage.store_manage_roles(entries)
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError(
                "No se pudo guardar roles por organización"
            ) from exc

    def check_organization_name(self, organization_name: str) -> bool:
        """Valida si existe una organización."""

        organizations = self.list_organizations()
        if not organizations:
            return False
        normalized_input = self._normalize_text(organization_name)
        return any(
            self._normalize_text(str(org.organization_name)) == normalized_input
            for org in organizations
        )

    def create_organization(self, payload: dict[str, Any]) -> int:
        """Crea una organización y retorna el ID."""

        organization_name = payload.get("organization_name", "").strip()
        if self.check_organization_name(organization_name):
            raise BackendCoreBusinessError(
                "Esa organización ya existe en nuestro sistema"
            )

        organizations = self.list_organizations()
        existing_ids = [org.organization_id for org in organizations]
        next_id = max(existing_ids, default=0) + 1
        record = OrganizationDto(
            organization_id=next_id,
            organization_name=organization_name,
            organization_email=payload.get("organization_email", "").strip(),
            organization_tlf=payload.get("organization_tlf", "").strip(),
            organization_address=payload.get("organization_address", "").strip(),
            organization_country=payload.get("organization_country", "").strip(),
            organization_state=payload.get("organization_state", "").strip(),
        )
        organizations.append(record)
        self.store_organizations(organizations)
        self._logger.info("Organización creada org_id=%s", next_id)
        return next_id

    def create_user(self, payload: dict[str, Any]) -> dict[str, int]:
        """Crea un usuario y registra rol por organización."""

        users = self.list_users()
        existing_ids = [user.user_id for user in users]
        next_id = max(existing_ids, default=0) + 1
        organization_id = int(payload.get("organization_id", 1))
        identity_type_id = self._resolve_identity_type_id(
            organization_id, payload.get("identity_type_id")
        )

        user_record = UserDto(
            user_id=next_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
            user_name=str(payload.get("user_name", "")).strip(),
            user_password=payload.get("user_password", ""),
            user_email=str(payload.get("user_email", "")).strip().lower(),
            user_mobile=str(payload.get("user_mobile", "")).strip(),
            user_otp=payload.get("user_otp", ""),
            active=bool(payload.get("active", True)),
            blocked=bool(payload.get("blocked", False)),
            contact_info=payload.get("contact_info", {}),
            billing_info=payload.get("billing_info", {}),
        )
        users.append(user_record)
        self.store_users(users)
        self._append_manage_role_entry(next_id, organization_id, identity_type_id)
        self._logger.info(
            "Usuario creado user_id=%s org_id=%s role_id=%s",
            next_id,
            organization_id,
            identity_type_id,
        )
        return {
            "user_id": next_id,
            "organization_id": organization_id,
            "identity_type_id": identity_type_id,
        }

    def get_permissions(self, identity_type_id: int) -> dict[str, Any]:
        """Obtiene permisos asociados a un rol."""

        roles = self.list_roles()
        role_entry = next(
            (role for role in roles if role.identity_type_id == identity_type_id),
            None,
        )
        if role_entry is None:
            self._logger.info(
                "Consulta permisos role_id=%s sin coincidencias",
                identity_type_id,
            )
            return {"permissions": [], "low_level_permissions": {}}
        permissions = self.list_basic_permissions()
        permission_ids = role_entry.identity_type_group_permissions
        basic_permissions = [
            permission.model_dump(by_alias=True)
            for permission in permissions
            if permission.id in permission_ids
        ]
        low_level_permissions = {}
        if permission_ids:
            permission_id = permission_ids[0]
            low_level_permissions = self._find_low_level_permission(permission_id)
        self._logger.info(
            "Consulta permisos role_id=%s permission_id=%s low_level_keys=%s",
            identity_type_id,
            permission_ids[0] if permission_ids else None,
            list(low_level_permissions.keys()) if low_level_permissions else [],
        )
        return {
            "permissions": basic_permissions,
            "low_level_permissions": low_level_permissions,
        }

    def fmo_operation(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Ejecuta operaciones de fichero/carpeta en fmanagement."""

        client = self._get_fmanagement_client()
        settings = load_fmanagement_settings()
        params = self._build_fmo_params(payload, settings.base_path)
        try:
            return client.request_json(
                "GET",
                "/fmo",
                params=params,
                headers=headers,
            )
        except FmanagementClientError as exc:
            raise BackendCoreBusinessError(
                "No se pudo ejecutar operación en fmanagement"
            ) from exc

    def fmo_upload(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
        file_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Sube un fichero a través de fmanagement."""

        client = self._get_fmanagement_client()
        settings = load_fmanagement_settings()
        form = self._build_fmo_params(payload, settings.base_path)
        try:
            return client.request_json(
                "POST",
                "/fmo",
                headers=headers,
                form=form,
                file_payload=file_payload,
            )
        except FmanagementClientError as exc:
            raise BackendCoreBusinessError(
                "No se pudo subir fichero en fmanagement"
            ) from exc

    def list_directory(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Lista estructura de carpetas vía fmanagement."""

        client = self._get_fmanagement_client()
        settings = load_fmanagement_settings()
        params = self._build_fmo_params(payload, settings.base_path)
        try:
            return client.request_json(
                "GET",
                "/fmo/list",
                params=params,
                headers=headers,
            )
        except FmanagementClientError as exc:
            raise BackendCoreBusinessError(
                "No se pudo listar directorios en fmanagement"
            ) from exc

    def create_new_version(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Crea una nueva versión delegando en fmanagement."""

        client = self._get_fmanagement_client()
        settings = load_fmanagement_settings()
        form = self._build_fmo_params(payload, settings.base_path)
        try:
            return client.request_json(
                "POST",
                "/fmo/newversion",
                headers=headers,
                form=form,
            )
        except FmanagementClientError as exc:
            raise BackendCoreBusinessError(
                "No se pudo crear nueva versión en fmanagement"
            ) from exc

    def diff_versions(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Compara versiones delegando en fmanagement."""

        client = self._get_fmanagement_client()
        settings = load_fmanagement_settings()
        params = self._build_fmo_params(payload, settings.base_path)
        try:
            return client.request_json(
                "GET",
                "/fmo/diffversion",
                params=params,
                headers=headers,
            )
        except FmanagementClientError as exc:
            raise BackendCoreBusinessError(
                "No se pudo comparar versiones en fmanagement"
            ) from exc

    def _find_low_level_permission(self, permission_id: int) -> dict[str, Any]:
        """Obtiene permisos de bajo nivel asociados a un permiso base."""

        for permission in self.list_low_level_permissions():
            if permission.id_permissions == permission_id:
                return permission.model_dump()
        return {}

    def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Procesa datos (placeholder)."""

        if not payload:
            raise BackendCoreBusinessError("El payload no puede estar vacío")
        return {"echo": payload}

    def _resolve_identity_type_id(
        self, organization_id: int, requested_identity_type_id: int | None
    ) -> int:
        """Determina el rol a asignar para un usuario."""

        entries = self.list_manage_roles()
        is_first_user = not any(
            entry.id_organization == organization_id for entry in entries
        )
        if is_first_user:
            return 2
        if requested_identity_type_id is not None:
            return requested_identity_type_id
        return 2

    def _append_manage_role_entry(
        self, user_id: int, organization_id: int, identity_type_id: int
    ) -> None:
        """Crea el registro de rol por organización."""

        entries = self.list_manage_roles()
        now_str = datetime.now().strftime("%d/%m/%y-%H:%M")
        entries.append(
            ManageRoleByOrgDto(
                id_user=user_id,
                id_organization=organization_id,
                identity_type_id=identity_type_id,
                create_date=now_str,
                modification_date="",
                id_modifier_user=1,
                active=True,
            )
        )
        self.store_manage_roles(entries)

    def _get_fmanagement_client(self) -> FmanagementClient:
        """Obtiene el cliente de fmanagement."""

        if self._fmanagement_client is None:
            raise BackendCoreBusinessError(
                "Cliente de fmanagement no configurado"
            )
        return self._fmanagement_client

    @staticmethod
    def _build_fmo_params(
        payload: dict[str, Any], base_path: str
    ) -> dict[str, str]:
        """Construye parámetros esperados por fmanagement."""

        id_organization = int(payload.get("id_organization", 0))
        id_project = int(payload.get("id_project", 0))
        version_path = str(payload.get("version_path", "")).strip()
        subfolders = str(payload.get("subfolders", "")).strip()
        paths = build_storage_paths(
            id_organization=id_organization,
            id_project=id_project,
            version_path=version_path,
            subfolders=subfolders,
        )
        params = {
            "iduser": str(payload.get("id_user", 0)),
            "basepath": base_path,
            "orgpath": paths["orgpath"],
            "prjpath": paths["prjpath"],
            "versionpath": paths["versionpath"],
            "subfolders": paths["subfolders"],
            "filename": str(payload.get("filename", "")).strip(),
            "extfile": str(payload.get("ext_file", "")).strip(),
            "operation": str(payload.get("operation", "")).strip(),
            "new_filename": str(payload.get("new_filename", "")).strip(),
            "new_extfile": str(payload.get("new_extfile", "")).strip(),
            "compare_versionpath": str(
                payload.get("compare_version_path", "")
            ).strip(),
            "identity_type_id": str(payload.get("identity_type_id", "")).strip(),
        }
        return {key: value for key, value in params.items() if value}

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza texto eliminando acentos y convirtiendo a minúsculas."""

        normalized = unicodedata.normalize("NFD", text.strip().lower())
        return "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )

"""Capa de orquestación del backend core con validación de permisos.

Este módulo implementa la capa de orquestación del backend core,
integrando validación de permisos de bajo nivel (Security by Design)
en todas las operaciones.

Principios:
- Toda operación valida permisos antes de ejecutarse
- Los permisos se obtienen del PermissionValidationService centralizado
- Si no hay permiso, se lanza BackendCorePermissionError
"""

from __future__ import annotations

import importlib.util
import logging
import sys
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
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_permission_service() -> Any:
    """Carga el servicio de validación de permisos."""

    module_path = (
        Path(__file__).resolve().parents[3]
        / "src/2_shared_application/services/permission_validation_service.py"
    )
    module_name = "permission_validation_service_core"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el servicio de permisos")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_permission_module = _load_permission_service()
PermissionValidationService = _permission_module.PermissionValidationService
PermissionContext = _permission_module.PermissionContext


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
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_storage_module = _load_storage_module("backend_core_storage")

JsonMockStorageAdapter = _storage_module.JsonMockStorageAdapter
StorageAdapterError = _storage_module.StorageAdapterError
build_storage_paths = _storage_module.build_storage_paths
load_fmanagement_settings = _storage_module.load_fmanagement_settings
load_mariadb_settings = _storage_module.load_mariadb_settings


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


class BackendCorePermissionError(Exception):
    """Error de permisos del backend core (Security by Design)."""
    
    def __init__(self, permission_key: str, identity_type_id: int, message: str = ""):
        self.permission_key = permission_key
        self.identity_type_id = identity_type_id
        super().__init__(
            message or f"Permiso '{permission_key}' denegado para rol {identity_type_id}"
        )


class BackendCoreRouter:
    """Orquestador de operaciones del backend core con validación de permisos.
    
    Implementa Security by Design validando permisos de bajo nivel
    antes de ejecutar cualquier operación sobre recursos.
    
    Attributes:
        _storage: Adaptador de almacenamiento
        _fmanagement_client: Cliente de fmanagement para operaciones de archivos
        _permission_service: Servicio centralizado de validación de permisos
    """

    def __init__(
        self,
        storage: JsonMockStorageAdapter,
        fmanagement_client: FmanagementClient | None = None,
        permission_service: PermissionValidationService | None = None,
    ) -> None:
        self._storage = storage
        self._fmanagement_client = fmanagement_client
        self._permission_service = permission_service or PermissionValidationService()
        self._logger = logging.getLogger("backend_core.router")
    
    # === Métodos de validación de permisos (Security by Design) ===
    
    def validate_permission(
        self,
        identity_type_id: int,
        permission_key: str,
        raise_on_deny: bool = True,
    ) -> bool:
        """
        Valida si el rol tiene un permiso específico.
        
        Args:
            identity_type_id: ID del tipo de identidad (rol)
            permission_key: Clave del permiso (ej: "folder_rename")
            raise_on_deny: Si es True, lanza excepción si no tiene permiso
        
        Returns:
            True si tiene el permiso
        
        Raises:
            BackendCorePermissionError: Si no tiene permiso y raise_on_deny=True
        """
        allowed = self._permission_service.can_perform_action(
            identity_type_id, permission_key
        )
        
        if not allowed and raise_on_deny:
            self._logger.warning(
                "Permiso denegado: identity_type_id=%s permission=%s",
                identity_type_id,
                permission_key,
            )
            raise BackendCorePermissionError(permission_key, identity_type_id)
        
        return allowed
    
    def validate_folder_operation(
        self,
        identity_type_id: int,
        operation: str,
    ) -> bool:
        """
        Valida permiso para operaciones de carpeta.
        
        Args:
            identity_type_id: ID del rol
            operation: Tipo de operación (create, delete, rename, read, list)
        
        Returns:
            True si tiene permiso
        
        Raises:
            BackendCorePermissionError: Si no tiene permiso
        """
        permission_map = {
            "create": "folder_create",
            "delete": "folder_delete",
            "rename": "folder_rename",
            "read": "folder_read",
            "list": "folder_list",
        }
        permission_key = permission_map.get(operation.lower())
        if not permission_key:
            raise BackendCoreBusinessError(f"Operación de carpeta desconocida: {operation}")
        
        return self.validate_permission(identity_type_id, permission_key)
    
    def validate_file_operation(
        self,
        identity_type_id: int,
        operation: str,
    ) -> bool:
        """
        Valida permiso para operaciones de archivo.
        
        Args:
            identity_type_id: ID del rol
            operation: Tipo de operación (create, read, update, delete, list)
        
        Returns:
            True si tiene permiso
        
        Raises:
            BackendCorePermissionError: Si no tiene permiso
        """
        permission_map = {
            "create": "file_create",
            "read": "file_read",
            "update": "file_update",
            "delete": "file_delete",
            "list": "file_list",
        }
        permission_key = permission_map.get(operation.lower())
        if not permission_key:
            raise BackendCoreBusinessError(f"Operación de archivo desconocida: {operation}")
        
        return self.validate_permission(identity_type_id, permission_key)
    
    def validate_project_operation(
        self,
        identity_type_id: int,
        operation: str,
    ) -> bool:
        """
        Valida permiso para operaciones de proyecto.
        
        Args:
            identity_type_id: ID del rol
            operation: Tipo de operación (create, read, update, delete, list)
        
        Returns:
            True si tiene permiso
        
        Raises:
            BackendCorePermissionError: Si no tiene permiso
        """
        permission_map = {
            "create": "project_create",
            "read": "project_read",
            "update": "project_update",
            "delete": "project_delete",
            "list": "project_list",
        }
        permission_key = permission_map.get(operation.lower())
        if not permission_key:
            raise BackendCoreBusinessError(f"Operación de proyecto desconocida: {operation}")
        
        return self.validate_permission(identity_type_id, permission_key)
    
    def validate_version_operation(
        self,
        identity_type_id: int,
        operation: str,
    ) -> bool:
        """
        Valida permiso para operaciones de versión.
        
        Args:
            identity_type_id: ID del rol
            operation: Tipo de operación (create, read, update, delete, list)
        
        Returns:
            True si tiene permiso
        
        Raises:
            BackendCorePermissionError: Si no tiene permiso
        """
        permission_map = {
            "create": "version_create",
            "read": "version_read",
            "update": "version_update",
            "delete": "version_delete",
            "list": "version_list",
        }
        permission_key = permission_map.get(operation.lower())
        if not permission_key:
            raise BackendCoreBusinessError(f"Operación de versión desconocida: {operation}")
        
        return self.validate_permission(identity_type_id, permission_key)
    
    def validate_training_operation(
        self,
        identity_type_id: int,
        operation: str,
    ) -> bool:
        """
        Valida permiso para operaciones de entrenamiento.
        
        Args:
            identity_type_id: ID del rol
            operation: Tipo de operación (create, read, update, delete, start, stop)
        
        Returns:
            True si tiene permiso
        
        Raises:
            BackendCorePermissionError: Si no tiene permiso
        """
        permission_map = {
            "create": "training_create",
            "read": "training_read",
            "update": "training_update",
            "delete": "training_delete",
            "start": "training_start",
            "stop": "training_stop",
        }
        permission_key = permission_map.get(operation.lower())
        if not permission_key:
            raise BackendCoreBusinessError(f"Operación de entrenamiento desconocida: {operation}")
        
        return self.validate_permission(identity_type_id, permission_key)
    
    def validate_user_operation(
        self,
        identity_type_id: int,
        operation: str,
    ) -> bool:
        """
        Valida permiso para operaciones de usuario.
        
        Args:
            identity_type_id: ID del rol
            operation: Tipo de operación (create, read, update, delete, enable, disable)
        
        Returns:
            True si tiene permiso
        
        Raises:
            BackendCorePermissionError: Si no tiene permiso
        """
        permission_map = {
            "create": "user_create",
            "read": "user_read",
            "update": "user_update",
            "delete": "user_delete",
            "enable": "user_enable",
            "disable": "user_disable",
        }
        permission_key = permission_map.get(operation.lower())
        if not permission_key:
            raise BackendCoreBusinessError(f"Operación de usuario desconocida: {operation}")
        
        return self.validate_permission(identity_type_id, permission_key)

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

    def store_roles(self, roles: list[RoleDto]) -> None:
        """Guarda roles."""

        try:
            self._storage.store_roles(roles)
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError("No se pudo guardar roles") from exc

    def list_basic_permissions(self) -> list[BasicPermissionDto]:
        """Lista permisos básicos."""

        try:
            return self._storage.load_basic_permissions()
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError(
                "No se pudo cargar permisos básicos"
            ) from exc

    def store_basic_permissions(self, permissions: list[BasicPermissionDto]) -> None:
        """Guarda permisos básicos."""

        try:
            self._storage.store_basic_permissions(permissions)
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError(
                "No se pudo guardar permisos básicos"
            ) from exc

    def list_low_level_permissions(self) -> list[LowLevelPermissionDto]:
        """Lista permisos de bajo nivel."""

        try:
            return self._storage.load_low_level_permissions()
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError(
                "No se pudo cargar permisos de bajo nivel"
            ) from exc

    def store_low_level_permissions(self, permissions: list[LowLevelPermissionDto]) -> None:
        """Guarda permisos de bajo nivel."""

        try:
            self._storage.store_low_level_permissions(permissions)
        except StorageAdapterError as exc:
            raise BackendCoreBusinessError(
                "No se pudo guardar permisos de bajo nivel"
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

    def update_user_status(
        self, user_id: int, active: bool, requester_org_id: int
    ) -> dict[str, Any]:
        """Actualiza el estado activo/inactivo de un usuario en MariaDB.
        
        Este es el destino final del flujo:
        Frontend → Middleware → Broker → Backend Core (aquí) → MariaDB
        
        Args:
            user_id: ID del usuario a modificar
            active: True para habilitar, False para deshabilitar
            requester_org_id: ID de la organización del solicitante (para validación)
        
        Returns:
            Diccionario con user_id, active y message
        
        Raises:
            BackendCoreBusinessError: Si el usuario no existe o no pertenece a la org
        """
        # Cargar usuarios
        users = self.list_users()
        
        # Buscar el usuario
        target_user = None
        for user in users:
            if user.user_id == user_id:
                target_user = user
                break
        
        if target_user is None:
            raise BackendCoreBusinessError(f"Usuario con ID {user_id} no encontrado")
        
        # Validar que pertenece a la misma organización
        if target_user.organization_id != requester_org_id:
            raise BackendCoreBusinessError(
                "No tiene permisos para modificar usuarios de otra organización"
            )
        
        # Actualizar en JSON
        for user in users:
            if user.user_id == user_id:
                user.active = active
                break
        
        self.store_users(users)
        
        # Actualizar en MariaDB
        self._update_user_active_in_db(user_id, active)
        
        action = "habilitado" if active else "deshabilitado"
        self._logger.info(
            "Usuario %s (id=%s) %s por org_id=%s",
            target_user.user_name,
            user_id,
            action,
            requester_org_id,
        )
        
        return {
            "user_id": user_id,
            "active": active,
            "message": f"Usuario {action} correctamente",
        }

    def _update_user_active_in_db(self, user_id: int, active: bool) -> None:
        """Actualiza el campo active en la base de datos MariaDB."""
        try:
            from sqlalchemy import create_engine, text
            
            # Obtener DSN desde la configuración de MariaDB
            mariadb_config = load_mariadb_settings()
            dsn = mariadb_config.get("writer_dsn", "")
            
            if not dsn:
                self._logger.warning("No hay DSN configurado para actualizar en BD")
                return
            
            engine = create_engine(dsn)
            with engine.connect() as conn:
                conn.execute(
                    text("UPDATE users SET active = :active WHERE user_id = :user_id"),
                    {"active": 1 if active else 0, "user_id": user_id},
                )
                conn.commit()
            
            self._logger.info(
                "Usuario id=%s actualizado en MariaDB: active=%s", user_id, active
            )
        except Exception as e:
            self._logger.error("Error actualizando usuario en BD: %s", e)
            raise BackendCoreBusinessError(f"Error en base de datos: {e}") from e

    def check_user_exists(self, user_name: str) -> bool:
        """Verifica si existe un usuario por nombre de usuario.
        
        Args:
            user_name: Nombre de usuario a verificar
        
        Returns:
            True si el usuario existe, False en caso contrario
        """
        users = self.list_users()
        for user in users:
            if user.user_name.lower() == user_name.lower():
                self._logger.info("Usuario '%s' encontrado", user_name)
                return True
        self._logger.info("Usuario '%s' no encontrado", user_name)
        return False

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Obtiene datos de un usuario por email.
        
        Args:
            email: Email del usuario
        
        Returns:
            Diccionario con datos del usuario o None si no existe
        """
        users = self.list_users()
        email_lower = email.lower().strip()
        for user in users:
            if user.user_email.lower() == email_lower:
                self._logger.info("Usuario con email '%s' encontrado: id=%s", email, user.user_id)
                return {
                    "user_id": user.user_id,
                    "user_name": user.user_name,
                    "user_email": user.user_email,
                    "user_mobile": user.user_mobile,
                    "organization_id": user.organization_id,
                }
        self._logger.info("Usuario con email '%s' no encontrado", email)
        return None

    def update_user_password(self, email: str, new_password: str, new_otp: str) -> bool:
        """Actualiza contraseña y OTP de un usuario.
        
        Args:
            email: Email del usuario
            new_password: Nueva contraseña (ya cifrada)
            new_otp: Nuevo código OTP
        
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        users = self.list_users()
        email_lower = email.lower().strip()
        
        user_found = False
        user_id = None
        for user in users:
            if user.user_email.lower() == email_lower:
                user.user_password = new_password
                user.user_otp = new_otp
                user_found = True
                user_id = user.user_id
                break
        
        if not user_found:
            self._logger.warning("Usuario con email '%s' no encontrado para actualizar", email)
            return False
        
        # Guardar en JSON
        self.store_users(users)
        
        # Actualizar en MariaDB
        self._update_user_password_in_db(email, new_password, new_otp)
        
        self._logger.info("Contraseña actualizada para usuario email='%s' id=%s", email, user_id)
        return True

    def _update_user_password_in_db(self, email: str, new_password: str, new_otp: str) -> None:
        """Actualiza contraseña y OTP en MariaDB."""
        try:
            from sqlalchemy import create_engine, text
            
            mariadb_config = load_mariadb_settings()
            dsn = mariadb_config.get("writer_dsn", "")
            
            if not dsn:
                self._logger.warning("No hay DSN configurado para actualizar contraseña en BD")
                return
            
            engine = create_engine(dsn)
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        UPDATE users 
                        SET user_password = :password, user_otp = :otp 
                        WHERE user_email = :email
                    """),
                    {"password": new_password, "otp": new_otp, "email": email},
                )
                conn.commit()
            
            self._logger.info("Contraseña actualizada en MariaDB para email='%s'", email)
        except Exception as e:
            self._logger.error("Error actualizando contraseña en BD: %s", e)
            # No lanzar excepción, el JSON ya fue actualizado

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
        """
        Ejecuta operaciones de fichero/carpeta en fmanagement.
        
        SECURITY BY DESIGN: Valida permisos antes de ejecutar.
        """
        # Obtener identity_type_id del payload
        identity_type_id = int(payload.get("identity_type_id", 0))
        operation = str(payload.get("operation", "")).lower()
        
        # Validar permisos según tipo de operación
        if identity_type_id > 0 and operation:
            self._validate_fmo_permission(identity_type_id, operation, payload)
        
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
    
    def _validate_fmo_permission(
        self,
        identity_type_id: int,
        operation: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Valida permisos para operaciones de fmanagement.
        
        Mapea operaciones de fmanagement a permisos de bajo nivel.
        """
        # Mapeo de operaciones a permisos
        operation_permission_map = {
            # Operaciones de carpeta
            "createfolder": "folder_create",
            "deletefolder": "folder_delete",
            "renamefolder": "folder_rename",
            "readfolder": "folder_read",
            "listfolder": "folder_list",
            # Operaciones de archivo
            "createfile": "file_create",
            "readfile": "file_read",
            "updatefile": "file_update",
            "deletefile": "file_delete",
            "listfile": "file_list",
            "uploadfile": "file_create",
            "downloadfile": "file_read",
            # Operaciones combinadas
            "list": "folder_list",
            "read": "file_read",
            "write": "file_update",
            "delete": "file_delete",
        }
        
        permission_key = operation_permission_map.get(operation)
        if permission_key:
            self.validate_permission(identity_type_id, permission_key)
            self._logger.info(
                "Permiso validado: identity_type_id=%s operation=%s permission=%s",
                identity_type_id,
                operation,
                permission_key,
            )

    def fmo_upload(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
        file_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Sube un fichero a través de fmanagement.
        
        SECURITY BY DESIGN: Requiere permiso file_create.
        """
        # Validar permiso de creación de archivo
        identity_type_id = int(payload.get("identity_type_id", 0))
        if identity_type_id > 0:
            self.validate_permission(identity_type_id, "file_create")
            self._logger.info(
                "Permiso validado para upload: identity_type_id=%s",
                identity_type_id,
            )
        
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
        """
        Lista estructura de carpetas vía fmanagement.
        
        SECURITY BY DESIGN: Requiere permiso folder_list.
        """
        # Validar permiso de listado de carpetas
        identity_type_id = int(payload.get("identity_type_id", 0))
        if identity_type_id > 0:
            self.validate_permission(identity_type_id, "folder_list")
        
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
        """
        Crea una nueva versión delegando en fmanagement.
        
        SECURITY BY DESIGN: Requiere permiso version_create.
        """
        # Validar permiso de creación de versión
        identity_type_id = int(payload.get("identity_type_id", 0))
        if identity_type_id > 0:
            self.validate_permission(identity_type_id, "version_create")
            self._logger.info(
                "Permiso validado para nueva versión: identity_type_id=%s",
                identity_type_id,
            )
        
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
        """
        Compara versiones delegando en fmanagement.
        
        SECURITY BY DESIGN: Requiere permiso version_read.
        """
        # Validar permiso de lectura de versión
        identity_type_id = int(payload.get("identity_type_id", 0))
        if identity_type_id > 0:
            self.validate_permission(identity_type_id, "version_read")
        
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

    def transfer_version(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """
        Transfiere una versión entre servidores backend y trainer.
        
        Delega la operación en fmanagement que ejecutará la transferencia
        usando rsync over SSH (remoto) o copia local (desarrollo).
        
        SECURITY BY DESIGN: Requiere permiso version_create.
        
        Args:
            payload: Diccionario con los datos de transferencia:
                - id_user: ID del usuario
                - id_organization: ID de la organización
                - id_project: ID del proyecto
                - version_path: Versión a transferir (ej: v001)
                - target_type: Destino ('trainer' o 'core')
                - identity_type_id: ID del tipo de identidad para permisos
            headers: Headers HTTP para autenticación
        
        Returns:
            Diccionario con el resultado de la transferencia:
                - status: Estado de la operación
                - message: Mensaje descriptivo
                - source_path: Ruta origen
                - destination_path: Ruta destino
                - bytes_transferred: Bytes transferidos
                - files_transferred: Archivos transferidos
        
        Raises:
            BackendCoreBusinessError: Si falla la transferencia
            BackendCorePermissionError: Si no tiene permiso version_create
        """
        # Validar permiso de creación de versión (usado para transferencias)
        identity_type_id = int(payload.get("identity_type_id", 0))
        if identity_type_id > 0:
            self.validate_permission(identity_type_id, "version_create")
            self._logger.info(
                "Permiso validado para transferencia de versión: identity_type_id=%s",
                identity_type_id,
            )
        
        # Validar target_type
        target_type = str(payload.get("target_type", "")).lower()
        if target_type not in ("trainer", "core"):
            raise BackendCoreBusinessError(
                "target_type debe ser 'trainer' o 'core'"
            )
        
        client = self._get_fmanagement_client()
        
        # Construir payload para fmanagement
        id_organization = int(payload.get("id_organization", 0))
        id_project = int(payload.get("id_project", 0))
        version_path = str(payload.get("version_path", "")).strip()
        
        paths = build_storage_paths(
            id_organization=id_organization,
            id_project=id_project,
            version_path=version_path,
            subfolders="",
        )
        
        transfer_params = {
            "iduser": str(payload.get("id_user", 0)),
            "orgpath": paths["orgpath"],
            "prjpath": paths["prjpath"],
            "versionpath": paths["versionpath"],
            "target_type": target_type,
            "identity_type_id": str(identity_type_id) if identity_type_id else "",
        }
        
        self._logger.info(
            "Iniciando transferencia de versión: org=%s prj=%s version=%s target=%s",
            paths["orgpath"],
            paths["prjpath"],
            paths["versionpath"],
            target_type,
        )
        
        try:
            result = client.request_json(
                "POST",
                "/fmo/transferversion",
                headers=headers,
                form=transfer_params,
            )
            
            self._logger.info(
                "Transferencia completada: status=%s files=%s bytes=%s",
                result.get("status"),
                result.get("files_transferred", 0),
                result.get("bytes_transferred", 0),
            )
            
            return result
        except FmanagementClientError as exc:
            self._logger.error(
                "Error en transferencia de versión: %s", str(exc)
            )
            raise BackendCoreBusinessError(
                "No se pudo transferir la versión en fmanagement"
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

    # ========================================================================
    # Gestión de Proyectos (myllm_projects_db)
    # ========================================================================

    def get_organization_projects(
        self,
        organization_id: int,
        headers: dict[str, str],
        include_deleted: bool = False,
    ) -> list[dict[str, Any]]:
        """Obtiene los proyectos de una organización desde MariaDB.

        Consulta la base de datos myllm_projects_db directamente.
        
        Args:
            include_deleted: Si True, incluye proyectos con existe=false
        """
        self._logger.info(
            "[%s] Consultando proyectos org_id=%s include_deleted=%s",
            headers.get("X-Client-App", "unknown"),
            organization_id,
            include_deleted,
        )

        try:
            return self._get_projects_from_db(organization_id, include_deleted)
        except Exception as exc:
            self._logger.error("Error obteniendo proyectos: %s", exc)
            raise BackendCoreBusinessError(
                f"Error consultando proyectos: {exc}"
            ) from exc

    def create_project(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Crea un nuevo proyecto en MariaDB.

        El trigger tr_proyecto_after_insert crea automáticamente:
        - Registro en tabla estado (versión 1)
        - Registro en tabla cambios (tipo "Alta proyecto")
        """
        nombre = payload.get("nombre", "").strip()
        descripcion = payload.get("descripcion", "").strip()
        id_organizacion = int(payload.get("id_organizacion", 0))
        active = payload.get("active", True)
        id_flujo = int(payload.get("id_flujo", 1))

        if not nombre:
            raise BackendCoreBusinessError("El nombre del proyecto es obligatorio")
        if id_organizacion <= 0:
            raise BackendCoreBusinessError("ID de organización inválido")

        self._logger.info(
            "[%s] Creando proyecto: nombre=%s org_id=%s",
            headers.get("X-Client-App", "unknown"),
            nombre,
            id_organizacion,
        )

        try:
            project_id = self._insert_project_in_db(
                nombre, descripcion, id_organizacion, active, id_flujo
            )
            return {
                "project_id": project_id,
                "nombre": nombre,
                "id_organizacion": id_organizacion,
                "id_flujo": id_flujo,
            }
        except Exception as exc:
            self._logger.error("Error creando proyecto: %s", exc)
            raise BackendCoreBusinessError(
                f"Error creando proyecto: {exc}"
            ) from exc

    def update_project(
        self, project_id: int, update_data: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Actualiza un proyecto existente en MariaDB.

        El trigger tr_proyecto_flujo_update registra cambios automáticamente.
        """
        if not update_data:
            raise BackendCoreBusinessError("No hay datos para actualizar")

        self._logger.info(
            "[%s] Actualizando proyecto: project_id=%s data=%s",
            headers.get("X-Client-App", "unknown"),
            project_id,
            update_data,
        )

        try:
            updated = self._update_project_in_db(project_id, update_data)
            return {"updated": updated, "project_id": project_id}
        except Exception as exc:
            self._logger.error("Error actualizando proyecto: %s", exc)
            raise BackendCoreBusinessError(
                f"Error actualizando proyecto: {exc}"
            ) from exc

    def delete_project(
        self, project_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Elimina un proyecto de MariaDB.

        El trigger tr_proyecto_before_delete registra el borrado.
        """
        self._logger.info(
            "[%s] Eliminando proyecto: project_id=%s",
            headers.get("X-Client-App", "unknown"),
            project_id,
        )

        try:
            deleted = self._delete_project_in_db(project_id)
            return {"deleted": deleted, "project_id": project_id}
        except Exception as exc:
            self._logger.error("Error eliminando proyecto: %s", exc)
            raise BackendCoreBusinessError(
                f"Error eliminando proyecto: {exc}"
            ) from exc

    def request_project_support(
        self,
        project_id: int,
        tipo_cambio: str,
        descripcion: str,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Registra una solicitud de soporte para un proyecto.

        Usa el procedimiento sp_registrar_cambio_proyecto.
        """
        self._logger.info(
            "[%s] Solicitud de soporte: project_id=%s tipo=%s",
            headers.get("X-Client-App", "unknown"),
            project_id,
            tipo_cambio,
        )

        try:
            cambio_id = self._register_project_change(
                project_id, tipo_cambio, descripcion
            )
            return {"success": True, "cambio_id": cambio_id}
        except Exception as exc:
            self._logger.error("Error registrando soporte: %s", exc)
            raise BackendCoreBusinessError(
                f"Error registrando solicitud de soporte: {exc}"
            ) from exc

    # ========================================================================
    # Métodos privados de acceso a BD (myllm_projects_db)
    # ========================================================================

    def _get_projects_db_connection(self):
        """Obtiene conexión de LECTURA a la base de datos de proyectos."""
        from urllib.parse import quote_plus
        from sqlalchemy import create_engine

        settings = load_mariadb_settings()
        host = settings.get("host", "localhost")
        port = settings.get("port", "3306")
        user = settings.get("reader_user", "")
        password = quote_plus(settings.get("reader_password", ""))
        database = settings.get("projects_database", "myllm_projects_db")

        dsn = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(dsn)
        return engine.connect()

    def _get_projects_db_writer_connection(self):
        """Obtiene conexión de ESCRITURA a la base de datos de proyectos."""
        from urllib.parse import quote_plus
        from sqlalchemy import create_engine

        settings = load_mariadb_settings()
        host = settings.get("host", "localhost")
        port = settings.get("port", "3306")
        user = settings.get("writer_user", "")
        password = quote_plus(settings.get("writer_password", ""))
        database = settings.get("projects_database", "myllm_projects_db")

        dsn = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(dsn)
        return engine.connect()

    def _get_projects_from_db(
        self, organization_id: int, include_deleted: bool = False
    ) -> list[dict[str, Any]]:
        """Consulta proyectos de una organización desde MariaDB.
        
        Args:
            organization_id: ID de la organización
            include_deleted: Si True, incluye proyectos con existe=false
        """
        from sqlalchemy import text

        # Filtro de existencia: por defecto solo proyectos existentes
        existe_filter = "" if include_deleted else "AND COALESCE(p.existe, 1) = 1"

        with self._get_projects_db_connection() as conn:
            result = conn.execute(
                text(f"""
                    SELECT 
                        p.id,
                        p.nombre,
                        COALESCE(p.descripcion, '') as descripcion,
                        p.id_organizacion,
                        COALESCE(p.active, 1) as active,
                        COALESCE(p.id_flujo, 1) as id_flujo,
                        f.nombre as flujo_nombre,
                        f.emoji as flujo_emoji,
                        COALESCE(p.existe, 1) as existe
                    FROM proyectos p
                    LEFT JOIN flujos f ON p.id_flujo = f.id_flujo
                    WHERE p.id_organizacion = :org_id {existe_filter}
                    ORDER BY p.nombre
                """),
                {"org_id": organization_id},
            )
            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "nombre": row[1],
                    "descripcion": row[2],
                    "id_organizacion": row[3],
                    "active": bool(row[4]),
                    "id_flujo": row[5],
                    "flujo_nombre": row[6],
                    "flujo_emoji": row[7],
                    "existe": bool(row[8]),
                }
                for row in rows
            ]

    def _insert_project_in_db(
        self,
        nombre: str,
        descripcion: str,
        id_organizacion: int,
        active: bool,
        id_flujo: int,
    ) -> int:
        """Inserta un proyecto en MariaDB y retorna el ID."""
        from urllib.parse import quote_plus
        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        host = settings.get("host", "localhost")
        port = settings.get("port", "3306")
        user = settings.get("writer_user", "")
        password = quote_plus(settings.get("writer_password", ""))
        database = settings.get("projects_database", "myllm_projects_db")

        dsn = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(dsn)

        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO proyectos (nombre, descripcion, id_organizacion, active, id_flujo)
                    VALUES (:nombre, :descripcion, :id_organizacion, :active, :id_flujo)
                """),
                {
                    "nombre": nombre,
                    "descripcion": descripcion,
                    "id_organizacion": id_organizacion,
                    "active": 1 if active else 0,
                    "id_flujo": id_flujo,
                },
            )
            conn.commit()
            return result.lastrowid

    def _update_project_in_db(
        self, project_id: int, update_data: dict[str, Any]
    ) -> bool:
        """Actualiza un proyecto en MariaDB."""
        from urllib.parse import quote_plus
        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        host = settings.get("host", "localhost")
        port = settings.get("port", "3306")
        user = settings.get("writer_user", "")
        password = quote_plus(settings.get("writer_password", ""))
        database = settings.get("projects_database", "myllm_projects_db")

        dsn = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(dsn)

        # Construir SET clause dinámicamente
        set_clauses = []
        params = {"project_id": project_id}

        if "nombre" in update_data:
            set_clauses.append("nombre = :nombre")
            params["nombre"] = update_data["nombre"]
        if "descripcion" in update_data:
            set_clauses.append("descripcion = :descripcion")
            params["descripcion"] = update_data["descripcion"]
        if "active" in update_data:
            set_clauses.append("active = :active")
            params["active"] = 1 if update_data["active"] else 0
        if "id_flujo" in update_data:
            set_clauses.append("id_flujo = :id_flujo")
            params["id_flujo"] = update_data["id_flujo"]
        if "existe" in update_data:
            set_clauses.append("existe = :existe")
            params["existe"] = 1 if update_data["existe"] else 0

        if not set_clauses:
            return False

        sql = f"UPDATE proyectos SET {', '.join(set_clauses)} WHERE id = :project_id"

        with engine.connect() as conn:
            result = conn.execute(text(sql), params)
            conn.commit()
            return result.rowcount > 0

    def _delete_project_in_db(self, project_id: int) -> bool:
        """Elimina un proyecto de MariaDB."""
        from urllib.parse import quote_plus
        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        host = settings.get("host", "localhost")
        port = settings.get("port", "3306")
        user = settings.get("writer_user", "")
        password = quote_plus(settings.get("writer_password", ""))
        database = settings.get("projects_database", "myllm_projects_db")

        dsn = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(dsn)

        with engine.connect() as conn:
            result = conn.execute(
                text("DELETE FROM proyectos WHERE id = :project_id"),
                {"project_id": project_id},
            )
            conn.commit()
            return result.rowcount > 0

    def _register_project_change(
        self, project_id: int, tipo_cambio: str, descripcion: str
    ) -> int | None:
        """Registra un cambio de proyecto usando el procedimiento almacenado."""
        from urllib.parse import quote_plus
        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        host = settings.get("host", "localhost")
        port = settings.get("port", "3306")
        user = settings.get("writer_user", "")
        password = quote_plus(settings.get("writer_password", ""))
        database = settings.get("projects_database", "myllm_projects_db")

        dsn = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(dsn)

        with engine.connect() as conn:
            # Obtener id_organizacion del proyecto
            result = conn.execute(
                text("SELECT id_organizacion FROM proyectos WHERE id = :pid"),
                {"pid": project_id},
            )
            row = result.fetchone()
            if not row:
                raise BackendCoreBusinessError(f"Proyecto {project_id} no encontrado")

            id_organizacion = row[0]

            # Llamar al procedimiento almacenado
            conn.execute(
                text("""
                    CALL sp_registrar_cambio_proyecto(
                        :p_id_proyecto,
                        :p_id_organizacion,
                        :p_tipo_cambio,
                        :p_descripcion,
                        :p_id_usuario
                    )
                """),
                {
                    "p_id_proyecto": project_id,
                    "p_id_organizacion": id_organizacion,
                    "p_tipo_cambio": tipo_cambio,
                    "p_descripcion": descripcion,
                    "p_id_usuario": 0,  # Usuario del sistema
                },
            )
            conn.commit()
            return None  # El SP no retorna el ID directamente

    # ========================================================================
    # GESTIÓN DE ROLES DE USUARIO EN PROYECTOS
    # ========================================================================

    def get_project_roles_base(self) -> list[dict[str, Any]]:
        """Obtiene el catálogo maestro de roles base para proyectos.

        Consulta la tabla proyectos_roles_base que contiene los roles
        disponibles para asignar a usuarios en proyectos.

        Returns:
            Lista de diccionarios con id, nombre_rol y descripcion
        """
        from sqlalchemy import text

        self._logger.info("[backend-core] Consultando catálogo de roles base")

        with self._get_projects_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT 
                        id,
                        nombre_rol,
                        COALESCE(descripcion, '') as descripcion
                    FROM proyectos_roles_base
                    ORDER BY 
                        CASE id 
                            WHEN 0 THEN 1
                            WHEN 3 THEN 2
                            WHEN 4 THEN 3
                            WHEN 5 THEN 4
                        END
                """)
            )

            roles = [
                {
                    "id": row[0],
                    "nombre_rol": row[1],
                    "descripcion": row[2],
                }
                for row in result.fetchall()
            ]

            self._logger.info(
                "[backend-core] Roles base obtenidos: %d", len(roles)
            )
            return roles

    def get_user_project_roles(
        self, user_id: int, organization_id: int
    ) -> list[dict[str, Any]]:
        """Obtiene los roles de un usuario en proyectos de una organización.

        Consulta proyectos_roles JOIN proyectos para obtener nombres.

        Args:
            user_id: ID del usuario
            organization_id: ID de la organización

        Returns:
            Lista de diccionarios con los roles del usuario
        """
        from sqlalchemy import text

        self._logger.info(
            "[backend-core] Consultando roles de usuario %s en org %s",
            user_id,
            organization_id,
        )

        with self._get_projects_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT 
                        pr.id,
                        pr.id_usuario,
                        pr.id_proyecto,
                        pr.id_organizacion,
                        pr.id_rol,
                        CASE pr.id_rol
                            WHEN 3 THEN 'Editor'
                            WHEN 4 THEN 'Lector'
                            WHEN 5 THEN 'Auditor'
                            ELSE 'Sin Asignar'
                        END as rol_nombre,
                        p.nombre as proyecto_nombre,
                        COALESCE(pr.active, 1) as active
                    FROM proyectos_roles pr
                    INNER JOIN proyectos p ON pr.id_proyecto = p.id
                    WHERE pr.id_usuario = :user_id
                      AND pr.id_organizacion = :org_id
                    ORDER BY p.nombre
                """),
                {"user_id": user_id, "org_id": organization_id},
            )
            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "id_usuario": row[1],
                    "id_proyecto": row[2],
                    "id_organizacion": row[3],
                    "id_rol": row[4],
                    "rol_nombre": row[5],
                    "proyecto_nombre": row[6],
                    "active": bool(row[7]),
                }
                for row in rows
            ]

    def assign_user_to_project(
        self,
        id_usuario: int,
        id_proyecto: int,
        id_organizacion: int,
        id_rol: int,
    ) -> dict[str, Any]:
        """Asigna un usuario a un proyecto con un rol específico.

        Si existe registro: actualiza id_rol y active=1
        Si no existe: crea nuevo registro

        Registra cambio en tabla cambios.

        Args:
            id_usuario: ID del usuario a asignar
            id_proyecto: ID del proyecto
            id_organizacion: ID de la organización
            id_rol: ID del rol (3=Editor, 4=Lector, 5=Auditor)

        Returns:
            Diccionario con resultado de la operación
        """
        from sqlalchemy import text

        # Validar rol
        if id_rol not in (3, 4, 5):
            raise BackendCoreBusinessError(
                f"Rol inválido: {id_rol}. Valores válidos: 3=Editor, 4=Lector, 5=Auditor"
            )

        self._logger.info(
            "[backend-core] Asignando usuario %s a proyecto %s con rol %s",
            id_usuario,
            id_proyecto,
            id_rol,
        )

        with self._get_projects_db_writer_connection() as conn:
            # Verificar si ya existe registro
            existing = conn.execute(
                text("""
                    SELECT id, id_rol, active 
                    FROM proyectos_roles 
                    WHERE id_usuario = :user_id 
                      AND id_proyecto = :project_id 
                      AND id_organizacion = :org_id
                """),
                {
                    "user_id": id_usuario,
                    "project_id": id_proyecto,
                    "org_id": id_organizacion,
                },
            ).fetchone()

            created = False
            if existing:
                # Actualizar registro existente
                conn.execute(
                    text("""
                        UPDATE proyectos_roles 
                        SET id_rol = :id_rol, 
                            active = 1
                        WHERE id_usuario = :user_id 
                          AND id_proyecto = :project_id 
                          AND id_organizacion = :org_id
                    """),
                    {
                        "id_rol": id_rol,
                        "user_id": id_usuario,
                        "project_id": id_proyecto,
                        "org_id": id_organizacion,
                    },
                )
                self._logger.info(
                    "[backend-core] Actualizado rol existente para usuario %s",
                    id_usuario,
                )
            else:
                # Crear nuevo registro
                conn.execute(
                    text("""
                        INSERT INTO proyectos_roles 
                            (id_usuario, id_proyecto, id_organizacion, id_rol, active)
                        VALUES 
                            (:user_id, :project_id, :org_id, :id_rol, 1)
                    """),
                    {
                        "user_id": id_usuario,
                        "project_id": id_proyecto,
                        "org_id": id_organizacion,
                        "id_rol": id_rol,
                    },
                )
                created = True
                self._logger.info(
                    "[backend-core] Creado nuevo rol para usuario %s",
                    id_usuario,
                )

            # Registrar cambio en tabla cambios
            rol_nombre = {3: "Editor", 4: "Lector", 5: "Auditor"}.get(id_rol, "Desconocido")
            conn.execute(
                text("""
                    CALL sp_registrar_cambio_proyecto(
                        :p_id_proyecto,
                        :p_id_organizacion,
                        :p_tipo_cambio,
                        :p_descripcion,
                        :p_id_usuario
                    )
                """),
                {
                    "p_id_proyecto": id_proyecto,
                    "p_id_organizacion": id_organizacion,
                    "p_tipo_cambio": "Asignación usuario",
                    "p_descripcion": f"Usuario {id_usuario} asignado como {rol_nombre}",
                    "p_id_usuario": id_usuario,
                },
            )

            conn.commit()

            return {
                "success": True,
                "message": "Usuario asignado correctamente",
                "id_usuario": id_usuario,
                "id_proyecto": id_proyecto,
                "id_rol": id_rol,
                "created": created,
            }

    def remove_user_from_project(
        self,
        id_usuario: int,
        id_proyecto: int,
        id_organizacion: int,
    ) -> dict[str, Any]:
        """Quita un usuario de un proyecto (desactiva la asignación).

        Busca el registro y pone active=0.
        Registra cambio en tabla cambios.

        Args:
            id_usuario: ID del usuario a quitar
            id_proyecto: ID del proyecto
            id_organizacion: ID de la organización

        Returns:
            Diccionario con resultado de la operación
        """
        from sqlalchemy import text

        self._logger.info(
            "[backend-core] Quitando usuario %s de proyecto %s",
            id_usuario,
            id_proyecto,
        )

        with self._get_projects_db_writer_connection() as conn:
            # Verificar si existe el registro
            existing = conn.execute(
                text("""
                    SELECT id, id_rol 
                    FROM proyectos_roles 
                    WHERE id_usuario = :user_id 
                      AND id_proyecto = :project_id 
                      AND id_organizacion = :org_id
                """),
                {
                    "user_id": id_usuario,
                    "project_id": id_proyecto,
                    "org_id": id_organizacion,
                },
            ).fetchone()

            if not existing:
                raise BackendCoreBusinessError(
                    f"No existe asignación del usuario {id_usuario} "
                    f"al proyecto {id_proyecto}"
                )

            # Desactivar registro
            conn.execute(
                text("""
                    UPDATE proyectos_roles 
                    SET active = 0
                    WHERE id_usuario = :user_id 
                      AND id_proyecto = :project_id 
                      AND id_organizacion = :org_id
                """),
                {
                    "user_id": id_usuario,
                    "project_id": id_proyecto,
                    "org_id": id_organizacion,
                },
            )

            # Registrar cambio en tabla cambios
            conn.execute(
                text("""
                    CALL sp_registrar_cambio_proyecto(
                        :p_id_proyecto,
                        :p_id_organizacion,
                        :p_tipo_cambio,
                        :p_descripcion,
                        :p_id_usuario
                    )
                """),
                {
                    "p_id_proyecto": id_proyecto,
                    "p_id_organizacion": id_organizacion,
                    "p_tipo_cambio": "Quitar usuario",
                    "p_descripcion": f"Usuario {id_usuario} quitado del proyecto",
                    "p_id_usuario": id_usuario,
                },
            )

            conn.commit()

            self._logger.info(
                "[backend-core] Usuario %s quitado de proyecto %s",
                id_usuario,
                id_proyecto,
            )

            return {
                "success": True,
                "message": "Usuario quitado del proyecto",
                "id_usuario": id_usuario,
                "id_proyecto": id_proyecto,
            }

    # ========================================================================
    # GESTIÓN DE TICKETS DE SOPORTE
    # ========================================================================

    def create_ticket(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Crea un nuevo ticket de soporte.

        Crea registro en tickets + ticket_interacciones + cambios.

        Args:
            payload: {titulo, consulta, id_organizacion, id_proyecto?}
            headers: Headers de seguridad

        Returns:
            {success: True, ticket_id: int, mensaje: str}
        """
        titulo = payload.get("titulo", "").strip()
        consulta = payload.get("consulta", "").strip()
        id_organizacion = int(payload.get("id_organizacion", 0))
        id_proyecto = payload.get("id_proyecto")
        cliente_id = int(payload.get("cliente_id", 0))

        if not titulo:
            raise BackendCoreBusinessError("El motivo del ticket es obligatorio")
        if not consulta:
            raise BackendCoreBusinessError("La consulta es obligatoria")
        if id_organizacion <= 0:
            raise BackendCoreBusinessError("ID de organización inválido")
        if cliente_id <= 0:
            raise BackendCoreBusinessError("No se pudo identificar al usuario")

        self._logger.info(
            "[%s] Creando ticket: titulo=%s org_id=%s cliente_id=%s",
            headers.get("X-Client-App", "unknown"),
            titulo,
            id_organizacion,
            cliente_id,
        )

        try:
            ticket_id = self._create_ticket_in_db(
                titulo, consulta, cliente_id, id_organizacion, id_proyecto
            )
            return {
                "success": True,
                "ticket_id": ticket_id,
                "mensaje": "Ticket creado correctamente",
            }
        except Exception as exc:
            self._logger.error("Error creando ticket: %s", exc)
            raise BackendCoreBusinessError(f"Error creando ticket: {exc}") from exc

    def _create_ticket_in_db(
        self,
        titulo: str,
        consulta: str,
        cliente_id: int,
        id_organizacion: int,
        id_proyecto: int | None,
    ) -> int:
        """Inserta ticket y primera interacción en MariaDB."""
        from sqlalchemy import text

        with self._get_projects_db_writer_connection() as conn:
            # Insertar ticket con organización y proyecto
            result = conn.execute(
                text("""
                    INSERT INTO tickets (titulo, cliente_id, id_organizacion, id_proyecto, estado, prioridad)
                    VALUES (:titulo, :cliente_id, :id_organizacion, :id_proyecto, 'abierto', 'media')
                """),
                {
                    "titulo": titulo,
                    "cliente_id": cliente_id,
                    "id_organizacion": id_organizacion,
                    "id_proyecto": id_proyecto,
                },
            )
            ticket_id = result.lastrowid

            # Insertar primera interacción
            conn.execute(
                text("""
                    INSERT INTO ticket_interacciones 
                    (ticket_id, autor_consulta_id, consulta)
                    VALUES (:ticket_id, :autor_id, :consulta)
                """),
                {
                    "ticket_id": ticket_id,
                    "autor_id": cliente_id,
                    "consulta": consulta,
                },
            )

            # Registrar cambio solo si hay proyecto asociado
            if id_proyecto:
                conn.execute(
                    text("""
                        CALL sp_registrar_cambio_proyecto(
                            :p_id_proyecto,
                            :p_id_organizacion,
                            :p_tipo_cambio,
                            :p_descripcion,
                            :p_id_usuario
                        )
                    """),
                    {
                        "p_id_proyecto": id_proyecto,
                        "p_id_organizacion": id_organizacion,
                        "p_tipo_cambio": "Solicitud soporte proyecto",
                        "p_descripcion": f"Ticket #{ticket_id}: {titulo[:50]}",
                        "p_id_usuario": cliente_id,
                    },
                )

            conn.commit()
            return ticket_id

    def get_organization_tickets(
        self, organization_id: int, headers: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Obtiene los tickets de una organización."""
        self._logger.info(
            "[%s] Consultando tickets org_id=%s",
            headers.get("X-Client-App", "unknown"),
            organization_id,
        )

        try:
            return self._get_tickets_from_db(organization_id)
        except Exception as exc:
            self._logger.error("Error obteniendo tickets: %s", exc)
            raise BackendCoreBusinessError(f"Error consultando tickets: {exc}") from exc

    def _get_tickets_from_db(self, organization_id: int) -> list[dict[str, Any]]:
        """Consulta tickets con sus interacciones desde MariaDB."""
        from sqlalchemy import text

        with self._get_projects_db_connection() as conn:
            # Obtener tickets con primera interacción filtrados por organización
            result = conn.execute(
                text("""
                    SELECT 
                        t.id,
                        t.titulo,
                        t.cliente_id,
                        t.estado,
                        t.prioridad,
                        t.fecha_creacion,
                        t.fecha_actualizacion,
                        ti.consulta,
                        ti.respuesta,
                        ti.autor_consulta_id,
                        ti.autor_respuesta_id,
                        ti.fecha_consulta,
                        ti.fecha_respuesta,
                        t.id_proyecto,
                        t.id_organizacion
                    FROM tickets t
                    LEFT JOIN ticket_interacciones ti ON t.id = ti.ticket_id
                    WHERE t.id_organizacion = :org_id
                    ORDER BY t.fecha_creacion DESC
                """),
                {"org_id": organization_id},
            )
            rows = result.fetchall()

            return [
                {
                    "id": row[0],
                    "titulo": row[1],
                    "cliente_id": row[2],
                    "estado": row[3],
                    "prioridad": row[4],
                    "fecha_creacion": str(row[5]) if row[5] else None,
                    "fecha_actualizacion": str(row[6]) if row[6] else None,
                    "consulta": row[7],
                    "respuesta": row[8],
                    "autor_consulta_id": row[9],
                    "autor_respuesta_id": row[10],
                    "fecha_consulta": str(row[11]) if row[11] else None,
                    "fecha_respuesta": str(row[12]) if row[12] else None,
                    "id_proyecto": row[13],
                    "id_organizacion": row[14],
                }
                for row in rows
            ]

    def get_ticket_detail(
        self, ticket_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Obtiene el detalle de un ticket específico."""
        self._logger.info(
            "[%s] Consultando ticket_id=%s",
            headers.get("X-Client-App", "unknown"),
            ticket_id,
        )

        try:
            return self._get_ticket_detail_from_db(ticket_id)
        except Exception as exc:
            self._logger.error("Error obteniendo ticket: %s", exc)
            raise BackendCoreBusinessError(f"Error consultando ticket: {exc}") from exc

    def _get_ticket_detail_from_db(self, ticket_id: int) -> dict[str, Any]:
        """Consulta detalle de un ticket desde MariaDB."""
        from sqlalchemy import text

        with self._get_projects_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT 
                        t.id,
                        t.titulo,
                        t.cliente_id,
                        t.estado,
                        t.prioridad,
                        t.fecha_creacion,
                        t.fecha_actualizacion,
                        ti.consulta,
                        ti.respuesta,
                        ti.autor_consulta_id,
                        ti.autor_respuesta_id,
                        ti.fecha_consulta,
                        ti.fecha_respuesta
                    FROM tickets t
                    LEFT JOIN ticket_interacciones ti ON t.id = ti.ticket_id
                    WHERE t.id = :ticket_id
                """),
                {"ticket_id": ticket_id},
            )
            row = result.fetchone()

            if not row:
                raise BackendCoreBusinessError(f"Ticket {ticket_id} no encontrado")

            return {
                "id": row[0],
                "titulo": row[1],
                "cliente_id": row[2],
                "estado": row[3],
                "prioridad": row[4],
                "fecha_creacion": str(row[5]) if row[5] else None,
                "fecha_actualizacion": str(row[6]) if row[6] else None,
                "consulta": row[7],
                "respuesta": row[8],
                "autor_consulta_id": row[9],
                "autor_respuesta_id": row[10],
                "fecha_consulta": str(row[11]) if row[11] else None,
                "fecha_respuesta": str(row[12]) if row[12] else None,
            }

    def update_ticket(
        self, ticket_id: int, update_data: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Actualiza estado/prioridad de un ticket."""
        if not update_data:
            raise BackendCoreBusinessError("No hay datos para actualizar")

        self._logger.info(
            "[%s] Actualizando ticket_id=%s data=%s",
            headers.get("X-Client-App", "unknown"),
            ticket_id,
            update_data,
        )

        try:
            updated = self._update_ticket_in_db(ticket_id, update_data, headers)
            return {"success": True, "updated": updated, "ticket_id": ticket_id}
        except Exception as exc:
            self._logger.error("Error actualizando ticket: %s", exc)
            raise BackendCoreBusinessError(f"Error actualizando ticket: {exc}") from exc

    def _update_ticket_in_db(
        self, ticket_id: int, update_data: dict[str, Any], headers: dict[str, str]
    ) -> bool:
        """Actualiza un ticket en MariaDB."""
        from sqlalchemy import text

        set_clauses = []
        params = {"ticket_id": ticket_id}

        if "estado" in update_data:
            set_clauses.append("estado = :estado")
            params["estado"] = update_data["estado"]
        if "prioridad" in update_data:
            set_clauses.append("prioridad = :prioridad")
            params["prioridad"] = update_data["prioridad"]

        if not set_clauses:
            return False

        with self._get_projects_db_writer_connection() as conn:
            # Obtener organización y proyecto del ticket para el registro de cambios
            ticket_result = conn.execute(
                text("""
                    SELECT t.id_organizacion, t.id_proyecto
                    FROM tickets t
                    WHERE t.id = :ticket_id
                """),
                {"ticket_id": ticket_id},
            )
            ticket_row = ticket_result.fetchone()
            id_organizacion = ticket_row[0] if ticket_row else 0
            id_proyecto = ticket_row[1] if ticket_row and ticket_row[1] else None

            sql = f"UPDATE tickets SET {', '.join(set_clauses)} WHERE id = :ticket_id"
            result = conn.execute(text(sql), params)

            # Registrar cambio solo si hay proyecto asociado
            user_id = int(update_data.get("user_id", 0))
            if id_proyecto:
                descripcion_parts = []
                if "estado" in update_data:
                    descripcion_parts.append(f"estado → {update_data['estado']}")
                if "prioridad" in update_data:
                    descripcion_parts.append(f"prioridad → {update_data['prioridad']}")

                conn.execute(
                    text("""
                        CALL sp_registrar_cambio_proyecto(
                            :p_id_proyecto,
                            :p_id_organizacion,
                            :p_tipo_cambio,
                            :p_descripcion,
                            :p_id_usuario
                        )
                    """),
                    {
                        "p_id_proyecto": id_proyecto,
                        "p_id_organizacion": id_organizacion,
                        "p_tipo_cambio": "Actualización soporte proyecto",
                        "p_descripcion": f"Ticket #{ticket_id}: {', '.join(descripcion_parts)}",
                        "p_id_usuario": user_id,
                    },
                )

            conn.commit()
            return result.rowcount > 0

    def add_ticket_response(
        self, ticket_id: int, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Añade respuesta a un ticket."""
        respuesta = payload.get("respuesta", "").strip()
        user_id = int(payload.get("user_id", 0))

        if not respuesta:
            raise BackendCoreBusinessError("La respuesta no puede estar vacía")
        if user_id <= 0:
            raise BackendCoreBusinessError("No se pudo identificar al usuario")

        self._logger.info(
            "[%s] Añadiendo respuesta a ticket_id=%s user_id=%s",
            headers.get("X-Client-App", "unknown"),
            ticket_id,
            user_id,
        )

        try:
            updated = self._add_response_in_db(ticket_id, respuesta, user_id)
            return {"success": True, "updated": updated, "ticket_id": ticket_id}
        except Exception as exc:
            self._logger.error("Error añadiendo respuesta: %s", exc)
            raise BackendCoreBusinessError(f"Error añadiendo respuesta: {exc}") from exc

    def _add_response_in_db(
        self, ticket_id: int, respuesta: str, user_id: int
    ) -> bool:
        """Actualiza la respuesta en ticket_interacciones."""
        from sqlalchemy import text

        autor_respuesta_id = user_id

        with self._get_projects_db_writer_connection() as conn:
            # Obtener organización y proyecto del ticket
            ticket_result = conn.execute(
                text("""
                    SELECT t.id_organizacion, t.id_proyecto
                    FROM tickets t
                    WHERE t.id = :ticket_id
                """),
                {"ticket_id": ticket_id},
            )
            ticket_row = ticket_result.fetchone()
            id_organizacion = ticket_row[0] if ticket_row else 0
            id_proyecto = ticket_row[1] if ticket_row and ticket_row[1] else None

            # Actualizar la primera interacción del ticket
            result = conn.execute(
                text("""
                    UPDATE ticket_interacciones 
                    SET respuesta = :respuesta,
                        autor_respuesta_id = :autor_id,
                        fecha_respuesta = NOW()
                    WHERE ticket_id = :ticket_id
                    LIMIT 1
                """),
                {
                    "respuesta": respuesta,
                    "autor_id": autor_respuesta_id,
                    "ticket_id": ticket_id,
                },
            )

            # Registrar cambio solo si hay proyecto asociado
            if id_proyecto:
                conn.execute(
                    text("""
                        CALL sp_registrar_cambio_proyecto(
                            :p_id_proyecto,
                            :p_id_organizacion,
                            :p_tipo_cambio,
                            :p_descripcion,
                            :p_id_usuario
                        )
                    """),
                    {
                        "p_id_proyecto": id_proyecto,
                        "p_id_organizacion": id_organizacion,
                        "p_tipo_cambio": "Respuesta soporte proyecto",
                        "p_descripcion": f"Respuesta a ticket #{ticket_id}",
                        "p_id_usuario": autor_respuesta_id,
                    },
                )

            conn.commit()
            return result.rowcount > 0

    def _extract_user_id_from_headers(self, headers: dict[str, str]) -> int:
        """Extrae user_id del token JWT en los headers."""
        import jwt

        auth_header = headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return 0

        token = auth_header[7:]
        try:
            # Decodificar sin verificar para extraer el user_id
            payload = jwt.decode(token, options={"verify_signature": False})
            return int(payload.get("user_id", 0))
        except Exception:
            return 0

    # ========================================================================
    # GESTIÓN DE TECNOLOGÍAS
    # ========================================================================

    def get_tecnologias(self) -> dict[str, Any]:
        """Obtiene todas las tecnologías disponibles."""
        from sqlalchemy import text

        self._logger.info("[backend-core] Consultando tecnologías")

        with self._get_projects_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT id, name, descripcion, active
                    FROM tecnologia
                    ORDER BY name
                """)
            )
            rows = result.fetchall()

            tecnologias = [
                {
                    "id": row[0],
                    "name": row[1],
                    "descripcion": row[2],
                    "active": bool(row[3]),
                }
                for row in rows
            ]

            return {"tecnologias": tecnologias, "total": len(tecnologias)}

    def get_proyecto_tecnologia(self, project_id: int) -> dict[str, Any]:
        """Obtiene la tecnología asignada a un proyecto."""
        from sqlalchemy import text

        self._logger.info("[backend-core] Consultando tecnología de proyecto %s", project_id)

        with self._get_projects_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT pt.id, pt.id_proyecto, pt.id_tecnologia, pt.coste_base, t.name
                    FROM proyectos_tecnologia pt
                    JOIN tecnologia t ON pt.id_tecnologia = t.id
                    WHERE pt.id_proyecto = :project_id
                """),
                {"project_id": project_id},
            )
            row = result.fetchone()

            if row:
                return {
                    "success": True,
                    "asignacion": {
                        "id": row[0],
                        "id_proyecto": row[1],
                        "id_tecnologia": row[2],
                        "coste_base": row[3],
                        "tecnologia_name": row[4],
                    },
                }
            return {"success": True, "asignacion": None}

    def asignar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Asigna una tecnología a un proyecto (primera asignación)."""
        from sqlalchemy import text

        id_tecnologia = int(payload.get("id_tecnologia", 0))
        coste_base = payload.get("coste_base", "17% sobre base")

        if id_tecnologia <= 0:
            raise BackendCoreBusinessError("ID de tecnología inválido")

        self._logger.info(
            "[backend-core] Asignando tecnología %s a proyecto %s",
            id_tecnologia,
            project_id,
        )

        with self._get_projects_db_writer_connection() as conn:
            # Verificar que no exista ya una asignación
            existing = conn.execute(
                text("SELECT id FROM proyectos_tecnologia WHERE id_proyecto = :pid"),
                {"pid": project_id},
            ).fetchone()

            if existing:
                raise BackendCoreBusinessError(
                    "El proyecto ya tiene una tecnología asignada"
                )

            # Insertar asignación
            result = conn.execute(
                text("""
                    INSERT INTO proyectos_tecnologia (id_proyecto, id_tecnologia, coste_base)
                    VALUES (:pid, :tid, :coste)
                """),
                {"pid": project_id, "tid": id_tecnologia, "coste": coste_base},
            )
            conn.commit()

            # Obtener el registro creado
            return self.get_proyecto_tecnologia(project_id)

    def actualizar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza la tecnología de un proyecto (solo Backoffice)."""
        from sqlalchemy import text

        id_tecnologia = int(payload.get("id_tecnologia", 0))
        coste_base = payload.get("coste_base", "17% sobre base")

        if id_tecnologia <= 0:
            raise BackendCoreBusinessError("ID de tecnología inválido")

        self._logger.info(
            "[backend-core] Actualizando tecnología de proyecto %s a %s",
            project_id,
            id_tecnologia,
        )

        with self._get_projects_db_writer_connection() as conn:
            # Verificar si existe
            existing = conn.execute(
                text("SELECT id FROM proyectos_tecnologia WHERE id_proyecto = :pid"),
                {"pid": project_id},
            ).fetchone()

            if existing:
                # Actualizar
                conn.execute(
                    text("""
                        UPDATE proyectos_tecnologia 
                        SET id_tecnologia = :tid, coste_base = :coste
                        WHERE id_proyecto = :pid
                    """),
                    {"pid": project_id, "tid": id_tecnologia, "coste": coste_base},
                )
            else:
                # Insertar nuevo
                conn.execute(
                    text("""
                        INSERT INTO proyectos_tecnologia (id_proyecto, id_tecnologia, coste_base)
                        VALUES (:pid, :tid, :coste)
                    """),
                    {"pid": project_id, "tid": id_tecnologia, "coste": coste_base},
                )

            conn.commit()
            return self.get_proyecto_tecnologia(project_id)

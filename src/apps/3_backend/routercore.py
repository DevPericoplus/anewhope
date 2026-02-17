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

    def get_user_role(self, user_id: int) -> int | None:
        """Obtiene el identity_type_id de un usuario por su ID."""
        users = self.list_users()
        user = next((u for u in users if u.user_id == user_id), None)
        return user.identity_type_id if user else None

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
        self, user_id: int, active: bool, requester_org_id: int, requester_identity_type_id: int = 0
    ) -> dict[str, Any]:
        """Actualiza el estado activo/inactivo de un usuario en MariaDB.

        Este es el destino final del flujo:
        Frontend → Middleware → Broker → Backend Core (aquí) → MariaDB

        Args:
            user_id: ID del usuario a modificar
            active: True para habilitar, False para deshabilitar
            requester_org_id: ID de la organización del solicitante (para validación)
            requester_identity_type_id: Tipo de identidad del solicitante (1=SuperAdmin)

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

        # Validar permisos: SuperAdmin (identity_type_id=1) puede modificar cualquier usuario
        # Otros usuarios solo pueden modificar usuarios de su misma organización
        if requester_identity_type_id != 1 and target_user.organization_id != requester_org_id:
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
        """Crea un nuevo proyecto en MariaDB con su infraestructura inicial.

        Flujo completo:
        1. Crea el proyecto en la tabla proyectos
        2. Crea automáticamente la versión v001 en tabla versiones
        3. Crea la estructura de carpetas v001 en fmanagement (ORG.../PRJ.../v001/)
        4. Crea el estado inicial de la versión

        El trigger tr_proyecto_after_insert crea automáticamente:
        - Registro en tabla estado (versión 1)
        - Registro en tabla cambios (tipo "Alta proyecto")
        """
        nombre = payload.get("nombre", "").strip()
        descripcion = payload.get("descripcion", "").strip()
        id_organizacion = int(payload.get("id_organizacion", 0))
        active = payload.get("active", True)
        id_flujo = int(payload.get("id_flujo", 1))

        # Extraer información del usuario (necesaria para crear v001)
        user_id = int(headers.get("X-User-ID", 1))
        identity_type_id = int(headers.get("X-Identity-Type-ID", 1))

        if not nombre:
            raise BackendCoreBusinessError("El nombre del proyecto es obligatorio")
        if id_organizacion <= 0:
            raise BackendCoreBusinessError("ID de organización inválido")

        self._logger.info(
            "[%s] Creando proyecto con infraestructura: nombre=%s org_id=%s user_id=%s",
            headers.get("X-Client-App", "unknown"),
            nombre,
            id_organizacion,
            user_id,
        )

        try:
            # PASO 1: Crear registro del proyecto en base de datos
            project_id = self._insert_project_in_db(
                nombre, descripcion, id_organizacion, active, id_flujo
            )

            self._logger.info(
                "[backend-core] Proyecto creado con ID=%s. Creando v001...",
                project_id,
            )

            # PASO 2: Crear versión v001 con estructura completa en fmanagement
            try:
                version_result = self.create_version_full(
                    project_id=project_id,
                    org_id=id_organizacion,
                    user_id=user_id,
                    identity_type_id=identity_type_id,
                    descripcion="Versión inicial del proyecto",
                    clone_from_version=None,  # v001 siempre se crea vacía
                )

                self._logger.info(
                    "[backend-core] Versión v001 creada para proyecto %s",
                    project_id,
                )

                return {
                    "success": True,
                    "project_id": project_id,
                    "nombre": nombre,
                    "id_organizacion": id_organizacion,
                    "id_flujo": id_flujo,
                    "version": version_result,  # Información de v001 creada
                }

            except Exception as version_exc:
                self._logger.error(
                    "[backend-core] Error creando v001 para proyecto %s: %s",
                    project_id,
                    version_exc,
                )
                # El proyecto ya fue creado, así que devolvemos un warning
                return {
                    "success": True,
                    "project_id": project_id,
                    "nombre": nombre,
                    "id_organizacion": id_organizacion,
                    "id_flujo": id_flujo,
                    "warning": f"Proyecto creado pero error en v001: {version_exc}",
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

            # Registrar cambio SIEMPRE (con o sin proyecto)
            tipo_cambio = "Solicitud soporte proyecto" if id_proyecto else "Solicitud soporte organización"
            descripcion = f"Ticket #{ticket_id}: {titulo[:50]}"

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
                    "p_id_proyecto": id_proyecto,  # Puede ser NULL
                    "p_id_organizacion": id_organizacion,
                    "p_tipo_cambio": tipo_cambio,
                    "p_descripcion": descripcion,
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

    def get_tecnologias_asignadas_org(self, org_id: int) -> dict[str, Any]:
        """Obtiene todas las tecnologías asignadas a proyectos de una organización.
        
        Args:
            org_id: ID de la organización
            
        Returns:
            Dict con lista de proyectos y sus tecnologías asignadas
        """
        from sqlalchemy import text

        self._logger.info(
            "[backend-core] Consultando tecnologías asignadas para organización %s",
            org_id,
        )

        with self._get_projects_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT p.id, p.nombre, t.id, t.name
                    FROM proyectos p
                    LEFT JOIN proyectos_tecnologia pt ON p.id = pt.id_proyecto
                    LEFT JOIN tecnologia t ON pt.id_tecnologia = t.id
                    WHERE p.id_organizacion = :org_id AND p.existe = 1
                    ORDER BY p.nombre
                """),
                {"org_id": org_id},
            )
            rows = result.fetchall()

            asignaciones = [
                {
                    "project_id": row[0],
                    "project_name": row[1],
                    "tecnologia_id": row[2],
                    "tecnologia_name": row[3],
                }
                for row in rows
            ]

            return {"asignaciones": asignaciones, "total": len(asignaciones)}

    # ========================================================================
    # Gestión de Versiones
    # ========================================================================

    def get_project_versions(self, project_id: int, org_id: int) -> dict[str, Any]:
        """Obtiene todas las versiones de un proyecto.
        
        Args:
            project_id: ID del proyecto
            org_id: ID de la organización (para validar pertenencia)
            
        Returns:
            Dict con lista de versiones del proyecto
        """
        from sqlalchemy import text

        self._logger.info(
            "[backend-core] Consultando versiones proyecto=%s org=%s",
            project_id,
            org_id,
        )

        with self._get_projects_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT id_version, id_proyecto, id_organizacion
                    FROM versiones
                    WHERE id_proyecto = :project_id 
                      AND id_organizacion = :org_id
                    ORDER BY id_version
                """),
                {"project_id": project_id, "org_id": org_id},
            )
            rows = result.fetchall()

            versiones = [
                {
                    "id_version": row[0],
                    "id_proyecto": row[1],
                    "id_organizacion": row[2],
                    "version_folder": f"v{row[0]:03d}",
                }
                for row in rows
            ]

            return {"versiones": versiones, "total": len(versiones)}

    def create_project_version(self, project_id: int, org_id: int) -> dict[str, Any]:
        """Crea una nueva versión para un proyecto.
        
        La versión se crea con el siguiente id_version disponible para ese proyecto.
        
        Args:
            project_id: ID del proyecto
            org_id: ID de la organización
            
        Returns:
            Dict con la versión creada
        """
        from sqlalchemy import text

        self._logger.info(
            "[backend-core] Creando versión proyecto=%s org=%s",
            project_id,
            org_id,
        )

        with self._get_projects_db_writer_connection() as conn:
            # Obtener el siguiente id_version para este proyecto
            result = conn.execute(
                text("""
                    SELECT COALESCE(MAX(id_version), 0) + 1 as next_version
                    FROM versiones
                    WHERE id_proyecto = :project_id AND id_organizacion = :org_id
                """),
                {"project_id": project_id, "org_id": org_id},
            )
            row = result.fetchone()
            next_version = row[0] if row else 1

            # Insertar la nueva versión
            conn.execute(
                text("""
                    INSERT INTO versiones (id_version, id_proyecto, id_organizacion, fecha_lanzamiento, descripcion)
                    VALUES (:id_version, :project_id, :org_id, CURDATE(), :descripcion)
                """),
                {
                    "id_version": next_version,
                    "project_id": project_id,
                    "org_id": org_id,
                    "descripcion": description,
                },
            )
            conn.commit()

            self._logger.info(
                "[backend-core] Versión %s creada para proyecto %s",
                next_version,
                project_id,
            )

            return {
                "success": True,
                "version": {
                    "id_version": next_version,
                    "id_proyecto": project_id,
                    "id_organizacion": org_id,
                    "version_folder": f"v{next_version:03d}",
                },
                "mensaje": f"Versión {next_version} creada correctamente",
            }

    # ===================================================================
    # GESTIÓN DE ESTADOS DE VERSIÓN
    # ===================================================================

    def get_version_state(
        self, project_id: int, version_id: int, org_id: int
    ) -> dict[str, Any]:
        """Obtiene el estado actual de una versión.
        
        Args:
            project_id: ID del proyecto
            version_id: Número de versión
            org_id: ID de la organización
            
        Returns:
            Dict con el estado de la versión
        """
        from sqlalchemy import text

        self._logger.info(
            "[backend-core] Consultando estado versión=%s proyecto=%s org=%s",
            version_id,
            project_id,
            org_id,
        )

        with self._get_projects_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        id, id_organizacion, id_proyecto, id_version,
                        state, protected, size_bytes, final_c, final_i,
                        created_at, updated_at
                    FROM version_states
                    WHERE id_proyecto = :project_id
                      AND id_version = :version_id
                      AND id_organizacion = :org_id
                """),
                {
                    "project_id": project_id,
                    "version_id": version_id,
                    "org_id": org_id,
                },
            )
            row = result.fetchone()

            if not row:
                # Si no existe, retornar estado por defecto
                self._logger.warning(
                    "[backend-core] Estado no encontrado, retornando default"
                )
                return {
                    "success": False,
                    "message": "Estado de versión no encontrado",
                    "data": None,
                }

            state_data = {
                "id": row[0],
                "id_organizacion": row[1],
                "id_proyecto": row[2],
                "id_version": row[3],
                "state": row[4],
                "protected": bool(row[5]),
                "size": row[6],
                "final_c": bool(row[7]),
                "final_i": bool(row[8]),
                "created_at": row[9].isoformat() if row[9] else None,
                "updated_at": row[10].isoformat() if row[10] else None,
            }

            return {
                "success": True,
                "message": "Estado obtenido correctamente",
                "data": state_data,
            }

    def update_version_state(
        self,
        project_id: int,
        version_id: int,
        org_id: int,
        update_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Actualiza el estado de una versión.
        
        Args:
            project_id: ID del proyecto
            version_id: Número de versión
            org_id: ID de la organización
            update_data: Datos a actualizar (state, protected, final_c, final_i, size_bytes, user_id)
            
        Returns:
            Dict con el resultado de la actualización
        """
        from sqlalchemy import text

        user_id = update_data.get("user_id")
        
        self._logger.info(
            "[backend-core] Actualizando estado versión=%s proyecto=%s user=%s",
            version_id,
            project_id,
            user_id,
        )
        self._logger.info(
            "[backend-core] DEBUG update_data recibido: %s",
            update_data,
        )

        # Construir la query dinámica según campos presentes
        update_fields = []
        params = {
            "project_id": project_id,
            "version_id": version_id,
            "org_id": org_id,
            "user_id": user_id,
        }

        if "state" in update_data:
            update_fields.append("state = :state")
            params["state"] = update_data["state"]

        if "protected" in update_data:
            update_fields.append("protected = :protected")
            params["protected"] = update_data["protected"]

        if "final_c" in update_data:
            update_fields.append("final_c = :final_c")
            params["final_c"] = update_data["final_c"]

        if "final_i" in update_data:
            update_fields.append("final_i = :final_i")
            params["final_i"] = update_data["final_i"]

        if "size_bytes" in update_data:
            update_fields.append("size_bytes = :size_bytes")
            params["size_bytes"] = update_data["size_bytes"]

        if not update_fields:
            return {
                "success": False,
                "message": "No hay campos para actualizar",
                "data": None,
            }

        query = f"""
            UPDATE version_states
            SET {', '.join(update_fields)}
            WHERE id_proyecto = :project_id
              AND id_version = :version_id
              AND id_organizacion = :org_id
        """

        with self._get_projects_db_writer_connection() as conn:
            result = conn.execute(text(query), params)
            conn.commit()

            if result.rowcount == 0:
                self._logger.warning(
                    "[backend-core] Estado de versión no encontrado para actualizar"
                )
                return {
                    "success": False,
                    "message": "Estado de versión no encontrado",
                    "data": None,
                }

            self._logger.info(
                "[backend-core] Estado actualizado correctamente"
            )

            # Registrar cambio en tabla cambios con información de proyecto y versión
            if "state" in update_data:
                new_state = update_data["state"]

                # Obtener nombre del proyecto
                project_name_query = text("""
                    SELECT nombre FROM proyectos
                    WHERE id = :project_id AND id_organizacion = :org_id
                """)
                project_result = conn.execute(
                    project_name_query,
                    {"project_id": project_id, "org_id": org_id}
                ).fetchone()
                project_name = project_result[0] if project_result else f"Proyecto {project_id}"

                # Mapear estados a tipos y descripciones
                state_mapping = {
                    "Abierta": {
                        "tipo": "Abrir",
                        "descripcion": f"Versión v{version_id:03d} del proyecto '{project_name}' abierta para edición"
                    },
                    "Bloqueada": {
                        "tipo": "Bloquear",
                        "descripcion": f"Versión v{version_id:03d} del proyecto '{project_name}' bloqueada temporalmente"
                    },
                    "Entrenar": {
                        "tipo": "Entrenar",
                        "descripcion": f"El cliente solicita entrenamiento para versión v{version_id:03d} del proyecto '{project_name}'"
                    },
                    "Final": {
                        "tipo": "Finalizar",
                        "descripcion": f"Versión v{version_id:03d} del proyecto '{project_name}' lista para entrenar"
                    }
                }

                cambio_info = state_mapping.get(new_state, {
                    "tipo": "Cambio de Estado",
                    "descripcion": f"Estado de versión v{version_id:03d} del proyecto '{project_name}' cambiado a {new_state}"
                })

                # Obtener id de la versión en tabla versiones (no el número de versión)
                version_db_id_query = text("""
                    SELECT id FROM versiones
                    WHERE id_proyecto = :project_id
                      AND id_version = :version_id
                      AND id_organizacion = :org_id
                """)
                version_db_result = conn.execute(
                    version_db_id_query,
                    {"project_id": project_id, "version_id": version_id, "org_id": org_id}
                ).fetchone()
                version_db_id = version_db_result[0] if version_db_result else None

                if version_db_id:
                    # Insertar registro en tabla cambios
                    insert_cambio_query = text("""
                        INSERT INTO cambios (
                            id_organizacion, id_proyecto, id_version,
                            fecha_cambio, tipo_cambio, descripcion
                        ) VALUES (
                            :org_id, :project_id, :version_db_id,
                            CURDATE(),
                            :tipo_cambio,
                            :descripcion
                        )
                    """)
                    conn.execute(insert_cambio_query, {
                        "org_id": org_id,
                        "project_id": project_id,
                        "version_db_id": version_db_id,
                        "tipo_cambio": cambio_info["tipo"],
                        "descripcion": cambio_info["descripcion"]
                    })
                    conn.commit()

                    self._logger.info(
                        "[backend-core] Cambio registrado: tipo=%s proyecto=%s versión=%s",
                        cambio_info["tipo"],
                        project_name,
                        f"v{version_id:03d}"
                    )
                else:
                    self._logger.warning(
                        "[backend-core] No se encontró version_db_id para registrar cambio"
                    )

        # Retornar el estado actualizado
        return self.get_version_state(project_id, version_id, org_id)

    def create_version_state(
        self, project_id: int, version_id: int, org_id: int, user_id: int
    ) -> dict[str, Any]:
        """Crea un estado inicial para una versión nueva.
        
        Args:
            project_id: ID del proyecto
            version_id: Número de versión
            org_id: ID de la organización
            user_id: Usuario que crea el estado
            
        Returns:
            Dict con el estado creado
        """
        from sqlalchemy import text

        self._logger.info(
            "[backend-core] Creando estado versión=%s proyecto=%s",
            version_id,
            project_id,
        )

        with self._get_projects_db_writer_connection() as conn:
            conn.execute(
                text("""
                    INSERT INTO version_states (
                        id_organizacion, id_proyecto, id_version,
                        state, protected, size_bytes, final_c, final_i
                    ) VALUES (
                        :org_id, :project_id, :version_id,
                        'Abierta', FALSE, 0, FALSE, FALSE
                    )
                """),
                {
                    "org_id": org_id,
                    "project_id": project_id,
                    "version_id": version_id,
                },
            )
            conn.commit()

            self._logger.info(
                "[backend-core] Estado creado con éxito"
            )

        return self.get_version_state(project_id, version_id, org_id)

    def create_version_event(
        self, event_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Registra un evento de versión para auditoría.
        
        Args:
            event_data: Datos del evento (proyecto, versión, tipo, mensaje, user, etc)
            
        Returns:
            Dict con el resultado del registro
        """
        from sqlalchemy import text
        import json

        self._logger.info(
            "[backend-core] Registrando evento versión=%s proyecto=%s tipo=%s",
            event_data.get("id_version"),
            event_data.get("id_proyecto"),
            event_data.get("evento"),
        )

        metadata_json = None
        if "metadata" in event_data and event_data["metadata"]:
            metadata_json = json.dumps(event_data["metadata"])

        with self._get_projects_db_writer_connection() as conn:
            conn.execute(
                text("""
                    INSERT INTO version_events (
                        id_organizacion, id_proyecto, id_version,
                        evento, mensaje, user_id, user_name,
                        old_state, new_state, metadata
                    ) VALUES (
                        :org_id, :project_id, :version_id,
                        :evento, :mensaje, :user_id, :user_name,
                        :old_state, :new_state, :metadata
                    )
                """),
                {
                    "org_id": event_data.get("id_organizacion"),
                    "project_id": event_data.get("id_proyecto"),
                    "version_id": event_data.get("id_version"),
                    "evento": event_data.get("evento"),
                    "mensaje": event_data.get("mensaje"),
                    "user_id": event_data.get("user_id"),
                    "user_name": event_data.get("user_name"),
                    "old_state": event_data.get("old_state"),
                    "new_state": event_data.get("new_state"),
                    "metadata": metadata_json,
                },
            )
            conn.commit()

            self._logger.info(
                "[backend-core] Evento registrado correctamente"
            )

        return {
            "success": True,
            "message": "Evento registrado correctamente",
        }

    def get_version_events(
        self, project_id: int, version_id: int, org_id: int, limit: int = 50
    ) -> dict[str, Any]:
        """Obtiene el historial de eventos de una versión.
        
        Args:
            project_id: ID del proyecto
            version_id: Número de versión
            org_id: ID de la organización
            limit: Máximo número de eventos a retornar
            
        Returns:
            Dict con la lista de eventos
        """
        from sqlalchemy import text
        import json

        self._logger.info(
            "[backend-core] Consultando eventos versión=%s proyecto=%s",
            version_id,
            project_id,
        )

        with self._get_projects_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT 
                        id, id_organizacion, id_proyecto, id_version,
                        evento, mensaje, user_id, user_name,
                        old_state, new_state, metadata, timestamp
                    FROM version_events
                    WHERE id_proyecto = :project_id 
                      AND id_version = :version_id
                      AND id_organizacion = :org_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """),
                {
                    "project_id": project_id,
                    "version_id": version_id,
                    "org_id": org_id,
                    "limit": limit,
                },
            )
            rows = result.fetchall()

            events = []
            for row in rows:
                metadata = None
                if row[10]:  # metadata column
                    try:
                        metadata = json.loads(row[10])
                    except json.JSONDecodeError:
                        metadata = None

                events.append({
                    "id": row[0],
                    "id_organizacion": row[1],
                    "id_proyecto": row[2],
                    "id_version": row[3],
                    "evento": row[4],
                    "mensaje": row[5],
                    "user_id": row[6],
                    "user_name": row[7],
                    "old_state": row[8],
                    "new_state": row[9],
                    "metadata": metadata,
                    "timestamp": row[11].isoformat() if row[11] else None,
                })

            return {
                "success": True,
                "message": "Eventos obtenidos correctamente",
                "data": events,
                "total": len(events),
            }

    # ===================================================================
    # INTEGRACIÓN CON FMANAGEMENT
    # ===================================================================

    def fmanagement_list(
        self, org_folder: str, prj_folder: str, version_folder: str,
        user_id: int, identity_type_id: int
    ) -> dict[str, Any]:
        """Proxy para listar estructura de archivos vía fmanagement.
        
        Args:
            org_folder: Carpeta organización (ej: ORG00001)
            prj_folder: Carpeta proyecto (ej: PRJ0001)
            version_folder: Carpeta versión (ej: v001)
            user_id: ID del usuario
            identity_type_id: Tipo de identidad del usuario
            
        Returns:
            Dict con la estructura de archivos de fmanagement
        """
        self._logger.info(
            "[backend-core] Listando estructura fmanagement org=%s prj=%s version=%s",
            org_folder,
            prj_folder,
            version_folder,
        )

        try:
            # Importar cliente fmanagement
            from clients.fmanagement_client import FmanagementClient
            
            # Obtener configuración de fmanagement
            fmanagement_config = load_fmanagement_settings()
            base_url = fmanagement_config.base_url
            base_path = fmanagement_config.base_path

            # Expandir ~ en el basepath
            import os
            base_path = os.path.expanduser(base_path)

            client = FmanagementClient(base_url=base_url, logger=self._logger)

            result = client.list_structure(
                orgpath=org_folder,
                prjpath=prj_folder,
                versionpath=version_folder,
                iduser=user_id,
                basepath=base_path,
            )

            self._logger.info(
                "[backend-core] Resultado de fmanagement: %s",
                result
            )

            # Extraer items del resultado
            # El fmanagement devuelve un JSON con estructura jerárquica
            items = result.get("items", []) if isinstance(result, dict) else []

            self._logger.info(
                "[backend-core] Items extraídos: %d items",
                len(items)
            )

            return {
                "success": True,
                "items": items,
                "mensaje": "Estructura obtenida correctamente",
            }
            
        except Exception as e:
            self._logger.error(
                "[backend-core] Error listando estructura fmanagement: %s",
                str(e),
            )
            return {
                "success": False,
                "items": [],
                "mensaje": f"Error al obtener estructura: {str(e)}",
            }

    def fmanagement_operation(
        self, operation: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Ejecuta una operación genérica en fmanagement.
        
        Args:
            operation: Tipo de operación (create_folder, delete_file, etc)
            params: Parámetros de la operación
            
        Returns:
            Dict con el resultado de la operación
        """
        self._logger.info(
            "[backend-core] Operación fmanagement: %s",
            operation,
        )

        try:
            # Import using relative path since this is within 3_backend package
            import sys
            from pathlib import Path
            _backend_root = Path(__file__).parent
            sys.path.insert(0, str(_backend_root))
            from clients.fmanagement_client import FmanagementClient
            sys.path.pop(0)

            fmanagement_config = load_fmanagement_settings()
            base_url = fmanagement_config.base_url

            client = FmanagementClient(base_url=base_url, logger=self._logger)
            
            # Normalizar parámetros si vienen con nombres cortos
            params = params.copy()

            # Log params ANTES de transformación
            self._logger.info(f"[FMANAGEMENT] Params ANTES transformación: {params}")

            if "org" in params: params["orgpath"] = params.pop("org")
            if "prj" in params: params["prjpath"] = params.pop("prj")
            if "version" in params: params["versionpath"] = params.pop("version")
            if "user_id" in params: params["iduser"] = params.pop("user_id")
            if "id_user" in params: params["iduser"] = params.pop("id_user")

            # Log params DESPUÉS de transformación
            self._logger.info(f"[FMANAGEMENT] Params DESPUÉS transformación: {params}")

            # Subfolders y Extensiones
            if "file_path" in params:
                full_path = params.pop("file_path")
                if "." in full_path:
                    parts = full_path.rsplit(".", 1)
                    params["filename"] = parts[0]
                    params["extfile"] = parts[1]
                else:
                    params["filename"] = full_path

            # Eliminar 'operation' de params ya que los métodos específicos no lo necesitan
            params.pop("operation", None)

            # Mapear operación a método del cliente
            result = None
            if operation == "create_folder":
                result = client.create_folder(**params)
            elif operation == "rename_folder":
                result = client.rename_folder(**params)
            elif operation == "delete_folder":
                result = client.delete_folder(**params)
            elif operation == "create_file":
                result = client.create_file(**params)
            elif operation == "rename_file":
                result = client.rename_file(**params)
            elif operation == "delete_file":
                result = client.delete_file(**params)
            elif operation == "download_file" or operation == "read_file":
                result = client.download_file(**params)
            elif operation == "create_version":
                result = client.create_version(**params)
            elif operation == "get_properties":
                result = client.get_properties(**params)
            else:
                # Operación no soportada
                raise ValueError(f"Operación no soportada: {operation}")
            
            # Si el resultado es binario (download_file), lo devolvemos tal cual para apicore.py
            if isinstance(result, dict) and result.get("is_binary"):
                self._logger.info("[backend-core] Descarga de archivo detectada")
                return result

            return {
                "success": True,
                "message": f"Operación {operation} ejecutada correctamente",
                "data": result,
            }
            
        except Exception as e:
            self._logger.error(
                "[backend-core] Error en operación fmanagement: %s",
                str(e),
            )
            return {
                "success": False,
                "message": f"Error en operación: {str(e)}",
                "data": None,
            }

    def create_version_full(
        self,
        project_id: int,
        org_id: int,
        user_id: int,
        identity_type_id: int,
        descripcion: str | None = None,
        clone_from_version: int | None = None,
        access_token: str | None = None,
        session_token: str | None = None,
    ) -> dict[str, Any]:
        """Crea una nueva versión completa (DB + fmanagement).
        
        Este método es atómico: si falla cualquier paso, se hace rollback.
        
        Flujo:
        1. Calcular siguiente id_version
        2. Insertar en tabla versiones (DB)
        3. Crear carpeta física vía fmanagement
        4. Crear estado inicial en version_states
        5. Registrar evento VERSION_CREADA
        
        Args:
            project_id: ID del proyecto
            org_id: ID de la organización
            user_id: Usuario que crea la versión
            identity_type_id: Tipo de identidad del usuario
            descripcion: Descripción opcional de la versión
            clone_from_version: ID de versión a clonar (opcional)
            
        Returns:
            Dict con el resultado completo
        """
        from sqlalchemy import text

        # Cargar FmanagementClient usando importlib (evitar import relativo)
        _fmanagement_client_path = (
            Path(__file__).resolve().parent / "clients" / "fmanagement_client.py"
        )
        _spec = importlib.util.spec_from_file_location(
            "fmanagement_client_backend", _fmanagement_client_path
        )
        _fmanagement_module = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_fmanagement_module)
        FmanagementClient = _fmanagement_module.FmanagementClient

        self._logger.info(
            "[backend-core] Creando versión completa proyecto=%s org=%s user=%s",
            project_id,
            org_id,
            user_id,
        )

        # Obtener carpetas formateadas
        org_folder = f"ORG{org_id:05d}"
        prj_folder = f"PRJ{project_id:05d}"

        version_id = None
        version_folder = None
        fmanagement_created = False

        try:
            with self._get_projects_db_writer_connection() as conn:
                # PASO 1: Calcular siguiente id_version
                result = conn.execute(
                    text("""
                        SELECT COALESCE(MAX(id_version), 0) + 1 as next_version
                        FROM versiones
                        WHERE id_proyecto = :project_id AND id_organizacion = :org_id
                    """),
                    {"project_id": project_id, "org_id": org_id},
                )
                row = result.fetchone()
                version_id = row[0] if row else 1
                version_folder = f"v{version_id:03d}"

                self._logger.info(
                    "[backend-core] Siguiente versión calculada: %s",
                    version_id,
                )

                # PASO 2: Insertar en tabla versiones
                result_insert = conn.execute(
                    text("""
                        INSERT INTO versiones (id_version, id_proyecto, id_organizacion, fecha_lanzamiento, descripcion)
                        VALUES (:id_version, :project_id, :org_id, CURDATE(), :descripcion)
                    """),
                    {
                        "id_version": version_id,
                        "project_id": project_id,
                        "org_id": org_id,
                        "descripcion": descripcion,
                    },
                )

                # Obtener el ID autoincremental generado
                version_db_id = result_insert.lastrowid
                self._logger.info(
                    "[backend-core] Versión insertada en BD con id=%s, id_version=%s",
                    version_db_id,
                    version_id,
                )

                # PASO 3: Crear carpeta física vía fmanagement
                # Usar el cliente inyectado que ya tiene la configuración correcta
                client = self._get_fmanagement_client()

                # Determinar estrategia de creación:
                # - Si es v001: crear vacía con estructura base
                # - Si es v002+: clonar desde versión anterior (o la especificada)

                clone_from_folder = None
                if version_id == 1:
                    # Primera versión: crear estructura base vacía
                    self._logger.info(
                        "[backend-core] Creando v001 con estructura base vacía"
                    )
                    clone_from_folder = None
                elif clone_from_version:
                    # Clonar desde versión específica
                    clone_from_folder = f"v{clone_from_version:03d}"
                    self._logger.info(
                        "[backend-core] Clonando desde versión específica: %s",
                        clone_from_folder,
                    )
                else:
                    # Clonar desde versión anterior (automático)
                    previous_version_id = version_id - 1
                    clone_from_folder = f"v{previous_version_id:03d}"
                    self._logger.info(
                        "[backend-core] Clonando desde versión anterior: %s",
                        clone_from_folder,
                    )

                # Crear estructura en fmanagement
                try:
                    self._logger.info(
                        "[backend-core] Creando estructura en fmanagement: %s/%s/%s (clone_from=%s)",
                        org_folder,
                        prj_folder,
                        version_folder,
                        clone_from_folder,
                    )

                    # Llamar a fmanagement para crear la versión
                    fm_result = client.create_version(
                        orgpath=org_folder,
                        prjpath=prj_folder,
                        versionpath=version_folder,
                        identity_type_id=identity_type_id,
                        clone_from=clone_from_folder,
                        iduser=user_id,
                    )

                    self._logger.info(
                        "[backend-core] Resultado de fmanagement.create_version: %s",
                        fm_result
                    )

                    if fm_result.get("error"):
                        self._logger.error(
                            "[backend-core] Error en fmanagement: %s",
                            fm_result.get("error")
                        )
                        # No fallar la transacción, solo registrar el error
                        # La carpeta se creará con el script de sincronización
                        fmanagement_created = False
                    else:
                        self._logger.info(
                            "[backend-core] Estructura creada en fmanagement exitosamente"
                        )
                        fmanagement_created = True

                except Exception as e:
                    self._logger.error(
                        "[backend-core] Excepción al crear en fmanagement: %s",
                        str(e)
                    )
                    # No fallar la transacción, continuar
                    fmanagement_created = False
                    fm_result = {"error": str(e)}

                # PASO 4: Crear estado inicial en la tabla estado
                # NOTA: Los triggers trg_versiones_after_insert y trg_estado_version_after_insert
                # se encargan automáticamente de crear los registros en estado_version y estado.
                # Por lo tanto, NO necesitamos hacer INSERT manual aquí.
                self._logger.info(
                    "[backend-core] Estado inicial será creado automáticamente por triggers"
                )

                # PASO 5: Registrar cambio en la tabla cambios
                # IMPORTANTE: usar version_db_id (id autoincremental) no version_id (número de versión)
                conn.execute(
                    text("""
                        INSERT INTO cambios (
                            id_organizacion, id_proyecto, id_version,
                            fecha_cambio, tipo_cambio, descripcion
                        ) VALUES (
                            :org_id, :project_id, :version_db_id,
                            CURDATE(),
                            'VERSION_CREADA',
                            :descripcion
                        )
                    """),
                    {
                        "org_id": org_id,
                        "project_id": project_id,
                        "version_db_id": version_db_id,
                        "descripcion": f"Versión {version_folder} creada desde Proyecciones" +
                                 (f" (clonada desde v{clone_from_version:03d})" if clone_from_version else ""),
                    },
                )

                # Commit de toda la transacción
                conn.commit()

                self._logger.info(
                    "[backend-core] Versión %s creada exitosamente (version_db_id=%s)",
                    version_id,
                    version_db_id,
                )

                # Consultar la versión y estado creados para retornarlos completos
                self._logger.info("[backend-core] Consultando versión con id=%s", version_db_id)
                version_result = conn.execute(
                    text("""
                        SELECT id, id_proyecto, id_version, fecha_lanzamiento, descripcion,
                               creado_at, actualizado_at, id_organizacion
                        FROM versiones
                        WHERE id = :version_db_id
                    """),
                    {"version_db_id": version_db_id},
                )
                version_row = version_result.fetchone()
                self._logger.info("[backend-core] version_row obtenida: %s", version_row)

                self._logger.info("[backend-core] Consultando estado con id_version=%s (versiones.id)", version_db_id)
                estado_result = conn.execute(
                    text("""
                        SELECT id, id_organizacion, id_proyecto, id_version,
                               propuesta_cliente, revision_interna, propuesta_mejoras,
                               aceptacion_cliente, aceptacion_interna, entrenamiento_inicial,
                               evaluacion_entrenamiento, reentrenamiento, optimizacion,
                               aprobacion_calidad, generacion_llm, notificacion_descarga,
                               creado_at, actualizado_at
                        FROM estado
                        WHERE id_version = :version_db_id
                    """),
                    {"version_db_id": version_db_id},
                )
                estado_row = estado_result.fetchone()
                self._logger.info("[backend-core] estado_row obtenida: %s", estado_row)

                # Construir objetos de respuesta
                version_dict = None
                if version_row:
                    version_dict = {
                        "id": version_row[0],
                        "id_proyecto": version_row[1],
                        "id_version": version_row[2],
                        "fecha_lanzamiento": version_row[3].isoformat() if version_row[3] else None,
                        "descripcion": version_row[4],
                        "creado_at": version_row[5].isoformat() if version_row[5] else None,
                        "actualizado_at": version_row[6].isoformat() if version_row[6] else None,
                        "id_organizacion": version_row[7],
                    }

                estado_dict = None
                if estado_row:
                    estado_dict = {
                        "id": estado_row[0],
                        "id_organizacion": estado_row[1],
                        "id_proyecto": estado_row[2],
                        "id_version": estado_row[3],
                        "propuesta_cliente": bool(estado_row[4]),
                        "revision_interna": bool(estado_row[5]),
                        "propuesta_mejoras": bool(estado_row[6]),
                        "aceptacion_cliente": bool(estado_row[7]),
                        "aceptacion_interna": bool(estado_row[8]),
                        "entrenamiento_inicial": bool(estado_row[9]),
                        "evaluacion_entrenamiento": bool(estado_row[10]),
                        "reentrenamiento": bool(estado_row[11]),
                        "optimizacion": bool(estado_row[12]),
                        "aprobacion_calidad": bool(estado_row[13]),
                        "generacion_llm": bool(estado_row[14]),
                        "notificacion_descarga": bool(estado_row[15]),
                        "creado_at": estado_row[16].isoformat() if estado_row[16] else None,
                        "actualizado_at": estado_row[17].isoformat() if estado_row[17] else None,
                    }

                return {
                    "success": True,
                    "message": f"Versión {version_folder} creada correctamente",
                    "version_id": version_id,
                    "version_folder": version_folder,
                    "version": version_dict,
                    "state": estado_dict,
                    "fmanagement_result": fm_result,
                }

        except Exception as e:
            self._logger.error(
                "[backend-core] Error creando versión completa: %s",
                str(e),
            )
            
            # Si llegamos aquí, la transacción DB se hará rollback automáticamente
            # TODO: Considerar rollback físico de carpeta en fmanagement si fue creada
            
            return {
                "success": False,
                "message": f"Error al crear versión: {str(e)}",
                "version_id": None,
                "version_folder": None,
                "fmanagement_result": None,
            }

    # ========================================================================
    # ASSIGNMENTS MANAGER - Gestor de asignaciones (SuperAdmin only)
    # ========================================================================

    def _build_dsn(self, settings: dict, database: str) -> str:
        """Builds MariaDB DSN from settings."""
        from urllib.parse import quote_plus

        host = settings.get("host", "localhost")
        port = settings.get("port", 3306)
        user = settings.get("writer_user", "")
        password = quote_plus(settings.get("writer_password", ""))

        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

    def get_internal_users(self) -> list[dict[str, Any]]:
        """Gets internal users (training_create=true) for assignment selectors.

        Returns list of users with training permissions who can be assigned
        to organizations and projects.
        """
        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        database = settings.get("core_database", "myllm_core_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT u.user_id, u.user_name, u.user_email
                    FROM users u
                    INNER JOIN low_level_permissions llp
                        ON u.identity_type_id = llp.id_permissions
                    WHERE llp.training_create = TRUE
                      AND u.active = TRUE
                    ORDER BY u.user_name
                """)
            )
            return [
                {
                    "user_id": row.user_id,
                    "user_name": row.user_name,
                    "user_email": row.user_email,
                }
                for row in result
            ]

    def get_organization_assignments(
        self, organization_id: int, identity_type_id: int
    ) -> list[dict[str, Any]]:
        """Gets all assignments for an organization with user/role names.

        Security: Only SuperAdmin (identity_type_id=1) can access.
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError(
                "assignments_read", identity_type_id
            )

        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        aoi.id,
                        aoi.id_usuario_interno,
                        u.user_name,
                        aoi.id_organizacion,
                        o.organization_name,
                        aoi.id_rol,
                        COALESCE(r.identity_type_name, 'Unknown') as role_name,
                        aoi.activo
                    FROM asignaciones_organizaciones_internas aoi
                    INNER JOIN myllm_core_db.users u
                        ON aoi.id_usuario_interno = u.user_id
                    INNER JOIN myllm_core_db.organizations o
                        ON aoi.id_organizacion = o.organization_id
                    INNER JOIN myllm_core_db.roles r
                        ON aoi.id_rol = r.identity_type_id
                    WHERE aoi.id_organizacion = :org_id
                    ORDER BY u.user_name, r.identity_type_name
                """),
                {"org_id": organization_id},
            )
            return [
                {
                    "id": row.id,
                    "user_id": row.id_usuario_interno,
                    "user_name": row.user_name,
                    "organization_id": row.id_organizacion,
                    "organization_name": row.organization_name,
                    "role_id": row.id_rol,
                    "role_name": row.role_name,
                    "active": bool(row.activo),
                }
                for row in result
            ]

    def create_organization_assignment(
        self,
        user_id: int,
        organization_id: int,
        role_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Creates organization assignment for internal user.

        Security: Only SuperAdmin can create assignments.
        Validation: Prevents duplicates.
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError(
                "assignments_create", identity_type_id
            )

        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            # Check for duplicate
            existing = conn.execute(
                text("""
                    SELECT id FROM asignaciones_organizaciones_internas
                    WHERE id_usuario_interno = :user_id
                      AND id_organizacion = :org_id
                """),
                {"user_id": user_id, "org_id": organization_id},
            ).fetchone()

            if existing:
                raise BackendCoreBusinessError(
                    "El usuario ya tiene una asignación a esta organización"
                )

            # Insert (asignado_por is set to identity_type_id for now)
            result = conn.execute(
                text("""
                    INSERT INTO asignaciones_organizaciones_internas
                    (id_usuario_interno, id_organizacion, id_rol, activo, asignado_por)
                    VALUES (:user_id, :org_id, :role_id, 1, :assigned_by)
                """),
                {
                    "user_id": user_id,
                    "org_id": organization_id,
                    "role_id": role_id,
                    "assigned_by": identity_type_id,
                },
            )
            conn.commit()

            assignment_id = result.lastrowid

            self._logger.info(
                "[ASSIGNMENTS] Created org assignment: id=%s user=%s org=%s role=%s",
                assignment_id, user_id, organization_id, role_id,
            )

            return {
                "success": True,
                "assignment_id": assignment_id,
                "message": "Asignación creada exitosamente",
            }

    def update_organization_assignment(
        self,
        assignment_id: int,
        active: bool,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates active status of organization assignment (logical deletion).

        Security: Only SuperAdmin can update.
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError(
                "assignments_update", identity_type_id
            )

        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE asignaciones_organizaciones_internas
                    SET activo = :active
                    WHERE id = :assignment_id
                """),
                {"active": 1 if active else 0, "assignment_id": assignment_id},
            )
            conn.commit()

            if result.rowcount == 0:
                raise BackendCoreBusinessError("Asignación no encontrada")

            action = "habilitada" if active else "deshabilitada"
            self._logger.info(
                "[ASSIGNMENTS] Org assignment %s: id=%s", action, assignment_id
            )

            return {
                "success": True,
                "updated": True,
                "message": f"Asignación {action}",
            }

    def delete_organization_assignment(
        self,
        assignment_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Permanently deletes organization assignment (physical deletion).

        Security: Only SuperAdmin can delete.
        Warning: This is irreversible.
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError(
                "assignments_delete", identity_type_id
            )

        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    DELETE FROM asignaciones_organizaciones_internas
                    WHERE id = :assignment_id
                """),
                {"assignment_id": assignment_id},
            )
            conn.commit()

            if result.rowcount == 0:
                raise BackendCoreBusinessError("Asignación no encontrada")

            self._logger.warning(
                "[ASSIGNMENTS] Deleted org assignment: id=%s", assignment_id
            )

            return {
                "success": True,
                "deleted": True,
                "message": "Asignación eliminada permanentemente",
            }

    def validate_org_prerequisite(
        self,
        user_id: int,
        organization_id: int,
    ) -> dict[str, Any]:
        """Validates if user has active org role (prerequisite for project assignment).

        Returns validation result with details.
        """
        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, id_rol
                    FROM asignaciones_organizaciones_internas
                    WHERE id_usuario_interno = :user_id
                      AND id_organizacion = :org_id
                      AND activo = 1
                    LIMIT 1
                """),
                {"user_id": user_id, "org_id": organization_id},
            ).fetchone()

            if result:
                return {
                    "valid": True,
                    "message": "Usuario tiene rol activo en la organización",
                    "has_org_role": True,
                    "org_role_id": result.id_rol,
                }
            else:
                return {
                    "valid": False,
                    "message": "Usuario no tiene rol activo en la organización",
                    "has_org_role": False,
                    "org_role_id": None,
                }

    def get_project_assignments(
        self, project_id: int, identity_type_id: int
    ) -> list[dict[str, Any]]:
        """Gets all assignments for a project with user/role names.

        Security: Only SuperAdmin (identity_type_id=1) can access.
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError(
                "assignments_read", identity_type_id
            )

        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        pr.id,
                        pr.id_usuario,
                        u.user_name,
                        pr.id_organizacion,
                        o.organization_name,
                        pr.id_proyecto,
                        p.nombre as project_name,
                        pr.id_rol,
                        COALESCE(prb.nombre_rol, CONCAT('Rol ', pr.id_rol, ' (inválido)')) as role_name,
                        pr.active
                    FROM proyectos_roles pr
                    INNER JOIN myllm_core_db.users u
                        ON pr.id_usuario = u.user_id
                    INNER JOIN myllm_core_db.organizations o
                        ON pr.id_organizacion = o.organization_id
                    INNER JOIN proyectos p
                        ON pr.id_proyecto = p.id
                    LEFT JOIN proyectos_roles_base prb
                        ON pr.id_rol = prb.id
                    WHERE pr.id_proyecto = :project_id
                    ORDER BY u.user_name, COALESCE(prb.nombre_rol, '')
                """),
                {"project_id": project_id},
            )
            return [
                {
                    "id": row.id,
                    "user_id": row.id_usuario,
                    "user_name": row.user_name,
                    "organization_id": row.id_organizacion,
                    "organization_name": row.organization_name,
                    "project_id": row.id_proyecto,
                    "project_name": row.project_name,
                    "role_id": row.id_rol,
                    "role_name": row.role_name,
                    "active": bool(row.active),
                }
                for row in result
            ]

    def create_project_assignment(
        self,
        user_id: int,
        organization_id: int,
        project_id: int,
        role_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Creates project assignment for internal user.

        Security: Only SuperAdmin can create.
        Validation: Requires active org role (prerequisite).
        """
        self._logger.info(
            "[ASSIGNMENTS] create_project_assignment: user=%s org=%s project=%s role=%s identity=%s",
            user_id, organization_id, project_id, role_id, identity_type_id,
        )

        if identity_type_id != 1:
            raise BackendCorePermissionError(
                "assignments_create", identity_type_id
            )

        # Validate prerequisite
        prerequisite = self.validate_org_prerequisite(user_id, organization_id)
        if not prerequisite["has_org_role"]:
            self._logger.warning(
                "[ASSIGNMENTS] Prerequisite failed: user=%s has no active role in org=%s",
                user_id, organization_id,
            )
            raise BackendCoreBusinessError(
                "El usuario debe tener un rol activo en la organización antes de asignarlo a proyectos"
            )

        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            # Check for duplicate
            existing = conn.execute(
                text("""
                    SELECT pr.id, pr.id_rol, pr.active,
                           COALESCE(prb.nombre_rol, CONCAT('Rol ', pr.id_rol)) as role_name,
                           u.user_name
                    FROM proyectos_roles pr
                    LEFT JOIN proyectos_roles_base prb ON pr.id_rol = prb.id
                    LEFT JOIN myllm_core_db.users u ON pr.id_usuario = u.user_id
                    WHERE pr.id_usuario = :user_id
                      AND id_proyecto = :project_id
                """),
                {"user_id": user_id, "project_id": project_id},
            ).fetchone()

            if existing:
                self._logger.warning(
                    "[ASSIGNMENTS] Duplicate: user=%s (%s) already assigned to project=%s "
                    "(id=%s, role=%s, active=%s)",
                    user_id, existing.user_name, project_id,
                    existing.id, existing.role_name, existing.active,
                )
                raise BackendCoreBusinessError(
                    f"El usuario '{existing.user_name}' ya tiene una asignación a este proyecto "
                    f"(rol: {existing.role_name}, "
                    f"{'activa' if existing.active else 'inactiva'}, "
                    f"registro id={existing.id})"
                )

            # Insert
            result = conn.execute(
                text("""
                    INSERT INTO proyectos_roles
                    (id_usuario, id_organizacion, id_proyecto, id_rol, active)
                    VALUES (:user_id, :org_id, :project_id, :role_id, TRUE)
                """),
                {
                    "user_id": user_id,
                    "org_id": organization_id,
                    "project_id": project_id,
                    "role_id": role_id,
                },
            )
            conn.commit()

            assignment_id = result.lastrowid

            self._logger.info(
                "[ASSIGNMENTS] Created project assignment: id=%s user=%s project=%s role=%s",
                assignment_id, user_id, project_id, role_id,
            )

            return {
                "success": True,
                "assignment_id": assignment_id,
                "message": "Asignación de proyecto creada exitosamente",
            }

    def update_project_assignment(
        self,
        assignment_id: int,
        active: bool,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates active status of project assignment.

        Security: Only SuperAdmin can update.
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError(
                "assignments_update", identity_type_id
            )

        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE proyectos_roles
                    SET active = :active
                    WHERE id = :assignment_id
                """),
                {"active": 1 if active else 0, "assignment_id": assignment_id},
            )
            conn.commit()

            if result.rowcount == 0:
                raise BackendCoreBusinessError("Asignación no encontrada")

            action = "habilitada" if active else "deshabilitada"
            self._logger.info(
                "[ASSIGNMENTS] Project assignment %s: id=%s", action, assignment_id
            )

            return {
                "success": True,
                "updated": True,
                "message": f"Asignación {action}",
            }

    def delete_project_assignment(
        self,
        assignment_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Permanently deletes project assignment.

        Security: Only SuperAdmin can delete.
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError(
                "assignments_delete", identity_type_id
            )

        from sqlalchemy import create_engine, text

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    DELETE FROM proyectos_roles
                    WHERE id = :assignment_id
                """),
                {"assignment_id": assignment_id},
            )
            conn.commit()

            if result.rowcount == 0:
                raise BackendCoreBusinessError("Asignación no encontrada")

            self._logger.warning(
                "[ASSIGNMENTS] Deleted project assignment: id=%s", assignment_id
            )

            return {
                "success": True,
                "deleted": True,
                "message": "Asignación eliminada permanentemente",
            }

    # ========================================================================
    # PROMPTS MANAGEMENT - Gestión de Prompts (SuperAdmin only)
    # ========================================================================

    def _get_prompt_table(self, category: str) -> str:
        """Gets the table name for a prompt category.
        
        Args:
            category: One of 'identidades', 'contexto', 'solicitudes', 'modalidad'
            
        Returns:
            Table name
            
        Raises:
            BackendCoreBusinessError: If category is invalid
        """
        valid_categories = {
            "identidades": "prompts_identidades",
            "contexto": "prompts_contexto",
            "solicitudes": "prompts_solicitudes",
            "modalidad": "prompts_modalidad",
        }
        
        table = valid_categories.get(category)
        if not table:
            raise BackendCoreBusinessError(
                f"Categoría inválida: {category}. Debe ser una de: {', '.join(valid_categories.keys())}"
            )
        
        return table

    def get_prompts(
        self, category: str, identity_type_id: int
    ) -> list[dict[str, Any]]:
        """Gets all prompts from a category.
        
        Security: Only SuperAdmin (identity_type_id=1) can access.
        
        Args:
            category: Prompt category
            identity_type_id: User's identity type
            
        Returns:
            List of prompts with all fields
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError("prompts_read", identity_type_id)

        from sqlalchemy import create_engine, text

        table = self._get_prompt_table(category)
        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            result = conn.execute(
                text(f"""
                    SELECT 
                        id_prompt, name, description, prompt, active,
                        created_at, updated_at, created_by, updated_by
                    FROM {table}
                    ORDER BY active DESC, name ASC
                """)
            )
            return [
                {
                    "id_prompt": row.id_prompt,
                    "name": row.name,
                    "description": row.description,
                    "prompt": row.prompt,
                    "active": bool(row.active),
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    "created_by": row.created_by,
                    "updated_by": row.updated_by,
                }
                for row in result
            ]

    def get_prompt(
        self, category: str, id_prompt: int, identity_type_id: int
    ) -> dict[str, Any]:
        """Gets a specific prompt by ID.
        
        Security: Only SuperAdmin can access.
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError("prompts_read", identity_type_id)

        from sqlalchemy import create_engine, text

        table = self._get_prompt_table(category)
        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            result = conn.execute(
                text(f"""
                    SELECT 
                        id_prompt, name, description, prompt, active,
                        created_at, updated_at, created_by, updated_by
                    FROM {table}
                    WHERE id_prompt = :id_prompt
                """),
                {"id_prompt": id_prompt},
            ).fetchone()

            if not result:
                raise BackendCoreBusinessError(f"Prompt no encontrado: {id_prompt}")

            return {
                "id_prompt": result.id_prompt,
                "name": result.name,
                "description": result.description,
                "prompt": result.prompt,
                "active": bool(result.active),
                "created_at": result.created_at.isoformat() if result.created_at else None,
                "updated_at": result.updated_at.isoformat() if result.updated_at else None,
                "created_by": result.created_by,
                "updated_by": result.updated_by,
            }

    def create_prompt(
        self,
        category: str,
        name: str,
        description: str | None,
        prompt: str,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Creates a new prompt.
        
        Security: Only SuperAdmin can create.
        Validation: Name must be unique within category.
        Audit: Automatically sets created_by.
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError("prompts_create", identity_type_id)

        from sqlalchemy import create_engine, text

        table = self._get_prompt_table(category)
        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            # Check for duplicate name
            existing = conn.execute(
                text(f"SELECT id_prompt FROM {table} WHERE name = :name"),
                {"name": name},
            ).fetchone()

            if existing:
                raise BackendCoreBusinessError(
                    f"Ya existe un prompt con el nombre '{name}' en la categoría {category}"
                )

            # Insert new prompt
            result = conn.execute(
                text(f"""
                    INSERT INTO {table}
                    (name, description, prompt, active, created_by)
                    VALUES (:name, :description, :prompt, TRUE, :created_by)
                """),
                {
                    "name": name,
                    "description": description,
                    "prompt": prompt,
                    "created_by": user_id,
                },
            )
            conn.commit()

            prompt_id = result.lastrowid

            self._logger.info(
                "[PROMPTS] Created prompt: category=%s id=%s name=%s user=%s",
                category, prompt_id, name, user_id,
            )

            return {
                "success": True,
                "id_prompt": prompt_id,
                "message": f"Prompt '{name}' creado exitosamente",
            }

    def update_prompt(
        self,
        category: str,
        id_prompt: int,
        name: str,
        description: str | None,
        prompt: str,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates an existing prompt.
        
        Security: Only SuperAdmin can update.
        Validation: Name must be unique within category (excluding current prompt).
        Audit: Automatically sets updated_by and updated_at.
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError("prompts_update", identity_type_id)

        from sqlalchemy import create_engine, text

        table = self._get_prompt_table(category)
        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            # Check if prompt exists
            existing_prompt = conn.execute(
                text(f"SELECT id_prompt FROM {table} WHERE id_prompt = :id_prompt"),
                {"id_prompt": id_prompt},
            ).fetchone()

            if not existing_prompt:
                raise BackendCoreBusinessError(f"Prompt no encontrado: {id_prompt}")

            # Check for duplicate name (excluding current prompt)
            duplicate = conn.execute(
                text(f"""
                    SELECT id_prompt FROM {table}
                    WHERE name = :name AND id_prompt != :id_prompt
                """),
                {"name": name, "id_prompt": id_prompt},
            ).fetchone()

            if duplicate:
                raise BackendCoreBusinessError(
                    f"Ya existe otro prompt con el nombre '{name}' en la categoría {category}"
                )

            # Update prompt
            result = conn.execute(
                text(f"""
                    UPDATE {table}
                    SET name = :name,
                        description = :description,
                        prompt = :prompt,
                        updated_by = :updated_by
                    WHERE id_prompt = :id_prompt
                """),
                {
                    "name": name,
                    "description": description,
                    "prompt": prompt,
                    "updated_by": user_id,
                    "id_prompt": id_prompt,
                },
            )
            conn.commit()

            if result.rowcount == 0:
                raise BackendCoreBusinessError("Error al actualizar el prompt")

            self._logger.info(
                "[PROMPTS] Updated prompt: category=%s id=%s name=%s user=%s",
                category, id_prompt, name, user_id,
            )

            return {
                "success": True,
                "updated": True,
                "message": f"Prompt '{name}' actualizado exitosamente",
            }

    def toggle_prompt(
        self,
        category: str,
        id_prompt: int,
        active: bool,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Toggles prompt active status (enable/disable).
        
        Security: Only SuperAdmin can toggle.
        Audit: Automatically sets updated_by and updated_at.
        """
        if identity_type_id != 1:
            raise BackendCorePermissionError("prompts_update", identity_type_id)

        from sqlalchemy import create_engine, text

        table = self._get_prompt_table(category)
        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        engine = create_engine(dsn)
        with engine.connect() as conn:
            result = conn.execute(
                text(f"""
                    UPDATE {table}
                    SET active = :active,
                        updated_by = :updated_by
                    WHERE id_prompt = :id_prompt
                """),
                {
                    "active": 1 if active else 0,
                    "updated_by": user_id,
                    "id_prompt": id_prompt,
                },
            )
            conn.commit()

            if result.rowcount == 0:
                raise BackendCoreBusinessError("Prompt no encontrado")

            action = "habilitado" if active else "deshabilitado"
            self._logger.info(
                "[PROMPTS] Toggled prompt: category=%s id=%s action=%s user=%s",
                category, id_prompt, action, user_id,
            )

            return {
                "success": True,
                "updated": True,
                "message": f"Prompt {action} exitosamente",
            }

    # ========================================================================
    # PROJECT VERSION STATE - Estado de versiones de proyectos (DDD)
    # ========================================================================

    def get_project_version_state_by_id(
        self,
        state_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> dict[str, Any] | None:
        """Obtiene estado de versión por ID con validación de permisos.

        Args:
            state_id: ID del estado en estado_version
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Diccionario con datos del estado o None si no existe

        Raises:
            BackendCorePermissionError: Si no tiene permisos
        """
        from sqlalchemy import create_engine

        # Inicializar repositorio y servicio
        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)
        engine = create_engine(dsn)

        # Importar dinámicamente
        from src.shared_application.adapters.mariadb_project_version_state_repository import (
            MariaDBProjectVersionStateRepository,
        )
        from src.shared_application.services.project_version_state_service import (
            ProjectVersionStateService,
            PermissionDeniedError,
        )

        repository = MariaDBProjectVersionStateRepository(engine)
        service = ProjectVersionStateService(repository, engine)

        try:
            state = service.get_state_by_id(
                state_id,
                requesting_user_id,
                requesting_user_identity_type,
            )

            if state is None:
                return None

            return self._project_version_state_to_dict(state)

        except PermissionDeniedError as exc:
            raise BackendCorePermissionError(
                "project_version_state_read",
                requesting_user_identity_type,
            ) from exc

    def get_project_version_state_by_version(
        self,
        organization_id: int,
        project_id: int,
        version_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> dict[str, Any] | None:
        """Obtiene estado de una versión específica.

        Args:
            organization_id: ID de la organización
            project_id: ID del proyecto
            version_id: ID de la versión
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Diccionario con datos del estado o None si no existe
        """
        from sqlalchemy import create_engine
        from src.shared_application.adapters.mariadb_project_version_state_repository import (
            MariaDBProjectVersionStateRepository,
        )
        from src.shared_application.services.project_version_state_service import (
            ProjectVersionStateService,
            PermissionDeniedError,
        )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)
        engine = create_engine(dsn)

        repository = MariaDBProjectVersionStateRepository(engine)
        service = ProjectVersionStateService(repository, engine)

        try:
            state = service.get_state_by_version(
                organization_id,
                project_id,
                version_id,
                requesting_user_id,
                requesting_user_identity_type,
            )

            if state is None:
                return None

            return self._project_version_state_to_dict(state)

        except PermissionDeniedError as exc:
            raise BackendCorePermissionError(
                "project_version_state_read",
                requesting_user_identity_type,
            ) from exc

    def list_project_version_states_by_user(
        self,
        requesting_user_id: int,
        requesting_user_identity_type: int,
        organization_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Lista estados según asignaciones del usuario.

        Args:
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante
            organization_id: Filtrar por organización (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a saltar

        Returns:
            Lista de estados visibles para el usuario
        """
        from sqlalchemy import create_engine
        from src.shared_application.adapters.mariadb_project_version_state_repository import (
            MariaDBProjectVersionStateRepository,
        )
        from src.shared_application.services.project_version_state_service import (
            ProjectVersionStateService,
        )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)
        engine = create_engine(dsn)

        repository = MariaDBProjectVersionStateRepository(engine)
        service = ProjectVersionStateService(repository, engine)

        states = service.list_states_by_user(
            requesting_user_id,
            requesting_user_identity_type,
            organization_id,
            limit,
            offset,
        )

        return [self._project_version_state_to_dict(state) for state in states]

    def update_proposal_phase(
        self,
        state_id: int,
        aceptacion_cliente: bool,
        aceptacion_interna: bool,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> dict[str, Any]:
        """Actualiza fase de propuesta (aceptaciones).

        Args:
            state_id: ID del estado
            aceptacion_cliente: Estado de aceptación del cliente
            aceptacion_interna: Estado de aceptación interna
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Diccionario con resultado de la operación
        """
        from sqlalchemy import create_engine
        from src.shared_application.adapters.mariadb_project_version_state_repository import (
            MariaDBProjectVersionStateRepository,
        )
        from src.shared_application.services.project_version_state_service import (
            ProjectVersionStateService,
            PermissionDeniedError,
            NotFoundError,
        )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)
        engine = create_engine(dsn)

        repository = MariaDBProjectVersionStateRepository(engine)
        service = ProjectVersionStateService(repository, engine)

        try:
            # Determinar método según qué cambió
            state = repository.get_by_id(state_id)
            if state is None:
                raise BackendCoreBusinessError("Estado no encontrado")

            # Aplicar cambios según valores
            if aceptacion_cliente and not state.proposal.aceptacion_cliente:
                updated_state = service.approve_proposal_by_client(
                    state_id,
                    requesting_user_id,
                    requesting_user_identity_type,
                )
            elif not aceptacion_cliente and state.proposal.aceptacion_cliente:
                updated_state = service.revoke_client_approval(
                    state_id,
                    requesting_user_id,
                    requesting_user_identity_type,
                )
            elif aceptacion_interna and not state.proposal.aceptacion_interna:
                updated_state = service.approve_proposal_by_internal(
                    state_id,
                    requesting_user_id,
                    requesting_user_identity_type,
                )
            elif not aceptacion_interna and state.proposal.aceptacion_interna:
                updated_state = service.revoke_internal_approval(
                    state_id,
                    requesting_user_id,
                    requesting_user_identity_type,
                )
            else:
                # Sin cambios
                updated_state = state

            self._logger.info(
                "[PROJECT_VERSION_STATE] Updated proposal phase: state_id=%s user=%s",
                state_id,
                requesting_user_id,
            )

            return {
                "success": True,
                "state": self._project_version_state_to_dict(updated_state),
            }

        except PermissionDeniedError as exc:
            raise BackendCorePermissionError(
                "project_version_state_update",
                requesting_user_identity_type,
            ) from exc
        except NotFoundError as exc:
            raise BackendCoreBusinessError(str(exc)) from exc

    def update_training_phase(
        self,
        state_id: int,
        completado: bool,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> dict[str, Any]:
        """Actualiza fase de entrenamiento.

        Args:
            state_id: ID del estado
            completado: Si el entrenamiento está completado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Diccionario con resultado de la operación
        """
        from sqlalchemy import create_engine
        from src.shared_application.adapters.mariadb_project_version_state_repository import (
            MariaDBProjectVersionStateRepository,
        )
        from src.shared_application.services.project_version_state_service import (
            ProjectVersionStateService,
            PermissionDeniedError,
            NotFoundError,
        )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)
        engine = create_engine(dsn)

        repository = MariaDBProjectVersionStateRepository(engine)
        service = ProjectVersionStateService(repository, engine)

        try:
            if completado:
                updated_state = service.complete_training(
                    state_id,
                    requesting_user_id,
                    requesting_user_identity_type,
                )
            else:
                # Desmarcar completado (actualización directa)
                success = repository.update_training_phase(
                    state_id,
                    completado=False,
                    updated_by=requesting_user_id,
                )
                if not success:
                    raise BackendCoreBusinessError("No se pudo actualizar")

                updated_state = repository.get_by_id(state_id)

            self._logger.info(
                "[PROJECT_VERSION_STATE] Updated training phase: state_id=%s completed=%s user=%s",
                state_id,
                completado,
                requesting_user_id,
            )

            return {
                "success": True,
                "state": self._project_version_state_to_dict(updated_state) if updated_state else None,
            }

        except PermissionDeniedError as exc:
            raise BackendCorePermissionError(
                "project_version_state_update",
                requesting_user_identity_type,
            ) from exc
        except NotFoundError as exc:
            raise BackendCoreBusinessError(str(exc)) from exc

    def update_evaluation_phase(
        self,
        state_id: int,
        evaluacion: bool,
        reentrenamiento: bool,
        optimizacion: bool,
        calidad_aprobada: bool,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> dict[str, Any]:
        """Actualiza fase de evaluación/reentrenamiento.

        Args:
            state_id: ID del estado
            evaluacion: Si está en evaluación
            reentrenamiento: Si está en reentrenamiento
            optimizacion: Si está en optimización
            calidad_aprobada: Si pasó control de calidad
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Diccionario con resultado de la operación
        """
        from sqlalchemy import create_engine
        from src.shared_application.adapters.mariadb_project_version_state_repository import (
            MariaDBProjectVersionStateRepository,
        )
        from src.shared_application.services.project_version_state_service import (
            ProjectVersionStateService,
            PermissionDeniedError,
        )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)
        engine = create_engine(dsn)

        repository = MariaDBProjectVersionStateRepository(engine)
        service = ProjectVersionStateService(repository, engine)

        try:
            if calidad_aprobada:
                # Usar método del servicio para aprobación
                updated_state = service.approve_quality(
                    state_id,
                    requesting_user_id,
                    requesting_user_identity_type,
                )
            else:
                # Actualizar flags del bucle
                updated_state = service.update_evaluation_flags(
                    state_id,
                    evaluacion,
                    reentrenamiento,
                    optimizacion,
                    requesting_user_id,
                    requesting_user_identity_type,
                )

            self._logger.info(
                "[PROJECT_VERSION_STATE] Updated evaluation phase: state_id=%s user=%s",
                state_id,
                requesting_user_id,
            )

            return {
                "success": True,
                "state": self._project_version_state_to_dict(updated_state),
            }

        except PermissionDeniedError as exc:
            raise BackendCorePermissionError(
                "project_version_state_update",
                requesting_user_identity_type,
            ) from exc

    def update_generation_phase(
        self,
        state_id: int,
        solicitada: bool,
        completada: bool,
        ruta_fichero: str | None,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> dict[str, Any]:
        """Actualiza fase de generación LLM.

        Args:
            state_id: ID del estado
            solicitada: Si la generación fue solicitada
            completada: Si la generación está completada
            ruta_fichero: Ruta del fichero generado (required if completada=True)
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Diccionario con resultado de la operación
        """
        from sqlalchemy import create_engine
        from src.shared_application.adapters.mariadb_project_version_state_repository import (
            MariaDBProjectVersionStateRepository,
        )
        from src.shared_application.services.project_version_state_service import (
            ProjectVersionStateService,
            PermissionDeniedError,
        )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)
        engine = create_engine(dsn)

        repository = MariaDBProjectVersionStateRepository(engine)
        service = ProjectVersionStateService(repository, engine)

        try:
            state = repository.get_by_id(state_id)
            if state is None:
                raise BackendCoreBusinessError("Estado no encontrado")

            if solicitada and not state.generation.solicitada:
                # Solicitar generación
                updated_state = service.request_generation(
                    state_id,
                    requesting_user_id,
                    requesting_user_identity_type,
                )
            elif completada and not state.generation.completada:
                # Completar generación
                if not ruta_fichero:
                    raise BackendCoreBusinessError(
                        "Se requiere ruta_fichero para completar generación"
                    )
                updated_state = service.complete_generation(
                    state_id,
                    ruta_fichero,
                    requesting_user_id,
                    requesting_user_identity_type,
                )
            else:
                # Actualización directa
                success = repository.update_generation_phase(
                    state_id,
                    solicitada,
                    completada,
                    ruta_fichero,
                    requesting_user_id,
                )
                if not success:
                    raise BackendCoreBusinessError("No se pudo actualizar")
                updated_state = repository.get_by_id(state_id)

            self._logger.info(
                "[PROJECT_VERSION_STATE] Updated generation phase: state_id=%s user=%s",
                state_id,
                requesting_user_id,
            )

            return {
                "success": True,
                "state": self._project_version_state_to_dict(updated_state) if updated_state else None,
            }

        except PermissionDeniedError as exc:
            raise BackendCorePermissionError(
                "project_version_state_update",
                requesting_user_identity_type,
            ) from exc

    def update_notification_phase(
        self,
        state_id: int,
        enviada: bool,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> dict[str, Any]:
        """Actualiza fase de notificación.

        Args:
            state_id: ID del estado
            enviada: Si la notificación fue enviada
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Diccionario con resultado de la operación
        """
        from sqlalchemy import create_engine
        from src.shared_application.adapters.mariadb_project_version_state_repository import (
            MariaDBProjectVersionStateRepository,
        )
        from src.shared_application.services.project_version_state_service import (
            ProjectVersionStateService,
            PermissionDeniedError,
        )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)
        engine = create_engine(dsn)

        repository = MariaDBProjectVersionStateRepository(engine)
        service = ProjectVersionStateService(repository, engine)

        try:
            if enviada:
                updated_state = service.send_notification(
                    state_id,
                    requesting_user_id,
                    requesting_user_identity_type,
                )
            else:
                # Desmarcar notificación (actualización directa)
                success = repository.update_notification_phase(
                    state_id,
                    enviada=False,
                    updated_by=requesting_user_id,
                )
                if not success:
                    raise BackendCoreBusinessError("No se pudo actualizar")
                updated_state = repository.get_by_id(state_id)

            self._logger.info(
                "[PROJECT_VERSION_STATE] Updated notification phase: state_id=%s sent=%s user=%s",
                state_id,
                enviada,
                requesting_user_id,
            )

            return {
                "success": True,
                "state": self._project_version_state_to_dict(updated_state) if updated_state else None,
            }

        except PermissionDeniedError as exc:
            raise BackendCorePermissionError(
                "project_version_state_update",
                requesting_user_identity_type,
            ) from exc

    def _project_version_state_to_dict(self, state: Any) -> dict[str, Any]:
        """Convierte entidad ProjectVersionState a diccionario serializable.

        Args:
            state: Entidad ProjectVersionState

        Returns:
            Diccionario con todos los campos
        """
        return {
            "id": state.id,
            "organization_id": state.organization_id,
            "project_id": state.project_id,
            "version_id": state.version_id,
            "state": state.state.value,
            "state_internal": state.state_internal.value,
            "state_internal_display": state.state_internal.display_name,
            "protected": state.protected,
            "size": state.size,
            # Fase 1: Propuesta
            "proposal": {
                "propuesta_cliente": state.proposal.propuesta_cliente,
                "revision_interna": state.proposal.revision_interna,
                "propuesta_mejoras": state.proposal.propuesta_mejoras,
                "aceptacion_cliente": state.proposal.aceptacion_cliente,
                "aceptacion_interna": state.proposal.aceptacion_interna,
                "is_approved": state.proposal.is_approved,
            },
            # Fase 2: Entrenamiento
            "training": {
                "solicitado": state.training.solicitado,
                "completado": state.training.completado,
                "fecha_completado": (
                    state.training.fecha_completado.isoformat()
                    if state.training.fecha_completado
                    else None
                ),
                "is_completed": state.training.is_completed,
            },
            # Fase 3: Evaluación
            "evaluation": {
                "evaluacion_en_curso": state.evaluation.evaluacion_en_curso,
                "reentrenamiento_en_curso": state.evaluation.reentrenamiento_en_curso,
                "optimizacion_en_curso": state.evaluation.optimizacion_en_curso,
                "calidad_aprobada": state.evaluation.calidad_aprobada,
                "is_approved": state.evaluation.is_approved,
            },
            # Fase 4: Generación
            "generation": {
                "solicitada": state.generation.solicitada,
                "completada": state.generation.completada,
                "fecha_completado": (
                    state.generation.fecha_completado.isoformat()
                    if state.generation.fecha_completado
                    else None
                ),
                "ruta_fichero": state.generation.ruta_fichero,
                "is_completed": state.generation.is_completed,
            },
            # Fase 5: Notificación
            "notification": {
                "enviada": state.notification.enviada,
                "fecha_envio": (
                    state.notification.fecha_envio.isoformat()
                    if state.notification.fecha_envio
                    else None
                ),
                "is_sent": state.notification.is_sent,
            },
            # Metadatos y progreso
            "progress_percentage": state.progress_percentage,
            "current_phase_number": state.current_phase_number,
            "is_completed": state.is_completed,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
            "updated_by": state.updated_by,
        }

    # ========================================================================
    # Project Version State - Phase Updates
    # ========================================================================

    def update_proposal_phase(
        self,
        state_id: int,
        aceptacion_cliente: bool,
        aceptacion_interna: bool,
        user_id: int,
        identity_type_id: int,
        revision_interna: bool | None = None,
        propuesta_mejoras: bool | None = None,
    ) -> dict[str, Any]:
        """Actualiza fase de propuesta (aceptaciones cliente e interna).

        Args:
            state_id: ID del estado de versión
            aceptacion_cliente: Flag de aceptación del cliente
            aceptacion_interna: Flag de aceptación interna
            identity_type_id: Tipo de identidad del usuario
            user_id: ID del usuario que realiza la actualización
            revision_interna: Flag de revisión interna (opcional)
            propuesta_mejoras: Flag de propuesta de mejoras (opcional)

        Returns:
            Dict con success y mensaje
        """
        # Verificar permisos (solo SuperAdmin o con asignación)
        if identity_type_id not in (1, 2, 3):
            raise BackendCorePermissionError(
                "project_version_state_update", identity_type_id
            )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        from sqlalchemy import create_engine, text
        from datetime import datetime

        engine = create_engine(dsn)
        with engine.connect() as conn:
            # Determinar state y protected según las reglas del constraint
            # chk_state_protected: combinaciones válidas:
            #   Abierta    → protected=0, final_c=0, final_i=0
            #   Bloqueada  → protected=1, final_c=0, final_i=0
            #   Protegida  → protected=1, final_c=1, final_i=0
            #   Final      → protected=1, final_c=1, final_i=1
            # NOTA: final_i=1 sin final_c=1 no está permitido por el constraint.
            # Si se intenta, se rechaza con error de negocio claro.
            if aceptacion_cliente and aceptacion_interna:
                state = 'Final'
                protected = True
            elif aceptacion_cliente and not aceptacion_interna:
                state = 'Protegida'
                protected = True
            elif not aceptacion_cliente and aceptacion_interna:
                raise BackendCoreBusinessError(
                    "La aceptación interna requiere la aceptación del cliente primero"
                )
            else:
                state = 'Abierta'
                protected = False

            # Construir query dinámicamente según campos presentes
            set_clauses = [
                "final_c = :final_c",
                "final_i = :final_i",
                "state = :state",
                "protected = :protected",
                "updated_at = :updated_at",
                "updated_by = :updated_by",
            ]
            params = {
                "final_c": 1 if aceptacion_cliente else 0,
                "final_i": 1 if aceptacion_interna else 0,
                "state": state,
                "protected": 1 if protected else 0,
                "updated_at": datetime.now(),
                "updated_by": user_id,
                "state_id": state_id,
            }

            if revision_interna is not None:
                set_clauses.append("revision_interna = :revision_interna")
                params["revision_interna"] = 1 if revision_interna else 0

            if propuesta_mejoras is not None:
                set_clauses.append("propuesta_mejoras = :propuesta_mejoras")
                params["propuesta_mejoras"] = 1 if propuesta_mejoras else 0

            query = text(f"""
                UPDATE estado_version
                SET {", ".join(set_clauses)}
                WHERE id = :state_id
            """)

            result = conn.execute(query, params)
            conn.commit()

            if result.rowcount == 0:
                raise BackendCoreBusinessError("Estado de versión no encontrado")

            self._logger.info(
                "[ESTADO_VERSION] Fase propuesta actualizada: state_id=%s final_c=%s final_i=%s",
                state_id, aceptacion_cliente, aceptacion_interna
            )

            return {
                "success": True,
                "message": "Fase de propuesta actualizada correctamente",
            }

    def update_training_phase(
        self,
        state_id: int,
        completado: bool,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Actualiza fase de entrenamiento inicial.

        Args:
            state_id: ID del estado de versión
            completado: Flag de entrenamiento completado
            identity_type_id: Tipo de identidad del usuario
            user_id: ID del usuario que realiza la actualización

        Returns:
            Dict con success y mensaje
        """
        if identity_type_id not in (1, 2, 3):
            raise BackendCorePermissionError(
                "project_version_state_update", identity_type_id
            )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        from sqlalchemy import create_engine, text
        from datetime import datetime

        engine = create_engine(dsn)
        with engine.connect() as conn:
            # Si se marca como completado, actualizar también la fecha
            if completado:
                query = text("""
                    UPDATE estado_version
                    SET entrenamiento_inicial_completado = 1,
                        entrenamiento_inicial_fecha = :fecha,
                        updated_at = :updated_at,
                        updated_by = :updated_by
                    WHERE id = :state_id
                """)
                params = {
                    "fecha": datetime.now(),
                    "updated_at": datetime.now(),
                    "updated_by": user_id,
                    "state_id": state_id,
                }
            else:
                query = text("""
                    UPDATE estado_version
                    SET entrenamiento_inicial_completado = 0,
                        entrenamiento_inicial_fecha = NULL,
                        updated_at = :updated_at,
                        updated_by = :updated_by
                    WHERE id = :state_id
                """)
                params = {
                    "updated_at": datetime.now(),
                    "updated_by": user_id,
                    "state_id": state_id,
                }

            result = conn.execute(query, params)
            conn.commit()

            if result.rowcount == 0:
                raise BackendCoreBusinessError("Estado de versión no encontrado")

            self._logger.info(
                "[ESTADO_VERSION] Fase entrenamiento actualizada: state_id=%s completado=%s",
                state_id, completado
            )

            return {
                "success": True,
                "message": "Fase de entrenamiento actualizada correctamente",
            }

    def update_evaluation_phase(
        self,
        state_id: int,
        evaluacion: bool,
        reentrenamiento: bool,
        optimizacion: bool,
        calidad_aprobada: bool,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Actualiza fase de evaluación y reentrenamiento.

        Args:
            state_id: ID del estado de versión
            evaluacion: Flag de evaluación en curso
            reentrenamiento: Flag de reentrenamiento en curso
            optimizacion: Flag de optimización en curso
            calidad_aprobada: Flag de calidad aprobada
            identity_type_id: Tipo de identidad del usuario
            user_id: ID del usuario que realiza la actualización

        Returns:
            Dict con success y mensaje
        """
        if identity_type_id not in (1, 2, 3):
            raise BackendCorePermissionError(
                "project_version_state_update", identity_type_id
            )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        from sqlalchemy import create_engine, text
        from datetime import datetime

        engine = create_engine(dsn)
        with engine.connect() as conn:
            query = text("""
                UPDATE estado_version
                SET evaluacion_entrenamiento = :evaluacion,
                    reentrenamiento = :reentrenamiento,
                    optimizacion = :optimizacion,
                    control_calidad_aprobado = :calidad_aprobada,
                    updated_at = :updated_at,
                    updated_by = :updated_by
                WHERE id = :state_id
            """)

            result = conn.execute(
                query,
                {
                    "evaluacion": 1 if evaluacion else 0,
                    "reentrenamiento": 1 if reentrenamiento else 0,
                    "optimizacion": 1 if optimizacion else 0,
                    "calidad_aprobada": 1 if calidad_aprobada else 0,
                    "updated_at": datetime.now(),
                    "updated_by": user_id,
                    "state_id": state_id,
                },
            )
            conn.commit()

            if result.rowcount == 0:
                raise BackendCoreBusinessError("Estado de versión no encontrado")

            self._logger.info(
                "[ESTADO_VERSION] Fase evaluación actualizada: state_id=%s",
                state_id
            )

            return {
                "success": True,
                "message": "Fase de evaluación actualizada correctamente",
            }

    def update_generation_phase(
        self,
        state_id: int,
        generacion_completada: bool | None = None,
        user_id: int = 0,
        identity_type_id: int = 0,
        generacion_solicitada: bool | None = None,
    ) -> dict[str, Any]:
        """Actualiza fase de generación del modelo LLM.

        Args:
            state_id: ID del estado de versión
            generacion_completada: Flag de generación completada (opcional)
            identity_type_id: Tipo de identidad del usuario
            user_id: ID del usuario que realiza la actualización
            generacion_solicitada: Flag de generación solicitada (opcional)

        Returns:
            Dict con success y mensaje
        """
        if identity_type_id not in (1, 2, 3):
            raise BackendCorePermissionError(
                "project_version_state_update", identity_type_id
            )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        from sqlalchemy import create_engine, text
        from datetime import datetime

        engine = create_engine(dsn)
        with engine.connect() as conn:
            # Construir query dinámicamente
            set_clauses = []
            params = {
                "updated_at": datetime.now(),
                "updated_by": user_id,
                "state_id": state_id,
            }

            # Actualizar generacion_completada si se proporciona
            if generacion_completada is not None:
                set_clauses.append("generacion_llm_completada = :generacion_completada")
                params["generacion_completada"] = 1 if generacion_completada else 0

                # Si se marca como completada, actualizar también la fecha
                if generacion_completada:
                    set_clauses.append("generacion_llm_fecha = :fecha")
                    params["fecha"] = datetime.now()
                else:
                    set_clauses.append("generacion_llm_fecha = NULL")

            # Actualizar generacion_solicitada si se proporciona
            if generacion_solicitada is not None:
                set_clauses.append("generacion_llm_solicitada = :generacion_solicitada")
                params["generacion_solicitada"] = 1 if generacion_solicitada else 0

            set_clauses.extend(["updated_at = :updated_at", "updated_by = :updated_by"])

            query = text(f"""
                UPDATE estado_version
                SET {", ".join(set_clauses)}
                WHERE id = :state_id
            """)

            result = conn.execute(query, params)
            conn.commit()

            if result.rowcount == 0:
                raise BackendCoreBusinessError("Estado de versión no encontrado")

            self._logger.info(
                "[ESTADO_VERSION] Fase generación actualizada: state_id=%s completada=%s",
                state_id, generacion_completada
            )

            return {
                "success": True,
                "message": "Fase de generación actualizada correctamente",
            }

    def update_notification_phase(
        self,
        state_id: int,
        notificacion_enviada: bool,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Actualiza fase de notificación de descarga.

        Args:
            state_id: ID del estado de versión
            notificacion_enviada: Flag de notificación enviada
            identity_type_id: Tipo de identidad del usuario
            user_id: ID del usuario que realiza la actualización

        Returns:
            Dict con success y mensaje
        """
        if identity_type_id not in (1, 2, 3):
            raise BackendCorePermissionError(
                "project_version_state_update", identity_type_id
            )

        settings = load_mariadb_settings()
        database = settings.get("projects_database", "myllm_projects_db")
        dsn = self._build_dsn(settings, database)

        from sqlalchemy import create_engine, text
        from datetime import datetime

        engine = create_engine(dsn)
        with engine.connect() as conn:
            # Si se marca como enviada, actualizar también la fecha
            if notificacion_enviada:
                query = text("""
                    UPDATE estado_version
                    SET notificacion_descarga_enviada = 1,
                        notificacion_descarga_fecha = :fecha,
                        updated_at = :updated_at,
                        updated_by = :updated_by
                    WHERE id = :state_id
                """)
                params = {
                    "fecha": datetime.now(),
                    "updated_at": datetime.now(),
                    "updated_by": user_id,
                    "state_id": state_id,
                }
            else:
                query = text("""
                    UPDATE estado_version
                    SET notificacion_descarga_enviada = 0,
                        notificacion_descarga_fecha = NULL,
                        updated_at = :updated_at,
                        updated_by = :updated_by
                    WHERE id = :state_id
                """)
                params = {
                    "updated_at": datetime.now(),
                    "updated_by": user_id,
                    "state_id": state_id,
                }

            result = conn.execute(query, params)
            conn.commit()

            if result.rowcount == 0:
                raise BackendCoreBusinessError("Estado de versión no encontrado")

            self._logger.info(
                "[ESTADO_VERSION] Fase notificación actualizada: state_id=%s enviada=%s",
                state_id, notificacion_enviada
            )

            return {
                "success": True,
                "message": "Fase de notificación actualizada correctamente",
            }

    # ================================================================
    # Gestión de Jobs (actualización de estado desde Trainer)
    # ================================================================

    def complete_job(
        self,
        job_id: int,
        id_organizacion: int,
        id_proyecto: int,
        id_version: int,
        descripcion: str,
        referencia_salida: str,
        tipo_cambio: str = "evaluacion_documental",
        id_estado: int = 4,
    ) -> dict[str, Any]:
        """Actualiza el estado de un job y registra un evento en la tabla cambios.

        Ejecuta en una sola transacción:
        1. INSERT INTO cambios → registra el evento de finalización
        2. UPDATE jobs → establece id_estado, completado_en, referencia_salida e id_cambio

        Args:
            job_id: ID del job a actualizar
            id_organizacion: ID de la organización
            id_proyecto: ID del proyecto
            id_version: ID de la versión
            descripcion: Descripción del resultado
            referencia_salida: Ruta del archivo generado
            tipo_cambio: Tipo de cambio para la tabla cambios
            id_estado: Estado final del job (4=finalizado, 3=error)

        Returns:
            Diccionario con success, id_cambio y message
        """
        from sqlalchemy import text

        self._logger.info(
            "[JOBS] Completando job_id=%s estado=%s tipo=%s",
            job_id, id_estado, tipo_cambio,
        )

        with self._get_projects_db_writer_connection() as conn:
            try:
                # Paso 1: INSERT INTO cambios
                result_cambio = conn.execute(
                    text("""
                        INSERT INTO cambios
                            (id_version, fecha_cambio, tipo_cambio, descripcion,
                             creado_at, id_proyecto, id_organizacion)
                        VALUES
                            (:id_version, NOW(), :tipo_cambio, :descripcion,
                             NOW(), :id_proyecto, :id_organizacion)
                    """),
                    {
                        "id_version": id_version,
                        "tipo_cambio": tipo_cambio,
                        "descripcion": descripcion,
                        "id_proyecto": id_proyecto,
                        "id_organizacion": id_organizacion,
                    },
                )

                # Obtener el id del cambio insertado
                id_cambio = result_cambio.lastrowid

                # Paso 2: UPDATE jobs con estado y referencia
                conn.execute(
                    text("""
                        UPDATE jobs
                        SET id_estado = :id_estado,
                            completado_en = NOW(),
                            referencia_salida = :referencia_salida,
                            id_cambio = :id_cambio
                        WHERE id = :job_id
                    """),
                    {
                        "id_estado": id_estado,
                        "referencia_salida": referencia_salida,
                        "id_cambio": id_cambio,
                        "job_id": job_id,
                    },
                )

                conn.commit()

                self._logger.info(
                    "[JOBS] Job completado: job_id=%s id_cambio=%s estado=%s",
                    job_id, id_cambio, id_estado,
                )

                return {
                    "success": True,
                    "id_cambio": id_cambio,
                    "message": f"Job {job_id} actualizado a estado {id_estado}",
                }

            except Exception as exc:
                conn.rollback()
                self._logger.error(
                    "[JOBS] Error completando job_id=%s: %s", job_id, exc,
                )
                raise BackendCoreBusinessError(
                    f"Error actualizando job {job_id}: {exc}"
                ) from exc

    def get_pending_training_versions(self) -> list[dict[str, Any]]:
        """Obtiene versiones con entrenamiento inicial solicitado.

        Consulta estado_version con JOIN a organizations y proyectos
        para obtener nombres legibles. Solo incluye versiones donde
        entrenamiento_inicial_solicitado = 1.

        Returns:
            Lista de dicts con organization_name, proyecto_nombre,
            id_version y metadatos.
        """
        from sqlalchemy import text

        self._logger.info(
            "[backend-core] Consultando versiones pendientes de entrenamiento"
        )

        with self._get_projects_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        o.organization_name,
                        p.nombre AS proyecto_nombre,
                        ev.id_version,
                        ev.id AS state_id,
                        ev.id_organizacion,
                        ev.id_proyecto
                    FROM estado_version ev
                    INNER JOIN myllm_core_db.organizations o
                        ON ev.id_organizacion = o.organization_id
                    INNER JOIN proyectos p
                        ON ev.id_proyecto = p.id
                    WHERE ev.entrenamiento_inicial_solicitado = 1
                    ORDER BY o.organization_name, p.nombre, ev.id_version
                """),
            )
            rows = result.fetchall()

            return [
                {
                    "organization_name": row[0],
                    "proyecto_nombre": row[1],
                    "id_version": row[2],
                    "version_display": f"v{row[2]:03d}",
                    "state_id": row[3],
                    "id_organizacion": row[4],
                    "id_proyecto": row[5],
                }
                for row in rows
            ]

    # ============================================================================
    # Training - Registro y seguimiento de entrenamientos
    # ============================================================================

    def _load_training_default_params(self) -> dict[str, Any]:
        """Carga los parámetros de entrenamiento por defecto desde protected_values."""

        env_settings_path = (
            Path(__file__).resolve().parents[3]
            / "src/2_shared_application/config/env_settings.py"
        )
        spec = importlib.util.spec_from_file_location(
            "env_settings_training_params", env_settings_path
        )
        if spec is None or spec.loader is None:
            raise BackendCoreBusinessError(
                "No se pudo cargar el módulo de configuración"
            )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        protected = module.load_protected_settings()
        if not protected:
            raise BackendCoreBusinessError(
                "No se pudo cargar protected_values para parámetros de entrenamiento"
            )

        return {
            "learning_rate": protected.get("training_default_learning_rate", 0.001),
            "batch_size": protected.get("training_default_batch_size", 32),
            "epochs": protected.get("training_default_epochs", 10),
            "embedding_dimension": protected.get(
                "training_default_embedding_dimension", 768
            ),
            "sequence_length": protected.get(
                "training_default_sequence_length", 512
            ),
            "hidden_units": protected.get("training_default_hidden_units", 256),
            "dropout_rate": protected.get("training_default_dropout_rate", 0.1),
            "chunk_size": protected.get("training_default_chunk_size", 1000),
            "chunk_overlap": protected.get("training_default_chunk_overlap", 200),
            "temperature": protected.get("training_default_temperature", 0.7),
            "max_tokens": protected.get("training_default_max_tokens", 2048),
            "distance_metric": protected.get(
                "training_default_distance_metric", "cosine"
            ),
            "top_k": protected.get("training_default_top_k", 5),
            "loss_function": protected.get(
                "training_default_loss_function", "cross_entropy"
            ),
            "optimizer": protected.get("training_default_optimizer", "adam"),
        }

    def get_training_params(
        self,
        org_id: int,
        project_id: int,
        version_id: int,
    ) -> dict[str, Any]:
        """Endpoint inteligente: devuelve parámetros de entrenamiento.

        Si no hay entrenamientos previos completados para la versión,
        devuelve los defaults de protected_values.py.
        Si hay entrenamientos previos, devuelve los parámetros del último
        jobs_entrenamientos asociado.

        Incluye flags es_primer_entrenamiento/es_reentrenamiento y lista
        de modelos disponibles de jobs_modelos.

        Args:
            org_id: ID de la organización.
            project_id: ID del proyecto.
            version_id: ID de la versión.

        Returns:
            Diccionario con parámetros, flags y modelos disponibles.
        """
        from sqlalchemy import text

        self._logger.info(
            "[TRAINING] Consultando parámetros: org=%s, prj=%s, ver=%s",
            org_id, project_id, version_id,
        )

        # Cargar defaults como base
        defaults = self._load_training_default_params()

        # Obtener modelo base de Ollama desde env.yaml
        env_settings_path = (
            Path(__file__).resolve().parents[3]
            / "src/2_shared_application/config/env_settings.py"
        )
        spec = importlib.util.spec_from_file_location(
            "env_settings_model_base", env_settings_path
        )
        default_model = "deepseek-r1:8b"
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            default_model = module.get_env_value(
                "ollama_rag_base_model", "deepseek-r1:8b"
            )

        with self._get_projects_db_connection() as conn:
            try:
                # Contar entrenamientos completados para esta versión
                count_result = conn.execute(
                    text("""
                        SELECT COUNT(*) FROM entrenamientos
                        WHERE id_version = :version_id
                          AND estado = 'completado'
                    """),
                    {"version_id": version_id},
                )
                completed_count = count_result.scalar() or 0

                es_primer = completed_count == 0
                es_reentrenamiento = completed_count > 0

                params = dict(defaults)
                model_type = default_model

                if es_reentrenamiento:
                    # Obtener parámetros del último entrenamiento completado
                    last_job = conn.execute(
                        text("""
                            SELECT je.*
                            FROM entrenamientos e
                            INNER JOIN jobs_entrenamientos je
                                ON e.id_job_entrenamientos = je.id
                            WHERE e.id_version = :version_id
                              AND e.estado = 'completado'
                            ORDER BY e.created_at DESC
                            LIMIT 1
                        """),
                        {"version_id": version_id},
                    )
                    row = last_job.mappings().fetchone()
                    if row:
                        for key in (
                            "learning_rate", "batch_size", "epochs",
                            "embedding_dimension", "sequence_length",
                            "hidden_units", "dropout_rate", "chunk_size",
                            "chunk_overlap", "temperature", "max_tokens",
                            "distance_metric", "top_k", "loss_function",
                            "optimizer",
                        ):
                            if key in row and row[key] is not None:
                                params[key] = row[key]

                # Obtener modelos disponibles de jobs_modelos
                modelos_result = conn.execute(
                    text("""
                        SELECT id, nombre, tag, familia
                        FROM jobs_modelos
                        WHERE activo = 1
                        ORDER BY nombre
                    """),
                )
                modelos_rows = modelos_result.mappings().fetchall()
                modelos_disponibles = [
                    {
                        "id": int(r["id"]),
                        "nombre": str(r["nombre"]),
                        "tag": str(r.get("tag", "") or ""),
                        "familia": str(r.get("familia", "") or ""),
                    }
                    for r in modelos_rows
                ]

                self._logger.info(
                    "[TRAINING] Parámetros: primer=%s, reentrenamiento=%s, "
                    "modelos=%s, modelo_default=%s",
                    es_primer, es_reentrenamiento,
                    len(modelos_disponibles), model_type,
                )

                return {
                    "success": True,
                    "es_primer_entrenamiento": es_primer,
                    "es_reentrenamiento": es_reentrenamiento,
                    "chunk_size": params["chunk_size"],
                    "chunk_overlap": params["chunk_overlap"],
                    "embedding_dimension": params["embedding_dimension"],
                    "sequence_length": params.get("sequence_length", 512),
                    "distance_metric": params["distance_metric"],
                    "model_type": model_type,
                    "temperature": params["temperature"],
                    "max_tokens": params["max_tokens"],
                    "top_k": params["top_k"],
                    "learning_rate": params["learning_rate"],
                    "batch_size": params["batch_size"],
                    "epochs": params["epochs"],
                    "hidden_units": params.get("hidden_units", 256),
                    "dropout_rate": params.get("dropout_rate", 0.1),
                    "loss_function": params["loss_function"],
                    "optimizer": params["optimizer"],
                    "modelos_disponibles": modelos_disponibles,
                    "message": (
                        "Parámetros por defecto" if es_primer
                        else "Parámetros del último entrenamiento"
                    ),
                }

            except Exception as exc:
                self._logger.error(
                    "[TRAINING] Error obteniendo parámetros: %s", exc,
                )
                raise BackendCoreBusinessError(
                    f"Error obteniendo parámetros de entrenamiento: {exc}"
                ) from exc

    def register_entrenamiento(
        self,
        id_organizacion: int,
        id_proyecto: int,
        id_version: int,
        pat_version: str,
        entrenamiento_inicial: bool = True,
        reentrenamiento: bool = False,
        training_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Registra un nuevo entrenamiento creando registros en jobs_entrenamientos y entrenamientos.

        Calcula numero_secuencia (MAX+1 para la versión) y genera collection_name
        para ChromaDB con el formato ORG{org}_PRJ{prj}_v{ver}_ENT{id}_SEQ{seq}.

        Args:
            id_organizacion: ID de la organización.
            id_proyecto: ID del proyecto.
            id_version: ID de la versión.
            pat_version: Ruta completa al contenido de la versión.
            entrenamiento_inicial: True si es el primer entrenamiento.
            reentrenamiento: True si es un reentrenamiento.
            training_params: Parámetros de entrenamiento enviados desde el modal.
                Si es None, se cargan los defaults de protected_values.py.

        Returns:
            Diccionario con id_entrenamiento, id_job_entrenamientos,
            collection_name y numero_secuencia.
        """
        from sqlalchemy import text

        self._logger.info(
            "[TRAINING] Registrando entrenamiento: org=%s, prj=%s, ver=%s, "
            "inicial=%s, reentrenamiento=%s",
            id_organizacion,
            id_proyecto,
            id_version,
            entrenamiento_inicial,
            reentrenamiento,
        )

        # Usar parámetros del request si los hay, sino cargar defaults
        if training_params:
            defaults = self._load_training_default_params()
            # Merge: request sobreescribe defaults
            params = {**defaults, **training_params}
            self._logger.info(
                "[TRAINING] Usando parámetros del request para entrenamiento"
            )
        else:
            params = self._load_training_default_params()
            self._logger.info(
                "[TRAINING] Usando parámetros por defecto (no se enviaron desde modal)"
            )

        with self._get_projects_db_writer_connection() as conn:
            try:
                # 1. Calcular numero_secuencia (MAX+1 para esta versión)
                seq_result = conn.execute(
                    text("""
                        SELECT COALESCE(MAX(numero_secuencia), 0) + 1
                        FROM entrenamientos
                        WHERE id_version = :id_version
                    """),
                    {"id_version": id_version},
                )
                numero_secuencia = seq_result.scalar()

                # 2. Insertar parámetros en jobs_entrenamientos
                job_name = (
                    f"Training ORG{id_organizacion:05d}_PRJ{id_proyecto:05d}"
                    f"_v{id_version:03d}_SEQ{numero_secuencia}"
                )
                conn.execute(
                    text("""
                        INSERT INTO jobs_entrenamientos (
                            nombre, learning_rate, batch_size, epochs,
                            embedding_dimension, sequence_length, hidden_units,
                            dropout_rate, chunk_size, chunk_overlap,
                            distance_metric, top_k, temperature, max_tokens,
                            loss_function, optimizer, activo
                        ) VALUES (
                            :nombre, :learning_rate, :batch_size, :epochs,
                            :embedding_dimension, :sequence_length, :hidden_units,
                            :dropout_rate, :chunk_size, :chunk_overlap,
                            :distance_metric, :top_k, :temperature, :max_tokens,
                            :loss_function, :optimizer, 1
                        )
                    """),
                    {
                        "nombre": job_name,
                        "learning_rate": params["learning_rate"],
                        "batch_size": params["batch_size"],
                        "epochs": params["epochs"],
                        "embedding_dimension": params["embedding_dimension"],
                        "sequence_length": params["sequence_length"],
                        "hidden_units": params["hidden_units"],
                        "dropout_rate": params["dropout_rate"],
                        "chunk_size": params["chunk_size"],
                        "chunk_overlap": params["chunk_overlap"],
                        "distance_metric": params["distance_metric"],
                        "top_k": params["top_k"],
                        "temperature": params["temperature"],
                        "max_tokens": params["max_tokens"],
                        "loss_function": params["loss_function"],
                        "optimizer": params["optimizer"],
                    },
                )
                id_job = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

                # 3. Generar collection_name para ChromaDB
                collection_name = (
                    f"ORG{id_organizacion:05d}_PRJ{id_proyecto:05d}"
                    f"_v{id_version:03d}_ENT{{id}}_SEQ{numero_secuencia}"
                )

                # 4. Insertar registro en entrenamientos
                conn.execute(
                    text("""
                        INSERT INTO entrenamientos (
                            id_organizacion, id_proyecto, id_version,
                            pat_version, entrenamiento_inicial, reentrenamiento,
                            numero_secuencia, fase_actual, estado,
                            id_job_entrenamientos
                        ) VALUES (
                            :id_organizacion, :id_proyecto, :id_version,
                            :pat_version, :entrenamiento_inicial, :reentrenamiento,
                            :numero_secuencia, 'recepcion', 'pendiente',
                            :id_job
                        )
                    """),
                    {
                        "id_organizacion": id_organizacion,
                        "id_proyecto": id_proyecto,
                        "id_version": id_version,
                        "pat_version": pat_version,
                        "entrenamiento_inicial": 1 if entrenamiento_inicial else 0,
                        "reentrenamiento": 1 if reentrenamiento else 0,
                        "numero_secuencia": numero_secuencia,
                        "id_job": id_job,
                    },
                )
                id_entrenamiento = conn.execute(
                    text("SELECT LAST_INSERT_ID()")
                ).scalar()

                # 5. Actualizar collection_name con el id real
                collection_name = (
                    f"ORG{id_organizacion:05d}_PRJ{id_proyecto:05d}"
                    f"_v{id_version:03d}_ENT{id_entrenamiento}_SEQ{numero_secuencia}"
                )
                conn.execute(
                    text("""
                        UPDATE entrenamientos
                        SET collection_name = :collection_name
                        WHERE id = :id_entrenamiento
                    """),
                    {
                        "collection_name": collection_name,
                        "id_entrenamiento": id_entrenamiento,
                    },
                )

                conn.commit()

                # 6. Registrar cambio en tabla cambios (inicio de entrenamiento)
                try:
                    tipo_ent = "inicial" if entrenamiento_inicial else "reentrenamiento"
                    descripcion = f"Inicio de entrenamiento {tipo_ent} (secuencia {numero_secuencia})"

                    conn.execute(
                        text("CALL sp_registrar_cambio_entrenamiento(:id_ent, :tipo, :desc)"),
                        {
                            "id_ent": id_entrenamiento,
                            "tipo": "Inicio de entrenamiento",
                            "desc": descripcion,
                        },
                    )
                    conn.commit()
                    self._logger.info(
                        "[TRAINING] Cambio registrado: inicio entrenamiento %s",
                        id_entrenamiento,
                    )
                except Exception as exc:
                    # No fallar el registro si falla el cambio
                    self._logger.warning(
                        "[TRAINING] Error registrando cambio de inicio: %s", exc,
                    )

                self._logger.info(
                    "[TRAINING] Entrenamiento registrado: id=%s, job=%s, "
                    "collection=%s, seq=%s",
                    id_entrenamiento,
                    id_job,
                    collection_name,
                    numero_secuencia,
                )

                return {
                    "success": True,
                    "id_entrenamiento": id_entrenamiento,
                    "id_job_entrenamientos": id_job,
                    "collection_name": collection_name,
                    "numero_secuencia": numero_secuencia,
                    "message": (
                        f"Entrenamiento {id_entrenamiento} registrado "
                        f"con colección {collection_name}"
                    ),
                }

            except Exception as exc:
                conn.rollback()
                self._logger.error(
                    "[TRAINING] Error registrando entrenamiento: %s", exc,
                )
                raise BackendCoreBusinessError(
                    f"Error registrando entrenamiento: {exc}"
                ) from exc

    def update_entrenamiento_phase(
        self,
        id_entrenamiento: int,
        fase_actual: str,
    ) -> dict[str, Any]:
        """Actualiza la fase actual de un entrenamiento.

        Si es la primera actualización de fase (estado=pendiente),
        establece fecha_inicio y cambia estado a en_progreso.

        Args:
            id_entrenamiento: ID del entrenamiento.
            fase_actual: Nueva fase (validacion, preparacion, configuracion, entrenamiento).

        Returns:
            Diccionario con success y message.
        """
        from sqlalchemy import text

        valid_phases = (
            "recepcion", "validacion", "preparacion",
            "configuracion", "entrenamiento",
        )
        if fase_actual not in valid_phases:
            raise BackendCoreBusinessError(
                f"Fase '{fase_actual}' no válida. Valores permitidos: {valid_phases}"
            )

        self._logger.info(
            "[TRAINING] Actualizando fase: entrenamiento=%s, fase=%s",
            id_entrenamiento,
            fase_actual,
        )

        with self._get_projects_db_writer_connection() as conn:
            try:
                # Verificar que existe y obtener estado actual
                row = conn.execute(
                    text("""
                        SELECT estado, fase_actual
                        FROM entrenamientos
                        WHERE id = :id_entrenamiento
                    """),
                    {"id_entrenamiento": id_entrenamiento},
                ).fetchone()

                if not row:
                    raise BackendCoreBusinessError(
                        f"Entrenamiento {id_entrenamiento} no encontrado"
                    )

                estado_actual = row[0]

                # Si estaba pendiente, establecer fecha_inicio y estado en_progreso
                if estado_actual == "pendiente":
                    conn.execute(
                        text("""
                            UPDATE entrenamientos
                            SET fase_actual = :fase,
                                estado = 'en_progreso',
                                fecha_inicio = NOW()
                            WHERE id = :id_entrenamiento
                        """),
                        {
                            "fase": fase_actual,
                            "id_entrenamiento": id_entrenamiento,
                        },
                    )
                else:
                    conn.execute(
                        text("""
                            UPDATE entrenamientos
                            SET fase_actual = :fase
                            WHERE id = :id_entrenamiento
                        """),
                        {
                            "fase": fase_actual,
                            "id_entrenamiento": id_entrenamiento,
                        },
                    )

                conn.commit()

                self._logger.info(
                    "[TRAINING] Fase actualizada: entrenamiento=%s → %s",
                    id_entrenamiento,
                    fase_actual,
                )

                return {
                    "success": True,
                    "message": (
                        f"Entrenamiento {id_entrenamiento} "
                        f"actualizado a fase '{fase_actual}'"
                    ),
                }

            except BackendCoreBusinessError:
                conn.rollback()
                raise
            except Exception as exc:
                conn.rollback()
                self._logger.error(
                    "[TRAINING] Error actualizando fase: %s", exc,
                )
                raise BackendCoreBusinessError(
                    f"Error actualizando fase: {exc}"
                ) from exc

    def complete_entrenamiento(
        self,
        id_entrenamiento: int,
        modelo_path: str = "",
    ) -> dict[str, Any]:
        """Marca un entrenamiento como completado.

        Actualiza estado a 'completado', establece fecha_fin y modelo_path.

        Args:
            id_entrenamiento: ID del entrenamiento.
            modelo_path: Ruta del modelo generado.

        Returns:
            Diccionario con success y message.
        """
        from sqlalchemy import text

        self._logger.info(
            "[TRAINING] Completando entrenamiento=%s, modelo=%s",
            id_entrenamiento,
            modelo_path,
        )

        with self._get_projects_db_writer_connection() as conn:
            try:
                result = conn.execute(
                    text("""
                        UPDATE entrenamientos
                        SET estado = 'completado',
                            fase_actual = 'entrenamiento',
                            fecha_fin = NOW(),
                            modelo_path = :modelo_path
                        WHERE id = :id_entrenamiento
                    """),
                    {
                        "modelo_path": modelo_path,
                        "id_entrenamiento": id_entrenamiento,
                    },
                )

                if result.rowcount == 0:
                    raise BackendCoreBusinessError(
                        f"Entrenamiento {id_entrenamiento} no encontrado"
                    )

                conn.commit()

                # Registrar cambio en tabla cambios
                try:
                    descripcion = f"Entrenamiento completado exitosamente. Modelo: {modelo_path}"
                    conn.execute(
                        text("CALL sp_registrar_cambio_entrenamiento(:id_ent, :tipo, :desc)"),
                        {
                            "id_ent": id_entrenamiento,
                            "tipo": "Entrenamiento completado",
                            "desc": descripcion,
                        },
                    )
                    conn.commit()
                    self._logger.info(
                        "[TRAINING] Cambio registrado: completado entrenamiento %s",
                        id_entrenamiento,
                    )
                except Exception as exc:
                    self._logger.warning(
                        "[TRAINING] Error registrando cambio de completado: %s", exc,
                    )

                self._logger.info(
                    "[TRAINING] Entrenamiento %s completado", id_entrenamiento,
                )

                return {
                    "success": True,
                    "message": (
                        f"Entrenamiento {id_entrenamiento} completado. "
                        f"Modelo: {modelo_path}"
                    ),
                }

            except BackendCoreBusinessError:
                conn.rollback()
                raise
            except Exception as exc:
                conn.rollback()
                self._logger.error(
                    "[TRAINING] Error completando entrenamiento: %s", exc,
                )
                raise BackendCoreBusinessError(
                    f"Error completando entrenamiento: {exc}"
                ) from exc

    def error_entrenamiento(
        self,
        id_entrenamiento: int,
        error_mensaje: str = "",
    ) -> dict[str, Any]:
        """Marca un entrenamiento como error.

        Actualiza estado a 'error', establece fecha_fin y error_mensaje.

        Args:
            id_entrenamiento: ID del entrenamiento.
            error_mensaje: Mensaje descriptivo del error.

        Returns:
            Diccionario con success y message.
        """
        from sqlalchemy import text

        self._logger.info(
            "[TRAINING] Error en entrenamiento=%s: %s",
            id_entrenamiento,
            error_mensaje[:200],
        )

        with self._get_projects_db_writer_connection() as conn:
            try:
                result = conn.execute(
                    text("""
                        UPDATE entrenamientos
                        SET estado = 'error',
                            fecha_fin = NOW(),
                            error_mensaje = :error_mensaje
                        WHERE id = :id_entrenamiento
                    """),
                    {
                        "error_mensaje": error_mensaje,
                        "id_entrenamiento": id_entrenamiento,
                    },
                )

                if result.rowcount == 0:
                    raise BackendCoreBusinessError(
                        f"Entrenamiento {id_entrenamiento} no encontrado"
                    )

                conn.commit()

                # Registrar cambio en tabla cambios
                try:
                    descripcion = f"Error en entrenamiento: {error_mensaje[:200]}"
                    conn.execute(
                        text("CALL sp_registrar_cambio_entrenamiento(:id_ent, :tipo, :desc)"),
                        {
                            "id_ent": id_entrenamiento,
                            "tipo": "Error en entrenamiento",
                            "desc": descripcion,
                        },
                    )
                    conn.commit()
                    self._logger.info(
                        "[TRAINING] Cambio registrado: error entrenamiento %s",
                        id_entrenamiento,
                    )
                except Exception as exc:
                    self._logger.warning(
                        "[TRAINING] Error registrando cambio de error: %s", exc,
                    )

                self._logger.info(
                    "[TRAINING] Entrenamiento %s marcado como error",
                    id_entrenamiento,
                )

                return {
                    "success": True,
                    "message": (
                        f"Entrenamiento {id_entrenamiento} marcado como error"
                    ),
                }

            except BackendCoreBusinessError:
                conn.rollback()
                raise
            except Exception as exc:
                conn.rollback()
                self._logger.error(
                    "[TRAINING] Error marcando error: %s", exc,
                )
                raise BackendCoreBusinessError(
                    f"Error marcando entrenamiento como error: {exc}"
                ) from exc

    def cancel_entrenamiento(
        self,
        id_entrenamiento: int,
        motivo: str = "Cancelado por usuario",
    ) -> dict[str, Any]:
        """Cancela un entrenamiento en progreso.

        Actualiza estado a 'cancelado', establece fecha_fin y registra
        el motivo en la tabla cambios.

        Args:
            id_entrenamiento: ID del entrenamiento.
            motivo: Motivo de la cancelación.

        Returns:
            Diccionario con success y message.
        """
        from sqlalchemy import text

        self._logger.info(
            "[TRAINING] Cancelando entrenamiento=%s, motivo=%s",
            id_entrenamiento,
            motivo,
        )

        with self._get_projects_db_writer_connection() as conn:
            try:
                # Verificar que el entrenamiento existe y está en progreso
                check_result = conn.execute(
                    text("""
                        SELECT estado FROM entrenamientos
                        WHERE id = :id_entrenamiento
                    """),
                    {"id_entrenamiento": id_entrenamiento},
                )
                row = check_result.fetchone()

                if not row:
                    raise BackendCoreBusinessError(
                        f"Entrenamiento {id_entrenamiento} no encontrado"
                    )

                current_state = row[0]
                if current_state in ("completado", "error", "cancelado"):
                    raise BackendCoreBusinessError(
                        f"No se puede cancelar un entrenamiento en estado '{current_state}'"
                    )

                # Actualizar entrenamiento a cancelado
                conn.execute(
                    text("""
                        UPDATE entrenamientos
                        SET estado = 'cancelado',
                            fecha_fin = NOW()
                        WHERE id = :id_entrenamiento
                    """),
                    {"id_entrenamiento": id_entrenamiento},
                )

                conn.commit()

                # Registrar en tabla cambios
                try:
                    descripcion = f"Entrenamiento cancelado. Motivo: {motivo}"
                    conn.execute(
                        text("CALL sp_registrar_cambio_entrenamiento(:id_ent, :tipo, :desc)"),
                        {
                            "id_ent": id_entrenamiento,
                            "tipo": "Entrenamiento cancelado",
                            "desc": descripcion,
                        },
                    )
                    conn.commit()
                    self._logger.info(
                        "[TRAINING] Cambio registrado: cancelado entrenamiento %s",
                        id_entrenamiento,
                    )
                except Exception as exc:
                    self._logger.warning(
                        "[TRAINING] Error registrando cambio de cancelación: %s", exc,
                    )

                self._logger.info(
                    "[TRAINING] Entrenamiento %s cancelado", id_entrenamiento,
                )

                return {
                    "success": True,
                    "message": f"Entrenamiento {id_entrenamiento} cancelado",
                }

            except BackendCoreBusinessError:
                conn.rollback()
                raise
            except Exception as exc:
                conn.rollback()
                self._logger.error(
                    "[TRAINING] Error cancelando entrenamiento: %s", exc,
                )
                raise BackendCoreBusinessError(
                    f"Error cancelando entrenamiento: {exc}"
                ) from exc

    async def update_training_progress(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Recibe y almacena notificaciones de progreso del entrenamiento.

        Guarda el progreso en la tabla evoluciones_entrenamientos para que
        el backoffice pueda consultar el estado actualizado en tiempo real.

        Args:
            payload: Diccionario con id_entrenamiento, phase_key, subfase_key,
                    subfase_name, status, elapsed_time, error_message.

        Returns:
            Diccionario con success y message.
        """
        from datetime import datetime
        from sqlalchemy import text

        id_entrenamiento = payload.get("id_entrenamiento", 0)
        phase_key = payload.get("phase_key", "")
        subfase_key = payload.get("subfase_key", "")
        subfase_name = payload.get("subfase_name", "")
        status = payload.get("status", "")
        elapsed_time = payload.get("elapsed_time", "")
        error_message = payload.get("error_message", "")

        self._logger.info(
            "[TRAINING-PROGRESS] id=%s, subfase=%s (%s), status=%s, time=%s",
            id_entrenamiento,
            subfase_key,
            subfase_name,
            status,
            elapsed_time,
        )

        # Convertir elapsed_time a segundos
        duracion_segundos = self._parse_elapsed_time_to_seconds(elapsed_time)

        try:
            # Usar UPSERT: INSERT ... ON DUPLICATE KEY UPDATE
            query = text("""
                INSERT INTO evoluciones_entrenamientos
                    (id_entrenamiento, phase_key, subfase_key, subfase_name, status,
                     fecha_inicio, fecha_fin, duracion_segundos, error_mensaje)
                VALUES
                    (:id_ent, :phase, :subfase, :name, :status,
                     :fecha_inicio, :fecha_fin, :duracion, :error)
                ON DUPLICATE KEY UPDATE
                    status = VALUES(status),
                    fecha_fin = VALUES(fecha_fin),
                    duracion_segundos = VALUES(duracion_segundos),
                    error_mensaje = VALUES(error_mensaje),
                    updated_at = CURRENT_TIMESTAMP
            """)

            # Calcular fechas según el status
            now = datetime.now()
            fecha_inicio = now if status == "in_progress" else None
            fecha_fin = now if status in ("completed", "error") else None

            with self._get_projects_db_writer_connection() as conn:
                conn.execute(query, {
                    "id_ent": id_entrenamiento,
                    "phase": phase_key,
                    "subfase": subfase_key,
                    "name": subfase_name,
                    "status": status,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "duracion": duracion_segundos,
                    "error": error_message if error_message else None,
                })
                conn.commit()

            return {
                "success": True,
                "message": f"Progreso actualizado: {subfase_key} - {status}",
            }

        except Exception as exc:
            self._logger.error(
                "[TRAINING-PROGRESS] Error guardando en BD: %s",
                exc
            )
            return {
                "success": False,
                "message": f"Error almacenando progreso: {str(exc)}",
            }

    def _parse_elapsed_time_to_seconds(self, elapsed_time: str) -> int:
        """Convierte elapsed_time (ej: '1m 30s', '45s') a segundos."""
        if not elapsed_time:
            return 0

        total_seconds = 0
        parts = elapsed_time.split()

        for part in parts:
            if 'm' in part:
                total_seconds += int(part.replace('m', '')) * 60
            elif 's' in part:
                total_seconds += int(part.replace('s', ''))
            elif 'h' in part:
                total_seconds += int(part.replace('h', '')) * 3600

        return total_seconds

    async def get_training_progress(
        self,
        id_entrenamiento: int,
    ) -> dict[str, Any]:
        """Obtiene el progreso actual de un entrenamiento desde la BD.

        Args:
            id_entrenamiento: ID del entrenamiento a consultar.

        Returns:
            Diccionario con el progreso de todas las fases y subfases.
        """
        from sqlalchemy import text

        try:
            query = text("""
                SELECT
                    phase_key,
                    subfase_key,
                    subfase_name,
                    status,
                    duracion_segundos,
                    error_mensaje,
                    updated_at
                FROM evoluciones_entrenamientos
                WHERE id_entrenamiento = :id_ent
                ORDER BY phase_key, subfase_key
            """)

            with self._get_projects_db_connection() as conn:
                result = conn.execute(query, {"id_ent": id_entrenamiento})
                rows = result.fetchall()

            if not rows:
                return {
                    "success": False,
                    "message": "No hay datos de progreso para este entrenamiento",
                    "data": None,
                }

            # Agrupar por fases
            phases = {}
            last_phase = None

            for row in rows:
                phase_key = row[0]
                subfase_key = row[1]
                subfase_name = row[2]
                status = row[3]
                duracion = row[4] or 0
                error = row[5]

                # Convertir duracion_segundos a formato legible
                elapsed_time = self._format_seconds_to_elapsed(duracion)

                if phase_key not in phases:
                    phases[phase_key] = {"subfases": {}}

                phases[phase_key]["subfases"][subfase_key] = {
                    "name": subfase_name,
                    "status": status,
                    "elapsed_time": elapsed_time,
                    "error_message": error,
                }

                last_phase = phase_key

            return {
                "success": True,
                "data": {
                    "phases": phases,
                    "last_update": last_phase,
                },
            }

        except Exception as exc:
            self._logger.error(
                "[TRAINING-PROGRESS] Error consultando BD: %s",
                exc
            )
            return {
                "success": False,
                "message": f"Error consultando progreso: {str(exc)}",
                "data": None,
            }

    def _format_seconds_to_elapsed(self, seconds: int) -> str:
        """Convierte segundos a formato legible (ej: '1m 30s')."""
        if seconds == 0:
            return "0s"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    def _build_dsn(self, settings: dict, database: str) -> str:
        """Construye DSN para SQLAlchemy."""
        from urllib.parse import quote_plus

        host = settings.get("host", "localhost")
        port = settings.get("port", 3306)
        user = settings.get("writer_user", "")
        password = quote_plus(settings.get("writer_password", ""))

        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

    async def get_analysis_metrics(
        self,
        organization_id: int | None = None,
        project_id: int | None = None,
        version_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Obtiene las métricas de análisis de entrenamientos filtradas.

        Args:
            organization_id: ID de la organización (opcional).
            project_id: ID del proyecto (opcional).
            version_id: ID de la versión (opcional).

        Returns:
            Lista de análisis con métricas agregadas por categorías.
        """
        from sqlalchemy import text

        try:
            # Construir WHERE clause dinámico
            where_clauses = []
            params = {}

            if organization_id:
                where_clauses.append("e.id_organizacion = :org_id")
                params["org_id"] = organization_id

            if project_id:
                where_clauses.append("e.id_proyecto = :proj_id")
                params["proj_id"] = project_id

            if version_id:
                where_clauses.append("e.id_version = :ver_id")
                params["ver_id"] = version_id

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            query = text(f"""
                SELECT
                    a.id,
                    a.numero_secuencia,
                    a.nombre_modelo,
                    a.rag_precision,
                    a.rag_recall,
                    a.rag_f1_score,
                    a.rag_mrr,
                    a.rag_ndcg,
                    a.response_relevance,
                    a.response_coherence,
                    a.response_fluency,
                    a.response_groundedness,
                    a.response_completeness,
                    a.bleu_score,
                    a.rouge_1,
                    a.rouge_2,
                    a.rouge_l,
                    a.meteor_score,
                    a.perplexity,
                    a.factual_accuracy,
                    a.hallucination_rate,
                    a.citation_accuracy,
                    a.overall_quality_score,
                    a.fecha_analisis
                FROM job_entrenamientos_analisis a
                INNER JOIN entrenamientos e ON a.id_entrenamiento = e.id
                WHERE {where_sql}
                ORDER BY a.numero_secuencia ASC
            """)

            with self._get_projects_db_connection() as conn:
                result = conn.execute(query, params)
                rows = result.fetchall()

            if not rows:
                return []

            # Procesar resultados y calcular scores por categoría
            analisis_list = []
            for row in rows:
                # RAG Quality Score (promedio de métricas RAG)
                rag_metrics = [
                    float(row[3] or 0),  # rag_precision
                    float(row[4] or 0),  # rag_recall
                    float(row[5] or 0),  # rag_f1_score
                    float(row[6] or 0),  # rag_mrr
                    float(row[7] or 0),  # rag_ndcg
                ]
                rag_quality_score = sum(rag_metrics) / len([m for m in rag_metrics if m > 0]) if any(rag_metrics) else 0

                # Response Quality Score (promedio de métricas de respuesta)
                response_metrics = [
                    float(row[8] or 0),   # response_relevance
                    float(row[9] or 0),   # response_coherence
                    float(row[10] or 0),  # response_fluency
                    float(row[11] or 0),  # response_groundedness
                    float(row[12] or 0),  # response_completeness
                ]
                response_quality_score = sum(response_metrics) / len([m for m in response_metrics if m > 0]) if any(response_metrics) else 0

                # Generation Quality Score (promedio de métricas de generación)
                generation_metrics = [
                    float(row[13] or 0),  # bleu_score
                    float(row[14] or 0),  # rouge_1
                    float(row[15] or 0),  # rouge_2
                    float(row[16] or 0),  # rouge_l
                    float(row[17] or 0),  # meteor_score
                ]
                generation_quality_score = sum(generation_metrics) / len([m for m in generation_metrics if m > 0]) if any(generation_metrics) else 0

                # Factuality Score (promedio de métricas de factualidad)
                factuality_metrics = [
                    float(row[19] or 0),  # factual_accuracy
                    1.0 - float(row[20] or 0),  # 1 - hallucination_rate (invertido)
                    float(row[21] or 0),  # citation_accuracy
                ]
                factuality_score = sum(factuality_metrics) / len([m for m in factuality_metrics if m > 0]) if any(factuality_metrics) else 0

                analisis = {
                    "id": row[0],
                    "numero_secuencia": row[1],
                    "nombre_modelo": row[2],
                    "fecha_analisis": row[23].isoformat() if row[23] else None,
                    "metricas": {
                        "rag_quality_score": rag_quality_score,
                        "response_quality_score": response_quality_score,
                        "generation_quality_score": generation_quality_score,
                        "factuality_score": factuality_score,
                        "overall_quality_score": float(row[22] or 0),
                    }
                }
                analisis_list.append(analisis)

            return analisis_list

        except Exception as exc:
            logger.error(f"Error obteniendo métricas de análisis: {exc}")
            raise BackendCoreBusinessError(f"Error obteniendo métricas: {str(exc)}") from exc

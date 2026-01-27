"""
Servicio centralizado de validación de permisos.

Este servicio implementa el principio de Security by Design centralizando
toda la lógica de validación de permisos en un único punto. Puede ser usado
por todas las capas de la aplicación:

- Frontend/Backoffice: Validar qué opciones mostrar en la UI
- Middleware: Validar peticiones antes de procesarlas
- Backend Core: Validar operaciones antes de ejecutarlas
- fmanagement: Validar acceso a archivos/carpetas

Ejemplo de uso:
    service = PermissionValidationService(permissions_repository)
    
    # Validar un permiso específico
    if service.can_perform_action(identity_type_id=2, permission_key="folder_rename"):
        permitir_renombrar_carpeta()
    
    # Validar múltiples permisos
    if service.has_all_permissions(identity_type_id=2, ["folder_create", "file_create"]):
        permitir_crear_proyecto()
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


def _load_security_hierarchy() -> Any:
    """Carga el módulo de jerarquía de seguridad del dominio."""
    
    module_path = (
        Path(__file__).resolve().parents[2]
        / "1_shared_domain/security_hierarchy.py"
    )
    module_name = "security_hierarchy_service"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar security_hierarchy.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_security = _load_security_hierarchy()
LowLevelPermission = _security.LowLevelPermission
LowLevelPermissions = _security.LowLevelPermissions


class LowLevelPermissionsProvider(Protocol):
    """Protocolo para proveedores de permisos de bajo nivel."""
    
    def get_permissions_for_identity_type(
        self, identity_type_id: int
    ) -> dict[str, Any]:
        """Obtiene los permisos para un tipo de identidad."""
        ...


@dataclass(frozen=True)
class PermissionContext:
    """Contexto de validación de permisos."""
    
    user_id: int
    organization_id: int
    identity_type_id: int
    project_id: int | None = None
    version_id: int | None = None


@dataclass(frozen=True)
class PermissionResult:
    """Resultado de una validación de permiso."""
    
    allowed: bool
    permission_key: str
    context: PermissionContext
    reason: str = ""


# Lista completa de permisos alineados con low_level_permissions.json
ALL_PERMISSION_KEYS: tuple[str, ...] = (
    # Carpetas
    "folder_create",
    "folder_delete",
    "folder_rename",
    "folder_read",
    "folder_list",
    # Archivos
    "file_create",
    "file_read",
    "file_update",
    "file_delete",
    "file_list",
    # Proyectos
    "project_create",
    "project_read",
    "project_update",
    "project_delete",
    "project_list",
    # Versiones
    "version_create",
    "version_read",
    "version_update",
    "version_delete",
    "version_list",
    # Entrenamiento
    "training_create",
    "training_read",
    "training_update",
    "training_delete",
    "training_start",
    "training_stop",
    # Parámetros
    "parameters_create",
    "parameters_read",
    "parameters_update",
    "parameters_delete",
    # Notificaciones
    "notifications_create",
    "notifications_read",
    "notifications_update",
    "notifications_delete",
    # Usuarios
    "user_create",
    "user_read",
    "user_update",
    "user_delete",
    "user_enable",
    "user_disable",
)


class PermissionValidationService:
    """
    Servicio centralizado para validación de permisos.
    
    Implementa Security by Design centralizando la lógica de validación
    de permisos de bajo nivel (low_level_permissions).
    
    Attributes:
        _permissions_provider: Proveedor de permisos (puede ser JSON, DB, etc.)
        _cache: Cache en memoria de permisos por identity_type_id
    """
    
    def __init__(
        self,
        permissions_provider: LowLevelPermissionsProvider | None = None
    ) -> None:
        """
        Inicializa el servicio de validación.
        
        Args:
            permissions_provider: Proveedor de permisos. Si es None,
                                  se usa el proveedor por defecto (JSON).
        """
        self._provider = permissions_provider or _DefaultPermissionsProvider()
        self._cache: dict[int, dict[str, bool]] = {}
        self._logger = logging.getLogger("permission_validation")
    
    def clear_cache(self) -> None:
        """Limpia la cache de permisos."""
        self._cache.clear()
        self._logger.debug("Cache de permisos limpiada")
    
    def _get_permissions(self, identity_type_id: int) -> dict[str, bool]:
        """
        Obtiene los permisos para un identity_type_id.
        
        Usa cache en memoria para evitar lecturas repetidas.
        """
        if identity_type_id not in self._cache:
            raw_permissions = self._provider.get_permissions_for_identity_type(
                identity_type_id
            )
            # Normalizar a dict[str, bool]
            self._cache[identity_type_id] = {
                key: bool(raw_permissions.get(key, False))
                for key in ALL_PERMISSION_KEYS
            }
            self._logger.debug(
                "Permisos cargados para identity_type_id=%s",
                identity_type_id
            )
        return self._cache[identity_type_id]
    
    def can_perform_action(
        self,
        identity_type_id: int,
        permission_key: str,
    ) -> bool:
        """
        Valida si un tipo de identidad puede realizar una acción.
        
        Este es el método principal para validar permisos.
        
        Args:
            identity_type_id: ID del tipo de identidad (rol)
            permission_key: Clave del permiso (ej: "folder_rename")
        
        Returns:
            True si tiene el permiso, False en caso contrario
        
        Example:
            >>> service.can_perform_action(2, "folder_rename")
            True
        """
        if not permission_key:
            return False
        
        if permission_key not in ALL_PERMISSION_KEYS:
            self._logger.warning(
                "Permiso desconocido: %s", permission_key
            )
            return False
        
        permissions = self._get_permissions(identity_type_id)
        allowed = permissions.get(permission_key, False)
        
        self._logger.debug(
            "Validación de permiso: identity_type_id=%s key=%s allowed=%s",
            identity_type_id,
            permission_key,
            allowed
        )
        
        return allowed
    
    def validate_permission(
        self,
        context: PermissionContext,
        permission_key: str,
    ) -> PermissionResult:
        """
        Valida un permiso con contexto completo y retorna resultado detallado.
        
        Útil para logging y auditoría.
        
        Args:
            context: Contexto de la validación
            permission_key: Clave del permiso a validar
        
        Returns:
            PermissionResult con el resultado y detalles
        """
        allowed = self.can_perform_action(
            context.identity_type_id,
            permission_key
        )
        
        reason = ""
        if not allowed:
            reason = (
                f"Usuario {context.user_id} (rol {context.identity_type_id}) "
                f"no tiene permiso '{permission_key}'"
            )
        
        return PermissionResult(
            allowed=allowed,
            permission_key=permission_key,
            context=context,
            reason=reason,
        )
    
    def has_permission(
        self,
        identity_type_id: int,
        permission_key: str,
    ) -> bool:
        """
        Alias de can_perform_action para compatibilidad con SharedSessionState.
        """
        return self.can_perform_action(identity_type_id, permission_key)
    
    def has_any_permission(
        self,
        identity_type_id: int,
        permission_keys: list[str],
    ) -> bool:
        """
        Verifica si tiene AL MENOS UNO de los permisos especificados.
        
        Args:
            identity_type_id: ID del tipo de identidad
            permission_keys: Lista de permisos a verificar
        
        Returns:
            True si tiene al menos uno de los permisos
        """
        return any(
            self.can_perform_action(identity_type_id, key)
            for key in permission_keys
        )
    
    def has_all_permissions(
        self,
        identity_type_id: int,
        permission_keys: list[str],
    ) -> bool:
        """
        Verifica si tiene TODOS los permisos especificados.
        
        Args:
            identity_type_id: ID del tipo de identidad
            permission_keys: Lista de permisos requeridos
        
        Returns:
            True si tiene todos los permisos
        """
        return all(
            self.can_perform_action(identity_type_id, key)
            for key in permission_keys
        )
    
    def get_all_permissions(
        self,
        identity_type_id: int,
    ) -> dict[str, bool]:
        """
        Obtiene todos los permisos como diccionario.
        
        El formato coincide con low_level_permissions.json.
        
        Args:
            identity_type_id: ID del tipo de identidad
        
        Returns:
            Diccionario {permission_key: bool}
        """
        return self._get_permissions(identity_type_id).copy()
    
    # === Métodos de conveniencia para validaciones comunes ===
    
    def can_manage_folders(self, identity_type_id: int) -> bool:
        """Verifica si puede gestionar carpetas (crear/renombrar/eliminar)."""
        return self.has_any_permission(
            identity_type_id,
            ["folder_create", "folder_rename", "folder_delete"]
        )
    
    def can_manage_files(self, identity_type_id: int) -> bool:
        """Verifica si puede gestionar archivos (crear/editar/eliminar)."""
        return self.has_any_permission(
            identity_type_id,
            ["file_create", "file_update", "file_delete"]
        )
    
    def can_manage_projects(self, identity_type_id: int) -> bool:
        """Verifica si puede gestionar proyectos."""
        return self.has_any_permission(
            identity_type_id,
            ["project_create", "project_update", "project_delete"]
        )
    
    def can_manage_versions(self, identity_type_id: int) -> bool:
        """Verifica si puede gestionar versiones."""
        return self.has_any_permission(
            identity_type_id,
            ["version_create", "version_update", "version_delete"]
        )
    
    def can_manage_training(self, identity_type_id: int) -> bool:
        """Verifica si puede gestionar entrenamientos."""
        return self.has_any_permission(
            identity_type_id,
            ["training_create", "training_start", "training_stop"]
        )
    
    def can_manage_users(self, identity_type_id: int) -> bool:
        """Verifica si puede gestionar usuarios."""
        return self.has_any_permission(
            identity_type_id,
            ["user_create", "user_update", "user_delete", "user_enable", "user_disable"]
        )
    
    def can_access_backoffice(self, identity_type_id: int) -> bool:
        """
        Verifica si puede acceder al backoffice.
        
        Requisito: Tener permiso training_create = True
        """
        return self.can_perform_action(identity_type_id, "training_create")
    
    # === Validaciones específicas de recursos ===
    
    def can_rename_folder(
        self,
        identity_type_id: int,
        organization_id: int | None = None,
        project_id: int | None = None,
    ) -> bool:
        """
        Valida si puede renombrar carpetas.
        
        Por ahora solo valida el permiso base.
        En el futuro puede incluir validaciones adicionales
        por organización o proyecto.
        """
        return self.can_perform_action(identity_type_id, "folder_rename")
    
    def can_create_file(
        self,
        identity_type_id: int,
        organization_id: int | None = None,
        project_id: int | None = None,
    ) -> bool:
        """Valida si puede crear archivos."""
        return self.can_perform_action(identity_type_id, "file_create")
    
    def can_delete_project(
        self,
        identity_type_id: int,
        organization_id: int | None = None,
    ) -> bool:
        """Valida si puede eliminar proyectos."""
        return self.can_perform_action(identity_type_id, "project_delete")
    
    def can_start_training(
        self,
        identity_type_id: int,
        organization_id: int | None = None,
        project_id: int | None = None,
    ) -> bool:
        """Valida si puede iniciar entrenamiento."""
        return self.can_perform_action(identity_type_id, "training_start")


class _DefaultPermissionsProvider:
    """Proveedor de permisos por defecto que lee desde JSON."""
    
    def __init__(self) -> None:
        self._permissions_path = self._get_permissions_path()
    
    def _get_permissions_path(self) -> Path:
        """Obtiene la ruta del archivo de permisos."""
        return (
            Path(__file__).resolve().parents[1]
            / "moks/low_level_permisions.json"
        )
    
    def get_permissions_for_identity_type(
        self, identity_type_id: int
    ) -> dict[str, Any]:
        """Obtiene permisos desde el archivo JSON."""
        import json
        
        try:
            with self._permissions_path.open("r", encoding="utf-8") as f:
                all_permissions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error("Error al cargar permisos: %s", e)
            return {}
        
        # Buscar permisos para el identity_type_id
        # El id_permissions en el JSON corresponde al identity_type_group_permissions
        # del rol, pero por simplicidad asumimos que id_permissions == identity_type_id
        # cuando no hay mapping explícito
        
        for permission_set in all_permissions:
            if permission_set.get("id_permissions") == identity_type_id:
                return permission_set
        
        # Si no se encuentra, buscar usando el mapeo de roles
        # Por ahora retornar vacío
        logger.warning(
            "No se encontraron permisos para identity_type_id=%s",
            identity_type_id
        )
        return {}


# Instancia singleton para uso global
_service_instance: PermissionValidationService | None = None


def get_permission_service() -> PermissionValidationService:
    """Obtiene la instancia singleton del servicio de permisos."""
    global _service_instance
    if _service_instance is None:
        _service_instance = PermissionValidationService()
    return _service_instance

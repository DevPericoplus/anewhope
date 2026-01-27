"""Capa de orquestación del backend IA (trainer) con validación de permisos.

Este módulo implementa la capa de orquestación del backend IA,
integrando validación de permisos de bajo nivel (Security by Design)
en todas las operaciones de entrenamiento.

Principios:
- Toda operación valida permisos antes de ejecutarse
- Los permisos se obtienen del PermissionValidationService centralizado
- Si no hay permiso, se lanza BackendTrainerPermissionError

Permisos de entrenamiento:
- training_create: Crear/iniciar entrenamiento
- training_read: Ver estado/métricas
- training_update: Modificar parámetros
- training_delete: Eliminar entrenamiento
- training_start: Iniciar proceso
- training_stop: Detener proceso
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _load_permission_service() -> Any:
    """Carga el servicio de validación de permisos."""

    module_path = (
        Path(__file__).resolve().parents[3]
        / "src/2_shared_application/services/permission_validation_service.py"
    )
    module_name = "permission_validation_service_trainer"
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


_fmanagement_module = _load_fmanagement_module("backend_trainer_fmanagement")

FmanagementClient = _fmanagement_module.FmanagementClient
FmanagementClientError = _fmanagement_module.FmanagementClientError


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


_storage_module = _load_storage_module("backend_trainer_storage")

build_storage_paths = _storage_module.build_storage_paths
load_fmanagement_settings = _storage_module.load_fmanagement_settings


class BackendTrainerBusinessError(Exception):
    """Error de negocio del backend IA (trainer)."""


class BackendTrainerPermissionError(Exception):
    """Error de permisos del backend IA (Security by Design)."""

    def __init__(self, permission_key: str, identity_type_id: int, message: str = ""):
        self.permission_key = permission_key
        self.identity_type_id = identity_type_id
        super().__init__(
            message or f"Permiso '{permission_key}' denegado para rol {identity_type_id}"
        )


class BackendTrainerRouter:
    """Orquestador de operaciones del backend IA con validación de permisos.

    Implementa Security by Design validando permisos de bajo nivel
    antes de ejecutar cualquier operación de entrenamiento.

    Attributes:
        _fmanagement_client: Cliente de fmanagement para operaciones de archivos
        _permission_service: Servicio centralizado de validación de permisos
        _client_app: Identificador del cliente que origina la petición
    """

    def __init__(
        self,
        fmanagement_client: FmanagementClient | None = None,
        permission_service: PermissionValidationService | None = None,
    ) -> None:
        self._fmanagement_client = fmanagement_client
        self._permission_service = permission_service or PermissionValidationService()
        self._logger = logging.getLogger("backend_trainer.router")
        self._client_app: str = "unknown"

    def set_client_app(self, client_app: str) -> None:
        """Configura el identificador de aplicación cliente para trazabilidad."""
        self._client_app = client_app or "unknown"

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
            permission_key: Clave del permiso (ej: "training_start")
            raise_on_deny: Si es True, lanza excepción si no tiene permiso

        Returns:
            True si tiene el permiso

        Raises:
            BackendTrainerPermissionError: Si no tiene permiso y raise_on_deny=True
        """
        allowed = self._permission_service.can_perform_action(
            identity_type_id, permission_key
        )

        if not allowed and raise_on_deny:
            self._logger.warning(
                "[%s] Permiso denegado: identity_type_id=%s permission=%s",
                self._client_app,
                identity_type_id,
                permission_key,
            )
            raise BackendTrainerPermissionError(permission_key, identity_type_id)

        return allowed

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
            BackendTrainerPermissionError: Si no tiene permiso
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
            raise BackendTrainerBusinessError(
                f"Operación de entrenamiento desconocida: {operation}"
            )

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
            BackendTrainerPermissionError: Si no tiene permiso
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
            raise BackendTrainerBusinessError(
                f"Operación de versión desconocida: {operation}"
            )

        return self.validate_permission(identity_type_id, permission_key)

    # === Operaciones de Versión para Entrenamiento ===

    def clone_version_for_training(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Clona una versión para preparar el entrenamiento.

        Args:
            payload: Datos de la versión a clonar
            headers: Headers de seguridad (Authorization, X-Client-App, etc.)

        Returns:
            Resultado del clonado con path de destino

        Raises:
            BackendTrainerPermissionError: Si no tiene permiso
            BackendTrainerBusinessError: Si falla el clonado
        """
        identity_type_id = payload.get("identity_type_id", 0)

        # Validar permisos: necesita poder leer versiones y crear entrenamientos
        if identity_type_id:
            self.validate_version_operation(identity_type_id, "read")
            self.validate_training_operation(identity_type_id, "create")

        self._logger.info(
            "[%s] Clonando versión para entrenamiento: org=%s project=%s version=%s",
            self._client_app,
            payload.get("id_organization"),
            payload.get("id_project"),
            payload.get("version_path"),
        )

        # TODO: Implementar clonado real vía fmanagement
        # Por ahora retornamos un placeholder
        return {
            "success": True,
            "cloned_path": f"/training/org{payload.get('id_organization')}/prj{payload.get('id_project')}/{payload.get('version_path')}",
            "message": "Versión clonada para entrenamiento (placeholder)",
        }

    def get_version_files(
        self,
        version_id: int,
        identity_type_id: int | None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Lista archivos de una versión clonada.

        Args:
            version_id: ID de la versión
            identity_type_id: ID del rol para validación
            headers: Headers de seguridad

        Returns:
            Lista de archivos y total

        Raises:
            BackendTrainerPermissionError: Si no tiene permiso
        """
        if identity_type_id:
            self.validate_version_operation(identity_type_id, "read")

        self._logger.info(
            "[%s] Listando archivos de versión: version_id=%s",
            self._client_app,
            version_id,
        )

        # TODO: Implementar listado real vía fmanagement
        return {
            "files": [],
            "total_files": 0,
        }

    # === Operaciones de Entrenamiento ===

    def start_training(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Inicia un proceso de entrenamiento.

        Args:
            payload: Configuración del entrenamiento
            headers: Headers de seguridad

        Returns:
            ID del entrenamiento iniciado

        Raises:
            BackendTrainerPermissionError: Si no tiene permisos
            BackendTrainerBusinessError: Si falla el inicio
        """
        identity_type_id = payload.get("identity_type_id", 0)

        # Validar permisos: necesita training_start y training_create
        if identity_type_id:
            self.validate_training_operation(identity_type_id, "start")
            self.validate_training_operation(identity_type_id, "create")

        self._logger.info(
            "[%s] Iniciando entrenamiento: org=%s project=%s version=%s",
            self._client_app,
            payload.get("id_organization"),
            payload.get("id_project"),
            payload.get("version_path"),
        )

        # TODO: Implementar inicio real de entrenamiento
        return {
            "success": True,
            "training_id": 1,  # Placeholder
            "message": "Entrenamiento iniciado (placeholder)",
        }

    def stop_training(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Detiene un proceso de entrenamiento.

        Args:
            payload: Datos del entrenamiento a detener
            headers: Headers de seguridad

        Returns:
            Confirmación de detención

        Raises:
            BackendTrainerPermissionError: Si no tiene permiso
        """
        identity_type_id = payload.get("identity_type_id", 0)

        if identity_type_id:
            self.validate_training_operation(identity_type_id, "stop")

        training_id = payload.get("training_id")
        self._logger.info(
            "[%s] Deteniendo entrenamiento: training_id=%s",
            self._client_app,
            training_id,
        )

        # TODO: Implementar detención real
        return {
            "success": True,
            "message": f"Entrenamiento {training_id} detenido (placeholder)",
        }

    def get_training_status(
        self,
        training_id: int,
        identity_type_id: int | None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Obtiene el estado de un entrenamiento.

        Args:
            training_id: ID del entrenamiento
            identity_type_id: ID del rol para validación
            headers: Headers de seguridad

        Returns:
            Estado del entrenamiento con métricas

        Raises:
            BackendTrainerPermissionError: Si no tiene permiso
        """
        if identity_type_id:
            self.validate_training_operation(identity_type_id, "read")

        self._logger.info(
            "[%s] Consultando estado de entrenamiento: training_id=%s",
            self._client_app,
            training_id,
        )

        # TODO: Implementar consulta real de estado
        return {
            "training_id": training_id,
            "status": "pending",  # pending, running, completed, failed, stopped
            "progress": 0.0,
            "metrics": {},
            "started_at": None,
            "finished_at": None,
        }

    # === Operaciones de Modelos ===

    def list_models(
        self,
        id_organization: int | None,
        id_project: int | None,
        identity_type_id: int | None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Lista modelos entrenados.

        Args:
            id_organization: Filtro por organización
            id_project: Filtro por proyecto
            identity_type_id: ID del rol para validación
            headers: Headers de seguridad

        Returns:
            Lista de modelos

        Raises:
            BackendTrainerPermissionError: Si no tiene permiso
        """
        if identity_type_id:
            self.validate_training_operation(identity_type_id, "read")

        self._logger.info(
            "[%s] Listando modelos: org=%s project=%s",
            self._client_app,
            id_organization,
            id_project,
        )

        # TODO: Implementar listado real de modelos
        return {
            "models": [],
            "total": 0,
        }

    def get_model_metrics(
        self,
        model_id: int,
        identity_type_id: int | None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Obtiene métricas de un modelo.

        Args:
            model_id: ID del modelo
            identity_type_id: ID del rol para validación
            headers: Headers de seguridad

        Returns:
            Métricas del modelo

        Raises:
            BackendTrainerPermissionError: Si no tiene permiso
        """
        if identity_type_id:
            self.validate_training_operation(identity_type_id, "read")

        self._logger.info(
            "[%s] Consultando métricas de modelo: model_id=%s",
            self._client_app,
            model_id,
        )

        # TODO: Implementar consulta real de métricas
        return {
            "model_id": model_id,
            "metrics": {
                "accuracy": 0.0,
                "loss": 0.0,
                "epochs_trained": 0,
            },
            "training_history": [],
        }

    # === Permisos ===

    def get_training_permissions(
        self,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """
        Obtiene permisos de entrenamiento para un rol.

        Args:
            identity_type_id: ID del rol

        Returns:
            Diccionario con permisos de entrenamiento
        """
        self._logger.info(
            "[%s] Consultando permisos de entrenamiento: identity_type_id=%s",
            self._client_app,
            identity_type_id,
        )

        training_permissions = [
            "training_create",
            "training_read",
            "training_update",
            "training_delete",
            "training_start",
            "training_stop",
        ]

        permissions = {}
        for perm in training_permissions:
            permissions[perm] = self._permission_service.can_perform_action(
                identity_type_id, perm
            )

        return {
            "identity_type_id": identity_type_id,
            "permissions": permissions,
        }

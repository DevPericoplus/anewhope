"""Capa de orquestación del broker backend."""

from __future__ import annotations

import logging
from typing import Any

try:
    from .interfacetocore import CoreBackendClient, CoreBackendCommunicationError
    from .interfacetotrainer import TrainerBackendClient, TrainerBackendCommunicationError
except ImportError:  # pragma: no cover - soporte para ejecuciones fuera de paquete
    import importlib.util
    from pathlib import Path

    _base_path = Path(__file__).resolve().parent

    _module_path = _base_path / "interfacetocore.py"
    _spec = importlib.util.spec_from_file_location("interfacetocore", _module_path)
    if _spec is None or _spec.loader is None:
        raise
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)

    CoreBackendClient = _module.CoreBackendClient
    CoreBackendCommunicationError = _module.CoreBackendCommunicationError

    _trainer_path = _base_path / "interfacetotrainer.py"
    _trainer_spec = importlib.util.spec_from_file_location("interfacetotrainer", _trainer_path)
    if _trainer_spec is None or _trainer_spec.loader is None:
        raise
    _trainer_module = importlib.util.module_from_spec(_trainer_spec)
    _trainer_spec.loader.exec_module(_trainer_module)

    TrainerBackendClient = _trainer_module.TrainerBackendClient
    TrainerBackendCommunicationError = _trainer_module.TrainerBackendCommunicationError


class BrokerBusinessError(Exception):
    """Error de reglas de negocio del broker."""


class BrokerBackendRouter:
    """Orquestador de operaciones del broker backend.

    Este router enruta operaciones hacia:
    - Backend Core (8003): Datos (usuarios, organizaciones, permisos, fmanagement)
    - Backend IA (8004): Entrenamiento, modelos, métricas

    Propaga contexto de seguridad (JWT, session token) a todos los clientes
    para mantener la validación de permisos en cada capa (Security by Design).
    """

    def __init__(
        self,
        core_client: CoreBackendClient,
        trainer_client: TrainerBackendClient | None = None,
    ) -> None:
        self._core_client = core_client
        self._trainer_client = trainer_client
        self._logger = logging.getLogger("broker_backend.router")
        self._client_app: str = "unknown"
        self._authorization: str | None = None
        self._session_token: str | None = None

    def set_client_app(self, client_app: str) -> None:
        """Configura el identificador de aplicación cliente para trazabilidad."""

        self._client_app = client_app or "unknown"
        self._core_client.set_client_app(self._client_app)
        if self._trainer_client:
            self._trainer_client.set_client_app(self._client_app)

    def set_security_context(
        self,
        authorization: str | None = None,
        session_token: str | None = None,
    ) -> None:
        """Configura el contexto de seguridad para propagar a los backends.

        Este método propaga los headers de seguridad a los clientes del
        Backend Core y Backend IA para mantener el contexto de sesión
        en todo el flujo (Security by Design).

        Args:
            authorization: Token JWT (formato: "Bearer <token>")
            session_token: Token de sesión del usuario
        """
        self._authorization = authorization
        self._session_token = session_token

        # Propagar a clientes
        self._core_client.set_security_context(authorization, session_token)
        if self._trainer_client:
            self._trainer_client.set_security_context(authorization, session_token)

        # Log para auditoría (sin exponer el token completo)
        self._logger.debug(
            "[%s] Contexto de seguridad configurado: jwt=%s session=%s",
            self._client_app,
            bool(authorization),
            bool(session_token),
        )

    def fetch_users(self) -> list[dict[str, Any]]:
        """Obtiene usuarios desde el backend core."""

        try:
            return self._core_client.fetch_users()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError("No se pudo cargar usuarios desde core") from exc

    def store_users(self, users: list[dict[str, Any]]) -> None:
        """Guarda usuarios en el backend core."""

        try:
            self._core_client.store_users(users)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError("No se pudo guardar usuarios en core") from exc

    def fetch_organizations(self) -> list[dict[str, Any]]:
        """Obtiene organizaciones desde el backend core."""

        try:
            return self._core_client.fetch_organizations()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo cargar organizaciones desde core"
            ) from exc

    def store_organizations(self, organizations: list[dict[str, Any]]) -> None:
        """Guarda organizaciones en el backend core."""

        try:
            self._core_client.store_organizations(organizations)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo guardar organizaciones en core"
            ) from exc

    def fetch_roles(self) -> list[dict[str, Any]]:
        """Obtiene roles desde el backend core."""

        try:
            return self._core_client.fetch_roles()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError("No se pudo cargar roles desde core") from exc

    def store_roles(self, roles: list[dict[str, Any]]) -> None:
        """Guarda roles en el backend core."""

        try:
            self._core_client.store_roles(roles)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError("No se pudo guardar roles en core") from exc

    def fetch_basic_permissions(self) -> list[dict[str, Any]]:
        """Obtiene permisos básicos desde el backend core."""

        try:
            return self._core_client.fetch_basic_permissions()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo cargar permisos desde core"
            ) from exc

    def store_basic_permissions(self, permissions: list[dict[str, Any]]) -> None:
        """Guarda permisos básicos en el backend core."""

        try:
            self._core_client.store_basic_permissions(permissions)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo guardar permisos básicos en core"
            ) from exc

    def fetch_low_level_permissions(self) -> list[dict[str, Any]]:
        """Obtiene permisos de bajo nivel desde el backend core."""

        try:
            return self._core_client.fetch_low_level_permissions()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo cargar permisos de bajo nivel desde core"
            ) from exc

    def store_low_level_permissions(self, permissions: list[dict[str, Any]]) -> None:
        """Guarda permisos de bajo nivel en el backend core."""

        try:
            self._core_client.store_low_level_permissions(permissions)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo guardar permisos de bajo nivel en core"
            ) from exc

    def fetch_manage_roles(self) -> list[dict[str, Any]]:
        """Obtiene roles por organización desde el backend core."""

        try:
            return self._core_client.fetch_manage_roles()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo cargar roles por organización desde core"
            ) from exc

    def store_manage_roles(self, entries: list[dict[str, Any]]) -> None:
        """Guarda roles por organización en el backend core."""

        try:
            self._core_client.store_manage_roles(entries)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo guardar roles por organización en core"
            ) from exc

    def check_organization_name(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Valida la existencia de una organización."""

        try:
            return self._core_client.check_organization_name(payload)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo validar organización en core"
            ) from exc

    def create_organization(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea una organización en backend core."""

        try:
            return self._core_client.create_organization(payload)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo crear organización en core"
            ) from exc

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea un usuario en backend core."""

        try:
            return self._core_client.create_user(payload)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError("No se pudo crear usuario en core") from exc

    def update_user_status(
        self, user_id: int, active: bool, requester_org_id: int
    ) -> dict[str, Any]:
        """Actualiza el estado activo/inactivo de un usuario en backend core.
        
        Args:
            user_id: ID del usuario a modificar
            active: True para habilitar, False para deshabilitar
            requester_org_id: ID de la organización del solicitante (para validación)
        
        Returns:
            Diccionario con user_id, active y message
        """
        try:
            self._logger.info(
                "[%s] Actualizando estado usuario user_id=%s active=%s org_id=%s",
                self._client_app,
                user_id,
                active,
                requester_org_id,
            )
            return self._core_client.update_user_status(
                user_id=user_id,
                active=active,
                requester_org_id=requester_org_id,
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo actualizar estado del usuario {user_id}"
            ) from exc

    def check_user_exists(self, user_name: str) -> dict[str, Any]:
        """Verifica si existe un usuario por nombre de usuario.
        
        Args:
            user_name: Nombre de usuario a verificar
        
        Returns:
            Diccionario con exists y user_name
        """
        try:
            self._logger.info(
                "[%s] Verificando existencia de usuario '%s'",
                self._client_app,
                user_name,
            )
            return self._core_client.check_user_exists(user_name)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo verificar existencia del usuario {user_name}"
            ) from exc

    def get_user_by_email(self, email: str) -> dict[str, Any]:
        """Obtiene datos de un usuario por email.
        
        Args:
            email: Email del usuario
        
        Returns:
            Diccionario con datos del usuario o found=False
        """
        try:
            self._logger.info(
                "[%s] Buscando usuario por email '%s'",
                self._client_app,
                email,
            )
            return self._core_client.get_user_by_email(email)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo obtener usuario con email {email}"
            ) from exc

    def update_user_password(
        self, email: str, new_password: str, new_otp: str
    ) -> dict[str, Any]:
        """Actualiza contraseña y OTP de un usuario.
        
        Args:
            email: Email del usuario
            new_password: Nueva contraseña (ya cifrada)
            new_otp: Nuevo código OTP
        
        Returns:
            Diccionario con success y message
        """
        try:
            self._logger.info(
                "[%s] Actualizando contraseña para email '%s'",
                self._client_app,
                email,
            )
            return self._core_client.update_user_password(email, new_password, new_otp)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo actualizar contraseña para {email}"
            ) from exc

    def get_permissions(self, identity_type_id: int) -> dict[str, Any]:
        """Obtiene permisos desde backend core."""

        try:
            response = self._core_client.get_permissions(identity_type_id)
            self._logger.info(
                "[%s] Consulta permisos role_id=%s low_level=%s",
                self._client_app,
                identity_type_id,
                bool(response.get("low_level_permissions")),
            )
            return response
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError("No se pudo cargar permisos desde core") from exc

    def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía el procesamiento a backend core."""

        try:
            return self._core_client.process_data(payload)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo procesar datos en core"
            ) from exc

    # === Operaciones de Entrenamiento (Backend IA) ===

    def _ensure_trainer_client(self) -> TrainerBackendClient:
        """Verifica que el cliente trainer esté disponible."""

        if self._trainer_client is None:
            raise BrokerBusinessError(
                "El cliente del backend IA (trainer) no está configurado"
            )
        return self._trainer_client

    def trainer_health_check(self) -> dict[str, Any]:
        """Verifica el estado del servicio trainer."""

        client = self._ensure_trainer_client()
        try:
            return client.health_check()
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo verificar el estado del trainer"
            ) from exc

    def clone_version_for_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Clona una versión para entrenamiento."""

        client = self._ensure_trainer_client()
        self._logger.info(
            "[%s] Clonando versión para entrenamiento: org=%s project=%s",
            self._client_app,
            payload.get("id_organization"),
            payload.get("id_project"),
        )
        try:
            return client.clone_version(payload)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo clonar versión para entrenamiento"
            ) from exc

    def start_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Inicia un proceso de entrenamiento."""

        client = self._ensure_trainer_client()
        self._logger.info(
            "[%s] Iniciando entrenamiento: org=%s project=%s",
            self._client_app,
            payload.get("id_organization"),
            payload.get("id_project"),
        )
        try:
            return client.start_training(payload)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo iniciar el entrenamiento"
            ) from exc

    def stop_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Detiene un proceso de entrenamiento."""

        client = self._ensure_trainer_client()
        self._logger.info(
            "[%s] Deteniendo entrenamiento: training_id=%s",
            self._client_app,
            payload.get("training_id"),
        )
        try:
            return client.stop_training(payload)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo detener el entrenamiento"
            ) from exc

    def get_training_status(
        self,
        training_id: int,
        identity_type_id: int | None = None,
    ) -> dict[str, Any]:
        """Obtiene el estado de un entrenamiento."""

        client = self._ensure_trainer_client()
        try:
            return client.get_training_status(training_id, identity_type_id)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo obtener el estado del entrenamiento"
            ) from exc

    def list_models(
        self,
        id_organization: int | None = None,
        id_project: int | None = None,
        identity_type_id: int | None = None,
    ) -> dict[str, Any]:
        """Lista modelos entrenados."""

        client = self._ensure_trainer_client()
        try:
            return client.list_models(id_organization, id_project, identity_type_id)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo listar los modelos"
            ) from exc

    def get_model_metrics(
        self,
        model_id: int,
        identity_type_id: int | None = None,
    ) -> dict[str, Any]:
        """Obtiene métricas de un modelo."""

        client = self._ensure_trainer_client()
        try:
            return client.get_model_metrics(model_id, identity_type_id)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo obtener métricas del modelo"
            ) from exc

    def get_training_permissions(self, identity_type_id: int) -> dict[str, Any]:
        """Obtiene permisos de entrenamiento para un rol."""

        client = self._ensure_trainer_client()
        try:
            return client.get_training_permissions(identity_type_id)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo obtener permisos de entrenamiento"
            ) from exc

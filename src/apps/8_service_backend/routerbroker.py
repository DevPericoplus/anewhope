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
        self, user_id: int, active: bool, requester_org_id: int, requester_identity_type_id: int = 0
    ) -> dict[str, Any]:
        """Actualiza el estado activo/inactivo de un usuario en backend core.

        Args:
            user_id: ID del usuario a modificar
            active: True para habilitar, False para deshabilitar
            requester_org_id: ID de la organización del solicitante (para validación)
            requester_identity_type_id: Tipo de identidad del solicitante (1=SuperAdmin)

        Returns:
            Diccionario con user_id, active y message
        """
        try:
            self._logger.info(
                "[%s] Actualizando estado usuario user_id=%s active=%s org_id=%s identity_type_id=%s",
                self._client_app,
                user_id,
                active,
                requester_org_id,
                requester_identity_type_id,
            )
            return self._core_client.update_user_status(
                user_id=user_id,
                active=active,
                requester_org_id=requester_org_id,
                requester_identity_type_id=requester_identity_type_id,
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

    def ollama_health(self) -> dict[str, Any]:
        """Verifica el estado de Ollama en el trainer."""
        client = self._ensure_trainer_client()
        try:
            return client.ollama_health()
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError("No se pudo verificar el estado de Ollama") from exc

    def ollama_list_models(self) -> dict[str, Any]:
        """Lista modelos disponibles en Ollama."""
        client = self._ensure_trainer_client()
        try:
            return client.ollama_list_models()
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError("No se pudo obtener la lista de modelos") from exc

    def ollama_generate(self, request: dict) -> dict[str, Any]:
        """Genera texto con Ollama."""
        client = self._ensure_trainer_client()
        try:
            print(f"[DEBUG BROKER] Calling trainer ollama_generate with request: {request}")
            result = client.ollama_generate(request)
            print(f"[DEBUG BROKER] Trainer returned: {result}")
            return result
        except TrainerBackendCommunicationError as exc:
            print(f"[ERROR BROKER] TrainerBackendCommunicationError: {exc}")
            import traceback
            traceback.print_exc()
            raise BrokerBusinessError("Error generando texto con Ollama") from exc

    def ollama_chat(self, request: dict) -> dict[str, Any]:
        """Chat con Ollama."""
        client = self._ensure_trainer_client()
        try:
            return client.ollama_chat(request)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError("Error en chat con Ollama") from exc

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

    def send_documentacion(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía solicitud de análisis de documentación al trainer."""

        client = self._ensure_trainer_client()
        try:
            return client.send_documentacion(payload)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo enviar la solicitud de análisis de documentación al trainer"
            ) from exc

    def send_metadatos(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía solicitud de análisis de metadatos al trainer."""

        client = self._ensure_trainer_client()
        try:
            return client.send_metadatos(payload)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo enviar la solicitud de análisis de metadatos al trainer"
            ) from exc

    def send_entrenamiento(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía solicitud de entrenamiento inicial al trainer."""

        client = self._ensure_trainer_client()
        try:
            return client.send_entrenamiento(payload)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo enviar la solicitud de entrenamiento al trainer"
            ) from exc

    def send_autonomous_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía solicitud de entrenamiento autónomo al trainer.

        Ejecuta las fases 6-9 (Dataset + LoRA + GGUF export).
        """

        client = self._ensure_trainer_client()
        try:
            return client.send_autonomous_training(payload)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo enviar la solicitud de entrenamiento autónomo al trainer"
            ) from exc

    async def initialize_autonomous_training(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Inicializa registro de entrenamiento autónomo via Backend Core.

        Args:
            payload: Diccionario con id_entrenamiento y training_mode.

        Returns:
            Diccionario con success y message.
        """
        self._logger.info(
            "[%s] Inicializando entrenamiento autónomo: ent=%s",
            self._client_app,
            payload.get("id_entrenamiento"),
        )
        try:
            return await self._core_client.initialize_autonomous_training(payload)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error inicializando entrenamiento autónomo: {str(exc)}"
            ) from exc

    async def update_autonomous_metadata(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza metadatos de entrenamiento autónomo via Backend Core.

        Args:
            payload: Diccionario con id_entrenamiento, metadata_type y data.

        Returns:
            Diccionario con success y message.
        """
        self._logger.info(
            "[%s] Actualizando metadata autónoma: ent=%s type=%s",
            self._client_app,
            payload.get("id_entrenamiento"),
            payload.get("metadata_type"),
        )
        try:
            return await self._core_client.update_autonomous_metadata(payload)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error actualizando metadata autónoma: {str(exc)}"
            ) from exc

    async def get_autonomous_training_progress(
        self, id_entrenamiento: int
    ) -> dict[str, Any]:
        """Consulta el progreso del entrenamiento autónomo (fases 6-9) via Backend Core.

        Args:
            id_entrenamiento: ID del entrenamiento autónomo a consultar

        Returns:
            Diccionario con success y data (subphases del entrenamiento autónomo)
        """
        self._logger.info(
            "[%s] Consultando progreso autónomo: ent=%s",
            self._client_app,
            id_entrenamiento,
        )
        try:
            return await self._core_client.get_autonomous_progress(id_entrenamiento)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo consultar el progreso del entrenamiento autónomo"
            ) from exc

    def download_autonomous_package(self, id_entrenamiento: int):
        """Descarga el paquete ZIP del modelo autónomo generado.

        Args:
            id_entrenamiento: ID del entrenamiento autónomo

        Returns:
            httpx.Response con el contenido del archivo ZIP
        """
        client = self._ensure_trainer_client()
        try:
            return client.download_autonomous_package(id_entrenamiento)
        except TrainerBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo descargar el paquete del modelo autónomo"
            ) from exc

    async def list_autonomous_packages(
        self,
        id_organizacion: int | None = None,
        id_proyecto: int | None = None,
        id_version: int | None = None,
    ) -> dict[str, Any]:
        """Lista los paquetes autónomos disponibles via Backend Core.

        Args:
            id_organizacion: Filtrar por organización (opcional)
            id_proyecto: Filtrar por proyecto (opcional)
            id_version: Filtrar por versión (opcional)

        Returns:
            Diccionario con success y lista de paquetes
        """
        self._logger.info(
            "[%s] Listando paquetes autónomos: org=%s prj=%s ver=%s",
            self._client_app,
            id_organizacion,
            id_proyecto,
            id_version,
        )
        try:
            return await self._core_client.list_autonomous_packages(
                id_organizacion, id_proyecto, id_version
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo listar los paquetes autónomos"
            ) from exc

    # ========================================================================
    # Gestión de Proyectos (enrutados a Backend Core)
    # ========================================================================

    def get_organization_projects(
        self,
        organization_id: int,
        headers: dict[str, str],
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """Obtiene los proyectos de una organización.

        Enruta a Backend Core → MariaDB (myllm_projects_db)
        
        Args:
            include_deleted: Si True, incluye proyectos con existe=false
        """
        self._logger.info(
            "[%s] Consultando proyectos org_id=%s include_deleted=%s",
            self._client_app,
            organization_id,
            include_deleted,
        )
        try:
            return self._core_client.get_organization_projects(
                organization_id, headers, include_deleted=include_deleted
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudieron obtener proyectos: {exc}"
            ) from exc

    def create_project(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Crea un nuevo proyecto.

        Enruta a Backend Core → MariaDB (INSERT proyectos)
        El trigger crea automáticamente estado y cambios.
        """
        self._logger.info(
            "[%s] Creando proyecto: nombre=%s org_id=%s",
            self._client_app,
            payload.get("nombre"),
            payload.get("id_organizacion"),
        )
        try:
            return self._core_client.create_project(payload, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo crear el proyecto: {exc}"
            ) from exc

    def update_project(
        self, project_id: int, update_data: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Actualiza un proyecto existente.

        Enruta a Backend Core → MariaDB (UPDATE proyectos)
        El trigger registra cambios automáticamente.
        """
        self._logger.info(
            "[%s] Actualizando proyecto: project_id=%s data=%s",
            self._client_app,
            project_id,
            update_data,
        )
        try:
            return self._core_client.update_project(project_id, update_data, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo actualizar el proyecto: {exc}"
            ) from exc

    def delete_project(
        self, project_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Elimina un proyecto.

        Enruta a Backend Core → MariaDB (DELETE proyectos)
        El trigger registra el borrado automáticamente.
        """
        self._logger.info(
            "[%s] Eliminando proyecto: project_id=%s",
            self._client_app,
            project_id,
        )
        try:
            return self._core_client.delete_project(project_id, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo eliminar el proyecto: {exc}"
            ) from exc

    def request_project_support(
        self,
        project_id: int,
        tipo_cambio: str,
        descripcion: str,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Registra una solicitud de soporte para un proyecto.

        Enruta a Backend Core → MariaDB (CALL sp_registrar_cambio_proyecto)
        """
        self._logger.info(
            "[%s] Solicitud de soporte: project_id=%s tipo=%s",
            self._client_app,
            project_id,
            tipo_cambio,
        )
        try:
            return self._core_client.request_project_support(
                project_id, tipo_cambio, descripcion, headers
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo registrar solicitud de soporte: {exc}"
            ) from exc

    # ========================================================================
    # GESTIÓN DE ROLES DE USUARIO EN PROYECTOS
    # ========================================================================

    def get_project_roles_base(self, headers: dict[str, str]) -> dict[str, Any]:
        """Obtiene el catálogo maestro de roles base para proyectos.

        Enruta a Backend Core → MariaDB (proyectos_roles_base)
        """
        self._logger.info("[%s] Consultando catálogo de roles base", self._client_app)
        try:
            return self._core_client.get_project_roles_base(headers)
        except Exception as e:
            self._logger.error("[%s] Error obteniendo roles base: %s", self._client_app, e)
            raise BrokerBackendBusinessError(f"Error obteniendo roles base: {e}") from e

    def get_user_project_roles(
        self, user_id: int, organization_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Obtiene los roles de un usuario en proyectos.

        Enruta a Backend Core → MariaDB (proyectos_roles)
        """
        self._logger.info(
            "[%s] Consultando roles de usuario %s en org %s",
            self._client_app,
            user_id,
            organization_id,
        )
        try:
            return self._core_client.get_user_project_roles(
                user_id, organization_id, headers
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudieron obtener roles del usuario: {exc}"
            ) from exc

    def assign_user_to_project(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Asigna un usuario a un proyecto.

        Enruta a Backend Core → MariaDB (INSERT/UPDATE proyectos_roles)
        """
        self._logger.info(
            "[%s] Asignando usuario %s a proyecto %s con rol %s",
            self._client_app,
            payload.get("id_usuario"),
            payload.get("id_proyecto"),
            payload.get("id_rol"),
        )
        try:
            return self._core_client.assign_user_to_project(payload, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo asignar usuario al proyecto: {exc}"
            ) from exc

    def remove_user_from_project(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Quita un usuario de un proyecto.

        Enruta a Backend Core → MariaDB (UPDATE proyectos_roles active=0)
        """
        self._logger.info(
            "[%s] Quitando usuario %s de proyecto %s",
            self._client_app,
            payload.get("id_usuario"),
            payload.get("id_proyecto"),
        )
        try:
            return self._core_client.remove_user_from_project(payload, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo quitar usuario del proyecto: {exc}"
            ) from exc

    # ========================================================================
    # GESTIÓN DE TICKETS DE SOPORTE
    # ========================================================================

    def create_ticket(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Crea un nuevo ticket de soporte.

        Enruta a Backend Core → MariaDB (INSERT tickets + ticket_interacciones)
        """
        self._logger.info(
            "[%s] Creando ticket: %s",
            self._client_app,
            payload.get("titulo"),
        )
        try:
            return self._core_client.create_ticket(payload, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"No se pudo crear el ticket: {exc}") from exc

    def get_organization_tickets(
        self, organization_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Obtiene los tickets de una organización."""
        self._logger.info(
            "[%s] Consultando tickets org_id=%s",
            self._client_app,
            organization_id,
        )
        try:
            return self._core_client.get_organization_tickets(organization_id, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudieron obtener tickets: {exc}"
            ) from exc

    def get_ticket_detail(
        self, ticket_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Obtiene el detalle de un ticket específico."""
        self._logger.info(
            "[%s] Consultando ticket_id=%s",
            self._client_app,
            ticket_id,
        )
        try:
            return self._core_client.get_ticket_detail(ticket_id, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo obtener el ticket: {exc}"
            ) from exc

    def update_ticket(
        self, ticket_id: int, update_data: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Actualiza estado/prioridad de un ticket."""
        self._logger.info(
            "[%s] Actualizando ticket_id=%s data=%s",
            self._client_app,
            ticket_id,
            update_data,
        )
        try:
            return self._core_client.update_ticket(ticket_id, update_data, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo actualizar el ticket: {exc}"
            ) from exc

    def add_ticket_response(
        self, ticket_id: int, respuesta: str, user_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Añade respuesta a un ticket."""
        self._logger.info(
            "[%s] Añadiendo respuesta a ticket_id=%s user_id=%s",
            self._client_app,
            ticket_id,
            user_id,
        )
        try:
            return self._core_client.add_ticket_response(
                ticket_id, respuesta, user_id, headers
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo añadir respuesta: {exc}"
            ) from exc

    # ========================================================================
    # GESTIÓN DE CONVERSACIONES Y CAMBIOS
    # ========================================================================

    def get_user_conversation(
        self, user_id: int, org_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Busca conversación abierta de un usuario."""
        self._logger.info(
            "[%s] Buscando conversación user_id=%s org_id=%s",
            self._client_app, user_id, org_id,
        )
        try:
            return self._core_client.get_user_conversation(user_id, org_id, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error buscando conversación: {exc}"
            ) from exc

    def create_conversation(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Crea una nueva conversación."""
        self._logger.info(
            "[%s] Creando conversación org=%s user=%s",
            self._client_app,
            payload.get("id_organizacion"),
            payload.get("id_usuario_cliente"),
        )
        try:
            return self._core_client.create_conversation(payload, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error creando conversación: {exc}"
            ) from exc

    def get_conversation_messages(
        self, conversation_id: int, headers: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Obtiene los mensajes de una conversación."""
        self._logger.info(
            "[%s] Obteniendo mensajes conversación=%s",
            self._client_app, conversation_id,
        )
        try:
            return self._core_client.get_conversation_messages(conversation_id, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error obteniendo mensajes: {exc}"
            ) from exc

    def send_conversation_message(
        self, conversation_id: int, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Envía un mensaje en una conversación."""
        self._logger.info(
            "[%s] Enviando mensaje en conversación=%s",
            self._client_app, conversation_id,
        )
        try:
            return self._core_client.send_conversation_message(
                conversation_id, payload, headers
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error enviando mensaje: {exc}"
            ) from exc

    def mark_conversation_read(
        self, conversation_id: int, payload: dict[str, str], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Marca mensajes como leídos."""
        self._logger.info(
            "[%s] Marcando leídos conversación=%s tipo=%s",
            self._client_app, conversation_id, payload.get("tipo_lector"),
        )
        try:
            return self._core_client.mark_conversation_read(
                conversation_id, payload, headers
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error marcando leídos: {exc}"
            ) from exc

    def get_cambios_calendar(
        self,
        org_id: int,
        headers: dict[str, str],
        mes: int | None = None,
        anio: int | None = None,
        proyecto_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Obtiene eventos del calendario."""
        self._logger.info(
            "[%s] Consultando cambios calendario org=%s mes=%s anio=%s proyecto=%s",
            self._client_app, org_id, mes, anio, proyecto_id,
        )
        try:
            return self._core_client.get_cambios_calendar(
                org_id, headers, mes=mes, anio=anio, proyecto_id=proyecto_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error consultando cambios: {exc}"
            ) from exc

    # ========================================================================
    # CONVERSACIONES - BACKOFFICE
    # ========================================================================

    def get_organization_conversations(
        self, org_id: int, headers: dict[str, str], solo_activas: bool = True
    ) -> list[dict[str, Any]]:
        """Obtiene conversaciones de una organización."""
        self._logger.info(
            "[%s] Consultando conversaciones org=%s", self._client_app, org_id,
        )
        try:
            return self._core_client.get_organization_conversations(
                org_id, headers, solo_activas=solo_activas
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error consultando conversaciones org: {exc}"
            ) from exc

    def join_conversation(
        self, conversation_id: int, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Un usuario interno se une a una conversación."""
        self._logger.info(
            "[%s] Unirse a conversación %s", self._client_app, conversation_id,
        )
        try:
            return self._core_client.join_conversation(
                conversation_id, payload, headers
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error uniéndose a conversación: {exc}"
            ) from exc

    def get_conversation_detail(
        self, conversation_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Obtiene detalle de una conversación."""
        self._logger.info(
            "[%s] Consultando detalle conversación %s",
            self._client_app, conversation_id,
        )
        try:
            return self._core_client.get_conversation_detail(
                conversation_id, headers
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error consultando detalle conversación: {exc}"
            ) from exc

    def update_conversation_priority(
        self, conversation_id: int, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Actualiza la prioridad de una conversación."""
        self._logger.info(
            "[%s] Actualizando prioridad conversación %s",
            self._client_app, conversation_id,
        )
        try:
            return self._core_client.update_conversation_priority(
                conversation_id, payload, headers
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error actualizando prioridad: {exc}"
            ) from exc

    def update_conversation_state(
        self, conversation_id: int, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Actualiza el estado de una conversación."""
        self._logger.info(
            "[%s] Actualizando estado conversación %s",
            self._client_app, conversation_id,
        )
        try:
            return self._core_client.update_conversation_state(
                conversation_id, payload, headers
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error actualizando estado: {exc}"
            ) from exc

    def get_ticket_details(
        self, ticket_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Obtiene detalles de un ticket."""
        self._logger.info(
            "[%s] Consultando detalle ticket %s", self._client_app, ticket_id,
        )
        try:
            return self._core_client.get_ticket_details(ticket_id, headers)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error consultando detalle ticket: {exc}"
            ) from exc

    def save_ticket_interaction(
        self, ticket_id: int, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Guarda interacción de ticket."""
        self._logger.info(
            "[%s] Guardando interacción ticket %s", self._client_app, ticket_id,
        )
        try:
            return self._core_client.save_ticket_interaction(
                ticket_id, payload, headers
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error guardando interacción ticket: {exc}"
            ) from exc

    # ========================================================================
    # GESTIÓN DE TECNOLOGÍAS
    # ========================================================================

    def get_tecnologias(self) -> dict[str, Any]:
        """Obtiene todas las tecnologías disponibles."""
        self._logger.info("[%s] Consultando tecnologías", self._client_app)
        try:
            return self._core_client.get_tecnologias()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"No se pudieron obtener tecnologías: {exc}") from exc

    def get_proyecto_tecnologia(self, project_id: int) -> dict[str, Any]:
        """Obtiene la tecnología asignada a un proyecto."""
        self._logger.info(
            "[%s] Consultando tecnología de proyecto %s", self._client_app, project_id
        )
        try:
            return self._core_client.get_proyecto_tecnologia(project_id)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo obtener tecnología: {exc}"
            ) from exc

    def asignar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Asigna una tecnología a un proyecto."""
        self._logger.info(
            "[%s] Asignando tecnología a proyecto %s", self._client_app, project_id
        )
        try:
            return self._core_client.asignar_tecnologia(project_id, payload)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"No se pudo asignar tecnología: {exc}") from exc

    def actualizar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza la tecnología de un proyecto."""
        self._logger.info(
            "[%s] Actualizando tecnología de proyecto %s", self._client_app, project_id
        )
        try:
            return self._core_client.actualizar_tecnologia(project_id, payload)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo actualizar tecnología: {exc}"
            ) from exc

    def get_tecnologias_asignadas_org(self, org_id: int) -> dict[str, Any]:
        """Obtiene todas las tecnologías asignadas a proyectos de una organización."""
        self._logger.info(
            "[%s] Consultando tecnologías asignadas para organización %s",
            self._client_app,
            org_id,
        )
        try:
            return self._core_client.get_tecnologias_asignadas_org(org_id)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudieron obtener tecnologías asignadas: {exc}"
            ) from exc

    # ========================================================================
    # GESTIÓN DE VERSIONES
    # ========================================================================

    def get_project_versions(self, project_id: int, org_id: int) -> dict[str, Any]:
        """Obtiene todas las versiones de un proyecto."""
        self._logger.info(
            "[%s] Consultando versiones proyecto=%s org=%s",
            self._client_app,
            project_id,
            org_id,
        )
        try:
            return self._core_client.get_project_versions(project_id, org_id)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudieron obtener versiones: {exc}"
            ) from exc

    def create_project_version(self, project_id: int, org_id: int) -> dict[str, Any]:
        """Crea una nueva versión para un proyecto."""
        self._logger.info(
            "[%s] Creando versión proyecto=%s org=%s",
            self._client_app,
            project_id,
            org_id,
        )
        try:
            return self._core_client.create_project_version(project_id, org_id)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo crear versión: {exc}"
            ) from exc

    # ===================================================================
    # GESTIÓN DE ESTADOS DE VERSIÓN
    # ===================================================================

    def get_version_state(
        self, project_id: int, version_id: int, org_id: int
    ) -> dict[str, Any]:
        """Obtiene el estado actual de una versión."""
        self._logger.info(
            "[%s] Consultando estado versión=%s proyecto=%s org=%s",
            self._client_app,
            version_id,
            project_id,
            org_id,
        )
        try:
            return self._core_client.get_version_state(project_id, version_id, org_id)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo obtener estado de versión: {exc}"
            ) from exc

    def update_version_state(
        self, project_id: int, version_id: int, org_id: int, update_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza el estado de una versión."""
        self._logger.info(
            "[%s] Actualizando estado versión=%s proyecto=%s",
            self._client_app,
            version_id,
            project_id,
        )
        try:
            return self._core_client.update_version_state(
                project_id, version_id, org_id, update_data
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo actualizar estado de versión: {exc}"
            ) from exc

    def get_version_events(
        self, project_id: int, version_id: int, org_id: int, limit: int = 50
    ) -> dict[str, Any]:
        """Obtiene el historial de eventos de una versión."""
        self._logger.info(
            "[%s] Consultando eventos versión=%s proyecto=%s",
            self._client_app,
            version_id,
            project_id,
        )
        try:
            return self._core_client.get_version_events(
                project_id, version_id, org_id, limit
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudieron obtener eventos de versión: {exc}"
            ) from exc

    def create_version_full(
        self, project_id: int, request_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Crea una nueva versión completa (DB + fmanagement)."""
        self._logger.info(
            "[%s] Creando versión completa proyecto=%s org=%s",
            self._client_app,
            project_id,
            request_data.get("id_organizacion"),
        )
        try:
            return self._core_client.create_version_full(project_id, request_data)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo crear versión completa: {exc}"
            ) from exc

    # ===================================================================
    # INTEGRACIÓN CON FMANAGEMENT
    # ===================================================================

    def fmanagement_list(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Lista estructura de archivos vía fmanagement."""
        self._logger.info(
            "[%s] Listando fmanagement org=%s prj=%s version=%s",
            self._client_app,
            request_data.get("org_folder"),
            request_data.get("prj_folder"),
            request_data.get("version_folder"),
        )
        try:
            return self._core_client.fmanagement_list(request_data)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo listar estructura fmanagement: {exc}"
            ) from exc

    def fmanagement_operation(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta una operación genérica en fmanagement."""
        self._logger.info(
            "[%s] Operación fmanagement: %s",
            self._client_app,
            request_data.get("operation"),
        )
        try:
            return self._core_client.fmanagement_operation(request_data)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo ejecutar operación fmanagement: {exc}"
            ) from exc

    def fmanagement_diff(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Compara versiones vía fmanagement."""
        self._logger.info("[%s] Comparando versiones fmanagement", self._client_app)
        try:
            return self._core_client.fmanagement_diff(request_data)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"Error comparando versiones: {exc}") from exc

    def fmanagement_transfer(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Transfiere versiones vía fmanagement."""
        self._logger.info("[%s] Transfiriendo versión fmanagement", self._client_app)
        try:
            return self._core_client.fmanagement_transfer(request_data)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"Error transfiriendo versión: {exc}") from exc

    def fmanagement_download(self, request_data: dict[str, Any]) -> bytes:
        """Descarga un archivo vía fmanagement."""
        self._logger.info("[%s] Descargando archivo fmanagement", self._client_app)
        try:
            return self._core_client.fmanagement_download(request_data)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"Error descargando archivo: {exc}") from exc

    # ========================================================================
    # ASSIGNMENTS MANAGER - Gestor de asignaciones
    # ========================================================================

    def list_organizations(self) -> list[dict[str, Any]]:
        """Lista todas las organizaciones."""
        try:
            return self._core_client.list_organizations()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo obtener organizaciones"
            ) from exc

    def get_accessible_organizations(
        self, user_id: int, identity_type_id: int
    ) -> list[dict[str, Any]]:
        """Returns organizations accessible to a user."""
        try:
            return self._core_client.get_accessible_organizations(
                user_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo obtener organizaciones accesibles"
            ) from exc

    def list_roles(self) -> list[dict[str, Any]]:
        """Lista todos los roles."""
        try:
            return self._core_client.list_roles()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo obtener roles"
            ) from exc

    def get_internal_users(self) -> list[dict[str, Any]]:
        """Gets internal users from core."""
        try:
            return self._core_client.get_internal_users()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo obtener usuarios internos"
            ) from exc

    def get_organization_assignments(
        self, organization_id: int, identity_type_id: int
    ) -> list[dict[str, Any]]:
        """Gets organization assignments from core."""
        try:
            return self._core_client.get_organization_assignments(
                organization_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo obtener asignaciones"
            ) from exc

    def create_organization_assignment(
        self,
        user_id: int,
        organization_id: int,
        role_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Creates organization assignment."""
        try:
            return self._core_client.create_organization_assignment(
                user_id, organization_id, role_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al crear asignación: {str(exc)}"
            ) from exc

    def update_organization_assignment(
        self,
        assignment_id: int,
        active: bool,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates organization assignment."""
        try:
            return self._core_client.update_organization_assignment(
                assignment_id, active, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo actualizar asignación"
            ) from exc

    def delete_organization_assignment(
        self,
        assignment_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Deletes organization assignment."""
        try:
            return self._core_client.delete_organization_assignment(
                assignment_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo eliminar asignación"
            ) from exc

    def validate_org_prerequisite(
        self,
        user_id: int,
        organization_id: int,
    ) -> dict[str, Any]:
        """Validates org prerequisite."""
        try:
            return self._core_client.validate_org_prerequisite(
                user_id, organization_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo validar prerequisito"
            ) from exc

    def get_project_assignments(
        self, project_id: int, identity_type_id: int
    ) -> list[dict[str, Any]]:
        """Gets project assignments from core."""
        try:
            return self._core_client.get_project_assignments(
                project_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo obtener asignaciones de proyecto"
            ) from exc

    def create_project_assignment(
        self,
        user_id: int,
        organization_id: int,
        project_id: int,
        role_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Creates project assignment."""
        try:
            return self._core_client.create_project_assignment(
                user_id, organization_id, project_id, role_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"No se pudo crear asignación de proyecto: {exc}"
            ) from exc

    def update_project_assignment(
        self,
        assignment_id: int,
        active: bool,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates project assignment."""
        try:
            return self._core_client.update_project_assignment(
                assignment_id, active, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo actualizar asignación de proyecto"
            ) from exc

    def delete_project_assignment(
        self,
        assignment_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Deletes project assignment."""
        try:
            return self._core_client.delete_project_assignment(
                assignment_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                "No se pudo eliminar asignación de proyecto"
            ) from exc

    # ========================================================================
    # Métodos de Prompts
    # ========================================================================

    def get_prompts(
        self,
        category: str,
        identity_type_id: int,
    ) -> list[dict[str, Any]]:
        """Gets all prompts for a category."""
        try:
            return self._core_client.get_prompts(category, identity_type_id)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al obtener prompts de categoría {category}: {str(exc)}"
            ) from exc

    def get_prompt(
        self,
        category: str,
        id_prompt: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Gets a specific prompt by ID."""
        try:
            return self._core_client.get_prompt(
                category, id_prompt, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al obtener prompt {id_prompt}: {str(exc)}"
            ) from exc

    def create_prompt(
        self,
        category: str,
        payload: dict,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Creates a new prompt."""
        try:
            return self._core_client.create_prompt(
                category, payload, user_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al crear prompt: {str(exc)}"
            ) from exc

    def update_prompt(
        self,
        category: str,
        id_prompt: int,
        payload: dict,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates an existing prompt."""
        try:
            return self._core_client.update_prompt(
                category, id_prompt, payload, user_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al actualizar prompt {id_prompt}: {str(exc)}"
            ) from exc

    def toggle_prompt(
        self,
        category: str,
        id_prompt: int,
        payload: dict,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Toggles prompt active status."""
        try:
            return self._core_client.toggle_prompt(
                category, id_prompt, payload, user_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al cambiar estado del prompt {id_prompt}: {str(exc)}"
            ) from exc

    # ========================================================================
    # PROJECT VERSION STATE - Estado de versiones de proyectos (DDD)
    # ========================================================================

    def get_project_version_state_by_id(
        self,
        state_id: int,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Gets project version state by ID."""
        try:
            return self._core_client.get_project_version_state_by_id(
                state_id, user_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al obtener estado {state_id}: {str(exc)}"
            ) from exc

    def get_project_version_state_by_version(
        self,
        organization_id: int,
        project_id: int,
        version_id: int,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Gets project version state by version."""
        try:
            return self._core_client.get_project_version_state_by_version(
                organization_id, project_id, version_id, user_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al obtener estado de versión: {str(exc)}"
            ) from exc

    def list_project_version_states(
        self,
        user_id: int,
        identity_type_id: int,
        organization_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Lists project version states by user assignments."""
        try:
            return self._core_client.list_project_version_states(
                user_id, identity_type_id, organization_id, limit, offset
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al listar estados: {str(exc)}"
            ) from exc

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
        """Updates proposal phase."""
        try:
            return self._core_client.update_proposal_phase(
                state_id,
                aceptacion_cliente,
                aceptacion_interna,
                user_id,
                identity_type_id,
                revision_interna=revision_interna,
                propuesta_mejoras=propuesta_mejoras,
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al actualizar fase de propuesta: {str(exc)}"
            ) from exc

    def update_training_phase(
        self,
        state_id: int,
        completado: bool,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates training phase."""
        try:
            return self._core_client.update_training_phase(
                state_id, completado, user_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al actualizar fase de entrenamiento: {str(exc)}"
            ) from exc

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
        """Updates evaluation phase."""
        try:
            return self._core_client.update_evaluation_phase(
                state_id, evaluacion, reentrenamiento, optimizacion, calidad_aprobada, user_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al actualizar fase de evaluación: {str(exc)}"
            ) from exc

    def update_generation_phase(
        self,
        state_id: int,
        generacion_completada: bool | None,
        user_id: int,
        identity_type_id: int,
        generacion_solicitada: bool | None = None,
    ) -> dict[str, Any]:
        """Updates generation phase."""
        try:
            return self._core_client.update_generation_phase(
                state_id, generacion_completada, user_id, identity_type_id,
                generacion_solicitada=generacion_solicitada,
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al actualizar fase de generación: {str(exc)}"
            ) from exc

    def update_notification_phase(
        self,
        state_id: int,
        notificacion_enviada: bool,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates notification phase."""
        try:
            return self._core_client.update_notification_phase(
                state_id, notificacion_enviada, user_id, identity_type_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error al actualizar fase de notificación: {str(exc)}"
            ) from exc

    def get_pending_training_versions(self) -> dict[str, Any]:
        """Obtiene versiones con entrenamiento inicial solicitado.

        Enruta a Backend Core → MariaDB (myllm_projects_db + myllm_core_db)
        """
        self._logger.info(
            "[%s] Consultando versiones pendientes de entrenamiento",
            self._client_app,
        )
        try:
            return self._core_client.get_pending_training_versions()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error obteniendo versiones pendientes: {str(exc)}"
            ) from exc

    # ================================================================
    # Training - Registro y seguimiento de entrenamientos
    # ================================================================

    def get_training_params(
        self, org_id: int, project_id: int, version_id: int
    ) -> dict[str, Any]:
        """Obtiene parámetros de entrenamiento inteligentes desde Backend Core.

        Devuelve defaults (primer entrenamiento) o los parámetros del último
        job (reentrenamiento), junto con flags informativos y lista de modelos.

        Enruta: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        self._logger.info(
            "[%s] Consultando parámetros de entrenamiento: org=%s, prj=%s, ver=%s",
            self._client_app,
            org_id,
            project_id,
            version_id,
        )
        try:
            return self._core_client.get_training_params(
                org_id, project_id, version_id
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error obteniendo parámetros de entrenamiento: {str(exc)}"
            ) from exc

    def register_entrenamiento(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Registra un nuevo entrenamiento via Backend Core.

        Enruta: Trainer → Broker → Backend Core → MariaDB
        """
        self._logger.info(
            "[%s] Registrando entrenamiento: org=%s, prj=%s, ver=%s",
            self._client_app,
            payload.get("id_organizacion"),
            payload.get("id_proyecto"),
            payload.get("id_version"),
        )
        try:
            return self._core_client.register_entrenamiento(payload)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error registrando entrenamiento: {str(exc)}"
            ) from exc

    def update_entrenamiento_phase(
        self, id_entrenamiento: int, fase_actual: str
    ) -> dict[str, Any]:
        """Actualiza la fase de un entrenamiento via Backend Core."""
        self._logger.info(
            "[%s] Actualizando fase entrenamiento=%s → %s",
            self._client_app,
            id_entrenamiento,
            fase_actual,
        )
        try:
            return self._core_client.update_entrenamiento_phase(
                id_entrenamiento, fase_actual
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error actualizando fase de entrenamiento: {str(exc)}"
            ) from exc

    def complete_entrenamiento(
        self, id_entrenamiento: int, modelo_path: str
    ) -> dict[str, Any]:
        """Marca un entrenamiento como completado via Backend Core."""
        self._logger.info(
            "[%s] Completando entrenamiento=%s, modelo=%s",
            self._client_app,
            id_entrenamiento,
            modelo_path,
        )
        try:
            return self._core_client.complete_entrenamiento(
                id_entrenamiento, modelo_path
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error completando entrenamiento: {str(exc)}"
            ) from exc

    def error_entrenamiento(
        self, id_entrenamiento: int, error_mensaje: str
    ) -> dict[str, Any]:
        """Marca un entrenamiento como error via Backend Core."""
        self._logger.info(
            "[%s] Error en entrenamiento=%s: %s",
            self._client_app,
            id_entrenamiento,
            error_mensaje[:200],
        )
        try:
            return self._core_client.error_entrenamiento(
                id_entrenamiento, error_mensaje
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error marcando entrenamiento como error: {str(exc)}"
            ) from exc

    def cancel_entrenamiento(
        self, id_entrenamiento: int, motivo: str = "Cancelado por usuario"
    ) -> dict[str, Any]:
        """Cancela un entrenamiento en progreso via Backend Core."""
        self._logger.info(
            "[%s] Cancelando entrenamiento=%s, motivo=%s",
            self._client_app,
            id_entrenamiento,
            motivo,
        )
        try:
            return self._core_client.cancel_entrenamiento(
                id_entrenamiento, motivo
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error cancelando entrenamiento: {str(exc)}"
            ) from exc

    async def update_training_progress(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Envía notificación de progreso al Backend Core."""
        id_entrenamiento = payload.get("id_entrenamiento", 0)
        subfase_key = payload.get("subfase_key", "")

        self._logger.info(
            "[%s] Progreso entrenamiento=%s: subfase=%s",
            self._client_app,
            id_entrenamiento,
            subfase_key,
        )
        try:
            return await self._core_client.update_training_progress(payload)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error actualizando progreso: {str(exc)}"
            ) from exc

    async def get_training_progress(
        self,
        id_entrenamiento: int,
    ) -> dict[str, Any]:
        """Consulta el progreso actual de un entrenamiento desde el Backend Core."""
        self._logger.info(
            "[%s] Consultando progreso entrenamiento=%s",
            self._client_app,
            id_entrenamiento,
        )
        try:
            return await self._core_client.get_training_progress(id_entrenamiento)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error consultando progreso: {str(exc)}"
            ) from exc

    # ========================================================================
    # INFORMES
    # ========================================================================

    def list_informe_files(
        self, org_id: int, project_id: int, version_id: int
    ) -> dict[str, Any]:
        """Lista archivos markdown de informes para una versión."""
        self._logger.info(
            "[%s] Listando informes org=%s project=%s version=%s",
            self._client_app, org_id, project_id, version_id,
        )
        try:
            return self._core_client.list_informe_files(org_id, project_id, version_id)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error listando informes: {str(exc)}"
            ) from exc

    def get_informe_content(
        self, org_id: int, project_id: int, version_id: int, display_name: str
    ) -> dict[str, Any]:
        """Obtiene el contenido de un archivo markdown de informe."""
        self._logger.info(
            "[%s] Obteniendo informe org=%s project=%s version=%s file=%s",
            self._client_app, org_id, project_id, version_id, display_name,
        )
        try:
            return self._core_client.get_informe_content(
                org_id, project_id, version_id, display_name
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error obteniendo informe: {str(exc)}"
            ) from exc

    # ========================================================================
    # MODEL PACKAGES
    # ========================================================================

    def list_model_packages(
        self, org_id: int | None = None
    ) -> dict[str, Any]:
        """Lista paquetes ZIP de modelos disponibles para descarga."""
        self._logger.info(
            "[%s] Listando paquetes de modelos org=%s",
            self._client_app, org_id,
        )
        try:
            return self._core_client.list_model_packages(org_id)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error listando paquetes de modelos: {str(exc)}"
            ) from exc

    def download_model_package(
        self, org_id: int, project_id: int, version_id: int, filename: str
    ) -> bytes:
        """Descarga un paquete ZIP de modelo."""
        self._logger.info(
            "[%s] Descargando modelo org=%s prj=%s ver=%s file=%s",
            self._client_app, org_id, project_id, version_id, filename,
        )
        try:
            return self._core_client.download_model_package(
                org_id, project_id, version_id, filename
            )
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(
                f"Error descargando modelo: {str(exc)}"
            ) from exc

    # === JOB TEMPLATES ===

    def get_job_template_catalogs(self) -> dict[str, Any]:
        """Obtiene catálogos de job templates."""
        try:
            return self._core_client.get_job_template_catalogs()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"Error obteniendo catálogos: {exc}") from exc

    def get_job_templates(self) -> list[dict[str, Any]]:
        """Lista plantillas de jobs."""
        try:
            return self._core_client.get_job_templates()
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"Error obteniendo plantillas: {exc}") from exc

    def save_job_template(self, data: dict[str, Any]) -> dict[str, Any]:
        """Crea o actualiza una plantilla de job."""
        try:
            return self._core_client.save_job_template(data)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"Error guardando plantilla: {exc}") from exc

    def toggle_job_template(self, template_id: int) -> dict[str, Any]:
        """Activa/desactiva una plantilla de job."""
        try:
            return self._core_client.toggle_job_template(template_id)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"Error cambiando estado plantilla: {exc}") from exc

    # ========================================================================
    # JOBS
    # ========================================================================

    def get_jobs(
        self, org_id: int, project_id: int, version_id: int, tipo_clave: str | None = None
    ) -> list[dict[str, Any]]:
        """Lista jobs."""
        try:
            return self._core_client.get_jobs(org_id, project_id, version_id, tipo_clave)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"Error obteniendo jobs: {exc}") from exc

    def create_job(self, data: dict[str, Any]) -> dict[str, Any]:
        """Crea un nuevo job."""
        try:
            return self._core_client.create_job(data)
        except CoreBackendCommunicationError as exc:
            raise BrokerBusinessError(f"Error creando job: {exc}") from exc

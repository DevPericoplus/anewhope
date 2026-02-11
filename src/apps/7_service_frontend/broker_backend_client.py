"""Cliente síncrono para comunicación con el broker backend.

Este cliente propaga headers de seguridad (Authorization, X-Session-Token)
para mantener el contexto de sesión en todo el flujo de servicios.
"""

from __future__ import annotations

import json
from typing import Any

import httpx


class BrokerBackendCommunicationError(Exception):
    """Error de comunicación con el broker backend."""


class BrokerBackendClient:
    """Cliente HTTP síncrono para operaciones de persistencia.

    Propaga headers de seguridad para mantener el contexto de sesión:
    - Authorization: Token JWT del usuario
    - X-Session-Token: Token de sesión
    - X-Client-App: Identificador del cliente origen
    """

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client()
        self._owns_client = client is None
        self._client_app: str = "middleware"
        self._authorization: str | None = None
        self._session_token: str | None = None

    def set_client_app(self, client_app: str) -> None:
        """Configura el identificador de aplicación cliente para trazabilidad."""

        self._client_app = client_app or "middleware"

    def set_security_context(
        self,
        authorization: str | None = None,
        session_token: str | None = None,
    ) -> None:
        """Configura el contexto de seguridad para propagar en las peticiones.

        Args:
            authorization: Token JWT (formato: "Bearer <token>")
            session_token: Token de sesión del usuario
        """
        self._authorization = authorization
        self._session_token = session_token

    def close(self) -> None:
        """Cierra el cliente HTTP si es propio."""

        if self._owns_client:
            self._client.close()

    def _build_headers(
        self,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Construye headers incluyendo contexto de seguridad.

        Args:
            extra_headers: Headers adicionales opcionales

        Returns:
            Diccionario con todos los headers necesarios
        """
        headers: dict[str, str] = {"X-Client-App": self._client_app}

        if self._authorization:
            headers["Authorization"] = self._authorization
        if self._session_token:
            headers["X-Session-Token"] = self._session_token

        if extra_headers:
            headers.update(extra_headers)

        return headers

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | list[Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: float = 10.0,
    ) -> Any:
        """Ejecuta una petición HTTP y valida la respuesta.

        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            path: Ruta del endpoint
            payload: Cuerpo de la petición (opcional)
            extra_headers: Headers adicionales (opcional)
            timeout: Timeout en segundos (por defecto 10.0)

        Returns:
            Respuesta deserializada como JSON

        Raises:
            BrokerBackendCommunicationError: Si hay error de comunicación
        """
        url = f"{self._base_url}{path}"
        headers = self._build_headers(extra_headers)

        try:
            response = self._client.request(
                method, url, json=payload, headers=headers, timeout=timeout
            )
        except httpx.RequestError as exc:
            raise BrokerBackendCommunicationError(
                "No se pudo contactar con el broker backend"
            ) from exc

        if response.status_code >= 400:
            detail = ""
            try:
                error_data = response.json()
                detail = error_data.get("detail", "")
            except Exception:
                pass
            raise BrokerBackendCommunicationError(
                f"Error del broker backend: {response.status_code} - {detail}"
            )

        if response.content:
            try:
                return response.json()
            except json.JSONDecodeError as exc:
                raise BrokerBackendCommunicationError(
                    "Respuesta del broker backend no es JSON válido"
                ) from exc
        return None

    def fetch_users(self) -> list[dict[str, Any]]:
        """Obtiene la lista de usuarios."""

        data = self._request("GET", "/users")
        return list(data or [])

    def store_users(self, users: list[dict[str, Any]]) -> None:
        """Guarda la lista de usuarios."""

        self._request("PUT", "/users", payload=users)

    def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Crea un usuario individual en el backend core vía broker.
        
        Args:
            user_data: Diccionario con los datos del usuario:
                - organization_id: ID de la organización
                - identity_type_id: ID del tipo de identidad (rol)
                - user_name: Nombre de usuario
                - user_password: Contraseña cifrada
                - user_email: Correo electrónico
                - user_mobile: Teléfono móvil
                - user_otp: OTP de 4 dígitos
                - active: Estado activo (bool)
                - blocked: Estado bloqueado (bool)
                - contact_info: Información de contacto (dict)
                - billing_info: Información de facturación (dict)
        
        Returns:
            Diccionario con user_id, organization_id, identity_type_id
        
        Raises:
            BrokerBackendCommunicationError: Si hay error de comunicación
        """
        data = self._request("POST", "/users", payload=user_data)
        return dict(data or {})

    def update_user_status(
        self, user_id: int, active: bool, requester_org_id: int
    ) -> dict[str, Any]:
        """Actualiza el estado activo/inactivo de un usuario.
        
        Flujo: Middleware → Broker → Backend Core → MariaDB
        
        Args:
            user_id: ID del usuario a modificar
            active: True para habilitar, False para deshabilitar
            requester_org_id: ID de la organización del solicitante
        
        Returns:
            Diccionario con user_id, active y message
        """
        data = self._request(
            "PATCH",
            f"/users/{user_id}/status",
            payload={
                "user_id": user_id,
                "active": active,
                "requester_org_id": requester_org_id,
            },
        )
        return dict(data or {})

    def check_user_exists(self, user_name: str) -> dict[str, Any]:
        """Verifica si existe un usuario por nombre de usuario.
        
        Flujo: Middleware → Broker (aquí) → Backend Core → JSON/MariaDB
        """
        data = self._request(
            "POST",
            "/users/check-exists",
            payload={"user_name": user_name},
        )
        return dict(data or {})

    def get_user_by_email(self, email: str) -> dict[str, Any]:
        """Obtiene datos de un usuario por email.
        
        Flujo: Middleware → Broker (aquí) → Backend Core → JSON/MariaDB
        """
        data = self._request(
            "POST",
            "/users/by-email",
            payload={"email": email},
        )
        return dict(data or {})

    def update_user_password(
        self, email: str, new_password: str, new_otp: str
    ) -> dict[str, Any]:
        """Actualiza contraseña y OTP de un usuario.
        
        Flujo: Middleware → Broker (aquí) → Backend Core → JSON/MariaDB
        """
        data = self._request(
            "POST",
            "/users/update-password",
            payload={
                "email": email,
                "new_password": new_password,
                "new_otp": new_otp,
            },
        )
        return dict(data or {})

    def fetch_organizations(self) -> list[dict[str, Any]]:
        """Obtiene la lista de organizaciones."""

        data = self._request("GET", "/organizations")
        return list(data or [])

    def store_organizations(self, organizations: list[dict[str, Any]]) -> None:
        """Guarda la lista de organizaciones."""

        self._request("PUT", "/organizations", payload=organizations)

    def fetch_roles(self) -> list[dict[str, Any]]:
        """Obtiene la lista de roles."""

        data = self._request("GET", "/roles")
        return list(data or [])

    def fetch_basic_permissions(self) -> list[dict[str, Any]]:
        """Obtiene la lista de permisos básicos."""

        data = self._request("GET", "/basic-permissions")
        return list(data or [])

    def fetch_low_level_permissions(self) -> list[dict[str, Any]]:
        """Obtiene la lista de permisos de bajo nivel."""

        data = self._request("GET", "/low-level-permissions")
        return list(data or [])

    def fetch_manage_roles(self) -> list[dict[str, Any]]:
        """Obtiene la lista de roles por organización."""

        data = self._request("GET", "/manage-roles-by-org")
        return list(data or [])

    def store_manage_roles(self, entries: list[dict[str, Any]]) -> None:
        """Guarda la lista de roles por organización."""

        self._request("PUT", "/manage-roles-by-org", payload=entries)

    def get_permissions(self, identity_type_id: int) -> dict[str, Any]:
        """Obtiene permisos para un rol específico.

        Args:
            identity_type_id: ID del tipo de identidad (rol)

        Returns:
            Diccionario con permisos básicos y de bajo nivel
        """
        data = self._request("GET", f"/permissions?identity_type_id={identity_type_id}")
        return dict(data or {})

    # === Operaciones de Training (Backend IA) ===

    def trainer_health_check(self) -> dict[str, Any]:
        """Verifica el estado del servicio trainer."""

        data = self._request("GET", "/training/health")
        return dict(data or {})

    def clone_version_for_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Clona una versión para entrenamiento.

        Args:
            payload: Datos de la versión (id_user, id_organization, id_project, version_path)

        Returns:
            Resultado del clonado con path de destino
        """
        data = self._request("POST", "/training/clone-version", payload=payload)
        return dict(data or {})

    def start_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Inicia un proceso de entrenamiento.

        Args:
            payload: Configuración del entrenamiento

        Returns:
            ID del entrenamiento iniciado
        """
        data = self._request("POST", "/training/start", payload=payload)
        return dict(data or {})

    def stop_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Detiene un proceso de entrenamiento.

        Args:
            payload: Datos del entrenamiento a detener

        Returns:
            Confirmación de detención
        """
        data = self._request("POST", "/training/stop", payload=payload)
        return dict(data or {})

    def get_training_status(
        self,
        training_id: int,
        identity_type_id: int | None = None,
    ) -> dict[str, Any]:
        """Obtiene el estado de un entrenamiento.

        Args:
            training_id: ID del entrenamiento
            identity_type_id: ID del rol para validación

        Returns:
            Estado del entrenamiento con métricas
        """
        params = f"?identity_type_id={identity_type_id}" if identity_type_id else ""
        data = self._request("GET", f"/training/{training_id}/status{params}")
        return dict(data or {})

    def list_models(
        self,
        id_organization: int | None = None,
        id_project: int | None = None,
        identity_type_id: int | None = None,
    ) -> dict[str, Any]:
        """Lista modelos entrenados.

        Args:
            id_organization: Filtro por organización
            id_project: Filtro por proyecto
            identity_type_id: ID del rol para validación

        Returns:
            Lista de modelos
        """
        params = []
        if id_organization is not None:
            params.append(f"id_organization={id_organization}")
        if id_project is not None:
            params.append(f"id_project={id_project}")
        if identity_type_id is not None:
            params.append(f"identity_type_id={identity_type_id}")
        query = f"?{'&'.join(params)}" if params else ""
        data = self._request("GET", f"/training/models{query}")
        return dict(data or {})

    def get_model_metrics(
        self,
        model_id: int,
        identity_type_id: int | None = None,
    ) -> dict[str, Any]:
        """Obtiene métricas de un modelo.

        Args:
            model_id: ID del modelo
            identity_type_id: ID del rol para validación

        Returns:
            Métricas del modelo
        """
        params = f"?identity_type_id={identity_type_id}" if identity_type_id else ""
        data = self._request("GET", f"/training/models/{model_id}/metrics{params}")
        return dict(data or {})

    def get_training_permissions(self, identity_type_id: int) -> dict[str, Any]:
        """Obtiene permisos de entrenamiento para un rol.

        Args:
            identity_type_id: ID del rol

        Returns:
            Diccionario con permisos de entrenamiento
        """
        data = self._request(
            "GET", f"/training/permissions?identity_type_id={identity_type_id}"
        )
        return dict(data or {})

    # === Análisis de Documentación ===

    def send_documentacion(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía solicitud de análisis de documentación al broker → trainer.

        Args:
            payload: Datos del job con prompt_final, ids de org/prj/ver, etc.

        Returns:
            Respuesta ACK del trainer
        """
        data = self._request("POST", "/training/documentacion", payload=payload)
        return dict(data or {})

    def send_metadatos(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía solicitud de análisis de metadatos al broker → trainer.

        Args:
            payload: Datos del job con prompt_final, ids de org/prj/ver, etc.

        Returns:
            Respuesta ACK del trainer
        """
        data = self._request("POST", "/training/metadatos", payload=payload)
        return dict(data or {})

    # === Operaciones de Ollama ===

    def ollama_health(self) -> dict[str, Any]:
        """Verifica el estado de Ollama en el trainer."""
        data = self._request("GET", "/training/ollama/health", timeout=1800.0)
        return dict(data or {})

    def ollama_list_models(self) -> dict[str, Any]:
        """Lista modelos disponibles en Ollama."""
        data = self._request("GET", "/training/ollama/models", timeout=1800.0)
        return dict(data or {})

    def ollama_generate(self, request: dict[str, Any]) -> dict[str, Any]:
        """Genera texto con Ollama.

        Args:
            request: Configuración de generación (model, prompt, options)

        Returns:
            Respuesta de Ollama con el texto generado
        """
        data = self._request("POST", "/training/ollama/generate", payload=request, timeout=1800.0)
        return dict(data or {})

    def ollama_chat(self, request: dict[str, Any]) -> dict[str, Any]:
        """Chat con Ollama.

        Args:
            request: Configuración del chat (model, messages, options)

        Returns:
            Respuesta de Ollama con el mensaje generado
        """
        data = self._request("POST", "/training/ollama/chat", payload=request, timeout=1800.0)
        return dict(data or {})

    # ========================================================================
    # Gestión de Proyectos
    # ========================================================================

    def get_organization_projects(
        self, organization_id: int, include_deleted: bool = False
    ) -> dict[str, Any]:
        """Obtiene los proyectos de una organización.

        Args:
            organization_id: ID de la organización
            include_deleted: Si True, incluye proyectos con existe=false

        Returns:
            {"projects": [...], "total": int}
        """
        path = f"/projects/organization/{organization_id}"
        if include_deleted:
            path += "?include_deleted=true"
        data = self._request("GET", path)
        return dict(data or {"projects": [], "total": 0})

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea un nuevo proyecto.

        Args:
            payload: {"nombre": str, "descripcion": str, "id_organizacion": int, ...}

        Returns:
            {"project_id": int, "nombre": str, ...}
        """
        data = self._request("POST", "/projects", payload=payload)
        return dict(data or {})

    def update_project(
        self, project_id: int, update_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza un proyecto existente.

        Args:
            project_id: ID del proyecto
            update_data: Campos a actualizar

        Returns:
            {"success": True, "updated": True, "project_id": int}
        """
        data = self._request("PATCH", f"/projects/{project_id}", payload=update_data)
        return dict(data or {})

    def delete_project(self, project_id: int) -> dict[str, Any]:
        """Elimina un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            {"success": True, "deleted": True, "project_id": int}
        """
        data = self._request("DELETE", f"/projects/{project_id}")
        return dict(data or {})

    def request_project_support(
        self, project_id: int, tipo_cambio: str, descripcion: str
    ) -> dict[str, Any]:
        """Registra una solicitud de soporte para un proyecto.

        Args:
            project_id: ID del proyecto
            tipo_cambio: Tipo de cambio a registrar
            descripcion: Descripción de la solicitud

        Returns:
            {"success": True, "cambio_id": int | None}
        """
        data = self._request(
            "POST",
            f"/projects/{project_id}/support",
            payload={
                "project_id": project_id,
                "tipo_cambio": tipo_cambio,
                "descripcion": descripcion,
            },
        )
        return dict(data or {})

    # ========================================================================
    # GESTIÓN DE ROLES DE USUARIO EN PROYECTOS
    # ========================================================================

    def get_project_roles_base(self) -> dict[str, Any]:
        """Obtiene el catálogo maestro de roles base para proyectos.

        Returns:
            {"roles": [{"id": int, "nombre_rol": str, "descripcion": str}, ...], "total": int}
        """
        data = self._request("GET", "/project-roles-base")
        return dict(data or {})

    def get_user_project_roles(
        self, user_id: int, organization_id: int
    ) -> dict[str, Any]:
        """Obtiene los roles de un usuario en proyectos.

        Args:
            user_id: ID del usuario
            organization_id: ID de la organización

        Returns:
            {"user_id": int, "organization_id": int, "roles": [...], "total": int}
        """
        data = self._request(
            "GET",
            f"/users/{user_id}/project-roles?organization_id={organization_id}",
        )
        return dict(data or {})

    def assign_user_to_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Asigna un usuario a un proyecto.

        Args:
            payload: {"id_usuario": int, "id_proyecto": int, "id_organizacion": int, "id_rol": int}

        Returns:
            {"success": True, "message": str, ...}
        """
        data = self._request("POST", "/project-roles/assign", payload=payload)
        return dict(data or {})

    def remove_user_from_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Quita un usuario de un proyecto.

        Args:
            payload: {"id_usuario": int, "id_proyecto": int, "id_organizacion": int}

        Returns:
            {"success": True, "message": str, ...}
        """
        data = self._request("POST", "/project-roles/remove", payload=payload)
        return dict(data or {})

    # ========================================================================
    # GESTIÓN DE TICKETS DE SOPORTE
    # ========================================================================

    def create_ticket(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea un nuevo ticket de soporte.

        Args:
            payload: {"titulo": str, "consulta": str, "id_organizacion": int, ...}

        Returns:
            {"success": True, "ticket_id": int, "mensaje": str}
        """
        data = self._request("POST", "/tickets", payload=payload)
        return dict(data or {})

    def get_organization_tickets(self, organization_id: int) -> dict[str, Any]:
        """Obtiene los tickets de una organización.

        Args:
            organization_id: ID de la organización

        Returns:
            {"tickets": [...], "total": int}
        """
        data = self._request("GET", f"/tickets/organization/{organization_id}")
        return dict(data or {"tickets": [], "total": 0})

    def get_ticket_detail(self, ticket_id: int) -> dict[str, Any]:
        """Obtiene el detalle de un ticket específico.

        Args:
            ticket_id: ID del ticket

        Returns:
            TicketDto como diccionario
        """
        data = self._request("GET", f"/tickets/{ticket_id}")
        return dict(data or {})

    def update_ticket(
        self, ticket_id: int, update_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza estado/prioridad de un ticket.

        Args:
            ticket_id: ID del ticket
            update_data: {"estado": str?, "prioridad": str?}

        Returns:
            {"success": True, "updated": bool, "ticket_id": int}
        """
        data = self._request("PATCH", f"/tickets/{ticket_id}", payload=update_data)
        return dict(data or {})

    def add_ticket_response(
        self, ticket_id: int, respuesta: str, user_id: int = 0
    ) -> dict[str, Any]:
        """Añade respuesta a un ticket.

        Args:
            ticket_id: ID del ticket
            respuesta: Texto de la respuesta
            user_id: ID del usuario que responde

        Returns:
            {"success": True, "updated": bool, "ticket_id": int}
        """
        data = self._request(
            "POST",
            f"/tickets/{ticket_id}/respuesta",
            payload={"respuesta": respuesta, "user_id": user_id},
        )
        return dict(data or {})

    # ========================================================================
    # GESTIÓN DE TECNOLOGÍAS
    # ========================================================================

    def get_tecnologias(self) -> dict[str, Any]:
        """Obtiene todas las tecnologías disponibles."""
        data = self._request("GET", "/tecnologias")
        return dict(data or {})

    def get_proyecto_tecnologia(self, project_id: int) -> dict[str, Any]:
        """Obtiene la tecnología asignada a un proyecto."""
        data = self._request("GET", f"/proyectos/{project_id}/tecnologia")
        return dict(data or {})

    def asignar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Asigna una tecnología a un proyecto."""
        data = self._request(
            "POST", f"/proyectos/{project_id}/tecnologia", payload=payload
        )
        return dict(data or {})

    def actualizar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza la tecnología de un proyecto."""
        data = self._request(
            "PATCH", f"/proyectos/{project_id}/tecnologia", payload=payload
        )
        return dict(data or {})

    def get_tecnologias_asignadas_org(self, org_id: int) -> dict[str, Any]:
        """Obtiene todas las tecnologías asignadas a proyectos de una organización."""
        data = self._request("GET", f"/organizaciones/{org_id}/tecnologias-asignadas")
        return dict(data or {})
    # ========================================================================
    # GESTIÓN DE TECNOLOGÍAS
    # ========================================================================

    def get_tecnologias(self) -> dict[str, Any]:
        """Obtiene todas las tecnologías disponibles."""
        data = self._request("GET", "/tecnologias")
        return dict(data or {})

    def get_proyecto_tecnologia(self, project_id: int) -> dict[str, Any]:
        """Obtiene la tecnología asignada a un proyecto."""
        data = self._request("GET", f"/proyectos/{project_id}/tecnologia")
        return dict(data or {})

    def asignar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Asigna una tecnología a un proyecto."""
        data = self._request(
            "POST", f"/proyectos/{project_id}/tecnologia", payload=payload
        )
        return dict(data or {})

    def actualizar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza la tecnología de un proyecto."""
        data = self._request(
            "PATCH", f"/proyectos/{project_id}/tecnologia", payload=payload
        )
        return dict(data or {})

    def get_tecnologias_asignadas_org(self, org_id: int) -> dict[str, Any]:
        """Obtiene todas las tecnologías asignadas a proyectos de una organización."""
        data = self._request("GET", f"/organizaciones/{org_id}/tecnologias-asignadas")
        return dict(data or {})
    # ========================================================================
    # GESTIÓN DE TECNOLOGÍAS
    # ========================================================================

    def get_tecnologias(self) -> dict[str, Any]:
        """Obtiene todas las tecnologías disponibles."""
        data = self._request("GET", "/tecnologias")
        return dict(data or {})

    def get_proyecto_tecnologia(self, project_id: int) -> dict[str, Any]:
        """Obtiene la tecnología asignada a un proyecto."""
        data = self._request("GET", f"/proyectos/{project_id}/tecnologia")
        return dict(data or {})

    def asignar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Asigna una tecnología a un proyecto."""
        data = self._request(
            "POST", f"/proyectos/{project_id}/tecnologia", payload=payload
        )
        return dict(data or {})

    def actualizar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza la tecnología de un proyecto."""
        data = self._request(
            "PATCH", f"/proyectos/{project_id}/tecnologia", payload=payload
        )
        return dict(data or {})

    def get_tecnologias_asignadas_org(self, org_id: int) -> dict[str, Any]:
        """Obtiene todas las tecnologías asignadas a proyectos de una organización."""
        data = self._request("GET", f"/organizaciones/{org_id}/tecnologias-asignadas")
        return dict(data or {})
    # ========================================================================
    # GESTIÓN DE VERSIONES DE PROYECTOS
    # ========================================================================

    def get_project_versions(self, project_id: int, org_id: int) -> dict[str, Any]:
        """Obtiene todas las versiones de un proyecto."""
        data = self._request("GET", f"/proyectos/{project_id}/versiones?org_id={org_id}")
        return dict(data or {})

    def create_project_version(self, project_id: int, org_id: int) -> dict[str, Any]:
        """Crea una nueva versión para un proyecto."""
        payload = {"id_proyecto": project_id, "id_organizacion": org_id}
        data = self._request("POST", f"/proyectos/{project_id}/versiones", payload=payload)
        return dict(data or {})

    # ===================================================================
    # GESTIÓN DE ESTADOS DE VERSIÓN
    # ===================================================================

    def get_version_state(
        self, project_id: int, version_id: int, org_id: int
    ) -> dict[str, Any]:
        """Obtiene el estado actual de una versión."""
        data = self._request(
            "GET",
            f"/proyectos/{project_id}/versiones/{version_id}/estado?org_id={org_id}",
        )
        return dict(data or {})

    def update_version_state(
        self, project_id: int, version_id: int, org_id: int, update_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza el estado de una versión."""
        data = self._request(
            "PATCH",
            f"/proyectos/{project_id}/versiones/{version_id}/estado?org_id={org_id}",
            payload=update_data,
        )
        return dict(data or {})

    def get_version_events(
        self, project_id: int, version_id: int, org_id: int, limit: int = 50
    ) -> dict[str, Any]:
        """Obtiene el historial de eventos de una versión."""
        data = self._request(
            "GET",
            f"/proyectos/{project_id}/versiones/{version_id}/eventos?org_id={org_id}&limit={limit}",
        )
        return dict(data or {})

    def create_version_full(
        self, project_id: int, request_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Crea una versión completa (DB + fmanagement)."""
        data = self._request(
            "POST",
            f"/proyectos/{project_id}/versiones/crear-completa",
            payload=request_data,
        )
        return dict(data or {})

    # ===================================================================
    # INTEGRACIÓN CON FMANAGEMENT
    # ===================================================================

    def fmanagement_list(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Lista estructura de archivos vía fmanagement."""
        data = self._request("POST", "/fmanagement/list", payload=request_data)
        return dict(data or {})

    def fmanagement_operation(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta una operación genérica en fmanagement."""
        data = self._request("POST", "/fmanagement/operation", payload=request_data)
        return dict(data or {})

    def fmanagement_download(self, request_data: dict[str, Any]) -> bytes:
        """Descarga un archivo vía fmanagement."""
        url = f"{self._base_url}/fmanagement/download"
        headers = self._build_headers()
        try:
            response = self._client.post(url, json=request_data, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.content
        except Exception as exc:
            raise BrokerCommunicationError(f"Error descargando archivo del broker: {exc}") from exc

    def fmanagement_diff(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Compara versiones vía fmanagement."""
        data = self._request("POST", "/fmanagement/diff", payload=request_data)
        return dict(data or {})

    def fmanagement_transfer(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Transfiere versiones vía fmanagement."""
        data = self._request("POST", "/fmanagement/transfer", payload=request_data)
        return dict(data or {})

    # ========================================================================
    # ASSIGNMENTS MANAGER - Gestor de asignaciones
    # ========================================================================

    def list_organizations(self) -> list[dict[str, Any]]:
        """Lista todas las organizaciones."""
        data = self._request("GET", "/assignments/organizations")
        return list(data or [])

    def list_roles(self) -> list[dict[str, Any]]:
        """Lista todos los roles."""
        data = self._request("GET", "/assignments/roles")
        return list(data or [])

    def get_internal_users(self) -> list[dict[str, Any]]:
        """Gets internal users."""
        data = self._request("GET", "/assignments/internal-users")
        return list(data or [])

    def get_organization_assignments(
        self, organization_id: int, identity_type_id: int
    ) -> list[dict[str, Any]]:
        """Gets organization assignments."""
        data = self._request(
            "GET",
            f"/assignments/organizations/{organization_id}?identity_type_id={identity_type_id}",
        )
        return list(data or [])

    def create_organization_assignment(
        self,
        user_id: int,
        organization_id: int,
        role_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Creates organization assignment."""
        payload = {
            "user_id": user_id,
            "organization_id": organization_id,
            "role_id": role_id,
        }
        data = self._request(
            "POST",
            f"/assignments/organizations?identity_type_id={identity_type_id}",
            payload=payload,
        )
        return dict(data or {})

    def update_organization_assignment(
        self,
        assignment_id: int,
        active: bool,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates organization assignment."""
        data = self._request(
            "PATCH",
            f"/assignments/organizations/{assignment_id}?active={active}&identity_type_id={identity_type_id}",
        )
        return dict(data or {})

    def delete_organization_assignment(
        self,
        assignment_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Deletes organization assignment."""
        data = self._request(
            "DELETE",
            f"/assignments/organizations/{assignment_id}?identity_type_id={identity_type_id}",
        )
        return dict(data or {})

    def validate_org_prerequisite(
        self,
        user_id: int,
        organization_id: int,
    ) -> dict[str, Any]:
        """Validates org prerequisite."""
        data = self._request(
            "GET",
            f"/assignments/validate-org-prerequisite?user_id={user_id}&organization_id={organization_id}",
        )
        return dict(data or {})

    def get_project_assignments(
        self, project_id: int, identity_type_id: int
    ) -> list[dict[str, Any]]:
        """Gets project assignments."""
        data = self._request(
            "GET",
            f"/assignments/projects/{project_id}?identity_type_id={identity_type_id}",
        )
        return list(data or [])

    def create_project_assignment(
        self,
        user_id: int,
        organization_id: int,
        project_id: int,
        role_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Creates project assignment."""
        payload = {
            "user_id": user_id,
            "organization_id": organization_id,
            "project_id": project_id,
            "role_id": role_id,
        }
        data = self._request(
            "POST",
            f"/assignments/projects?identity_type_id={identity_type_id}",
            payload=payload,
        )
        return dict(data or {})

    def update_project_assignment(
        self,
        assignment_id: int,
        active: bool,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates project assignment."""
        data = self._request(
            "PATCH",
            f"/assignments/projects/{assignment_id}?active={active}&identity_type_id={identity_type_id}",
        )
        return dict(data or {})

    def delete_project_assignment(
        self,
        assignment_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Deletes project assignment."""
        data = self._request(
            "DELETE",
            f"/assignments/projects/{assignment_id}?identity_type_id={identity_type_id}",
        )
        return dict(data or {})

    # ========================================================================
    # Métodos de Prompts
    # ========================================================================

    def get_prompts(
        self,
        category: str,
        identity_type_id: int,
    ) -> list[dict[str, Any]]:
        """Gets all prompts for a category."""
        data = self._request(
            "GET",
            f"/prompts/{category}?identity_type_id={identity_type_id}",
        )
        return list(data or [])

    def get_prompt(
        self,
        category: str,
        id_prompt: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Gets a specific prompt by ID."""
        data = self._request(
            "GET",
            f"/prompts/{category}/{id_prompt}?identity_type_id={identity_type_id}",
        )
        return dict(data or {})

    def create_prompt(
        self,
        category: str,
        payload: dict,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Creates a new prompt."""
        data = self._request(
            "POST",
            f"/prompts/{category}?identity_type_id={identity_type_id}&user_id={user_id}",
            payload=payload,
        )
        return dict(data or {})

    def update_prompt(
        self,
        category: str,
        id_prompt: int,
        payload: dict,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates an existing prompt."""
        data = self._request(
            "PUT",
            f"/prompts/{category}/{id_prompt}?identity_type_id={identity_type_id}&user_id={user_id}",
            payload=payload,
        )
        return dict(data or {})

    def toggle_prompt(
        self,
        category: str,
        id_prompt: int,
        payload: dict,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Toggles prompt active status."""
        data = self._request(
            "PATCH",
            f"/prompts/{category}/{id_prompt}/toggle?identity_type_id={identity_type_id}&user_id={user_id}",
            payload=payload,
        )
        return dict(data or {})

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
        data = self._request(
            "GET",
            f"/project-version-states/{state_id}?user_id={user_id}&identity_type_id={identity_type_id}",
        )
        return dict(data or {})

    def get_project_version_state_by_version(
        self,
        organization_id: int,
        project_id: int,
        version_id: int,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Gets project version state by version."""
        data = self._request(
            "GET",
            f"/project-version-states/version/{organization_id}/{project_id}/{version_id}?user_id={user_id}&identity_type_id={identity_type_id}",
        )
        return dict(data or {})

    def list_project_version_states(
        self,
        user_id: int,
        identity_type_id: int,
        organization_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Lists project version states by user assignments."""
        params = f"user_id={user_id}&identity_type_id={identity_type_id}&limit={limit}&offset={offset}"
        if organization_id is not None:
            params += f"&organization_id={organization_id}"

        data = self._request("GET", f"/project-version-states?{params}")
        return list(data or [])

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
        payload = {
            "aceptacion_cliente": aceptacion_cliente,
            "aceptacion_interna": aceptacion_interna,
        }
        if revision_interna is not None:
            payload["revision_interna"] = revision_interna
        if propuesta_mejoras is not None:
            payload["propuesta_mejoras"] = propuesta_mejoras

        data = self._request(
            "PATCH",
            f"/project-version-states/{state_id}/proposal?user_id={user_id}&identity_type_id={identity_type_id}",
            payload=payload,
        )
        return dict(data or {})

    def update_training_phase(
        self,
        state_id: int,
        completado: bool,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates training phase."""
        payload = {"completado": completado}
        data = self._request(
            "PATCH",
            f"/project-version-states/{state_id}/training?user_id={user_id}&identity_type_id={identity_type_id}",
            payload=payload,
        )
        return dict(data or {})

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
        payload = {
            "evaluacion": evaluacion,
            "reentrenamiento": reentrenamiento,
            "optimizacion": optimizacion,
            "calidad_aprobada": calidad_aprobada,
        }
        data = self._request(
            "PATCH",
            f"/project-version-states/{state_id}/evaluation?user_id={user_id}&identity_type_id={identity_type_id}",
            payload=payload,
        )
        return dict(data or {})

    def update_generation_phase(
        self,
        state_id: int,
        generacion_completada: bool | None = None,
        user_id: int = 0,
        identity_type_id: int = 0,
        generacion_solicitada: bool | None = None,
    ) -> dict[str, Any]:
        """Updates generation phase."""
        payload = {}
        if generacion_completada is not None:
            payload["generacion_completada"] = generacion_completada
        if generacion_solicitada is not None:
            payload["generacion_solicitada"] = generacion_solicitada

        data = self._request(
            "PATCH",
            f"/project-version-states/{state_id}/generation?user_id={user_id}&identity_type_id={identity_type_id}",
            payload=payload,
        )
        return dict(data or {})

    def update_notification_phase(
        self,
        state_id: int,
        notificacion_enviada: bool,
        user_id: int,
        identity_type_id: int,
    ) -> dict[str, Any]:
        """Updates notification phase."""
        payload = {"notificacion_enviada": notificacion_enviada}
        data = self._request(
            "PATCH",
            f"/project-version-states/{state_id}/notification?user_id={user_id}&identity_type_id={identity_type_id}",
            payload=payload,
        )
        return dict(data or {})

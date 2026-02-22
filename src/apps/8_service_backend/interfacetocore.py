"""Capa de cliente HTTP para comunicación con backend core.

Este cliente propaga headers de seguridad (Authorization, X-Session-Token)
para mantener el contexto de sesión en todo el flujo de servicios.
"""

from __future__ import annotations

import json
from typing import Any

import httpx


class CoreBackendCommunicationError(Exception):
    """Error de comunicación con el backend core."""


class CoreBackendClient:
    """Cliente HTTP síncrono para comunicación con backend core.

    Propaga headers de seguridad para mantener el contexto de sesión:
    - Authorization: Token JWT del usuario
    - X-Session-Token: Token de sesión
    - X-Client-App: Identificador del cliente origen
    """

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client()
        self._owns_client = client is None
        self._client_app: str = "unknown"
        self._authorization: str | None = None
        self._session_token: str | None = None

    def set_client_app(self, client_app: str) -> None:
        """Configura el identificador de aplicación cliente para trazabilidad."""

        self._client_app = client_app or "unknown"

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
    ) -> Any:
        """Ejecuta una petición HTTP y valida la respuesta.

        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            path: Ruta del endpoint
            payload: Cuerpo de la petición (opcional)
            extra_headers: Headers adicionales (opcional)

        Returns:
            Respuesta deserializada como JSON

        Raises:
            CoreBackendCommunicationError: Si hay error de comunicación
        """
        url = f"{self._base_url}{path}"
        headers = self._build_headers(extra_headers)

        try:
            response = self._client.request(
                method, url, json=payload, headers=headers, timeout=10.0
            )
        except httpx.RequestError as exc:
            raise CoreBackendCommunicationError(
                "No se pudo contactar con el backend core"
            ) from exc

        if response.status_code >= 400:
            detail = ""
            try:
                error_data = response.json()
                detail = error_data.get("detail", "")
            except Exception:
                pass
            raise CoreBackendCommunicationError(
                f"Error del backend core: {response.status_code} - {detail}"
            )

        if response.content:
            try:
                return response.json()
            except json.JSONDecodeError as exc:
                raise CoreBackendCommunicationError(
                    "Respuesta del backend core no es JSON válido"
                ) from exc
        return None

    def fetch_users(self) -> list[dict[str, Any]]:
        """Obtiene la lista de usuarios."""

        data = self._request("GET", "/users")
        return list(data or [])

    def store_users(self, users: list[dict[str, Any]]) -> None:
        """Guarda la lista de usuarios."""

        self._request("PUT", "/users", payload=users)

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

    def store_roles(self, roles: list[dict[str, Any]]) -> None:
        """Guarda la lista de roles."""

        self._request("PUT", "/roles", payload=roles)

    def fetch_basic_permissions(self) -> list[dict[str, Any]]:
        """Obtiene la lista de permisos básicos."""

        data = self._request("GET", "/basic-permissions")
        return list(data or [])

    def store_basic_permissions(self, permissions: list[dict[str, Any]]) -> None:
        """Guarda la lista de permisos básicos."""

        self._request("PUT", "/basic-permissions", payload=permissions)

    def fetch_low_level_permissions(self) -> list[dict[str, Any]]:
        """Obtiene la lista de permisos de bajo nivel."""

        data = self._request("GET", "/low-level-permissions")
        return list(data or [])

    def store_low_level_permissions(self, permissions: list[dict[str, Any]]) -> None:
        """Guarda la lista de permisos de bajo nivel."""

        self._request("PUT", "/low-level-permissions", payload=permissions)

    def fetch_manage_roles(self) -> list[dict[str, Any]]:
        """Obtiene la lista de roles por organización."""

        data = self._request("GET", "/manage-roles-by-org")
        return list(data or [])

    def store_manage_roles(self, entries: list[dict[str, Any]]) -> None:
        """Guarda la lista de roles por organización."""

        self._request("PUT", "/manage-roles-by-org", payload=entries)

    def check_organization_name(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Valida si existe una organización."""

        return self._request("POST", "/organizations/check-name", payload=payload)

    def create_organization(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea una organización."""

        return self._request("POST", "/organizations", payload=payload)

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea un usuario."""

        return self._request("POST", "/users", payload=payload)

    def update_user_status(
        self, user_id: int, active: bool, requester_org_id: int, requester_identity_type_id: int = 0
    ) -> dict[str, Any]:
        """Actualiza el estado activo/inactivo de un usuario.

        Args:
            user_id: ID del usuario a modificar
            active: True para habilitar, False para deshabilitar
            requester_org_id: ID de la organización del solicitante
            requester_identity_type_id: Tipo de identidad del solicitante (1=SuperAdmin)

        Returns:
            Diccionario con user_id, active y message
        """
        return self._request(
            "PATCH",
            f"/users/{user_id}/status",
            payload={
                "active": active,
                "requester_org_id": requester_org_id,
                "requester_identity_type_id": requester_identity_type_id,
            },
        )

    def check_user_exists(self, user_name: str) -> dict[str, Any]:
        """Verifica si existe un usuario por nombre de usuario."""
        return self._request(
            "POST",
            "/users/check-exists",
            payload={"user_name": user_name},
        )

    def get_user_by_email(self, email: str) -> dict[str, Any]:
        """Obtiene datos de un usuario por email."""
        return self._request(
            "POST",
            "/users/by-email",
            payload={"email": email},
        )

    def update_user_password(
        self, email: str, new_password: str, new_otp: str
    ) -> dict[str, Any]:
        """Actualiza contraseña y OTP de un usuario."""
        return self._request(
            "POST",
            "/users/update-password",
            payload={
                "email": email,
                "new_password": new_password,
                "new_otp": new_otp,
            },
        )

    def get_permissions(self, identity_type_id: int) -> dict[str, Any]:
        """Obtiene permisos por rol."""

        return self._request(
            "GET", f"/permissions?identity_type_id={identity_type_id}"
        )

    def list_organizations(self) -> list[dict[str, Any]]:
        """Lista todas las organizaciones."""
        data = self._request("GET", "/organizations")
        return list(data or [])

    def get_accessible_organizations(
        self, user_id: int, identity_type_id: int
    ) -> list[dict[str, Any]]:
        """Returns organizations accessible to a user."""
        data = self._request(
            "GET",
            f"/accessible-organizations?user_id={user_id}&identity_type_id={identity_type_id}",
        )
        return list(data or [])

    def list_roles(self) -> list[dict[str, Any]]:
        """Lista todos los roles."""
        data = self._request("GET", "/roles")
        return list(data or [])

    def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía datos a backend core para procesamiento."""

        return self._request("POST", "/process-data", payload=payload)

    # ========================================================================
    # Gestión de Proyectos
    # ========================================================================

    def get_organization_projects(
        self,
        organization_id: int,
        headers: dict[str, str],
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """Obtiene los proyectos de una organización.

        Args:
            organization_id: ID de la organización
            headers: Headers de seguridad a propagar
            include_deleted: Si True, incluye proyectos con existe=false

        Returns:
            {"projects": [...], "total": int}
        """
        self._apply_headers(headers)
        path = f"/projects/organization/{organization_id}"
        if include_deleted:
            path += "?include_deleted=true"
        return self._request("GET", path)

    def create_project(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Crea un nuevo proyecto.

        Args:
            payload: {"nombre": str, "descripcion": str, "id_organizacion": int, ...}
            headers: Headers de seguridad a propagar

        Returns:
            {"project_id": int, "nombre": str, ...}
        """
        self._apply_headers(headers)
        return self._request("POST", "/projects", payload=payload)

    def update_project(
        self, project_id: int, update_data: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Actualiza un proyecto existente.

        Args:
            project_id: ID del proyecto
            update_data: Campos a actualizar
            headers: Headers de seguridad a propagar

        Returns:
            {"success": True, "updated": True, "project_id": int}
        """
        self._apply_headers(headers)
        return self._request(
            "PATCH",
            f"/projects/{project_id}",
            payload=update_data,
        )

    def delete_project(
        self, project_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Elimina un proyecto.

        Args:
            project_id: ID del proyecto
            headers: Headers de seguridad a propagar

        Returns:
            {"success": True, "deleted": True, "project_id": int}
        """
        self._apply_headers(headers)
        return self._request("DELETE", f"/projects/{project_id}")

    def request_project_support(
        self,
        project_id: int,
        tipo_cambio: str,
        descripcion: str,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Registra una solicitud de soporte para un proyecto.

        Args:
            project_id: ID del proyecto
            tipo_cambio: Tipo de cambio a registrar
            descripcion: Descripción de la solicitud
            headers: Headers de seguridad a propagar

        Returns:
            {"success": True, "cambio_id": int | None}
        """
        self._apply_headers(headers)
        return self._request(
            "POST",
            f"/projects/{project_id}/support",
            payload={
                "project_id": project_id,
                "tipo_cambio": tipo_cambio,
                "descripcion": descripcion,
            },
        )

    # ========================================================================
    # GESTIÓN DE ROLES DE USUARIO EN PROYECTOS
    # ========================================================================

    def get_project_roles_base(self, headers: dict[str, str]) -> dict[str, Any]:
        """Obtiene el catálogo maestro de roles base para proyectos.

        Args:
            headers: Headers de seguridad a propagar

        Returns:
            {"roles": [...], "total": int}
        """
        self._apply_headers(headers)
        return self._request("GET", "/project-roles-base")

    def get_user_project_roles(
        self, user_id: int, organization_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Obtiene los roles de un usuario en proyectos.

        Args:
            user_id: ID del usuario
            organization_id: ID de la organización
            headers: Headers de seguridad a propagar

        Returns:
            {"user_id": int, "organization_id": int, "roles": [...], "total": int}
        """
        self._apply_headers(headers)
        return self._request(
            "GET",
            f"/users/{user_id}/project-roles?organization_id={organization_id}",
        )

    def assign_user_to_project(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Asigna un usuario a un proyecto.

        Args:
            payload: {"id_usuario": int, "id_proyecto": int, "id_organizacion": int, "id_rol": int}
            headers: Headers de seguridad a propagar

        Returns:
            {"success": bool, "message": str, ...}
        """
        self._apply_headers(headers)
        return self._request("POST", "/project-roles/assign", payload=payload)

    def remove_user_from_project(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Quita un usuario de un proyecto.

        Args:
            payload: {"id_usuario": int, "id_proyecto": int, "id_organizacion": int}
            headers: Headers de seguridad a propagar

        Returns:
            {"success": bool, "message": str, ...}
        """
        self._apply_headers(headers)
        return self._request("POST", "/project-roles/remove", payload=payload)

    # ========================================================================
    # GESTIÓN DE TICKETS DE SOPORTE
    # ========================================================================

    def create_ticket(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Crea un nuevo ticket de soporte."""
        self._apply_headers(headers)
        return self._request("POST", "/tickets", payload=payload)

    def get_organization_tickets(
        self, organization_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Obtiene los tickets de una organización."""
        self._apply_headers(headers)
        return self._request("GET", f"/tickets/organization/{organization_id}")

    def get_ticket_detail(
        self, ticket_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Obtiene el detalle de un ticket específico."""
        self._apply_headers(headers)
        return self._request("GET", f"/tickets/{ticket_id}")

    def update_ticket(
        self, ticket_id: int, update_data: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Actualiza estado/prioridad de un ticket."""
        self._apply_headers(headers)
        return self._request("PATCH", f"/tickets/{ticket_id}", payload=update_data)

    def add_ticket_response(
        self, ticket_id: int, respuesta: str, user_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Añade respuesta a un ticket."""
        self._apply_headers(headers)
        return self._request(
            "POST",
            f"/tickets/{ticket_id}/respuesta",
            payload={"respuesta": respuesta, "user_id": user_id},
        )

    # ========================================================================
    # GESTIÓN DE CONVERSACIONES Y CAMBIOS
    # ========================================================================

    def get_user_conversation(
        self, user_id: int, org_id: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Busca conversación abierta de un usuario."""
        self._apply_headers(headers)
        return self._request("GET", f"/conversations/user/{user_id}?org_id={org_id}")

    def create_conversation(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Crea una nueva conversación."""
        self._apply_headers(headers)
        return self._request("POST", "/conversations", payload=payload)

    def get_conversation_messages(
        self, conversation_id: int, headers: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Obtiene los mensajes de una conversación."""
        self._apply_headers(headers)
        return self._request("GET", f"/conversations/{conversation_id}/messages")

    def send_conversation_message(
        self, conversation_id: int, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Envía un mensaje en una conversación."""
        self._apply_headers(headers)
        return self._request(
            "POST", f"/conversations/{conversation_id}/messages", payload=payload
        )

    def mark_conversation_read(
        self, conversation_id: int, payload: dict[str, str], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Marca mensajes como leídos."""
        self._apply_headers(headers)
        return self._request(
            "POST", f"/conversations/{conversation_id}/mark-read", payload=payload
        )

    def get_cambios_calendar(
        self,
        org_id: int,
        headers: dict[str, str],
        mes: int | None = None,
        anio: int | None = None,
        proyecto_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Obtiene eventos del calendario."""
        self._apply_headers(headers)
        params = []
        if mes is not None:
            params.append(f"mes={mes}")
        if anio is not None:
            params.append(f"anio={anio}")
        if proyecto_id is not None:
            params.append(f"proyecto_id={proyecto_id}")
        qs = f"?{'&'.join(params)}" if params else ""
        return self._request("GET", f"/cambios/organization/{org_id}{qs}")

    # ========================================================================
    # CONVERSACIONES - BACKOFFICE
    # ========================================================================

    def get_organization_conversations(
        self,
        org_id: int,
        headers: dict[str, str],
        solo_activas: bool = True,
    ) -> list[dict[str, Any]]:
        """Obtiene conversaciones de una organización."""
        self._apply_headers(headers)
        qs = f"?solo_activas={str(solo_activas).lower()}"
        return self._request("GET", f"/conversations/organization/{org_id}{qs}")

    def join_conversation(
        self,
        conversation_id: int,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Un usuario interno se une a una conversación."""
        self._apply_headers(headers)
        return self._request(
            "POST", f"/conversations/{conversation_id}/join", payload=payload
        )

    def get_conversation_detail(
        self,
        conversation_id: int,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Obtiene detalle de una conversación."""
        self._apply_headers(headers)
        return self._request("GET", f"/conversations/{conversation_id}/detail")

    def update_conversation_priority(
        self,
        conversation_id: int,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Actualiza la prioridad de una conversación."""
        self._apply_headers(headers)
        return self._request(
            "PATCH", f"/conversations/{conversation_id}/priority", payload=payload
        )

    def update_conversation_state(
        self,
        conversation_id: int,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Actualiza el estado de una conversación."""
        self._apply_headers(headers)
        return self._request(
            "PATCH", f"/conversations/{conversation_id}/state", payload=payload
        )

    def get_ticket_details(
        self,
        ticket_id: int,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Obtiene detalles de un ticket."""
        self._apply_headers(headers)
        return self._request("GET", f"/tickets/{ticket_id}/details")

    def save_ticket_interaction(
        self,
        ticket_id: int,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Guarda interacción de ticket."""
        self._apply_headers(headers)
        return self._request(
            "POST", f"/tickets/{ticket_id}/interactions", payload=payload
        )

    # ========================================================================
    # GESTIÓN DE TECNOLOGÍAS
    # ========================================================================

    def get_tecnologias(self) -> dict[str, Any]:
        """Obtiene todas las tecnologías disponibles."""
        return self._request("GET", "/tecnologias")

    def get_proyecto_tecnologia(self, project_id: int) -> dict[str, Any]:
        """Obtiene la tecnología asignada a un proyecto."""
        return self._request("GET", f"/proyectos/{project_id}/tecnologia")

    def asignar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Asigna una tecnología a un proyecto."""
        return self._request("POST", f"/proyectos/{project_id}/tecnologia", payload=payload)

    def actualizar_tecnologia(
        self, project_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza la tecnología de un proyecto."""
        return self._request("PATCH", f"/proyectos/{project_id}/tecnologia", payload=payload)

    def get_tecnologias_asignadas_org(self, org_id: int) -> dict[str, Any]:
        """Obtiene todas las tecnologías asignadas a proyectos de una organización."""
        return self._request("GET", f"/organizaciones/{org_id}/tecnologias-asignadas")

    # ========================================================================
    # GESTIÓN DE VERSIONES
    # ========================================================================

    def get_project_versions(self, project_id: int, org_id: int) -> dict[str, Any]:
        """Obtiene todas las versiones de un proyecto."""
        return self._request("GET", f"/proyectos/{project_id}/versiones?org_id={org_id}")

    def create_project_version(self, project_id: int, org_id: int) -> dict[str, Any]:
        """Crea una nueva versión para un proyecto."""
        payload = {"id_proyecto": project_id, "id_organizacion": org_id}
        return self._request("POST", f"/proyectos/{project_id}/versiones", payload=payload)

    # Métodos de Estados de Versión
    # ================================================================

    def get_version_state(
        self, project_id: int, version_id: int, org_id: int
    ) -> dict[str, Any]:
        """Obtiene el estado actual de una versión."""
        return self._request(
            "GET",
            f"/proyectos/{project_id}/versiones/{version_id}/estado?org_id={org_id}",
        )

    def update_version_state(
        self,
        project_id: int,
        version_id: int,
        org_id: int,
        update_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Actualiza el estado de una versión."""
        return self._request(
            "PATCH",
            f"/proyectos/{project_id}/versiones/{version_id}/estado?org_id={org_id}",
            payload=update_data,
        )

    def get_version_events(
        self, project_id: int, version_id: int, org_id: int, limit: int = 50
    ) -> dict[str, Any]:
        """Obtiene el historial de eventos de una versión."""
        return self._request(
            "GET",
            f"/proyectos/{project_id}/versiones/{version_id}/eventos?org_id={org_id}&limit={limit}",
        )

    def create_version_full(
        self, project_id: int, request_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Crea una versión completa (DB + fmanagement)."""
        return self._request(
            "POST",
            f"/proyectos/{project_id}/versiones/crear-completa",
            payload=request_data,
        )

    # Métodos de Integración con fmanagement
    # ================================================================

    def fmanagement_list(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Lista estructura de archivos vía fmanagement."""
        return self._request(
            "POST",
            "/fmanagement/list",
            payload=request_data,
        )

    def fmanagement_operation(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta una operación genérica en fmanagement."""
        return self._request(
            "POST",
            "/fmanagement/operation",
            payload=request_data,
        )

    def fmanagement_download(self, request_data: dict[str, Any]) -> bytes:
        """Descarga un archivo vía fmanagement."""
        url = f"{self._base_url}/fmanagement/operation"
        headers = self._build_headers()
        
        try:
            # Forzamos la operación a download_file si no viene
            if "operation" not in request_data:
                request_data["operation"] = "download_file"
                
            response = self._client.post(url, json=request_data, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.content
        except Exception as exc:
            raise CoreBackendCommunicationError(f"Error descargando archivo: {exc}") from exc

    def fmanagement_diff(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Compara versiones vía fmanagement."""
        payload = {
            "operation": "diff",
            "params": request_data
        }
        return self.fmanagement_operation(payload)

    def fmanagement_transfer(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Transfiere versiones vía fmanagement."""
        payload = {
            "operation": "transfer",
            "params": request_data
        }
        return self.fmanagement_operation(payload)

    def _apply_headers(self, headers: dict[str, str]) -> None:
        """Aplica headers de seguridad al contexto del cliente.

        Args:
            headers: Headers a aplicar (Authorization, X-Session-Token, X-Client-App)
        """
        if headers.get("Authorization"):
            self._authorization = headers["Authorization"]
        if headers.get("X-Session-Token"):
            self._session_token = headers["X-Session-Token"]
        if headers.get("X-Client-App"):
            self._client_app = headers["X-Client-App"]

    # ========================================================================
    # ASSIGNMENTS MANAGER - Gestor de asignaciones
    # ========================================================================

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
        payload = {"active": active}
        data = self._request(
            "PATCH",
            f"/assignments/organizations/{assignment_id}?identity_type_id={identity_type_id}",
            payload=payload,
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
        payload = {"active": active}
        data = self._request(
            "PATCH",
            f"/assignments/projects/{assignment_id}?identity_type_id={identity_type_id}",
            payload=payload,
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
        payload: dict[str, Any] = {
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

    def get_pending_training_versions(self) -> dict[str, Any]:
        """Obtiene versiones con entrenamiento inicial solicitado."""
        data = self._request("GET", "/training/pending-versions")
        return dict(data or {"versions": [], "total": 0})

    # ================================================================
    # Training - Registro y seguimiento de entrenamientos
    # ================================================================

    def get_training_params(
        self, org_id: int, project_id: int, version_id: int
    ) -> dict[str, Any]:
        """Obtiene parámetros de entrenamiento inteligentes desde Backend Core.

        Devuelve defaults (primer entrenamiento) o los parámetros del último
        job (reentrenamiento), junto con flags informativos y lista de modelos.
        """
        data = self._request(
            "GET",
            f"/training/params/{org_id}/{project_id}/{version_id}",
        )
        return dict(data or {})

    def list_active_models(self) -> dict[str, Any]:
        """Lista modelos activos desde Backend Core."""
        data = self._request("GET", "/models/active")
        return dict(data or {})

    def register_entrenamiento(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Registra un nuevo entrenamiento en Backend Core."""
        data = self._request("POST", "/entrenamientos/register", payload=payload)
        return dict(data or {})

    def update_entrenamiento_phase(
        self, id_entrenamiento: int, fase_actual: str
    ) -> dict[str, Any]:
        """Actualiza la fase de un entrenamiento en Backend Core."""
        payload = {"fase_actual": fase_actual}
        data = self._request(
            "PATCH",
            f"/entrenamientos/{id_entrenamiento}/phase",
            payload=payload,
        )
        return dict(data or {})

    def complete_entrenamiento(
        self, id_entrenamiento: int, modelo_path: str
    ) -> dict[str, Any]:
        """Marca un entrenamiento como completado en Backend Core."""
        payload = {"modelo_path": modelo_path}
        data = self._request(
            "PATCH",
            f"/entrenamientos/{id_entrenamiento}/complete",
            payload=payload,
        )
        return dict(data or {})

    def error_entrenamiento(
        self, id_entrenamiento: int, error_mensaje: str
    ) -> dict[str, Any]:
        """Marca un entrenamiento como error en Backend Core."""
        payload = {"error_mensaje": error_mensaje}
        data = self._request(
            "PATCH",
            f"/entrenamientos/{id_entrenamiento}/error",
            payload=payload,
        )
        return dict(data or {})

    def cancel_entrenamiento(
        self, id_entrenamiento: int, motivo: str = "Cancelado por usuario"
    ) -> dict[str, Any]:
        """Cancela un entrenamiento en progreso en Backend Core."""
        payload = {"motivo": motivo}
        data = self._request(
            "PATCH",
            f"/entrenamientos/{id_entrenamiento}/cancel",
            payload=payload,
        )
        return dict(data or {})

    async def update_training_progress(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Envía notificación de progreso al Backend Core."""
        data = self._request("PATCH", "/training/progress", payload=payload)
        return dict(data or {})

    async def get_training_progress(self, id_entrenamiento: int) -> dict[str, Any]:
        """Consulta el progreso actual de un entrenamiento."""
        data = self._request(
            "GET",
            f"/training/entrenamientos/{id_entrenamiento}/progress"
        )
        return dict(data or {})

    # ========================================================================
    # Entrenamiento Autónomo (fases 6-9)
    # ========================================================================

    async def initialize_autonomous_training(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Inicializa registro de entrenamiento autónomo en Backend Core."""
        data = self._request("POST", "/training/autonomous/init", payload=payload)
        return dict(data or {})

    async def update_autonomous_metadata(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza metadatos de entrenamiento autónomo en Backend Core."""
        data = self._request("PATCH", "/training/autonomous/metadata", payload=payload)
        return dict(data or {})

    async def get_autonomous_progress(
        self, id_entrenamiento: int
    ) -> dict[str, Any]:
        """Consulta el progreso del entrenamiento autónomo (fases 6-9)."""
        data = self._request(
            "GET",
            f"/training/autonomous/{id_entrenamiento}/progress"
        )
        return dict(data or {})

    async def list_autonomous_packages(
        self,
        id_organizacion: int | None = None,
        id_proyecto: int | None = None,
        id_version: int | None = None,
    ) -> dict[str, Any]:
        """Lista paquetes autónomos disponibles desde Backend Core."""
        params = {}
        if id_organizacion is not None:
            params["id_organizacion"] = id_organizacion
        if id_proyecto is not None:
            params["id_proyecto"] = id_proyecto
        if id_version is not None:
            params["id_version"] = id_version

        # Build query string
        query_parts = [f"{k}={v}" for k, v in params.items()]
        query_string = "&".join(query_parts)
        path = "/training/autonomous/packages"
        if query_string:
            path = f"{path}?{query_string}"

        data = self._request("GET", path)
        return dict(data or {})

    # ========================================================================
    # INFORMES
    # ========================================================================

    def list_informe_files(
        self, org_id: int, project_id: int, version_id: int
    ) -> dict[str, Any]:
        """Lista archivos markdown de informes para una versión."""
        data = self._request(
            "GET",
            f"/informes/{org_id}/{project_id}/{version_id}/files",
        )
        return dict(data or {})

    def get_informe_content(
        self, org_id: int, project_id: int, version_id: int, display_name: str
    ) -> dict[str, Any]:
        """Obtiene el contenido de un archivo markdown de informe."""
        from urllib.parse import quote
        data = self._request(
            "GET",
            f"/informes/{org_id}/{project_id}/{version_id}/content?file={quote(display_name)}",
        )
        return dict(data or {})

    # ========================================================================
    # MODEL PACKAGES
    # ========================================================================

    def list_model_packages(self, org_id: int | None = None) -> dict[str, Any]:
        """Lista paquetes ZIP de modelos disponibles para descarga."""
        params = f"?org_id={org_id}" if org_id is not None else ""
        data = self._request(
            "GET",
            f"/models/packages{params}",
        )
        return dict(data or {})

    def download_model_package(
        self, org_id: int, project_id: int, version_id: int, filename: str
    ) -> bytes:
        """Descarga un paquete ZIP de modelo desde backend core."""
        from urllib.parse import quote
        url = (
            f"{self._base_url}/models/packages/download"
            f"?org_id={org_id}&project_id={project_id}"
            f"&version_id={version_id}&filename={quote(filename)}"
        )
        headers: dict[str, str] = {"X-Client-App": self._client_app}
        try:
            response = self._client.get(url, headers=headers, timeout=60.0)
            response.raise_for_status()
            return response.content
        except Exception as exc:
            raise CoreBackendCommunicationError(
                f"Error descargando modelo del backend core: {exc}"
            ) from exc

    # === JOB TEMPLATES ===

    def get_job_template_catalogs(self) -> dict[str, Any]:
        """Obtiene catálogos de job templates."""
        return dict(self._request("GET", "/job-templates/catalogs") or {})

    def get_job_templates(self) -> list[dict[str, Any]]:
        """Lista plantillas de jobs."""
        return list(self._request("GET", "/job-templates") or [])

    def save_job_template(self, data: dict[str, Any]) -> dict[str, Any]:
        """Crea o actualiza una plantilla de job."""
        return dict(self._request("POST", "/job-templates", payload=data) or {})

    def toggle_job_template(self, template_id: int) -> dict[str, Any]:
        """Activa/desactiva una plantilla de job."""
        return dict(self._request("PATCH", f"/job-templates/{template_id}/toggle") or {})

    # ========================================================================
    # JOBS
    # ========================================================================

    def get_jobs(
        self, org_id: int, project_id: int, version_id: int, tipo_clave: str | None = None
    ) -> list[dict[str, Any]]:
        """Lista jobs filtrados por org/proyecto/versión."""
        params = f"?org_id={org_id}&project_id={project_id}&version_id={version_id}"
        if tipo_clave:
            params += f"&tipo_clave={tipo_clave}"
        return list(self._request("GET", f"/jobs{params}") or [])

    def create_job(self, data: dict[str, Any]) -> dict[str, Any]:
        """Crea un nuevo job."""
        return dict(self._request("POST", "/jobs", payload=data) or {})

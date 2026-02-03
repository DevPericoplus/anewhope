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
        self, user_id: int, active: bool, requester_org_id: int
    ) -> dict[str, Any]:
        """Actualiza el estado activo/inactivo de un usuario.
        
        Args:
            user_id: ID del usuario a modificar
            active: True para habilitar, False para deshabilitar
            requester_org_id: ID de la organización del solicitante
        
        Returns:
            Diccionario con user_id, active y message
        """
        return self._request(
            "PATCH",
            f"/users/{user_id}/status",
            payload={
                "active": active,
                "requester_org_id": requester_org_id,
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

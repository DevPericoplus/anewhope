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

    def get_permissions(self, identity_type_id: int) -> dict[str, Any]:
        """Obtiene permisos por rol."""

        return self._request(
            "GET", f"/permissions?identity_type_id={identity_type_id}"
        )

    def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía datos a backend core para procesamiento."""

        return self._request("POST", "/process-data", payload=payload)


"""Capa de cliente HTTP para comunicación con backend core."""

from __future__ import annotations

import json
from typing import Any

import httpx


class CoreBackendCommunicationError(Exception):
    """Error de comunicación con el backend core."""


class CoreBackendClient:
    """Cliente HTTP síncrono para comunicación con backend core."""

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client()
        self._owns_client = client is None

    def close(self) -> None:
        """Cierra el cliente HTTP si es propio."""

        if self._owns_client:
            self._client.close()

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | list[Any] | None = None
    ) -> Any:
        """Ejecuta una petición HTTP y valida la respuesta."""

        url = f"{self._base_url}{path}"
        try:
            response = self._client.request(method, url, json=payload, timeout=10.0)
        except httpx.RequestError as exc:
            raise CoreBackendCommunicationError(
                "No se pudo contactar con el backend core"
            ) from exc

        if response.status_code >= 400:
            raise CoreBackendCommunicationError(
                f"Error del backend core: {response.status_code}"
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

    def fetch_basic_permissions(self) -> list[dict[str, Any]]:
        """Obtiene la lista de permisos básicos."""

        data = self._request("GET", "/basic-permissions")
        return list(data or [])

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


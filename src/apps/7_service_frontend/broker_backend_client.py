"""Cliente síncrono para comunicación con el broker backend."""

from __future__ import annotations

import json
from typing import Any

import httpx


class BrokerBackendCommunicationError(Exception):
    """Error de comunicación con el broker backend."""


class BrokerBackendClient:
    """Cliente HTTP síncrono para operaciones de persistencia."""

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client()
        self._owns_client = client is None
        self._client_app: str = "middleware"

    def set_client_app(self, client_app: str) -> None:
        """Configura el identificador de aplicación cliente para trazabilidad."""

        self._client_app = client_app or "middleware"

    def close(self) -> None:
        """Cierra el cliente HTTP si es propio."""

        if self._owns_client:
            self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | list[Any] | None = None,
        client_app: str | None = None,
    ) -> Any:
        """Ejecuta una petición HTTP y valida la respuesta."""

        url = f"{self._base_url}{path}"
        headers = {"X-Client-App": client_app or self._client_app}
        try:
            response = self._client.request(
                method, url, json=payload, headers=headers, timeout=10.0
            )
        except httpx.RequestError as exc:
            raise BrokerBackendCommunicationError(
                "No se pudo contactar con el broker backend"
            ) from exc

        if response.status_code >= 400:
            raise BrokerBackendCommunicationError(
                f"Error del broker backend: {response.status_code}"
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


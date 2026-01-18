"""Capa de cliente HTTP para comunicación con el backend."""

from __future__ import annotations

import json
from typing import Any

import httpx


class BackendCommunicationError(Exception):
    """Error de comunicación con el backend."""


class InterfaceToBackend:
    """Cliente HTTP asíncrono para comunicación con el backend."""

    def __init__(self, client: httpx.AsyncClient, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía datos al backend y retorna la respuesta parseada."""

        try:
            response = await self._client.post(
                f"{self._base_url}/process-data", json=payload, timeout=10.0
            )
        except httpx.RequestError as exc:
            raise BackendCommunicationError(
                "No se pudo contactar con el backend"
            ) from exc

        if response.status_code >= 400:
            raise BackendCommunicationError(
                f"Error del backend: {response.status_code}"
            )

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise BackendCommunicationError(
                "Respuesta del backend no es JSON válido"
            ) from exc

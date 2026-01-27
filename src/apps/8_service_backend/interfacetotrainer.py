"""Capa de cliente HTTP para comunicación con backend IA (trainer).

Este cliente propaga headers de seguridad (Authorization, X-Session-Token)
para mantener el contexto de sesión en todo el flujo de servicios.
"""

from __future__ import annotations

import json
from typing import Any

import httpx


class TrainerBackendCommunicationError(Exception):
    """Error de comunicación con el backend IA (trainer)."""


class TrainerBackendClient:
    """Cliente HTTP síncrono para comunicación con backend IA (trainer).

    Este cliente gestiona las peticiones al Backend IA para operaciones
    de entrenamiento, modelos y métricas. Propaga headers de seguridad
    para mantener el contexto de sesión:
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
            TrainerBackendCommunicationError: Si hay error de comunicación
        """
        url = f"{self._base_url}{path}"
        headers = self._build_headers(extra_headers)

        try:
            response = self._client.request(
                method, url, json=payload, headers=headers, timeout=30.0
            )
        except httpx.RequestError as exc:
            raise TrainerBackendCommunicationError(
                "No se pudo contactar con el backend IA (trainer)"
            ) from exc

        if response.status_code >= 400:
            detail = ""
            try:
                error_data = response.json()
                detail = error_data.get("detail", "")
            except Exception:
                pass
            raise TrainerBackendCommunicationError(
                f"Error del backend IA: {response.status_code} - {detail}"
            )

        if response.content:
            try:
                return response.json()
            except json.JSONDecodeError as exc:
                raise TrainerBackendCommunicationError(
                    "Respuesta del backend IA no es JSON válido"
                ) from exc
        return None

    # === Health Check ===

    def health_check(self) -> dict[str, Any]:
        """Verifica el estado del servicio trainer."""

        return self._request("GET", "/trainer/health")

    # === Operaciones de Versión ===

    def clone_version(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Clona una versión para entrenamiento.

        Args:
            payload: Datos de la versión (id_user, id_organization, id_project, version_path)

        Returns:
            Resultado del clonado con path de destino
        """
        return self._request("POST", "/trainer/version/clone", payload=payload)

    def get_version_files(
        self,
        version_id: int,
        identity_type_id: int | None = None,
    ) -> dict[str, Any]:
        """Lista archivos de una versión clonada.

        Args:
            version_id: ID de la versión
            identity_type_id: ID del rol para validación

        Returns:
            Lista de archivos
        """
        params = f"?identity_type_id={identity_type_id}" if identity_type_id else ""
        return self._request("GET", f"/trainer/version/{version_id}/files{params}")

    # === Operaciones de Entrenamiento ===

    def start_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Inicia un proceso de entrenamiento.

        Args:
            payload: Configuración del entrenamiento

        Returns:
            ID del entrenamiento iniciado
        """
        return self._request("POST", "/trainer/training/start", payload=payload)

    def stop_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Detiene un proceso de entrenamiento.

        Args:
            payload: Datos del entrenamiento a detener

        Returns:
            Confirmación de detención
        """
        return self._request("POST", "/trainer/training/stop", payload=payload)

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
        return self._request(
            "GET", f"/trainer/training/{training_id}/status{params}"
        )

    # === Operaciones de Modelos ===

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
        return self._request("GET", f"/trainer/models{query}")

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
        return self._request("GET", f"/trainer/models/{model_id}/metrics{params}")

    # === Permisos ===

    def get_training_permissions(self, identity_type_id: int) -> dict[str, Any]:
        """Obtiene permisos de entrenamiento para un rol.

        Args:
            identity_type_id: ID del rol

        Returns:
            Diccionario con permisos de entrenamiento
        """
        return self._request(
            "GET", f"/trainer/permissions?identity_type_id={identity_type_id}"
        )

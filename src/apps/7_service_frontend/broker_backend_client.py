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
            BrokerBackendCommunicationError: Si hay error de comunicación
        """
        url = f"{self._base_url}{path}"
        headers = self._build_headers(extra_headers)

        try:
            response = self._client.request(
                method, url, json=payload, headers=headers, timeout=10.0
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


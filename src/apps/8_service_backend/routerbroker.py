"""Capa de orquestación del broker backend."""

from __future__ import annotations

import logging
from typing import Any

try:
    from .interfacetocore import CoreBackendClient, CoreBackendCommunicationError
except ImportError:  # pragma: no cover - soporte para ejecuciones fuera de paquete
    import importlib.util
    from pathlib import Path

    _module_path = Path(__file__).resolve().parent / "interfacetocore.py"
    _spec = importlib.util.spec_from_file_location("interfacetocore", _module_path)
    if _spec is None or _spec.loader is None:
        raise
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)

    CoreBackendClient = _module.CoreBackendClient
    CoreBackendCommunicationError = _module.CoreBackendCommunicationError


class BrokerBusinessError(Exception):
    """Error de reglas de negocio del broker."""


class BrokerBackendRouter:
    """Orquestador de operaciones del broker backend."""

    def __init__(self, core_client: CoreBackendClient) -> None:
        self._core_client = core_client
        self._logger = logging.getLogger("broker_backend.router")
        self._client_app: str = "unknown"

    def set_client_app(self, client_app: str) -> None:
        """Configura el identificador de aplicación cliente para trazabilidad."""

        self._client_app = client_app or "unknown"
        self._core_client.set_client_app(self._client_app)

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

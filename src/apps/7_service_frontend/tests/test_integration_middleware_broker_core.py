"""Tests de integración middleware -> broker -> core."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any
from fastapi.testclient import TestClient


def _load_module(module_name: str, module_path: Path) -> Any:
    """Carga un módulo desde una ruta absoluta."""

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el módulo {module_name}")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: Any) -> None:
    """Escribe JSON en disco."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)


def test_middleware_broker_core_flow(tmp_path: Path, monkeypatch: Any) -> None:
    """Valida el flujo de lectura desde broker hacia core."""

    core_path = Path(__file__).resolve().parents[2] / "3_backend" / "apicore.py"
    broker_path = Path(__file__).resolve().parents[2] / "8_service_backend" / "apibe.py"
    middleware_path = Path(__file__).resolve().parents[1] / "apife.py"

    apicore = _load_module("apicore", core_path)
    apibe = _load_module("apibe", broker_path)
    apife = _load_module("apife", middleware_path)

    users_path = tmp_path / "users.json"
    organizations_path = tmp_path / "organizations.json"
    roles_path = tmp_path / "roles.json"
    permissions_path = tmp_path / "basic_permissions.json"
    low_level_permissions_path = tmp_path / "low_level_permissions.json"
    manage_roles_path = tmp_path / "manage_roles.json"

    _write_json(users_path, [])
    _write_json(
        organizations_path,
        [
            {
                "organization_id": 1,
                "organization_name": "Demo Org",
                "organization_email": "demo@org.com",
                "organization_tlf": "",
                "organization_address": "",
                "organization_country": "",
                "organization_state": "",
            }
        ],
    )
    _write_json(
        roles_path,
        [
            {
                "identity_type_id": 2,
                "identity_type_name": "Admin",
                "identity_type_rol": "Administrator",
                "identity_type_group_permissions": [1],
            }
        ],
    )
    _write_json(
        permissions_path,
        [
            {
                "id": 1,
                "PermissionName": "read_users",
                "PermissionDescription": "Permite leer usuarios",
            }
        ],
    )
    _write_json(
        low_level_permissions_path,
        [
            {
                "id_permissions": 1,
                "folder_create": True,
                "folder_delete": True,
                "folder_rename": True,
                "folder_read": True,
                "file_create": True,
                "file_read": True,
                "file_update": True,
                "file_delete": True,
                "project_create": True,
                "project_read": True,
                "project_update": True,
                "project_delete": True,
                "version_create": True,
                "version_read": True,
                "version_update": True,
                "version_delete": True,
                "training_create": True,
                "training_read": True,
                "training_update": True,
                "training_delete": True,
                "training_start": True,
                "training_stop": True,
                "parameters_create": True,
                "parameters_read": True,
                "parameters_update": True,
                "parameters_delete": True,
                "notifications_create": True,
                "notifications_read": True,
                "notifications_update": True,
                "notifications_delete": True,
                "user_create": True,
                "user_read": True,
                "user_update": True,
                "user_delete": True,
                "user_enable": True,
                "user_disable": True,
                "folder_list": True,
                "file_list": True,
                "project_list": True,
                "version_list": True,
            }
        ],
    )
    _write_json(manage_roles_path, [])

    def _get_adapter() -> Any:
        return apicore.JsonMockStorageAdapter(
            users_path=users_path,
            organizations_path=organizations_path,
            roles_path=roles_path,
            basic_permissions_path=permissions_path,
            low_level_permissions_path=low_level_permissions_path,
            manage_roles_path=manage_roles_path,
        )

    apicore.app.dependency_overrides[apicore.get_storage_adapter] = _get_adapter

    core_client = TestClient(apicore.app)

    class FakeCoreClient:
        """Cliente core en memoria para tests."""

        def __init__(self) -> None:
            self._client_app: str = "test"
            self._authorization: str | None = None
            self._session_token: str | None = None

        def set_client_app(self, client_app: str) -> None:
            """Configura el identificador de cliente para trazabilidad."""
            self._client_app = client_app

        def set_security_context(
            self,
            authorization: str | None = None,
            session_token: str | None = None,
        ) -> None:
            """Configura el contexto de seguridad."""
            self._authorization = authorization
            self._session_token = session_token

        def fetch_users(self) -> list[dict[str, Any]]:
            return core_client.get("/users").json()

        def store_users(self, users: list[dict[str, Any]]) -> None:
            core_client.put("/users", json=users)

        def fetch_organizations(self) -> list[dict[str, Any]]:
            return core_client.get("/organizations").json()

        def store_organizations(self, organizations: list[dict[str, Any]]) -> None:
            core_client.put("/organizations", json=organizations)

        def fetch_roles(self) -> list[dict[str, Any]]:
            return core_client.get("/roles").json()

        def fetch_basic_permissions(self) -> list[dict[str, Any]]:
            return core_client.get("/basic-permissions").json()

        def fetch_low_level_permissions(self) -> list[dict[str, Any]]:
            return core_client.get("/low-level-permissions").json()

        def fetch_manage_roles(self) -> list[dict[str, Any]]:
            return core_client.get("/manage-roles-by-org").json()

        def store_manage_roles(self, entries: list[dict[str, Any]]) -> None:
            core_client.put("/manage-roles-by-org", json=entries)

        def check_organization_name(self, payload: dict[str, Any]) -> dict[str, Any]:
            return core_client.post("/organizations/check-name", json=payload).json()

        def create_organization(self, payload: dict[str, Any]) -> dict[str, Any]:
            return core_client.post("/organizations", json=payload).json()

        def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
            return core_client.post("/users", json=payload).json()

        def get_permissions(self, identity_type_id: int) -> dict[str, Any]:
            return core_client.get(
                "/permissions", params={"identity_type_id": identity_type_id}
            ).json()

        def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
            return core_client.post("/process-data", json={"payload": payload}).json()

    def _get_core_client() -> Any:
        return FakeCoreClient()

    apibe.app.dependency_overrides[apibe.get_core_client] = _get_core_client

    broker_app_client = TestClient(apibe.app)

    class FakeBrokerClient:
        """Cliente broker en memoria para tests."""

        def __init__(self) -> None:
            self._client_app: str = "test"
            self._authorization: str | None = None
            self._session_token: str | None = None

        def set_client_app(self, client_app: str) -> None:
            """Configura el identificador de cliente para trazabilidad."""
            self._client_app = client_app

        def set_security_context(
            self,
            authorization: str | None = None,
            session_token: str | None = None,
        ) -> None:
            """Configura el contexto de seguridad."""
            self._authorization = authorization
            self._session_token = session_token

        def fetch_users(self) -> list[dict[str, Any]]:
            return broker_app_client.get("/users").json()

        def store_users(self, users: list[dict[str, Any]]) -> None:
            broker_app_client.put("/users", json=users)

        def fetch_organizations(self) -> list[dict[str, Any]]:
            return broker_app_client.get("/organizations").json()

        def store_organizations(self, organizations: list[dict[str, Any]]) -> None:
            broker_app_client.put("/organizations", json=organizations)

        def fetch_roles(self) -> list[dict[str, Any]]:
            return broker_app_client.get("/roles").json()

        def fetch_basic_permissions(self) -> list[dict[str, Any]]:
            return broker_app_client.get("/basic-permissions").json()

        def fetch_low_level_permissions(self) -> list[dict[str, Any]]:
            return broker_app_client.get("/low-level-permissions").json()

        def fetch_manage_roles(self) -> list[dict[str, Any]]:
            return broker_app_client.get("/manage-roles-by-org").json()

        def store_manage_roles(self, entries: list[dict[str, Any]]) -> None:
            broker_app_client.put("/manage-roles-by-org", json=entries)

        def check_organization_name(self, payload: dict[str, Any]) -> dict[str, Any]:
            return broker_app_client.post(
                "/organizations/check-name", json=payload
            ).json()

        def create_organization(self, payload: dict[str, Any]) -> dict[str, Any]:
            return broker_app_client.post("/organizations", json=payload).json()

        def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
            return broker_app_client.post("/users", json=payload).json()

        def get_permissions(self, identity_type_id: int) -> dict[str, Any]:
            return broker_app_client.get(
                "/permissions", params={"identity_type_id": identity_type_id}
            ).json()

        def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
            return broker_app_client.post("/process-data", json={"payload": payload}).json()

    def _get_broker_client() -> Any:
        return FakeBrokerClient()

    apife.app.dependency_overrides[apife.get_broker_client] = _get_broker_client

    monkeypatch.setenv("STORAGE_MODE", "mock")
    monkeypatch.setenv("BROKER_BACKEND_BASE_URL", "http://broker")
    monkeypatch.setenv("ORGANIZATIONS_DATA_PATH", str(organizations_path))
    monkeypatch.setenv("USERS_DATA_PATH", str(users_path))
    monkeypatch.setenv("ROLES_DATA_PATH", str(roles_path))

    client = TestClient(apife.app)
    response = client.post(
        "/organizations/check-name", json={"organization_name": "Demo Org"}
    )

    assert response.status_code == 200
    assert response.json()["exists"] is True

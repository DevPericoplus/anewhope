"""Tests básicos del broker backend."""

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


def _bootstrap_core_mocks(tmp_path: Path) -> dict[str, Path]:
    """Crea mocks para el backend core."""

    paths = {
        "users": tmp_path / "users.json",
        "organizations": tmp_path / "organizations.json",
        "roles": tmp_path / "roles.json",
        "basic_permissions": tmp_path / "basic_permissions.json",
        "low_level_permissions": tmp_path / "low_level_permissions.json",
        "manage_roles": tmp_path / "manage_roles_by_org.json",
    }
    _write_json(paths["users"], [])
    _write_json(paths["organizations"], [])
    _write_json(
        paths["roles"],
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
        paths["basic_permissions"],
        [
            {
                "id": 1,
                "PermissionName": "read_users",
                "PermissionDescription": "Permite leer usuarios",
            }
        ],
    )
    _write_json(
        paths["low_level_permissions"],
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
    _write_json(paths["manage_roles"], [])
    return paths


def test_broker_routes(tmp_path: Path) -> None:
    """Valida endpoints del broker con core en memoria."""

    core_path = Path(__file__).resolve().parents[2] / "3_backend" / "apicore.py"
    broker_path = Path(__file__).resolve().parents[1] / "apibe.py"

    apicore = _load_module("apicore", core_path)
    apibe = _load_module("apibe", broker_path)

    paths = _bootstrap_core_mocks(tmp_path)

    def _get_adapter() -> Any:
        return apicore.JsonMockStorageAdapter(
            users_path=paths["users"],
            organizations_path=paths["organizations"],
            roles_path=paths["roles"],
            basic_permissions_path=paths["basic_permissions"],
            low_level_permissions_path=paths["low_level_permissions"],
            manage_roles_path=paths["manage_roles"],
        )

    apicore.app.dependency_overrides[apicore.get_storage_adapter] = _get_adapter

    core_client = TestClient(apicore.app)

    class FakeCoreClient:
        """Cliente core en memoria para tests."""

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
    client = TestClient(apibe.app)

    response = client.post(
        "/organizations",
        json={
            "organization_name": "Demo Org",
            "organization_email": "demo@org.com",
            "organization_tlf": "",
            "organization_address": "",
            "organization_country": "",
            "organization_state": "",
        },
    )
    assert response.status_code == 200
    assert response.json()["organization_id"] == 1

    response = client.post("/organizations/check-name", json={"organization_name": "Demo Org"})
    assert response.status_code == 200
    assert response.json()["exists"] is True

    response = client.post(
        "/users",
        json={
            "organization_id": 1,
            "identity_type_id": None,
            "user_name": "demo",
            "user_password": "secret",
            "user_email": "demo@org.com",
            "user_mobile": "+34999999999",
            "user_otp": "1234",
            "active": True,
            "blocked": False,
            "contact_info": {},
            "billing_info": {},
        },
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == 1

    response = client.get("/permissions", params={"identity_type_id": 2})
    assert response.status_code == 200
    assert response.json()["permissions"]

    response = client.post("/process-data", json={"payload": {"ping": "pong"}})
    assert response.status_code == 200
    assert response.json()["result"]["result"]["echo"]["ping"] == "pong"

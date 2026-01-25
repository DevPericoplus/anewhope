"""Tests básicos del backend core."""

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
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: Any) -> None:
    """Escribe JSON en disco."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)


def _build_mock_paths(tmp_path: Path) -> dict[str, Path]:
    """Crea rutas temporales para mocks."""

    return {
        "users": tmp_path / "users.json",
        "organizations": tmp_path / "organizations.json",
        "roles": tmp_path / "roles.json",
        "basic_permissions": tmp_path / "basic_permissions.json",
        "low_level_permissions": tmp_path / "low_level_permissions.json",
        "manage_roles": tmp_path / "manage_roles_by_org.json",
    }


def _bootstrap_mocks(paths: dict[str, Path]) -> None:
    """Inicializa datos mock necesarios."""

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


def test_core_endpoints(tmp_path: Path) -> None:
    """Valida endpoints básicos del backend core."""

    module_path = Path(__file__).resolve().parents[1] / "apicore.py"
    apicore = _load_module("apicore", module_path)

    paths = _build_mock_paths(tmp_path)
    _bootstrap_mocks(paths)

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
    client = TestClient(apicore.app)

    response = client.post(
        "/organizations/check-name", json={"organization_name": "Demo Org"}
    )
    assert response.status_code == 200
    assert response.json()["exists"] is False

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
    org_id = response.json()["organization_id"]
    assert org_id > 0

    response = client.post(
        "/users",
        json={
            "organization_id": org_id,
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
    user_id = response.json()["user_id"]
    assert user_id > 0

    response = client.get("/permissions", params={"identity_type_id": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["identity_type_id"] == 2
    assert data["permissions"]
    assert data["low_level_permissions"]

    response = client.post("/process-data", json={"payload": {"key": "value"}})
    assert response.status_code == 200
    assert response.json()["result"]["echo"]["key"] == "value"

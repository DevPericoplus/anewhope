"""Tests de validación de permisos de bajo nivel en middleware."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


class DummyInterface:
    """Interfaz dummy para el middleware."""

    async def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Devuelve el payload sin cambios."""

        return payload


def _load_routermiddleware_module() -> Any:
    """Carga el módulo routermiddleware usando importlib."""

    module_path = (
        Path(__file__).resolve().parents[1] / "routermiddleware.py"
    )
    spec = importlib.util.spec_from_file_location("routermiddleware", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar routermiddleware")
    module = importlib.util.module_from_spec(spec)
    sys.modules["routermiddleware"] = module
    spec.loader.exec_module(module)
    return module


routermiddleware = _load_routermiddleware_module()


def _write_json(path: Path, payload: Any) -> None:
    """Escribe JSON en disco."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)


def _get_router() -> Any:
    """Construye el middleware con configuración dummy."""

    settings = routermiddleware.JwtSettings(
        access_secret="access",
        session_secret="session",
        algorithm="HS256",
        access_ttl_seconds=900,
        session_ttl_seconds=2700,
    )
    return routermiddleware.RouterMiddleware(
        interface=DummyInterface(), jwt_settings=settings
    )


def test_low_level_permission_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valida permisos de bajo nivel usando el contexto de sesión."""

    users_path = tmp_path / "users.json"
    roles_path = tmp_path / "roles.json"
    basic_permissions_path = tmp_path / "basic_permissions.json"
    low_level_permissions_path = tmp_path / "low_level_permissions.json"

    _write_json(
        users_path,
        [
            {
                "user_id": 1,
                "organization_id": 1,
                "identity_type_id": 2,
                "user_name": "demo",
                "user_password": "secret",
                "user_email": "demo@org.com",
                "user_mobile": "+34999999999",
                "user_otp": "1234",
                "active": True,
                "blocked": False,
                "contact_info": {},
                "billing_info": {},
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
        basic_permissions_path,
        [
            {
                "id": 1,
                "PermissionName": "admin",
                "PermissionDescription": "Permite administración total",
            }
        ],
    )
    _write_json(
        low_level_permissions_path,
        [
            {
                "id_permissions": 1,
                "folder_create": True,
                "folder_delete": False,
                "folder_rename": True,
                "folder_read": True,
                "file_create": False,
                "file_read": True,
                "file_update": False,
                "file_delete": False,
                "project_create": False,
                "project_read": True,
                "project_update": False,
                "project_delete": False,
                "version_create": False,
                "version_read": True,
                "version_update": False,
                "version_delete": False,
                "training_create": False,
                "training_read": False,
                "training_update": False,
                "training_delete": False,
                "training_start": False,
                "training_stop": False,
                "parameters_create": False,
                "parameters_read": False,
                "parameters_update": False,
                "parameters_delete": False,
                "notifications_create": False,
                "notifications_read": False,
                "notifications_update": False,
                "notifications_delete": False,
                "user_create": False,
                "user_read": True,
                "user_update": False,
                "user_delete": False,
                "user_enable": False,
                "user_disable": False,
                "folder_list": True,
                "file_list": True,
                "project_list": True,
                "version_list": True,
            }
        ],
    )

    monkeypatch.setenv("USERS_DATA_PATH", str(users_path))
    monkeypatch.setenv("ROLES_DATA_PATH", str(roles_path))
    monkeypatch.setenv("BASIC_PERMISSIONS_PATH", str(basic_permissions_path))
    monkeypatch.setenv(
        "LOW_LEVEL_PERMISSIONS_PATH", str(low_level_permissions_path)
    )

    router = _get_router()
    session = routermiddleware.SessionContext(
        user_id=1,
        organization_id=1,
        identity_type_id=2,
        access_payload={},
        session_payload={},
    )

    assert router.has_low_level_permission(session, "folder_rename") is True
    assert router.has_low_level_permission(session, "folder_delete") is False
    assert router.can_rename_folder(session) is True

"""Tests de creación de usuarios en el middleware."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import importlib.util
import sys

import pytest


class DummyInterface:
    """Interfaz dummy para el middleware."""

    async def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Devuelve el payload sin cambios."""

        return payload


def _create_empty_json(file_path: Path) -> None:
    """Crea un archivo JSON vacío."""

    file_path.write_text("[]", encoding="utf-8")


def _load_json(file_path: Path) -> list[dict[str, Any]]:
    """Carga contenido JSON como lista."""

    with file_path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


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


def test_create_user_creates_manage_role_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Crea un usuario y registra rol por organización con valores por defecto.
    
    Regla: El primer usuario de una organización nueva se convierte en admin (identity_type_id=2)
    automáticamente si no se especifica identity_type_id o se especifica None.
    Si se especifica identity_type_id=5 explícitamente, se respeta (auditor).
    """

    users_path = tmp_path / "users.json"
    roles_path = tmp_path / "manage_roles_by_org.json"
    _create_empty_json(users_path)
    _create_empty_json(roles_path)

    monkeypatch.setenv("STORAGE_MODE", "mock")
    monkeypatch.setenv("USERS_DATA_PATH", str(users_path))
    monkeypatch.setenv("MANAGE_ROLES_BY_ORG_PATH", str(roles_path))

    router = _get_router()
    # No especificar identity_type_id para que el middleware asigne admin (2)
    # al primer usuario de la organización
    result = router.create_user(
        {
            "organization_id": 10,
            # identity_type_id omitido → será admin (2)
            "user_name": "demo",
            "user_password": "password",
            "user_email": "demo@example.com",
            "user_mobile": "+34000000000",
            "user_otp": "1234",
        }
    )

    assert result.user_id == 1
    assert result.organization_id == 10
    # Primer usuario sin rol especificado → admin (2)
    assert result.identity_type_id == 2

    users = _load_json(users_path)
    assert users[0]["identity_type_id"] == 2

    manage_roles = _load_json(roles_path)
    assert len(manage_roles) == 1
    entry = manage_roles[0]
    assert entry["id_user"] == 1
    assert entry["id_organization"] == 10
    assert entry["identity_type_id"] == 2
    assert entry["modification_date"] == ""
    assert entry["id_modifier_user"] == 1
    assert entry["active"] is True
    assert re.match(r"\d{2}/\d{2}/\d{2}-\d{2}:\d{2}", entry["create_date"])


def test_create_user_uses_requested_role_for_existing_org(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Asigna el rol solicitado cuando la organización ya existe."""

    users_path = tmp_path / "users.json"
    roles_path = tmp_path / "manage_roles_by_org.json"
    _create_empty_json(users_path)
    _create_empty_json(roles_path)

    monkeypatch.setenv("STORAGE_MODE", "mock")
    monkeypatch.setenv("USERS_DATA_PATH", str(users_path))
    monkeypatch.setenv("MANAGE_ROLES_BY_ORG_PATH", str(roles_path))

    router = _get_router()
    router.create_user(
        {
            "organization_id": 20,
            "identity_type_id": 2,
            "user_name": "admin",
            "user_password": "password",
            "user_email": "admin@example.com",
            "user_mobile": "+34000000001",
            "user_otp": "1234",
        }
    )

    result = router.create_user(
        {
            "organization_id": 20,
            "identity_type_id": 3,
            "user_name": "editor",
            "user_password": "password",
            "user_email": "editor@example.com",
            "user_mobile": "+34000000002",
            "user_otp": "1234",
        }
    )

    assert result.identity_type_id == 3

    users = _load_json(users_path)
    assert users[1]["identity_type_id"] == 3

    manage_roles = _load_json(roles_path)
    assert len(manage_roles) == 2
    assert manage_roles[1]["identity_type_id"] == 3

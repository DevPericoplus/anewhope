"""Tests de invalidación de tokens tras logout en el middleware."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import importlib.util
import pytest


class DummyInterface:
    """Interfaz dummy para el middleware."""

    async def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Devuelve el payload sin cambios."""

        return payload


def _load_module(module_name: str, module_path: Path) -> Any:
    """Carga un módulo por ruta usando importlib."""

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(file_path: Path, payload: Any) -> None:
    """Escribe un JSON en disco."""

    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _build_user_payload(password_encrypted: str) -> list[dict[str, Any]]:
    """Construye un usuario mockeado."""

    return [
        {
            "user_id": 10,
            "organization_id": 5,
            "identity_type_id": 2,
            "user_name": "demo",
            "user_password": password_encrypted,
            "user_email": "demo@example.com",
            "user_mobile": "+34000000000",
            "user_otp": "1234",
            "active": True,
            "blocked": False,
            "contact_info": {},
            "billing_info": {},
        }
    ]


def test_logout_invalidates_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifica que tras logout los tokens quedan inválidos."""

    router_path = Path(__file__).resolve().parents[1] / "routermiddleware.py"
    security_dir = (
        Path(__file__).resolve().parents[4]
        / "src/2_shared_application/security"
    )
    cipher_path = security_dir / "custom_cipher_lib.py"
    routermiddleware = _load_module("routermiddleware", router_path)
    cipher_module = _load_module("custom_cipher_lib", cipher_path)

    temp_security_dir = tmp_path / "security"
    temp_security_dir.mkdir(parents=True, exist_ok=True)
    temp_cipher_path = temp_security_dir / "custom_cipher_lib.py"
    temp_cipher_path.write_text(
        cipher_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    key_file = temp_security_dir / "basesecuritypass.json"
    key_value = cipher_module.create_fernet_key(None)
    cipher_module.store_fernet_key_to_file(key_value, key_file)
    fernet_instance = cipher_module.load_fernet_key_from_file(key_file)
    password_encrypted = cipher_module.encrypt_value(
        fernet_instance, "secret123"
    ).decode("utf-8")

    users_path = tmp_path / "users.json"
    sessions_path = tmp_path / "sessions.json"
    _write_json(users_path, _build_user_payload(password_encrypted))
    _write_json(sessions_path, {"sessions": [], "auth_logs": []})

    monkeypatch.setenv("STORAGE_MODE", "mock")
    monkeypatch.setenv("USERS_DATA_PATH", str(users_path))
    monkeypatch.setenv("SESSIONS_DATA_PATH", str(sessions_path))
    monkeypatch.setenv("FERNET_KEY_PATH", str(key_file))

    settings = routermiddleware.JwtSettings(
        access_secret="access",
        session_secret="session",
        algorithm="HS256",
        access_ttl_seconds=900,
        session_ttl_seconds=2700,
    )
    router = routermiddleware.RouterMiddleware(
        interface=DummyInterface(), jwt_settings=settings
    )

    tokens = router.authenticate_user(
        user_name="demo",
        password="secret123",
        otp="1234",
    )
    session_context = router.validate_session(
        tokens.access_token, tokens.session_token
    )
    assert router.logout_session(session_context) is True

    with pytest.raises(routermiddleware.TokenValidationError):
        router.validate_session(tokens.access_token, tokens.session_token)

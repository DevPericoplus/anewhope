"""Cuenta de servicio `soporte`: clon de adminone, sin SMS, identity_type_id=1."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


class DummyInterface:
    async def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


def _load_routermiddleware() -> Any:
    module_path = Path(__file__).resolve().parents[1] / "routermiddleware.py"
    spec = importlib.util.spec_from_file_location(
        "routermiddleware_soporte_otp", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar routermiddleware")
    module = importlib.util.module_from_spec(spec)
    sys.modules["routermiddleware_soporte_otp"] = module
    spec.loader.exec_module(module)
    return module


routermiddleware = _load_routermiddleware()


def _get_router() -> Any:
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


def _adminone(**overrides: Any) -> dict[str, Any]:
    row = {
        "user_id": 1,
        "organization_id": 1,
        "identity_type_id": 1,
        "user_name": "adminone",
        "user_password": "cipher-admin",
        "user_email": "adminone@tfmmyllm.ai",
        "user_mobile": "600000000",
        "user_otp": "1234",
        "active": True,
        "blocked": False,
        "contact_info": {"first_name": "Admin", "sur_name": "One"},
        "billing_info": {},
    }
    row.update(overrides)
    return row


def _write_users(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows), encoding="utf-8")


def _sessions(path: Path) -> None:
    path.write_text(json.dumps({"auth_logs": [], "sessions": []}), encoding="utf-8")


def _router(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, Any]]):
    monkeypatch.setenv("STORAGE_MODE", "mock")
    users_path = tmp_path / "users.json"
    sessions_path = tmp_path / "sessions.json"
    roles_path = tmp_path / "manage_roles_by_org.json"
    _write_users(users_path, rows)
    _sessions(sessions_path)
    roles_path.write_text("[]", encoding="utf-8")
    router = _get_router()
    monkeypatch.setattr(router, "_get_users_file_path", lambda: users_path)
    monkeypatch.setattr(router, "_get_sessions_file_path", lambda: sessions_path)
    monkeypatch.setattr(router, "_get_manage_roles_path", lambda: roles_path)
    monkeypatch.setattr(router, "_decrypt_password", lambda stored: "ok-pass")
    monkeypatch.setattr(router, "_encrypt_password", lambda plain: f"enc:{plain}")
    return router, users_path


def test_is_otp_exempt_includes_soporte() -> None:
    router = _get_router()
    assert router._is_otp_exempt("soporte") is True
    assert router._is_otp_exempt("SOPORTE") is True
    assert router._is_otp_exempt("adminone") is False


def test_soporte_request_otp_skips_sms_without_mobile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    soporte = _adminone(
        user_id=9,
        user_name="soporte",
        user_email="soporte@laim.app",
        user_mobile="",
        user_otp="",
        user_password="cipher-soporte",
        contact_info={"first_name": "Soporte", "sur_name": "LAIM"},
    )
    router, _ = _router(tmp_path, monkeypatch, [_adminone(), soporte])
    result = router.request_login_otp("soporte", "ok-pass")
    assert result.get("success") is True
    assert result.get("otp_exempt") is True
    assert "otp" not in result
    assert "phone_number" not in result


def test_non_exempt_without_mobile_still_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ghost = _adminone(user_name="ghost", user_mobile="", user_email="ghost@example.com")
    router, _ = _router(tmp_path, monkeypatch, [ghost])
    with pytest.raises(routermiddleware.BusinessRuleError, match="teléfono"):
        router.request_login_otp("ghost", "ok-pass")


def test_ensure_soporte_clones_adminone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GETMYLLM_SOPORTE_PASSWORD", "ok-pass")
    router, users_path = _router(tmp_path, monkeypatch, [_adminone()])
    created = router.ensure_soporte_service_account()
    assert created is True
    users = json.loads(users_path.read_text(encoding="utf-8"))
    soporte = next(u for u in users if u["user_name"] == "soporte")
    assert soporte["user_email"] == "soporte@laim.app"
    assert soporte["identity_type_id"] == 1
    assert soporte["organization_id"] == 1
    assert soporte["user_mobile"] in ("", None)
    assert soporte["user_password"] == "enc:ok-pass"
    assert soporte["active"] is True
    assert soporte["blocked"] is False
    again = router.ensure_soporte_service_account()
    assert again is False
    users_after = json.loads(users_path.read_text(encoding="utf-8"))
    assert sum(1 for u in users_after if u["user_name"] == "soporte") == 1

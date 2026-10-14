"""Hooks de auditoría en login/registro: no tumbar el caso de uso."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")
    monkeypatch.setenv("LAIM_HCAPTCHA_DISABLED", "1")


def _load_auth():
    module_path = Path(__file__).resolve().parents[1] / "laim_auth_service.py"
    spec = importlib.util.spec_from_file_location("laim_auth_service_auditoria_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_auth_service_auditoria_test"] = module
    spec.loader.exec_module(module)
    return module


def test_register_writes_alta_and_survives_auditoria_failure() -> None:
    module = _load_auth()
    user_repo = MagicMock()
    user_repo.get_organization_id_by_name.return_value = 1
    user_repo.user_exists.return_value = False
    user_repo.create_user.return_value = 44
    auditoria = MagicMock()
    auditoria.safe_record_usuario.side_effect = RuntimeError("db down")
    service = module.LaimAuthService(user_repo=user_repo, auditoria=auditoria)
    service._verify_hcaptcha = MagicMock(return_value=True)
    module.encrypt_password = MagicMock(return_value="enc")

    result = service.register(
        user_name="nuevo",
        password="secret123",
        password_confirm="secret123",
        user_email="nuevo@laim.app",
        full_name="Nuevo Usuario",
    )
    assert result["success"] is True
    assert result["user_id"] == 44
    auditoria.safe_record_usuario.assert_called()
    kwargs = auditoria.safe_record_usuario.call_args.kwargs
    assert kwargs["accion"] == "alta"
    assert kwargs["user_id"] == 44


def test_login_success_writes_login() -> None:
    module = _load_auth()
    user = MagicMock()
    user.user_id = 9
    user.user_name = "laimone"
    user.organization_id = 1
    user.identity_type_id = 4
    user.active = True
    user.blocked = False
    user.user_password = "encrypted"
    user_repo = MagicMock()
    user_repo.get_user_by_name.return_value = user
    auditoria = MagicMock()
    service = module.LaimAuthService(user_repo=user_repo, auditoria=auditoria)
    session = MagicMock()
    session.session_id = "sess-9"
    token_pair = MagicMock()
    token_pair.access_token = "a"
    token_pair.session_token = "s"
    token_pair.access_expires_at = 1
    token_pair.session_expires_at = 2
    token_pair.session_id = "sess-9"
    created = MagicMock()
    created.session = session
    created.token_pair = token_pair
    service._session_service = MagicMock()
    service._session_service.create_session.return_value = created
    module.decrypt_password = MagicMock(return_value="secret")

    result = service.login("laimone", "secret")
    assert result.success is True
    kwargs = auditoria.safe_record_usuario.call_args.kwargs
    assert kwargs["accion"] == "login"
    assert kwargs["session_id"] == "sess-9"

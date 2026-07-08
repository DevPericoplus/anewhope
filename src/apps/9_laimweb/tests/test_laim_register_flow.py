"""Tests del flujo de registro LAIM Web (hCaptcha + background task)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

laimweb_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(laimweb_root))


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def test_set_reg_hcaptcha_token_chains_background_register() -> None:
    from laim_web.laim_state import LaimWebState

    with patch(
        "laim_web.components.hcaptcha.is_hcaptcha_configured",
        return_value=True,
    ):
        state = LaimWebState()
        event_spec = state.set_reg_hcaptcha_token("token-abc")

    assert event_spec is not None
    assert state.reg_hcaptcha_token == "token-abc"


def test_set_reg_hcaptcha_token_rejects_empty_when_configured() -> None:
    from laim_web.laim_state import LaimWebState

    with patch(
        "laim_web.components.hcaptcha.is_hcaptcha_configured",
        return_value=True,
    ):
        state = LaimWebState()
        event_spec = state.set_reg_hcaptcha_token("")

    assert event_spec is None
    assert "anti-bot" in state.error_message


def test_handle_register_without_hcaptcha_chains_background() -> None:
    from laim_web.laim_state import LaimWebState

    with patch(
        "laim_web.components.hcaptcha.is_hcaptcha_configured",
        return_value=False,
    ):
        state = LaimWebState()
        state.reg_username = "user1"
        state.reg_full_name = "User One"
        state.reg_email = "user1@example.com"
        state.reg_password = "password1"
        state.reg_password_confirm = "password1"

        event_spec = state.handle_register()

    assert event_spec is not None
    assert state.loading is False


def test_handle_register_with_token_chains_background() -> None:
    from laim_web.laim_state import LaimWebState

    with patch(
        "laim_web.components.hcaptcha.is_hcaptcha_configured",
        return_value=True,
    ):
        state = LaimWebState()
        state.reg_username = "user1"
        state.reg_full_name = "User One"
        state.reg_email = "user1@example.com"
        state.reg_password = "password1"
        state.reg_password_confirm = "password1"
        state.reg_hcaptcha_token = "token-abc"

        event_spec = state.handle_register()

    assert event_spec is not None
    assert state.loading is False


def test_register_success_prefills_login_password_on_manual_login() -> None:
    """Tras registro, la contraseña debe quedar en login_password si el auto-login falla."""
    source_path = laimweb_root / "laim_web" / "laim_state.py"
    source = source_path.read_text(encoding="utf-8")

    assert "login_result = laim_login(username, password)" in source
    assert "self.login_password = password" in source


def test_apply_laim_login_success_delegates_to_load_user_data() -> None:
    """Helper de login delega en load_user_data y cierra modales."""
    from laim_web.laim_state import LaimWebState

    state = LaimWebState()
    state.login_modal_open = True
    login_payload = {
        "success": True,
        "user_id": 10,
        "organization_id": 1,
        "identity_type_id": 2,
        "user_name": "user1",
        "user_email": "user1@example.com",
        "user_mobile": "",
        "access_token": "access",
        "session_token": "session",
        "access_expires_at": 9999999999,
        "session_expires_at": 9999999999,
        "session_id": "sess-1",
    }

    with (
        patch.object(
            LaimWebState,
            "_load_permissions_after_login",
            return_value={"folder_read": True},
        ) as mock_permissions,
        patch.object(LaimWebState, "load_user_data") as mock_load_user,
        patch.object(LaimWebState, "_load_static_page") as mock_static_page,
    ):
        applied = state._apply_laim_login_success(login_payload)

    assert applied is True
    mock_permissions.assert_called_once()
    mock_load_user.assert_called_once()
    mock_static_page.assert_called_once_with("instaladores")
    assert state.login_modal_open is False
    assert state.login_password == ""
    assert state._token_renewal_running is True

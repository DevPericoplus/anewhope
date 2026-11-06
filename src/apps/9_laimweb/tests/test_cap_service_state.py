"""Estado de Cap en el formulario de alta: solo «down» bloquea (fail-open)."""

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


def _filled_state():
    from laim_web.laim_state import LaimWebState

    state = LaimWebState()
    state.reg_username = "user1"
    state.reg_full_name = "User One"
    state.reg_email = "user1@example.com"
    state.reg_password = "password1"
    state.reg_password_confirm = "password1"
    return state


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"status": "ok"}, "ok"),
        ({"status": "down"}, "down"),
        ({"status": "off"}, "off"),
        ({"status": "weird"}, "unknown"),
        ({"success": False, "error": "Error de conexión: refused"}, "unknown"),
        ({}, "unknown"),
    ],
)
def test_client_maps_middleware_answer(response: dict, expected: str) -> None:
    from laim_web.adapters import laim_api_client

    with patch.object(laim_api_client, "_request_middleware", return_value=response) as req:
        assert laim_api_client.laim_captcha_health() == expected
    req.assert_called_once()
    assert req.call_args.args[:2] == ("GET", "/laim/captcha/health")


def test_client_never_raises() -> None:
    from laim_web.adapters import laim_api_client

    with patch.object(laim_api_client, "_request_middleware", side_effect=RuntimeError("x")):
        assert laim_api_client.laim_captcha_health() == "unknown"


def test_down_blocks_register() -> None:
    from laim_web.laim_state import MSG_CAPTCHA_UNAVAILABLE

    with patch("laim_web.components.hcaptcha.is_hcaptcha_configured", return_value=True):
        state = _filled_state()
        state.reg_cap_service = "down"
        assert state.handle_register() is None
    assert state.error_message == MSG_CAPTCHA_UNAVAILABLE


@pytest.mark.parametrize("status_value", ["unknown", "ok", "off"])
def test_other_states_do_not_block(status_value: str) -> None:
    with patch("laim_web.components.hcaptcha.is_hcaptcha_configured", return_value=True):
        state = _filled_state()
        state.reg_cap_service = status_value
        assert state.handle_register() is not None
    assert state.error_message == ""


def test_opening_the_form_checks_cap_and_retry_rechecks() -> None:
    from laim_web.laim_state import LaimWebState

    state = LaimWebState()
    for opener in (state.open_register_modal, state.switch_to_register_modal):
        events = opener()
        assert isinstance(events, list)
        assert "check_cap_service" in str(events)
    retry = state.retry_cap_service()
    assert "check_cap_service" in str(retry)


def test_modal_shows_message_retry_and_disables_button_when_down() -> None:
    source = (laimweb_root / "laim_web" / "components" / "auth_modals.py").read_text(
        encoding="utf-8"
    )
    register = source.split("def register_modal", 1)[1].split("def forgot_modal", 1)[0]
    assert 'LaimWebState.reg_cap_service == "down"' in register
    assert "MSG_CAPTCHA_UNAVAILABLE" in register
    assert "LaimWebState.retry_cap_service" in register
    assert '| (LaimWebState.reg_cap_service == "down")' in register


def test_captcha_failure_rechecks_cap() -> None:
    source = (laimweb_root / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    body = source.split("async def complete_register_background", 1)[1].split(
        "def open_login_modal", 1
    )[0]
    assert "recheck_cap" in body
    assert "yield LaimWebState.check_cap_service" in body
    check = source.split("async def check_cap_service", 1)[1].split("def retry_cap_service", 1)[0]
    # Con Cap caído, el aviso de servicio sustituye al de repetir la verificación.
    assert 'status_value == "down"' in check
    assert 'self.error_message = ""' in check

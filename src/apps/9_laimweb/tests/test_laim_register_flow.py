"""Tests del flujo de registro LAIM Web (hCaptcha + background task)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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

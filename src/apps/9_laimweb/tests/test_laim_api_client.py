"""Tests del cliente API LAIM Web."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

laimweb_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(laimweb_root))


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def test_laim_login_success() -> None:
    from laim_web.adapters import laim_api_client

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "user_id": 1,
        "access_token": "access",
        "session_token": "session",
    }

    with patch.object(laim_api_client.httpx, "Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = laim_api_client.laim_login("user", "pass")

    assert result["success"] is True
    assert result["access_token"] == "access"


def test_laim_register_sends_hcaptcha_token() -> None:
    from laim_web.adapters import laim_api_client

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"success": True, "message": "ok"}

    with patch.object(laim_api_client.httpx, "Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        laim_api_client.laim_register(
            username="newuser",
            password="password1",
            password_confirm="password1",
            email="new@example.com",
            full_name="New User",
            hcaptcha_token="hcaptcha-token",
        )

        call_kwargs = mock_client.request.call_args.kwargs
        payload = call_kwargs["json"]
        assert payload["hcaptcha_token"] == "hcaptcha-token"


def test_laim_submit_contact_message_posts_payload() -> None:
    from laim_web.adapters import laim_api_client

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "message_id": 10,
        "image_id": None,
    }

    payload = {
        "usage_mode": "local",
        "affected_user_info": "demo",
        "message_body": "Descripción suficientemente larga.",
        "reply_email": "user@example.com",
    }

    with patch.object(laim_api_client.httpx, "Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = laim_api_client.laim_submit_contact_message(payload)

    assert result["success"] is True
    assert result["message_id"] == 10
    call_kwargs = mock_client.request.call_args.kwargs
    assert call_kwargs["json"] == payload
    assert call_kwargs["headers"]["X-Client-App"] == "laimweb"
    assert call_kwargs["url"].endswith("/laim/contact/messages")


def test_ensure_valid_tokens_renews_when_near_expiry() -> None:
    from laim_web.adapters import laim_api_client
    import time

    with patch.object(
        laim_api_client,
        "laim_refresh_token",
        return_value={
            "success": True,
            "access_token": "new-access",
            "session_token": "new-session",
            "access_expires_at": int(time.time()) + 900,
            "session_expires_at": int(time.time()) + 2700,
        },
    ):
        result = laim_api_client.ensure_valid_tokens(
            access_token="old-access",
            session_token="old-session",
            access_expires_at=int(time.time()) + 30,
            session_expires_at=int(time.time()) + 3600,
        )

    assert result["renewed"] is True
    assert result["access_token"] == "new-access"


def test_hcaptcha_widget_without_site_key() -> None:
    from laim_web.components import hcaptcha

    with patch.object(hcaptcha, "get_cap_api_endpoint", return_value=""):
        component = hcaptcha.hcaptcha_widget()
        assert component is not None
        assert hcaptcha.is_hcaptcha_configured() is False


def test_register_validation_requires_username() -> None:
    from laim_web.laim_state import LaimWebState

    state = LaimWebState()
    state.reg_username = ""
    assert state._validate_register_form() == "El usuario es obligatorio."


def test_set_reg_hcaptcha_token_requires_token_when_configured() -> None:
    from laim_web.laim_state import LaimWebState

    state = LaimWebState()

    with patch("laim_web.components.hcaptcha.is_hcaptcha_configured", return_value=True):
        event_spec = state.set_reg_hcaptcha_token("")

    assert event_spec is None
    assert "anti-bot" in state.error_message.lower()

"""UI y flujo de Olvidé contraseña / página /r/{token}."""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

laimweb_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(laimweb_root))

_INDEX = laimweb_root / "laim_web" / "pages" / "index.py"
_MODALS = laimweb_root / "laim_web" / "components" / "auth_modals.py"
_APP = laimweb_root / "laim_web" / "laim_web.py"


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def test_cta_literal_removed_and_forgot_button_exists() -> None:
    source = _INDEX.read_text(encoding="utf-8")
    assert "Inicie sesión o cree una cuenta" not in source
    assert "Olvidé contraseña" in source
    assert "open_forgot_modal" in source


def test_forgot_modal_and_reset_route_exist() -> None:
    modals = _MODALS.read_text(encoding="utf-8")
    app = _APP.read_text(encoding="utf-8")
    assert "def forgot_modal" in modals
    assert "Olvidé contraseña" in modals
    assert 'route="/r/[token]"' in app
    assert "password_reset_page" in app


def test_reset_email_template_uses_user_name_and_opaque_url() -> None:
    from laim_web.password_reset_mail import build_reset_email, build_reset_url

    url = build_reset_url("https://laim.anewhope.silicon.loc", "tok_abc")
    subject, body = build_reset_email("ana", url)
    assert "ana" in body
    assert "/r/tok_abc" in body
    assert "15" in body
    assert "https://laim.app" not in body
    assert "Restablecer" in subject


def test_forgot_always_generic_and_sends_only_when_found() -> None:
    from laim_web.laim_state import LaimWebState
    from laim_web.password_reset_mail import (
        RESET_ACCEPTED_MSG,
        build_reset_email,
        build_reset_url,
    )

    sent: list[tuple[str, str, str]] = []

    def fake_send(to: str, subject: str, body: str) -> dict:
        sent.append((to, subject, body))
        return {"success": True}

    missing = LaimWebState()
    missing.forgot_email = "nadie@laim.example"
    missing.apply_forgot_prepare_and_send(
        {"accepted": True, "found": False},
        "https://laim.example",
        send_mail=fake_send,
        build_email=build_reset_email,
        build_url=build_reset_url,
    )
    assert missing.forgot_message == RESET_ACCEPTED_MSG
    assert sent == []

    found = LaimWebState()
    found.forgot_email = "ana@laim.example"
    found.apply_forgot_prepare_and_send(
        {"accepted": True, "found": True, "user_name": "ana", "token": "tok32"},
        "https://laim.example",
        send_mail=fake_send,
        build_email=build_reset_email,
        build_url=build_reset_url,
    )
    assert found.forgot_message == RESET_ACCEPTED_MSG
    assert len(sent) == 1
    assert "ana" in sent[0][2]
    assert "https://laim.example/r/tok32" in sent[0][2]


def test_reset_page_is_dead_after_used_or_expired() -> None:
    from laim_web.laim_state import LaimWebState

    used = LaimWebState()
    used.apply_reset_status("used-token", {"valid": False, "reason": "used"})
    assert used.reset_page_status == "dead"

    expired = LaimWebState()
    expired.apply_reset_status("expired-token", {"valid": False, "reason": "expired"})
    assert expired.reset_page_status == "dead"

    alive = LaimWebState()
    alive.apply_reset_status("live-token", {"valid": True})
    assert alive.reset_page_status == "form"

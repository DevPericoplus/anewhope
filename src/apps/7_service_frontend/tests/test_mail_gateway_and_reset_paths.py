"""Contrato de las 3 capas: envío en Router, reset por broker → core."""

from __future__ import annotations

from pathlib import Path

_MW = Path(__file__).resolve().parents[1]
_BROKER = Path(__file__).resolve().parents[2] / "8_service_backend"
_CORE = Path(__file__).resolve().parents[2] / "3_backend"


def test_mail_send_lives_in_middleware_router_not_broker() -> None:
    router = (_MW / "routermiddleware.py").read_text(encoding="utf-8")
    api = (_MW / "apife.py").read_text(encoding="utf-8")
    broker_api = (_BROKER / "apibe.py").read_text(encoding="utf-8")
    assert "def laim_mail_send" in router
    assert "send_support_mail" in router
    assert "@app.post(\"/laim/mail/send\")" in api
    assert "/laim/mail/send" not in broker_api
    assert "nginx" not in api.lower() or "location /laim/mail" not in api


def test_password_reset_path_exists_core_to_middleware() -> None:
    files = [
        _CORE / "router_laim_auth.py",
        _BROKER / "interfacetocore.py",
        _BROKER / "routerbroker.py",
        _BROKER / "apibe.py",
        _MW / "broker_backend_client.py",
        _MW / "routermiddleware.py",
        _MW / "apife.py",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "password-reset" in text or "password_reset" in text, path.name

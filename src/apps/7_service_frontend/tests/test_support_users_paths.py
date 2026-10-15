"""El canal de cuentas reutiliza support_ops 7→8→3, nunca nginx público."""

from __future__ import annotations

from pathlib import Path

_MW = Path(__file__).resolve().parents[1]
_BROKER = Path(__file__).resolve().parents[2] / "8_service_backend"
_CORE = Path(__file__).resolve().parents[2] / "3_backend"
_WEB = Path(__file__).resolve().parents[2] / "9_laimweb"


def test_support_users_path_core_to_laimweb() -> None:
    files = {
        _CORE / "router_laim_users_ops.py": "/laim/support/users",
        _CORE / "apicore.py": "router_laim_users_ops",
        _BROKER / "apibe.py": "/laim/support/users",
        _MW / "apife.py": "/laim/support/users",
        _WEB / "laim_web" / "support_gateway.py": "/laim/support/users",
        _WEB / "laim_web" / "laim_web.py": "/api/support/users",
    }
    for path, needle in files.items():
        text = path.read_text(encoding="utf-8")
        assert needle in text, path.name
    gateway = (_WEB / "laim_web" / "support_gateway.py").read_text(encoding="utf-8")
    assert "el cuerpo debe ir cifrado" in gateway
    assert "encrypt_support_payload" in gateway
    web = (_WEB / "laim_web" / "laim_web.py").read_text(encoding="utf-8")
    assert "location /laim/users" not in web
    assert "/api/support/users/{user_id:int}/password" in web

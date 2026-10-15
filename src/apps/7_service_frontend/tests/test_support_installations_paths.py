"""El canal de métricas de Registro reutiliza support_ops 7→8→3, nunca nginx público."""

from __future__ import annotations

from pathlib import Path

_MW = Path(__file__).resolve().parents[1]
_BROKER = Path(__file__).resolve().parents[2] / "8_service_backend"
_CORE = Path(__file__).resolve().parents[2] / "3_backend"
_WEB = Path(__file__).resolve().parents[2] / "9_laimweb"


def test_support_installations_path_core_to_laimweb() -> None:
    files = {
        _CORE / "router_laim_installations_ops.py": "/laim/support/installations",
        _CORE / "apicore.py": "router_laim_installations_ops",
        _BROKER / "apibe.py": "/laim/support/installations/metrics",
        _MW / "apife.py": "/laim/support/installations/metrics",
        _WEB / "laim_web" / "support_gateway.py": "/laim/support/installations/metrics",
        _WEB / "laim_web" / "laim_web.py": "/api/support/installations/metrics",
    }
    for path, needle in files.items():
        text = path.read_text(encoding="utf-8")
        assert needle in text, path.name
    gateway = (_WEB / "laim_web" / "support_gateway.py").read_text(encoding="utf-8")
    assert "el cuerpo debe ir cifrado" in gateway
    web = (_WEB / "laim_web" / "laim_web.py").read_text(encoding="utf-8")
    assert "/api/support/installations" in web
    assert "/api/support/installations/metrics" in web

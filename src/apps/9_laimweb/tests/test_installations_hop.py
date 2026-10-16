"""El CRUD y propose de instalaciones recorren middleware → broker → core."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def test_hop_exposes_session_and_public_propose_routes() -> None:
    apife = (_ROOT / "7_service_frontend" / "apife.py").read_text(encoding="utf-8")
    apibe = (_ROOT / "8_service_backend" / "apibe.py").read_text(encoding="utf-8")
    mw = (_ROOT / "7_service_frontend" / "routermiddleware.py").read_text(encoding="utf-8")
    broker = (_ROOT / "8_service_backend" / "routerbroker.py").read_text(encoding="utf-8")
    core = (_ROOT / "3_backend" / "apicore.py").read_text(encoding="utf-8")
    router = (_ROOT / "3_backend" / "router_laim_installations.py").read_text(encoding="utf-8")
    for src in (apife, apibe):
        assert "/laim/installations/verify" in src
        assert "/laim/installations/propose" in src
        assert "/recognize" in src
        assert "/reject" in src
        assert "/laim/installations/notifications/pending" in src
    assert 'prefix="/laim/installations"' in router
    assert '@router.post("/verify")' in router
    assert '@router.post("/propose")' in router
    pending = router.find('@router.get("/notifications/pending")')
    by_id = router.find("@router.patch(\"/{installation_id}\")")
    assert pending != -1 and by_id != -1 and pending < by_id
    assert "/recognize" in router
    assert "/reject" in router
    assert "laim_installations_request" in mw
    assert "laim_installations_request" in broker
    assert "router_laim_installations" in core
    assert "decrypt_install_payload" in router
    assert "load_install_register_keys" in router
    assert "el cuerpo debe ir cifrado" in (
        _ROOT.parent / "2_shared_application" / "security" / "laim_install_register.py"
    ).read_text(encoding="utf-8")

"""Contrato de la página Registro: menú, serial en core, sin master_key."""

from __future__ import annotations

from pathlib import Path

_LAIMWEB = Path(__file__).resolve().parents[1] / "laim_web"
_BACKEND = Path(__file__).resolve().parents[2] / "3_backend"
_APIFE = Path(__file__).resolve().parents[2] / "7_service_frontend" / "apife.py"
_APIBE = Path(__file__).resolve().parents[2] / "8_service_backend" / "apibe.py"
_NGINX = Path(
    "/Users/perico/develop/anh_ansible_environments/templates/docker-compose/frontend/frontend.conf.j2"
)


def test_menu_places_registro_between_instaladores_and_manuales() -> None:
    index = (_LAIMWEB / "pages" / "index.py").read_text(encoding="utf-8")
    assert '"registro": "Registro"' in index
    logged = index.split("LOGGED_IN_MENU_ITEMS = [", 1)[1].split("]", 1)[0]
    assert '"instaladores"' in logged
    assert '"registro"' in logged
    assert '"manuales"' in logged
    assert logged.index('"instaladores"') < logged.index('"registro"') < logged.index('"manuales"')
    assert "registro_panel()" in index


def test_panel_has_manual_form_validated_serial_and_actions() -> None:
    panel = (_LAIMWEB / "components" / "registro_panel.py").read_text(encoding="utf-8")
    assert "Registro manual" in panel
    assert "✅ Validado" in panel
    assert "verify_install_serial" in panel
    assert "on_blur" in panel
    assert "Reconocer" in panel
    assert "Rechazar" in panel
    assert "Acciones" in panel
    assert "master_key" not in panel
    assert "install_editing" in panel
    assert "Alias del dispositivo" in panel
    assert "Community Edition" in panel
    assert "list(_EDITION_OPTIONS)" not in panel
    assert "serial_masked" in panel
    assert "Una instalación de LAIM espera su reconocimiento" in panel
    assert "ticket de soporte" in (
        _BACKEND / "laim_installations_service.py"
    ).read_text(encoding="utf-8")


def test_verify_and_persist_go_through_middleware_to_core() -> None:
    client = (_LAIMWEB / "adapters" / "laim_api_client.py").read_text(encoding="utf-8")
    apife = _APIFE.read_text(encoding="utf-8")
    apibe = _APIBE.read_text(encoding="utf-8")
    router = (_BACKEND / "router_laim_installations.py").read_text(encoding="utf-8")
    service = (_BACKEND / "laim_installations_service.py").read_text(encoding="utf-8")
    assert "/laim/installations/verify" in client
    assert "/laim/installations/propose" in apife
    assert "/laim/installations/propose" in apibe
    assert 'prefix="/laim/installations"' in router
    assert '@router.post("/propose")' in router
    assert "verify_serial" in service
    assert "master_key" in service
    assert "El número de serie no es válido" in service
    nginx = _NGINX.read_text(encoding="utf-8")
    assert nginx.count("location /laim/installations/") >= 2

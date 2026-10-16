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
_BACKEND_ENV = Path(
    "/Users/perico/develop/anh_ansible_environments/templates/docker-compose/backend/.env.j2"
)
_BACKEND_COMPOSE = Path(
    "/Users/perico/develop/anh_ansible_environments/templates/docker-compose/backend/docker-compose.yml.j2"
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


def test_panel_has_registration_instructions_modal() -> None:
    panel = (_LAIMWEB / "components" / "registro_panel.py").read_text(encoding="utf-8")
    state = (_LAIMWEB / "laim_state.py").read_text(encoding="utf-8")
    index = (_LAIMWEB / "pages" / "index.py").read_text(encoding="utf-8")
    intro = (_LAIMWEB.parent / "static_pages" / "registro.md").read_text(encoding="utf-8")
    assert "Instrucciones de Registro" in panel
    assert "install_instructions_modal" in panel
    assert "open_install_instructions" in panel
    assert "close_install_instructions" in panel
    assert "install_instructions_open" in state
    assert "def open_install_instructions" in state
    assert "install_instructions_modal()" in index
    assert "ventana de login" in panel
    assert "⎘" in panel
    assert "2-K3MP-9QRA-LW7N-4BXT-M8HJ12C" in panel
    assert "PORTATIL-CASA" in panel
    assert "ana@empresa.com" in panel
    assert "Enviar propuesta" in panel
    assert "Internal › Local" in panel
    assert "Reconocer" in panel
    assert "ventana de login" in intro
    assert "Instrucciones de Registro" in intro


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
    assert "LAIM_SERIAL_SIGNING_KEY" in service
    assert "product_serial_signing_key" in (
        Path(__file__).resolve().parents[3]
        / "2_shared_application"
        / "security"
        / "laim_serial.py"
    ).read_text(encoding="utf-8")
    assert "No se puede validar el número de serie ahora mismo" in service
    nginx = _NGINX.read_text(encoding="utf-8")
    assert nginx.count("location /laim/installations/") >= 2
    env_j2 = _BACKEND_ENV.read_text(encoding="utf-8")
    compose = _BACKEND_COMPOSE.read_text(encoding="utf-8")
    assert "LAIM_SERIAL_SIGNING_KEY={{ laim_serial_signing_key | default('') }}" in env_j2
    assert 'LAIM_SERIAL_SIGNING_KEY: "${LAIM_SERIAL_SIGNING_KEY}"' in compose
    play = Path(
        "/Users/perico/develop/anh_ansible_environments/frontend.yml"
    ).read_text(encoding="utf-8")
    vhost = play.split("Generar vhost de nginx para docker-compose", 1)[1][:3500]
    assert "notify: recrear nginx (docker-compose)" in vhost
    assert "flush_handlers" in vhost
    assert "State.StartedAt" in vhost
    assert "nginx-frontend" in vhost
    for env_name in ("silicon", "dev", "pre"):
        backend_env = Path(
            f"/Users/perico/develop/anh_ansible_environments/env/{env_name}/backend.yml"
        ).read_text(encoding="utf-8")
        assert "laim_serial_signing_key" in backend_env

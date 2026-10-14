"""Captura de auditoría en el portal: copiar script, Descargar y cambio de sección."""

from pathlib import Path

_LAIMWEB = Path(__file__).resolve().parents[1] / "laim_web"
_STATE = (_LAIMWEB / "laim_state.py").read_text(encoding="utf-8")
_PANEL = (_LAIMWEB / "components" / "installers_panel.py").read_text(encoding="utf-8")
_CLIENT = (_LAIMWEB / "adapters" / "laim_api_client.py").read_text(encoding="utf-8")
_MIXIN = (_LAIMWEB / "laim_forum_mixin.py").read_text(encoding="utf-8")


def test_copy_script_records_auditoria() -> None:
    assert "def copy_installers_script" in _STATE
    assert 'laim_auditoria_instalador(\n                "copia_script"' in _STATE
    assert "on_click=LaimWebState.copy_installers_script" in _PANEL
    assert "rx.set_clipboard" in _STATE


def test_download_button_records_auditoria() -> None:
    assert "def record_installers_download" in _STATE
    assert 'laim_auditoria_instalador(\n                "descarga"' in _STATE
    assert "on_click=LaimWebState.record_installers_download" in _PANEL


def test_set_menu_and_heartbeat_call_seccion() -> None:
    assert "def _record_auditoria_seccion" in _STATE
    assert "auditoria_heartbeat_loop" in _STATE
    assert "def auditoria_heartbeat_visible" in _STATE
    assert "document.visibilityState" in _STATE
    assert "self._record_auditoria_seccion(item)" in _STATE


def test_forum_load_records_foro_seccion() -> None:
    assert 'recorder("foro")' in _MIXIN


def test_client_exposes_auditoria_endpoints() -> None:
    assert "/laim/auditoria/heartbeat" in _CLIENT
    assert "/laim/auditoria/seccion" in _CLIENT
    assert "/laim/auditoria/instaladores" in _CLIENT

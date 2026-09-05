"""Tests de flujo de sesión en LaimWebState."""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[4]
laimweb_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(laimweb_root))


def test_handle_logout_redirects_and_resets_menu() -> None:
    """Logout redirige a inicio y limpia la sesión en código."""
    source_path = laimweb_root / "laim_web" / "laim_state.py"
    source = source_path.read_text(encoding="utf-8")

    assert "return rx.redirect(\"/\")" in source
    assert 'self.active_menu = "inicio"' in source
    assert 'self._load_static_page("inicio")' in source
    assert "self.is_logged_in = False" in source
    assert "self._token_renewal_running = False" in source


def test_sync_menu_for_session_defaults() -> None:
    """La sincronización de menú fuerza instaladores/inicio según sesión."""
    source_path = laimweb_root / "laim_web" / "laim_state.py"
    source = source_path.read_text(encoding="utf-8")

    assert "def _sync_menu_for_session" in source
    assert "AUTHENTICATED_PAGE_MENUS" in source
    assert 'self.active_menu = "instaladores"' in source
    assert 'self.active_menu = "inicio"' in source
    assert "self._sync_menu_for_session()" in source


def test_user_info_panel_hides_organization() -> None:
    """El sidebar no muestra la organización al usuario."""
    source_path = laimweb_root / "laim_web" / "pages" / "index.py"
    source = source_path.read_text(encoding="utf-8")

    assert "organization_id" not in source
    assert "Org:" not in source


def test_public_menu_places_escenarios_after_documentacion() -> None:
    """Escenarios queda debajo de Documentación en el menú público."""
    source_path = laimweb_root / "laim_web" / "pages" / "index.py"
    source = source_path.read_text(encoding="utf-8")
    assert '"documentacion",\n    "escenarios",\n    "contacto"' in source
    assert '"escenarios": "Escenarios"' in source

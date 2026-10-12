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


def test_specialized_and_custom_model_pages_show_wip_badge() -> None:
    """Especializados y personalizados llevan In progress: aún no están."""
    from laim_web.static_pages_loader import load_static_page_markdown

    for menu in ("modelos_especializados", "modelos_personalizados"):
        content = load_static_page_markdown(menu)
        assert "`In progress`" in content
        assert "aún no está disponible" in content
    source = (laimweb_root / "laim_web" / "pages" / "index.py").read_text(
        encoding="utf-8"
    )
    assert "WIP_PAGE_MENUS" in source
    assert "modelos_especializados" in source
    assert "modelos_personalizados" in source
    assert 'class_name="crt-badge-wip"' in source


def test_logged_in_menu_uses_agents_not_skills() -> None:
    """El menú autenticado muestra Agentes, no Skills."""
    source_path = laimweb_root / "laim_web" / "pages" / "index.py"
    source = source_path.read_text(encoding="utf-8")
    assert '"agents": "Agentes"' in source
    assert '"agents": "Agents"' not in source
    assert '"skills": "Skills"' not in source
    assert '"agents",' in source


def test_login_modal_stays_mounted_while_typing() -> None:
    """El overlay de login no se desmonta en cada tecla (cierre fantasma en silicon)."""
    source = (
        laimweb_root / "laim_web" / "components" / "auth_modals.py"
    ).read_text(encoding="utf-8")
    assert "def login_modal()" in source
    assert 'display=rx.cond(LaimWebState.login_modal_open, "flex", "none")' in source
    assert "on_mouse_down=LaimWebState.close_login_modal" in source
    assert "on_click=LaimWebState.close_login_modal" not in source
    assert "on_mouse_down=rx.stop_propagation" in source


def test_help_manuals_open_from_page_actions() -> None:
    """Manuales abre cada réplica sin meter el cuerpo en el estado Redis."""
    state_src = (laimweb_root / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    actions_src = (
        laimweb_root / "laim_web" / "components" / "page_actions.py"
    ).read_text(encoding="utf-8")
    index_src = (laimweb_root / "laim_web" / "pages" / "index.py").read_text(
        encoding="utf-8"
    )
    assert "from laim_web.help_manuals import BACK_TO_MANUALES_ACTION, menu_for_action" in state_src
    assert "HELP_MANUAL_PAGE_MENUS" in state_src
    assert "no meter 300 KB en Redis" in state_src
    assert "sidebar_active_menu" in state_src
    assert "HELP_MANUALS" in actions_src
    assert "item.action_key" in actions_src
    assert "BACK_TO_MANUALES_ACTION" in actions_src
    assert "load_static_page_markdown(item.menu)" in index_src


def test_installers_page_lists_packages_not_patches() -> None:
    """Instaladores solo consulta artefactos installer; Windows tiene comando."""
    state_src = (laimweb_root / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    panel_src = (
        laimweb_root / "laim_web" / "components" / "installers_panel.py"
    ).read_text(encoding="utf-8")
    assert 'get_laim_product_list(edition, "installer"' in state_src
    assert 'get_laim_product_list(edition, "patch"' not in state_src
    assert "Todavía no hay ningún parche publicado" not in state_src
    assert "Todavía no hay ningún parche publicado" not in panel_src
    assert "_patches_result" not in panel_src
    assert "curl.exe -fsSL" in state_src
    assert "installers_filename" in state_src


def test_public_menu_places_escenarios_after_documentacion() -> None:
    """Escenarios queda debajo de Documentación en el menú público."""
    source_path = laimweb_root / "laim_web" / "pages" / "index.py"
    source = source_path.read_text(encoding="utf-8")
    assert '"documentacion",\n    "escenarios",\n    "contacto"' in source
    assert '"escenarios": "Escenarios"' in source

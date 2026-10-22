"""Contrato del backoffice Foro LAIM frente a las doce acciones de Radikal.

El hub ya existía en /config-foro. Configuración → Foro LAIM tiene que
pintar ese mismo panel, y las ediciones que Radikal ofrece (orden, activa,
ban, rotación, prefijos inactivos, reglas) tienen que estar en la vista.
El menú público Foro no gana rutas de administración.
"""

from __future__ import annotations

from pathlib import Path

APP = Path(__file__).resolve().parents[1]
HUB = (APP / "laim_web" / "components" / "forum_service_panel.py").read_text(
    encoding="utf-8"
)
INDEX = (APP / "laim_web" / "pages" / "index.py").read_text(encoding="utf-8")
SHELL = (APP / "laim_web" / "components" / "portal_shell.py").read_text(
    encoding="utf-8"
)
MIXIN = (APP / "laim_web" / "laim_forum_mixin.py").read_text(encoding="utf-8")
ADMIN_UI = (APP / "laim_web" / "components" / "forum_ui.py").read_text(
    encoding="utf-8"
)
EXTENDED = (APP / "laim_web" / "components" / "forum_extended_ui.py").read_text(
    encoding="utf-8"
)
CLIENT = (APP / "laim_web" / "adapters" / "laim_api_client.py").read_text(
    encoding="utf-8"
)
STATE = (APP / "laim_web" / "laim_state.py").read_text(encoding="utf-8")

RADIKAL_ACTIONS = (
    "Configuración general",
    "Categorías",
    "Subcategorías",
    "Prefijos de hilo",
    "Moderadores",
    "Baneos activos",
    "Permisos moderación",
    "Reglas automáticas",
    "URLs autorizadas",
    "Visor de logs",
    "Estadísticas",
    "Actualizar estado",
)


def _forum_nav_section() -> str:
    start = SHELL.index("def forum_nav_section")
    end = SHELL.index("def portal_sidebar", start)
    return SHELL[start:end]


def test_hub_keeps_the_twelve_radikal_actions() -> None:
    for label in RADIKAL_ACTIONS:
        assert label in HUB


def test_config_foro_menu_renders_the_admin_hub() -> None:
    assert 'active_menu == "config_foro"' in INDEX or '("config_foro"' in INDEX
    assert "forum_admin_view_router" in INDEX or "forum_config_embedded" in INDEX
    assert "forum_config_embedded" in HUB
    assert 'item == "config_foro"' in STATE


def test_public_forum_menu_stays_without_admin_routes() -> None:
    section = _forum_nav_section()
    assert "/config-foro" not in section
    assert "/foro-moderacion" not in section


def test_category_and_subcategory_edit_cover_orden_activa_ban_and_rotation() -> None:
    assert "forum_admin_edit_category" in MIXIN
    assert "forum_admin_edit_subcategory" in MIXIN
    assert "forum_admin_category_orden" in ADMIN_UI
    assert "forum_admin_category_activa" in ADMIN_UI
    assert "forum_admin_subcategory_orden" in ADMIN_UI
    assert "forum_admin_subcategory_activa" in ADMIN_UI
    assert "forum_admin_subcategory_ban_seconds" in ADMIN_UI
    assert "forum_admin_subcategory_log_rotation" in ADMIN_UI
    assert "Editar categoría" in ADMIN_UI
    assert "Editar subcategoría" in ADMIN_UI


def test_prefix_admin_lists_and_edits_including_inactive() -> None:
    assert "forum_admin_edit_prefix" in MIXIN
    assert "forum_admin_prefixes" in EXTENDED
    assert "forum_admin_prefix_activo" in EXTENDED
    assert "include_inactive" in CLIENT


def test_word_rule_can_be_edited_and_toggled() -> None:
    assert "forum_admin_edit_word_rule" in MIXIN
    assert "forum_admin_toggle_word_rule" in MIXIN
    assert "laim_forum_admin_update_word_rule" in MIXIN
    assert "Editar" in EXTENDED
    assert "forum_admin_toggle_word_rule" in EXTENDED


def test_general_config_is_read_only_runtime_data() -> None:
    assert "Host API" in HUB
    assert "Puerto API" in HUB
    assert "Poll" in HUB
    assert "Strikes" in HUB
    assert "env.yaml" not in HUB

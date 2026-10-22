"""Tests de navegación: Configuración solo admin y solo páginas documentales."""

from pathlib import Path


def test_forum_nav_excludes_admin_routes() -> None:
    """Config. foro y Moderación no aparecen en la sección Foro."""
    source = (
        Path(__file__).resolve().parents[1]
        / "laim_web/components/portal_shell.py"
    ).read_text(encoding="utf-8")
    forum_section_start = source.index("def forum_nav_section")
    forum_section_end = source.index("def portal_sidebar", forum_section_start)
    forum_section = source[forum_section_start:forum_section_end]

    assert "/config-foro" not in forum_section
    assert "/foro-moderacion" not in forum_section


def test_config_menu_is_documentary_and_admin_only() -> None:
    """Configuración abre Foro LAIM con set_menu, sin enlazar /config-foro."""
    source = (
        Path(__file__).resolve().parents[1]
        / "laim_web/components/portal_shell.py"
    ).read_text(encoding="utf-8")
    menu = source.split("def sidebar_config_menu", 1)[1].split(
        "def forum_nav_section", 1
    )[0]
    assert "/config-foro" not in menu
    assert "/foro-moderacion" not in menu
    assert "ADMIN_CONFIG_ROUTE_LINKS" not in source
    assert "LaimWebState.is_laim_admin" in menu
    assert '"Foro LAIM"' in source
    assert '"General"' in source
    assert '"Gestión de usuarios"' not in source
    assert '"Modelos IA"' not in source
    assert '"Fases y tiers"' not in source
    assert '"Gestión de sesiones"' not in source
    assert '"LAIM Share / Connect"' not in source
    assert '"Agentes"' not in source
    assert '"Auditoría y logs"' not in source


def test_main_sidebar_reuses_admin_gated_config_menu() -> None:
    """El portal principal usa el mismo menú Configuración que el foro."""
    index = (
        Path(__file__).resolve().parents[1] / "laim_web/pages/index.py"
    ).read_text(encoding="utf-8")
    assert "sidebar_config_menu" in index

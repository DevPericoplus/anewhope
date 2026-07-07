"""Tests de navegación: foro admin bajo menú Configuración."""

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


def test_config_menu_includes_forum_admin_routes() -> None:
    """El menú Configuración incluye rutas admin del foro."""
    source = (
        Path(__file__).resolve().parents[1]
        / "laim_web/components/portal_shell.py"
    ).read_text(encoding="utf-8")

    assert '("/config-foro", "Config. foro")' in source
    assert '("/foro-moderacion", "Moderación")' in source
    assert "LaimWebState.is_laim_admin" in source

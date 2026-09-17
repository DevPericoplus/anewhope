"""Tests del acordeón de secciones en Inicio."""

from pathlib import Path

_LAIMWEB_ROOT = Path(__file__).resolve().parents[1]


def test_inicio_page_wires_accordion_panel() -> None:
    """La página Inicio usa el panel de secciones contraíbles."""
    source = (_LAIMWEB_ROOT / "laim_web" / "pages" / "index.py").read_text(
        encoding="utf-8"
    )
    assert "inicio_accordion_panel" in source
    assert '("inicio", inicio_accordion_panel())' in source


def test_inicio_accordion_uses_laim_crt_title_color() -> None:
    """LAIM COLORS no tiene 'primary'; los títulos usan 'title'."""
    source = (
        _LAIMWEB_ROOT / "laim_web" / "components" / "inicio_accordion.py"
    ).read_text(encoding="utf-8")
    assert 'COLORS["primary"]' not in source
    assert 'COLORS["title"]' in source

    from laim_web.components.crt_theme import COLORS

    assert "title" in COLORS
    assert "primary" not in COLORS


def test_laim_state_has_inicio_accordion_events() -> None:
    """El State hidrata y conmuta las secciones de Inicio."""
    source = (_LAIMWEB_ROOT / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    assert "def _hydrate_inicio_sections" in source
    assert "def toggle_inicio_section" in source
    assert "def expand_inicio_sections" in source
    assert "def collapse_inicio_sections" in source
    assert 'if menu == "inicio"' in source

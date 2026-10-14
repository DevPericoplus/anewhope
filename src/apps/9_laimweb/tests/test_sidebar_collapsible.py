"""MENÚ y FORO del sidebar empiezan contraídos y se expanden al pulsar."""

from pathlib import Path

_LAIMWEB = Path(__file__).resolve().parents[1] / "laim_web"
_STATE = (_LAIMWEB / "laim_state.py").read_text(encoding="utf-8")
_INDEX = (_LAIMWEB / "pages" / "index.py").read_text(encoding="utf-8")
_SHELL = (_LAIMWEB / "components" / "portal_shell.py").read_text(encoding="utf-8")


def test_sidebar_sections_start_collapsed() -> None:
    assert "sidebar_menu_open: bool = False" in _STATE
    assert "sidebar_forum_open: bool = False" in _STATE
    assert "def toggle_sidebar_menu" in _STATE
    assert "def toggle_sidebar_forum" in _STATE


def test_menu_and_forum_headers_toggle() -> None:
    assert "toggle_sidebar_menu" in _INDEX
    assert "sidebar_menu_open" in _INDEX
    assert "toggle_sidebar_forum" in _SHELL
    assert "sidebar_forum_open" in _SHELL
    assert 'rx.text("Menú"' in _INDEX
    assert 'rx.text("Foro"' in _SHELL

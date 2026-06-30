"""Tests del cargador de páginas estáticas markdown."""

from laim_web.static_pages_loader import (
    STATIC_PAGE_MENUS,
    load_static_page_markdown,
)


def test_static_page_menus_contains_public_sections() -> None:
    """Las secciones públicas del menú tienen fichero markdown."""
    assert STATIC_PAGE_MENUS == frozenset(
        {"inicio", "servicios", "documentacion", "contacto"}
    )


def test_load_inicio_markdown() -> None:
    """Carga el contenido de inicio.md."""
    content = load_static_page_markdown("inicio")
    assert "# Bienvenido a LAIM" in content


def test_load_unknown_menu_returns_message() -> None:
    """Un menú sin fichero asociado devuelve mensaje de error."""
    content = load_static_page_markdown("dashboard")
    assert "Página no encontrada" in content

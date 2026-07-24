"""Tests del cargador de páginas estáticas markdown."""

from laim_web.static_pages_loader import (
    ADMIN_CONFIG_PAGE_MENUS,
    AUTHENTICATED_PAGE_MENUS,
    STATIC_PAGE_MENUS,
    load_static_page_markdown,
)


def test_static_page_menus_contains_public_sections() -> None:
    """Las secciones públicas del menú tienen fichero markdown."""
    assert {
        "inicio",
        "presentacion",
        "servicios",
        "documentacion",
        "contacto",
    }.issubset(STATIC_PAGE_MENUS)


def test_authenticated_menus_have_markdown_files() -> None:
    """Todas las secciones autenticadas tienen contenido markdown."""
    expected = {
        "instaladores",
        "manuales",
        "modelos_base",
        "modelos_especializados",
        "modelos_personalizados",
        "skills",
        "complementos",
        "soporte",
        "faq",
    }
    assert expected == AUTHENTICATED_PAGE_MENUS
    for menu in expected:
        content = load_static_page_markdown(menu)
        assert content.startswith("#")


def test_load_inicio_markdown() -> None:
    """Carga el contenido de inicio.md."""
    content = load_static_page_markdown("inicio")
    assert "# Bienvenido a LAIM" in content


def test_load_presentacion_markdown() -> None:
    """Carga el contenido de presentacion.md."""
    content = load_static_page_markdown("presentacion")
    assert "# Presentación" in content
    assert "traductor de conocimiento" in content.lower()


def test_load_instaladores_markdown() -> None:
    """Carga el contenido de instaladores.md."""
    content = load_static_page_markdown("instaladores")
    assert "Instaladores LAIM" in content


def test_static_page_menus_includes_admin_config() -> None:
    """Las páginas de configuración admin están en el catálogo global."""
    assert ADMIN_CONFIG_PAGE_MENUS.issubset(STATIC_PAGE_MENUS)


def test_markdown_component_map_uses_codeblock_not_pre() -> None:
    """Los bloques fenced deben mapearse a codeblock (no pre) para evitar errores JS."""
    from laim_web.components.markdown_viewer import CRT_MARKDOWN_COMPONENT_MAP

    assert "codeblock" in CRT_MARKDOWN_COMPONENT_MAP
    assert "pre" not in CRT_MARKDOWN_COMPONENT_MAP
    assert "table" in CRT_MARKDOWN_COMPONENT_MAP
    assert "li" in CRT_MARKDOWN_COMPONENT_MAP


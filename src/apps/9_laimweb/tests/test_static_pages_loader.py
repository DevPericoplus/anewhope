"""Tests del cargador de páginas estáticas markdown."""

from laim_web.static_pages_loader import (
    ADMIN_CONFIG_PAGE_MENUS,
    AUTHENTICATED_PAGE_MENUS,
    STATIC_PAGE_MENUS,
    load_static_page_markdown,
    split_markdown_h2_sections,
)


def test_static_page_menus_contains_public_sections() -> None:
    """Las secciones públicas del menú tienen fichero markdown."""
    assert {
        "inicio",
        "presentacion",
        "servicios",
        "documentacion",
        "escenarios",
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
    assert "MOM" in content
    assert "Mixture of Models" in content
    assert "Mixture of Experts" in content
    assert "Los administradores de cada LAIM" in content
    assert "familias de tiers" in content
    assert "Warmup predictivo" in content
    assert "KV-cache" in content
    assert "Tiers de modelos" in content
    assert "## El Alma de LAIM" in content
    assert "Sugerir mejora" in content
    assert "aprendizaje automático" in content
    assert "reiniciar" in content
    assert "## Acaricia al jerbo" in content
    assert "doble clic" in content
    assert "logo" in content
    assert "Hasta dónde se puede llegar" in content
    assert "LAIM, según el caso, el hardware y tu configuración" not in content


def test_split_markdown_h2_keeps_subheadings_inside_parent() -> None:
    """El parser deja ### dentro del cuerpo y no crea secciones extra."""
    markdown = (
        "# Título\n\n"
        "preámbulo\n\n"
        "## Primera\n\n"
        "cuerpo uno\n\n"
        "### Sub\n\n"
        "detalle\n\n"
        "## Segunda\n\n"
        "cuerpo dos\n"
    )
    title, preamble, sections = split_markdown_h2_sections(markdown)
    assert title == "Título"
    assert "preámbulo" in preamble
    assert [item["title"] for item in sections] == ["Primera", "Segunda"]
    assert "### Sub" in sections[0]["body"]
    assert "cuerpo uno" in sections[0]["body"]
    assert "## Primera" not in sections[0]["body"]


def test_inicio_splits_into_collapsible_h2_sections() -> None:
    """Inicio se parte en secciones ## usadas por el acordeón."""
    content = load_static_page_markdown("inicio")
    title, _preamble, sections = split_markdown_h2_sections(content)
    titles = [item["title"] for item in sections]
    assert title == "Bienvenido a LAIM"
    assert "MOM: Mixture of Models" in titles
    assert "El Alma de LAIM" in titles
    assert "Acaricia al jerbo" in titles
    mom = next(item for item in sections if item["title"].startswith("MOM"))
    assert "familias de tiers" in mom["body"]
    assert "## MOM" not in mom["body"]
    alma = next(item for item in sections if "Alma" in item["title"])
    assert "Sugerir mejora" in alma["body"]
    assert "### " in alma["body"]


def test_load_presentacion_markdown() -> None:
    """Carga el contenido de presentacion.md."""
    content = load_static_page_markdown("presentacion")
    assert "# Presentación" in content
    assert "traductor de conocimiento" in content.lower()


def test_load_documentacion_markdown() -> None:
    """Carga el contenido actualizado de documentacion.md."""
    content = load_static_page_markdown("documentacion")
    assert "# Documentación" in content
    assert "laim help" in content
    assert "laim.exe help" in content
    assert "./bin/" not in content
    assert "**`agents`**" in content
    assert "**`webdebug`**" in content
    assert "Mixture of Models" in content
    assert "los administradores asignan" in content
    assert "Sugerir" in content
    assert "alma" in content.lower()


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


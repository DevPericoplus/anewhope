"""Tests del cargador de páginas estáticas markdown."""

from pathlib import Path

from laim_web.help_manuals import HELP_MANUALS, HELP_MANUAL_PAGE_MENUS
from laim_web.static_pages_loader import (
    ADMIN_CONFIG_PAGE_MENUS,
    AUTHENTICATED_PAGE_MENUS,
    STATIC_PAGE_MENUS,
    load_static_page_markdown,
    split_markdown_h2_sections,
)

_LAIM_SPANISH = (
    Path(__file__).resolve().parents[5]
    / "laim"
    / "internal"
    / "manuals"
    / "spanish"
)
_HEADSCALE_ASSETS = (
    Path(__file__).resolve().parents[1] / "assets" / "images" / "headscale"
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
        "agents",
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


def test_load_faq_covers_cli_commands_with_examples() -> None:
    """FAQ explica la CLI de LAIM con ejemplos, no solo el mapa de Documentación."""
    content = load_static_page_markdown("faq")
    title, _preamble, sections = split_markdown_h2_sections(content)
    assert title == "Preguntas frecuentes (FAQ)"
    titles = [item["title"] for item in sections]
    assert "Respuestas rápidas con transparencia" in titles
    assert "Cómo usar la CLI" in titles
    cli = next(item for item in sections if item["title"] == "Cómo usar la CLI")
    assert "laim help" in cli["body"]
    assert "laim.exe help" in cli["body"]
    assert "laim login" in cli["body"]
    assert "laim chat" in cli["body"]
    assert "llama3.2:1b" in cli["body"]
    assert "laim web" in cli["body"]
    assert "laim webdebug" in cli["body"]
    assert "laim init" in cli["body"]
    assert "laim config" in cli["body"]
    assert "laim localmodels" in cli["body"]
    assert "laim catalog" in cli["body"]
    assert "laim eval" in cli["body"]
    assert "laim compare" in cli["body"]
    assert "laim connect" in cli["body"]
    assert "laim share" in cli["body"]
    assert "laim agents" in cli["body"]
    assert "laim update check" in cli["body"]
    assert "laim audit" in cli["body"]
    assert "laim notifications" in cli["body"]
    assert "laim monitor" in cli["body"]
    assert "```" in cli["body"]
    assert "administrador" in cli["body"].lower()


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
    assert "Reflex" not in content
    assert "reflex.dev" not in content
    assert "## En la Ayuda del cliente" in content
    assert "## Manual de administrador" in content
    assert "## Manual de usuario" in content
    assert "## Red mesh WireGuard (Headscale)" in content
    assert "## Recomendaciones" in content
    assert "## Ventana de contexto" in content
    assert "## Windows remoto (OpenSSH)" in content
    assert "## Editor" in content
    assert "## Temas" in content


def test_load_instaladores_markdown() -> None:
    """Instaladores describe paquetes reales y la guía de init/colas."""
    content = load_static_page_markdown("instaladores")
    assert "Instaladores LAIM" in content
    assert ".dmg" in content
    assert ".pkg" not in content
    assert "laim init" in content
    assert "Gestor de colas" in content
    assert "Ollama" in content
    assert "Todavía no hay ningún parche" not in content
    assert "Paquete .pkg" not in content


def test_static_page_menus_includes_admin_config() -> None:
    """Las páginas de configuración admin están en el catálogo global."""
    assert ADMIN_CONFIG_PAGE_MENUS.issubset(STATIC_PAGE_MENUS)


def test_markdown_component_map_uses_codeblock_not_pre() -> None:
    """Los bloques fenced deben mapearse a codeblock (no pre) para evitar errores JS."""
    from laim_web.components.markdown_viewer import CRT_MARKDOWN_COMPONENT_MAP

    assert "codeblock" in CRT_MARKDOWN_COMPONENT_MAP
    assert "code" in CRT_MARKDOWN_COMPONENT_MAP
    assert "pre" not in CRT_MARKDOWN_COMPONENT_MAP
    assert "table" in CRT_MARKDOWN_COMPONENT_MAP
    assert "li" in CRT_MARKDOWN_COMPONENT_MAP


def test_load_servicios_markdown() -> None:
    """Servicios describe el portal real y no el área pública obvia."""
    content = load_static_page_markdown("servicios")
    assert "# Servicios" in content
    assert "### Instaladores" in content
    assert "### Manuales" in content
    assert "Manual de administrador" in content
    assert "### Modelos de IA local" in content
    assert "### Agentes" in content
    assert "Local System" in content
    assert "LAIM cloud genérica" in content
    assert "`In progress`" in content
    assert "### Foro" in content
    assert "Qué encontrará en el área pública" not in content
    assert "### Skills" not in content
    assert "### Agents" not in content


def test_load_agents_markdown() -> None:
    """Agentes sustituye a Skills: ecosistema, skills, tools y flujos."""
    content = load_static_page_markdown("agents")
    assert content.startswith("# Agentes")
    assert not content.startswith("# Agents")
    assert not content.startswith("# Skills")
    assert "Local System" in content
    assert "Heuristic" in content
    assert "laim agents" in content
    assert "## Skills" in content
    assert "## Tools" in content
    assert "Agent Box" in content
    assert "pipeline" in content.lower()
    assert "ecosistema" in content.lower()


def test_load_manuales_index_lists_ayuda_catalog() -> None:
    """El índice de Manuales lista los 6 documentos de Ayuda y abre réplicas."""
    content = load_static_page_markdown("manuales")
    assert "# Manuales" in content
    assert "Bienvenido a la Ayuda de LAIM" in content
    assert "Manual de administrador" in content
    assert "Manual de usuario" in content
    assert "Red mesh WireGuard (Headscale)" in content
    assert "Recomendaciones" in content
    assert "Ventana de contexto" in content
    assert "Windows remoto (OpenSSH)" in content
    assert "El texto completo vive" not in content
    assert "no en este portal" not in content


def test_help_manuals_are_hidden_authenticated_pages() -> None:
    """Las réplicas no van al menú lateral; sí al catálogo de páginas."""
    assert HELP_MANUAL_PAGE_MENUS.isdisjoint(AUTHENTICATED_PAGE_MENUS)
    assert HELP_MANUAL_PAGE_MENUS.issubset(STATIC_PAGE_MENUS)
    assert {item.laim_id for item in HELP_MANUALS} == {
        "admin",
        "user",
        "headscale",
        "recommendations",
        "context_window",
        "windows_remote",
    }


def test_help_manual_replicas_match_laim_spanish() -> None:
    """Cada réplica es el markdown español canónico de laim."""
    for item in HELP_MANUALS:
        replica = load_static_page_markdown(item.menu)
        assert replica.startswith("#")
        assert len(replica) > 1000
        source = _LAIM_SPANISH / f"{item.laim_id}_manual.md"
        if source.is_file():
            assert replica == source.read_text(encoding="utf-8")


def test_headscale_manual_figures_are_in_assets() -> None:
    """Las 8 figuras CRT del manual de malla se sirven en /images/headscale/."""
    content = load_static_page_markdown("manual_headscale")
    assert "/images/headscale/fig01-hub-spoke.svg" in content
    for name in (
        "fig01-hub-spoke.svg",
        "fig02a-hairpin.svg",
        "fig02b-multihub.svg",
        "fig03-mesh.svg",
        "fig04-coordination.svg",
        "fig05-identity.svg",
        "fig06-nat-stun.svg",
        "fig07-derp.svg",
        "fig08-acl-nodes.svg",
    ):
        assert (_HEADSCALE_ASSETS / name).is_file()


def test_inline_code_maps_in_progress_to_badge() -> None:
    """El chip `In progress` del catálogo no se renderiza como código."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "laim_web"
        / "components"
        / "markdown_viewer.py"
    ).read_text(encoding="utf-8")
    assert 'if label.strip() == "In progress"' in source
    assert 'class_name="crt-badge-wip"' in source


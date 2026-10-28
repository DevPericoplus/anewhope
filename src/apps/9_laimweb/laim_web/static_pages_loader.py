"""Carga de contenido markdown desde static_pages/."""

from __future__ import annotations

import re
from pathlib import Path

from laim_web.help_manuals import HELP_MANUAL_MENU_FILES

STATIC_PAGES_DIR = Path(__file__).resolve().parent.parent / "static_pages"

PUBLIC_MENU_FILES: dict[str, str] = {
    "inicio": "inicio.md",
    "presentacion": "presentacion.md",
    "servicios": "servicios.md",
    "documentacion": "documentacion.md",
    "escenarios": "escenarios.md",
    "contacto": "contacto.md",
}

AUTHENTICATED_MENU_FILES: dict[str, str] = {
    "instaladores": "instaladores.md",
    "registro": "registro.md",
    "manuales": "manuales.md",
    "modelos_base": "modelos_base.md",
    "modelos_especializados": "modelos_especializados.md",
    "modelos_personalizados": "modelos_personalizados.md",
    "agents": "agents.md",
    "complementos": "complementos.md",
    "soporte": "soporte.md",
    "faq": "faq.md",
}

ADMIN_CONFIG_MENU_FILES: dict[str, str] = {
    "config_general": "config_general.md",
    "config_foro": "config_foro.md",
}

MENU_TO_MARKDOWN_FILE: dict[str, str] = {
    **PUBLIC_MENU_FILES,
    **AUTHENTICATED_MENU_FILES,
    **ADMIN_CONFIG_MENU_FILES,
    **HELP_MANUAL_MENU_FILES,
}

STATIC_PAGE_MENUS = frozenset(MENU_TO_MARKDOWN_FILE.keys())
AUTHENTICATED_PAGE_MENUS = frozenset(AUTHENTICATED_MENU_FILES.keys())
ADMIN_CONFIG_PAGE_MENUS = frozenset(ADMIN_CONFIG_MENU_FILES.keys())

# SuperAdmin (1) y Administrador de organización (2) en laim_identity_types.
LAIM_ADMIN_IDENTITY_TYPE_IDS: frozenset[int] = frozenset({1, 2})


def is_admin_config_menu(menu: str) -> bool:
    """Indica si la clave de menú pertenece a la sección Configuración."""
    return menu in ADMIN_CONFIG_PAGE_MENUS


def can_access_admin_config_menu(menu: str, identity_type_id: int) -> bool:
    """Valida acceso a páginas de configuración según el rol del usuario."""
    if not is_admin_config_menu(menu):
        return True
    return identity_type_id in LAIM_ADMIN_IDENTITY_TYPE_IDS


def split_markdown_h2_sections(
    markdown: str,
) -> tuple[str, str, list[dict[str, str]]]:
    """Separa el H1, un preámbulo opcional y las secciones ``##``.

    Los ``###`` permanecen dentro del cuerpo de su sección padre.
    """
    page_title = ""
    preamble_lines: list[str] = []
    sections: list[dict[str, str]] = []
    current_title: str | None = None
    current_body: list[str] = []

    def _flush_section() -> None:
        nonlocal current_title, current_body
        if current_title is None:
            return
        sections.append(
            {
                "title": current_title,
                "body": "\n".join(current_body).strip(),
            }
        )
        current_title = None
        current_body = []

    for line in markdown.splitlines():
        if line.startswith("# ") and not line.startswith("## "):
            if not page_title:
                page_title = line[2:].strip()
            continue
        if line.startswith("## ") and not line.startswith("### "):
            _flush_section()
            current_title = line[3:].strip()
            continue
        if current_title is None:
            preamble_lines.append(line)
            continue
        current_body.append(line)

    _flush_section()
    return page_title, "\n".join(preamble_lines).strip(), sections


def load_static_page_markdown(menu: str) -> str:
    """Lee el fichero markdown asociado a una opción del menú."""
    filename = MENU_TO_MARKDOWN_FILE.get(menu)
    if filename is None:
        return f"# Página no encontrada\n\nNo existe contenido para `{menu}`."

    file_path = STATIC_PAGES_DIR / filename
    if not file_path.is_file():
        return (
            f"# Contenido no disponible\n\n"
            f"No se encontró el fichero `{filename}` en `static_pages/`."
        )

    return file_path.read_text(encoding="utf-8")


# rx.markdown monta rehype-raw: un marcador como «<herramienta>» o «<nombre>»
# fuera de código se interpreta como etiqueta HTML desconocida y desaparece
# («¿qué es ?»). Las réplicas de los manuales deben seguir siendo idénticas al
# markdown de laim, así que el escape se hace al pintar, no en los ficheros.
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")
_PLACEHOLDER_RE = re.compile(r"<(/?)([^\W\d][\w-]*)>")
_HTML_TAGS = frozenset(
    {
        "a", "abbr", "b", "blockquote", "br", "code", "dd", "del", "details",
        "div", "dl", "dt", "em", "figcaption", "figure", "h1", "h2", "h3",
        "h4", "h5", "h6", "hr", "i", "img", "ins", "kbd", "li", "mark", "ol",
        "p", "picture", "pre", "s", "samp", "small", "source", "span",
        "strong", "sub", "summary", "sup", "table", "tbody", "td", "tfoot",
        "th", "thead", "tr", "u", "ul", "var", "video",
    }
)


def _escape_placeholders_in_text(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        if match.group(2).lower() in _HTML_TAGS:
            return match.group(0)
        return f"&lt;{match.group(1)}{match.group(2)}&gt;"

    return _PLACEHOLDER_RE.sub(_replace, text)


def _escape_placeholders_in_line(line: str) -> str:
    parts: list[str] = []
    pos = 0
    for span in _CODE_SPAN_RE.finditer(line):
        parts.append(_escape_placeholders_in_text(line[pos : span.start()]))
        parts.append(span.group(0))
        pos = span.end()
    parts.append(_escape_placeholders_in_text(line[pos:]))
    return "".join(parts)


def escape_markdown_placeholders(markdown: str) -> str:
    """Escapa marcadores ``<palabra>`` fuera de código para que se vean.

    Respeta bloques de código cercados, código en línea y etiquetas HTML
    reales (``<br>``, ``<details>``…).
    """
    lines: list[str] = []
    in_fence = False
    for line in markdown.split("\n"):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            lines.append(line)
            continue
        lines.append(line if in_fence else _escape_placeholders_in_line(line))
    return "\n".join(lines)


def load_static_page_for_render(menu: str) -> str:
    """Markdown de la página listo para rx.markdown (marcadores escapados)."""
    return escape_markdown_placeholders(load_static_page_markdown(menu))

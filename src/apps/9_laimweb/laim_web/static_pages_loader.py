"""Carga de contenido markdown desde static_pages/."""

from __future__ import annotations

from pathlib import Path

STATIC_PAGES_DIR = Path(__file__).resolve().parent.parent / "static_pages"

MENU_TO_MARKDOWN_FILE: dict[str, str] = {
    "inicio": "inicio.md",
    "servicios": "servicios.md",
    "documentacion": "documentacion.md",
    "contacto": "contacto.md",
}

STATIC_PAGE_MENUS = frozenset(MENU_TO_MARKDOWN_FILE.keys())


def load_static_page_markdown(menu: str) -> str:
    """Lee el fichero markdown asociado a una opción del menú público."""
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

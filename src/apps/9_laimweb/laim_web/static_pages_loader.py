"""Carga de contenido markdown desde static_pages/."""

from __future__ import annotations

from pathlib import Path

STATIC_PAGES_DIR = Path(__file__).resolve().parent.parent / "static_pages"

PUBLIC_MENU_FILES: dict[str, str] = {
    "inicio": "inicio.md",
    "servicios": "servicios.md",
    "documentacion": "documentacion.md",
    "contacto": "contacto.md",
}

AUTHENTICATED_MENU_FILES: dict[str, str] = {
    "instaladores": "instaladores.md",
    "manuales": "manuales.md",
    "modelos_base": "modelos_base.md",
    "modelos_especializados": "modelos_especializados.md",
    "modelos_personalizados": "modelos_personalizados.md",
    "skills": "skills.md",
    "complementos": "complementos.md",
    "soporte": "soporte.md",
    "faq": "faq.md",
}

MENU_TO_MARKDOWN_FILE: dict[str, str] = {
    **PUBLIC_MENU_FILES,
    **AUTHENTICATED_MENU_FILES,
}

STATIC_PAGE_MENUS = frozenset(MENU_TO_MARKDOWN_FILE.keys())
AUTHENTICATED_PAGE_MENUS = frozenset(AUTHENTICATED_MENU_FILES.keys())


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

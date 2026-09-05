"""Carga de contenido markdown desde static_pages/."""

from __future__ import annotations

from pathlib import Path

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
    "manuales": "manuales.md",
    "modelos_base": "modelos_base.md",
    "modelos_especializados": "modelos_especializados.md",
    "modelos_personalizados": "modelos_personalizados.md",
    "skills": "skills.md",
    "complementos": "complementos.md",
    "soporte": "soporte.md",
    "faq": "faq.md",
}

ADMIN_CONFIG_MENU_FILES: dict[str, str] = {
    "config_general": "config_general.md",
    "config_usuarios": "config_usuarios.md",
    "config_modelos_ia": "config_modelos_ia.md",
    "config_fases_tiers": "config_fases_tiers.md",
    "config_sesiones": "config_sesiones.md",
    "config_share": "config_share.md",
    "config_agentes": "config_agentes.md",
    "config_auditoria": "config_auditoria.md",
}

MENU_TO_MARKDOWN_FILE: dict[str, str] = {
    **PUBLIC_MENU_FILES,
    **AUTHENTICATED_MENU_FILES,
    **ADMIN_CONFIG_MENU_FILES,
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

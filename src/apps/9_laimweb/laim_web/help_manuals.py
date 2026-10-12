"""Catálogo de la réplica web de Ayuda (laim/internal/manuals/spanish).

IDs y textos de botón/pista coinciden con KnownManualIDs y help.* del cliente.
Editor y Temas son herramientas del cliente, no documentos.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HelpManual:
    """Un documento de Ayuda replicado en el portal."""

    laim_id: str
    menu: str
    filename: str
    button_label: str
    hint: str
    action_key: str


HELP_MANUALS: tuple[HelpManual, ...] = (
    HelpManual(
        laim_id="admin",
        menu="manual_admin",
        filename="help_manuals/admin_manual.md",
        button_label="📖 Manual de administrador",
        hint="Instalación, usuarios, modelos, Share/Connect, backups y seguridad.",
        action_key="open_manual_admin",
    ),
    HelpManual(
        laim_id="user",
        menu="manual_user",
        filename="help_manuals/user_manual.md",
        button_label="📗 Manual de usuario",
        hint="Chat, inferencia directa, sesiones y rendimiento.",
        action_key="open_manual_user",
    ),
    HelpManual(
        laim_id="headscale",
        menu="manual_headscale",
        filename="help_manuals/headscale_manual.md",
        button_label="🔒 Red mesh WireGuard (Headscale)",
        hint="Red mesh WireGuard, registro remoto, NAT traversal.",
        action_key="open_manual_headscale",
    ),
    HelpManual(
        laim_id="recommendations",
        menu="manual_recommendations",
        filename="help_manuals/recommendations_manual.md",
        button_label="📋 Recomendaciones",
        hint="Directrices de uso, aviso legal, responsabilidades y asunción de riesgos.",
        action_key="open_manual_recommendations",
    ),
    HelpManual(
        laim_id="context_window",
        menu="manual_context_window",
        filename="help_manuals/context_window_manual.md",
        button_label="💾 Ventana de contexto",
        hint="Límites de contexto, caché KV y compresión automática del historial.",
        action_key="open_manual_context_window",
    ),
    HelpManual(
        laim_id="windows_remote",
        menu="manual_windows_remote",
        filename="help_manuals/windows_remote_manual.md",
        button_label="🖥️ Windows remoto (OpenSSH)",
        hint="Instalar OpenSSH Server y registrar el equipo en laim remote.",
        action_key="open_manual_windows_remote",
    ),
)

HELP_MANUAL_MENU_FILES: dict[str, str] = {
    item.menu: item.filename for item in HELP_MANUALS
}
HELP_MANUAL_PAGE_MENUS = frozenset(HELP_MANUAL_MENU_FILES.keys())
BACK_TO_MANUALES_ACTION = "back_to_manuales"


def menu_for_action(action_key: str) -> str | None:
    """Resuelve open_manual_* al menú de la réplica."""
    for item in HELP_MANUALS:
        if item.action_key == action_key:
            return item.menu
    return None


def is_help_manual_menu(menu: str) -> bool:
    """Indica si el menú es un documento de Ayuda (no el índice)."""
    return menu in HELP_MANUAL_PAGE_MENUS

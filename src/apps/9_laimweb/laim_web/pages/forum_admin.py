"""Panel de administración del foro."""

from __future__ import annotations

import reflex as rx

from laim_web.components.forum_ui import forum_admin_panel
from laim_web.components.forum_extended_ui import forum_admin_extended_panel
from laim_web.components.portal_shell import portal_page


def forum_admin_page():
    """Configuración del foro (solo administradores)."""
    return portal_page(
        rx.vstack(
            forum_admin_panel(),
            rx.divider(margin_y="2em"),
            forum_admin_extended_panel(),
            spacing="4",
            width="100%",
        ),
        title="Config. foro — LAIM",
    )

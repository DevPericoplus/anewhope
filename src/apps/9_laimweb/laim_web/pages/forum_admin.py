"""Panel de administración del foro."""

from __future__ import annotations

from laim_web.components.forum_ui import forum_admin_panel
from laim_web.components.portal_shell import portal_page


def forum_admin_page():
    """Configuración del foro (solo administradores)."""
    return portal_page(forum_admin_panel(), title="Config. foro — LAIM")

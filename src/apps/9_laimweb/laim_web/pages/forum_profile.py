"""Perfil de usuario en el foro LAIM."""

from __future__ import annotations

from laim_web.components.forum_extended_ui import forum_profile_panel
from laim_web.components.portal_shell import portal_page


def forum_profile_page():
    """Configuración de perfil del foro (nombre, firma, avatar)."""
    return portal_page(forum_profile_panel(), title="Perfil foro — LAIM")

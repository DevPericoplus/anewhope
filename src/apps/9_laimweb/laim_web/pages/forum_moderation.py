"""Panel de moderación del foro LAIM."""

from __future__ import annotations

from laim_web.components.forum_extended_ui import forum_moderation_panel
from laim_web.components.portal_shell import portal_page


def forum_moderation_page():
    """Moderación: baneos y logs (solo administradores)."""
    return portal_page(forum_moderation_panel(), title="Moderación foro — LAIM")

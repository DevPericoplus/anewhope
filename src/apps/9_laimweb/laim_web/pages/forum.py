"""Página principal del foro LAIM."""

from __future__ import annotations

from laim_web.components.forum_ui import forum_main_layout
from laim_web.components.portal_shell import portal_page


def forum_page():
    """Foro: categorías, subcategorías, hilos y respuestas."""
    return portal_page(forum_main_layout(), title="Foro LAIM")

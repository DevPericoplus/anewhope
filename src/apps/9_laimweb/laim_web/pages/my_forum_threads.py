"""Página mis hilos del foro."""

from __future__ import annotations

from laim_web.components.forum_ui import forum_my_threads_table
from laim_web.components.portal_shell import portal_page


def my_forum_threads_page():
    """Listado de hilos creados por el usuario."""
    return portal_page(forum_my_threads_table(), title="Mis hilos — Foro LAIM")

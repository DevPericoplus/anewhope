"""Aplicación principal Reflex para LAIM Web."""

import reflex as rx

from laim_web.laim_state import LaimWebState
from laim_web.pages.index import index_page

app = rx.App(
    stylesheets=["/crt.css"],
    theme=rx.theme(
        appearance="dark",
    ),
)

app.add_page(
    index_page,
    route="/",
    title="LAIM — Local AI Management",
    on_load=LaimWebState.on_page_load,
)

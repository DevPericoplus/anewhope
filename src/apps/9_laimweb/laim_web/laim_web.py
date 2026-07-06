"""Aplicación principal Reflex para LAIM Web."""

import reflex as rx

from laim_web.laim_state import LaimWebState
from laim_web.pages.forum import forum_page
from laim_web.pages.forum_admin import forum_admin_page
from laim_web.pages.forum_moderation import forum_moderation_page
from laim_web.pages.forum_profile import forum_profile_page
from laim_web.pages.index import index_page
from laim_web.pages.my_forum_posts import my_forum_posts_page
from laim_web.pages.my_forum_threads import my_forum_threads_page

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

app.add_page(
    forum_page,
    route="/foro",
    title="Foro LAIM",
    on_load=LaimWebState.forum_on_page_load,
)

app.add_page(
    my_forum_threads_page,
    route="/mis-hilos-foro",
    title="Mis hilos — Foro LAIM",
    on_load=LaimWebState.forum_my_threads_on_load,
)

app.add_page(
    my_forum_posts_page,
    route="/mis-respuestas-foro",
    title="Mis respuestas — Foro LAIM",
    on_load=LaimWebState.forum_my_posts_on_load,
)

app.add_page(
    forum_admin_page,
    route="/config-foro",
    title="Config. foro — LAIM",
    on_load=LaimWebState.forum_admin_on_load,
)

app.add_page(
    forum_profile_page,
    route="/foro-perfil",
    title="Perfil foro — LAIM",
    on_load=LaimWebState.forum_profile_on_load,
)

app.add_page(
    forum_moderation_page,
    route="/foro-moderacion",
    title="Moderación foro — LAIM",
    on_load=LaimWebState.forum_mod_on_load,
)

"""Layout compartido del portal LAIM Web (header, sidebar, footer)."""

from __future__ import annotations

import reflex as rx

from laim_web.components.auth_modals import auth_modals
from laim_web.components.crt_theme import (
    COLORS,
    CONTENT_PADDING,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
)
from laim_web.laim_state import LaimWebState

FORUM_NAV = [
    ("/foro", "Foro"),
    ("/mis-hilos-foro", "Mis hilos"),
    ("/mis-respuestas-foro", "Mis respuestas"),
]


def logo() -> rx.Component:
    """Logo LAIM con estilo CRT."""
    return rx.link(
        rx.hstack(
            rx.text(
                "LAIM",
                font_weight="bold",
                font_size="1.6em",
                color=COLORS["title"],
                letter_spacing="0.08em",
            ),
            rx.text(".app", font_size="1.2em", color=COLORS["muted"]),
            spacing="1",
            align_items="baseline",
        ),
        href="/",
        _hover={"text_decoration": "none"},
    )


def header_auth_actions() -> rx.Component:
    """Acciones de autenticación en cabecera."""
    return rx.hstack(
        rx.button(
            "Iniciar sesión",
            on_click=LaimWebState.open_login_modal,
            class_name="crt-btn crt-btn-inline",
        ),
        rx.button(
            "Crear cuenta",
            on_click=LaimWebState.open_register_modal,
            class_name="crt-btn crt-btn-inline",
        ),
        spacing="2",
        align_items="center",
        class_name="crt-header-actions",
    )


def portal_header() -> rx.Component:
    """Cabecera del portal."""
    return rx.hstack(
        logo(),
        rx.box(flex_grow="1"),
        rx.cond(
            LaimWebState.is_logged_in,
            rx.hstack(
                rx.text(
                    LaimWebState.user_name,
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_BODY,
                ),
                rx.button(
                    "Desconectar",
                    on_click=LaimWebState.handle_logout,
                    class_name="crt-btn crt-btn-danger crt-btn-inline",
                    width="auto",
                    padding_x="1em",
                ),
                spacing="3",
                align_items="center",
            ),
            header_auth_actions(),
        ),
        width="100%",
        padding="0.75em 1.5em",
        background=COLORS["panel_bg"],
        border_bottom=f"1px solid {COLORS['border']}",
        align_items="center",
        min_height="3.2em",
    )


def _forum_nav_link(href: str, label: str) -> rx.Component:
    """Enlace de navegación del foro."""
    return rx.link(
        rx.text(label, font_size="0.9em", color=COLORS["text"]),
        href=href,
        width="100%",
        padding="0.55em 0.75em",
        _hover={"background": "rgba(0, 80, 0, 0.35)", "text_decoration": "none"},
    )


def forum_nav_section() -> rx.Component:
    """Sección de navegación del foro (solo autenticados)."""
    return rx.cond(
        LaimWebState.is_logged_in,
        rx.vstack(
            rx.divider(color=COLORS["border"], margin_y="0.5em"),
            rx.text("Foro", class_name="crt-title", font_size="1em"),
            *[_forum_nav_link(href, label) for href, label in FORUM_NAV],
            rx.cond(
                LaimWebState.is_laim_admin,
                _forum_nav_link("/config-foro", "Config. foro"),
                rx.fragment(),
            ),
            spacing="1",
            width="100%",
        ),
        rx.fragment(),
    )


def portal_sidebar() -> rx.Component:
    """Sidebar con enlaces al portal y al foro."""
    return rx.vstack(
        rx.cond(
            LaimWebState.is_logged_in,
            rx.vstack(
                rx.text("Sesión activa", class_name="crt-title", font_size="1em"),
                rx.text(
                    LaimWebState.user_name,
                    color=COLORS["text"],
                    font_size=FONT_SIZE_BODY,
                ),
                spacing="1",
                width="100%",
            ),
            rx.vstack(
                rx.text("Acceso al portal", class_name="crt-title", font_size="1em"),
                rx.text(
                    "Inicie sesión para acceder al foro y al panel de gestión.",
                    class_name="crt-muted",
                    font_size=FONT_SIZE_SMALL,
                ),
                rx.link(
                    rx.button("Ir al inicio", class_name="crt-btn", width="100%"),
                    href="/",
                ),
                spacing="2",
                width="100%",
            ),
        ),
        rx.divider(color=COLORS["border"], margin_y="0.75em"),
        rx.link(
            rx.text("← Portal principal", font_size="0.9em", color=COLORS["accent"]),
            href="/",
            padding="0.55em 0.75em",
        ),
        forum_nav_section(),
        spacing="2",
        padding="1em",
        width="100%",
        height="100%",
        overflow_y="auto",
    )


def portal_footer() -> rx.Component:
    """Pie del portal."""
    return rx.hstack(
        rx.text("LAIM v0.1.0", color=COLORS["muted"], font_size=FONT_SIZE_SMALL),
        rx.box(flex_grow="1"),
        rx.text(
            "© 2025 LAIM — Local Artificial Intelligence Management",
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
        ),
        width="100%",
        padding="0.6em 1.5em",
        background=COLORS["panel_bg"],
        border_top=f"1px solid {COLORS['border']}",
        align_items="center",
        min_height="2.5em",
    )


def portal_page(content: rx.Component, *, title: str = "LAIM Foro") -> rx.Component:
    """Layout estándar para páginas del foro."""
    return rx.box(
        rx.vstack(
            portal_header(),
            rx.hstack(
                rx.box(
                    portal_sidebar(),
                    width="25%",
                    min_width="220px",
                    max_width="320px",
                    background=COLORS["panel_bg"],
                    border_right=f"1px solid {COLORS['border']}",
                    height="100%",
                ),
                rx.box(
                    content,
                    flex="1",
                    min_width="0",
                    height="100%",
                    overflow_y="auto",
                    padding=CONTENT_PADDING,
                ),
                width="100%",
                spacing="0",
                flex="1",
                align_items="stretch",
                overflow="hidden",
            ),
            portal_footer(),
            width="100%",
            min_height="100vh",
            spacing="0",
        ),
        auth_modals(),
        class_name="crt-shell",
        width="100%",
    )

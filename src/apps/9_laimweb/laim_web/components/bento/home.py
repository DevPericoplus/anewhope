"""Home Inicio: cabecera + Modo clásico / gráfico."""

from __future__ import annotations

import reflex as rx

from laim_web.components.bento.grid import bento_grid
from laim_web.components.bento.section_modal import inicio_section_modal
from laim_web.components.crt_theme import COLORS, CONTENT_PADDING
from laim_web.components.inicio_accordion import inicio_accordion_sections
from laim_web.laim_state import LaimWebState


def inicio_home_panel() -> rx.Component:
    """Página Bienvenido a LAIM: red 3D por defecto, acordeón en clásico."""
    return rx.vstack(
        rx.hstack(
            rx.heading(
                LaimWebState.inicio_page_title,
                size="7",
                color=COLORS["title"],
                class_name="crt-title",
            ),
            rx.spacer(),
            rx.cond(
                LaimWebState.inicio_view == "classic",
                rx.button(
                    "Modo gráfico",
                    on_click=lambda: LaimWebState.set_inicio_view("graphic"),
                    class_name="crt-btn crt-btn-inline",
                ),
                rx.button(
                    "Modo clásico",
                    on_click=lambda: LaimWebState.set_inicio_view("classic"),
                    class_name="crt-btn crt-btn-inline",
                ),
            ),
            width="100%",
            align_items="center",
            flex_wrap="wrap",
            spacing="3",
        ),
        rx.cond(
            LaimWebState.inicio_view == "classic",
            inicio_accordion_sections(),
            bento_grid(),
        ),
        inicio_section_modal(),
        rx.script(src="/crt/bento_neural.js?v=3d2"),
        spacing="4",
        width="100%",
        align_items="stretch",
        padding=CONTENT_PADDING,
        class_name="crt-inicio-home",
    )

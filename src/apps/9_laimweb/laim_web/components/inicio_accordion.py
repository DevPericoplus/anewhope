"""Acordeón de secciones para la página de inicio."""

from __future__ import annotations

import reflex as rx

from laim_web.components.crt_theme import COLORS, CONTENT_PADDING
from laim_web.components.markdown_viewer import crt_markdown_body
from laim_web.laim_state import LaimWebState

HINT_INICIO_ACCORDION = (
    "Pulsa una sección para abrirla. Puedes tener varias abiertas a la vez."
)
LABEL_EXPAND_ALL = "Desplegar todas"
LABEL_COLLAPSE_ALL = "Contraer todas"


def _inicio_section_item(section: dict) -> rx.Component:
    """Una sección contraíble de Inicio."""
    is_open = LaimWebState.inicio_open_titles.contains(section["title"])
    return rx.vstack(
        rx.box(
            rx.hstack(
                rx.heading(
                    section["title"],
                    size="5",
                    color=COLORS["title"],
                    class_name="crt-title",
                ),
                rx.cond(
                    is_open,
                    rx.icon("chevron-down", size=20, color=COLORS["title"]),
                    rx.icon("chevron-right", size=20, color=COLORS["title"]),
                ),
                justify="between",
                align_items="center",
                width="100%",
            ),
            class_name="crt-accordion-trigger",
            on_click=lambda: LaimWebState.toggle_inicio_section(section["title"]),
            cursor="pointer",
            width="100%",
        ),
        rx.cond(
            is_open,
            rx.box(
                crt_markdown_body(section["body"]),
                class_name="crt-accordion-body",
                width="100%",
            ),
        ),
        spacing="0",
        width="100%",
    )


def inicio_accordion_panel() -> rx.Component:
    """Página Bienvenido a LAIM con secciones desplegables."""
    return rx.vstack(
        rx.heading(
            LaimWebState.inicio_page_title,
            size="7",
            color=COLORS["title"],
            class_name="crt-title",
        ),
        rx.text(HINT_INICIO_ACCORDION, class_name="crt-muted"),
        rx.hstack(
            rx.button(
                LABEL_EXPAND_ALL,
                on_click=LaimWebState.expand_inicio_sections,
                class_name="crt-btn",
                size="2",
            ),
            rx.button(
                LABEL_COLLAPSE_ALL,
                on_click=LaimWebState.collapse_inicio_sections,
                class_name="crt-btn",
                size="2",
            ),
            spacing="3",
            flex_wrap="wrap",
            width="100%",
        ),
        rx.foreach(LaimWebState.inicio_sections, _inicio_section_item),
        spacing="3",
        width="100%",
        align_items="stretch",
        padding=CONTENT_PADDING,
    )

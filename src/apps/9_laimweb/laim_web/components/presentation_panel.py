"""Panel de presentación: imagen hero + markdown con estilo CRT."""

from __future__ import annotations

import reflex as rx

from laim_web.components.markdown_viewer import crt_markdown_viewer
from laim_web.laim_state import LaimWebState

COLORS = {
    "border": "rgba(0, 200, 0, 0.35)",
    "muted": "rgba(200, 255, 200, 0.65)",
    "title": "#9dff9d",
}


def presentation_hero_viewer() -> rx.Component:
    """Visor superior con la imagen de diálogo humano–IA."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(
                    "HUMAN_INPUT ↔ AI_CORE",
                    font_size="0.75em",
                    color=COLORS["muted"],
                    letter_spacing="0.12em",
                    font_family="monospace",
                ),
                rx.box(flex_grow="1"),
                rx.text(
                    "NEURAL_FUSION",
                    font_size="0.75em",
                    color=COLORS["muted"],
                    letter_spacing="0.12em",
                    font_family="monospace",
                ),
                width="100%",
                align_items="center",
            ),
            rx.box(
                rx.image(
                    src=LaimWebState.presentacion_hero_url,
                    alt="Fusión entre inteligencia humana e inteligencia artificial",
                    width="100%",
                    height="auto",
                    max_height="420px",
                    object_fit="contain",
                    loading="lazy",
                ),
                class_name="crt-presentacion-hero-frame",
                width="100%",
            ),
            spacing="2",
            width="100%",
        ),
        class_name="crt-presentacion-hero",
        width="100%",
        margin_bottom="1.25em",
    )


def presentation_content_panel() -> rx.Component:
    """Contenido de presentación: hero + markdown."""
    return rx.vstack(
        presentation_hero_viewer(),
        rx.box(
            crt_markdown_viewer(LaimWebState.static_page_content),
            class_name="crt-presentacion-markdown",
            width="100%",
        ),
        spacing="0",
        width="100%",
        align_items="stretch",
    )

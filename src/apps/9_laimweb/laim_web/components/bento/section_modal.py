"""Modal CRT con el markdown de una sección y Volver."""

from __future__ import annotations

import reflex as rx

from laim_web.components.bento.glyphs import glyph_match
from laim_web.components.markdown_viewer import crt_markdown_body
from laim_web.laim_state import LaimWebState


def _modal_cta(item: dict) -> rx.Component:
    return rx.button(
        item["label"],
        on_click=lambda: LaimWebState.inicio_modal_go_menu(item["key"]),
        class_name="crt-btn crt-btn-inline",
    )


def inicio_section_modal() -> rx.Component:
    """Contenido de la sección en overlay; Volver reanuda el pulso."""
    return rx.cond(
        LaimWebState.inicio_modal_open,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        glyph_match(LaimWebState.inicio_modal_glyph),
                        rx.heading(
                            LaimWebState.inicio_modal_title,
                            size="6",
                            class_name="crt-title",
                        ),
                        spacing="3",
                        align_items="center",
                        width="100%",
                    ),
                    rx.box(
                        crt_markdown_body(LaimWebState.inicio_modal_body),
                        class_name="crt-bento-modal-body",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.foreach(LaimWebState.inicio_modal_ctas, _modal_cta),
                        spacing="2",
                        flex_wrap="wrap",
                        width="100%",
                    ),
                    rx.button(
                        "Volver",
                        on_click=LaimWebState.close_inicio_section_modal,
                        class_name="crt-btn",
                    ),
                    spacing="4",
                    width="100%",
                    align_items="stretch",
                ),
                class_name="crt-panel crt-modal-panel crt-bento-modal-panel",
                role="dialog",
                aria_modal="true",
                aria_label=LaimWebState.inicio_modal_title,
                on_click=rx.stop_propagation,
            ),
            class_name="crt-modal-overlay crt-bento-modal-overlay",
            on_click=LaimWebState.close_inicio_section_modal,
        ),
    )

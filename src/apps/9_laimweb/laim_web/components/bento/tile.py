"""Baldosa Bento CRT: glifo + título corto, clic abre el modal."""

from __future__ import annotations

import reflex as rx

from laim_web.components.bento.glyphs import glyph_match
from laim_web.laim_state import LaimWebState


def bento_tile(section: dict) -> rx.Component:
    """Nodo de la rejilla — botón físico con el glifo de la sección."""
    return rx.el.button(
        glyph_match(section["glyph"]),
        rx.el.span(section["short"], class_name="crt-bento-label"),
        type="button",
        class_name=section["tile_class"],
        custom_attrs={
            "data-bento-glyph": section["glyph"],
            "data-bento-title": section["title"],
            "data-span": section["span"],
            "data-pause": section["pause_ms"],
        },
        aria_label=section["title"],
        on_click=lambda: LaimWebState.open_inicio_section_modal(section["title"]),
    )

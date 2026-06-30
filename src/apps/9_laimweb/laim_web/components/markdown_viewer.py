"""Visor de markdown con estilo terminal CRT."""

from __future__ import annotations

import reflex as rx

COLORS = {
    "text": "#e8ffe8",
    "title": "#9dff9d",
    "muted": "rgba(200, 255, 200, 0.65)",
    "accent": "#7dff7d",
    "border": "rgba(0, 200, 0, 0.35)",
    "code_bg": "rgba(0, 40, 0, 0.65)",
}

CONTENT_PADDING = "1.5em"

CRT_MARKDOWN_COMPONENT_MAP = {
    "h1": lambda text: rx.heading(
        text,
        size="8",
        color=COLORS["title"],
        margin_bottom="0.5em",
        font_weight="700",
        letter_spacing="0.06em",
    ),
    "h2": lambda text: rx.heading(
        text,
        size="6",
        color=COLORS["title"],
        margin_top="1em",
        margin_bottom="0.5em",
        font_weight="700",
    ),
    "h3": lambda text: rx.heading(
        text,
        size="5",
        color=COLORS["accent"],
        margin_top="0.75em",
        margin_bottom="0.4em",
        font_weight="700",
    ),
    "p": lambda text: rx.text(
        text,
        color=COLORS["muted"],
        font_size="0.95em",
        line_height="1.6",
        margin_y="0.65em",
    ),
    "strong": lambda text: rx.text(
        text,
        as_="strong",
        color=COLORS["text"],
        font_weight="700",
    ),
    "em": lambda text: rx.text(
        text,
        as_="em",
        color=COLORS["text"],
        font_style="italic",
    ),
    "code": lambda text: rx.code(
        text,
        color=COLORS["accent"],
        background=COLORS["code_bg"],
        padding="0.1em 0.35em",
        border_radius="3px",
        font_size="0.9em",
    ),
    "pre": lambda text, **props: rx.code_block(
        text,
        **props,
        theme=rx.code_block.themes.a11y_dark,
        margin_y="1em",
        width="100%",
    ),
    "a": lambda text, **props: rx.link(
        text,
        **props,
        color=COLORS["accent"],
        text_decoration="underline",
        _hover={"color": COLORS["title"]},
    ),
    "li": lambda text: rx.text(
        text,
        as_="li",
        color=COLORS["muted"],
        font_size="0.95em",
        line_height="1.5",
        margin_y="0.25em",
    ),
    "blockquote": lambda text: rx.box(
        rx.text(text, color=COLORS["muted"], font_style="italic", line_height="1.6"),
        border_left=f"3px solid {COLORS['border']}",
        padding_left="1em",
        margin_y="1em",
    ),
    "hr": lambda _: rx.divider(color=COLORS["border"], margin_y="1.25em"),
}


def crt_markdown_viewer(content: str) -> rx.Component:
    """Renderiza markdown con la paleta y tipografía CRT de LAIM Web."""
    return rx.box(
        rx.markdown(
            content,
            component_map=CRT_MARKDOWN_COMPONENT_MAP,
        ),
        class_name="crt-markdown",
        width="100%",
        padding=CONTENT_PADDING,
    )

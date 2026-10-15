"""Visor de markdown con estilo terminal CRT."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import reflex as rx

from laim_web.components.crt_theme import CONTENT_PADDING

_SHARED_CRT_THEME = (
    Path(__file__).resolve().parents[4]
    / "2_shared_application"
    / "reflex_shared"
    / "crt"
    / "crt_theme.py"
)
_spec = importlib.util.spec_from_file_location("shared_crt_theme_md", _SHARED_CRT_THEME)
if _spec is None or _spec.loader is None:
    raise ImportError(f"No se pudo cargar CRT theme compartido: {_SHARED_CRT_THEME}")
_shared_theme = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared_theme)

_BASE_MARKDOWN_MAP: dict[str, Any] = _shared_theme.get_markdown_component_map("green")

def _inline_code(text: str = "", **props: Any) -> rx.Component:
    """El chip `In progress` del catálogo de Servicios no es código."""
    label = text if isinstance(text, str) else str(text)
    if label.strip() == "In progress":
        return rx.el.span("In progress", class_name="crt-badge-wip")
    factory = _BASE_MARKDOWN_MAP.get("code")
    if callable(factory):
        return factory(text, **props)
    return rx.code(text, **props)


CRT_MARKDOWN_COMPONENT_MAP: dict[str, Any] = {
    **_BASE_MARKDOWN_MAP,
    "code": _inline_code,
    "hr": lambda *_a, **_k: rx.el.hr(class_name="crt-md-section-rule"),
    "codeblock": lambda text, **props: rx.code_block(
        text,
        theme=rx.code_block.themes.a11y_dark,
        margin_y="1em",
        width="100%",
        wrap_long_lines=True,
        **props,
    ),
}


def crt_markdown_body(content: str) -> rx.Component:
    """Markdown CRT sin padding exterior (para acordeones y paneles)."""
    return rx.box(
        rx.markdown(
            content,
            component_map=CRT_MARKDOWN_COMPONENT_MAP,
        ),
        class_name="crt-markdown",
        width="100%",
    )


def crt_markdown_viewer(content: str) -> rx.Component:
    """Renderiza markdown con la paleta y tipografía CRT de LAIM Web."""
    return rx.box(
        crt_markdown_body(content),
        width="100%",
        padding=CONTENT_PADDING,
    )

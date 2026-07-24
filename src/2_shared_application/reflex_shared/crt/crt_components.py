"""Componentes Reflex reutilizables con estilo CRT."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import reflex as rx

from .crt_theme import CrtVariant, FONT_FAMILY, get_crt_colors, get_select_style


def crt_label(text: str, **kwargs: Any) -> rx.Component:
    """Etiqueta de formulario CRT."""
    return rx.text(text, class_name="crt-label", **kwargs)


def crt_muted(text: str, **kwargs: Any) -> rx.Component:
    """Texto secundario CRT."""
    return rx.text(text, class_name="crt-muted", **kwargs)


def crt_heading_page(text: str, **kwargs: Any) -> rx.Component:
    """Título de página CRT."""
    return rx.heading(text, size="8", class_name="crt-title", **kwargs)


def crt_heading_panel(text: str, **kwargs: Any) -> rx.Component:
    """Título de panel o sección CRT."""
    return rx.heading(text, size="6", class_name="crt-title", **kwargs)


def crt_input(**kwargs: Any) -> rx.Component:
    """Campo de entrada CRT."""
    return rx.input(class_name="crt-input", **kwargs)


def crt_select(*args: Any, variant: CrtVariant = "green", **kwargs: Any) -> rx.Component:
    """Selector CRT con estilo oscuro."""
    style = kwargs.pop("style", {})
    merged_style = {**get_select_style(variant), **style}
    return rx.select(*args, class_name="crt-input", style=merged_style, **kwargs)


def crt_button(
    *children: Any,
    on_click: Callable[..., Any] | None = None,
    variant: str = "default",
    class_name: str = "",
    **kwargs: Any,
) -> rx.Component:
    """Botón CRT con variantes predefinidas."""
    classes = ["crt-btn"]
    if variant == "inline":
        classes.append("crt-btn-inline")
    elif variant == "danger":
        classes.append("crt-btn-danger")
    elif variant == "link":
        classes.append("crt-btn-link")
    elif variant == "icon":
        classes.append("crt-btn-icon")
    elif variant == "cross":
        classes.append("crt-btn-inline crt-btn-cross")
    if class_name:
        classes.append(class_name)
    return rx.button(
        *children,
        on_click=on_click,
        class_name=" ".join(classes),
        **kwargs,
    )


def crt_cross_portal_button(
    label: str,
    on_click: Callable[..., Any],
    target_variant: CrtVariant,
) -> rx.Component:
    """Botón de navegación entre portales (color del destino)."""
    colors = get_crt_colors(target_variant)
    return rx.button(
        label,
        on_click=on_click,
        class_name="crt-btn crt-btn-inline crt-btn-cross",
        style={
            "borderColor": colors["accent_strong"],
            "color": colors["btn_text"],
            "fontWeight": "bold",
            "fontSize": "1.05em",
        },
        _hover={"background": colors["btn_hover"], "boxShadow": f"0 0 8px {colors['btn_hover_glow']}"},
    )


def crt_app_style() -> dict[str, str]:
    """Estilo global para rx.App."""
    return {"font_family": FONT_FAMILY}

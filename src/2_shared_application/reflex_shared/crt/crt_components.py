"""Componentes Reflex reutilizables con estilo CRT."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import reflex as rx

_CRT_THEME_MODULE = "reflex_shared_crt_theme"


def _load_crt_theme():
    """Carga crt_theme (compatible con importlib desde portal_crt)."""
    if _CRT_THEME_MODULE in sys.modules:
        return sys.modules[_CRT_THEME_MODULE]
    theme_path = Path(__file__).resolve().parent / "crt_theme.py"
    spec = importlib.util.spec_from_file_location(_CRT_THEME_MODULE, theme_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar módulo CRT: {theme_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_CRT_THEME_MODULE] = module
    spec.loader.exec_module(module)
    return module


_crt_theme = _load_crt_theme()
CrtVariant = _crt_theme.CrtVariant
FONT_FAMILY = _crt_theme.FONT_FAMILY
TEXT_ON_ACCENT = _crt_theme.TEXT_ON_ACCENT
get_crt_colors = _crt_theme.get_crt_colors
get_select_style = _crt_theme.get_select_style
get_markdown_component_map = _crt_theme.get_markdown_component_map
CONTENT_PADDING = _crt_theme.CONTENT_PADDING


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
    elif variant == "block":
        classes.append("crt-btn-block")
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
    """Botón de navegación entre portales (paleta del destino: verde o ámbar)."""
    colors = get_crt_colors(target_variant)
    portal_class = f"crt-btn-cross-portal crt-btn-cross-portal--{target_variant}"
    return rx.button(
        label,
        on_click=on_click,
        class_name=f"crt-btn crt-btn-inline {portal_class}",
        style={
            "borderColor": colors["accent_strong"],
            "background": colors["btn_bg"],
            "color": colors["btn_text"],
            "fontWeight": "bold",
            "fontSize": "1.05em",
        },
        _hover={
            "background": colors["btn_hover"],
            "borderColor": colors["accent_strong"],
            "boxShadow": f"0 0 8px {colors['btn_hover_glow']}",
        },
    )


def crt_app_style() -> dict[str, str]:
    """Estilo global para rx.App."""
    return {"font_family": FONT_FAMILY}


def crt_markdown_viewer(
    content: str,
    *,
    variant: CrtVariant = "green",
    component_map: dict[str, Any] | None = None,
    class_name: str = "crt-markdown",
    padding: str | None = None,
    **box_kwargs: Any,
) -> rx.Component:
    """Renderiza markdown CRT ocupando todo el ancho del contenedor padre."""
    markdown_map = component_map or get_markdown_component_map(variant)
    box_props: dict[str, Any] = {
        "class_name": class_name,
        "width": "100%",
        **box_kwargs,
    }
    if padding is not None:
        box_props["padding"] = padding
    return rx.box(
        rx.markdown(content, component_map=markdown_map),
        **box_props,
    )

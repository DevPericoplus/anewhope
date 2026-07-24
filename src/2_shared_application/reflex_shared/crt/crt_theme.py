"""Paleta CRT, tokens de portal y helpers de estilo compartidos."""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx

CrtVariant = Literal["green", "amber"]

GREEN_THEME: dict[str, str] = {
    "bg": "black",
    "radial": "rgba(0, 150, 0, 0.75)",
    "text": "#e8ffe8",
    "text_glow": "#c8c8c8",
    "title": "#9dff9d",
    "accent": "#7dff7d",
    "accent_strong": "#00b400",
    "btn_text": "#d6ffd6",
    "muted": "rgba(200, 255, 200, 0.65)",
    "panel_bg": "rgba(0, 20, 0, 0.55)",
    "border": "rgba(0, 200, 0, 0.35)",
    "border_strong": "rgba(0, 180, 0, 0.45)",
    "input_bg": "rgba(0, 30, 0, 0.8)",
    "btn_bg": "rgba(0, 40, 0, 0.65)",
    "btn_hover": "rgba(0, 80, 0, 0.75)",
    "btn_hover_glow": "rgba(0, 200, 0, 0.35)",
    "panel_glow": "rgba(0, 180, 0, 0.25)",
    "success": "#9dff9d",
    "error": "#ff8a8a",
    "danger": "rgba(255, 80, 80, 0.55)",
    "danger_border": "rgba(255, 80, 80, 0.55)",
    "danger_text": "#ffbdbd",
    "selection": "#0080ff",
    "menu_active_bg": "rgba(0, 180, 0, 0.3)",
    "menu_hover_bg": "rgba(0, 80, 0, 0.35)",
    "cross_accent": "#ff8c00",
    "cross_accent_hover": "#ff7000",
    "chart_stroke": "#5cff5c",
    "code_bg": "rgba(0, 40, 0, 0.65)",
}

AMBER_THEME: dict[str, str] = {
    "bg": "black",
    "radial": "rgba(180, 90, 0, 0.65)",
    "text": "#ffe8c8",
    "text_glow": "rgba(255, 200, 120, 0.55)",
    "title": "#ffb000",
    "accent": "#ffc966",
    "accent_strong": "#ff8c00",
    "btn_text": "#ffd59a",
    "muted": "rgba(255, 220, 180, 0.65)",
    "panel_bg": "rgba(40, 18, 0, 0.55)",
    "border": "rgba(255, 140, 0, 0.35)",
    "border_strong": "rgba(255, 120, 0, 0.45)",
    "input_bg": "rgba(50, 25, 0, 0.8)",
    "btn_bg": "rgba(60, 30, 0, 0.65)",
    "btn_hover": "rgba(90, 45, 0, 0.75)",
    "btn_hover_glow": "rgba(255, 140, 0, 0.35)",
    "panel_glow": "rgba(255, 120, 0, 0.25)",
    "success": "#ffc966",
    "error": "#ff8a8a",
    "danger": "rgba(255, 80, 80, 0.55)",
    "danger_border": "rgba(255, 80, 80, 0.55)",
    "danger_text": "#ffbdbd",
    "selection": "#cc6600",
    "menu_active_bg": "rgba(255, 140, 0, 0.3)",
    "menu_hover_bg": "rgba(120, 60, 0, 0.35)",
    "cross_accent": "#22c55e",
    "cross_accent_hover": "#16a34a",
    "chart_stroke": "#ffb000",
    "code_bg": "rgba(60, 30, 0, 0.65)",
}

CRTStylesheets: dict[CrtVariant, list[str]] = {
    "green": ["/crt/crt_base.css", "/crt/crt_theme_green.css"],
    "amber": ["/crt/crt_base.css", "/crt/crt_theme_amber.css"],
}

CRT_SHELL_CLASS: dict[CrtVariant, str] = {
    "green": "crt-shell crt-theme-green",
    "amber": "crt-shell crt-theme-amber",
}

FONT_FAMILY = "Inconsolata, ui-monospace, monospace"
FONT_SIZE_TITLE = "1.4em"
FONT_SIZE_BODY = "0.95em"
FONT_SIZE_SMALL = "0.85em"
CONTENT_PADDING = "1.5em"


def get_crt_colors(variant: CrtVariant = "green") -> dict[str, str]:
    """Retorna la paleta CRT para la variante indicada."""
    if variant == "amber":
        return dict(AMBER_THEME)
    return dict(GREEN_THEME)


def get_portal_colors(variant: CrtVariant = "green") -> dict[str, str]:
    """Mapea la paleta CRT a las claves COLORS usadas en frontend/backoffice."""
    colors = get_crt_colors(variant)
    return {
        "background": colors["bg"],
        "card": colors["panel_bg"],
        "foreground": colors["text"],
        "primary": colors["title"],
        "secondary": colors["panel_bg"],
        "border": colors["border"],
        "input": colors["input_bg"],
        "muted_foreground": colors["muted"],
        "accent": colors["accent_strong"],
        "muted": colors["muted"],
        "title": colors["title"],
        "text": colors["text"],
        "panel_bg": colors["panel_bg"],
        "btn_text": colors["btn_text"],
        "success": colors["success"],
        "error": colors["error"],
        "cross_accent": colors["cross_accent"],
        "cross_accent_hover": colors["cross_accent_hover"],
        "danger": colors.get("danger", colors["danger_border"]),
    }


def get_select_style(variant: CrtVariant = "green") -> dict[str, str]:
    """Estilo inline estándar para selectores en tema CRT."""
    colors = get_crt_colors(variant)
    return {
        "backgroundColor": colors["input_bg"],
        "color": colors["text"],
        "borderColor": colors["border"],
    }


def get_markdown_component_map(
    variant: CrtVariant = "green",
    *,
    body_font_size: str = "1.15em",
    h1_size: str = "7",
    h2_size: str = "6",
    h3_size: str = "5",
) -> dict[str, Any]:
    """Component map CRT para rx.markdown."""
    colors = get_crt_colors(variant)

    def _heading(text: str, size: str, color: str) -> rx.Component:
        return rx.heading(
            text,
            size=size,
            color=color,
            letter_spacing="0.06em",
            text_transform="uppercase",
            margin_bottom="0.5em",
        )

    return {
        "h1": lambda text: _heading(text, h1_size, colors["title"]),
        "h2": lambda text: _heading(text, h2_size, colors["title"]),
        "h3": lambda text: _heading(text, h3_size, colors["accent"]),
        "p": lambda text: rx.text(
            text,
            color=colors["muted"],
            font_size=body_font_size,
            line_height="1.6",
        ),
        "li": lambda text: rx.text(
            text,
            color=colors["muted"],
            font_size=body_font_size,
            line_height="1.6",
        ),
        "strong": lambda text: rx.text(text, color=colors["text"], font_weight="bold"),
        "code": lambda text: rx.code(
            text,
            color=colors["accent"],
            background_color=colors["code_bg"],
            padding="0.15em 0.35em",
            border_radius="3px",
        ),
        "a": lambda text: rx.link(
            text,
            color=colors["accent"],
            text_decoration="underline",
        ),
    }


def get_active_menu_style(variant: CrtVariant = "green") -> dict[str, str]:
    """Estilo inline para ítem de menú lateral activo."""
    colors = get_crt_colors(variant)
    return {
        "background": colors["menu_active_bg"],
        "borderLeft": f"3px solid {colors['accent_strong']}",
        "color": colors["title"],
        "padding": "0.45rem 0.55rem",
        "cursor": "pointer",
    }


def get_menu_hover_style(variant: CrtVariant = "green") -> dict[str, str]:
    """Estilo inline para hover de menú lateral."""
    colors = get_crt_colors(variant)
    return {
        "background": colors["menu_hover_bg"],
        "padding": "0.45rem 0.55rem",
        "cursor": "pointer",
    }

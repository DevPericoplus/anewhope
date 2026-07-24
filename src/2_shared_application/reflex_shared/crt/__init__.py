"""Sistema de diseño CRT retro-moderno compartido entre portales Reflex."""

from .crt_theme import (
    AMBER_THEME,
    CRTStylesheets,
    GREEN_THEME,
    get_crt_colors,
    get_markdown_component_map,
    get_portal_colors,
    get_select_style,
)
from .crt_components import (
    crt_button,
    crt_heading_page,
    crt_heading_panel,
    crt_input,
    crt_label,
    crt_muted,
    crt_select,
)

__all__ = [
    "AMBER_THEME",
    "CRTStylesheets",
    "GREEN_THEME",
    "crt_button",
    "crt_heading_page",
    "crt_heading_panel",
    "crt_input",
    "crt_label",
    "crt_muted",
    "crt_select",
    "get_crt_colors",
    "get_markdown_component_map",
    "get_portal_colors",
    "get_select_style",
]

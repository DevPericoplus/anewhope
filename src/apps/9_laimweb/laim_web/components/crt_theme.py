"""Paleta y constantes visuales CRT — reexportación desde capa compartida."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_shared_crt = (
    Path(__file__).resolve().parents[4]
    / "2_shared_application"
    / "reflex_shared"
    / "crt"
    / "crt_theme.py"
)
_spec = importlib.util.spec_from_file_location("shared_crt_theme", _shared_crt)
if _spec is None or _spec.loader is None:
    raise ImportError(f"No se pudo cargar CRT theme compartido: {_shared_crt}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

COLORS = _module.get_crt_colors("green")
FONT_SIZE_TITLE = _module.FONT_SIZE_TITLE
FONT_SIZE_BODY = _module.FONT_SIZE_BODY
FONT_SIZE_SMALL = _module.FONT_SIZE_SMALL
CONTENT_PADDING = _module.CONTENT_PADDING
SELECT_STYLE = _module.get_select_style("green")
FORUM_PROFILE_PANEL_STYLE = _module.get_portal_colors("green")
FORUM_PROFILE_AVATAR_GRID_STYLE = {
    "display": "flex",
    "flexWrap": "wrap",
    "alignItems": "flex-start",
    "gap": "0.75rem",
    "width": "100%",
    "marginTop": "0.75rem",
    "marginBottom": "2rem",
    "minHeight": "9.5rem",
}
FORUM_PROFILE_AVATAR_TILE_STYLE = {
    "display": "flex",
    "flexDirection": "column",
    "alignItems": "center",
    "justifyContent": "flex-start",
    "boxSizing": "border-box",
    "width": "5.75rem",
    "maxWidth": "5.75rem",
    "flexShrink": "0",
    "padding": "0.55rem 0.35rem 0.45rem",
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "4px",
    "background": COLORS["panel_bg"],
    "cursor": "pointer",
}
FORUM_PROFILE_AVATAR_SECTION_STYLE = {
    "display": "block",
    "width": "100%",
    "marginBottom": "1.5rem",
    "paddingBottom": "0.5rem",
    "position": "relative",
    "zIndex": "1",
}
FORUM_PROFILE_UPLOAD_SECTION_STYLE = {
    "display": "block",
    "width": "100%",
    "marginTop": "0.5rem",
    "paddingTop": "1.25rem",
    "borderTop": f"1px solid {COLORS['border']}",
    "clear": "both",
    "position": "relative",
    "zIndex": "2",
}
FORUM_PROFILE_UPLOAD_ROW_STYLE = {
    "display": "flex",
    "flexWrap": "wrap",
    "alignItems": "center",
    "gap": "0.75rem",
    "width": "100%",
}
FORUM_PROFILE_UPLOAD_BTN_STYLE = {
    "flex": "0 0 auto",
    "width": "auto",
    "minWidth": "11rem",
    "marginBottom": "0",
    "textAlign": "center",
}

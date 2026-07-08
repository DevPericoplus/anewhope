"""Paleta y constantes visuales CRT compartidas en LAIM Web."""

from __future__ import annotations

COLORS = {
    "bg": "black",
    "panel_bg": "rgba(0, 20, 0, 0.55)",
    "border": "rgba(0, 200, 0, 0.35)",
    "text": "#e8ffe8",
    "title": "#9dff9d",
    "muted": "rgba(200, 255, 200, 0.65)",
    "accent": "#00b400",
    "input_bg": "rgba(0, 30, 0, 0.8)",
    "btn_bg": "rgba(0, 40, 0, 0.65)",
    "btn_hover": "rgba(0, 80, 0, 0.75)",
    "danger": "rgba(255, 80, 80, 0.55)",
}

FONT_SIZE_TITLE = "1.4em"
FONT_SIZE_BODY = "0.95em"
FONT_SIZE_SMALL = "0.85em"
CONTENT_PADDING = "1.5em"

# Estilo estándar para selectores en tema oscuro CRT
SELECT_STYLE = {
    "backgroundColor": COLORS["input_bg"],
    "color": COLORS["text"],
    "borderColor": COLORS["border"],
}

FORUM_PROFILE_PANEL_STYLE = {
    "width": "100%",
    "maxWidth": "100%",
    "gap": "1rem",
}

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

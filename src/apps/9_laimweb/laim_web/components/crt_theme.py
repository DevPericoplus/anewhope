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

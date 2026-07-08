"""Visor legible de mensajes del foro (markdown en blanco, sin efectos CRT)."""

from __future__ import annotations

import re
from typing import Any

import reflex as rx

# Paleta de lectura cómoda (texto claro sobre panel oscuro neutro)
READABLE_COLORS = {
    "text": "#f5f5f5",
    "heading": "#ffffff",
    "muted": "#d4d4d4",
    "accent": "#e5e5e5",
    "link": "#bae6fd",
    "code_bg": "rgba(255, 255, 255, 0.08)",
    "quote_border": "rgba(255, 255, 255, 0.35)",
    "divider": "rgba(255, 255, 255, 0.18)",
}

EMOJI_SHORTCUTS: dict[str, str] = {
    ":smile:": "😊",
    ":grin:": "😁",
    ":wink:": "😉",
    ":heart:": "❤️",
    ":thumbsup:": "👍",
    ":thumbsdown:": "👎",
    ":fire:": "🔥",
    ":star:": "⭐",
    ":check:": "✅",
    ":cross:": "❌",
    ":warning:": "⚠️",
    ":idea:": "💡",
    ":rocket:": "🚀",
    ":clap:": "👏",
    ":think:": "🤔",
    ":wave:": "👋",
    ":ok:": "👌",
    ":100:": "💯",
}

_EMOJI_PATTERN = re.compile(
    "|".join(re.escape(key) for key in sorted(EMOJI_SHORTCUTS, key=len, reverse=True))
)


def forum_message_preview_text(raw: str, max_length: int = 140) -> str:
    """Genera un extracto plano para listas (sin sintaxis markdown)."""
    enriched = enrich_forum_message_markdown(raw)
    if not enriched:
        return ""

    text = enriched
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def enrich_forum_message_row(row: dict[str, Any]) -> dict[str, Any]:
    """Añade display_md y display_preview a un ítem con cuerpo de mensaje."""
    enriched = dict(row)
    raw_md = str(enriched.get("cuerpo_md") or enriched.get("display_md") or "")
    enriched["display_md"] = enrich_forum_message_markdown(raw_md)
    enriched["display_preview"] = forum_message_preview_text(raw_md)
    return enriched


def enrich_forum_message_markdown(raw: str) -> str:
    """Normaliza y enriquece el cuerpo de un mensaje para lectura en markdown.

    - Convierte shortcodes de emoticonos (:smile:, :heart:, …) a Unicode.
    - Unifica saltos de línea.
    - Si el texto no parece markdown estructurado, mejora párrafos y viñetas simples.
    """
    text = (raw or "").replace("\r\n", "\n").strip()
    if not text:
        return ""

    def _replace_shortcut(match: re.Match[str]) -> str:
        return EMOJI_SHORTCUTS.get(match.group(0), match.group(0))

    text = _EMOJI_PATTERN.sub(_replace_shortcut, text)
    text = _normalize_plain_text_to_markdown(text)
    return text


def _normalize_plain_text_to_markdown(text: str) -> str:
    """Convierte texto plano en markdown legible cuando no hay estructura explícita."""
    if _looks_like_markdown(text):
        return text

    lines = text.split("\n")
    blocks: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        blocks.append(" ".join(paragraph))
        paragraph.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue
        if stripped.startswith(("- ", "* ", "• ")):
            flush_paragraph()
            item = stripped.lstrip("-*• ").strip()
            blocks.append(f"- {item}")
            continue
        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            blocks.append(stripped)
            continue
        paragraph.append(stripped)

    flush_paragraph()
    return "\n\n".join(blocks) if blocks else text


def _looks_like_markdown(text: str) -> bool:
    """Detecta si el texto ya incluye sintaxis markdown relevante."""
    patterns = (
        r"^#{1,6}\s",
        r"^\*\*[^*]+\*\*",
        r"^>\s",
        r"^```",
        r"^\|.+\|",
        r"!\[",
        r"\[[^\]]+\]\([^)]+\)",
        r"^-\s+\S",
        r"^\d+\.\s+\S",
    )
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in patterns:
            if re.match(pattern, stripped):
                return True
    return False


def _readable_paragraph(text) -> rx.Component:
    """Párrafo con tipografía de lectura prolongada."""
    return rx.text(
        text,
        color=READABLE_COLORS["text"],
        font_size="1.02em",
        line_height="1.75",
        margin_y="0.55em",
        font_weight="400",
        style={"textShadow": "none"},
    )


FORUM_READABLE_MARKDOWN_COMPONENT_MAP = {
    "h1": lambda text: rx.heading(
        text,
        size="6",
        color=READABLE_COLORS["heading"],
        margin_bottom="0.45em",
        margin_top="0.25em",
        font_weight="700",
        style={"textShadow": "none"},
    ),
    "h2": lambda text: rx.heading(
        text,
        size="5",
        color=READABLE_COLORS["heading"],
        margin_top="0.85em",
        margin_bottom="0.4em",
        font_weight="700",
        style={"textShadow": "none"},
    ),
    "h3": lambda text: rx.heading(
        text,
        size="4",
        color=READABLE_COLORS["heading"],
        margin_top="0.65em",
        margin_bottom="0.35em",
        font_weight="600",
        style={"textShadow": "none"},
    ),
    "p": lambda text: _readable_paragraph(text),
    "li": lambda text: rx.text(
        text,
        color=READABLE_COLORS["text"],
        font_size="1.02em",
        line_height="1.7",
        style={"textShadow": "none"},
    ),
    "code": lambda text: rx.code(
        text,
        color=READABLE_COLORS["accent"],
        background=READABLE_COLORS["code_bg"],
        padding="0.12em 0.4em",
        border_radius="4px",
        font_size="0.92em",
        style={"textShadow": "none"},
    ),
    "codeblock": lambda text, **props: rx.code_block(
        text,
        theme=rx.code_block.themes.a11y_dark,
        margin_y="0.85em",
        width="100%",
        wrap_long_lines=True,
        **props,
    ),
    "a": lambda text, **props: rx.link(
        text,
        **props,
        color=READABLE_COLORS["link"],
        text_decoration="underline",
        _hover={"color": READABLE_COLORS["heading"]},
        style={"textShadow": "none"},
    ),
    "blockquote": lambda text: rx.box(
        rx.text(
            text,
            color=READABLE_COLORS["muted"],
            font_style="italic",
            line_height="1.75",
            font_size="1.02em",
            style={"textShadow": "none"},
        ),
        border_left=f"3px solid {READABLE_COLORS['quote_border']}",
        padding_left="1em",
        margin_y="0.85em",
        padding_y="0.25em",
    ),
    "hr": lambda _: rx.divider(color=READABLE_COLORS["divider"], margin_y="1em"),
}


def forum_readable_markdown_viewer(content: str) -> rx.Component:
    """Renderiza markdown del foro con máxima legibilidad (sin efectos CRT)."""
    return rx.box(
        rx.markdown(
            content,
            component_map=FORUM_READABLE_MARKDOWN_COMPONENT_MAP,
        ),
        class_name="forum-message-viewer",
        width="100%",
    )


def forum_message_body(
    content: str,
    *,
    class_name: str = "forum-post-body",
) -> rx.Component:
    """Contenedor estándar para el cuerpo legible de un mensaje del foro."""
    return rx.box(
        forum_readable_markdown_viewer(content),
        class_name=class_name,
        width="100%",
    )

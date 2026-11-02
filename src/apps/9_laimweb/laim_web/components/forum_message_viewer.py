"""Visor legible de mensajes del foro (markdown en blanco, sin efectos CRT)."""

from __future__ import annotations

import re
from typing import Any

import reflex as rx

from laim_web.components.crt_theme import markdown_link

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

# Carátula pública de YouTube (hqdefault existe para cualquier id; maxres no).
# Como mucho cuatro por mensaje: el resto del texto sigue siendo el enlace.
_MAX_YOUTUBE_COVERS = 4
_VIDEO_ID = r"[A-Za-z0-9_-]{11}"
_YOUTUBE_URL_RE = re.compile(
    rf"""(?xi)
    (?P<url>
      https?://
      (?:
        (?:www\.|m\.|music\.)?youtube\.com/
        (?:
          watch\?(?:[^&\s<>()\[\]'"]*&)*v=(?P<id_watch>{_VIDEO_ID})(?![A-Za-z0-9_-])
          | shorts/(?P<id_shorts>{_VIDEO_ID})(?![A-Za-z0-9_-])
          | embed/(?P<id_embed>{_VIDEO_ID})(?![A-Za-z0-9_-])
          | live/(?P<id_live>{_VIDEO_ID})(?![A-Za-z0-9_-])
          | v/(?P<id_v>{_VIDEO_ID})(?![A-Za-z0-9_-])
        )
        | youtu\.be/(?P<id_short>{_VIDEO_ID})(?![A-Za-z0-9_-])
      )
      [^\s<>()\[\]'".,;!?]*
    )
    """
)
_YOUTUBE_ID_GROUPS = (
    "id_watch",
    "id_shorts",
    "id_embed",
    "id_live",
    "id_v",
    "id_short",
)
_YOUTUBE_COVER_MD_RE = re.compile(
    rf"\[!\[[^\]]*\]\(https://img\.youtube\.com/vi/{_VIDEO_ID}/hqdefault\.jpg\)\]"
    r"\([^)\s]+\)"
)


def forum_message_preview_text(raw: str, max_length: int = 140) -> str:
    """Genera un extracto plano para listas (sin sintaxis markdown)."""
    enriched = enrich_forum_message_markdown(raw)
    if not enriched:
        return ""

    text = enriched
    text = _YOUTUBE_COVER_MD_RE.sub(" ", text)
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
    - Bajo cada enlace de YouTube (youtube.com / youtu.be) pone la carátula
      estática, enlazada al mismo vídeo. El listado usa el extracto y no la lleva.
    """
    text = (raw or "").replace("\r\n", "\n").strip()
    if not text:
        return ""

    def _replace_shortcut(match: re.Match[str]) -> str:
        return EMOJI_SHORTCUTS.get(match.group(0), match.group(0))

    text = _EMOJI_PATTERN.sub(_replace_shortcut, text)
    text = _normalize_plain_text_to_markdown(text)
    return _attach_youtube_covers(text)


def _attach_youtube_covers(text: str) -> str:
    """Inserta la carátula bajo la primera aparición de cada vídeo."""
    masked = _mask_code_regions(text)
    inserts: list[tuple[int, str]] = []
    seen: set[str] = set()
    for match in _YOUTUBE_URL_RE.finditer(masked):
        video_id = _youtube_video_id(match)
        if not video_id or video_id in seen:
            continue
        thumb = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        if thumb in text:
            seen.add(video_id)
            continue
        if len(seen) >= _MAX_YOUTUBE_COVERS:
            break
        seen.add(video_id)
        end = match.end()
        if end < len(text) and text[end] in ")>":
            end += 1
        while end < len(text) and text[end] in ".,;!?":
            end += 1
        if end < len(text) and text[end] == " ":
            end += 1
        inserts.append((end, _youtube_cover_markdown(match.group("url"), thumb)))
    if not inserts:
        return text
    parts: list[str] = []
    cursor = 0
    for end, cover in inserts:
        parts.append(text[cursor:end])
        parts.append(cover)
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


def _youtube_video_id(match: re.Match[str]) -> str:
    for name in _YOUTUBE_ID_GROUPS:
        value = match.group(name)
        if value:
            return value
    return ""


def _youtube_cover_markdown(page_url: str, thumb: str) -> str:
    """Imagen estática cuyo enlace es el mismo vídeo, en markdown."""
    return f"\n\n[![Carátula del vídeo]({thumb})]({page_url})\n\n"


def _mask_code_regions(text: str) -> str:
    """Tapa bloques e inline code para no tratar un ejemplo como un vídeo."""

    def _blank(match: re.Match[str]) -> str:
        return " " * (match.end() - match.start())

    masked = re.sub(r"```.*?```", _blank, text, flags=re.DOTALL)
    masked = re.sub(r"```.*\Z", _blank, masked, flags=re.DOTALL)
    return re.sub(r"`[^`\n]*`", _blank, masked)


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
    # <li> y <blockquote> pueden contener bloques (<p>, <ul>, <pre>): se
    # pintan como <li>/<div>, nunca como <p> (rx.text), para que el DOM sea
    # válido y React no avise de «<p> cannot contain a nested …».
    "li": lambda text: rx.list_item(
        rx.box(
            text,
            color=READABLE_COLORS["text"],
            font_size="1.02em",
            line_height="1.7",
            style={"textShadow": "none"},
        ),
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
    "a": lambda text, **props: markdown_link(
        text,
        color=READABLE_COLORS["link"],
        _hover={"color": READABLE_COLORS["heading"]},
        style={"textShadow": "none"},
        **props,
    ),
    "blockquote": lambda text: rx.box(
        rx.box(
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

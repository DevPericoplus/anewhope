"""Tests del visor legible de mensajes del foro."""

from __future__ import annotations

from laim_web.components.forum_message_viewer import (
    enrich_forum_message_markdown,
    enrich_forum_message_row,
    forum_message_preview_text,
)


def test_enrich_converts_emoji_shortcuts() -> None:
    """Convierte shortcodes comunes a emoticonos Unicode."""
    raw = "Gracias por la ayuda :smile: :heart:"
    result = enrich_forum_message_markdown(raw)
    assert "😊" in result
    assert "❤️" in result
    assert ":smile:" not in result


def test_enrich_plain_text_to_paragraphs() -> None:
    """Texto plano multilínea se convierte en párrafos markdown."""
    raw = "Primera línea del mensaje.\n\nSegunda idea en otro párrafo."
    result = enrich_forum_message_markdown(raw)
    assert "Primera línea del mensaje." in result
    assert "Segunda idea" in result


def test_enrich_plain_bullet_lines() -> None:
    """Líneas con viñeta simple se normalizan a listas markdown."""
    raw = "- Punto uno\n- Punto dos"
    result = enrich_forum_message_markdown(raw)
    assert result.count("- Punto") == 2


def test_enrich_preserves_existing_markdown() -> None:
    """No altera markdown ya estructurado."""
    raw = "## Título\n\n**Negrita** y [enlace](https://example.com)"
    result = enrich_forum_message_markdown(raw)
    assert result == raw


def test_enrich_empty_string() -> None:
    """Cadena vacía retorna vacío."""
    assert enrich_forum_message_markdown("") == ""
    assert enrich_forum_message_markdown("   ") == ""


def test_preview_strips_markdown_and_truncates() -> None:
    """El extracto elimina markdown y acorta texto largo."""
    raw = "## Título\n\nTexto con **negrita** y :smile: al final del mensaje."
    preview = forum_message_preview_text(raw, max_length=40)
    assert "##" not in preview
    assert "**" not in preview
    assert "😊" in preview
    assert len(preview) <= 40


def test_enrich_message_row_adds_display_fields() -> None:
    """Enriquece filas con display_md y display_preview."""
    row = enrich_forum_message_row({"id": 1, "cuerpo_md": "Hola :heart:"})
    assert "❤️" in row["display_md"]
    assert "❤️" in row["display_preview"]
    assert row["id"] == 1

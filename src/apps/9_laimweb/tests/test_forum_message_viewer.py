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


def _cover(video_id: str, page_url: str) -> str:
    thumb = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    return f"[![Carátula del vídeo]({thumb})]({page_url})"


def test_enrich_youtu_be_adds_cover_under_the_link() -> None:
    """Un enlace corto se queda y, debajo, la carátula abre ese mismo vídeo."""
    raw = (
        "Sin tener en cuenta el truco utilizado en la presentacion, "
        "su propuesta no deja de ser algo que se puede tener en cuenta.\n"
        "https://youtu.be/181asZ4FJFg"
    )
    result = enrich_forum_message_markdown(raw)
    assert "https://youtu.be/181asZ4FJFg" in result
    assert result.index("https://youtu.be/181asZ4FJFg") < result.index(_cover(
        "181asZ4FJFg", "https://youtu.be/181asZ4FJFg"
    ))
    assert result.count("hqdefault.jpg") == 1


def test_enrich_youtube_watch_url_adds_cover() -> None:
    """watch?v= usa el id del vídeo, no el resto de la query."""
    raw = (
        "Entenderlo es necesario para conocer como se ha conseguido "
        "comunicarse con la tecnologia de la IA.\n"
        "https://www.youtube.com/watch?v=JV-KVcFWkmk"
    )
    result = enrich_forum_message_markdown(raw)
    assert _cover("JV-KVcFWkmk", "https://www.youtube.com/watch?v=JV-KVcFWkmk") in result
    preview = forum_message_preview_text(raw, max_length=400)
    assert "Entenderlo es necesario" in preview
    assert "img.youtube.com" not in preview
    assert "Carátula" not in preview
    assert "hqdefault" not in preview


def test_enrich_youtube_shapes_share_one_cover_per_video() -> None:
    """Shorts, embed, live, móvil y el mismo id repetido no duplican la carátula."""
    raw = "\n".join([
        "https://m.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/live/abcdefghijk",
        "https://www.youtube.com/embed/qwertyuiopa",
        "https://music.youtube.com/watch?list=PLxxxx&v=0123456789a&t=12",
        "https://youtu.be/zzzzzzzzzz1",
    ])
    result = enrich_forum_message_markdown(raw)
    assert result.count("hqdefault.jpg") == 4
    assert "zzzzzzzzzz1" in result
    assert "img.youtube.com/vi/zzzzzzzzzz1/" not in result
    assert _cover(
        "0123456789a",
        "https://music.youtube.com/watch?list=PLxxxx&v=0123456789a&t=12",
    ) in result


def test_enrich_ignores_playlist_without_video_and_code_samples() -> None:
    """Una lista sin id, y un ejemplo dentro de código, no llevan carátula."""
    raw = (
        "Lista: https://www.youtube.com/playlist?list=PLabcdefghij\n\n"
        "```\nhttps://youtu.be/181asZ4FJFg\n```\n\n"
        "El ejemplo `https://www.youtube.com/watch?v=JV-KVcFWkmk` no es un enlace."
    )
    result = enrich_forum_message_markdown(raw)
    assert "hqdefault.jpg" not in result
    assert "https://youtu.be/181asZ4FJFg" in result


def test_enrich_markdown_link_keeps_the_label_and_adds_cover() -> None:
    """El texto del enlace no se sustituye; la carátula va detrás del paréntesis."""
    raw = "Mira [este vídeo](https://youtu.be/181asZ4FJFg) cuando puedas."
    result = enrich_forum_message_markdown(raw)
    assert "[este vídeo](https://youtu.be/181asZ4FJFg)" in result
    assert _cover("181asZ4FJFg", "https://youtu.be/181asZ4FJFg") in result
    assert result.index("[este vídeo](https://youtu.be/181asZ4FJFg)") < result.index(
        "hqdefault.jpg"
    )


def test_enrich_youtube_cover_is_idempotent() -> None:
    """Volver a preparar el mensaje no apila otra carátula."""
    raw = "https://youtu.be/181asZ4FJFg"
    once = enrich_forum_message_markdown(raw)
    twice = enrich_forum_message_markdown(once)
    assert twice.strip() == once.strip()
    assert once.count("hqdefault.jpg") == 1


def test_youtube_cover_css_sizes_the_linked_image() -> None:
    """La carátula usa el enlace que ya abre otra pestaña, sin subrayado."""
    from pathlib import Path

    css = (
        Path(__file__).resolve().parents[1] / "assets" / "crt" / "crt_base.css"
    ).read_text(encoding="utf-8")
    assert ".forum-message-viewer a:has(img)" in css
    assert "text-decoration: none !important" in css
    assert "min(100%, 480px)" in css

"""Los marcadores «<palabra>» de las páginas estáticas se ven al pintarlas.

QA: el manual de usuario mostraba «¿qué es ?» en vez de «¿qué es
<herramienta>?» porque rx.markdown monta rehype-raw y trata el marcador como
una etiqueta HTML desconocida.
"""

from __future__ import annotations

from laim_web.help_manuals import HELP_MANUALS
from laim_web.static_pages_loader import (
    STATIC_PAGE_MENUS,
    escape_markdown_placeholders,
    load_static_page_for_render,
    load_static_page_markdown,
)


def test_placeholder_outside_code_is_escaped() -> None:
    raw = "Pregunta *«¿qué es <herramienta>?»*"
    assert escape_markdown_placeholders(raw) == "Pregunta *«¿qué es &lt;herramienta&gt;?»*"


def test_accented_and_closing_placeholders_are_escaped() -> None:
    assert escape_markdown_placeholders("<versión> </nombre>") == (
        "&lt;versión&gt; &lt;/nombre&gt;"
    )


def test_inline_code_and_fences_are_left_alone() -> None:
    raw = (
        "Usa `ollama pull <nombre>` o ``<slug>.exe``\n"
        "```\nplugins/<nombre>/\n```\n"
        "~~~\n<tool_root>\n~~~\n"
        "y luego <nombre>"
    )
    escaped = escape_markdown_placeholders(raw)
    assert "`ollama pull <nombre>`" in escaped
    assert "``<slug>.exe``" in escaped
    assert "plugins/<nombre>/" in escaped
    assert "\n<tool_root>\n" in escaped
    assert escaped.endswith("y luego &lt;nombre&gt;")


def test_real_html_tags_and_autolinks_are_left_alone() -> None:
    raw = "a<br>b <details><summary>Más</summary></details> <https://laim.app>"
    assert escape_markdown_placeholders(raw) == raw


def test_user_manual_tool_question_keeps_its_placeholder() -> None:
    manual = next(item for item in HELP_MANUALS if item.laim_id == "user")
    rendered = load_static_page_for_render(manual.menu)
    assert "«¿qué es &lt;herramienta&gt;?»" in rendered
    assert "«¿qué es <herramienta>?»" not in rendered
    # El fichero sigue siendo la réplica literal del manual de laim.
    assert "«¿qué es <herramienta>?»" in load_static_page_markdown(manual.menu)


def test_no_static_page_renders_a_bare_placeholder() -> None:
    import re

    bare = re.compile(r"<(/?)([^\W\d][\w-]*)>")
    for menu in sorted(STATIC_PAGE_MENUS):
        rendered = load_static_page_for_render(menu)
        in_fence = False
        for line in rendered.split("\n"):
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            outside_code = re.sub(r"(`+)(.+?)\1", "", line)
            for match in bare.finditer(outside_code):
                assert match.group(2).lower() in {
                    "br", "details", "summary", "div", "span", "img", "sub", "sup", "kbd",
                }, f"{menu}: marcador sin escapar {match.group(0)!r} en {line!r}"

"""El component map CRT de rx.markdown no anida bloques dentro de un <p>.

react-markdown pasa a <li> y <blockquote> hijos de bloque (<p>, <ul>, <pre>).
Si su envoltorio es rx.text (un <p>), React avisa en consola de
«<p> cannot contain a nested <p>/<ul>/<pre>» y el DOM queda inválido.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

rx = pytest.importorskip("reflex")

_CRT_THEME = (
    Path(__file__).resolve().parents[1] / "reflex_shared" / "crt" / "crt_theme.py"
)
_spec = importlib.util.spec_from_file_location("test_shared_crt_theme", _CRT_THEME)
assert _spec is not None and _spec.loader is not None
_crt_theme = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_crt_theme)

# Etiquetas markdown cuyos hijos pueden ser bloques.
_BLOCK_CONTAINER_TAGS = ("li", "blockquote")
_PARAGRAPH_MARKERS = ("RadixThemesText", 'as:"p"', 'jsx("p"')


def _rendered_tag(component_map: dict, tag: str) -> str:
    rendered = rx.markdown("x", component_map=component_map).format_component_map()
    return str(rendered[tag])


@pytest.mark.parametrize("variant", ["green", "amber"])
@pytest.mark.parametrize("tag", _BLOCK_CONTAINER_TAGS)
def test_block_containers_never_render_a_paragraph(variant: str, tag: str) -> None:
    js = _rendered_tag(_crt_theme.get_markdown_component_map(variant), tag)
    for marker in _PARAGRAPH_MARKERS:
        assert marker not in js, f"{tag} ({variant}) envuelve hijos en un <p>: {js}"


@pytest.mark.parametrize("variant", ["green", "amber"])
def test_crt_look_is_kept_on_list_items_and_quotes(variant: str) -> None:
    colors = _crt_theme.get_crt_colors(variant)
    component_map = _crt_theme.get_markdown_component_map(variant, body_font_size="0.9em")
    li_js = _rendered_tag(component_map, "li")
    assert 'jsx("li"' in li_js
    assert colors["muted"] in li_js
    assert '"0.9em"' in li_js
    assert '"1.6"' in li_js
    assert '"0.35em"' in li_js
    quote_js = _rendered_tag(component_map, "blockquote")
    assert colors["muted"] in quote_js
    assert '"italic"' in quote_js
    assert f"3px solid {colors['border']}" in quote_js


def test_paragraphs_are_still_crt_text() -> None:
    js = _rendered_tag(_crt_theme.get_markdown_component_map("green"), "p")
    assert 'as:"p"' in js
    assert _crt_theme.GREEN_THEME["muted"] in js


@pytest.mark.parametrize("variant", ["green", "amber"])
@pytest.mark.parametrize("tag", ["th", "td"])
def test_table_cells_drop_the_is_header_prop(variant: str, tag: str) -> None:
    """react-markdown 8 pasa isHeader a <th>/<td>; no debe llegar al DOM."""
    js = _rendered_tag(_crt_theme.get_markdown_component_map(variant), tag)
    assert "isHeader" in js.split("=>", 1)[0], f"{tag} no saca isHeader de props: {js}"
    assert "...props" in js

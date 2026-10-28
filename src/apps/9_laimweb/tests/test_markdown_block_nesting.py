"""Los visores markdown de LAIM Web no anidan bloques dentro de un <p>.

QA: la consola de React avisaba de «<p>/<pre>/<ul> cannot be a descendant
of <p>» en manuales y mensajes del foro: <li> y <blockquote> envolvían sus
hijos (párrafos, listas anidadas, bloques de código) en rx.text (<p>).
"""

from __future__ import annotations

import pytest
import reflex as rx

from laim_web.components.forum_message_viewer import FORUM_READABLE_MARKDOWN_COMPONENT_MAP
from laim_web.components.markdown_viewer import CRT_MARKDOWN_COMPONENT_MAP

_PARAGRAPH_MARKERS = ("RadixThemesText", 'as:"p"', 'jsx("p"')


def _rendered(component_map: dict) -> dict:
    return rx.markdown("x", component_map=component_map).format_component_map()


@pytest.mark.parametrize(
    "component_map",
    [CRT_MARKDOWN_COMPONENT_MAP, FORUM_READABLE_MARKDOWN_COMPONENT_MAP],
    ids=["crt", "forum"],
)
@pytest.mark.parametrize("tag", ["li", "blockquote"])
def test_block_containers_never_render_a_paragraph(component_map: dict, tag: str) -> None:
    js = str(_rendered(component_map)[tag])
    for marker in _PARAGRAPH_MARKERS:
        assert marker not in js, f"{tag} envuelve hijos de bloque en un <p>: {js}"


def test_forum_list_items_are_real_list_items() -> None:
    """Antes el foro pintaba cada <li> como un <p> suelto dentro del <ul>."""
    js = str(_rendered(FORUM_READABLE_MARKDOWN_COMPONENT_MAP)["li"])
    assert 'jsx("li"' in js
    assert "#f5f5f5" in js

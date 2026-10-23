"""Glifos CRT — trazo currentColor, viewBox 48.

El jerbo es la excepción: silueta rellena del logo oficial, para que
el icono de Inicio y el logotipo sean el mismo animal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    import reflex as rx

# Paths de un solo trazo (o pocos, mismo peso). El jerbo va relleno.
GLYPH_PATHS: Final[dict[str, tuple[str, ...]]] = {
    "core": (
        "M24 7.5a16.5 16.5 0 1 0 .01 0z",
        "M24 16.5a7.5 7.5 0 1 0 .01 0z",
        "M24 7.5v5.2",
        "M24 35.3v5.2",
        "M7.5 24h5.2",
        "M35.3 24h5.2",
    ),
    "knot": (
        "M14 30 C14 16 26 12 30 20 C34 28 26 34 20 30 C15 27 18 20 26 18 C34 16 36 26 30 32",
    ),
    "mesh": (
        "M16 15.5a3.2 3.2 0 1 0 .01 0z",
        "M32 15.5a3.2 3.2 0 1 0 .01 0z",
        "M24 32.5a3.2 3.2 0 1 0 .01 0z",
        "M18.6 17.6 L29.4 17.6",
        "M18.2 18.4 L22.6 29.6",
        "M29.8 18.4 L25.4 29.6",
    ),
    "soul": (
        "M24 9.5a14.5 14.5 0 1 0 .01 0z",
        "M24 24.5a2.4 2.4 0 1 0 .01 0z",
    ),
    "bars": (
        "M10 38 H38",
        "M14 38 V28",
        "M24 38 V20",
        "M34 38 V11",
    ),
    "hardware": (
        "M9.5 11.5 H38.5 V30.5 H9.5 Z",
        "M18 35.5 H30",
        "M24 30.5 V35.5",
    ),
    "steps": (
        "M8.5 34.5 H18.5 V26.5 H28.5 V18.5 H39.5",
        "M18.5 34.5 V26.5",
        "M28.5 26.5 V18.5",
    ),
    "gerbil": (
        "M 4.0 32.3 L 4.7 31.8 L 4.7 31.3 L 6.2 30.6 L 8.1 31.1 "
        "L 11.7 29.4 L 17.2 25.6 L 20.5 22.7 L 21.7 18.9 L 25.1 15.5 "
        "L 28.0 14.5 L 30.8 14.5 L 33.5 15.3 L 33.9 14.5 L 33.0 13.3 "
        "L 32.7 11.7 L 33.7 10.2 L 35.6 10.5 L 36.6 11.2 L 38.0 13.3 "
        "L 40.9 14.3 L 44.0 17.9 L 44.0 18.4 L 42.6 19.6 L 40.6 20.0 "
        "L 39.0 20.0 L 37.1 22.7 L 36.6 22.2 L 36.1 22.7 L 36.8 23.6 "
        "L 38.0 24.1 L 38.3 24.6 L 38.3 25.8 L 37.8 26.3 L 36.8 24.6 "
        "L 34.4 24.4 L 33.7 23.9 L 33.2 22.9 L 33.0 23.9 L 33.5 24.6 "
        "L 32.3 25.3 L 32.3 23.9 L 31.3 21.7 L 29.4 20.3 L 28.7 20.5 "
        "L 29.9 21.2 L 31.1 22.7 L 31.3 25.8 L 30.6 27.2 L 29.6 28.2 "
        "L 26.5 29.6 L 25.3 30.8 L 25.1 32.3 L 28.4 36.6 L 31.1 36.8 "
        "L 31.8 37.8 L 28.0 37.8 L 27.5 37.3 L 25.3 34.2 L 23.2 31.8 "
        "L 23.2 31.1 L 24.8 29.4 L 25.3 28.0 L 24.8 27.2 L 22.7 26.3 "
        "L 21.0 24.1 L 15.3 28.2 L 12.1 30.1 L 8.3 31.8 L 7.6 32.7 "
        "L 6.6 33.2 L 5.0 33.0 L 4.7 32.5 L 4.0 32.5 Z",
    ),
    "idea": (
        "M24 7.5 A10.2 10.2 0 0 1 31.8 24.8 C31.8 28.6 29 31 24 31 C19 31 16.2 28.6 16.2 24.8 A10.2 10.2 0 0 1 24 7.5",
        "M20 35.5 H28",
        "M21.2 39 H26.8",
    ),
}

STROKE = "1.7"
FILLED_GLYPHS: Final[frozenset[str]] = frozenset({"gerbil"})


def _path_markup(glyph_id: str, d: str) -> str:
    if glyph_id in FILLED_GLYPHS:
        return f'<path d="{d}" fill="currentColor" stroke="none"/>'
    return (
        f'<path d="{d}" fill="none" stroke="currentColor" '
        f'stroke-width="{STROKE}" stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
    )


def glyph_ids() -> tuple[str, ...]:
    """Ids estables del set CRT (9)."""
    return tuple(GLYPH_PATHS.keys())


def glyph_svg_markup(glyph_id: str, extra_class: str = "") -> str:
    """SVG inline listo para rx.html / sprite."""
    paths = GLYPH_PATHS.get(glyph_id, GLYPH_PATHS["core"])
    parts = [_path_markup(glyph_id, d) for d in paths]
    cls = "crt-bento-glyph" + (f" {extra_class}" if extra_class else "")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" '
        f'class="{cls}" aria-hidden="true">{"".join(parts)}</svg>'
    )


def glyph_sprite_markup() -> str:
    """Sprite con un <symbol> por glifo (assets y escenario)."""
    symbols: list[str] = []
    for glyph_id, paths in GLYPH_PATHS.items():
        inner = "".join(_path_markup(glyph_id, d) for d in paths)
        symbols.append(
            f'<symbol id="glyph-{glyph_id}" viewBox="0 0 48 48">{inner}</symbol>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" '
        'aria-hidden="true" class="crt-bento-sprite">'
        f"{''.join(symbols)}</svg>"
    )


def glyph_el(glyph_id: str):
    """SVG inline (paths fijos) — no depende de rx.html ni de un sprite externo."""
    import reflex as rx

    paths = GLYPH_PATHS.get(glyph_id, GLYPH_PATHS["core"])
    if glyph_id in FILLED_GLYPHS:
        children = [
            rx.el.path(d=d, fill="currentColor", stroke="none") for d in paths
        ]
    else:
        children = [
            rx.el.path(
                d=d,
                fill="none",
                stroke="currentColor",
                stroke_width="1.7",
                stroke_linecap="round",
                stroke_linejoin="round",
            )
            for d in paths
        ]
    return rx.el.svg(
        *children,
        view_box="0 0 48 48",
        class_name="crt-bento-glyph",
        custom_attrs={"aria-hidden": "true"},
    )


def glyph_match(glyph_var):
    """Elige el glifo CRT a partir de un Var de Reflex."""
    import reflex as rx

    return rx.match(
        glyph_var,
        ("core", glyph_el("core")),
        ("knot", glyph_el("knot")),
        ("mesh", glyph_el("mesh")),
        ("soul", glyph_el("soul")),
        ("bars", glyph_el("bars")),
        ("hardware", glyph_el("hardware")),
        ("steps", glyph_el("steps")),
        ("gerbil", glyph_el("gerbil")),
        ("idea", glyph_el("idea")),
        glyph_el("core"),
    )

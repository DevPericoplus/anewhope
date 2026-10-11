"""Glifos CRT de trazo — una línea, currentColor, viewBox 48."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    import reflex as rx

# Paths de un solo trazo (o pocos, mismo peso). Sin relleno.
GLYPH_PATHS: Final[dict[str, tuple[str, ...]]] = {
    "core": (
        "M24 7.5a16.5 16.5 0 1 0 .01 0z",
        "M24 16.5a7.5 7.5 0 1 0 .01 0z",
        "M24 7.5v5.2",
        "M24 35.3v5.2",
        "M7.5 24h5.2",
        "M35.3 24h5.2",
    ),
    "shield": (
        "M24 6.5 L39 13.2 V24.5 C39 33.8 31.6 39.6 24 43.2 C16.4 39.6 9 33.8 9 24.5 V13.2 Z",
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
    "tools": (
        "M14 34 L26.5 21.5",
        "M26.5 21.5 L33 19.2 L35.4 21.6 L33.1 28.2 L20.5 36.2",
        "M16.5 15.5 L21 20",
        "M31.5 30.5 L36 35",
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
        "M17.5 20 Q14 9 20.5 10 Q22.2 14.5 23.5 19",
        "M30.5 20 Q34 9 27.5 10 Q25.8 14.5 24.5 19",
        "M14.5 23 Q24 38 33.5 23 Q35 33 24 35.5 Q13 33 14.5 23",
        "M33.2 29 Q40 31 38.5 39",
    ),
    "idea": (
        "M24 7.5 A10.2 10.2 0 0 1 31.8 24.8 C31.8 28.6 29 31 24 31 C19 31 16.2 28.6 16.2 24.8 A10.2 10.2 0 0 1 24 7.5",
        "M20 35.5 H28",
        "M21.2 39 H26.8",
    ),
}

STROKE = "1.7"


def glyph_ids() -> tuple[str, ...]:
    """Ids estables del set CRT (9)."""
    return tuple(GLYPH_PATHS.keys())


def glyph_svg_markup(glyph_id: str, extra_class: str = "") -> str:
    """SVG inline listo para rx.html / sprite."""
    paths = GLYPH_PATHS.get(glyph_id, GLYPH_PATHS["core"])
    parts = [
        f'<path d="{d}" fill="none" stroke="currentColor" '
        f'stroke-width="{STROKE}" stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
        for d in paths
    ]
    cls = "crt-bento-glyph" + (f" {extra_class}" if extra_class else "")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" '
        f'class="{cls}" aria-hidden="true">{"".join(parts)}</svg>'
    )


def glyph_sprite_markup() -> str:
    """Sprite con un <symbol> por glifo (assets y escenario)."""
    symbols: list[str] = []
    for glyph_id, paths in GLYPH_PATHS.items():
        inner = "".join(
            f'<path d="{d}" fill="none" stroke="currentColor" '
            f'stroke-width="{STROKE}" stroke-linecap="round" '
            f'stroke-linejoin="round"/>'
            for d in paths
        )
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
    return rx.el.svg(
        *[
            rx.el.path(
                d=d,
                fill="none",
                stroke="currentColor",
                stroke_width="1.7",
                stroke_linecap="round",
                stroke_linejoin="round",
            )
            for d in paths
        ],
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
        ("shield", glyph_el("shield")),
        ("mesh", glyph_el("mesh")),
        ("soul", glyph_el("soul")),
        ("tools", glyph_el("tools")),
        ("hardware", glyph_el("hardware")),
        ("steps", glyph_el("steps")),
        ("gerbil", glyph_el("gerbil")),
        ("idea", glyph_el("idea")),
        glyph_el("core"),
    )

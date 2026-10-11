"""Hero 2×2: escenario neuronal. El JS dibuja nodos, aristas y pulso."""

from __future__ import annotations

import reflex as rx


def neural_stage() -> rx.Component:
    """Lienzo CRT del núcleo — los 9 glifos viven aquí como nodos."""
    return rx.box(
        rx.el.svg(
            id="crt-neural-svg",
            class_name="crt-neural-svg",
            custom_attrs={"aria-hidden": "true"},
        ),
        rx.el.span("NÚCLEO", class_name="crt-bento-stage-label"),
        class_name="crt-bento-tile crt-bento-tile--hero crt-bento-stage",
        id="crt-neural-stage",
    )

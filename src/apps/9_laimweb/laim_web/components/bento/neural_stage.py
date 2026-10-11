"""Lienzo 3D de la red: el canvas dibuja aristas, pulsos y neuronas anónimas."""

from __future__ import annotations

import reflex as rx


def neural_stage() -> rx.Component:
    """Fondo CRT de la única escena — los 9 títulos se superponen encima."""
    return rx.el.canvas(
        id="crt-neural-canvas",
        class_name="crt-neural-canvas",
        custom_attrs={"aria-hidden": "true"},
    )

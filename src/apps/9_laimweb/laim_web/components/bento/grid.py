"""Una sola escena neuronal 3D; las baldosas son nodos de resultado."""

from __future__ import annotations

import reflex as rx

from laim_web.components.bento.neural_stage import neural_stage
from laim_web.components.bento.tile import bento_tile
from laim_web.laim_state import LaimWebState


def bento_grid() -> rx.Component:
    """Modo gráfico: red 3D + 9 neuronas de decisión clicables."""
    return rx.box(
        neural_stage(),
        rx.foreach(LaimWebState.inicio_bento_tiles, bento_tile),
        class_name="crt-bento-grid crt-neural-world",
        custom_attrs={
            "data-paused": LaimWebState.inicio_grid_paused,
        },
    )

"""Modal CRT con la referencia blue/green de modelos base."""

from __future__ import annotations

import reflex as rx

from laim_web.base_models_catalog import CATALOG_INTRO, catalog_table_markdown
from laim_web.base_models_compare import compare_guide_markdown
from laim_web.base_models_recommend import recommend_guide_markdown
from laim_web.components.markdown_viewer import crt_markdown_body
from laim_web.laim_state import LaimWebState


def base_models_catalog_modal() -> rx.Component:
    """Permanece montada (display) para no cerrarse al re-render."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(
                        "LAIM — Catálogo de modelos base",
                        class_name="crt-title",
                        margin_bottom="0",
                    ),
                    rx.spacer(),
                    rx.button(
                        "✕",
                        on_click=LaimWebState.close_base_models_catalog,
                        class_name="crt-btn crt-btn-icon crt-modal-close",
                        aria_label="Cerrar",
                    ),
                    width="100%",
                    align_items="center",
                    class_name="crt-modal-header",
                ),
                rx.text(
                    "Referencia de desarrollo · familias blue / green",
                    class_name="crt-muted",
                ),
                crt_markdown_body(CATALOG_INTRO),
                crt_markdown_body(catalog_table_markdown()),
                spacing="3",
                width="100%",
            ),
            class_name="crt-panel crt-modal-panel crt-modal-panel--catalog",
            padding="1.25rem",
            on_click=rx.stop_propagation,
            on_mouse_down=rx.stop_propagation,
        ),
        class_name="crt-modal-overlay",
        on_mouse_down=LaimWebState.close_base_models_catalog,
        display=rx.cond(LaimWebState.base_models_catalog_open, "flex", "none"),
        z_index="10001",
    )


def recommended_model_modal() -> rx.Component:
    """Mini-guía de cores, memoria, warmup y techos por GB."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(
                        "LAIM — Modelo recomendado para mi equipo",
                        class_name="crt-title",
                        margin_bottom="0",
                    ),
                    rx.spacer(),
                    rx.button(
                        "✕",
                        on_click=LaimWebState.close_recommended_model,
                        class_name="crt-btn crt-btn-icon crt-modal-close",
                        aria_label="Cerrar",
                    ),
                    width="100%",
                    align_items="center",
                    class_name="crt-modal-header",
                ),
                rx.text(
                    "Cores, memoria, concurrencia y warmup",
                    class_name="crt-muted",
                ),
                crt_markdown_body(recommend_guide_markdown()),
                spacing="3",
                width="100%",
            ),
            class_name="crt-panel crt-modal-panel crt-modal-panel--catalog",
            padding="1.25rem",
            on_click=rx.stop_propagation,
            on_mouse_down=rx.stop_propagation,
        ),
        class_name="crt-modal-overlay",
        on_mouse_down=LaimWebState.close_recommended_model,
        display=rx.cond(LaimWebState.recommended_model_open, "flex", "none"),
        z_index="10001",
    )


def compare_requirements_modal() -> rx.Component:
    """Comparativa monopuesto vs Share/Connect, Headscale y ajustes internos."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(
                        "LAIM — Comparativa de requisitos",
                        class_name="crt-title",
                        margin_bottom="0",
                    ),
                    rx.spacer(),
                    rx.button(
                        "✕",
                        on_click=LaimWebState.close_compare_requirements,
                        class_name="crt-btn crt-btn-icon crt-modal-close",
                        aria_label="Cerrar",
                    ),
                    width="100%",
                    align_items="center",
                    class_name="crt-modal-header",
                ),
                rx.text(
                    "Monopuesto · Share/Connect · Headscale · colas",
                    class_name="crt-muted",
                ),
                crt_markdown_body(compare_guide_markdown()),
                spacing="3",
                width="100%",
            ),
            class_name="crt-panel crt-modal-panel crt-modal-panel--catalog",
            padding="1.25rem",
            on_click=rx.stop_propagation,
            on_mouse_down=rx.stop_propagation,
        ),
        class_name="crt-modal-overlay",
        on_mouse_down=LaimWebState.close_compare_requirements,
        display=rx.cond(LaimWebState.compare_requirements_open, "flex", "none"),
        z_index="10001",
    )

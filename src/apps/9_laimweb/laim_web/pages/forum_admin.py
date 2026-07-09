"""Panel de administración del foro."""

from __future__ import annotations

import reflex as rx

from laim_web.components.forum_extended_ui import forum_stats_dialog
from laim_web.components.forum_service_panel import forum_admin_view_router
from laim_web.components.portal_shell import portal_page
from laim_web.laim_state import LaimWebState


def forum_admin_page():
    """Configuración del foro (solo administradores)."""
    return portal_page(
        rx.vstack(
            rx.cond(
                LaimWebState.forum_admin_view != "hub",
                rx.button(
                    rx.hstack(
                        rx.icon("arrow-left", size=16),
                        rx.text("Volver al panel del servicio"),
                        spacing="2",
                    ),
                    on_click=LaimWebState.forum_admin_go_hub,
                    class_name="crt-btn crt-btn-inline",
                    margin_bottom="0.5em",
                ),
                rx.fragment(),
            ),
            rx.cond(
                LaimWebState.forum_admin_message != "",
                rx.text(
                    LaimWebState.forum_admin_message,
                    color="#9dff9d",
                    margin_bottom="0.5em",
                ),
                rx.fragment(),
            ),
            forum_admin_view_router(),
            forum_stats_dialog(),
            spacing="4",
            width="100%",
        ),
        title="Config. foro — LAIM",
    )

"""Página pública temporal /r/{token} para cambiar la contraseña."""

from __future__ import annotations

import reflex as rx

from laim_web.components.crt_theme import COLORS
from laim_web.laim_state import LaimWebState
from laim_web.password_reset_mail import RESET_CHANGED_MSG, RESET_DEAD_MSG

FONT_SIZE_SMALL = "0.85em"


def password_reset_page() -> rx.Component:
    """Formulario de nueva contraseña o página muerta si el token caducó."""
    return rx.box(
        rx.center(
            rx.box(
                rx.vstack(
                    rx.text("LAIM — Contraseña", class_name="crt-title"),
                    rx.cond(
                        LaimWebState.reset_page_status == "dead",
                        rx.text(RESET_DEAD_MSG, class_name="crt-muted"),
                        rx.cond(
                            LaimWebState.reset_page_status == "done",
                            rx.text(RESET_CHANGED_MSG, class_name="crt-success"),
                            rx.vstack(
                                rx.text(
                                    "Elige una contraseña nueva (mínimo 8 caracteres).",
                                    class_name="crt-muted",
                                ),
                                rx.input(
                                    placeholder="Nueva contraseña",
                                    type="password",
                                    value=LaimWebState.reset_password,
                                    on_change=LaimWebState.set_reset_password,
                                    class_name="crt-input",
                                    width="100%",
                                ),
                                rx.input(
                                    placeholder="Repetir contraseña",
                                    type="password",
                                    value=LaimWebState.reset_password_confirm,
                                    on_change=LaimWebState.set_reset_password_confirm,
                                    class_name="crt-input",
                                    width="100%",
                                ),
                                rx.cond(
                                    LaimWebState.reset_error != "",
                                    rx.text(
                                        LaimWebState.reset_error,
                                        class_name="crt-error",
                                        font_size=FONT_SIZE_SMALL,
                                    ),
                                ),
                                rx.button(
                                    rx.cond(
                                        LaimWebState.reset_submitting,
                                        "Actualizando…",
                                        "Actualizar",
                                    ),
                                    on_click=LaimWebState.handle_reset_confirm,
                                    class_name="crt-btn",
                                    width="100%",
                                    disabled=LaimWebState.reset_submitting,
                                ),
                                spacing="3",
                                width="100%",
                            ),
                        ),
                    ),
                    spacing="3",
                    width="100%",
                ),
                class_name="crt-panel crt-modal-panel crt-modal-panel--auth",
                padding="1.25rem",
                width="100%",
                max_width="28rem",
            ),
            min_height="100vh",
            padding="2rem",
        ),
        class_name="crt-shell crt-theme-green",
        width="100%",
        background=COLORS["bg"],
    )

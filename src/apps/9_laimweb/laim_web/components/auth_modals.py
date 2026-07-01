"""Modales CRT de autenticación (login y registro)."""

from __future__ import annotations

import reflex as rx

from laim_web.components.hcaptcha import hcaptcha_widget
from laim_web.laim_state import LaimWebState

FONT_SIZE_SMALL = "0.85em"


def _modal_close_button(on_close) -> rx.Component:
    """Botón de cierre en la cabecera del modal."""
    return rx.button(
        "✕",
        on_click=on_close,
        class_name="crt-btn crt-btn-icon crt-modal-close",
        aria_label="Cerrar",
    )


def login_modal() -> rx.Component:
    """Ventana modal de inicio de sesión."""
    return rx.cond(
        LaimWebState.login_modal_open,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "LAIM — Inicio de sesión",
                            class_name="crt-title",
                            margin_bottom="0",
                        ),
                        rx.spacer(),
                        _modal_close_button(LaimWebState.close_login_modal),
                        width="100%",
                        align_items="center",
                        class_name="crt-modal-header",
                    ),
                    rx.text(
                        "Acceda al portal con sus credenciales de usuario.",
                        class_name="crt-muted",
                    ),
                    rx.input(
                        placeholder="Usuario",
                        value=LaimWebState.login_username,
                        on_change=LaimWebState.set_login_username,
                        class_name="crt-input",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Contraseña",
                        type="password",
                        value=LaimWebState.login_password,
                        on_change=LaimWebState.set_login_password,
                        class_name="crt-input",
                        width="100%",
                    ),
                    rx.cond(
                        LaimWebState.error_message != "",
                        rx.text(
                            LaimWebState.error_message,
                            class_name="crt-error",
                            font_size=FONT_SIZE_SMALL,
                        ),
                    ),
                    rx.cond(
                        LaimWebState.register_message != "",
                        rx.text(
                            LaimWebState.register_message,
                            class_name="crt-success",
                            font_size=FONT_SIZE_SMALL,
                        ),
                    ),
                    rx.button(
                        rx.cond(LaimWebState.loading, "Conectando…", "Conectar"),
                        on_click=LaimWebState.handle_login,
                        class_name="crt-btn",
                        width="100%",
                        disabled=LaimWebState.loading,
                    ),
                    rx.hstack(
                        rx.text("¿Sin cuenta?", class_name="crt-muted", font_size=FONT_SIZE_SMALL),
                        rx.button(
                            "Crear cuenta",
                            on_click=LaimWebState.switch_to_register_modal,
                            class_name="crt-btn crt-btn-link",
                        ),
                        spacing="2",
                        align_items="center",
                        width="100%",
                        flex_wrap="wrap",
                    ),
                    spacing="3",
                    width="100%",
                ),
                class_name="crt-panel crt-modal-panel crt-modal-panel--auth",
                padding="1.25rem",
                on_click=rx.stop_propagation,
            ),
            class_name="crt-modal-overlay",
            on_click=LaimWebState.close_login_modal,
            z_index="10001",
        ),
    )


def register_modal() -> rx.Component:
    """Ventana modal de registro público."""
    return rx.cond(
        LaimWebState.register_modal_open,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "LAIM — Crear cuenta",
                            class_name="crt-title",
                            margin_bottom="0",
                        ),
                        rx.spacer(),
                        _modal_close_button(LaimWebState.close_register_modal),
                        width="100%",
                        align_items="center",
                        class_name="crt-modal-header",
                    ),
                    rx.text(
                        "Registro de usuario para acceder al portal de gestión.",
                        class_name="crt-muted",
                    ),
                    rx.input(
                        placeholder="Usuario",
                        value=LaimWebState.reg_username,
                        on_change=LaimWebState.set_reg_username,
                        class_name="crt-input",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Nombre completo",
                        value=LaimWebState.reg_full_name,
                        on_change=LaimWebState.set_reg_full_name,
                        class_name="crt-input",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Email",
                        value=LaimWebState.reg_email,
                        on_change=LaimWebState.set_reg_email,
                        class_name="crt-input",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Móvil (opcional)",
                        value=LaimWebState.reg_mobile,
                        on_change=LaimWebState.set_reg_mobile,
                        class_name="crt-input",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Contraseña",
                        type="password",
                        value=LaimWebState.reg_password,
                        on_change=LaimWebState.set_reg_password,
                        class_name="crt-input",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Confirmar contraseña",
                        type="password",
                        value=LaimWebState.reg_password_confirm,
                        on_change=LaimWebState.set_reg_password_confirm,
                        class_name="crt-input",
                        width="100%",
                    ),
                    hcaptcha_widget(),
                    rx.input(
                        id="laim-hcaptcha-token-input",
                        value=LaimWebState.reg_hcaptcha_token,
                        on_change=LaimWebState.set_reg_hcaptcha_token_value,
                        display="none",
                    ),
                    rx.cond(
                        LaimWebState.error_message != "",
                        rx.text(
                            LaimWebState.error_message,
                            class_name="crt-error",
                            font_size=FONT_SIZE_SMALL,
                        ),
                    ),
                    rx.button(
                        rx.cond(LaimWebState.loading, "Registrando…", "Registrarse"),
                        on_click=LaimWebState.handle_register,
                        class_name="crt-btn",
                        width="100%",
                        disabled=LaimWebState.loading,
                    ),
                    rx.hstack(
                        rx.text("¿Ya tiene cuenta?", class_name="crt-muted", font_size=FONT_SIZE_SMALL),
                        rx.button(
                            "Iniciar sesión",
                            on_click=LaimWebState.switch_to_login_modal,
                            class_name="crt-btn crt-btn-link",
                        ),
                        spacing="2",
                        align_items="center",
                        width="100%",
                        flex_wrap="wrap",
                    ),
                    spacing="3",
                    width="100%",
                ),
                class_name="crt-panel crt-modal-panel crt-modal-panel--auth",
                padding="1.25rem",
                on_click=rx.stop_propagation,
            ),
            class_name="crt-modal-overlay",
            on_click=LaimWebState.close_register_modal,
            z_index="10001",
        ),
    )


def auth_modals() -> rx.Component:
    """Contenedor de modales de autenticación."""
    return rx.fragment(
        login_modal(),
        register_modal(),
    )

"""Formulario de contacto interno (estilo CRT)."""

from __future__ import annotations

import reflex as rx

from laim_web.components.crt_theme import COLORS
from laim_web.laim_state import LaimWebState

USAGE_MODE_OPTIONS = [
    "local",
    "share",
    "connect",
    "remote",
    "other",
]


def _field_group(*children: rx.Component, extra_class: str = "") -> rx.Component:
    cls = "crt-contact-field-group" + (f" {extra_class}" if extra_class else "")
    return rx.el.div(*children, class_name=cls)


def _contact_image_preview_modal() -> rx.Component:
    """Visor a tamaño cómodo, mismo patrón que el foro."""
    return rx.cond(
        LaimWebState.contact_preview_open,
        rx.box(
            rx.box(
                rx.image(
                    src=LaimWebState.contact_screenshot_preview_url,
                    max_width="90vw",
                    max_height="80vh",
                    object_fit="contain",
                ),
                rx.button(
                    "Cerrar",
                    on_click=LaimWebState.contact_close_preview,
                    class_name="crt-btn crt-btn-inline",
                    margin_top="1em",
                ),
                padding="1.5em",
                background=COLORS["panel_bg"],
                border=f"1px solid {COLORS['border']}",
                border_radius="4px",
            ),
            position="fixed",
            top="0",
            left="0",
            width="100vw",
            height="100vh",
            background="rgba(0,0,0,0.85)",
            display="flex",
            align_items="center",
            justify_content="center",
            z_index="1000",
            on_click=LaimWebState.contact_close_preview,
        ),
        rx.fragment(),
    )


def contact_form_panel() -> rx.Component:
    """Formulario debajo del markdown de la página Contacto."""
    return rx.box(
        rx.vstack(
            rx.text(
                "Formulario de contacto",
                class_name="crt-title",
                font_size="1.1em",
                margin_bottom="0.25em",
            ),
            rx.text(
                "Complete los campos para enviar su consulta. "
                "Puede adjuntar una captura de pantalla (PNG o JPG, máx. 5 MB).",
                class_name="crt-muted",
                font_size="0.9em",
            ),
            rx.el.div(
                _field_group(
                    rx.text("Modo de uso", class_name="crt-label"),
                    rx.select(
                        USAGE_MODE_OPTIONS,
                        value=LaimWebState.contact_usage_mode,
                        on_change=LaimWebState.set_contact_usage_mode,
                        class_name="crt-input crt-contact-select",
                    ),
                ),
                _field_group(
                    rx.text("Usuario afectado", class_name="crt-label"),
                    rx.input(
                        placeholder="usuario",
                        value=LaimWebState.contact_affected_user,
                        on_change=LaimWebState.set_contact_affected_user,
                        class_name="crt-input crt-contact-user",
                    ),
                ),
                _field_group(
                    rx.text("E-mail de respuesta", class_name="crt-label"),
                    rx.input(
                        placeholder="su@email.com",
                        type="email",
                        value=LaimWebState.contact_reply_email,
                        on_change=LaimWebState.set_contact_reply_email,
                        class_name="crt-input crt-contact-email",
                    ),
                ),
                class_name="crt-contact-meta-row",
            ),
            _field_group(
                rx.text("Descripción del problema", class_name="crt-label"),
                rx.text_area(
                    placeholder="Describa el problema, pasos para reproducirlo y cualquier detalle relevante…",
                    value=LaimWebState.contact_message_body,
                    on_change=LaimWebState.set_contact_message_body,
                    class_name="crt-input crt-textarea crt-contact-description",
                    rows="12",
                ),
                extra_class="crt-contact-description-group",
            ),
            _field_group(
                rx.text("Captura de pantalla (opcional)", class_name="crt-label"),
                rx.el.input(
                    type="file",
                    id="laim_contact_screenshot",
                    accept="image/png,image/jpeg,image/jpg",
                    class_name="crt-input crt-contact-file",
                    on_change=LaimWebState.contact_read_screenshot_preview,
                ),
                rx.cond(
                    LaimWebState.contact_screenshot_preview_url != "",
                    rx.el.button(
                        rx.image(
                            src=LaimWebState.contact_screenshot_preview_url,
                            alt=LaimWebState.contact_screenshot_name,
                        ),
                        rx.el.span(
                            LaimWebState.contact_screenshot_name,
                            class_name="crt-contact-preview-name",
                        ),
                        type="button",
                        class_name="crt-contact-preview",
                        on_click=LaimWebState.contact_open_preview,
                    ),
                    rx.fragment(),
                ),
            ),
            rx.cond(
                LaimWebState.contact_form_error != "",
                rx.text(
                    LaimWebState.contact_form_error,
                    class_name="crt-error",
                    font_size="0.85em",
                ),
            ),
            rx.cond(
                LaimWebState.contact_form_success,
                rx.text(
                    LaimWebState.contact_success_message,
                    class_name="crt-success",
                    font_size="0.85em",
                ),
            ),
            rx.el.div(
                rx.button(
                    rx.cond(
                        LaimWebState.contact_submitting,
                        "Enviando…",
                        "Enviar mensaje",
                    ),
                    on_click=LaimWebState.submit_contact_form,
                    class_name="crt-btn crt-contact-submit",
                    disabled=LaimWebState.contact_submitting,
                ),
                class_name="crt-contact-submit-wrap",
            ),
            spacing="3",
            width="100%",
            align_items="stretch",
            padding_top="1em",
        ),
        _contact_image_preview_modal(),
        class_name="crt-panel crt-contact-form",
        width="100%",
        margin_top="1em",
        padding="1em",
    )

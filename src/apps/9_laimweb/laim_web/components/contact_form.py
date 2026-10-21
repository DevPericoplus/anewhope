"""Formulario de contacto: botón en la página y modal CRT."""

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

CONTACT_THANKS_MESSAGE = "Agradecemos haber contactado con nosotros y trataremos de responder a su mensaje lo antes posible."


def _field_group(*children: rx.Component, extra_class: str = "") -> rx.Component:
    cls = "crt-contact-field-group" + (f" {extra_class}" if extra_class else "")
    return rx.el.div(*children, class_name=cls)


def _contact_image_preview_modal() -> rx.Component:
    """Visor a tamaño cómodo, por encima del modal de contacto."""
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
            z_index="10002",
            on_click=LaimWebState.contact_close_preview,
        ),
        rx.fragment(),
    )


def _contact_form_fields() -> rx.Component:
    """Campos del formulario (viven dentro del modal)."""
    return rx.vstack(
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
        class_name="crt-contact-form",
    )


def _contact_form_modal() -> rx.Component:
    """Ventana modal con el formulario de contacto."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(
                        "Formulario de contacto",
                        class_name="crt-title",
                        margin_bottom="0",
                    ),
                    rx.spacer(),
                    rx.button(
                        "✕",
                        on_click=LaimWebState.close_contact_modal,
                        class_name="crt-btn crt-btn-icon crt-modal-close",
                        aria_label="Cerrar",
                    ),
                    width="100%",
                    align_items="center",
                    class_name="crt-modal-header",
                ),
                _contact_form_fields(),
                spacing="3",
                width="100%",
            ),
            class_name="crt-panel crt-modal-panel crt-modal-panel--contact",
            padding="1.25rem",
            on_click=rx.stop_propagation,
            on_mouse_down=rx.stop_propagation,
        ),
        _contact_image_preview_modal(),
        class_name="crt-modal-overlay",
        on_mouse_down=LaimWebState.close_contact_modal,
        display=rx.cond(LaimWebState.contact_modal_open, "flex", "none"),
        z_index="10001",
    )


def _contact_thanks_modal() -> rx.Component:
    """Aviso breve tras el envío. «Volver» deja la página de Contacto."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.text(
                    CONTACT_THANKS_MESSAGE,
                    class_name="crt-muted",
                    font_size="1em",
                ),
                rx.el.div(
                    rx.button(
                        "Volver",
                        on_click=LaimWebState.contact_thanks_back,
                        class_name="crt-btn crt-contact-submit",
                    ),
                    class_name="crt-contact-submit-wrap",
                ),
                spacing="3",
                width="100%",
                align_items="stretch",
            ),
            class_name="crt-panel crt-modal-panel crt-modal-panel--thanks",
            padding="1.25rem",
            on_click=rx.stop_propagation,
            on_mouse_down=rx.stop_propagation,
        ),
        class_name="crt-modal-overlay",
        display=rx.cond(LaimWebState.contact_thanks_open, "flex", "none"),
        z_index="10003",
    )


def contact_form_panel() -> rx.Component:
    """Botón «Contactar» en la página; el formulario vive en el modal.

    La página de Contacto es la misma con sesión y sin ella (menú público
    y «Contactar por email» desde Soporte).
    """
    return rx.fragment(
        rx.el.div(
            rx.button(
                "Contactar",
                on_click=LaimWebState.open_contact_modal,
                class_name="crt-btn crt-contact-open",
            ),
            class_name="crt-contact-open-wrap",
        ),
        _contact_form_modal(),
        _contact_thanks_modal(),
    )

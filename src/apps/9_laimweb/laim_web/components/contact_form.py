"""Formulario de contacto interno (estilo CRT)."""

from __future__ import annotations

import reflex as rx

from laim_web.laim_state import LaimWebState

USAGE_MODE_OPTIONS = [
    "local",
    "share",
    "connect",
    "remote",
    "other",
]


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
                "Puede adjuntar una captura de pantalla (PNG, JPG, WEBP o GIF, máx. 5 MB).",
                class_name="crt-muted",
                font_size="0.9em",
            ),
            rx.text("Modo de uso", class_name="crt-label"),
            rx.select(
                USAGE_MODE_OPTIONS,
                value=LaimWebState.contact_usage_mode,
                on_change=LaimWebState.set_contact_usage_mode,
                class_name="crt-input",
                width="100%",
            ),
            rx.text("Usuario afectado", class_name="crt-label"),
            rx.input(
                placeholder="Nombre de usuario o identificador afectado",
                value=LaimWebState.contact_affected_user,
                on_change=LaimWebState.set_contact_affected_user,
                class_name="crt-input",
                width="100%",
            ),
            rx.text("E-mail de respuesta", class_name="crt-label"),
            rx.input(
                placeholder="su@email.com",
                type="email",
                value=LaimWebState.contact_reply_email,
                on_change=LaimWebState.set_contact_reply_email,
                class_name="crt-input",
                width="100%",
            ),
            rx.text("Descripción del problema", class_name="crt-label"),
            rx.text_area(
                placeholder="Describa el problema, pasos para reproducirlo y cualquier detalle relevante…",
                value=LaimWebState.contact_message_body,
                on_change=LaimWebState.set_contact_message_body,
                class_name="crt-input crt-textarea",
                width="100%",
                rows="6",
            ),
            rx.text("Captura de pantalla (opcional)", class_name="crt-label"),
            rx.el.input(
                type="file",
                id="laim_contact_screenshot",
                accept="image/png,image/jpeg,image/jpg,image/webp,image/gif",
                class_name="crt-input",
                style={"width": "100%"},
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
                    "Mensaje enviado correctamente. Le responderemos a la dirección indicada.",
                    class_name="crt-success",
                    font_size="0.85em",
                ),
            ),
            rx.button(
                rx.cond(
                    LaimWebState.contact_submitting,
                    "Enviando…",
                    "Enviar mensaje",
                ),
                on_click=LaimWebState.submit_contact_form,
                class_name="crt-btn",
                width="100%",
                disabled=LaimWebState.contact_submitting,
            ),
            spacing="3",
            width="100%",
            align_items="stretch",
            padding_top="1em",
        ),
        class_name="crt-panel crt-contact-form",
        width="100%",
        margin_top="1em",
        padding="1em",
    )

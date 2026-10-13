"""Modales CRT de tickets de soporte (crear + estado)."""

from __future__ import annotations

import reflex as rx

from laim_web.laim_state import LaimWebState


def _field(label: str, value) -> rx.Component:
    return rx.hstack(
        rx.text(label, class_name="crt-muted", width="9em"),
        rx.text(value, class_name="crt-text"),
        spacing="2",
        width="100%",
    )


def ticket_create_modal() -> rx.Component:
    """Alta de ticket con datos de sesión ya rellenos."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text("Abrir ticket de soporte", class_name="crt-title", margin_bottom="0"),
                    rx.spacer(),
                    rx.button(
                        "✕",
                        on_click=LaimWebState.close_ticket_create,
                        class_name="crt-btn crt-btn-icon crt-modal-close",
                        aria_label="Cerrar",
                    ),
                    width="100%",
                    align_items="center",
                    class_name="crt-modal-header",
                ),
                _field("Usuario", LaimWebState.user_name),
                _field("Email", LaimWebState.user_email),
                _field("Edición", LaimWebState.ticket_edition_label),
                rx.text("Asunto", class_name="crt-muted"),
                rx.input(
                    value=LaimWebState.ticket_subject,
                    on_change=LaimWebState.set_ticket_subject,
                    class_name="crt-input",
                    placeholder="Resuma el problema",
                ),
                rx.text("Descripción", class_name="crt-muted"),
                rx.text_area(
                    value=LaimWebState.ticket_body,
                    on_change=LaimWebState.set_ticket_body,
                    class_name="crt-input crt-contact-description",
                    placeholder="Cuéntenos qué ocurre y qué ha intentado.",
                    rows="8",
                ),
                rx.cond(
                    LaimWebState.ticket_form_error != "",
                    rx.text(LaimWebState.ticket_form_error, class_name="crt-error"),
                    rx.fragment(),
                ),
                rx.cond(
                    LaimWebState.ticket_form_success != "",
                    rx.text(LaimWebState.ticket_form_success, class_name="crt-text"),
                    rx.fragment(),
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "Enviar",
                        on_click=LaimWebState.submit_ticket,
                        loading=LaimWebState.ticket_submitting,
                        class_name="crt-btn",
                    ),
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            class_name="crt-panel crt-modal-panel",
            padding="1.25rem",
            on_click=rx.stop_propagation,
            on_mouse_down=rx.stop_propagation,
        ),
        class_name="crt-modal-overlay",
        on_mouse_down=LaimWebState.close_ticket_create,
        display=rx.cond(LaimWebState.ticket_create_open, "flex", "none"),
        z_index="10001",
    )


def _ticket_row(item: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(item["id"]),
        rx.table.cell(item["subject"]),
        rx.table.cell(item["estado_nombre"]),
        rx.table.cell(item["opened_at"]),
        on_click=lambda: LaimWebState.open_ticket_detail(item["id"]),
        cursor="pointer",
    )


def _message_row(item: dict) -> rx.Component:
    return rx.box(
        rx.text(
            item["actor_name"] + " · " + item["created_at"],
            class_name="crt-muted",
        ),
        rx.text(item["cuerpo"], class_name="crt-text", white_space="pre-wrap"),
        padding_y="0.4em",
        border_bottom="1px solid rgba(0, 200, 0, 0.15)",
        width="100%",
    )


def ticket_status_modal() -> rx.Component:
    """Tabla de tickets del usuario + detalle/cronología."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text("Estado de tickets", class_name="crt-title", margin_bottom="0"),
                    rx.spacer(),
                    rx.button(
                        "✕",
                        on_click=LaimWebState.close_ticket_status,
                        class_name="crt-btn crt-btn-icon crt-modal-close",
                        aria_label="Cerrar",
                    ),
                    width="100%",
                    align_items="center",
                    class_name="crt-modal-header",
                ),
                rx.cond(
                    LaimWebState.ticket_list_error != "",
                    rx.text(LaimWebState.ticket_list_error, class_name="crt-error"),
                    rx.fragment(),
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("#"),
                            rx.table.column_header_cell("Asunto"),
                            rx.table.column_header_cell("Estado"),
                            rx.table.column_header_cell("Abierto"),
                        )
                    ),
                    rx.table.body(rx.foreach(LaimWebState.ticket_items, _ticket_row)),
                    width="100%",
                ),
                rx.cond(
                    LaimWebState.ticket_detail_id > 0,
                    rx.vstack(
                        rx.text(
                            LaimWebState.ticket_detail_subject,
                            class_name="crt-title",
                            font_size="1em",
                        ),
                        _field("Estado", LaimWebState.ticket_detail_estado),
                        _field("Edición", LaimWebState.ticket_detail_edition),
                        rx.text("Cronología", class_name="crt-muted"),
                        rx.foreach(LaimWebState.ticket_messages, _message_row),
                        rx.cond(
                            LaimWebState.ticket_detail_readonly,
                            rx.text("Este ticket está cerrado y es solo lectura.", class_name="crt-muted"),
                            rx.vstack(
                                rx.text_area(
                                    value=LaimWebState.ticket_reply_body,
                                    on_change=LaimWebState.set_ticket_reply_body,
                                    class_name="crt-input crt-contact-description",
                                    placeholder="Escriba su respuesta",
                                    rows="5",
                                ),
                                rx.button(
                                    "Responder",
                                    on_click=LaimWebState.submit_ticket_reply,
                                    loading=LaimWebState.ticket_replying,
                                    class_name="crt-btn",
                                ),
                                width="100%",
                                spacing="2",
                            ),
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.text("Pulse una fila para ver el detalle.", class_name="crt-muted"),
                ),
                spacing="3",
                width="100%",
            ),
            class_name="crt-panel crt-modal-panel crt-modal-panel--catalog",
            padding="1.25rem",
            on_click=rx.stop_propagation,
            on_mouse_down=rx.stop_propagation,
        ),
        class_name="crt-modal-overlay",
        on_mouse_down=LaimWebState.close_ticket_status,
        display=rx.cond(LaimWebState.ticket_status_open, "flex", "none"),
        z_index="10001",
    )


def ticket_notification_modal() -> rx.Component:
    """Aviso persistido: el operador pide atención. Abrir el ticket confirma."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.text("Soporte", class_name="crt-title"),
                rx.text(
                    "Un ticket de soporte requiere su atención.",
                    class_name="crt-text",
                ),
                rx.text(
                    "#",
                    LaimWebState.ticket_notif_ticket_id,
                    " · ",
                    LaimWebState.ticket_notif_subject,
                    class_name="crt-muted",
                ),
                rx.hstack(
                    rx.button(
                        "Ir a soporte",
                        on_click=LaimWebState.ack_ticket_notification(True),
                        class_name="crt-btn",
                    ),
                    rx.button(
                        "Cerrar",
                        on_click=LaimWebState.ack_ticket_notification(False),
                        class_name="crt-btn crt-btn-icon",
                    ),
                    spacing="2",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            class_name="crt-panel crt-modal-panel",
            padding="1.25rem",
            on_click=rx.stop_propagation,
            on_mouse_down=rx.stop_propagation,
        ),
        class_name="crt-modal-overlay",
        display=rx.cond(LaimWebState.ticket_notif_open, "flex", "none"),
        z_index="10002",
    )

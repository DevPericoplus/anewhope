"""Página Registro: instalaciones LAIM del usuario autenticado."""

from __future__ import annotations

import reflex as rx

from laim_web.laim_state import LaimWebState

_OS_OPTIONS = ("windows", "mac", "linux")
# Advance se activa con ADVANCE_LICENSES_ENABLED en el core; el selector
# extra de licencia (vigencia, plugins) se añadirá aquí cuando exista cobro.
_ADVANCE_FORM_ENABLED = False
_EDITION_LABEL = "Community Edition"


def _status_label(item: dict) -> rx.Component:
    return rx.cond(
        item["status"] == "pending_recognition",
        rx.text("Pendiente de reconocer", class_name="crt-muted"),
        rx.text("Registrada", class_name="crt-text"),
    )


def _install_row(item: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.cond(
                item["display_name"] != "",
                item["display_name"],
                item["hostname"],
            )
        ),
        rx.table.cell(item["serial_masked"]),
        rx.table.cell(item["operating_system"]),
        rx.table.cell(_EDITION_LABEL),
        rx.table.cell(_status_label(item)),
        rx.table.cell(
            rx.cond(
                item["status"] == "pending_recognition",
                rx.hstack(
                    rx.button(
                        "✅",
                        on_click=lambda: LaimWebState.recognize_installation(item["installation_id"]),
                        class_name="crt-btn crt-btn-icon",
                        title="Reconocer",
                        aria_label="Reconocer",
                        on_mouse_down=rx.stop_propagation,
                    ),
                    rx.button(
                        "❌",
                        on_click=lambda: LaimWebState.reject_installation(item["installation_id"]),
                        class_name="crt-btn crt-btn-icon",
                        title="Rechazar",
                        aria_label="Rechazar",
                        on_mouse_down=rx.stop_propagation,
                    ),
                    spacing="1",
                    on_mouse_down=rx.stop_propagation,
                ),
                rx.fragment(),
            )
        ),
        on_click=lambda: LaimWebState.open_installation(item["installation_id"]),
        cursor="pointer",
    )


def _manual_form() -> rx.Component:
    return rx.vstack(
        rx.text(
            rx.cond(LaimWebState.install_editing, "Modificar registro", "Registro manual"),
            class_name="crt-title",
            font_size="1em",
        ),
        rx.text("Número de serie", class_name="crt-muted"),
        rx.hstack(
            rx.input(
                value=LaimWebState.install_serial,
                on_change=LaimWebState.set_install_serial,
                on_blur=LaimWebState.verify_install_serial,
                class_name="crt-input",
                placeholder="2-XXXX-XXXX-…",
                disabled=LaimWebState.install_editing,
                width="100%",
            ),
            rx.cond(
                LaimWebState.install_serial_valid,
                rx.text("✅ Validado", class_name="crt-text"),
                rx.fragment(),
            ),
            align="center",
            width="100%",
            spacing="2",
        ),
        rx.cond(
            LaimWebState.install_serial_error != "",
            rx.text(LaimWebState.install_serial_error, class_name="crt-error"),
            rx.fragment(),
        ),
        rx.text("Nombre de máquina", class_name="crt-muted"),
        rx.input(
            value=LaimWebState.install_hostname,
            on_change=LaimWebState.set_install_hostname,
            class_name="crt-input",
            disabled=LaimWebState.install_editing,
        ),
        rx.text("Alias del dispositivo", class_name="crt-muted"),
        rx.input(
            value=LaimWebState.install_display_name,
            on_change=LaimWebState.set_install_display_name,
            class_name="crt-input",
            placeholder="p. ej. Portátil de casa",
        ),
        rx.text("Sistema operativo", class_name="crt-muted"),
        rx.select(
            list(_OS_OPTIONS),
            value=LaimWebState.install_os,
            on_change=LaimWebState.set_install_os,
            class_name="crt-input",
        ),
        rx.text("Edición", class_name="crt-muted"),
        rx.text(_EDITION_LABEL, class_name="crt-text"),
        rx.cond(
            _ADVANCE_FORM_ENABLED,
            rx.text(
                "Opciones Advance (vigencia, plugins) se mostrarán aquí.",
                class_name="crt-muted",
            ),
            rx.fragment(),
        ),
        rx.cond(
            LaimWebState.install_form_error != "",
            rx.text(LaimWebState.install_form_error, class_name="crt-error"),
            rx.fragment(),
        ),
        rx.cond(
            LaimWebState.install_form_success != "",
            rx.text(LaimWebState.install_form_success, class_name="crt-text"),
            rx.fragment(),
        ),
        rx.hstack(
            rx.button(
                "Guardar",
                on_click=LaimWebState.save_installation,
                loading=LaimWebState.install_saving,
                class_name="crt-btn",
            ),
            rx.button(
                "Cancelar",
                on_click=LaimWebState.close_install_form,
                class_name="crt-btn crt-btn-inline",
            ),
            spacing="2",
        ),
        spacing="2",
        width="100%",
        class_name="crt-panel crt-form-section",
        padding="1rem",
    )


def registro_panel() -> rx.Component:
    """Tabla de instalaciones + alta/edición manual."""
    return rx.vstack(
        rx.hstack(
            rx.button(
                "Registro manual",
                on_click=LaimWebState.open_manual_register,
                class_name="crt-btn",
            ),
            rx.button(
                "Actualizar",
                on_click=LaimWebState.load_installations,
                class_name="crt-btn crt-btn-inline",
            ),
            spacing="2",
        ),
        rx.cond(
            LaimWebState.install_list_error != "",
            rx.text(LaimWebState.install_list_error, class_name="crt-error"),
            rx.fragment(),
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Alias"),
                    rx.table.column_header_cell("Número de serie"),
                    rx.table.column_header_cell("SO"),
                    rx.table.column_header_cell("Edición"),
                    rx.table.column_header_cell("Estado"),
                    rx.table.column_header_cell("Acciones"),
                )
            ),
            rx.table.body(rx.foreach(LaimWebState.install_items, _install_row)),
            width="100%",
        ),
        rx.cond(LaimWebState.install_form_open, _manual_form(), rx.fragment()),
        spacing="3",
        width="100%",
        padding_top="1rem",
    )


def install_notification_modal() -> rx.Component:
    """Aviso persistido: una propuesta de laim espera reconocimiento. El poll no hace ack."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.text("Registro", class_name="crt-title"),
                rx.text(
                    "Una instalación de LAIM espera su reconocimiento.",
                    class_name="crt-text",
                ),
                rx.text(
                    LaimWebState.install_notif_label,
                    class_name="crt-muted",
                ),
                rx.hstack(
                    rx.button(
                        "Ir a Registro",
                        on_click=LaimWebState.ack_install_notification(True),
                        class_name="crt-btn",
                    ),
                    rx.button(
                        "Cerrar",
                        on_click=LaimWebState.ack_install_notification(False),
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
        display=rx.cond(LaimWebState.install_notif_open, "flex", "none"),
        z_index="10003",
    )

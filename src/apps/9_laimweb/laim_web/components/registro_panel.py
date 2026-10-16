"""Página Registro: instalaciones LAIM del usuario autenticado."""

from __future__ import annotations

import reflex as rx

from laim_web.laim_state import LaimWebState

_OS_OPTIONS = ("windows", "mac", "linux")
# Advance se activa con ADVANCE_LICENSES_ENABLED en el core; el selector
# extra de licencia (vigencia, plugins) se añadirá aquí cuando exista cobro.
_ADVANCE_FORM_ENABLED = False

_EDITION_LABEL = "Community Edition"

REGISTER_INSTRUCTIONS_MD = """
Cada copia de LAIM de su equipo se asocia a **esta cuenta**. Puede registrar varias. Hay dos caminos; elija uno por instalación.

### 1. Registro manual (desde este portal)

Ideal si acaba de instalar LAIM y tiene delante la pantalla de login.

1. Abra LAIM en ese equipo (`laim web` → http://localhost:4321). En la **ventana de login**, debajo del botón de entrar, aparece el número de serie, por ejemplo `2-K3MP-9QRA-LW7N-4BXT-M8HJ12C`.
2. Pulse el botón **⎘** (Copiar serial). Queda en el portapapeles; no hace falta transcribirlo a mano.
3. Vuelva aquí y pulse **Registro manual**.
4. Pegue el serial. Cuando sea auténtico verá **✅ Validado**.
5. Nombre de máquina: el que muestra el equipo, p. ej. `PORTATIL-CASA`.
6. Alias (opcional): `Portátil de casa`.
7. Sistema operativo: `windows`, `mac` o `linux`.
8. Pulse **Guardar**. La fila queda **Registrada**.

El serial y el nombre de máquina no se pueden cambiar después. El alias sí.

### 2. Desde LAIM (propuesta automática)

Ideal cuando ya ha iniciado sesión en LAIM.

1. En LAIM: **Configuración › Internal › Local › Registro en laim.app › Registrar**.
2. Escriba el **usuario** y el **e-mail** de **esta** cuenta del portal, los mismos del alta. Ejemplo: usuario `ana`, correo `ana@empresa.com`.
3. Pulse **Enviar propuesta** **una sola vez**.
4. Vuelva a esta página (o pulse **Actualizar**). Verá la fila **Pendiente de reconocer**.
5. Pulse **✅ Reconocer**. Con eso confirma que esa instalación es suya.

Si pulsa Enviar propuesta otra vez con el mismo serial, el portal dirá que ya está registrado: no es un fallo, es que la propuesta ya llegó.

**Rechazar** descarta la propuesta. Después puede volver a registrarla (manual o desde LAIM).
"""


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
                "Instrucciones de Registro",
                on_click=LaimWebState.open_install_instructions,
                class_name="crt-btn crt-btn-inline",
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

def install_instructions_modal() -> rx.Component:
    """Guía de las dos modalidades de registro (manual y desde LAIM)."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text("Instrucciones de Registro", class_name="crt-title", margin_bottom="0"),
                    rx.spacer(),
                    rx.button(
                        "✕",
                        on_click=LaimWebState.close_install_instructions,
                        class_name="crt-btn crt-btn-icon crt-modal-close",
                        aria_label="Cerrar",
                    ),
                    width="100%",
                    align_items="center",
                    class_name="crt-modal-header",
                ),
                rx.box(
                    rx.markdown(REGISTER_INSTRUCTIONS_MD),
                    overflow_y="auto",
                    max_height="70vh",
                    width="100%",
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "Cerrar",
                        on_click=LaimWebState.close_install_instructions,
                        class_name="crt-btn",
                    ),
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            class_name="crt-panel crt-modal-panel",
            padding="1.25rem",
            max_width="42rem",
            width="100%",
            on_click=rx.stop_propagation,
            on_mouse_down=rx.stop_propagation,
        ),
        class_name="crt-modal-overlay",
        on_mouse_down=LaimWebState.close_install_instructions,
        display=rx.cond(LaimWebState.install_instructions_open, "flex", "none"),
        z_index="10002",
    )


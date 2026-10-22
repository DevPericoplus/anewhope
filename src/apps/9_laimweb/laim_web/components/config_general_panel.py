"""Botones y modales de Configuración → General."""

from __future__ import annotations

import reflex as rx

from laim_web.laim_state import LaimWebState


def _overlay(panel: rx.Component) -> rx.Component:
    return rx.box(panel, class_name="crt-modal-overlay")


def _modal(title: str, body: rx.Component, on_close, wide: bool = False) -> rx.Component:
    return _overlay(
        rx.box(
            rx.hstack(
                rx.heading(title, size="4"),
                rx.button("Cerrar", on_click=on_close, class_name="crt-btn"),
                justify="between",
                align="center",
                width="100%",
            ),
            body,
            class_name="crt-panel crt-modal-panel",
            style={
                "maxWidth": "960px" if wide else "520px",
                "width": "92vw",
                "maxHeight": "86vh",
                "overflow": "auto",
                "padding": "1rem",
            },
        )
    )


def _users_table() -> rx.Component:
    return rx.el.table(
        rx.el.thead(
            rx.el.tr(
                rx.el.th("ID"),
                rx.el.th("Usuario"),
                rx.el.th("Email"),
                rx.el.th("Móvil"),
                rx.el.th("Estado"),
                rx.el.th(""),
            )
        ),
        rx.el.tbody(
            rx.foreach(
                LaimWebState.cfg_users,
                lambda item: rx.el.tr(
                    rx.el.td(item["user_id"]),
                    rx.el.td(item["user_name"]),
                    rx.el.td(item["user_email"]),
                    rx.el.td(item["user_mobile"]),
                    rx.el.td(
                        rx.cond(
                            item["estado"] == "",
                            rx.text("—"),
                            rx.button(
                                item["estado"],
                                on_click=LaimWebState.toggle_cfg_user_status(
                                    item["user_id"], item["blocked"]
                                ),
                                class_name="crt-btn",
                                color=rx.cond(item["blocked"], "#b91c1c", "#15803d"),
                            ),
                        )
                    ),
                    rx.el.td(
                        rx.button(
                            "Abrir",
                            on_click=LaimWebState.open_cfg_user(item["user_id"]),
                            class_name="crt-btn",
                        )
                    ),
                ),
            )
        ),
        width="100%",
    )


def _user_detail_modal() -> rx.Component:
    return rx.cond(
        LaimWebState.cfg_user_open,
        _modal(
            "Usuario",
            rx.vstack(
                rx.input(
                    placeholder="Usuario",
                    value=LaimWebState.cfg_user_name,
                    on_change=LaimWebState.set_cfg_user_name,
                    class_name="crt-input",
                    width="100%",
                ),
                rx.input(
                    placeholder="Nombre completo",
                    value=LaimWebState.cfg_user_full_name,
                    on_change=LaimWebState.set_cfg_user_full_name,
                    class_name="crt-input",
                    width="100%",
                ),
                rx.input(
                    placeholder="Email",
                    value=LaimWebState.cfg_user_email,
                    on_change=LaimWebState.set_cfg_user_email,
                    class_name="crt-input",
                    width="100%",
                ),
                rx.input(
                    placeholder="Móvil",
                    value=LaimWebState.cfg_user_mobile,
                    on_change=LaimWebState.set_cfg_user_mobile,
                    class_name="crt-input",
                    width="100%",
                ),
                rx.hstack(
                    rx.button("Guardar", on_click=LaimWebState.save_cfg_user, class_name="crt-btn"),
                    rx.button(
                        "Actualizar contraseña",
                        on_click=LaimWebState.open_cfg_password,
                        class_name="crt-btn",
                    ),
                    spacing="2",
                ),
                spacing="3",
                width="100%",
            ),
            LaimWebState.close_cfg_user,
        ),
        rx.fragment(),
    )


def _password_modal() -> rx.Component:
    return rx.cond(
        LaimWebState.cfg_password_open,
        _modal(
            "Actualizar contraseña",
            rx.vstack(
                rx.input(
                    placeholder="Contraseña",
                    type="password",
                    value=LaimWebState.cfg_password,
                    on_change=LaimWebState.set_cfg_password,
                    class_name="crt-input",
                    width="100%",
                ),
                rx.input(
                    placeholder="Confirmación",
                    type="password",
                    value=LaimWebState.cfg_password_confirm,
                    on_change=LaimWebState.set_cfg_password_confirm,
                    class_name="crt-input",
                    width="100%",
                ),
                rx.button(
                    "Guardar contraseña",
                    on_click=LaimWebState.submit_cfg_password,
                    class_name="crt-btn",
                ),
                spacing="3",
                width="100%",
            ),
            LaimWebState.close_cfg_password,
        ),
        rx.fragment(),
    )


def _users_modal() -> rx.Component:
    return rx.cond(
        LaimWebState.cfg_users_open,
        _modal(
            "Usuarios",
            rx.vstack(
                rx.text(
                    "Cuentas de este portal. Pulsar el estado lo cambia en el servidor; si falla, la fila no se modifica.",
                    font_size="0.9rem",
                ),
                rx.hstack(
                    rx.input(
                        placeholder="Buscar usuario o email",
                        value=LaimWebState.cfg_users_query,
                        on_change=LaimWebState.set_cfg_users_query,
                        class_name="crt-input",
                        width="100%",
                    ),
                    rx.button("Buscar", on_click=LaimWebState.load_cfg_users, class_name="crt-btn"),
                    width="100%",
                ),
                rx.cond(
                    LaimWebState.cfg_users_error != "",
                    rx.text(LaimWebState.cfg_users_error, class_name="crt-error"),
                    rx.fragment(),
                ),
                rx.cond(
                    LaimWebState.cfg_users_notice != "",
                    rx.text(LaimWebState.cfg_users_notice),
                    rx.fragment(),
                ),
                _users_table(),
                spacing="3",
                width="100%",
            ),
            LaimWebState.close_cfg_users,
            wide=True,
        ),
        rx.fragment(),
    )


def _registro_table() -> rx.Component:
    return rx.el.table(
        rx.el.thead(
            rx.el.tr(
                rx.el.th("ID"),
                rx.el.th("Usuario"),
                rx.el.th("Alias"),
                rx.el.th("Número de serie"),
                rx.el.th("SO"),
                rx.el.th("Edición"),
                rx.el.th("Estado"),
                rx.el.th("Registrada"),
            )
        ),
        rx.el.tbody(
            rx.foreach(
                LaimWebState.cfg_registro_rows,
                lambda item: rx.el.tr(
                    rx.el.td(item["installation_id"]),
                    rx.el.td(item["user_id"]),
                    rx.el.td(item["alias"]),
                    rx.el.td(item["serial_masked"]),
                    rx.el.td(item["operating_system"]),
                    rx.el.td(item["edition"]),
                    rx.el.td(item["status"]),
                    rx.el.td(item["registered_at"]),
                ),
            )
        ),
        width="100%",
    )


def _chart(title: str, svg) -> rx.Component:
    return rx.cond(
        svg != "",
        rx.vstack(
            rx.text(title, weight="bold"),
            rx.box(
                rx.html(svg),
                style={"background": "#f8fafc", "padding": "0.5rem", "borderRadius": "8px"},
                width="100%",
            ),
            width="100%",
            align="start",
        ),
        rx.fragment(),
    )


def _dash_modal() -> rx.Component:
    return rx.cond(
        LaimWebState.cfg_dash_open,
        _modal(
            LaimWebState.cfg_dash_title,
            rx.vstack(
                rx.text(LaimWebState.cfg_dash_subtitle),
                rx.flex(
                    rx.foreach(
                        LaimWebState.cfg_dash_highlights,
                        lambda card: rx.box(
                            rx.text(card["title"], color="white"),
                            rx.heading(card["value"], size="5", color="white"),
                            rx.text(card["delta"], color="white"),
                            rx.html(card["spark_svg"]),
                            style={"background": card["background"], "padding": "0.75rem", "minWidth": "160px"},
                        ),
                    ),
                    wrap="wrap",
                    spacing="2",
                    width="100%",
                ),
                _chart("Tendencia", LaimWebState.cfg_svg_trend),
                _chart("Altas mensuales", LaimWebState.cfg_svg_monthly),
                _chart("Mix", LaimWebState.cfg_svg_mix),
                _chart("Actividad", LaimWebState.cfg_svg_scatter),
                _chart("Totales por sistema", LaimWebState.cfg_svg_os),
                rx.cond(
                    LaimWebState.cfg_svg_gauge != "",
                    rx.box(
                        rx.html(LaimWebState.cfg_svg_gauge),
                        style={"background": "#111827", "padding": "0.5rem", "maxWidth": "180px"},
                    ),
                    rx.fragment(),
                ),
                spacing="3",
                width="100%",
            ),
            LaimWebState.close_cfg_dash,
            wide=True,
        ),
        rx.fragment(),
    )


def _registro_modal() -> rx.Component:
    return rx.cond(
        LaimWebState.cfg_registro_open,
        _modal(
            "Registro",
            rx.vstack(
                rx.text(
                    "Inventario de instalaciones de este entorno. El menú Registro del portal sigue siendo el alta del usuario.",
                    font_size="0.9rem",
                ),
                rx.button(
                    "Evolución de registros",
                    on_click=LaimWebState.open_cfg_dash,
                    class_name="crt-btn",
                ),
                rx.cond(
                    LaimWebState.cfg_registro_error != "",
                    rx.text(LaimWebState.cfg_registro_error, class_name="crt-error"),
                    rx.fragment(),
                ),
                _registro_table(),
                spacing="3",
                width="100%",
            ),
            LaimWebState.close_cfg_registro,
            wide=True,
        ),
        rx.fragment(),
    )


def config_general_panel() -> rx.Component:
    """Acciones de General. El markdown de la página se sigue mostrando encima."""
    return rx.cond(
        LaimWebState.is_laim_admin,
        rx.vstack(
            rx.hstack(
                rx.button("Usuarios", on_click=LaimWebState.open_cfg_users, class_name="crt-btn"),
                rx.button("Registro", on_click=LaimWebState.open_cfg_registro, class_name="crt-btn"),
                spacing="3",
            ),
            _users_modal(),
            _user_detail_modal(),
            _password_modal(),
            _registro_modal(),
            _dash_modal(),
            spacing="3",
            width="100%",
            padding="1rem",
        ),
        rx.fragment(),
    )

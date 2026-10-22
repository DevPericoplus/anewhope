"""Panel hub del servicio de foro LAIM (estilo Radikal + temática CRT)."""

from __future__ import annotations

import reflex as rx

from laim_web.components.crt_theme import COLORS, FONT_SIZE_BODY, FONT_SIZE_SMALL
from laim_web.components.forum_extended_ui import (
    forum_admin_extended_panel,
    forum_stats_dialog,
)
from laim_web.components.forum_ui import forum_admin_panel
from laim_web.laim_state import LaimWebState


def _service_badge() -> rx.Component:
    """Indicador en línea / detenido."""
    return rx.cond(
        LaimWebState.forum_service_active,
        rx.box(
            rx.text("En línea", color=COLORS["accent"], font_weight="bold"),
            padding="0.35em 0.75em",
            border=f"1px solid {COLORS['accent']}",
            border_radius="4px",
        ),
        rx.box(
            rx.text("Detenido", color="#ff6b6b", font_weight="bold"),
            padding="0.35em 0.75em",
            border="1px solid #ff6b6b",
            border_radius="4px",
        ),
    )


def _service_action_button(label: str, icon: str, view: str) -> rx.Component:
    """Botón del grid de administración del foro."""
    return rx.button(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(label, font_weight="bold"),
            spacing="2",
            align_items="center",
        ),
        on_click=LaimWebState.forum_admin_open_view(view),
        class_name="crt-btn",
        width="100%",
        justify_content="flex-start",
        padding="0.85em 1em",
    )


def forum_service_hub() -> rx.Component:
    """Hub principal con grid de 12 acciones (como Radikal)."""
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon("library-big", size=28, color=COLORS["accent"]),
                padding="0.5em",
                border=f"1px solid {COLORS['border']}",
                border_radius="4px",
            ),
            rx.vstack(
                rx.heading("Servicio de foro", size="6", color=COLORS["title"]),
                rx.text(
                    LaimWebState.forum_service_detail,
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_SMALL,
                ),
                spacing="1",
                align_items="flex-start",
            ),
            rx.spacer(),
            _service_badge(),
            width="100%",
            align_items="center",
            margin_bottom="1em",
        ),
        rx.box(height="1px", width="100%", background=COLORS["border"], margin_bottom="1em"),
        rx.grid(
            _service_action_button("Configuración general", "settings", "config_general"),
            _service_action_button("Categorías", "folder", "categories"),
            _service_action_button("Subcategorías", "folder-tree", "subcategories"),
            _service_action_button("Prefijos de hilo", "tags", "prefixes"),
            _service_action_button("Moderadores", "user-cog", "moderators"),
            _service_action_button("Baneos activos", "ban", "bans"),
            _service_action_button("Permisos moderación", "shield", "permissions"),
            _service_action_button("Reglas automáticas", "list-checks", "word-rules"),
            _service_action_button("URLs autorizadas", "link", "allowed-urls"),
            _service_action_button("Visor de logs", "scroll-text", "logs"),
            _service_action_button("Estadísticas", "bar-chart-2", "stats"),
            rx.button(
                rx.hstack(
                    rx.icon("refresh-cw", size=18),
                    rx.text("Actualizar estado", font_weight="bold"),
                    spacing="2",
                    align_items="center",
                ),
                on_click=LaimWebState.forum_service_reload_config,
                class_name="crt-btn",
                width="100%",
                justify_content="flex-start",
                padding="0.85em 1em",
            ),
            columns="2",
            spacing="3",
            width="100%",
        ),
        class_name="crt-panel",
        padding="1.5em",
        width="100%",
    )


def forum_general_config_view() -> rx.Component:
    """Vista de configuración general del servicio. Solo lectura."""
    return rx.vstack(
        rx.heading("Configuración general del foro", size="6", color=COLORS["title"]),
        rx.text(
            "Estos datos salen del servicio que ya está en marcha. "
            "Desde el portal no se editan.",
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
        ),
        rx.box(
            rx.text(
                rx.fragment("Host API: ", LaimWebState.forum_cfg_host),
                color=COLORS["text"],
                font_size=FONT_SIZE_BODY,
            ),
            rx.text(
                rx.fragment("Puerto API: ", LaimWebState.forum_cfg_port),
                color=COLORS["text"],
                font_size=FONT_SIZE_BODY,
                margin_top="0.5em",
            ),
            rx.text(
                rx.fragment("Estado: ", LaimWebState.forum_cfg_estado),
                color=COLORS["text"],
                font_size=FONT_SIZE_BODY,
                margin_top="0.5em",
            ),
            rx.text(
                rx.fragment("Poll (segundos): ", LaimWebState.forum_cfg_poll),
                color=COLORS["text"],
                font_size=FONT_SIZE_BODY,
                margin_top="0.5em",
            ),
            rx.text(
                rx.fragment("Strikes URL: ", LaimWebState.forum_cfg_strikes),
                color=COLORS["text"],
                font_size=FONT_SIZE_BODY,
                margin_top="0.5em",
            ),
            rx.text(
                rx.fragment("Detalle: ", LaimWebState.forum_service_detail),
                color=COLORS["muted"],
                font_size=FONT_SIZE_SMALL,
                margin_top="0.75em",
            ),
            padding="1em",
            border=f"1px solid {COLORS['border']}",
            border_radius="4px",
            width="100%",
        ),
        rx.button(
            "Actualizar estado del servicio",
            on_click=LaimWebState.forum_service_reload_config,
            class_name="crt-btn",
        ),
        spacing="3",
        width="100%",
    )


def forum_bans_admin_view() -> rx.Component:
    """Lista de baneos activos."""
    return rx.vstack(
        rx.heading("Baneos activos", size="6", color=COLORS["title"]),
        rx.button(
            "Recargar baneos",
            on_click=LaimWebState.forum_load_admin_bans,
            class_name="crt-btn crt-btn-inline",
        ),
        rx.cond(
            LaimWebState.forum_mod_bans.length() == 0,
            rx.text("No hay baneos activos.", color=COLORS["muted"]),
            rx.foreach(
                LaimWebState.forum_mod_bans,
                lambda ban: rx.box(
                    rx.text(
                        rx.fragment(
                            "Usuario #",
                            ban["user_id"],
                            " · ",
                            ban["subcategory_id"],
                            " — ",
                            ban["motivo"],
                        ),
                        color=COLORS["text"],
                        font_size=FONT_SIZE_BODY,
                    ),
                    rx.text(
                        rx.fragment(
                            "Moderador: ",
                            ban["moderador_user_name"],
                            " · Expira: ",
                            ban["expires_at"],
                        ),
                        color=COLORS["muted"],
                        font_size=FONT_SIZE_SMALL,
                    ),
                    rx.button(
                        "Revocar",
                        on_click=LaimWebState.forum_revoke_ban(ban["id"]),
                        class_name="crt-btn crt-btn-inline",
                        margin_top="0.35em",
                    ),
                    padding="0.75em",
                    border=f"1px solid {COLORS['border']}",
                    border_radius="4px",
                    width="100%",
                    margin_bottom="0.5em",
                ),
            ),
        ),
        spacing="3",
        width="100%",
    )


def _log_date_modal(title: str, opened, value, on_apply, on_close) -> rx.Component:
    """Calendario nativo dentro de un modal."""
    return rx.cond(
        opened,
        rx.box(
            rx.vstack(
                rx.heading(title, size="4", color=COLORS["title"]),
                rx.input(
                    type="date",
                    value=value,
                    on_change=on_apply,
                    class_name="crt-input",
                    width="100%",
                ),
                rx.button("Cerrar", on_click=on_close, class_name="crt-btn"),
                class_name="crt-panel crt-modal-panel",
                style={"maxWidth": "420px", "width": "92vw", "padding": "1rem"},
                spacing="3",
            ),
            class_name="crt-modal-overlay",
        ),
        rx.fragment(),
    )


def forum_logs_admin_view() -> rx.Component:
    """Visor del log de moderación persistido, con filtros ALL por defecto."""
    return rx.vstack(
        rx.heading("Visor de logs", size="6", color=COLORS["title"]),
        rx.text(
            "Actividad de moderación guardada en base de datos. ALL no acota ese nivel.",
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
        ),
        rx.hstack(
            rx.vstack(
                rx.text("Categoría", color=COLORS["title"]),
                rx.select(
                    LaimWebState.forum_log_category_labels,
                    value=LaimWebState.forum_log_category,
                    on_change=LaimWebState.forum_log_set_category,
                    width="100%",
                ),
                width="100%",
            ),
            rx.vstack(
                rx.text("Subcategoría", color=COLORS["title"]),
                rx.select(
                    LaimWebState.forum_log_subcategory_labels,
                    value=LaimWebState.forum_log_subcategory,
                    on_change=LaimWebState.forum_log_set_subcategory,
                    width="100%",
                ),
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        rx.hstack(
            rx.button(
                rx.fragment("Desde: ", LaimWebState.forum_log_from_label),
                on_click=LaimWebState.forum_log_open_from,
                class_name="crt-btn",
            ),
            rx.button(
                rx.fragment("Hasta: ", LaimWebState.forum_log_to_label),
                on_click=LaimWebState.forum_log_open_to,
                class_name="crt-btn",
            ),
            spacing="3",
        ),
        _log_date_modal(
            "Desde",
            LaimWebState.forum_log_from_open,
            LaimWebState.forum_log_from,
            LaimWebState.forum_log_apply_from,
            LaimWebState.forum_log_close_from,
        ),
        _log_date_modal(
            "Hasta",
            LaimWebState.forum_log_to_open,
            LaimWebState.forum_log_to,
            LaimWebState.forum_log_apply_to,
            LaimWebState.forum_log_close_to,
        ),
        rx.cond(
            LaimWebState.forum_admin_logs_rows.length() == 0,
            rx.text("Sin entradas de log.", color=COLORS["muted"]),
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Fecha"),
                        rx.el.th("Categoría"),
                        rx.el.th("Subcategoría"),
                        rx.el.th("Tipo"),
                        rx.el.th("Quién"),
                        rx.el.th("Actividad"),
                    )
                ),
                rx.el.tbody(
                    rx.foreach(
                        LaimWebState.forum_admin_logs_rows,
                        lambda entry: rx.el.tr(
                            rx.el.td(entry["created_at"]),
                            rx.el.td(entry["category_name"]),
                            rx.el.td(entry["subcategory_name"]),
                            rx.el.td(entry["event_type"]),
                            rx.el.td(entry["actor"]),
                            rx.el.td(entry["message"]),
                        ),
                    )
                ),
                width="100%",
            ),
        ),
        spacing="3",
        width="100%",
    )


def forum_admin_view_router() -> rx.Component:
    """Enruta la vista admin según forum_admin_view."""
    return rx.cond(
        LaimWebState.forum_admin_view == "hub",
        forum_service_hub(),
        rx.cond(
            LaimWebState.forum_admin_view == "config_general",
            forum_general_config_view(),
            rx.cond(
                LaimWebState.forum_admin_view == "categories",
                forum_admin_panel(),
                rx.cond(
                    LaimWebState.forum_admin_view == "subcategories",
                    forum_admin_panel(),
                    rx.cond(
                        LaimWebState.forum_admin_view == "bans",
                        forum_bans_admin_view(),
                        rx.cond(
                            LaimWebState.forum_admin_view == "logs",
                            forum_logs_admin_view(),
                            rx.cond(
                                LaimWebState.forum_admin_view == "prefixes",
                                forum_admin_extended_panel(),
                                rx.cond(
                                    LaimWebState.forum_admin_view == "moderators",
                                    forum_admin_extended_panel(),
                                    rx.cond(
                                        LaimWebState.forum_admin_view == "permissions",
                                        forum_admin_extended_panel(),
                                        rx.cond(
                                            LaimWebState.forum_admin_view == "word-rules",
                                            forum_admin_extended_panel(),
                                            rx.cond(
                                                LaimWebState.forum_admin_view == "allowed-urls",
                                                forum_admin_extended_panel(),
                                                rx.cond(
                                                    LaimWebState.forum_admin_view == "avatars",
                                                    forum_admin_extended_panel(),
                                                    forum_service_hub(),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def forum_config_embedded() -> rx.Component:
    """Cuerpo del backoffice, compartido por /config-foro y Configuración → Foro LAIM."""
    return rx.vstack(
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
    )

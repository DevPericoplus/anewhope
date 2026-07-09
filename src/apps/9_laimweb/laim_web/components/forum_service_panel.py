"""Panel hub del servicio de foro LAIM (estilo Radikal + temática CRT)."""

from __future__ import annotations

import reflex as rx

from laim_web.components.crt_theme import COLORS, FONT_SIZE_BODY, FONT_SIZE_SMALL
from laim_web.components.forum_extended_ui import forum_admin_extended_panel
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
    """Vista de configuración general del servicio."""
    return rx.vstack(
        rx.heading("Configuración general del foro", size="6", color=COLORS["title"]),
        rx.text(
            "El foro LAIM se ejecuta como servicio independiente (daemon FastAPI). "
            "Host, puerto y límites operativos se definen en env.yaml del entorno activo.",
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
        ),
        rx.box(
            rx.text(
                rx.fragment("Estado: ", LaimWebState.forum_service_detail),
                color=COLORS["text"],
                font_size=FONT_SIZE_BODY,
            ),
            rx.text(
                rx.fragment(
                    "Servicio activo (config): ",
                    rx.cond(LaimWebState.forum_service_active, "Sí", "No"),
                ),
                color=COLORS["text"],
                font_size=FONT_SIZE_BODY,
                margin_top="0.5em",
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


def forum_logs_admin_view() -> rx.Component:
    """Visor global de logs de moderación."""
    return rx.vstack(
        rx.heading("Visor de logs", size="6", color=COLORS["title"]),
        rx.hstack(
            rx.input(
                placeholder="Subcategoría (opcional)",
                value=LaimWebState.forum_admin_logs_subcategory_id,
                on_change=LaimWebState.forum_admin_set_logs_subcategory_id,
                class_name="crt-input",
                width="100%",
            ),
            rx.button(
                "Cargar logs",
                on_click=LaimWebState.forum_load_admin_logs,
                class_name="crt-btn crt-btn-inline",
            ),
            spacing="3",
            width="100%",
        ),
        rx.cond(
            LaimWebState.forum_admin_logs_lines.length() == 0,
            rx.text("Sin entradas de log.", color=COLORS["muted"]),
            rx.foreach(
                LaimWebState.forum_admin_logs_lines,
                lambda entry: rx.text(
                    entry["line"],
                    color=COLORS["text"],
                    font_size=FONT_SIZE_SMALL,
                    font_family="monospace",
                ),
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

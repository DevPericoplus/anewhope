"""Perfil, moderación y administración extendida del foro LAIM."""

from __future__ import annotations

import reflex as rx

from laim_web.components.crt_theme import (
    COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FORUM_PROFILE_AVATAR_GRID_STYLE,
    FORUM_PROFILE_AVATAR_SECTION_STYLE,
    FORUM_PROFILE_AVATAR_TILE_STYLE,
    FORUM_PROFILE_PANEL_STYLE,
    FORUM_PROFILE_UPLOAD_BTN_STYLE,
    FORUM_PROFILE_UPLOAD_ROW_STYLE,
    FORUM_PROFILE_UPLOAD_SECTION_STYLE,
)
from laim_web.components.forum_ui import forum_error_banner
from laim_web.laim_state import LaimWebState


def _admin_tab_button(tab: str, label: str) -> rx.Component:
    return rx.button(
        label,
        on_click=LaimWebState.forum_admin_set_tab(tab),
        class_name="crt-btn crt-btn-inline",
        style=rx.cond(
            LaimWebState.forum_admin_tab == tab,
            {"font_weight": "bold", "border": f"1px solid {COLORS['accent']}"},
            {},
        ),
    )


def _forum_avatar_catalog_tile(item) -> rx.Component:
    """Celda del catálogo de avatares (sin estilos de botón ancho completo)."""
    return rx.box(
        rx.vstack(
            rx.cond(
                item["preview_url"] != "",
                rx.image(
                    src=item["preview_url"],
                    width="56px",
                    height="56px",
                    border_radius="50%",
                    alt=item["label"],
                ),
                rx.box(
                    width="56px",
                    height="56px",
                    border_radius="50%",
                    background_color=COLORS["panel_bg"],
                ),
            ),
            rx.text(
                item["label"],
                class_name="forum-profile-avatar-label",
                font_size=FONT_SIZE_SMALL,
            ),
            spacing="1",
            align_items="center",
        ),
        on_click=LaimWebState.forum_select_catalog_avatar(item["image_id"]),
        class_name="forum-profile-avatar-tile",
        style=rx.cond(
            LaimWebState.forum_profile_avatar_id == item["image_id"],
            {
                **FORUM_PROFILE_AVATAR_TILE_STYLE,
                "borderColor": "rgba(157, 255, 157, 0.85)",
                "boxShadow": "0 0 12px rgba(120, 255, 120, 0.35)",
                "background": "rgba(0, 50, 0, 0.55)",
            },
            FORUM_PROFILE_AVATAR_TILE_STYLE,
        ),
    )


def _forum_generative_avatar_tile(item) -> rx.Component:
    """Celda de una variante generativa (mármol, haz, pixel…)."""
    radius = rx.cond(LaimWebState.forum_avatar_square, "8px", "50%")
    return rx.box(
        rx.vstack(
            rx.image(
                src=item["preview_url"],
                width="64px",
                height="64px",
                border_radius=radius,
                alt=item["label"],
            ),
            rx.text(
                item["label"],
                class_name="forum-profile-avatar-label",
                font_size=FONT_SIZE_SMALL,
            ),
            spacing="1",
            align_items="center",
        ),
        on_click=LaimWebState.forum_select_generative_avatar(item["variant"]),
        class_name="forum-profile-avatar-tile forum-profile-generative-tile",
        style=rx.cond(
            LaimWebState.forum_avatar_variant == item["variant"],
            {
                **FORUM_PROFILE_AVATAR_TILE_STYLE,
                "width": "6.25rem",
                "maxWidth": "6.25rem",
                "borderColor": "rgba(157, 255, 157, 0.85)",
                "boxShadow": "0 0 12px rgba(120, 255, 120, 0.35)",
                "background": "rgba(0, 50, 0, 0.55)",
            },
            {
                **FORUM_PROFILE_AVATAR_TILE_STYLE,
                "width": "6.25rem",
                "maxWidth": "6.25rem",
            },
        ),
    )


def _forum_palette_chip(item) -> rx.Component:
    """Chip de paleta de color para el generador."""
    return rx.button(
        item["label"],
        on_click=LaimWebState.forum_set_avatar_palette(item["id"]),
        class_name="crt-btn crt-btn-inline forum-profile-palette-chip",
        style=rx.cond(
            LaimWebState.forum_avatar_palette_id == item["id"],
            {"font_weight": "bold", "border": f"1px solid {COLORS['accent']}"},
            {},
        ),
    )


def _forum_catalog_style_chip(item) -> rx.Component:
    """Chip de colección del catálogo ilustrado."""
    return rx.button(
        item["label"],
        on_click=LaimWebState.forum_set_avatar_catalog_style(item["id"]),
        class_name="crt-btn crt-btn-inline forum-profile-catalog-style-chip",
        style=rx.cond(
            LaimWebState.forum_avatar_catalog_style == item["id"],
            {"font_weight": "bold", "border": f"1px solid {COLORS['accent']}"},
            {},
        ),
    )


def forum_profile_panel() -> rx.Component:
    """Formulario de perfil de foro."""
    return rx.vstack(
        rx.heading("Perfil del foro", size="7", color=COLORS["title"]),
        rx.text(
            "Nombre visible, firma, avatar y preferencias de notificación.",
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
            margin_bottom="0.5em",
        ),
        forum_error_banner(),
        rx.cond(
            LaimWebState.forum_profile_message != "",
            rx.text(LaimWebState.forum_profile_message, color=COLORS["accent"]),
            rx.fragment(),
        ),
        rx.input(
            placeholder="Nombre visible en el foro",
            value=LaimWebState.forum_profile_display_name,
            on_change=LaimWebState.forum_set_profile_display_name,
            class_name="crt-input",
            width="100%",
        ),
        rx.text_area(
            placeholder="Firma (Markdown)",
            value=LaimWebState.forum_profile_signature,
            on_change=LaimWebState.forum_set_profile_signature,
            class_name="crt-input",
            width="100%",
            min_height="100px",
        ),
        rx.hstack(
            rx.checkbox(
                "Notificar menciones",
                checked=LaimWebState.forum_profile_notify_mentions,
                on_change=LaimWebState.forum_set_profile_notify_mentions,
            ),
            rx.checkbox(
                "Notificar respuestas",
                checked=LaimWebState.forum_profile_notify_replies,
                on_change=LaimWebState.forum_set_profile_notify_replies,
            ),
            spacing="4",
            flex_wrap="wrap",
        ),
        rx.box(
            rx.text("Avatar actual", class_name="crt-title", font_size="1em"),
            rx.cond(
                LaimWebState.forum_has_profile_avatar,
                rx.hstack(
                    rx.image(
                        src=LaimWebState.forum_profile_avatar_preview_url,
                        width="72px",
                        height="72px",
                        border_radius=rx.cond(
                            LaimWebState.forum_avatar_square, "8px", "50%"
                        ),
                        alt="Avatar del perfil",
                        border=f"2px solid {COLORS['accent']}",
                    ),
                    rx.vstack(
                        rx.text(
                            "Este avatar se muestra en tus mensajes del foro.",
                            color=COLORS["muted"],
                            font_size=FONT_SIZE_SMALL,
                        ),
                        spacing="1",
                        align_items="flex-start",
                    ),
                    spacing="4",
                    align_items="center",
                    flex_wrap="wrap",
                    margin_top="0.5em",
                ),
                rx.text(
                    "Aún no tienes avatar. Elige un estilo generativo, "
                    "uno del catálogo o sube una imagen.",
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_SMALL,
                    margin_top="0.5em",
                ),
            ),
            class_name="forum-profile-current-avatar-section",
            width="100%",
            margin_top="0.25em",
        ),
        rx.box(
            rx.text("Avatar generativo", class_name="crt-title", font_size="1em"),
            rx.text(
                "Se dibuja a partir de tu nombre visible (o el de sesión). "
                "Misma semilla, mismo retrato. Pulsa un estilo para usarlo.",
                color=COLORS["muted"],
                font_size=FONT_SIZE_SMALL,
                margin_top="0.35em",
            ),
            rx.text(
                LaimWebState.forum_avatar_seed,
                color=COLORS["accent"],
                font_size=FONT_SIZE_SMALL,
                margin_top="0.25em",
            ),
            rx.hstack(
                rx.foreach(
                    LaimWebState.forum_avatar_palette_options,
                    _forum_palette_chip,
                ),
                spacing="2",
                flex_wrap="wrap",
                class_name="forum-profile-palette-row",
                margin_top="0.65em",
            ),
            rx.hstack(
                rx.button(
                    "Circular",
                    on_click=LaimWebState.forum_set_avatar_square(False),
                    class_name="crt-btn crt-btn-inline",
                    style=rx.cond(
                        ~LaimWebState.forum_avatar_square,
                        {
                            "font_weight": "bold",
                            "border": f"1px solid {COLORS['accent']}",
                        },
                        {},
                    ),
                ),
                rx.button(
                    "Cuadrado",
                    on_click=LaimWebState.forum_set_avatar_square(True),
                    class_name="crt-btn crt-btn-inline",
                    style=rx.cond(
                        LaimWebState.forum_avatar_square,
                        {
                            "font_weight": "bold",
                            "border": f"1px solid {COLORS['accent']}",
                        },
                        {},
                    ),
                ),
                spacing="2",
                margin_top="0.5em",
            ),
            rx.flex(
                rx.foreach(
                    LaimWebState.forum_generative_avatar_tiles,
                    _forum_generative_avatar_tile,
                ),
                direction="row",
                wrap="wrap",
                spacing="3",
                class_name="forum-profile-avatar-grid",
                style=FORUM_PROFILE_AVATAR_GRID_STYLE,
                width="100%",
            ),
            class_name="forum-profile-avatar-section forum-profile-generative-section",
            style=FORUM_PROFILE_AVATAR_SECTION_STYLE,
            width="100%",
        ),
        rx.box(
            rx.text("Avatares del catálogo", class_name="crt-title", font_size="1em"),
            rx.text(
                "Retratos originales LAIM y colecciones ilustradas libres "
                "(alohe/avatars, MIT). Elige un estilo para ver sus retratos.",
                color=COLORS["muted"],
                font_size=FONT_SIZE_SMALL,
                margin_top="0.35em",
            ),
            rx.hstack(
                rx.foreach(
                    LaimWebState.forum_avatar_catalog_style_options,
                    _forum_catalog_style_chip,
                ),
                spacing="2",
                flex_wrap="wrap",
                class_name="forum-profile-catalog-style-row",
                margin_top="0.65em",
            ),
            rx.cond(
                LaimWebState.forum_has_avatar_catalog,
                rx.cond(
                    LaimWebState.forum_has_filtered_avatar_catalog,
                    rx.flex(
                        rx.foreach(
                            LaimWebState.forum_filtered_avatar_catalog,
                            _forum_avatar_catalog_tile,
                        ),
                        direction="row",
                        wrap="wrap",
                        spacing="3",
                        class_name="forum-profile-avatar-grid",
                        style=FORUM_PROFILE_AVATAR_GRID_STYLE,
                        width="100%",
                    ),
                    rx.text(
                        "Esta colección aún no está cargada en el servidor. "
                        "El administrador debe ejecutar el seed del catálogo.",
                        color=COLORS["muted"],
                        font_size=FONT_SIZE_SMALL,
                        margin_top="0.5em",
                    ),
                ),
                rx.text(
                    "No hay avatares en el catálogo. El administrador debe cargarlos "
                    "desde Config. foro → Avatares o ejecutar el seed del sistema.",
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_SMALL,
                    margin_top="0.5em",
                ),
            ),
            class_name="forum-profile-avatar-section",
            style=FORUM_PROFILE_AVATAR_SECTION_STYLE,
            width="100%",
        ),
        rx.box(
            rx.text(
                "Avatar personalizado",
                class_name="crt-title",
                font_size="1em",
                margin_bottom="0.75em",
            ),
            rx.hstack(
                rx.input(
                    type="file",
                    id="forum_avatar_file_input",
                    accept="image/png,image/jpeg,image/webp,image/gif",
                    style={"flex": "1 1 14rem", "minWidth": "0", "maxWidth": "100%"},
                ),
                rx.button(
                    "Subir avatar personal",
                    on_click=LaimWebState.forum_request_avatar_upload,
                    class_name="crt-btn crt-btn-inline forum-profile-upload-btn",
                    style=FORUM_PROFILE_UPLOAD_BTN_STYLE,
                ),
                spacing="3",
                align_items="center",
                flex_wrap="wrap",
                class_name="forum-profile-upload-row",
                style=FORUM_PROFILE_UPLOAD_ROW_STYLE,
                width="100%",
            ),
            class_name="forum-profile-upload-section",
            style=FORUM_PROFILE_UPLOAD_SECTION_STYLE,
            width="100%",
        ),
        rx.button(
            "Guardar perfil",
            on_click=LaimWebState.forum_save_profile,
            class_name="crt-btn forum-profile-save-btn",
            margin_top="0.5em",
        ),
        spacing="4",
        width="100%",
        class_name="forum-profile-panel",
        style=FORUM_PROFILE_PANEL_STYLE,
    )


def forum_moderation_panel() -> rx.Component:
    """Panel de moderación: logs y baneos."""
    return rx.vstack(
        rx.heading("Moderación del foro", size="7", color=COLORS["title"]),
        rx.text(
            rx.fragment(
                "Subcategoría activa: ",
                LaimWebState.forum_selected_subcategory_id,
                " (selecciónela en /foro si está vacía)",
            ),
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
        ),
        forum_error_banner(),
        rx.cond(
            LaimWebState.forum_mod_message != "",
            rx.text(LaimWebState.forum_mod_message, color=COLORS["accent"]),
            rx.fragment(),
        ),
        rx.button(
            "Actualizar logs",
            on_click=LaimWebState.forum_refresh_moderation,
            class_name="crt-btn crt-btn-inline",
        ),
        rx.text("Registrar baneo", class_name="crt-title", font_size="1em", margin_top="1em"),
        rx.input(
            placeholder="ID de usuario",
            value=LaimWebState.forum_ban_user_id_text,
            on_change=LaimWebState.forum_set_ban_user_id,
            class_name="crt-input",
        ),
        rx.input(
            placeholder="Motivo",
            value=LaimWebState.forum_ban_motivo,
            on_change=LaimWebState.forum_set_ban_motivo,
            class_name="crt-input",
        ),
        rx.input(
            placeholder="Expira (ISO, opcional)",
            value=LaimWebState.forum_ban_expires_at,
            on_change=LaimWebState.forum_set_ban_expires,
            class_name="crt-input",
        ),
        rx.button("Banear usuario", on_click=LaimWebState.forum_submit_ban, class_name="crt-btn"),
        rx.divider(color=COLORS["border"], margin_y="1em"),
        rx.text("Logs de moderación", class_name="crt-title", font_size="1em"),
        rx.foreach(
            LaimWebState.forum_mod_logs,
            lambda log: rx.box(
                rx.text(
                    rx.fragment(log["event_type"], " — ", log["message"]),
                    font_size=FONT_SIZE_BODY,
                    color=COLORS["text"],
                ),
                rx.text(
                    log["created_at"],
                    font_size=FONT_SIZE_SMALL,
                    color=COLORS["muted"],
                ),
                padding="0.5em 0",
                border_bottom=f"1px solid {COLORS['border']}",
                width="100%",
            ),
        ),
        spacing="2",
        width="100%",
    )


def _forum_stats_metric(label: str, value) -> rx.Component:
    return rx.vstack(
        rx.text(label, color=COLORS["muted"], font_size=FONT_SIZE_SMALL),
        rx.text(value, color=COLORS["accent"], font_size="1.2em", font_weight="bold"),
        spacing="1",
        align_items="center",
        min_width="120px",
    )


def forum_stats_dialog() -> rx.Component:
    """Diálogo con estadísticas globales del foro (solo admin)."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Estadísticas del foro", color=COLORS["title"]),
            rx.cond(
                LaimWebState.forum_stats_loading,
                rx.text("Cargando estadísticas...", color=COLORS["muted"]),
                rx.cond(
                    LaimWebState.forum_stats_message != "",
                    rx.text(LaimWebState.forum_stats_message, color=COLORS["accent"]),
                    rx.vstack(
                        rx.hstack(
                            _forum_stats_metric(
                                "Categorías", LaimWebState.forum_stats_categorias
                            ),
                            _forum_stats_metric(
                                "Subcategorías", LaimWebState.forum_stats_subcategorias
                            ),
                            _forum_stats_metric("Hilos", LaimWebState.forum_stats_hilos),
                            _forum_stats_metric(
                                "Respuestas", LaimWebState.forum_stats_respuestas
                            ),
                            flex_wrap="wrap",
                            spacing="4",
                            width="100%",
                        ),
                        rx.hstack(
                            _forum_stats_metric(
                                "Valoraciones", LaimWebState.forum_stats_valoraciones
                            ),
                            _forum_stats_metric(
                                "Promedio ★",
                                LaimWebState.forum_stats_valoracion_promedio_text,
                            ),
                            _forum_stats_metric(
                                "Usuarios activos",
                                LaimWebState.forum_stats_usuarios_activos,
                            ),
                            _forum_stats_metric(
                                "Baneos activos",
                                LaimWebState.forum_stats_baneos_activos,
                            ),
                            flex_wrap="wrap",
                            spacing="4",
                            width="100%",
                        ),
                        rx.hstack(
                            _forum_stats_metric(
                                "Infracciones hoy",
                                LaimWebState.forum_stats_infracciones_hoy,
                            ),
                            _forum_stats_metric(
                                "Adjuntos", LaimWebState.forum_stats_adjuntos
                            ),
                            flex_wrap="wrap",
                            spacing="4",
                            width="100%",
                        ),
                        rx.text(
                            "Actividad por subcategoría",
                            class_name="crt-title",
                            font_size="1em",
                            margin_top="1em",
                        ),
                        rx.cond(
                            LaimWebState.forum_stats_subcategory_rows.length() > 0,
                            rx.vstack(
                                rx.foreach(
                                    LaimWebState.forum_stats_subcategory_rows,
                                    lambda row: rx.hstack(
                                        rx.text(
                                            rx.fragment(
                                                row["category_name"],
                                                " / ",
                                                row["subcategory_name"],
                                            ),
                                            font_size=FONT_SIZE_BODY,
                                            width="55%",
                                        ),
                                        rx.text(
                                            rx.fragment(
                                                row["hilos"],
                                                " hilos · ",
                                                row["respuestas"],
                                                " resp.",
                                            ),
                                            font_size=FONT_SIZE_SMALL,
                                            color=COLORS["muted"],
                                            width="45%",
                                        ),
                                        width="100%",
                                    ),
                                ),
                                spacing="1",
                                width="100%",
                            ),
                            rx.text(
                                "Sin subcategorías registradas.",
                                color=COLORS["muted"],
                                font_size=FONT_SIZE_SMALL,
                            ),
                        ),
                        rx.text(
                            "Top 10 reputación",
                            class_name="crt-title",
                            font_size="1em",
                            margin_top="1em",
                        ),
                        rx.cond(
                            LaimWebState.forum_stats_top_users.length() > 0,
                            rx.vstack(
                                rx.foreach(
                                    LaimWebState.forum_stats_top_users,
                                    lambda user: rx.hstack(
                                        rx.text(
                                            user["display_name"],
                                            font_size=FONT_SIZE_BODY,
                                            width="50%",
                                        ),
                                        rx.text(
                                            rx.fragment(
                                                user["reputation_avg"],
                                                " ★ (",
                                                user["reputation_votes"],
                                                " votos)",
                                            ),
                                            font_size=FONT_SIZE_SMALL,
                                            color=COLORS["muted"],
                                            width="50%",
                                        ),
                                        width="100%",
                                    ),
                                ),
                                spacing="1",
                                width="100%",
                            ),
                            rx.text(
                                "Aún no hay valoraciones de reputación.",
                                color=COLORS["muted"],
                                font_size=FONT_SIZE_SMALL,
                            ),
                        ),
                        spacing="3",
                        width="100%",
                    ),
                ),
            ),
            rx.dialog.close(
                rx.button("Cerrar", class_name="crt-btn crt-btn-inline", margin_top="1em"),
            ),
            background=COLORS["panel_bg"],
            border=f"1px solid {COLORS['border']}",
            max_width="720px",
            max_height="85vh",
            overflow_y="auto",
        ),
        open=LaimWebState.forum_stats_dialog_open,
        on_open_change=LaimWebState.forum_on_stats_dialog_change,
    )


def forum_admin_extended_panel() -> rx.Component:
    """Panel admin con pestañas."""
    return rx.vstack(
        rx.heading("Configuración avanzada", size="6", color=COLORS["title"]),
        rx.hstack(
            _admin_tab_button("settings", "Ajustes"),
            _admin_tab_button("prefixes", "Prefijos"),
            _admin_tab_button("word-rules", "Palabras"),
            _admin_tab_button("allowed-urls", "URLs"),
            _admin_tab_button("moderators", "Moderadores"),
            _admin_tab_button("avatars", "Avatares"),
            flex_wrap="wrap",
            spacing="2",
            margin_bottom="1em",
        ),
        rx.cond(
            LaimWebState.forum_admin_message != "",
            rx.text(LaimWebState.forum_admin_message, color=COLORS["accent"]),
            rx.fragment(),
        ),
        rx.cond(
            LaimWebState.forum_admin_tab == "settings",
            rx.vstack(
                rx.checkbox(
                    "Anunciar ban en log",
                    checked=LaimWebState.forum_admin_settings_announce_ban,
                    on_change=LaimWebState.forum_admin_set_announce_ban,
                ),
                rx.text_area(
                    placeholder="Plantilla ban",
                    value=LaimWebState.forum_admin_settings_ban_template,
                    on_change=LaimWebState.forum_admin_set_ban_template,
                    class_name="crt-input",
                    width="100%",
                ),
                rx.text_area(
                    placeholder="Plantilla eliminación",
                    value=LaimWebState.forum_admin_settings_delete_template,
                    on_change=LaimWebState.forum_admin_set_delete_template,
                    class_name="crt-input",
                    width="100%",
                ),
                rx.button(
                    "Guardar ajustes",
                    on_click=LaimWebState.forum_admin_save_settings,
                    class_name="crt-btn",
                ),
                spacing="2",
                width="100%",
            ),
            rx.cond(
                LaimWebState.forum_admin_tab == "prefixes",
                rx.vstack(
                    rx.input(
                        placeholder="ID prefijo",
                        value=LaimWebState.forum_admin_prefix_id,
                        on_change=LaimWebState.forum_admin_set_prefix_id,
                        class_name="crt-input",
                    ),
                    rx.input(
                        placeholder="Texto",
                        value=LaimWebState.forum_admin_prefix_text,
                        on_change=LaimWebState.forum_admin_set_prefix_text,
                        class_name="crt-input",
                    ),
                    rx.input(
                        placeholder="Color (green, blue...)",
                        value=LaimWebState.forum_admin_prefix_color,
                        on_change=LaimWebState.forum_admin_set_prefix_color,
                        class_name="crt-input",
                    ),
                    rx.button(
                        "Guardar prefijo",
                        on_click=LaimWebState.forum_admin_save_prefix,
                        class_name="crt-btn",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.cond(
                    LaimWebState.forum_admin_tab == "word-rules",
                    rx.vstack(
                        rx.input(
                            placeholder="Palabra",
                            value=LaimWebState.forum_admin_word_palabra,
                            on_change=LaimWebState.forum_admin_set_word_palabra,
                            class_name="crt-input",
                        ),
                        rx.select(
                            LaimWebState.forum_rule_action_options,
                            value=LaimWebState.forum_admin_word_accion,
                            on_change=LaimWebState.forum_admin_set_word_accion,
                            class_name="crt-input",
                            width="100%",
                        ),
                        rx.input(
                            placeholder="Mensaje al usuario",
                            value=LaimWebState.forum_admin_word_mensaje,
                            on_change=LaimWebState.forum_admin_set_word_mensaje,
                            class_name="crt-input",
                        ),
                        rx.button(
                            "Añadir regla",
                            on_click=LaimWebState.forum_admin_save_word_rule,
                            class_name="crt-btn",
                        ),
                        rx.foreach(
                            LaimWebState.forum_word_rules,
                            lambda rule: rx.hstack(
                                rx.text(
                                    rx.fragment(rule["palabra"], " → ", rule["accion"]),
                                    font_size=FONT_SIZE_BODY,
                                ),
                                rx.button(
                                    "Eliminar",
                                    on_click=LaimWebState.forum_admin_delete_word_rule(
                                        rule["id"]
                                    ),
                                    class_name="crt-btn crt-btn-inline",
                                ),
                                width="100%",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.cond(
                        LaimWebState.forum_admin_tab == "allowed-urls",
                        rx.vstack(
                            rx.input(
                                placeholder="dominio.com",
                                value=LaimWebState.forum_admin_url_dominio,
                                on_change=LaimWebState.forum_admin_set_url_dominio,
                                class_name="crt-input",
                            ),
                            rx.input(
                                placeholder="Descripción",
                                value=LaimWebState.forum_admin_url_descripcion,
                                on_change=LaimWebState.forum_admin_set_url_descripcion,
                                class_name="crt-input",
                            ),
                            rx.button(
                                "Añadir dominio",
                                on_click=LaimWebState.forum_admin_save_allowed_url,
                                class_name="crt-btn",
                            ),
                            rx.foreach(
                                LaimWebState.forum_allowed_urls,
                                lambda url: rx.hstack(
                                    rx.text(url["dominio"], font_size=FONT_SIZE_BODY),
                                    rx.button(
                                        "Eliminar",
                                        on_click=LaimWebState.forum_admin_delete_allowed_url(
                                            url["id"]
                                        ),
                                        class_name="crt-btn crt-btn-inline",
                                    ),
                                    width="100%",
                                ),
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        rx.cond(
                            LaimWebState.forum_admin_tab == "moderators",
                            rx.vstack(
                                rx.input(
                                    placeholder="User ID",
                                    value=LaimWebState.forum_admin_mod_user_id_text,
                                    on_change=LaimWebState.forum_admin_set_mod_user_id,
                                    class_name="crt-input",
                                ),
                                rx.input(
                                    placeholder="Nombre usuario",
                                    value=LaimWebState.forum_admin_mod_user_name,
                                    on_change=LaimWebState.forum_admin_set_mod_user_name,
                                    class_name="crt-input",
                                ),
                                rx.input(
                                    placeholder="Subcategoría ID",
                                    value=LaimWebState.forum_admin_mod_subcategory_id,
                                    on_change=LaimWebState.forum_admin_set_mod_subcategory_id,
                                    class_name="crt-input",
                                ),
                                rx.button(
                                    "Asignar moderador",
                                    on_click=LaimWebState.forum_admin_assign_moderator,
                                    class_name="crt-btn",
                                ),
                                rx.foreach(
                                    LaimWebState.forum_moderators,
                                    lambda mod: rx.hstack(
                                        rx.text(
                                            rx.fragment(
                                                mod["user_name"],
                                                " @ ",
                                                mod["subcategory_id"],
                                            ),
                                            font_size=FONT_SIZE_BODY,
                                        ),
                                        rx.button(
                                            "Desactivar",
                                            on_click=LaimWebState.forum_admin_deactivate_moderator(
                                                mod["id"]
                                            ),
                                            class_name="crt-btn crt-btn-inline",
                                        ),
                                        width="100%",
                                    ),
                                ),
                                spacing="2",
                                width="100%",
                            ),
                            rx.cond(
                                LaimWebState.forum_admin_tab == "avatars",
                                rx.vstack(
                                    rx.input(
                                        placeholder="Image ID (subida previamente)",
                                        value=LaimWebState.forum_admin_avatar_image_id_text,
                                        on_change=LaimWebState.forum_admin_set_avatar_image_id,
                                        class_name="crt-input",
                                    ),
                                    rx.input(
                                        placeholder="Etiqueta",
                                        value=LaimWebState.forum_admin_avatar_label,
                                        on_change=LaimWebState.forum_admin_set_avatar_label,
                                        class_name="crt-input",
                                    ),
                                    rx.button(
                                        "Añadir al catálogo",
                                        on_click=LaimWebState.forum_admin_add_catalog_avatar,
                                        class_name="crt-btn",
                                    ),
                                    spacing="2",
                                    width="100%",
                                ),
                                rx.fragment(),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        spacing="3",
        width="100%",
    )

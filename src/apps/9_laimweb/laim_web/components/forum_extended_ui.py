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


def _forum_stats_metric(label: str, value, note=None) -> rx.Component:
    children = [
        rx.text(label, color=COLORS["muted"], font_size=FONT_SIZE_SMALL),
        rx.text(value, color=COLORS["accent"], font_size="1.2em", font_weight="bold"),
    ]
    if note is not None:
        children.append(note)
    return rx.vstack(
        *children,
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
                                "Subcategorías",
                                LaimWebState.forum_stats_subcategorias,
                                # El selector del foro solo ofrece las activas.
                                rx.cond(
                                    LaimWebState.forum_stats_subcategorias_nota != "",
                                    rx.text(
                                        LaimWebState.forum_stats_subcategorias_nota,
                                        color=COLORS["muted"],
                                        font_size=FONT_SIZE_SMALL,
                                    ),
                                ),
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
                                                row["estado_sufijo"],
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
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Confirmar", color=COLORS["title"]),
                rx.text(LaimWebState.forum_confirm_prompt),
                rx.hstack(
                    rx.button(
                        rx.cond(
                            LaimWebState.forum_confirm_kind == "moderator",
                            "Desactivar",
                            rx.cond(
                                LaimWebState.forum_confirm_kind == "word-off",
                                "Desactivar",
                                "Eliminar",
                            ),
                        ),
                        on_click=LaimWebState.forum_accept_confirm,
                        class_name="crt-btn",
                    ),
                    rx.button(
                        "Cancelar",
                        on_click=LaimWebState.forum_cancel_confirm,
                        class_name="crt-btn",
                    ),
                    spacing="2",
                ),
                background=COLORS["panel_bg"],
                border=f"1px solid {COLORS['border']}",
            ),
            open=LaimWebState.forum_confirm_open,
            on_open_change=LaimWebState.forum_cancel_confirm,
        ),
        rx.cond(
            LaimWebState.forum_admin_tab == "settings",
            rx.vstack(
                rx.text(
                    "Cada fila es un ajuste guardado. Modificar cambia el valor y lo guarda. Restablecer vuelve al texto de semilla. Marcadores: {usuario}, {subcategoria}, {motivo}.",
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_SMALL,
                ),
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Ajuste"),
                            rx.el.th("Valor"),
                            rx.el.th("Acciones"),
                        )
                    ),
                    rx.el.tbody(
                        rx.el.tr(
                            rx.el.td("Anunciar ban en el log"),
                            rx.el.td(
                                rx.checkbox(
                                    "Activo",
                                    checked=LaimWebState.forum_admin_settings_announce_ban,
                                    on_change=LaimWebState.forum_admin_set_announce_ban,
                                )
                            ),
                            rx.el.td(
                                rx.hstack(
                                    rx.button(
                                        "Modificar",
                                        on_click=LaimWebState.forum_admin_save_settings,
                                        class_name="crt-btn crt-btn-inline",
                                    ),
                                    rx.button(
                                        "Restablecer",
                                        on_click=LaimWebState.forum_admin_clear_setting("announce"),
                                        class_name="crt-btn crt-btn-inline",
                                    ),
                                    spacing="2",
                                )
                            ),
                        ),
                        rx.el.tr(
                            rx.el.td("Plantilla del mensaje de ban"),
                            rx.el.td(
                                rx.text_area(
                                    placeholder="Texto que se publica al banear",
                                    value=LaimWebState.forum_admin_settings_ban_template,
                                    on_change=LaimWebState.forum_admin_set_ban_template,
                                    class_name="crt-input",
                                    width="100%",
                                )
                            ),
                            rx.el.td(
                                rx.hstack(
                                    rx.button(
                                        "Modificar",
                                        on_click=LaimWebState.forum_admin_save_settings,
                                        class_name="crt-btn crt-btn-inline",
                                    ),
                                    rx.button(
                                        "Restablecer",
                                        on_click=LaimWebState.forum_admin_clear_setting("ban"),
                                        class_name="crt-btn crt-btn-inline",
                                    ),
                                    spacing="2",
                                )
                            ),
                        ),
                        rx.el.tr(
                            rx.el.td("Plantilla del mensaje de eliminación"),
                            rx.el.td(
                                rx.text_area(
                                    placeholder="Texto que se publica al eliminar",
                                    value=LaimWebState.forum_admin_settings_delete_template,
                                    on_change=LaimWebState.forum_admin_set_delete_template,
                                    class_name="crt-input",
                                    width="100%",
                                )
                            ),
                            rx.el.td(
                                rx.hstack(
                                    rx.button(
                                        "Modificar",
                                        on_click=LaimWebState.forum_admin_save_settings,
                                        class_name="crt-btn crt-btn-inline",
                                    ),
                                    rx.button(
                                        "Restablecer",
                                        on_click=LaimWebState.forum_admin_clear_setting("delete"),
                                        class_name="crt-btn crt-btn-inline",
                                    ),
                                    spacing="2",
                                )
                            ),
                        ),
                    ),
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            rx.cond(
                LaimWebState.forum_admin_tab == "prefixes",
                rx.vstack(
                    rx.text(
                        "Un prefijo es la etiqueta que va delante del título del hilo, por ejemplo [Duda]. El color es el nombre del esquema: green, blue, red.",
                        color=COLORS["muted"],
                        font_size=FONT_SIZE_SMALL,
                    ),
                    rx.text("Identificador", color=COLORS["title"]),
                    rx.input(
                        placeholder="ID prefijo",
                        value=LaimWebState.forum_admin_prefix_id,
                        on_change=LaimWebState.forum_admin_set_prefix_id,
                        disabled=LaimWebState.forum_admin_prefix_editing,
                        class_name="crt-input",
                    ),
                    rx.text("Texto que ve el usuario", color=COLORS["title"]),
                    rx.input(
                        placeholder="Texto",
                        value=LaimWebState.forum_admin_prefix_text,
                        on_change=LaimWebState.forum_admin_set_prefix_text,
                        class_name="crt-input",
                    ),
                    rx.text("Color del esquema", color=COLORS["title"]),
                    rx.select(
                        ["green", "blue", "red", "amber", "gray", "orange", "purple"],
                        value=LaimWebState.forum_admin_prefix_color,
                        on_change=LaimWebState.forum_admin_set_prefix_color,
                        width="100%",
                    ),
                    rx.checkbox(
                        "Activo",
                        checked=LaimWebState.forum_admin_prefix_activo,
                        on_change=LaimWebState.forum_admin_set_prefix_activo,
                    ),
                    rx.hstack(
                        rx.button(
                            "Guardar prefijo",
                            on_click=LaimWebState.forum_admin_save_prefix,
                            class_name="crt-btn",
                        ),
                        rx.button(
                            "Nuevo prefijo",
                            on_click=LaimWebState.forum_admin_new_prefix,
                            class_name="crt-btn",
                        ),
                        spacing="2",
                    ),
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("ID"),
                                rx.el.th("Texto"),
                                rx.el.th("Color"),
                                rx.el.th("Estado"),
                                rx.el.th("Acciones"),
                            )
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                LaimWebState.forum_admin_prefixes,
                                lambda item: rx.el.tr(
                                    rx.el.td(item["id"]),
                                    rx.el.td(item["texto"]),
                                    rx.el.td(
                                        rx.badge(
                                            item["color_scheme"],
                                            color_scheme=item["color_scheme"],
                                        )
                                    ),
                                    rx.el.td(rx.cond(item["activo"], "Activo", "Inactivo")),
                                    rx.el.td(
                                        rx.hstack(
                                            rx.button(
                                                "Modificar",
                                                on_click=LaimWebState.forum_admin_edit_prefix(item["id"]),
                                                class_name="crt-btn crt-btn-inline",
                                            ),
                                            rx.button(
                                                "Eliminar",
                                                on_click=LaimWebState.forum_ask_confirm(
                                                    "prefix", item["id"], item["texto"]
                                                ),
                                                class_name="crt-btn crt-btn-inline",
                                            ),
                                            spacing="2",
                                        )
                                    ),
                                ),
                            )
                        ),
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.cond(
                    LaimWebState.forum_admin_tab == "word-rules",
                    rx.vstack(
                        rx.el.label("Palabra", color=COLORS["title"]),
                        rx.input(
                            placeholder="ejemplo",
                            value=LaimWebState.forum_admin_word_palabra,
                            on_change=LaimWebState.forum_admin_set_word_palabra,
                            class_name="crt-input",
                        ),
                        rx.text(
                            "Texto que la regla busca en el mensaje.",
                            color=COLORS["muted"],
                            font_size=FONT_SIZE_SMALL,
                        ),
                        rx.el.label("Acción", color=COLORS["title"]),
                        rx.select(
                            LaimWebState.forum_rule_action_options,
                            value=LaimWebState.forum_admin_word_accion,
                            on_change=LaimWebState.forum_admin_set_word_accion,
                            class_name="crt-input",
                            width="100%",
                        ),
                        rx.text(
                            "Qué hace el foro cuando aparece la palabra.",
                            color=COLORS["muted"],
                            font_size=FONT_SIZE_SMALL,
                        ),
                        rx.el.label("Mensaje al usuario", color=COLORS["title"]),
                        rx.input(
                            placeholder="Esa palabra no está permitida",
                            value=LaimWebState.forum_admin_word_mensaje,
                            on_change=LaimWebState.forum_admin_set_word_mensaje,
                            class_name="crt-input",
                        ),
                        rx.checkbox(
                            "Activa",
                            checked=LaimWebState.forum_admin_word_activo,
                            on_change=LaimWebState.forum_admin_set_word_activo,
                        ),
                        rx.hstack(
                            rx.button(
                                rx.cond(
                                    LaimWebState.forum_admin_word_rule_id > 0,
                                    "Guardar regla",
                                    "Añadir regla",
                                ),
                                on_click=LaimWebState.forum_admin_save_word_rule,
                                class_name="crt-btn",
                            ),
                            rx.cond(
                                LaimWebState.forum_admin_word_rule_id > 0,
                                rx.button(
                                    "Cancelar",
                                    on_click=LaimWebState.forum_admin_cancel_word_rule,
                                    class_name="crt-btn",
                                ),
                                rx.fragment(),
                            ),
                            spacing="2",
                        ),
                        rx.foreach(
                            LaimWebState.forum_word_rules,
                            lambda rule: rx.hstack(
                                rx.text(
                                    rx.fragment(rule["palabra"], " → ", rule["accion"]),
                                    font_size=FONT_SIZE_BODY,
                                ),
                                rx.button(
                                    "Editar",
                                    on_click=LaimWebState.forum_admin_edit_word_rule(
                                        rule["id"]
                                    ),
                                    class_name="crt-btn crt-btn-inline",
                                ),
                                rx.button(
                                    rx.cond(rule["activo"], "Desactivar", "Activar"),
                                    on_click=LaimWebState.forum_admin_ask_word_active(
                                        rule["id"], rule["palabra"], rule["activo"]
                                    ),
                                    class_name="crt-btn crt-btn-inline",
                                ),
                                rx.button(
                                    "Eliminar",
                                    on_click=LaimWebState.forum_ask_confirm(
                                        "word", rule["id"], rule["palabra"]
                                    ),
                                    class_name="crt-btn crt-btn-inline",
                                ),
                                width="100%",
                                align_items="center",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.cond(
                        LaimWebState.forum_admin_tab == "allowed-urls",
                        rx.vstack(
                            rx.text(
                                "Dominio que un mensaje puede enlazar, sin https://. Guardar el mismo dominio actualiza su descripción.",
                                color=COLORS["muted"],
                                font_size=FONT_SIZE_SMALL,
                            ),
                            rx.text("Dominio", color=COLORS["title"]),
                            rx.input(
                                placeholder="dominio.com",
                                value=LaimWebState.forum_admin_url_dominio,
                                on_change=LaimWebState.forum_admin_set_url_dominio,
                                class_name="crt-input",
                            ),
                            rx.text("Descripción", color=COLORS["title"]),
                            rx.input(
                                placeholder="Para qué se autoriza",
                                value=LaimWebState.forum_admin_url_descripcion,
                                on_change=LaimWebState.forum_admin_set_url_descripcion,
                                class_name="crt-input",
                            ),
                            rx.cond(
                                LaimWebState.forum_admin_url_id > 0,
                                rx.text(
                                    rx.fragment(
                                        "Editando dominio ",
                                        LaimWebState.forum_admin_url_dominio,
                                    ),
                                    color=COLORS["muted"],
                                    font_size=FONT_SIZE_SMALL,
                                ),
                                rx.fragment(),
                            ),
                            rx.hstack(
                                rx.button(
                                    "Guardar dominio",
                                    on_click=LaimWebState.forum_admin_save_allowed_url,
                                    class_name="crt-btn",
                                ),
                                rx.cond(
                                    LaimWebState.forum_admin_url_id > 0,
                                    rx.button(
                                        "Cancelar",
                                        on_click=LaimWebState.forum_admin_cancel_allowed_url,
                                        class_name="crt-btn",
                                    ),
                                    rx.fragment(),
                                ),
                                spacing="2",
                            ),
                            rx.el.table(
                                rx.el.thead(
                                    rx.el.tr(
                                        rx.el.th("Dominio"),
                                        rx.el.th("Descripción"),
                                        rx.el.th("Acciones"),
                                    )
                                ),
                                rx.el.tbody(
                                    rx.foreach(
                                        LaimWebState.forum_allowed_urls,
                                        lambda url: rx.el.tr(
                                            rx.el.td(url["dominio"]),
                                            rx.el.td(url["descripcion"]),
                                            rx.el.td(
                                                rx.hstack(
                                                    rx.button(
                                                        "Modificar",
                                                        on_click=LaimWebState.forum_admin_edit_allowed_url(
                                                            url["id"],
                                                            url["dominio"],
                                                            url["descripcion"],
                                                        ),
                                                        class_name="crt-btn crt-btn-inline",
                                                    ),
                                                    rx.button(
                                                        "Eliminar",
                                                        on_click=LaimWebState.forum_ask_confirm(
                                                            "url", url["id"], url["dominio"]
                                                        ),
                                                        class_name="crt-btn crt-btn-inline",
                                                    ),
                                                    spacing="2",
                                                )
                                            ),
                                        ),
                                    )
                                ),
                                width="100%",
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        rx.cond(
                            LaimWebState.forum_admin_tab == "moderators",
                            rx.vstack(
                                rx.text("Usuario", color=COLORS["title"]),
                                rx.select(
                                    LaimWebState.forum_mod_user_labels,
                                    value=LaimWebState.forum_mod_user_label,
                                    on_change=LaimWebState.forum_admin_pick_mod_user,
                                    placeholder="Seleccione usuario",
                                    width="100%",
                                ),
                                rx.text("Categoría", color=COLORS["title"]),
                                rx.select(
                                    LaimWebState.forum_mod_category_labels,
                                    value=LaimWebState.forum_mod_category_label,
                                    on_change=LaimWebState.forum_admin_pick_mod_category,
                                    placeholder="Seleccione categoría",
                                    width="100%",
                                ),
                                rx.text("Subcategoría", color=COLORS["title"]),
                                rx.select(
                                    LaimWebState.forum_mod_subcategory_labels,
                                    value=LaimWebState.forum_mod_subcategory_label,
                                    on_change=LaimWebState.forum_admin_pick_mod_subcategory,
                                    placeholder="Seleccione subcategoría",
                                    width="100%",
                                ),
                                rx.button(
                                    "Asignar moderador",
                                    on_click=LaimWebState.forum_admin_assign_moderator,
                                    class_name="crt-btn",
                                ),
                                rx.el.table(
                                    rx.el.thead(
                                        rx.el.tr(
                                            rx.el.th("Usuario"),
                                            rx.el.th("Categoría"),
                                            rx.el.th("Subcategoría"),
                                            rx.el.th("Estado"),
                                            rx.el.th("Acciones"),
                                        )
                                    ),
                                    rx.el.tbody(
                                        rx.foreach(
                                            LaimWebState.forum_moderators,
                                            lambda mod: rx.el.tr(
                                                rx.el.td(mod["user_name"]),
                                                rx.el.td(mod["category_name"]),
                                                rx.el.td(mod["subcategory_name"]),
                                                rx.el.td(mod["estado"]),
                                                rx.el.td(
                                                    rx.cond(
                                                        mod["activo"],
                                                        rx.button(
                                                            "Desactivar",
                                                            on_click=LaimWebState.forum_ask_confirm(
                                                                "moderator", mod["id"], mod["user_name"]
                                                            ),
                                                            class_name="crt-btn crt-btn-inline",
                                                        ),
                                                        rx.button(
                                                            "Activar",
                                                            on_click=LaimWebState.forum_admin_reactivate_moderator(
                                                                mod["user_id"],
                                                                mod["user_name"],
                                                                mod["subcategory_id"],
                                                            ),
                                                            class_name="crt-btn crt-btn-inline",
                                                        ),
                                                    )
                                                ),
                                            ),
                                        )
                                    ),
                                    width="100%",
                                ),
                                spacing="2",
                                width="100%",
                            ),
                            rx.cond(
                                LaimWebState.forum_admin_tab == "avatars",
                                rx.vstack(
                                    rx.text(
                                        "Sube la imagen desde aquí. La miniatura y la etiqueta quedan en el catálogo; puedes ordenarla, marcarla por defecto, desactivarla o quitarla.",
                                        color=COLORS["muted"],
                                        font_size=FONT_SIZE_SMALL,
                                    ),
                                    rx.el.label("Etiqueta", color=COLORS["title"]),
                                    rx.input(
                                        placeholder="Retrato azul",
                                        value=LaimWebState.forum_admin_avatar_label,
                                        on_change=LaimWebState.forum_admin_set_avatar_label,
                                        class_name="crt-input",
                                    ),
                                    rx.text(
                                        "Nombre que verá el usuario al elegir el avatar.",
                                        color=COLORS["muted"],
                                        font_size=FONT_SIZE_SMALL,
                                    ),
                                    rx.upload(
                                        rx.text(
                                            "Elegir imagen (PNG, JPG, WEBP o GIF).",
                                            font_size=FONT_SIZE_SMALL,
                                            color=COLORS["muted"],
                                        ),
                                        id="forum_catalog_avatar_upload",
                                        accept={
                                            "image/png": [".png"],
                                            "image/jpeg": [".jpg", ".jpeg"],
                                            "image/webp": [".webp"],
                                            "image/gif": [".gif"],
                                        },
                                        max_files=1,
                                        border=f"1px dashed {COLORS['border']}",
                                        padding="0.75em",
                                        width="100%",
                                    ),
                                    rx.cond(
                                        LaimWebState.forum_admin_avatar_preview != "",
                                        rx.image(
                                            src=LaimWebState.forum_admin_avatar_preview,
                                            width="64px",
                                            height="64px",
                                            alt="Vista previa",
                                        ),
                                        rx.fragment(),
                                    ),
                                    rx.button(
                                        "Subir y añadir al catálogo",
                                        on_click=LaimWebState.forum_admin_upload_catalog_avatar(
                                            rx.upload_files(upload_id="forum_catalog_avatar_upload")
                                        ),
                                        class_name="crt-btn",
                                    ),
                                    rx.hstack(
                                        rx.button(
                                            "Anterior",
                                            on_click=LaimWebState.forum_admin_avatar_page_step(-1),
                                            class_name="crt-btn",
                                        ),
                                        rx.text(LaimWebState.forum_admin_avatar_page_label),
                                        rx.button(
                                            "Siguiente",
                                            on_click=LaimWebState.forum_admin_avatar_page_step(1),
                                            class_name="crt-btn",
                                        ),
                                        spacing="2",
                                        align="center",
                                    ),
                                    rx.el.table(
                                        rx.el.thead(
                                            rx.el.tr(
                                                rx.el.th("Avatar"),
                                                rx.el.th("Etiqueta"),
                                                rx.el.th("Orden"),
                                                rx.el.th("Estado"),
                                                rx.el.th("Acciones"),
                                            )
                                        ),
                                        rx.el.tbody(
                                            rx.foreach(
                                                LaimWebState.forum_admin_avatar_page_rows,
                                                lambda item: rx.el.tr(
                                                    rx.el.td(
                                                        rx.image(
                                                            src=item["preview_url"],
                                                            width="40px",
                                                            height="40px",
                                                            alt=item["label"],
                                                        )
                                                    ),
                                                    rx.el.td(item["label"]),
                                                    rx.el.td(
                                                        rx.input(
                                                            default_value=item["sort_order"],
                                                            on_blur=LaimWebState.forum_admin_avatar_set_sort(item["id"]),
                                                            width="5em",
                                                        )
                                                    ),
                                                    rx.el.td(
                                                        rx.cond(item["active"], "Activo", "Inactivo")
                                                    ),
                                                    rx.el.td(
                                                        rx.hstack(
                                                            rx.button(
                                                                "Por defecto",
                                                                on_click=LaimWebState.forum_admin_avatar_make_default(
                                                                    item["id"]
                                                                ),
                                                                class_name="crt-btn crt-btn-inline",
                                                            ),
                                                            rx.button(
                                                                rx.cond(item["active"], "Desactivar", "Activar"),
                                                                on_click=LaimWebState.forum_admin_avatar_set_active(
                                                                    item["id"], item["active"]
                                                                ),
                                                                class_name="crt-btn crt-btn-inline",
                                                            ),
                                                            rx.button(
                                                                "Quitar del catálogo",
                                                                on_click=LaimWebState.forum_ask_confirm(
                                                                    "avatar", item["id"], item["label"]
                                                                ),
                                                                class_name="crt-btn crt-btn-inline",
                                                            ),
                                                            spacing="2",
                                                        )
                                                    ),
                                                ),
                                            )
                                        ),
                                        width="100%",
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

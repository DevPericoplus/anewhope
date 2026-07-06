"""Perfil, moderación y administración extendida del foro LAIM."""

from __future__ import annotations

import reflex as rx

from laim_web.components.crt_theme import COLORS, FONT_SIZE_BODY, FONT_SIZE_SMALL
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


def forum_profile_panel() -> rx.Component:
    """Formulario de perfil de foro."""
    return rx.vstack(
        rx.heading("Perfil del foro", size="7", color=COLORS["title"]),
        rx.text(
            "Nombre visible, firma, avatar y preferencias de notificación.",
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
            margin_bottom="1em",
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
        rx.text("Avatares del catálogo", class_name="crt-title", font_size="1em"),
        rx.hstack(
            rx.foreach(
                LaimWebState.forum_avatar_catalog,
                lambda item: rx.button(
                    item["label"],
                    on_click=LaimWebState.forum_select_catalog_avatar(item["image_id"]),
                    class_name="crt-btn crt-btn-inline",
                ),
            ),
            flex_wrap="wrap",
            spacing="2",
        ),
        rx.hstack(
            rx.input(type="file", id="forum_avatar_file_input", accept="image/*"),
            rx.button(
                "Subir avatar personal",
                on_click=LaimWebState.forum_request_avatar_upload,
                class_name="crt-btn crt-btn-inline",
            ),
            spacing="2",
            align_items="center",
            flex_wrap="wrap",
        ),
        rx.button(
            "Guardar perfil",
            on_click=LaimWebState.forum_save_profile,
            class_name="crt-btn",
        ),
        spacing="3",
        width="100%",
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
                        rx.input(
                            placeholder="Acción (warn, ban, delete)",
                            value=LaimWebState.forum_admin_word_accion,
                            on_change=LaimWebState.forum_admin_set_word_accion,
                            class_name="crt-input",
                        ),
                        rx.input(
                            placeholder="Mensaje",
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

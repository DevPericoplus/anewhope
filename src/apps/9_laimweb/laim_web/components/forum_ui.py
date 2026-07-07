"""Componentes UI del foro LAIM (estilo CRT)."""

from __future__ import annotations

import reflex as rx

from laim_web.components.crt_theme import COLORS, FONT_SIZE_BODY, FONT_SIZE_SMALL
from laim_web.components.markdown_viewer import crt_markdown_viewer
from laim_web.laim_state import LaimWebState


def _panel_title(text: str) -> rx.Component:
    return rx.text(text, class_name="crt-title", font_size="1.1em", margin_bottom="0.5em")


def forum_image_preview_modal() -> rx.Component:
    """Modal de vista previa de imagen adjunta."""
    return rx.cond(
        LaimWebState.forum_preview_image_url != "",
        rx.box(
            rx.box(
                rx.image(
                    src=LaimWebState.forum_preview_image_url,
                    max_width="90vw",
                    max_height="80vh",
                ),
                rx.button(
                    "Cerrar",
                    on_click=LaimWebState.forum_close_image_preview,
                    class_name="crt-btn crt-btn-inline",
                    margin_top="1em",
                ),
                padding="1.5em",
                background=COLORS["panel_bg"],
                border=f"1px solid {COLORS['border']}",
                border_radius="4px",
            ),
            position="fixed",
            top="0",
            left="0",
            width="100vw",
            height="100vh",
            background="rgba(0,0,0,0.85)",
            display="flex",
            align_items="center",
            justify_content="center",
            z_index="1000",
        ),
        rx.fragment(),
    )


def _attachment_button(image_id) -> rx.Component:
    """Botón para previsualizar un adjunto."""
    return rx.button(
        rx.fragment("Adjunto #", image_id),
        on_click=LaimWebState.forum_preview_image(image_id),
        class_name="crt-btn crt-btn-inline",
        size="1",
    )


def forum_new_thread_form() -> rx.Component:
    """Formulario de creación de hilo con prefijo y adjuntos."""
    return rx.box(
        rx.text("Nuevo hilo", class_name="crt-title", font_size="1em"),
        rx.input(
            placeholder="Título",
            value=LaimWebState.forum_new_title,
            on_change=LaimWebState.forum_set_new_title,
            class_name="crt-input",
            width="100%",
            margin_bottom="0.5em",
        ),
        rx.cond(
            LaimWebState.forum_has_prefixes,
            rx.vstack(
                rx.text(
                    "Prefijo (opcional)",
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_SMALL,
                ),
                rx.hstack(
                    rx.foreach(
                        LaimWebState.forum_prefixes,
                        lambda prefix: rx.button(
                            prefix["texto"],
                            on_click=LaimWebState.forum_set_new_prefix(prefix["id"]),
                            class_name="crt-btn crt-btn-inline",
                            style=rx.cond(
                                LaimWebState.forum_new_prefix_id == prefix["id"],
                                {"font_weight": "bold", "border": f"1px solid {COLORS['accent']}"},
                                {},
                            ),
                        ),
                    ),
                    flex_wrap="wrap",
                    spacing="2",
                ),
                rx.cond(
                    LaimWebState.forum_new_prefix_id != "",
                    rx.text(
                        rx.fragment("Seleccionado: ", LaimWebState.forum_new_prefix_id),
                        color=COLORS["accent"],
                        font_size=FONT_SIZE_SMALL,
                    ),
                    rx.fragment(),
                ),
                spacing="1",
                width="100%",
                margin_bottom="0.5em",
            ),
            rx.fragment(),
        ),
        rx.text_area(
            placeholder="Contenido (Markdown)",
            value=LaimWebState.forum_new_body,
            on_change=LaimWebState.forum_set_new_body,
            class_name="crt-input",
            width="100%",
            min_height="120px",
            margin_bottom="0.5em",
        ),
        rx.hstack(
            rx.input(
                type="file",
                id="forum_thread_file_input",
                accept="image/*",
            ),
            rx.button(
                "Adjuntar imagen",
                on_click=LaimWebState.forum_request_thread_attachment,
                class_name="crt-btn crt-btn-inline",
            ),
            rx.cond(
                LaimWebState.forum_new_attachment_count > 0,
                rx.text(
                    rx.fragment(
                        LaimWebState.forum_new_attachment_count,
                        " adjunto(s)",
                    ),
                    color=COLORS["accent"],
                    font_size=FONT_SIZE_SMALL,
                ),
                rx.fragment(),
            ),
            spacing="2",
            align_items="center",
            flex_wrap="wrap",
            margin_bottom="0.5em",
        ),
        rx.hstack(
            rx.button(
                "Publicar",
                on_click=LaimWebState.forum_create_thread,
                class_name="crt-btn crt-btn-inline",
            ),
            rx.button(
                "Cancelar",
                on_click=LaimWebState.forum_toggle_new_thread,
                class_name="crt-btn crt-btn-inline",
            ),
            spacing="2",
        ),
        padding="1em",
        margin_bottom="1em",
        border=f"1px solid {COLORS['border']}",
        border_radius="4px",
        spacing="2",
        width="100%",
    )


def forum_error_banner() -> rx.Component:
    """Muestra error del foro si existe."""
    return rx.cond(
        LaimWebState.forum_error != "",
        rx.box(
            rx.text(LaimWebState.forum_error, color="#ffaaaa", font_size=FONT_SIZE_SMALL),
            padding="0.75em",
            margin_bottom="1em",
            border=f"1px solid {COLORS['danger']}",
            border_radius="4px",
            width="100%",
        ),
        rx.fragment(),
    )


def forum_category_column() -> rx.Component:
    """Columna de categorías."""
    return rx.vstack(
        _panel_title("Categorías"),
        rx.foreach(
            LaimWebState.forum_categories,
            lambda item: rx.box(
                rx.text(item["nombre"], font_size=FONT_SIZE_BODY),
                on_click=LaimWebState.forum_select_category(item["id"]),
                padding="0.5em",
                cursor="pointer",
                width="100%",
                background=rx.cond(
                    LaimWebState.forum_selected_category_id == item["id"],
                    "rgba(0, 180, 0, 0.25)",
                    "transparent",
                ),
                border_left=rx.cond(
                    LaimWebState.forum_selected_category_id == item["id"],
                    f"3px solid {COLORS['accent']}",
                    "3px solid transparent",
                ),
                _hover={"background": "rgba(0, 80, 0, 0.3)"},
            ),
        ),
        spacing="1",
        width="100%",
        min_width="160px",
    )


def forum_subcategory_column() -> rx.Component:
    """Columna de subcategorías."""
    return rx.vstack(
        _panel_title("Subcategorías"),
        rx.foreach(
            LaimWebState.forum_subcategories,
            lambda item: rx.box(
                rx.text(item["nombre"], font_size=FONT_SIZE_BODY),
                on_click=LaimWebState.forum_select_subcategory(item["id"]),
                padding="0.5em",
                cursor="pointer",
                width="100%",
                background=rx.cond(
                    LaimWebState.forum_selected_subcategory_id == item["id"],
                    "rgba(0, 180, 0, 0.25)",
                    "transparent",
                ),
                border_left=rx.cond(
                    LaimWebState.forum_selected_subcategory_id == item["id"],
                    f"3px solid {COLORS['accent']}",
                    "3px solid transparent",
                ),
                _hover={"background": "rgba(0, 80, 0, 0.3)"},
            ),
        ),
        spacing="1",
        width="100%",
        min_width="160px",
    )


def _thread_row(thread) -> rx.Component:
    """Fila de hilo en listado (Var reactivo)."""
    return rx.box(
        rx.hstack(
            rx.cond(
                thread["fijado"],
                rx.badge("Fijado", color_scheme="green", variant="solid", size="1"),
                rx.fragment(),
            ),
            rx.cond(
                thread["cerrado"],
                rx.badge("Cerrado", color_scheme="gray", variant="solid", size="1"),
                rx.fragment(),
            ),
            rx.text(thread["titulo"], font_weight="bold", color=COLORS["title"]),
            spacing="2",
            align_items="center",
            flex_wrap="wrap",
        ),
        rx.text(
            rx.fragment("Por ", thread["user_name"]),
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
        ),
        on_click=LaimWebState.forum_open_thread(thread["id"]),
        padding="0.65em",
        border_bottom=f"1px solid {COLORS['border']}",
        cursor="pointer",
        width="100%",
        _hover={"background": "rgba(0, 60, 0, 0.35)"},
    )


def forum_threads_panel() -> rx.Component:
    """Listado de hilos de la subcategoría activa."""
    return rx.vstack(
        rx.hstack(
            _panel_title("Hilos"),
            rx.box(flex_grow="1"),
            rx.button(
                "Actualizar",
                on_click=LaimWebState.forum_refresh,
                class_name="crt-btn crt-btn-inline",
            ),
            rx.button(
                "Nuevo hilo",
                on_click=LaimWebState.forum_toggle_new_thread,
                class_name="crt-btn crt-btn-inline",
            ),
            width="100%",
            align_items="center",
        ),
        rx.cond(
            LaimWebState.forum_new_thread_open,
            forum_new_thread_form(),
            rx.fragment(),
        ),
        rx.cond(
            LaimWebState.forum_has_thread,
            rx.fragment(),
            rx.vstack(
                rx.foreach(LaimWebState.forum_threads, _thread_row),
                spacing="0",
                width="100%",
            ),
        ),
        spacing="2",
        width="100%",
        flex="1",
    )


def _post_row(post) -> rx.Component:
    """Fila de respuesta en detalle de hilo (Var reactivo)."""
    image_ids = post["image_ids"].to(list[int])
    return rx.box(
        rx.hstack(
            rx.text(
                post["user_name"],
                font_weight="bold",
                color=COLORS["accent"],
            ),
            rx.box(flex_grow="1"),
            rx.text("Valorar:", color=COLORS["muted"], font_size=FONT_SIZE_SMALL),
            rx.button(
                "1",
                on_click=LaimWebState.forum_rate_post(post["id"], 1),
                class_name="crt-btn crt-btn-inline",
                size="1",
            ),
            rx.button(
                "2",
                on_click=LaimWebState.forum_rate_post(post["id"], 2),
                class_name="crt-btn crt-btn-inline",
                size="1",
            ),
            rx.button(
                "3",
                on_click=LaimWebState.forum_rate_post(post["id"], 3),
                class_name="crt-btn crt-btn-inline",
                size="1",
            ),
            rx.button(
                "4",
                on_click=LaimWebState.forum_rate_post(post["id"], 4),
                class_name="crt-btn crt-btn-inline",
                size="1",
            ),
            rx.button(
                "5",
                on_click=LaimWebState.forum_rate_post(post["id"], 5),
                class_name="crt-btn crt-btn-inline",
                size="1",
            ),
            width="100%",
            align_items="center",
            flex_wrap="wrap",
            spacing="1",
        ),
        crt_markdown_viewer(post["cuerpo_md"]),
        rx.hstack(
            rx.foreach(
                image_ids,
                _attachment_button,
            ),
            flex_wrap="wrap",
            spacing="1",
            margin_top="0.35em",
        ),
        padding_y="0.75em",
        border_bottom=f"1px solid {COLORS['border']}",
        width="100%",
    )


def forum_thread_detail() -> rx.Component:
    """Vista de hilo abierto con respuestas."""
    return rx.cond(
        LaimWebState.forum_has_thread,
        rx.vstack(
            rx.hstack(
                rx.button(
                    "← Volver al listado",
                    on_click=LaimWebState.forum_close_thread,
                    class_name="crt-btn crt-btn-inline",
                ),
                rx.box(flex_grow="1"),
                rx.cond(
                    LaimWebState.forum_show_moderation,
                    rx.hstack(
                        rx.button(
                            rx.cond(
                                LaimWebState.forum_thread_pinned,
                                "Desfijar",
                                "Fijar",
                            ),
                            on_click=LaimWebState.forum_moderate_pin,
                            class_name="crt-btn crt-btn-inline",
                        ),
                        rx.button(
                            rx.cond(
                                LaimWebState.forum_thread_closed,
                                "Reabrir",
                                "Cerrar",
                            ),
                            on_click=LaimWebState.forum_moderate_close,
                            class_name="crt-btn crt-btn-inline",
                        ),
                        rx.button(
                            "Eliminar hilo",
                            on_click=LaimWebState.forum_moderate_delete_thread,
                            class_name="crt-btn crt-btn-inline",
                        ),
                        spacing="2",
                        flex_wrap="wrap",
                    ),
                    rx.fragment(),
                ),
                rx.button(
                    "Actualizar",
                    on_click=LaimWebState.forum_refresh,
                    class_name="crt-btn crt-btn-inline",
                ),
                width="100%",
                flex_wrap="wrap",
                spacing="2",
            ),
            rx.hstack(
                rx.cond(
                    LaimWebState.forum_thread_pinned,
                    rx.badge("Fijado", color_scheme="green", variant="solid"),
                    rx.fragment(),
                ),
                rx.cond(
                    LaimWebState.forum_thread_closed,
                    rx.badge("Cerrado", color_scheme="gray", variant="solid"),
                    rx.fragment(),
                ),
                rx.heading(
                    LaimWebState.forum_thread_title,
                    size="6",
                    color=COLORS["title"],
                ),
                spacing="2",
                flex_wrap="wrap",
                align_items="center",
            ),
            rx.text(
                rx.fragment("Autor: ", LaimWebState.forum_thread_author),
                color=COLORS["muted"],
                font_size=FONT_SIZE_SMALL,
            ),
            crt_markdown_viewer(LaimWebState.forum_thread_body),
            rx.cond(
                LaimWebState.forum_thread_has_attachments,
                rx.vstack(
                    rx.text("Adjuntos del hilo", class_name="crt-title", font_size="0.95em"),
                    rx.hstack(
                        rx.foreach(
                            LaimWebState.forum_thread_image_ids,
                            _attachment_button,
                        ),
                        flex_wrap="wrap",
                        spacing="2",
                    ),
                    spacing="1",
                    width="100%",
                    margin_top="0.5em",
                ),
                rx.fragment(),
            ),
            rx.divider(color=COLORS["border"], margin_y="1em"),
            _panel_title("Respuestas"),
            rx.foreach(
                LaimWebState.forum_posts,
                _post_row,
            ),
            rx.cond(
                ~LaimWebState.forum_thread_closed,
                rx.vstack(
                    rx.text_area(
                        placeholder="Escriba su respuesta (Markdown)...",
                        value=LaimWebState.forum_reply_body,
                        on_change=LaimWebState.forum_set_reply_body,
                        class_name="crt-input",
                        width="100%",
                        min_height="100px",
                    ),
                    rx.hstack(
                        rx.input(
                            type="file",
                            id="forum_reply_file_input",
                            accept="image/*",
                        ),
                        rx.button(
                            "Adjuntar imagen",
                            on_click=LaimWebState.forum_request_reply_attachment,
                            class_name="crt-btn crt-btn-inline",
                        ),
                        rx.cond(
                            LaimWebState.forum_reply_attachment_count > 0,
                            rx.text(
                                rx.fragment(
                                    LaimWebState.forum_reply_attachment_count,
                                    " adjunto(s)",
                                ),
                                color=COLORS["accent"],
                                font_size=FONT_SIZE_SMALL,
                            ),
                            rx.fragment(),
                        ),
                        spacing="2",
                        align_items="center",
                        flex_wrap="wrap",
                    ),
                    rx.button(
                        "Enviar respuesta",
                        on_click=LaimWebState.forum_submit_reply,
                        class_name="crt-btn",
                        width="auto",
                    ),
                    spacing="2",
                    width="100%",
                    margin_top="1em",
                ),
                rx.text(
                    "Este hilo está cerrado. No se admiten nuevas respuestas.",
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_SMALL,
                ),
            ),
            spacing="3",
            width="100%",
        ),
        rx.fragment(),
    )


def forum_main_layout() -> rx.Component:
    """Layout principal de tres columnas del foro."""
    return rx.vstack(
        rx.hstack(
            rx.heading("Foro LAIM", size="7", color=COLORS["title"]),
            rx.box(flex_grow="1"),
            rx.cond(
                LaimWebState.forum_notifications_count > 0,
                rx.badge(
                    LaimWebState.forum_notifications_count,
                    color_scheme="amber",
                    variant="solid",
                ),
                rx.fragment(),
            ),
            width="100%",
            align_items="center",
            margin_bottom="1em",
        ),
        forum_error_banner(),
        rx.cond(
            ~LaimWebState.forum_service_active,
            rx.text(
                "El foro no está activo en este entorno.",
                color=COLORS["muted"],
            ),
            rx.fragment(),
        ),
        rx.cond(
            LaimWebState.forum_has_thread,
            forum_thread_detail(),
            rx.hstack(
                rx.box(
                    forum_category_column(),
                    padding_right="1em",
                    border_right=f"1px solid {COLORS['border']}",
                ),
                rx.box(
                    forum_subcategory_column(),
                    padding_x="1em",
                    border_right=f"1px solid {COLORS['border']}",
                ),
                rx.box(forum_threads_panel(), flex="1", padding_left="1em"),
                width="100%",
                align_items="flex-start",
                spacing="0",
            ),
        ),
        forum_image_preview_modal(),
        spacing="2",
        width="100%",
    )


def forum_my_threads_table() -> rx.Component:
    """Tabla de mis hilos."""
    return rx.vstack(
        rx.heading("Mis hilos", size="7", color=COLORS["title"], margin_bottom="1em"),
        forum_error_banner(),
        rx.foreach(
            LaimWebState.forum_my_threads,
            lambda item: rx.hstack(
                rx.button(
                    item["titulo"],
                    on_click=LaimWebState.forum_go_to_thread(item["id"]),
                    class_name="crt-btn crt-btn-inline",
                    style={"color": COLORS["accent"], "font_weight": "normal"},
                ),
                rx.text(item["subcategory_id"], color=COLORS["muted"], font_size=FONT_SIZE_SMALL),
                rx.spacer(),
                rx.cond(
                    item["cerrado"],
                    rx.badge("Cerrado", color_scheme="gray", variant="solid", size="1"),
                    rx.badge("Abierto", color_scheme="green", variant="solid", size="1"),
                ),
                width="100%",
                padding="0.5em 0",
                border_bottom=f"1px solid {COLORS['border']}",
            ),
        ),
        width="100%",
    )


def forum_my_posts_table() -> rx.Component:
    """Tabla de mis respuestas."""
    return rx.vstack(
        rx.heading("Mis respuestas", size="7", color=COLORS["title"], margin_bottom="1em"),
        forum_error_banner(),
        rx.foreach(
            LaimWebState.forum_my_posts,
            lambda item: rx.hstack(
                rx.button(
                    rx.fragment("Hilo #", item["thread_id"]),
                    on_click=LaimWebState.forum_go_to_thread(item["thread_id"]),
                    class_name="crt-btn crt-btn-inline",
                ),
                rx.text(
                    item["cuerpo_md"],
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_SMALL,
                    max_width="60%",
                    overflow="hidden",
                    text_overflow="ellipsis",
                    white_space="nowrap",
                ),
                width="100%",
                padding="0.5em 0",
                border_bottom=f"1px solid {COLORS['border']}",
            ),
        ),
        width="100%",
    )


def forum_admin_panel() -> rx.Component:
    """Panel básico de administración del foro."""
    return rx.vstack(
        rx.heading("Configuración del foro", size="7", color=COLORS["title"]),
        rx.text(
            "Gestión de categorías y subcategorías (solo administradores).",
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
            margin_bottom="1em",
        ),
        rx.cond(
            LaimWebState.forum_admin_message != "",
            rx.text(LaimWebState.forum_admin_message, color=COLORS["accent"]),
            rx.fragment(),
        ),
        rx.hstack(
            rx.vstack(
                rx.text("Nueva categoría", class_name="crt-title", font_size="1em"),
                rx.input(
                    placeholder="ID (ej: general)",
                    value=LaimWebState.forum_admin_category_id,
                    on_change=LaimWebState.forum_admin_set_category_id,
                    class_name="crt-input",
                ),
                rx.input(
                    placeholder="Nombre",
                    value=LaimWebState.forum_admin_category_name,
                    on_change=LaimWebState.forum_admin_set_category_name,
                    class_name="crt-input",
                ),
                rx.input(
                    placeholder="Descripción",
                    value=LaimWebState.forum_admin_category_desc,
                    on_change=LaimWebState.forum_admin_set_category_desc,
                    class_name="crt-input",
                ),
                rx.button(
                    "Guardar categoría",
                    on_click=LaimWebState.forum_admin_save_category,
                    class_name="crt-btn",
                ),
                spacing="2",
                width="100%",
            ),
            rx.vstack(
                rx.text("Nueva subcategoría", class_name="crt-title", font_size="1em"),
                rx.text(
                    rx.fragment(
                        "Categoría padre: ",
                        LaimWebState.forum_selected_category_id,
                    ),
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_SMALL,
                ),
                rx.input(
                    placeholder="ID (ej: anuncios)",
                    value=LaimWebState.forum_admin_subcategory_id,
                    on_change=LaimWebState.forum_admin_set_subcategory_id,
                    class_name="crt-input",
                ),
                rx.input(
                    placeholder="Nombre",
                    value=LaimWebState.forum_admin_subcategory_name,
                    on_change=LaimWebState.forum_admin_set_subcategory_name,
                    class_name="crt-input",
                ),
                rx.input(
                    placeholder="Descripción",
                    value=LaimWebState.forum_admin_subcategory_desc,
                    on_change=LaimWebState.forum_admin_set_subcategory_desc,
                    class_name="crt-input",
                ),
                rx.button(
                    "Guardar subcategoría",
                    on_click=LaimWebState.forum_admin_save_subcategory,
                    class_name="crt-btn",
                ),
                spacing="2",
                width="100%",
            ),
            spacing="4",
            width="100%",
            align_items="flex-start",
        ),
        rx.divider(color=COLORS["border"], margin_y="1.5em"),
        rx.text("Categorías existentes", class_name="crt-title", font_size="1em"),
        rx.foreach(
            LaimWebState.forum_categories,
            lambda cat: rx.box(
                rx.text(
                    rx.fragment(cat["id"], " — ", cat["nombre"]),
                    color=COLORS["text"],
                    font_size=FONT_SIZE_BODY,
                ),
                on_click=LaimWebState.forum_select_category(cat["id"]),
                padding="0.35em 0",
                cursor="pointer",
                background=rx.cond(
                    LaimWebState.forum_selected_category_id == cat["id"],
                    "rgba(0, 180, 0, 0.2)",
                    "transparent",
                ),
            ),
        ),
        rx.text("Subcategorías", class_name="crt-title", font_size="1em", margin_top="1em"),
        rx.foreach(
            LaimWebState.forum_subcategories,
            lambda sub: rx.text(
                rx.fragment(sub["id"], " — ", sub["nombre"]),
                color=COLORS["text"],
                font_size=FONT_SIZE_BODY,
            ),
        ),
        rx.divider(color=COLORS["border"], margin_y="1.5em"),
        rx.text("Ajustes de moderación (JSON)", class_name="crt-title", font_size="1em"),
        rx.code_block(
            LaimWebState.forum_admin_settings_json,
            theme=rx.code_block.themes.a11y_dark,
            width="100%",
        ),
        spacing="3",
        width="100%",
    )

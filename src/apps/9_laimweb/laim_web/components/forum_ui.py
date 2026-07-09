"""Componentes UI del foro LAIM (estilo CRT)."""

from __future__ import annotations

import reflex as rx

from laim_web.components.crt_theme import (
    COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    SELECT_STYLE,
)
from laim_web.components.forum_message_viewer import forum_message_body
from laim_web.components.forum_star_rating import forum_thread_star_rating_panel
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
                on_click=LaimWebState.forum_close_new_thread,
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


def _forum_select_label(text: str) -> rx.Component:
    """Etiqueta de selector del foro."""
    return rx.text(
        text,
        font_size="1.1em",
        color=COLORS["title"],
        font_weight="bold",
    )


def forum_category_select() -> rx.Component:
    """Desplegable de categoría (barra superior, estilo Radikal)."""
    return rx.vstack(
        _forum_select_label("Categoría"),
        rx.select(
            LaimWebState.forum_category_select_labels,
            value=LaimWebState.forum_selected_category_label,
            on_change=LaimWebState.forum_select_category_by_label,
            placeholder="Categoría",
            size="3",
            width="100%",
            min_width="180px",
            style=SELECT_STYLE,
            class_name="forum-select",
        ),
        spacing="1",
        align_items="start",
    )


def forum_subcategory_select() -> rx.Component:
    """Desplegable de subcategoría (barra superior, estilo Radikal)."""
    return rx.vstack(
        _forum_select_label("Subcategoría"),
        rx.select(
            LaimWebState.forum_subcategory_select_labels,
            value=LaimWebState.forum_selected_subcategory_label,
            on_change=LaimWebState.forum_select_subcategory_by_label,
            placeholder="Subcategoría",
            size="3",
            width="100%",
            min_width="200px",
            style=SELECT_STYLE,
            class_name="forum-select",
        ),
        spacing="1",
        align_items="start",
    )


def _forum_category_filters_row() -> rx.Component:
    """Fila de filtros: categoría + subcategoría."""
    return rx.hstack(
        forum_category_select(),
        forum_subcategory_select(),
        spacing="4",
        width="100%",
        flex_wrap="wrap",
        align_items="end",
        flex_shrink="0",
        class_name="forum-filters-row",
    )


def forum_new_thread_dialog() -> rx.Component:
    """Diálogo modal para crear hilo (no ocupa espacio del listado)."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Nuevo hilo", color=COLORS["title"]),
            forum_new_thread_form(),
            background=COLORS["panel_bg"],
            border=f"1px solid {COLORS['border']}",
            max_width="560px",
        ),
        open=LaimWebState.forum_new_thread_open,
        on_open_change=LaimWebState.forum_on_new_thread_dialog_change,
    )


def _forum_toolbar() -> rx.Component:
    """Cabecera: solo título (filtros y acciones van debajo)."""
    return rx.hstack(
        rx.vstack(
            rx.heading("Foro LAIM", size="6", color=COLORS["title"]),
            rx.text(
                "Seleccione categoría y subcategoría; los hilos se muestran debajo.",
                color=COLORS["muted"],
                font_size=FONT_SIZE_SMALL,
            ),
            spacing="1",
        ),
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
        flex_shrink="0",
    )


def _forum_threads_toolbar() -> rx.Component:
    """Acciones del listado de hilos (debajo de los selectores)."""
    return rx.hstack(
        _panel_title("Hilos"),
        rx.box(flex_grow="1"),
        rx.button(
            "Actualizar",
            on_click=LaimWebState.forum_refresh,
            class_name="crt-btn crt-btn-inline",
        ),
        rx.button(
            "Nuevo hilo",
            on_click=LaimWebState.forum_open_new_thread,
            class_name="crt-btn crt-btn-inline",
        ),
        width="100%",
        align_items="center",
        flex_shrink="0",
        flex_wrap="wrap",
        spacing="2",
    )


def _thread_row(thread) -> rx.Component:
    """Fila de hilo en listado lateral (Var reactivo)."""
    return rx.box(
        rx.vstack(
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
                spacing="2",
            ),
            rx.text(thread["titulo"], font_weight="bold", color=COLORS["title"]),
            rx.hstack(
                rx.text(thread["user_name"], color=COLORS["accent"], font_size=FONT_SIZE_SMALL),
                rx.text("·", color=COLORS["muted"], font_size=FONT_SIZE_SMALL),
                rx.text(
                    thread["respuestas_count"],
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_SMALL,
                ),
                rx.text(" resp.", color=COLORS["muted"], font_size=FONT_SIZE_SMALL),
                spacing="1",
                flex_wrap="wrap",
            ),
            rx.cond(
                thread["actualizado"] != "",
                rx.text(
                    thread["actualizado"],
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_SMALL,
                    text_align="right",
                    width="100%",
                ),
                rx.fragment(),
            ),
            spacing="1",
            align_items="start",
            width="100%",
        ),
        on_click=LaimWebState.forum_open_thread(thread["id"]),
        padding="0.75em",
        border_radius="6px",
        background=rx.cond(
            LaimWebState.forum_active_thread_id == thread["id"],
            "rgba(0, 180, 0, 0.25)",
            COLORS["panel_bg"],
        ),
        border=f"1px solid {COLORS['border']}",
        cursor="pointer",
        width="100%",
        _hover={"background": "rgba(0, 80, 0, 0.35)"},
    )


def forum_threads_sidebar() -> rx.Component:
    """Columna lateral con listado de hilos (estilo Radikal)."""
    return rx.box(
        rx.vstack(
            rx.cond(
                LaimWebState.forum_has_selection,
                rx.cond(
                    LaimWebState.forum_threads.length() > 0,
                    rx.vstack(
                        rx.foreach(LaimWebState.forum_threads, _thread_row),
                        spacing="2",
                        width="100%",
                    ),
                    rx.text(
                        "No hay hilos en esta subcategoría.",
                        color=COLORS["muted"],
                        font_size=FONT_SIZE_SMALL,
                    ),
                ),
                rx.text(
                    "No hay hilos en esta subcategoría.",
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_SMALL,
                ),
            ),
            spacing="2",
            width="100%",
        ),
        width="280px",
        min_width="280px",
        height="100%",
        overflow_y="auto",
        padding="0.75em",
        background=COLORS["panel_bg"],
        border=f"1px solid {COLORS['border']}",
        border_radius="8px",
        class_name="forum-threads-sidebar",
    )


def _post_row(post) -> rx.Component:
    """Fila de respuesta en detalle de hilo (Var reactivo)."""
    image_ids = post["image_ids"].to(list[int])
    return rx.box(
        rx.hstack(
            rx.cond(
                post["author_avatar_preview_url"] != "",
                rx.image(
                    src=post["author_avatar_preview_url"],
                    width="40px",
                    height="40px",
                    border_radius="50%",
                    alt=post["user_name"],
                    flex_shrink="0",
                ),
                rx.box(
                    width="40px",
                    height="40px",
                    border_radius="50%",
                    background_color=COLORS["panel_bg"],
                    border=f"1px solid {COLORS['border']}",
                    flex_shrink="0",
                ),
            ),
            rx.text(
                post["user_name"],
                font_weight="bold",
                color=COLORS["accent"],
            ),
            rx.box(flex_grow="1"),
            width="100%",
            align_items="center",
            flex_wrap="wrap",
            spacing="1",
        ),
        rx.box(
            forum_message_body(post["display_md"]),
            class_name="forum-post-body",
            width="100%",
            margin_top="0.5em",
        ),
        rx.hstack(
            rx.foreach(
                image_ids,
                _attachment_button,
            ),
            flex_wrap="wrap",
            spacing="1",
            margin_top="0.35em",
        ),
        padding="0.85em 1em",
        margin_bottom="0.65em",
        border=f"1px solid {COLORS['border']}",
        border_radius="6px",
        background="rgba(255, 255, 255, 0.03)",
        width="100%",
        class_name="forum-post-row",
    )


def forum_thread_content_panel() -> rx.Component:
    """Panel principal: detalle del hilo seleccionado o mensaje vacío."""
    return rx.box(
        rx.cond(
            LaimWebState.forum_has_thread,
            rx.vstack(
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
                        size="5",
                        color=COLORS["title"],
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
                    width="100%",
                    flex_wrap="wrap",
                    spacing="2",
                    flex_shrink="0",
                ),
                rx.vstack(
                    rx.text(
                        rx.fragment("Autor: ", LaimWebState.forum_thread_author),
                        color=COLORS["muted"],
                        font_size=FONT_SIZE_SMALL,
                    ),
                    rx.cond(
                        LaimWebState.forum_has_thread_author_avatar,
                        rx.image(
                            src=LaimWebState.forum_thread_author_avatar_url,
                            width="56px",
                            height="56px",
                            border_radius="50%",
                            alt=LaimWebState.forum_thread_author,
                            border=f"2px solid {COLORS['accent']}",
                            class_name="forum-thread-author-avatar",
                        ),
                        rx.text(
                            "Sin avatar asignado",
                            color=COLORS["muted"],
                            font_size=FONT_SIZE_SMALL,
                            font_style="italic",
                        ),
                    ),
                    spacing="2",
                    align_items="flex-start",
                    width="100%",
                    class_name="forum-thread-author-block",
                ),
                forum_thread_star_rating_panel(),
                rx.box(
                    forum_message_body(
                        LaimWebState.forum_thread_body_display,
                        class_name="forum-post-body forum-thread-op-body",
                    ),
                    padding="0.85em 1em",
                    margin_bottom="0.65em",
                    border=f"1px solid {COLORS['border']}",
                    border_radius="6px",
                    background="rgba(255, 255, 255, 0.03)",
                    width="100%",
                    class_name="forum-post-row forum-thread-op-row",
                ),
                rx.box(
                    rx.vstack(
                        rx.cond(
                            LaimWebState.forum_thread_has_attachments,
                            rx.vstack(
                                rx.text(
                                    "Adjuntos del hilo",
                                    class_name="crt-title",
                                    font_size="0.95em",
                                ),
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
                            ),
                            rx.fragment(),
                        ),
                        rx.divider(color=COLORS["border"], margin_y="1em"),
                        _panel_title("Respuestas"),
                        rx.foreach(
                            LaimWebState.forum_posts,
                            _post_row,
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    class_name="forum-thread-scroll",
                    width="100%",
                    min_height="0",
                    flex="1",
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
                            min_height="80px",
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
                            rx.button(
                                "Enviar respuesta",
                                on_click=LaimWebState.forum_submit_reply,
                                class_name="crt-btn crt-btn-inline",
                            ),
                            spacing="2",
                            align_items="center",
                            flex_wrap="wrap",
                            width="100%",
                        ),
                        spacing="2",
                        width="100%",
                        class_name="forum-reply-panel",
                        flex_shrink="0",
                    ),
                    rx.text(
                        "Este hilo está cerrado. No se admiten nuevas respuestas.",
                        color=COLORS["muted"],
                        font_size=FONT_SIZE_SMALL,
                        flex_shrink="0",
                    ),
                ),
                spacing="2",
                width="100%",
                height="100%",
                min_height="0",
                class_name="forum-thread-layout",
            ),
            rx.center(
                rx.text(
                    "Seleccione un hilo de la lista.",
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_BODY,
                ),
                height="100%",
                width="100%",
            ),
        ),
        flex="1",
        min_width="0",
        height="100%",
        min_height="0",
        class_name="forum-thread-panel",
        padding="1em",
        background=COLORS["panel_bg"],
        border=f"1px solid {COLORS['border']}",
        border_radius="8px",
    )


def forum_thread_detail() -> rx.Component:
    """Alias de compatibilidad: vista de hilo en panel principal."""
    return forum_thread_content_panel()


def forum_main_layout() -> rx.Component:
    """Layout principal del foro: selectores arriba + hilos protagonistas."""
    return rx.box(
        rx.vstack(
            _forum_toolbar(),
            forum_error_banner(),
            rx.cond(
                ~LaimWebState.forum_service_active,
                rx.text(
                    "El foro no está activo en este entorno.",
                    color=COLORS["muted"],
                ),
                rx.vstack(
                    _forum_category_filters_row(),
                    rx.vstack(
                        _forum_threads_toolbar(),
                        rx.hstack(
                            forum_threads_sidebar(),
                            forum_thread_content_panel(),
                            spacing="4",
                            width="100%",
                            flex="1",
                            min_height="0",
                            align_items="stretch",
                            class_name="forum-panels-row",
                        ),
                        spacing="2",
                        width="100%",
                        flex="1",
                        min_height="0",
                        class_name="forum-threads-area",
                    ),
                    spacing="3",
                    width="100%",
                    flex="1",
                    min_height="0",
                    class_name="forum-service-area",
                ),
            ),
            forum_image_preview_modal(),
            forum_new_thread_dialog(),
            spacing="3",
            width="100%",
            flex="1",
            min_height="0",
        ),
        width="100%",
        flex="1",
        min_height="0",
        height="100%",
        class_name="forum-page-layout",
    )


def forum_my_threads_table() -> rx.Component:
    """Tabla de mis hilos."""
    return rx.vstack(
        rx.heading("Mis hilos", size="7", color=COLORS["title"], margin_bottom="1em"),
        forum_error_banner(),
        rx.foreach(
            LaimWebState.forum_my_threads,
            lambda item: rx.vstack(
                rx.hstack(
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
                    align_items="center",
                ),
                rx.cond(
                    item["display_preview"] != "",
                    rx.text(
                        item["display_preview"],
                        class_name="forum-list-preview",
                        font_size=FONT_SIZE_SMALL,
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                width="100%",
                padding="0.65em 0",
                border_bottom=f"1px solid {COLORS['border']}",
                spacing="1",
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
            lambda item: rx.vstack(
                rx.hstack(
                    rx.button(
                        rx.fragment("Hilo #", item["thread_id"]),
                        on_click=LaimWebState.forum_go_to_thread(item["thread_id"]),
                        class_name="crt-btn crt-btn-inline",
                    ),
                    rx.spacer(),
                    width="100%",
                ),
                rx.text(
                    item["display_preview"],
                    class_name="forum-list-preview",
                    font_size=FONT_SIZE_SMALL,
                    width="100%",
                ),
                width="100%",
                padding="0.65em 0",
                border_bottom=f"1px solid {COLORS['border']}",
                spacing="1",
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
        rx.button(
            "Estadísticas del foro",
            on_click=LaimWebState.forum_open_stats_dialog,
            class_name="crt-btn crt-btn-inline",
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
                rx.input(
                    placeholder="Duración ban automático (segundos, ej: 86400)",
                    value=LaimWebState.forum_admin_subcategory_ban_seconds,
                    on_change=LaimWebState.forum_admin_set_subcategory_ban_seconds,
                    class_name="crt-input",
                ),
                rx.select(
                    ["weekly", "daily", "none"],
                    value=LaimWebState.forum_admin_subcategory_log_rotation,
                    on_change=LaimWebState.forum_admin_set_subcategory_log_rotation,
                    class_name="crt-input",
                    width="100%",
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
        rx.text(
            "Los ajustes de moderación, prefijos y reglas se gestionan en "
            "«Configuración avanzada» (persistidos en la base de datos).",
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
        ),
        spacing="3",
        width="100%",
    )

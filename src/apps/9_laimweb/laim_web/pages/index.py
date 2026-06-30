"""Página principal de LAIM Web — layout con header, sidebar, contenido y footer."""

import reflex as rx

from laim_web.laim_state import LaimWebState


# Paleta de colores CRT para reutilización
COLORS = {
    "bg": "black",
    "panel_bg": "rgba(0, 20, 0, 0.55)",
    "border": "rgba(0, 200, 0, 0.35)",
    "text": "#e8ffe8",
    "title": "#9dff9d",
    "muted": "rgba(200, 255, 200, 0.65)",
    "accent": "#00b400",
    "input_bg": "rgba(0, 30, 0, 0.8)",
    "btn_bg": "rgba(0, 40, 0, 0.65)",
    "btn_hover": "rgba(0, 80, 0, 0.75)",
    "danger": "rgba(255, 80, 80, 0.55)",
}

FONT_SIZE_TITLE = "1.4em"
FONT_SIZE_BODY = "0.95em"
FONT_SIZE_SMALL = "0.85em"
CONTENT_PADDING = "1.5em"

MENU_ITEMS_LOGGED_OUT = ["inicio", "servicios", "documentacion", "contacto"]
MENU_ITEMS_LOGGED_IN = ["dashboard", "modelos", "datasets", "entrenamiento", "configuracion"]


def logo() -> rx.Component:
    """Logo LAIM con estilo CRT."""
    return rx.hstack(
        rx.text("LAIM", font_weight="bold", font_size="1.6em", color=COLORS["title"],
                letter_spacing="0.08em"),
        rx.text(".app", font_size="1.2em", color=COLORS["muted"]),
        spacing="1",
        align_items="baseline",
    )


def header() -> rx.Component:
    """Panel superior — logo, nombre de usuario y botón desconectar."""
    return rx.hstack(
        logo(),
        rx.box(flex_grow="1"),
        rx.cond(
            LaimWebState.is_logged_in,
            rx.hstack(
                rx.text(
                    LaimWebState.user_name,
                    color=COLORS["muted"],
                    font_size=FONT_SIZE_BODY,
                ),
                rx.button(
                    "Desconectar",
                    on_click=LaimWebState.handle_logout,
                    class_name="crt-btn crt-btn-danger",
                    width="auto",
                    padding_x="1em",
                ),
                spacing="3",
                align_items="center",
            ),
            rx.text(
                "Local Artificial Intelligence Management",
                color=COLORS["muted"],
                font_size=FONT_SIZE_BODY,
            ),
        ),
        width="100%",
        padding="0.75em 1.5em",
        background=COLORS["panel_bg"],
        border_bottom=f"1px solid {COLORS['border']}",
        align_items="center",
        min_height="3.2em",
    )


def login_panel() -> rx.Component:
    """Panel de autenticación en el sidebar."""
    return rx.vstack(
        rx.text("Autenticación", class_name="crt-title", font_size="1em"),
        rx.input(
            placeholder="Usuario",
            value=LaimWebState.login_username,
            on_change=LaimWebState.set_login_username,
            class_name="crt-input",
            width="100%",
        ),
        rx.input(
            placeholder="Contraseña",
            type="password",
            value=LaimWebState.login_password,
            on_change=LaimWebState.set_login_password,
            class_name="crt-input",
            width="100%",
        ),
        rx.cond(
            LaimWebState.error_message != "",
            rx.text(LaimWebState.error_message, class_name="crt-error", font_size=FONT_SIZE_SMALL),
        ),
        rx.button(
            "Conectar",
            on_click=LaimWebState.handle_login,
            class_name="crt-btn",
            width="100%",
            disabled=LaimWebState.loading,
        ),
        spacing="2",
        width="100%",
    )


def user_info_panel() -> rx.Component:
    """Información del usuario autenticado en el sidebar."""
    return rx.vstack(
        rx.text("Sesión activa", class_name="crt-title", font_size="1em"),
        rx.text(LaimWebState.user_name, color=COLORS["text"], font_size=FONT_SIZE_BODY),
        rx.text(
            rx.cond(
                LaimWebState.organization_id > 0,
                f"Org: {LaimWebState.organization_id}",
                "",
            ),
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
        ),
        spacing="1",
        width="100%",
    )


def sidebar_menu() -> rx.Component:
    """Menú de navegación lateral."""
    menu_items = rx.cond(
        LaimWebState.is_logged_in,
        MENU_ITEMS_LOGGED_IN,
        MENU_ITEMS_LOGGED_OUT,
    )

    return rx.vstack(
        rx.text("Menú", class_name="crt-title", font_size="1em", margin_top="0.5em"),
        rx.vstack(
            rx.foreach(
                menu_items,
                lambda item: rx.box(
                    rx.text(item.upper(), font_size="0.9em"),
                    on_click=LaimWebState.set_menu(item),
                    background=rx.cond(
                        LaimWebState.active_menu == item,
                        "rgba(0, 180, 0, 0.3)",
                        "transparent",
                    ),
                    border_left=rx.cond(
                        LaimWebState.active_menu == item,
                        f"3px solid {COLORS['accent']}",
                        "3px solid transparent",
                    ),
                    color=rx.cond(
                        LaimWebState.active_menu == item,
                        COLORS["title"],
                        COLORS["text"],
                    ),
                    width="100%",
                    padding="0.55em 0.75em",
                    cursor="pointer",
                    _hover={"background": "rgba(0, 80, 0, 0.35)"},
                ),
            ),
            spacing="1",
            width="100%",
        ),
        spacing="1",
        width="100%",
    )


def sidebar() -> rx.Component:
    """Sidebar izquierda: autenticación + menú."""
    return rx.vstack(
        rx.cond(
            LaimWebState.is_logged_in,
            user_info_panel(),
            login_panel(),
        ),
        rx.divider(color=COLORS["border"], margin_y="0.75em"),
        sidebar_menu(),
        spacing="2",
        padding="1em",
        width="100%",
        height="100%",
        overflow_y="auto",
    )


def content_inicio() -> rx.Component:
    """Contenido por defecto — pantalla de bienvenida."""
    return rx.vstack(
        rx.text("Bienvenido a LAIM", class_name="crt-title", font_size=FONT_SIZE_TITLE),
        rx.text(
            "Local Artificial Intelligence Management",
            color=COLORS["text"],
            font_size="1.1em",
        ),
        rx.divider(color=COLORS["border"], margin_y="1em"),
        rx.text(
            "LAIM es tu plataforma de gestión de inteligencia artificial local. "
            "Accede a tus sistemas,servicios,bases de datos o aplicaciones para gestionarlos con soporte de IA.",
            color=COLORS["muted"],
            font_size=FONT_SIZE_BODY,
            line_height="1.6",
        ),
        spacing="3",
        padding=CONTENT_PADDING,
    )


def content_dashboard() -> rx.Component:
    """Panel de control tras login."""
    return rx.vstack(
        rx.text("Dashboard", class_name="crt-title", font_size=FONT_SIZE_TITLE),
        rx.text(
            "Sesión activa — Usuario: ",
            color=COLORS["text"],
            font_size="1em",
        ),
        rx.text(LaimWebState.user_name, color=COLORS["title"], font_size="1em"),
        rx.divider(color=COLORS["border"], margin_y="1em"),
        rx.text(
            "Aquí se mostrará el resumen de actividad, modelos activos y estado del sistema.",
            color=COLORS["muted"],
            font_size=FONT_SIZE_BODY,
        ),
        spacing="3",
        padding=CONTENT_PADDING,
    )


def content_placeholder(title: str) -> rx.Component:
    """Contenido genérico para secciones pendientes de implementar."""
    return rx.vstack(
        rx.text(title, class_name="crt-title", font_size=FONT_SIZE_TITLE),
        rx.divider(color=COLORS["border"], margin_y="1em"),
        rx.text(
            "Esta sección se encuentra en desarrollo.",
            color=COLORS["muted"],
            font_size=FONT_SIZE_BODY,
        ),
        spacing="3",
        padding=CONTENT_PADDING,
    )


def main_content() -> rx.Component:
    """Panel de contenido principal — renderiza según menú activo."""
    return rx.box(
        rx.match(
            LaimWebState.active_menu,
            ("inicio", content_inicio()),
            ("dashboard", content_dashboard()),
            ("servicios", content_placeholder("Servicios")),
            ("documentacion", content_placeholder("Documentación")),
            ("contacto", content_placeholder("Contacto")),
            ("modelos", content_placeholder("Gestión de Modelos")),
            ("datasets", content_placeholder("Gestión de Datasets")),
            ("entrenamiento", content_placeholder("Entrenamiento")),
            ("configuracion", content_placeholder("Configuración")),
            content_inicio(),
        ),
        width="100%",
        height="100%",
        overflow_y="auto",
    )


def footer() -> rx.Component:
    """Panel inferior — información y copyright."""
    return rx.hstack(
        rx.text("LAIM v0.1.0", color=COLORS["muted"], font_size=FONT_SIZE_SMALL),
        rx.box(flex_grow="1"),
        rx.text(
            "© 2025 LAIM — Local Artificial Intelligence Management",
            color=COLORS["muted"],
            font_size=FONT_SIZE_SMALL,
        ),
        width="100%",
        padding="0.6em 1.5em",
        background=COLORS["panel_bg"],
        border_top=f"1px solid {COLORS['border']}",
        align_items="center",
        min_height="2.5em",
    )


def index_page() -> rx.Component:
    """Layout principal: header + (sidebar | contenido) + footer."""
    return rx.vstack(
        header(),
        rx.hstack(
            # Sidebar izquierda (25%)
            rx.box(
                sidebar(),
                width="25%",
                min_width="220px",
                max_width="320px",
                background=COLORS["panel_bg"],
                border_right=f"1px solid {COLORS['border']}",
                height="100%",
            ),
            # Contenido principal (75%)
            rx.box(
                main_content(),
                flex="1",
                min_width="0",
                height="100%",
            ),
            width="100%",
            spacing="0",
            flex="1",
            align_items="stretch",
            overflow="hidden",
        ),
        footer(),
        width="100%",
        min_height="100vh",
        spacing="0",
        background="black",
    )

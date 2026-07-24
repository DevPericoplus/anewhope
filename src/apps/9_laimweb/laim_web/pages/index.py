"""Página principal de LAIM Web — layout con header, sidebar, contenido y footer."""

import reflex as rx

from laim_web.components.auth_modals import auth_modals
from laim_web.components.contact_form import contact_form_panel
from laim_web.components.markdown_viewer import crt_markdown_viewer
from laim_web.components.presentation_panel import presentation_content_panel
from laim_web.components.page_actions import page_action_panel
from laim_web.components.laim_logo import laim_logo_sidebar
from laim_web.components.portal_shell import forum_nav_section, sidebar_config_menu
from laim_web.laim_state import LaimWebState

from laim_web.components.crt_theme import (
    COLORS,
    CONTENT_PADDING,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
)
MENU_ITEMS_LOGGED_OUT = ["inicio", "presentacion", "servicios", "documentacion", "contacto"]

MENU_LABELS: dict[str, str] = {
    "inicio": "Inicio",
    "presentacion": "Presentación",
    "servicios": "Servicios",
    "documentacion": "Documentación",
    "contacto": "Contacto",
    "instaladores": "Instaladores",
    "manuales": "Manuales",
    "modelos_base": "Modelos base",
    "modelos_especializados": "Modelos especializados",
    "modelos_personalizados": "Modelos personalizados",
    "skills": "Skills",
    "complementos": "Complementos",
    "soporte": "Soporte",
    "faq": "FAQ",
}

LOGGED_IN_MENU_ITEMS = [
    "instaladores",
    "manuales",
    "modelos_base",
    "modelos_especializados",
    "modelos_personalizados",
    "skills",
    "complementos",
    "soporte",
    "faq",
]


def logo() -> rx.Component:
    """Logo LAIM con estilo CRT (texto en cabecera)."""
    return rx.hstack(
        rx.text(
            "LAIM",
            font_weight="bold",
            font_size="1.6em",
            color=COLORS["title"],
            letter_spacing="0.08em",
        ),
        rx.text(".app", font_size="1.2em", color=COLORS["muted"]),
        spacing="1",
        align_items="baseline",
    )


def header_auth_actions() -> rx.Component:
    """Acciones de autenticación en la cabecera (usuario no conectado)."""
    return rx.hstack(
        rx.button(
            "Iniciar sesión",
            on_click=LaimWebState.open_login_modal,
            class_name="crt-btn crt-btn-inline",
        ),
        rx.button(
            "Crear cuenta",
            on_click=LaimWebState.open_register_modal,
            class_name="crt-btn crt-btn-inline",
        ),
        spacing="2",
        align_items="center",
        class_name="crt-header-actions",
    )


def header() -> rx.Component:
    """Panel superior — logo, usuario y acciones de sesión."""
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
                    class_name="crt-btn crt-btn-danger crt-btn-inline",
                    width="auto",
                    padding_x="1em",
                ),
                spacing="3",
                align_items="center",
            ),
            header_auth_actions(),
        ),
        width="100%",
        padding="0.75em 1.5em",
        background=COLORS["panel_bg"],
        border_bottom=f"1px solid {COLORS['border']}",
        align_items="center",
        min_height="3.2em",
    )


def auth_cta_panel() -> rx.Component:
    """Acceso compacto en sidebar — abre modales de autenticación."""
    return rx.vstack(
        laim_logo_sidebar(),
        rx.text("Acceso al portal", class_name="crt-title", font_size="1em"),
        rx.text(
            "Inicie sesión o cree una cuenta para acceder al panel de gestión de IA local.",
            class_name="crt-muted",
            font_size=FONT_SIZE_SMALL,
            line_height="1.45",
        ),
        rx.button(
            "Iniciar sesión",
            on_click=LaimWebState.open_login_modal,
            class_name="crt-btn",
            width="100%",
        ),
        rx.button(
            "Crear cuenta",
            on_click=LaimWebState.open_register_modal,
            class_name="crt-btn",
            width="100%",
        ),
        spacing="2",
        width="100%",
        class_name="crt-auth-sidebar-cta",
    )


def user_info_panel() -> rx.Component:
    """Información del usuario autenticado en el sidebar."""
    return rx.vstack(
        rx.text("Sesión activa", class_name="crt-title", font_size="1em"),
        rx.text(LaimWebState.user_name, color=COLORS["text"], font_size=FONT_SIZE_BODY),
        spacing="1",
        width="100%",
    )


def _menu_label(item: str) -> str:
    """Etiqueta legible para una clave de menú."""
    return MENU_LABELS.get(item, item.replace("_", " ").title())


def _sidebar_menu_item(item: str) -> rx.Component:
    """Entrada del menú lateral con etiqueta en español."""
    return rx.box(
        rx.text(_menu_label(item), font_size="0.9em"),
        on_click=lambda: LaimWebState.set_menu(item),
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
    )


def sidebar_menu() -> rx.Component:
    """Menú de navegación lateral."""
    return rx.vstack(
        rx.text("Menú", class_name="crt-title", font_size="1em", margin_top="0.5em"),
        rx.cond(
            LaimWebState.is_logged_in,
            rx.vstack(
                *[_sidebar_menu_item(item) for item in LOGGED_IN_MENU_ITEMS],
                spacing="1",
                width="100%",
            ),
            rx.vstack(
                rx.foreach(
                    MENU_ITEMS_LOGGED_OUT,
                    lambda item: _sidebar_menu_item(item),
                ),
                spacing="1",
                width="100%",
            ),
        ),
        spacing="1",
        width="100%",
    )


def sidebar() -> rx.Component:
    """Sidebar izquierda: acceso + menú de navegación."""
    return rx.vstack(
        rx.cond(
            LaimWebState.is_logged_in,
            user_info_panel(),
            auth_cta_panel(),
        ),
        rx.divider(color=COLORS["border"], margin_y="0.75em"),
        sidebar_menu(),
        forum_nav_section(),
        sidebar_config_menu(),
        spacing="2",
        padding="1em",
        width="100%",
        height="100%",
        overflow_y="auto",
    )


def content_static_page() -> rx.Component:
    """Contenido cargado desde static_pages/*.md (panel derecho)."""
    return rx.vstack(
        rx.cond(
            LaimWebState.active_menu == "presentacion",
            presentation_content_panel(),
            crt_markdown_viewer(LaimWebState.static_page_content),
        ),
        rx.cond(
            LaimWebState.active_menu == "contacto",
            contact_form_panel(),
            rx.fragment(),
        ),
        rx.match(
            LaimWebState.active_menu,
            ("instaladores", page_action_panel("instaladores")),
            ("manuales", page_action_panel("manuales")),
            ("modelos_base", page_action_panel("modelos_base")),
            ("modelos_especializados", page_action_panel("modelos_especializados")),
            ("modelos_personalizados", page_action_panel("modelos_personalizados")),
            ("skills", page_action_panel("skills")),
            ("complementos", page_action_panel("complementos")),
            ("soporte", page_action_panel("soporte")),
            ("faq", page_action_panel("faq")),
            rx.fragment(),
        ),
        spacing="0",
        width="100%",
        align_items="stretch",
    )


def main_content() -> rx.Component:
    """Panel de contenido principal — renderiza según menú activo."""
    return rx.box(
        content_static_page(),
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
    """Layout principal: header + (sidebar | contenido) + footer + modales."""
    return rx.box(
        rx.vstack(
            header(),
            rx.hstack(
                rx.box(
                    sidebar(),
                    width="25%",
                    min_width="220px",
                    max_width="320px",
                    background=COLORS["panel_bg"],
                    border_right=f"1px solid {COLORS['border']}",
                    height="100%",
                ),
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
        ),
        auth_modals(),
        class_name="crt-shell crt-theme-green",
        width="100%",
    )

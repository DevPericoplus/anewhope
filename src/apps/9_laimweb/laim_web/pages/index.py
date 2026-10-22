"""Página principal de LAIM Web — layout con header, sidebar, contenido y footer."""

import reflex as rx

from laim_web.components.auth_modals import auth_modals
from laim_web.components.config_general_panel import config_general_panel
from laim_web.components.contact_form import contact_form_panel
from laim_web.components.bento.home import inicio_home_panel
from laim_web.components.markdown_viewer import crt_markdown_viewer
from laim_web.components.escenarios_panel import escenarios_content_panel
from laim_web.components.presentation_panel import presentation_content_panel
from laim_web.components.page_actions import page_action_panel
from laim_web.components.base_models_modal import (
    base_models_catalog_modal,
    compare_requirements_modal,
    recommended_model_modal,
)
from laim_web.components.tickets_modal import (
    ticket_create_modal,
    ticket_notification_modal,
    ticket_status_modal,
)
from laim_web.components.installers_panel import advance_construction_modal, installers_panel
from laim_web.components.registro_panel import install_instructions_modal, install_notification_modal, registro_panel
from laim_web.components.laim_logo import laim_logo_sidebar
from laim_web.components.portal_shell import forum_nav_section, sidebar_config_menu
from laim_web.help_manuals import HELP_MANUALS
from laim_web.laim_state import LaimWebState
from laim_web.static_pages_loader import load_static_page_markdown

from laim_web.components.crt_theme import (
    COLORS,
    CONTENT_PADDING,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
)
MENU_ITEMS_LOGGED_OUT = [
    "inicio",
    "presentacion",
    "servicios",
    "documentacion",
    "escenarios",
    "contacto",
]

MENU_LABELS: dict[str, str] = {
    "inicio": "Inicio",
    "presentacion": "Presentación",
    "servicios": "Servicios",
    "documentacion": "Documentación",
    "escenarios": "Escenarios",
    "contacto": "Contacto",
    "instaladores": "Instaladores",
    "registro": "Registro",
    "manuales": "Manuales",
    "modelos_base": "Modelos base",
    "modelos_especializados": "Modelos especializados",
    "modelos_personalizados": "Modelos personalizados",
    "agents": "Agentes",
    "complementos": "Complementos",
    "soporte": "Soporte",
    "faq": "FAQ",
}

# Catálogo del portal aún no disponible (chip crt-badge-wip).
WIP_PAGE_MENUS = frozenset({"modelos_especializados", "modelos_personalizados"})

LOGGED_IN_MENU_ITEMS = [
    "escenarios",
    "instaladores",
    "registro",
    "manuales",
    "modelos_base",
    "modelos_especializados",
    "modelos_personalizados",
    "agents",
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
        rx.button(
            "Olvidé contraseña",
            on_click=LaimWebState.open_forgot_modal,
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
    label = rx.hstack(
        rx.text(_menu_label(item), font_size="0.9em"),
        (
            rx.el.span("In progress", class_name="crt-badge-wip")
            if item in WIP_PAGE_MENUS
            else rx.fragment()
        ),
        spacing="2",
        align_items="center",
        flex_wrap="wrap",
        width="100%",
    )
    return rx.box(
        label,
        on_click=lambda: LaimWebState.set_menu(item),
        background=rx.cond(
            LaimWebState.sidebar_active_menu == item,
            "rgba(0, 180, 0, 0.3)",
            "transparent",
        ),
        border_left=rx.cond(
            LaimWebState.sidebar_active_menu == item,
            f"3px solid {COLORS['accent']}",
            "3px solid transparent",
        ),
        color=rx.cond(
            LaimWebState.sidebar_active_menu == item,
            COLORS["title"],
            COLORS["text"],
        ),
        width="100%",
        padding="0.55em 0.75em",
        cursor="pointer",
        _hover={"background": "rgba(0, 80, 0, 0.35)"},
    )


def sidebar_menu() -> rx.Component:
    """Menú de navegación lateral (contraído por defecto)."""
    return rx.vstack(
        rx.hstack(
            rx.text("Menú", class_name="crt-title", font_size="1em"),
            rx.spacer(),
            rx.text(
                rx.cond(LaimWebState.sidebar_menu_open, "▾", "▸"),
                class_name="crt-muted",
                font_size="0.9em",
            ),
            width="100%",
            align_items="center",
            cursor="pointer",
            padding_y="0.25em",
            margin_top="0.5em",
            on_click=LaimWebState.toggle_sidebar_menu,
        ),
        rx.cond(
            LaimWebState.sidebar_menu_open,
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
            rx.fragment(),
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
            LaimWebState.active_menu == "config_general",
            config_general_panel(),
            rx.fragment(),
        ),
        rx.match(
            LaimWebState.active_menu,
            ("inicio", inicio_home_panel()),
            ("presentacion", presentation_content_panel()),
            ("escenarios", escenarios_content_panel()),
            *(
                (item.menu, crt_markdown_viewer(load_static_page_markdown(item.menu)))
                for item in HELP_MANUALS
            ),
            crt_markdown_viewer(LaimWebState.static_page_content),
        ),
        rx.cond(
            LaimWebState.active_menu == "contacto",
            contact_form_panel(),
            rx.fragment(),
        ),
        rx.match(
            LaimWebState.active_menu,
            ("servicios", page_action_panel("servicios")),
            ("instaladores", installers_panel()),
            ("registro", registro_panel()),
            ("manuales", page_action_panel("manuales")),
            *(
                (item.menu, page_action_panel(item.menu))
                for item in HELP_MANUALS
            ),
            ("modelos_base", page_action_panel("modelos_base")),
            ("modelos_especializados", page_action_panel("modelos_especializados")),
            ("modelos_personalizados", page_action_panel("modelos_personalizados")),
            ("agents", page_action_panel("agents")),
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
        advance_construction_modal(),
        base_models_catalog_modal(),
        recommended_model_modal(),
        compare_requirements_modal(),
        ticket_create_modal(),
        ticket_status_modal(),
        ticket_notification_modal(),
        install_notification_modal(),
        install_instructions_modal(),
        class_name="crt-shell crt-theme-green",
        width="100%",
    )

"""Botones de acción por sección del portal LAIM (usuario autenticado)."""

from __future__ import annotations

from dataclasses import dataclass

import reflex as rx

from laim_web.laim_state import LaimWebState

GETMYLLM_URL = "https://www.getmyllm.com/"


@dataclass(frozen=True)
class PageAction:
    """Acción disponible bajo el contenido markdown de una sección."""

    label: str
    action_key: str
    external_url: str = ""


PAGE_ACTIONS: dict[str, tuple[PageAction, ...]] = {
    "instaladores": (
        PageAction("Descargar para Windows", "download_windows"),
        PageAction("Descargar para macOS", "download_macos"),
        PageAction("Descargar Linux (.deb)", "download_linux_deb"),
        PageAction("Descargar Linux (.rpm)", "download_linux_rpm"),
        PageAction("Requisitos del sistema", "view_requirements"),
    ),
    "manuales": (
        PageAction("Guía de instalación rápida", "manual_quickstart"),
        PageAction("Manual de usuario", "manual_user"),
        PageAction("Configuración segura", "manual_security"),
        PageAction("Uso en línea de comandos (CLI)", "manual_cli"),
    ),
    "modelos_base": (
        PageAction("Ver catálogo de modelos base", "catalog_base_models"),
        PageAction("Modelo recomendado para mi equipo", "recommended_model"),
        PageAction("Comparativa de requisitos", "compare_requirements"),
    ),
    "modelos_especializados": (
        PageAction("Explorar modelos especializados", "catalog_specialized"),
        PageAction("Solicitar proyecto a medida", "specialized_project", GETMYLLM_URL),
        PageAction("Conocer el ecosistema myllm", "myllm_ecosystem", GETMYLLM_URL),
    ),
    "modelos_personalizados": (
        PageAction("Cómo crear un modelo personalizado", "custom_howto"),
        PageAction("Abrir portal de proyectos myllm", "myllm_projects", GETMYLLM_URL),
        PageAction("Contactar con un especialista", "contact_specialist", GETMYLLM_URL),
    ),
    "skills": (
        PageAction("Biblioteca de skills", "skills_library"),
        PageAction("Instalar skill de ejemplo", "skills_sample"),
        PageAction("Crear skill propio", "skills_create"),
    ),
    "complementos": (
        PageAction("Ver complementos disponibles", "addons_catalog"),
        PageAction("Integraciones recomendadas", "addons_integrations"),
        PageAction("Notas de versión", "addons_changelog"),
    ),
    "soporte": (
        PageAction("Abrir ticket de soporte", "support_ticket"),
        PageAction("Estado de servicios", "support_status"),
        PageAction("Contactar por email", "support_email", "mailto:soporte@laim.app"),
    ),
    "faq": (
        PageAction("Privacidad y datos locales", "faq_privacy"),
        PageAction("Seguridad y buenas prácticas", "faq_security"),
        PageAction("Ir a Soporte", "faq_to_support"),
    ),
}


def _action_button(action: PageAction) -> rx.Component:
    """Renderiza un botón de acción (enlace externo o evento interno)."""
    if action.external_url:
        return rx.link(
            rx.button(action.label, class_name="crt-btn crt-btn-inline"),
            href=action.external_url,
            is_external=True,
        )
    return rx.button(
        action.label,
        on_click=LaimWebState.handle_page_action(action.action_key),
        class_name="crt-btn crt-btn-inline",
    )


def page_action_panel(menu_key: str) -> rx.Component:
    """Panel de acciones para una sección concreta del menú autenticado."""
    actions = PAGE_ACTIONS.get(menu_key, ())
    if not actions:
        return rx.fragment()

    return rx.vstack(
        rx.text(
            "Acciones disponibles",
            class_name="crt-title",
            font_size="1em",
            margin_top="0.5em",
        ),
        rx.flex(
            *[_action_button(action) for action in actions],
            wrap="wrap",
            gap="0.65em",
            width="100%",
        ),
        spacing="2",
        width="100%",
        padding_x="1.5em",
        padding_bottom="1.5em",
        padding_top="0.5em",
        border_top="1px solid rgba(0, 200, 0, 0.25)",
        margin_top="1.25em",
    )

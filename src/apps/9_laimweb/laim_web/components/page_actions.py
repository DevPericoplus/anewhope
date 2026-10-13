"""Botones de acción por sección del portal LAIM (usuario autenticado)."""

from __future__ import annotations

from dataclasses import dataclass

import reflex as rx

from laim_web.help_manuals import BACK_TO_MANUALES_ACTION, HELP_MANUALS
from laim_web.laim_state import LaimWebState

GETMYLLM_URL = "https://www.getmylllm.com/"


@dataclass(frozen=True)
class PageAction:
    """Acción disponible bajo el contenido markdown de una sección."""

    label: str
    action_key: str
    external_url: str = ""


PAGE_ACTIONS: dict[str, tuple[PageAction, ...]] = {
    # "instaladores" ya no usa este panel genérico — ver installers_panel()
    # en components/installers_panel.py (selector de edición/plataforma +
    # descarga real vía laim_product).
    "servicios": (
        PageAction("Ir a Instaladores", "go_installers"),
    ),
    "manuales": tuple(
        PageAction(item.button_label, item.action_key) for item in HELP_MANUALS
    ),
    "modelos_base": (
        PageAction("Ver catálogo de modelos base", "catalog_base_models"),
        PageAction("Modelo recomendado para mi equipo", "recommended_model"),
        PageAction("Comparativa de requisitos", "compare_requirements"),
    ),
    "modelos_especializados": (
        PageAction("Explorar modelos especializados", "catalog_specialized"),
        PageAction("Solicitar proyecto a medida", "specialized_project", GETMYLLM_URL),
        PageAction("Conocer el ecosistema mylllm", "myllm_ecosystem", GETMYLLM_URL),
    ),
    "modelos_personalizados": (
        PageAction("Cómo crear un modelo personalizado", "custom_howto"),
        PageAction("Abrir portal de proyectos mylllm", "myllm_projects", GETMYLLM_URL),
        PageAction("Contactar con un especialista", "contact_specialist", GETMYLLM_URL),
    ),
    "agents": (
        PageAction("Catálogo en el cliente", "agents_catalog"),
        PageAction("Manual de administrador", "open_manual_admin"),
        PageAction("Abrir Manuales", "manual_user"),
    ),
    "complementos": (
        PageAction("Ver complementos disponibles", "addons_catalog"),
        PageAction("Integraciones recomendadas", "addons_integrations"),
        PageAction("Notas de versión", "addons_changelog"),
    ),
    "soporte": (
        PageAction("Abrir ticket de soporte", "support_ticket"),
        PageAction("Estado de tickets", "support_status"),
        PageAction("Contactar por email", "support_email"),
    ),
    "faq": (
        PageAction("Privacidad y datos locales", "faq_privacy"),
        PageAction("Seguridad y buenas prácticas", "faq_security"),
        PageAction("Ir a Soporte", "faq_to_support"),
    ),
}

for _manual in HELP_MANUALS:
    PAGE_ACTIONS[_manual.menu] = (
        PageAction("← Volver a Manuales", BACK_TO_MANUALES_ACTION),
    )


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
        on_click=lambda: LaimWebState.handle_page_action(action.action_key),
        class_name="crt-btn crt-btn-inline",
    )


def page_action_panel(menu_key: str) -> rx.Component:
    """Panel de acciones para una sección concreta del menú autenticado."""
    actions = PAGE_ACTIONS.get(menu_key, ())
    if not actions:
        return rx.fragment()

    heading = "Abrir un manual" if menu_key == "manuales" else "Acciones disponibles"
    return rx.vstack(
        rx.text(
            heading,
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

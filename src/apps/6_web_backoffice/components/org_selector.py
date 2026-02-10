"""Componentes UI reutilizables de selector de organización/proyecto/versión.

Estos componentes generan la barra de selectores que aparece en la parte
superior de múltiples páginas del backoffice para filtrar contenido por
organización, proyecto y/o versión.

El estilo visual sigue el patrón establecido en ``estado_proyectos.py``:
- Labels naranjas (#FF8C00) con font_weight="bold"
- ``rx.select`` con size="3" y ancho 100%
- Distribución horizontal equitativa

Uso::

    from components.org_selector import (
        org_selector_bar,
        org_project_selector_bar,
        org_project_version_selector_bar,
    )

    # En la función de layout de la página:
    def mi_pagina_panel():
        return rx.vstack(
            org_selector_bar(
                org_names=MiState.organization_names,
                selected_org_display=MiState.selected_org_display,
                on_org_change=MiState.set_organization,
            ),
            # ... contenido de la página
        )
"""

from typing import Any, Callable

import reflex as rx


# ============================================================================
# Constantes de estilo (alineadas con tema backoffice)
# ============================================================================

LABEL_COLOR = "#FF8C00"
LABEL_FONT_SIZE = "1.1em"
LABEL_FONT_WEIGHT = "bold"
SELECT_SIZE = "3"
SELECTOR_SPACING = "3"
SELECTOR_MARGIN_BOTTOM = "2em"
DEFAULT_ORG_PLACEHOLDER = "Seleccione organización"
DEFAULT_ORG_LABEL = "Organización"

# Estilo estándar para selectores en fondo oscuro (garantiza legibilidad)
SELECT_STYLE = {
    "backgroundColor": "#3a3a3a",
    "color": "#f2f2f5",
    "borderColor": "#555",
}


# ============================================================================
# Componentes de selector
# ============================================================================


def _selector_column(
    label: str,
    items: rx.Var,
    value: rx.Var,
    on_change: Any,
    placeholder: str,
    width: str = "100%",
) -> rx.Component:
    """Columna individual de un selector (label + select)."""
    return rx.vstack(
        rx.text(
            label,
            font_size=LABEL_FONT_SIZE,
            color=LABEL_COLOR,
            font_weight=LABEL_FONT_WEIGHT,
        ),
        rx.select(
            items,
            value=value,
            on_change=on_change,
            placeholder=placeholder,
            width="100%",
            size=SELECT_SIZE,
            style=SELECT_STYLE,
        ),
        spacing="1",
        width=width,
    )


def org_selector_bar(
    org_names: rx.Var,
    selected_org_display: rx.Var,
    on_org_change: Any,
    placeholder: str = DEFAULT_ORG_PLACEHOLDER,
) -> rx.Component:
    """Barra con selector de organización únicamente.

    Para páginas que solo necesitan filtrar por organización:
    Organizacion, Tecnologias, Seguimiento.

    Args:
        org_names: Var con lista de nombres de organizaciones.
        selected_org_display: Var con nombre de org seleccionada.
        on_org_change: Event handler al cambiar organización.
        placeholder: Texto placeholder del selector.

    Returns:
        Componente ``rx.hstack`` con un selector de organización.
    """
    return rx.hstack(
        _selector_column(
            label=DEFAULT_ORG_LABEL,
            items=org_names,
            value=selected_org_display,
            on_change=on_org_change,
            placeholder=placeholder,
            width="100%",
        ),
        spacing=SELECTOR_SPACING,
        width="100%",
        margin_bottom=SELECTOR_MARGIN_BOTTOM,
    )


def org_project_selector_bar(
    org_names: rx.Var,
    selected_org_display: rx.Var,
    on_org_change: Any,
    project_names: rx.Var,
    selected_project_display: rx.Var,
    on_project_change: Any,
    org_placeholder: str = DEFAULT_ORG_PLACEHOLDER,
    project_placeholder: str = "Seleccione proyecto",
) -> rx.Component:
    """Barra con selector de organización + proyecto.

    Para páginas que filtran por organización y proyecto:
    Flujos, Proyecciones, Informes.

    Args:
        org_names: Var con lista de nombres de organizaciones.
        selected_org_display: Var con nombre de org seleccionada.
        on_org_change: Event handler al cambiar organización.
        project_names: Var con lista de nombres de proyectos.
        selected_project_display: Var con nombre de proyecto seleccionado.
        on_project_change: Event handler al cambiar proyecto.
        org_placeholder: Texto placeholder del selector de organización.
        project_placeholder: Texto placeholder del selector de proyecto.

    Returns:
        Componente ``rx.hstack`` con dos selectores.
    """
    return rx.hstack(
        _selector_column(
            label=DEFAULT_ORG_LABEL,
            items=org_names,
            value=selected_org_display,
            on_change=on_org_change,
            placeholder=org_placeholder,
            width="50%",
        ),
        _selector_column(
            label="Proyecto",
            items=project_names,
            value=selected_project_display,
            on_change=on_project_change,
            placeholder=project_placeholder,
            width="50%",
        ),
        spacing=SELECTOR_SPACING,
        width="100%",
        margin_bottom=SELECTOR_MARGIN_BOTTOM,
    )


def org_project_version_selector_bar(
    org_names: rx.Var,
    selected_org_display: rx.Var,
    on_org_change: Any,
    project_names: rx.Var,
    selected_project_display: rx.Var,
    on_project_change: Any,
    version_numbers: rx.Var,
    selected_version_display: rx.Var,
    on_version_change: Any,
    org_placeholder: str = DEFAULT_ORG_PLACEHOLDER,
    project_placeholder: str = "Seleccione proyecto",
    version_placeholder: str = "Seleccione versión",
) -> rx.Component:
    """Barra con selector de organización + proyecto + versión.

    Para páginas que necesitan los tres niveles de filtrado:
    Estado Proyectos.

    Args:
        org_names: Var con lista de nombres de organizaciones.
        selected_org_display: Var con nombre de org seleccionada.
        on_org_change: Event handler al cambiar organización.
        project_names: Var con lista de nombres de proyectos.
        selected_project_display: Var con nombre de proyecto seleccionado.
        on_project_change: Event handler al cambiar proyecto.
        version_numbers: Var con lista de números de versión.
        selected_version_display: Var con versión seleccionada.
        on_version_change: Event handler al cambiar versión.
        org_placeholder: Texto placeholder del selector de organización.
        project_placeholder: Texto placeholder del selector de proyecto.
        version_placeholder: Texto placeholder del selector de versión.

    Returns:
        Componente ``rx.hstack`` con tres selectores.
    """
    return rx.hstack(
        _selector_column(
            label=DEFAULT_ORG_LABEL,
            items=org_names,
            value=selected_org_display,
            on_change=on_org_change,
            placeholder=org_placeholder,
            width="33%",
        ),
        _selector_column(
            label="Proyecto",
            items=project_names,
            value=selected_project_display,
            on_change=on_project_change,
            placeholder=project_placeholder,
            width="33%",
        ),
        _selector_column(
            label="Versión",
            items=version_numbers,
            value=selected_version_display,
            on_change=on_version_change,
            placeholder=version_placeholder,
            width="33%",
        ),
        spacing=SELECTOR_SPACING,
        width="100%",
        margin_bottom=SELECTOR_MARGIN_BOTTOM,
    )

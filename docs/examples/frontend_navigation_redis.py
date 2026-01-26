"""
Componente de navegación para el Frontend
Con botón de acceso al Backoffice (condicional)
"""
import reflex as rx
from .state.shared_session_state import SharedSessionState


def navigation_header() -> rx.Component:
    """
    Barra de navegación superior del frontend
    
    Muestra el botón "Backoffice" solo si:
    - El usuario está logueado
    - Tiene el permiso training_create = True
    """
    return rx.hstack(
        # Logo o título
        rx.heading(
            "Myllm",
            size="7",
            color="#00FF00",
            weight="bold",
        ),
        
        rx.spacer(),
        
        # Información del usuario (solo si está logueado)
        rx.cond(
            SharedSessionState.is_logged_in,
            rx.hstack(
                # Nombre del usuario
                rx.text(
                    SharedSessionState.user_name,
                    size="3",
                    weight="medium",
                ),
                
                # Email
                rx.text(
                    f"({SharedSessionState.user_email})",
                    size="2",
                    color="gray",
                ),
                
                # Separador
                rx.divider(
                    orientation="vertical",
                    height="20px",
                ),
                
                # Botón Backoffice (condicional)
                rx.cond(
                    SharedSessionState.can_access_backoffice,
                    rx.button(
                        rx.icon("wrench", size=18),
                        "Backoffice",
                        on_click=SharedSessionState.go_to_backoffice,
                        color_scheme="orange",
                        variant="solid",
                        size="2",
                    ),
                ),
                
                # Botón Desconectar
                rx.button(
                    rx.icon("log-out", size=18),
                    "Desconectar",
                    on_click=SharedSessionState.logout,
                    color_scheme="red",
                    variant="outline",
                    size="2",
                ),
                
                spacing="3",
                align="center",
            ),
        ),
        
        width="100%",
        padding="1em 2em",
        background_color="#1a1a1a",
        border_bottom="1px solid #00FF00",
        position="sticky",
        top="0",
        z_index="1000",
    )


def backoffice_access_card() -> rx.Component:
    """
    Tarjeta informativa sobre el acceso al backoffice
    
    Se muestra en el dashboard del usuario si tiene permisos
    """
    return rx.cond(
        SharedSessionState.can_access_backoffice,
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("wrench", size=32, color="orange"),
                    rx.heading(
                        "Acceso al Backoffice",
                        size="5",
                        color="orange",
                    ),
                    spacing="3",
                    align="center",
                ),
                
                rx.text(
                    "Tienes acceso a la consola administrativa del sistema.",
                    size="3",
                ),
                
                rx.text(
                    "Desde el backoffice puedes gestionar entrenamientos de modelos, "
                    "datasets, configuraciones avanzadas y más.",
                    size="2",
                    color="gray",
                ),
                
                rx.button(
                    rx.icon("arrow-right", size=18),
                    "Ir al Backoffice",
                    on_click=SharedSessionState.go_to_backoffice,
                    color_scheme="orange",
                    size="3",
                    width="100%",
                ),
                
                spacing="4",
                align="start",
            ),
            max_width="500px",
        ),
    )

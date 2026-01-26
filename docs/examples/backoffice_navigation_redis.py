"""
Componente de navegación para el Backoffice
Con botón para volver al Frontend
"""
import reflex as rx
from .state.shared_session_state import SharedSessionState


def backoffice_header() -> rx.Component:
    """
    Barra de navegación superior del backoffice
    
    Estilo naranja en lugar de verde
    """
    return rx.hstack(
        # Logo/título del backoffice
        rx.hstack(
            rx.icon("wrench", size=28, color="#FF8C00"),
            rx.heading(
                "Backoffice",
                size="7",
                color="#FF8C00",
                weight="bold",
            ),
            spacing="3",
            align="center",
        ),
        
        rx.spacer(),
        
        # Información del usuario
        rx.hstack(
            # Nombre del usuario
            rx.text(
                SharedSessionState.user_name,
                size="3",
                weight="medium",
                color="white",
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
            
            # Botón volver al Frontend
            rx.button(
                rx.icon("arrow-left", size=18),
                "Volver al Frontend",
                on_click=SharedSessionState.go_to_frontend,
                color_scheme="orange",
                variant="outline",
                size="2",
            ),
            
            # Botón Desconectar
            rx.button(
                rx.icon("log-out", size=18),
                "Desconectar",
                on_click=SharedSessionState.logout,
                color_scheme="red",
                variant="solid",
                size="2",
            ),
            
            spacing="3",
            align="center",
        ),
        
        width="100%",
        padding="1em 2em",
        background_color="#1a1a1a",
        border_bottom="2px solid #FF8C00",
        position="sticky",
        top="0",
        z_index="1000",
    )


def backoffice_guard() -> rx.Component:
    """
    Componente de protección para el backoffice
    
    Redirige al frontend si:
    - El usuario no está logueado
    - No tiene permisos de backoffice
    
    Se debe usar en la función on_load de cada página del backoffice
    """
    return rx.fragment(
        rx.cond(
            ~SharedSessionState.is_logged_in,
            rx.redirect("/"),
        ),
        rx.cond(
            ~SharedSessionState.can_access_backoffice,
            rx.redirect("/"),
        ),
    )


def backoffice_dashboard() -> rx.Component:
    """
    Dashboard principal del backoffice
    
    Incluye métricas y accesos rápidos
    """
    return rx.vstack(
        # Header
        backoffice_header(),
        
        # Guard (validación de acceso)
        backoffice_guard(),
        
        # Contenido principal
        rx.container(
            rx.vstack(
                # Título
                rx.heading(
                    "Panel de Administración",
                    size="8",
                    color="#FF8C00",
                ),
                
                rx.text(
                    f"Bienvenido, {SharedSessionState.user_name}",
                    size="4",
                    color="gray",
                ),
                
                # Grid de tarjetas de acceso rápido
                rx.grid(
                    # Gestión de entrenamientos
                    rx.card(
                        rx.vstack(
                            rx.icon("zap", size=40, color="#FF8C00"),
                            rx.heading("Entrenamientos", size="5"),
                            rx.text(
                                "Crear y gestionar entrenamientos de modelos",
                                size="2",
                                color="gray",
                            ),
                            rx.button(
                                "Ir a Entrenamientos",
                                color_scheme="orange",
                                width="100%",
                            ),
                            spacing="3",
                            align="center",
                        ),
                    ),
                    
                    # Gestión de datasets
                    rx.card(
                        rx.vstack(
                            rx.icon("database", size=40, color="#FF8C00"),
                            rx.heading("Datasets", size="5"),
                            rx.text(
                                "Administrar conjuntos de datos",
                                size="2",
                                color="gray",
                            ),
                            rx.button(
                                "Ir a Datasets",
                                color_scheme="orange",
                                width="100%",
                            ),
                            spacing="3",
                            align="center",
                        ),
                    ),
                    
                    # Gestión de modelos
                    rx.card(
                        rx.vstack(
                            rx.icon("cpu", size=40, color="#FF8C00"),
                            rx.heading("Modelos", size="5"),
                            rx.text(
                                "Ver y administrar modelos entrenados",
                                size="2",
                                color="gray",
                            ),
                            rx.button(
                                "Ir a Modelos",
                                color_scheme="orange",
                                width="100%",
                            ),
                            spacing="3",
                            align="center",
                        ),
                    ),
                    
                    # Configuración del sistema
                    rx.card(
                        rx.vstack(
                            rx.icon("settings", size=40, color="#FF8C00"),
                            rx.heading("Configuración", size="5"),
                            rx.text(
                                "Ajustes avanzados del sistema",
                                size="2",
                                color="gray",
                            ),
                            rx.button(
                                "Ir a Configuración",
                                color_scheme="orange",
                                width="100%",
                            ),
                            spacing="3",
                            align="center",
                        ),
                    ),
                    
                    columns="2",
                    spacing="4",
                    width="100%",
                ),
                
                # Información de sesión (para debugging)
                rx.divider(margin_y="2em"),
                
                rx.card(
                    rx.vstack(
                        rx.heading("Información de Sesión", size="4"),
                        rx.text(f"User ID: {SharedSessionState.user_id}"),
                        rx.text(f"Organización ID: {SharedSessionState.organization_id}"),
                        rx.text(f"Session ID: {SharedSessionState.session_id}"),
                        rx.text(f"Almacenado en: Redis"),
                        spacing="2",
                        align="start",
                    ),
                    max_width="600px",
                ),
                
                spacing="6",
                align="start",
                width="100%",
            ),
            max_width="1200px",
            padding="2em",
        ),
        
        width="100%",
        min_height="100vh",
        background_color="#0a0a0a",
    )

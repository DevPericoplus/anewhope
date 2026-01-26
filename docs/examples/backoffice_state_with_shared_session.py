"""
Ejemplo de integración de SharedSessionState en el backoffice.

Este archivo muestra cómo usar SharedSessionState en web_backoffice
para acceder a la sesión del usuario y gestionar la navegación.

Ubicación sugerida: src/apps/6_web_backoffice/web_backoffice/state.py
"""
import reflex as rx
import sys
import importlib.util
from pathlib import Path


# Cargar SharedSessionState dinámicamente
def _load_shared_session_state():
    """Carga SharedSessionState evitando SyntaxError con nombres numéricos."""
    shared_state_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "2_shared_application"
        / "reflex_shared"
        / "shared_session_state.py"
    )
    spec = importlib.util.spec_from_file_location(
        "shared_session_state", shared_state_path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["shared_session_state"] = module
    spec.loader.exec_module(module)
    return module.SharedSessionState


SharedSessionState = _load_shared_session_state()


class BackofficeState(SharedSessionState):
    """
    Estado del backoffice que extiende SharedSessionState.
    
    Hereda automáticamente:
    - Todos los campos del usuario (sincronizados desde frontend)
    - Todos los permisos de bajo nivel
    - Tokens JWT
    - Metadata de sesión
    - Métodos de navegación (go_to_backoffice, go_to_frontend, logout)
    
    IMPORTANTE: 
    - Este estado NO maneja login (solo el frontend lo hace)
    - Los datos vienen automáticamente desde el frontend vía Redis
    - Solo puede accederse si can_access_backoffice == True
    """
    
    # Estado específico del backoffice (no compartido)
    selected_project: str = ""
    selected_version: str = ""
    
    def check_access(self):
        """
        Verifica que el usuario tiene acceso al backoffice.
        
        Si no tiene acceso, redirige automáticamente al frontend.
        Debe ser llamado en el on_load de cada página del backoffice.
        """
        if not self.can_access_backoffice:
            return self.go_to_frontend()
    
    def select_project(self, project_name: str):
        """
        Selecciona un proyecto.
        
        Args:
            project_name: Nombre del proyecto seleccionado
        """
        self.selected_project = project_name
        self.update_activity()
    
    def select_version(self, version_id: str):
        """
        Selecciona una versión.
        
        Args:
            version_id: ID de la versión seleccionada
        """
        self.selected_version = version_id
        self.update_activity()


# =============================================================================
# COMPONENTES DE EJEMPLO
# =============================================================================


def backoffice_header() -> rx.Component:
    """
    Cabecera del backoffice con información del usuario.
    
    Muestra el nombre del usuario y botón para volver al frontend.
    Usa color naranja para diferenciar del frontend (verde).
    """
    return rx.hstack(
        rx.heading("Backoffice", size="lg", color="orange.600"),
        rx.spacer(),
        rx.vstack(
            rx.text(
                BackofficeState.user_display_name,
                font_weight="bold",
                font_size="16px",
            ),
            rx.text(
                BackofficeState.user_display_email,
                font_size="14px",
                color="gray",
            ),
            align_items="flex-end",
            spacing="0",
        ),
        rx.button(
            "Volver al Frontend",
            on_click=BackofficeState.go_to_frontend,
            bg="green.500",
            color="white",
            _hover={"bg": "green.600"},
        ),
        rx.button(
            "Desconectar",
            on_click=BackofficeState.logout,
            bg="red.500",
            color="white",
            _hover={"bg": "red.600"},
        ),
        width="100%",
        padding="1em",
        bg="orange.100",
        border_radius="8px",
    )


def backoffice_guard() -> rx.Component:
    """
    Componente de protección para páginas del backoffice.
    
    Verifica automáticamente si el usuario tiene acceso.
    Si no tiene acceso, muestra mensaje y redirige al frontend.
    
    Uso:
        def backoffice_page():
            return rx.vstack(
                backoffice_guard(),  # Primera línea de cada página
                # ... resto del contenido ...
            )
    """
    return rx.cond(
        BackofficeState.can_access_backoffice,
        rx.fragment(),  # Usuario tiene acceso, no mostrar nada
        # Usuario NO tiene acceso, mostrar mensaje y redirigir
        rx.vstack(
            rx.heading("Acceso Denegado", size="lg", color="red.600"),
            rx.text(
                "No tienes permisos para acceder al backoffice.",
                font_size="16px",
            ),
            rx.text(
                "Redirigiendo al frontend...",
                font_size="14px",
                color="gray",
            ),
            on_mount=BackofficeState.check_access,  # Redirige automáticamente
            spacing="1em",
            padding="2em",
        ),
    )


def backoffice_dashboard() -> rx.Component:
    """
    Dashboard principal del backoffice.
    
    Muestra tarjetas con acceso rápido a funcionalidades administrativas.
    """
    return rx.vstack(
        backoffice_guard(),  # Protección de acceso
        backoffice_header(),  # Cabecera con info del usuario
        rx.divider(),
        rx.heading("Panel de Administración", size="xl", color="orange.600"),
        # Tarjetas de acceso rápido
        rx.grid(
            # Tarjeta de entrenamientos
            rx.card(
                rx.vstack(
                    rx.icon("brain", size=40, color="orange.500"),
                    rx.heading("Entrenamientos", size="md"),
                    rx.text("Gestionar entrenamientos de modelos LLM"),
                    rx.button(
                        "Acceder",
                        bg="orange.500",
                        color="white",
                        width="100%",
                        _hover={"bg": "orange.600"},
                    ),
                    spacing="0.5em",
                ),
                padding="1.5em",
            ),
            # Tarjeta de modelos
            rx.card(
                rx.vstack(
                    rx.icon("box", size=40, color="orange.500"),
                    rx.heading("Modelos", size="md"),
                    rx.text("Gestionar modelos publicados"),
                    rx.button(
                        "Acceder",
                        bg="orange.500",
                        color="white",
                        width="100%",
                        _hover={"bg": "orange.600"},
                    ),
                    spacing="0.5em",
                ),
                padding="1.5em",
            ),
            # Tarjeta de datasets
            rx.card(
                rx.vstack(
                    rx.icon("database", size=40, color="orange.500"),
                    rx.heading("Datasets", size="md"),
                    rx.text("Gestionar conjuntos de datos"),
                    rx.button(
                        "Acceder",
                        bg="orange.500",
                        color="white",
                        width="100%",
                        _hover={"bg": "orange.600"},
                    ),
                    spacing="0.5em",
                ),
                padding="1.5em",
            ),
            # Tarjeta de usuarios
            rx.card(
                rx.vstack(
                    rx.icon("users", size=40, color="orange.500"),
                    rx.heading("Usuarios", size="md"),
                    rx.text("Gestionar usuarios y permisos"),
                    rx.button(
                        "Acceder",
                        bg="orange.500",
                        color="white",
                        width="100%",
                        _hover={"bg": "orange.600"},
                    ),
                    spacing="0.5em",
                ),
                padding="1.5em",
            ),
            columns="2",
            gap="1.5em",
            width="100%",
        ),
        rx.divider(),
        # Información de sesión
        rx.card(
            rx.vstack(
                rx.heading("Información de Sesión", size="sm", color="orange.600"),
                rx.grid(
                    rx.text("Usuario:", font_weight="bold"),
                    rx.text(BackofficeState.user_display_name),
                    rx.text("Email:", font_weight="bold"),
                    rx.text(BackofficeState.user_display_email),
                    rx.text("Organización ID:", font_weight="bold"),
                    rx.text(BackofficeState.organization_id),
                    rx.text("Última actividad:", font_weight="bold"),
                    rx.text(BackofficeState.last_activity),
                    columns="2",
                    gap="0.5em",
                ),
                spacing="0.5em",
                align_items="stretch",
            ),
            padding="1em",
            bg="orange.50",
        ),
        spacing="1em",
        padding="2em",
        width="100%",
    )

"""
Ejemplo de integración de SharedSessionState en el frontend.

Este archivo muestra cómo usar SharedSessionState en web_frontend
para gestionar la sesión del usuario y la navegación al backoffice.

Ubicación sugerida: src/apps/5_web_frontend/web_frontend/state.py
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


class FrontendState(SharedSessionState):
    """
    Estado del frontend que extiende SharedSessionState.
    
    Hereda automáticamente:
    - Todos los campos del usuario
    - Todos los permisos de bajo nivel
    - Tokens JWT
    - Metadata de sesión
    - Métodos de navegación (go_to_backoffice, go_to_frontend, logout)
    """
    
    # Estado específico del frontend (no compartido)
    show_login_modal: bool = False
    error_message: str = ""
    
    def handle_login_success(
        self,
        user_id: int,
        organization_id: int,
        identity_type_id: int,
        user_name: str,
        user_email: str,
        user_mobile: str,
        access_token: str,
        session_token: str,
        permissions: dict,
    ):
        """
        Maneja el login exitoso.
        
        Carga los datos del usuario en SharedSessionState, que se sincroniza
        automáticamente con el backoffice vía Redis.
        
        Args:
            user_id: ID del usuario
            organization_id: ID de la organización
            identity_type_id: ID del tipo de identidad
            user_name: Nombre del usuario
            user_email: Email del usuario
            user_mobile: Teléfono del usuario
            access_token: Token JWT de acceso
            session_token: Token JWT de sesión
            permissions: Diccionario con permisos de bajo nivel
        """
        # Cargar datos en estado compartido
        self.load_user_data(
            user_id=user_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
            user_name=user_name,
            user_email=user_email,
            user_mobile=user_mobile,
            access_token=access_token,
            session_token=session_token,
            permissions=permissions,
        )
        
        # Cerrar modal y limpiar errores (estado local del frontend)
        self.show_login_modal = False
        self.error_message = ""
    
    def handle_login_error(self, error_message: str):
        """
        Maneja errores de login.
        
        Args:
            error_message: Mensaje de error a mostrar
        """
        self.error_message = error_message
        self.show_login_modal = True
    
    def open_login_modal(self):
        """Abre el modal de login."""
        self.show_login_modal = True
        self.error_message = ""
    
    def close_login_modal(self):
        """Cierra el modal de login."""
        self.show_login_modal = False
        self.error_message = ""


# =============================================================================
# COMPONENTES DE EJEMPLO
# =============================================================================


def user_header() -> rx.Component:
    """
    Componente de cabecera que muestra información del usuario.
    
    Muestra el nombre y email del usuario logueado.
    Si el usuario tiene permiso training_create, muestra botón "Backoffice".
    """
    return rx.cond(
        FrontendState.is_logged_in,
        rx.hstack(
            rx.vstack(
                rx.text(
                    FrontendState.user_display_name,
                    font_weight="bold",
                    font_size="16px",
                ),
                rx.text(
                    FrontendState.user_display_email,
                    font_size="14px",
                    color="gray",
                ),
                align_items="flex-start",
                spacing="0",
            ),
            rx.spacer(),
            # Botón Backoffice (solo si tiene permiso)
            rx.cond(
                FrontendState.can_access_backoffice,
                rx.button(
                    "Backoffice",
                    on_click=FrontendState.go_to_backoffice,
                    bg="orange.500",
                    color="white",
                    _hover={"bg": "orange.600"},
                ),
            ),
            # Botón Desconectar
            rx.button(
                "Desconectar",
                on_click=FrontendState.logout,
                bg="red.500",
                color="white",
                _hover={"bg": "red.600"},
            ),
            width="100%",
            padding="1em",
            bg="gray.100",
            border_radius="8px",
        ),
    )


def backoffice_access_card() -> rx.Component:
    """
    Tarjeta informativa sobre acceso al backoffice.
    
    Muestra información sobre los permisos administrativos del usuario.
    Solo visible si el usuario tiene acceso al backoffice.
    """
    return rx.cond(
        FrontendState.can_access_backoffice,
        rx.card(
            rx.vstack(
                rx.heading("Acceso Administrativo", size="md"),
                rx.text(
                    "Tienes permisos para acceder al backoffice de administración.",
                    font_size="14px",
                ),
                rx.divider(),
                rx.text("Permisos disponibles:", font_weight="bold", font_size="14px"),
                rx.list(
                    rx.list_item("✅ Crear entrenamientos"),
                    rx.list_item("✅ Ejecutar entrenamientos"),
                    rx.list_item("✅ Monitorear entrenamientos"),
                    font_size="13px",
                ),
                rx.button(
                    "Ir al Backoffice",
                    on_click=FrontendState.go_to_backoffice,
                    bg="orange.500",
                    color="white",
                    width="100%",
                    _hover={"bg": "orange.600"},
                ),
                spacing="0.5em",
                align_items="stretch",
            ),
            width="100%",
            max_width="400px",
            padding="1.5em",
            bg="orange.50",
            border="1px solid",
            border_color="orange.300",
        ),
    )

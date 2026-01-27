import base64
import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import reflex as rx

from adapters.api_client import (
    get_user_permissions,
    login_user,
    logout_user,
    refresh_tokens,
    request_login_otp,
)
from pages.flujos import FlujosState, flujos_diagram, load_flujos_content
from pages.organizacion import load_organizacion_content
from low_panel_pages.show_md import show_md  # noqa: F401 - Importado para registrar la ruta
from web_frontend.shared_state import SharedSessionState

# Importar logger de actividad usando importlib (el directorio tiene número)
_activity_logger_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "reflex_shared" / "activity_logger.py"
_spec = importlib.util.spec_from_file_location("activity_logger", _activity_logger_path)
_activity_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_activity_module)

# Logger de actividad del frontend
activity_log = _activity_module.get_frontend_logger()
activity_log.log_startup()

COLORS = {
    "background": "#1a1a1a",
    "card": "#2d2d2d",
    "foreground": "#f2f2f5",
    "primary": "#22c55e",
    "secondary": "#383854",
    "border": "#404040",
    "input": "#3a3a3a",
    "muted_foreground": "#E0E0E0",
    "accent": "#22c55e",
}

# Define the State class for managing application state
class State(SharedSessionState):
    """Main application state with Redis-based session sharing."""
    
    # User portal state (campos locales del frontend, no compartidos)
    user_active_menu: str = "inicio"
    user_username: str = ""
    user_password: str = ""
    user_otp: str = ""
    user_active_tab: str = "resumen"
    user_permissions: list[dict[str, str]] = []
    login_error: str = ""
    otp_request_message: str = ""
    
    # Nota: Los siguientes campos ya vienen de SharedSessionState:
    # - user_logged_in, access_token, session_token, user_id, organization_id
    # - user_name, user_email, user_mobile, identity_type_id
    # - 45 permisos (can_training_create, can_folder_rename, etc.)
    # - Métodos: load_user_data(), clear_session(), go_to_backoffice(), etc.
    
    def set_user_menu(self, menu: str):
        """Set active menu item for user portal."""
        self.user_active_menu = menu
        # Log de navegación
        if self.is_logged_in and self.user_id > 0:
            activity_log.log_navigation(self.user_id, menu)
        if menu == "flujos":
            organization_id = self.organization_id
            if organization_id <= 0 and self.access_token:
                organization_id = self._extract_org_id_from_token(self.access_token)
                if organization_id > 0:
                    self.organization_id = organization_id
            return FlujosState.initialize_from_session(organization_id)

    def on_page_load(self):
        """
        Ejecuta acciones al recargar la página.
        
        Si el usuario viene del backoffice con parámetros de sesión en la URL,
        restaura la sesión automáticamente.
        """
        # Leer tokens de query params (pasados desde el backoffice)
        params = self.router.page.params
        access_token = params.get("access_token", "")
        session_token = params.get("session_token", "")
        user_id = params.get("user_id", "")
        org_id = params.get("org_id", "")
        
        # Debug
        print(f"[DEBUG] on_page_load: access_token={bool(access_token)}, session_token={bool(session_token)}, user_id={user_id}")
        print(f"[DEBUG] on_page_load: is_logged_in={self.is_logged_in}, current params count={len(params)}")
        
        # Si vienen tokens en la URL, SIEMPRE restaurar sesión
        # (el usuario puede venir del backoffice con tokens válidos)
        if access_token and session_token:
            print(f"[DEBUG] Tokens encontrados en URL, restaurando sesión...")
            return self.restore_session_from_url(
                access_token, session_token, user_id, org_id
            )
        
        print(f"[DEBUG] No tokens in URL, is_logged_in={self.is_logged_in}")
        
        # Si el usuario ya está logueado y está en flujos, inicializar
        if self.user_active_menu == "flujos":
            organization_id = self.organization_id
            if organization_id <= 0 and self.access_token:
                organization_id = self._extract_org_id_from_token(self.access_token)
                if organization_id > 0:
                    self.organization_id = organization_id
            return FlujosState.initialize_from_session(organization_id)
    
    def restore_session_from_url(
        self, access_token: str, session_token: str, user_id: str, org_id: str
    ):
        """
        Restaura la sesión del usuario desde los parámetros de URL.
        Se usa cuando el usuario viene del backoffice.
        
        Args:
            access_token: Token JWT de acceso
            session_token: Token de sesión
            user_id: ID del usuario
            org_id: ID de la organización
        
        Returns:
            None si la sesión se restauró correctamente
        """
        if not access_token or not session_token:
            return None
        
        # Log para debug
        activity_log.log_session_activity(
            int(user_id) if user_id else 0,
            f"Restaurando sesión desde URL | org_id={org_id}"
        )
        
        try:
            # Restaurar tokens y datos básicos PRIMERO
            self.access_token = access_token
            self.session_token = session_token
            self.user_id = int(user_id) if user_id else 0
            self.organization_id = int(org_id) if org_id else 0
            self.is_logged_in = True  # Marcar como logueado inmediatamente
            self.current_app = "frontend"
            self.user_active_menu = "organizacion"  # Menú por defecto
            
            # Cargar permisos desde el middleware
            permissions_response = get_user_permissions(access_token, session_token)
            
            if permissions_response:
                # Actualizar permisos de bajo nivel
                low_level_permissions = permissions_response.get("low_level_permissions", {})
                self._load_permissions(low_level_permissions)
                
                # Actualizar datos de usuario adicionales
                self.identity_type_id = int(permissions_response.get("identity_type_id", self.identity_type_id))
                self.user_name = permissions_response.get("user_name", "")
                self.user_email = permissions_response.get("user_email", "")
                
                # Actualizar timestamp de actividad
                self.update_activity()
                
                activity_log.log_session_activity(
                    self.user_id,
                    "Sesión restaurada exitosamente | permisos cargados"
                )
            else:
                # Si no se pudieron cargar permisos, al menos el usuario está logueado
                activity_log.log_session_activity(
                    self.user_id,
                    "Sesión restaurada sin permisos del middleware"
                )
                
        except Exception as exc:
            # Si falla, el usuario verá el formulario de login
            self.login_error = f"Error al restaurar sesión: {str(exc)}"
            self.is_logged_in = False
            activity_log.log_session_activity(
                int(user_id) if user_id else 0,
                f"Error restaurando sesión: {str(exc)}"
            )
        
        return None

    def _extract_org_id_from_token(self, token: str) -> int:
        """Extrae organization_id desde el payload del JWT."""

        try:
            parts = token.split(".")
            if len(parts) < 2:
                return 0
            payload = parts[1]
            padded = payload + "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            return int(data.get("organization_id", 0))
        except Exception:
            return 0
    
    def set_user_username(self, username: str):
        """Set user username."""
        self.user_username = username
    
    def set_user_password(self, password: str):
        """Set user password."""
        self.user_password = password

    def set_user_otp(self, otp: str):
        """Set user OTP."""
        self.user_otp = otp
    
    def user_login(self):
        """Handle user portal login."""
        if not self.user_username or not self.user_password or not self.user_otp:
            self.login_error = "Debe ingresar usuario, contraseña y OTP"
            activity_log.warning(f"LOGIN ATTEMPT | incomplete credentials | user={self.user_username or 'empty'}")
            return

        activity_log.log_middleware_request("/auth/login", "POST")
        response = login_user(self.user_username, self.user_password, self.user_otp)
        access_token = response.get("access_token")
        session_token = response.get("session_token")
        if not access_token or not session_token:
            self.login_error = "No se pudo autenticar con el middleware"
            activity_log.log_user_login(self.user_username, success=False)
            return

        # Obtener permisos del usuario
        activity_log.log_middleware_request("/auth/permissions", "GET")
        permissions_response = get_user_permissions(access_token, session_token)
        permissions_list = permissions_response.get("permissions", [])
        
        # Los permisos de bajo nivel (training_create, folder_rename, etc.)
        # vienen como diccionario directamente del middleware
        low_level_permissions = permissions_response.get("low_level_permissions", {})
        
        user_id = int(response.get("user_id", 0))
        
        # Cargar datos en SharedSessionState con low_level_permissions
        # Estos permisos determinan funcionalidades como acceso al Backoffice
        self.load_user_data(
            user_id=user_id,
            organization_id=int(response.get("organization_id", 0)),
            identity_type_id=int(response.get("identity_type_id", 0)),
            user_name=self.user_username,
            user_email=response.get("email", ""),
            user_mobile=response.get("mobile", ""),
            access_token=access_token,
            session_token=session_token,
            permissions=low_level_permissions,
        )
        
        # Actualizar estado local del frontend
        self.is_logged_in = True
        self.login_error = ""
        self.otp_request_message = ""
        self.user_active_menu = "organizacion"
        self.user_permissions = permissions_list  # basic_permissions para UI
        
        # Log de login exitoso
        activity_log.log_user_login(self.user_username, success=True, user_id=user_id)
    
    def user_logout(self):
        """Handle user portal logout."""
        # Guardar datos para log antes de limpiar
        logout_user_id = self.user_id
        logout_username = self.user_name or self.user_username
        
        if self.access_token and self.session_token:
            activity_log.log_middleware_request("/auth/logout", "POST")
            logout_user(self.access_token, self.session_token)
        
        # Log de logout
        if logout_user_id > 0:
            activity_log.log_user_logout(logout_user_id, logout_username)
        
        # Limpiar SharedSessionState (se sincroniza automáticamente con Redis)
        self.clear_session()
        
        # Limpiar estado local del frontend
        self.is_logged_in = False
        self.user_username = ""
        self.user_password = ""
        self.user_otp = ""
        self.user_permissions = []
        self.login_error = ""
        self.otp_request_message = ""
        self.user_active_menu = "inicio"
        
        return rx.redirect("/")

    def refresh_session_tokens(self):
        """Renueva los tokens de sesión mediante el middleware."""

        if not self.session_token:
            self.login_error = "No hay sesión activa para renovar"
            return
        response = refresh_tokens(self.session_token)
        access_token = response.get("access_token")
        session_token = response.get("session_token")
        if not access_token or not session_token:
            self.login_error = "No se pudieron renovar los tokens"
            return
        self.access_token = access_token
        self.session_token = session_token

    def request_login_otp(self):
        """Solicita el código OTP para el login."""

        if not self.user_username or not self.user_password:
            self.otp_request_message = "Debe ingresar usuario y contraseña"
            return

        response = request_login_otp(self.user_username, self.user_password)
        if response.get("success"):
            self.otp_request_message = "Código OTP enviado por SMS"
            self.login_error = ""
            return
        self.otp_request_message = "No se pudo enviar el código OTP"
    
    def set_user_tab(self, tab: str):
        """Set active tab for user dashboard."""
        self.user_active_tab = tab


def load_presentation_content() -> str:
    """Carga el contenido de presentación desde un archivo markdown externo."""
    try:
        # Obtiene la ruta de presentation.md relativa a este archivo
        current_dir = Path(__file__).parent.parent
        presentation_file = current_dir / "presentation.md"
        with open(presentation_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        # Fallback al archivo .txt si no existe el .md
        try:
            current_dir = Path(__file__).parent.parent
            presentation_file = current_dir / "presentation.txt"
            with open(presentation_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except (FileNotFoundError, IOError):
            # Contenido por defecto si ninguno existe
            return (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
            )


def load_menu_content(filename: str, fallback_text: str) -> str:
    """Carga contenido de un archivo .md o .txt del menú con fallback.
    
    Intenta cargar primero la versión .md, luego .txt.
    """

    try:
        current_dir = Path(__file__).parent.parent
        
        # Intentar cargar versión .md primero
        md_filename = filename.replace(".txt", ".md")
        md_file = current_dir / md_filename
        if md_file.exists():
            with open(md_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        
        # Fallback a .txt
        content_file = current_dir / filename
        with open(content_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        # Contenido por defecto si el archivo no existe
        return fallback_text


def logo() -> rx.Component:
    """Logo component."""
    return rx.hstack(
        rx.text("MY", font_weight="bold", font_size="1.8em", color=COLORS["primary"]),
        rx.text("llm", font_size="1.8em", color=COLORS["foreground"]),
        spacing="1",
    )


def login_panel() -> rx.Component:
    """Login panel for user portal."""
    # Ancho fijo para las etiquetas para alinear los campos
    label_width = "100px"
    
    return rx.vstack(
            rx.text("Acceso de Usuario", font_size="1.3em", font_weight="bold", color=COLORS["foreground"]),
            rx.vstack(
                rx.hstack(
                    rx.text(
                        "Usuario",
                        font_size="1.1em",
                        color=COLORS["muted_foreground"],
                        min_width=label_width,
                        text_align="left",
                    ),
                    rx.input(
                        placeholder="Ingrese su usuario",
                        on_change=State.set_user_username,
                        value=State.user_username,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        font_size="1.05em",
                        flex="1",
                        border_radius="5px",
                    ),
                    width="100%",
                    align_items="center",
                    spacing="2",
                ),
                rx.hstack(
                    rx.text(
                        "Contraseña",
                        font_size="1.1em",
                        color=COLORS["muted_foreground"],
                        min_width=label_width,
                        text_align="left",
                    ),
                    rx.input(
                        placeholder="Ingrese su contraseña",
                        type_="password",
                        on_change=State.set_user_password,
                        value=State.user_password,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        font_size="1.05em",
                        flex="1",
                        border_radius="5px",
                    ),
                    width="100%",
                    align_items="center",
                    spacing="2",
                ),
                rx.button(
                    "Solicitar código OTP",
                    on_click=State.request_login_otp,
                    background_color="transparent",
                    color=COLORS["primary"],
                    width="100%",
                    text_align="left",
                    padding="0",
                    font_size="1.1em",
                    justify_content="flex-start",
                    _hover={"text_decoration": "underline"},
                ),
                rx.hstack(
                    rx.text(
                        "OTP",
                        font_size="1.1em",
                        color=COLORS["muted_foreground"],
                        min_width=label_width,
                        text_align="left",
                    ),
                    rx.input(
                        placeholder="Ingrese su OTP",
                        on_change=State.set_user_otp,
                        value=State.user_otp,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        font_size="1.05em",
                        flex="1",
                        border_radius="5px",
                    ),
                    width="100%",
                    align_items="center",
                    spacing="2",
                ),
                spacing="3",
            ),
            rx.button(
                "Iniciar Sesión",
                on_click=State.user_login,
                background_color=COLORS["primary"],
                color=COLORS["background"],
                width="100%",
                font_weight="bold",
                font_size="1.1em",
            ),
            rx.text(
                State.login_error,
                color="red",
                font_size="1.0em",
                display=rx.cond(State.login_error != "", "block", "none"),
            ),
            rx.text(
                State.otp_request_message,
                color=COLORS["muted_foreground"],
                font_size="1.0em",
                display=rx.cond(State.otp_request_message != "", "block", "none"),
            ),
            rx.vstack(
                rx.link(
                    "Crear nuevo usuario",
                    color=COLORS["primary"],
                    href="/user_creation?from=main",
                    font_size="1.1em",
                ),
                rx.link("Recordar contraseña", color=COLORS["primary"], href="/change_password?from=main", font_size="1.1em"),
                spacing="1",
            ),
            spacing="2",
            padding="1.5em",
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            border_radius="0.5em",
            width="100%",
        )


def sidebar_menu(is_logged_in: bool) -> rx.Component:
    """Sidebar menu for navigation."""
    menu_items = rx.cond(
        is_logged_in,
        [
            "organizacion",
            "tecnologias",
            "proyecciones",
            "seguimiento",
            "flujos",
            "descargas",
        ],
        ["inicio", "servicios", "proyectos", "soporte", "contacto"],
    )
    
    return rx.vstack(
            rx.text("Menú", font_size="1.3em", font_weight="bold", color=COLORS["foreground"], margin_bottom="1em"),
            rx.vstack(
                rx.foreach(
                    menu_items,
                    lambda item: rx.button(
                        item.title(),
                        on_click=lambda _, i=item: State.set_user_menu(i),
                        background_color=rx.cond(
                            State.user_active_menu == item,
                            COLORS["primary"],
                            "transparent"
                        ),
                        color=rx.cond(
                            State.user_active_menu == item,
                            COLORS["background"],
                            COLORS["foreground"]
                        ),
                        width="100%",
                        justify_content="flex-start",
                        border="none",
                        padding="0.75em",
                        border_radius="0.5em",
                        cursor="pointer",
                        text_align="left",
                        font_size="1.1em",
                        _hover={"opacity": "0.8"},
                    ),
                ),
                spacing="1",
                align_items="flex-start",
                width="100%",
            ),
            align_items="flex-start",
            width="100%",
        )


def info_panel(active_item: str, is_logged_in: bool) -> rx.Component:
    """Info panel displaying content based on active menu item."""
    presentation_text = load_presentation_content()
    services_text = load_menu_content(
        "services.txt", "Servicios especializados para impulsar sus proyectos de IA."
    )
    projects_text = load_menu_content(
        "proyectos.txt", "Proyectos y entregas en progreso."
    )
    support_text = load_menu_content(
        "soporte.txt", "Soporte técnico y acompañamiento."
    )
    contact_text = load_menu_content(
        "contacto.txt", "Canales de contacto y atención al cliente."
    )
    organization_text = load_organizacion_content()
    technologies_text = load_menu_content(
        "tecnologias.txt", "Tecnologías activas y stack aplicado en tus proyectos."
    )
    projections_text = load_menu_content(
        "proyecciones.txt", "Proyecciones, estimaciones y próximos hitos."
    )
    tracking_text = load_menu_content(
        "seguimiento.txt", "Seguimiento de avances, entregas y validaciones."
    )
    flows_text = load_flujos_content()
    downloads_text = load_menu_content(
        "descargas.txt", "Recursos, informes y entregables para descargar."
    )

    heading_text = rx.cond(
        is_logged_in,
        rx.match(
            active_item,
            ("organizacion", "Organizacion"),
            ("tecnologias", "Tecnologias"),
            ("proyecciones", "Proyecciones"),
            ("seguimiento", "Seguimiento"),
            ("flujos", "Flujos"),
            ("descargas", "Descargas"),
            "Organizacion",
        ),
        rx.match(
            active_item,
            ("servicios", "Servicios"),
            ("proyectos", "Proyectos"),
            ("soporte", "Soporte"),
            ("contacto", "Contacto"),
            "Inicio",
        ),
    )
    content_text = rx.cond(
        is_logged_in,
        rx.match(
            active_item,
            ("organizacion", organization_text),
            ("tecnologias", technologies_text),
            ("proyecciones", projections_text),
            ("seguimiento", tracking_text),
            ("flujos", flows_text),
            ("descargas", downloads_text),
            presentation_text,
        ),
        rx.match(
            active_item,
            ("servicios", services_text),
            ("proyectos", projects_text),
            ("soporte", support_text),
            ("contacto", contact_text),
            presentation_text,
        ),
    )
    
    return rx.vstack(
        rx.heading(heading_text, size="8", color=COLORS["foreground"]),
        rx.cond(
            rx.cond(is_logged_in, False, active_item == "inicio"),
            rx.box(
                rx.image(
                    src="/logo.jpg",
                    alt="Myllm Logo",
                    width="150px",
                    max_width="100%",
                    height="auto",
                ),
                width="100%",
                display="flex",
                justify_content="center",
                align_items="center",
                margin_y="1em",
            ),
            rx.box(height="0"),
        ),
        # Contenido: markdown para secciones públicas, texto plano para secciones internas
        rx.cond(
            is_logged_in,
            # Usuario logueado: texto plano para secciones internas
            rx.text(
                content_text,
                color=COLORS["muted_foreground"],
                font_size="1em",
                line_height="1.5em",
                white_space="pre-line",
                font_family="Inter, system-ui, sans-serif",
                width="100%",
            ),
            # Usuario no logueado: markdown para todas las secciones públicas
            rx.markdown(
                content_text,
                component_map={
                    "h1": lambda text: rx.heading(text, size="9", color=COLORS["foreground"], margin_bottom="0.5em"),
                    "h2": lambda text: rx.heading(text, size="7", color=COLORS["primary"], margin_top="1em", margin_bottom="0.5em"),
                    "h3": lambda text: rx.heading(text, size="5", color=COLORS["foreground"], margin_top="0.8em", margin_bottom="0.4em"),
                    "p": lambda text: rx.text(text, color=COLORS["muted_foreground"], font_size="1.15em", line_height="1.6", margin_bottom="0.6em"),
                    "li": lambda text: rx.list_item(rx.text(text, color=COLORS["muted_foreground"], font_size="1.15em", line_height="1.5")),
                    "strong": lambda text: rx.text(text, font_weight="bold", color=COLORS["foreground"], as_="span"),
                    "em": lambda text: rx.text(text, font_style="italic", as_="span"),
                    "blockquote": lambda text: rx.box(
                        rx.text(text, color=COLORS["primary"], font_style="italic", font_size="1.2em"),
                        border_left=f"4px solid {COLORS['primary']}",
                        padding_left="1.2em",
                        margin_y="1.2em",
                        background_color=f"{COLORS['primary']}10",
                        padding="1em",
                        border_radius="0.3em",
                    ),
                    "table": lambda children: rx.box(
                        children,
                        width="100%",
                        overflow_x="auto",
                        margin_y="1.2em",
                    ),
                    "th": lambda text: rx.table.column_header_cell(
                        rx.text(text, font_weight="bold", color=COLORS["foreground"], font_size="1.1em"),
                    ),
                    "td": lambda text: rx.table.cell(
                        rx.text(text, color=COLORS["muted_foreground"], font_size="1.05em"),
                    ),
                },
            ),
        ),
        rx.cond(
            rx.cond(is_logged_in, active_item == "flujos", False),
            flujos_diagram(),
            rx.box(height="0"),
        ),
        # Paneles de métricas: visibles solo en menú "inicio"
        rx.cond(
            active_item == "inicio",
            rx.flex(
                rx.box(
                    rx.vstack(
                        rx.text("Perplejidad", color=COLORS["muted_foreground"], font_size="0.9em"),
                        rx.text("≈30", font_size="2em", font_weight="bold", color=COLORS["foreground"]),
                        spacing="1",
                    ),
                    padding="1.5em",
                    background_color=COLORS["card"],
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                    flex="1",
                ),
                rx.box(
                    rx.vstack(
                        rx.text("BLEU Score", color=COLORS["muted_foreground"], font_size="0.9em"),
                        rx.text("0.5+", font_size="2em", font_weight="bold", color=COLORS["foreground"]),
                        spacing="1",
                    ),
                    padding="1.5em",
                    background_color=COLORS["card"],
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                    flex="1",
                ),
                rx.box(
                    rx.vstack(
                        rx.text("F1 Score", color=COLORS["muted_foreground"], font_size="0.9em"),
                        rx.text("≈70−80", font_size="2em", font_weight="bold", color=COLORS["foreground"]),
                        spacing="1",
                    ),
                    padding="1.5em",
                    background_color=COLORS["card"],
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                    flex="1",
                ),
                direction="row",
                spacing="4",
                width="100%",
            ),
            rx.box(height="0"),
        ),
        spacing="4",
        padding="2em",
        width="100%",
    )


def dashboard_tabs() -> rx.Component:
    """Dashboard with tabs for user portal."""
    tabs_config = [
        ("resumen", "Resumen"),
        ("proyectos", "Proyectos"),
        ("tareas", "Tareas"),
        ("reportes", "Reportes"),
        ("documentos", "Documentos"),
        ("configuracion", "Configuración"),
    ]
    
    active_tab = State.user_active_tab
    set_tab = State.set_user_tab
    
    return rx.vstack(
        rx.hstack(
            *[
                rx.button(
                    label,
                    on_click=lambda _, t=tab_id: set_tab(t),
                    background_color=rx.cond(
                        active_tab == tab_id,
                        COLORS["primary"],
                        "transparent"
                    ),
                    color=rx.cond(
                        active_tab == tab_id,
                        COLORS["background"],
                        COLORS["foreground"]
                    ),
                    border="none",
                    padding="0.75em 1.5em",
                    border_radius="0.5em",
                    cursor="pointer",
                    _hover={"opacity": "0.8"},
                    font_weight="bold",
                )
                for tab_id, label in tabs_config
            ],
            spacing="2",
            padding="1.5em",
            border_bottom=f"1px solid {COLORS['border']}",
            width="100%",
        ),
        rx.cond(
            active_tab == "resumen",
            rx.vstack(
                rx.heading("Resumen General", size="6", color=COLORS["foreground"]),
                rx.flex(
                    rx.box(
                        rx.vstack(
                            rx.text("Proyectos Activos", color=COLORS["muted_foreground"], font_size="0.9em"),
                            rx.text("12", font_size="2.5em", font_weight="bold", color=COLORS["foreground"]),
                            spacing="1",
                        ),
                        padding="1.5em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        flex="1",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.text("Tareas Pendientes", color=COLORS["muted_foreground"], font_size="0.9em"),
                            rx.text("24", font_size="2.5em", font_weight="bold", color=COLORS["foreground"]),
                            spacing="1",
                        ),
                        padding="1.5em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        flex="1",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.text("Reportes Nuevos", color=COLORS["muted_foreground"], font_size="0.9em"),
                            rx.text("36", font_size="2.5em", font_weight="bold", color=COLORS["foreground"]),
                            spacing="1",
                        ),
                        padding="1.5em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        flex="1",
                    ),
                    direction="row",
                    spacing="4",
                    width="100%",
                ),
                spacing="4",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "proyectos",
            rx.vstack(
                rx.heading("Proyectos", size="6", color=COLORS["foreground"]),
                *[
                    rx.hstack(
                        rx.vstack(
                            rx.text(f"Proyecto {chr(65+i)}", font_weight="bold", color=COLORS["foreground"]),
                            rx.text("En progreso", color=COLORS["muted_foreground"], font_size="0.9em"),
                            spacing="1",
                        ),
                        rx.text(f"{75 - i*15}% completado", color=COLORS["primary"], font_size="0.9em"),
                        padding="1em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        width="100%",
                        justify_content="space-between",
                    )
                    for i in range(3)
                ],
                spacing="2",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "tareas",
            rx.vstack(
                rx.heading("Tareas", size="6", color=COLORS["foreground"]),
                *[
                    rx.hstack(
                        rx.checkbox(checked=False),
                        rx.text(task, color=COLORS["foreground"]),
                        padding="1em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        width="100%",
                        align_items="center",
                    )
                    for task in [
                        "Revisar documentación",
                        "Actualizar sistema",
                        "Reunión con equipo",
                        "Preparar presentación",
                    ]
                ],
                spacing="2",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "reportes",
            rx.vstack(
                rx.heading("Reportes", size="6", color=COLORS["foreground"]),
                rx.flex(
                    *[
                        rx.box(
                            rx.vstack(
                                rx.text(report, font_weight="bold", color=COLORS["foreground"]),
                                rx.text("Generado: Nov 2026", color=COLORS["muted_foreground"], font_size="0.9em"),
                                spacing="1",
                            ),
                            padding="1.5em",
                            background_color=COLORS["card"],
                            border=f"1px solid {COLORS['border']}",
                            border_radius="0.5em",
                            flex="1",
                        )
                        for report in [
                            "Reporte Mensual",
                            "Análisis de Rendimiento",
                            "Estadísticas de Uso",
                            "Informe Financiero",
                        ]
                    ],
                    direction="row",
                    spacing="4",
                    width="100%",
                ),
                spacing="4",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "documentos",
            rx.vstack(
                rx.heading("Documentos", size="6", color=COLORS["foreground"]),
                *[
                    rx.hstack(
                        rx.text(doc, color=COLORS["foreground"]),
                        rx.link("Descargar", color=COLORS["primary"], href="#", font_size="0.9em"),
                        padding="1em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        width="100%",
                        justify_content="space-between",
                    )
                    for doc in [
                        "Manual de Usuario.pdf",
                        "Guía de Inicio.docx",
                        "Especificaciones Técnicas.pdf",
                        "Contrato de Servicio.pdf",
                    ]
                ],
                spacing="2",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "configuracion",
            rx.vstack(
                rx.heading("Configuración", size="6", color=COLORS["foreground"]),
                rx.vstack(
                    rx.vstack(
                        rx.text("Notificaciones por email", color=COLORS["muted_foreground"], font_size="0.9em"),
                        rx.hstack(
                            rx.checkbox(checked=True),
                            rx.text("Activadas", color=COLORS["foreground"]),
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Idioma", color=COLORS["muted_foreground"], font_size="0.9em"),
                        rx.select(
                            ["Español", "English"],
                            value="Español",
                            background_color=COLORS["input"],
                            border_color=COLORS["border"],
                            color=COLORS["foreground"],
                            width="100%",
                        ),
                        spacing="1",
                    ),
                    spacing="3",
                    padding="1.5em",
                    background_color=COLORS["card"],
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                ),
                spacing="3",
                padding="1.5em",
            ),
        ),
        spacing="0",
        width="100%",
        background_color=COLORS["background"],
    )


def footer() -> rx.Component:
    """Footer component."""
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text("Servicios", font_weight="bold", color=COLORS["foreground"], font_size="1.4em"),
                rx.link("Características", color=COLORS["primary"], href="/show-md?file=caracteristicas", is_external=True, font_size="1.3em"),
                rx.link("Precios", color=COLORS["primary"], href="/show-md?file=precios", is_external=True, font_size="1.3em"),
                rx.link("Seguridad", color=COLORS["primary"], href="/show-md?file=seguridad", is_external=True, font_size="1.3em"),
                spacing="2",
            ),
            rx.vstack(
                rx.text("Empresa", font_weight="bold", color=COLORS["foreground"], font_size="1.4em"),
                rx.link("Nosotros", color=COLORS["primary"], href="/show-md?file=nosotros", is_external=True, font_size="1.3em"),
                rx.link("Blog", color=COLORS["primary"], href="/show-md?file=blog", is_external=True, font_size="1.3em"),
                rx.link("Estado", color=COLORS["primary"], href="/show-md?file=estado", is_external=True, font_size="1.3em"),
                spacing="2",
            ),
            rx.vstack(
                rx.text("Recursos", font_weight="bold", color=COLORS["foreground"], font_size="1.4em"),
                rx.link("Documentación", color=COLORS["primary"], href="/show-md?file=documentacion", is_external=True, font_size="1.3em"),
                rx.link("Comunidad", color=COLORS["primary"], href="/show-md?file=comunidad", is_external=True, font_size="1.3em"),
                rx.link("Soporte", color=COLORS["primary"], href="/show-md?file=soporte", is_external=True, font_size="1.3em"),
                spacing="2",
            ),
            rx.vstack(
                rx.text("Legal", font_weight="bold", color=COLORS["foreground"], font_size="1.4em"),
                rx.link("Privacidad", color=COLORS["primary"], href="/show-md?file=privacidad", is_external=True, font_size="1.3em"),
                rx.link("Términos", color=COLORS["primary"], href="/show-md?file=terminos", is_external=True, font_size="1.3em"),
                rx.link("Contratos", color=COLORS["primary"], href="/show-md?file=contratos", is_external=True, font_size="1.3em"),
                spacing="2",
            ),
            spacing="6",
            width="100%",
            padding="2em",
            justify_content="center",
            align="center",
        ),
        rx.divider(margin_y="1em"),
        rx.box(
            rx.text(
                "© 2025 Myllm. Todos los derechos reservados.",
                color=COLORS["muted_foreground"],
                font_size="1.25em",
                text_align="center",
            ),
            width="100%",
            padding="1em",
            display="flex",
            justify_content="center",
            align_items="center",
        ),
        background_color=COLORS["card"],
        border_top=f"1px solid {COLORS['border']}",
        width="100%",
        spacing="0",
    )


def user_portal() -> rx.Component:
    """User portal main page."""
    return rx.cond(
        State.is_logged_in,
        rx.vstack(
            rx.hstack(
                logo(),
                rx.box(flex_grow="1"),
                # Botón Backoffice (solo si tiene permiso training_create)
                rx.cond(
                    State.can_access_backoffice,
                    rx.button(
                        "Backoffice",
                        on_click=State.go_to_backoffice,
                        background_color="#FF8C00",  # Naranja
                        color="white",
                        font_size="1.1em",
                        _hover={"background_color": "#FF7000"},
                    ),
                ),
                rx.button(
                    "Desconectar",
                    on_click=State.user_logout,
                    background_color=COLORS["primary"],
                    color=COLORS["background"],
                    font_size="1.1em",
                ),
                width="100%",
                padding="1em",
                background_color=COLORS["card"],
                border_bottom=f"1px solid {COLORS['border']}",
                align_items="center",
            ),
            rx.hstack(
                rx.box(
                    rx.vstack(
                        sidebar_menu(State.is_logged_in),
                        spacing="4",
                        padding="1.5em",
                    ),
                    width="25%",
                    padding="1em",
                    background_color=COLORS["card"],
                    border_right=f"1px solid {COLORS['border']}",
                    height="100%",
                ),
                rx.box(
                    info_panel(State.user_active_menu, State.is_logged_in),
                    width="75%",
                    background_color=COLORS["background"],
                    padding="0",
                    height="100%",
                ),
                width="100%",
                spacing="0",
                flex="1",
                align_items="stretch",
                background_color=COLORS["card"],
            ),
            footer(),
            background_color=COLORS["background"],
            width="100%",
            min_height="100vh",
            spacing="0",
        ),
        rx.vstack(
            rx.hstack(
                logo(),
                rx.box(flex_grow="1"),
                rx.text(
                    "Pagina principal",
                    color=COLORS["muted_foreground"],
                    font_size="1.1em",
                ),
                width="100%",
                padding="1em",
                background_color=COLORS["card"],
                border_bottom=f"1px solid {COLORS['border']}",
                align_items="center",
            ),
            rx.hstack(
                rx.box(
                    rx.vstack(
                        login_panel(),
                        sidebar_menu(State.is_logged_in),
                        spacing="4",
                        padding="1.5em",
                    ),
                    width="25%",
                    padding="1em",
                    background_color=COLORS["card"],
                    border_right=f"1px solid {COLORS['border']}",
                    height="100%",
                ),
                rx.box(
                    info_panel(State.user_active_menu, State.is_logged_in),
                    width="75%",
                    background_color=COLORS["background"],
                    padding="0",
                    height="100%",
                ),
                width="100%",
                spacing="0",
                flex="1",
                align_items="stretch",
                background_color=COLORS["card"],
            ),
            footer(),
            background_color=COLORS["background"],
            width="100%",
            min_height="100vh",
            spacing="0",
        ),
    )


# Crear la aplicación
app = rx.App(
    style={
        "font_family": "Inter, system-ui, sans-serif",
    },
)

# User portal route
app.add_page(
    user_portal,
    route="/",
    title="Myllm - Pagina principal",
    on_load=State.on_page_load,
)

# User creation route
import sys
from pathlib import Path
# Agregar el directorio 5_web_frontend al path para importar pages
frontend_dir = Path(__file__).parent.parent
if str(frontend_dir) not in sys.path:
    sys.path.insert(0, str(frontend_dir))

try:
    from pages.user_creation import user_creation_page
    app.add_page(user_creation_page, route="/user_creation", title="Myllm - Crear Usuario")
    print("✅ Ruta /user_creation registrada exitosamente")
except ImportError as e:
    print(f"⚠️ Warning: Could not import user_creation_page: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error al registrar ruta /user_creation: {e}")
    import traceback
    traceback.print_exc()

try:
    from pages.change_password import change_password_page
    app.add_page(change_password_page, route="/change_password", title="Myllm - Recordar Contraseña")
    print("✅ Ruta /change_password registrada exitosamente")
except ImportError as e:
    print(f"⚠️ Warning: Could not import change_password_page: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error al registrar ruta /change_password: {e}")
    import traceback
    traceback.print_exc()

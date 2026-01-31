import base64
import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import reflex as rx

from adapters.api_client import (
    create_organization_user,
    get_organization_users,
    get_user_permissions,
    login_user,
    logout_user,
    refresh_tokens,
    request_login_otp,
    update_user_status,
)
from pages.flujos import FlujosState, flujos_diagram, load_flujos_content
from pages.organizacion import load_organizacion_content
from low_panel_pages.show_md import show_md  # noqa: F401 - Importado para registrar la ruta
from web_backoffice.shared_state import SharedSessionState

# Importar logger de actividad usando importlib (el directorio tiene número)
_activity_logger_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "reflex_shared" / "activity_logger.py"
_spec = importlib.util.spec_from_file_location("activity_logger", _activity_logger_path)
_activity_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_activity_module)

# Logger de actividad del backoffice
activity_log = _activity_module.get_backoffice_logger()
activity_log.log_startup()

COLORS = {
    "background": "#1a1a1a",
    "card": "#2d2d2d",
    "foreground": "#f2f2f5",
    "primary": "#FF8C00",  # Naranja para backoffice
    "secondary": "#383854",
    "border": "#404040",
    "input": "#3a3a3a",
    "muted_foreground": "#E0E0E0",
    "accent": "#FF8C00",  # Naranja para backoffice
}

# Define the State class for managing application state
class State(SharedSessionState):
    """Backoffice state with Redis-based session sharing."""
    
    # User portal state (campos locales del backoffice, no compartidos)
    user_active_menu: str = "inicio"
    user_username: str = ""
    user_password: str = ""
    user_otp: str = ""
    user_active_tab: str = "resumen"
    user_permissions: list[dict[str, str]] = []
    login_error: str = ""
    otp_request_message: str = ""
    
    # Estado para gestión de usuarios y proyectos de la organización
    # Estado para gestión de usuarios de la organización
    # Estructura: {"user_id": int, "user_name": str, "active": bool}
    org_users: list[dict] = []
    org_projects: list[dict] = [
        {"id": 1, "name": "Asistente Comercial", "description": "Modelo de lenguaje para atención al cliente", "locked": False},
    ]
    
    # Estado del modal de creación de usuario
    show_create_user_modal: bool = False
    new_user_name: str = ""
    new_user_email: str = ""
    new_user_mobile: str = ""
    create_user_error: str = ""
    create_user_success: str = ""
    is_creating_user: bool = False
    
    # Nota: Los siguientes campos ya vienen de SharedSessionState:
    # - is_logged_in, access_token, session_token, user_id, organization_id
    # - user_name, user_email, user_mobile, identity_type_id
    # - 45 permisos (can_training_create, can_folder_rename, etc.)
    # - Métodos: load_user_data(), clear_session(), go_to_frontend(), etc.
    
    # ========== Propiedades computadas de permisos ==========
    
    @rx.var
    def can_manage_org_users(self) -> bool:
        """Indica si el usuario actual puede gestionar usuarios de la organización.
        
        Regla de seguridad: Solo pueden gestionar usuarios:
        - SuperAdmin (identity_type_id = 1)
        - Administrador de Organización (identity_type_id = 2)
        - Agentes automáticos con rol admin (identity_type_id = 10)
        
        Los editores (3), lectores (4), auditores (5) y agentes no-admin (11-13)
        NO pueden gestionar usuarios.
        """
        if self.identity_type_id <= 0:
            return False
        # SuperAdmin, Admin de Org, o Agente Admin
        return self.identity_type_id in (1, 2, 10)
    
    def check_backoffice_access(self):
        """
        Verifica que el usuario tiene acceso al backoffice.
        Redirige al frontend si no tiene permiso.
        """
        if not self.can_access_backoffice:
            return self.go_to_frontend()
    
    def load_tokens_from_url(self, access_token: str, session_token: str, user_id: str, org_id: str):
        """
        Carga tokens desde parámetros de URL (pasados desde el frontend).
        """
        if access_token and session_token:
            self.access_token = access_token
            self.session_token = session_token
            self.user_id = int(user_id) if user_id else 0
            self.organization_id = int(org_id) if org_id else 0
            self.is_logged_in = True
            # Cargar permisos desde el middleware
            return self.load_permissions_from_session()
        return None
    
    def load_permissions_from_session(self):
        """
        Carga permisos del usuario desde el middleware si no están en sesión.
        
        Este método se ejecuta al entrar al backoffice para asegurar que:
        1. Los permisos están cargados en SharedSessionState (sincronizados vía Redis)
        2. Si no hay permisos en Redis, los carga desde el middleware (fallback)
        3. Verifica que el usuario tiene acceso al backoffice
        
        Returns:
            Redirección al frontend si no tiene acceso o error
        """
        # Si no hay tokens, redirigir al frontend para login
        if not self.access_token or not self.session_token:
            self.login_error = "Debe iniciar sesión desde el sitio principal"
            return self.go_to_frontend()
        
        # Si ya tiene permisos cargados (desde Redis), verificar acceso
        if self.can_training_create:
            # Los permisos ya están sincronizados desde el frontend vía Redis
            self.current_app = "backoffice"
            self.update_activity()
            return None
        
        # Fallback: Si Redis no tiene permisos, cargar desde middleware
        try:
            permissions_response = get_user_permissions(
                self.access_token, self.session_token
            )
            
            if not permissions_response:
                self.login_error = "No se pudieron obtener los permisos del usuario"
                return self.go_to_frontend()
            
            # Obtener permisos de bajo nivel
            low_level_permissions = permissions_response.get("low_level_permissions", {})
            
            # Actualizar permisos en SharedSessionState (se sincroniza con Redis)
            self._load_permissions(low_level_permissions)
            
            # Actualizar datos de usuario si es necesario
            self.user_id = int(permissions_response.get("user_id", self.user_id))
            self.organization_id = int(permissions_response.get("organization_id", self.organization_id))
            self.identity_type_id = int(permissions_response.get("identity_type_id", self.identity_type_id))
            self.is_logged_in = True
            self.current_app = "backoffice"
            self.update_activity()
            
            # Verificar que tiene acceso al backoffice
            if not self.can_access_backoffice:
                self.login_error = "No tiene permisos para acceder al backoffice"
                return self.go_to_frontend()
            
            return None
            
        except Exception as exc:
            self.login_error = f"Error al cargar permisos: {str(exc)}"
            return self.go_to_frontend()
    
    def set_user_menu(self, menu: str):
        """Set active menu item for user portal."""
        self.user_active_menu = menu
        
        # Asegurar que identity_type_id y organization_id están disponibles desde el token
        if self.access_token:
            if self.identity_type_id <= 0:
                extracted_identity = self._extract_identity_type_id_from_token(self.access_token)
                if extracted_identity > 0:
                    self.identity_type_id = extracted_identity
            if self.organization_id <= 0:
                extracted_org = self._extract_org_id_from_token(self.access_token)
                if extracted_org > 0:
                    self.organization_id = extracted_org
        
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
        if menu == "organizacion":
            self.load_org_users()
            self.load_org_projects()

    # ========== Gestión de Usuarios de la Organización ==========
    
    def load_org_users(self):
        """Carga los usuarios de la organización actual desde la base de datos.
        
        Filtra por:
        - organization_id del usuario logueado
        - identity_type_id = 5 (auditores/usuarios base)
        """
        # Asegurar que identity_type_id está cargado desde el token si no está en el estado
        if self.identity_type_id <= 0 and self.access_token:
            extracted_identity = self._extract_identity_type_id_from_token(self.access_token)
            if extracted_identity > 0:
                self.identity_type_id = extracted_identity
        
        # Obtener organization_id de la sesión
        org_id = self.organization_id
        if org_id <= 0 and self.access_token:
            org_id = self._extract_org_id_from_token(self.access_token)
        
        if org_id <= 0:
            # Si no hay organización, mostrar lista vacía
            self.org_users = []
            return
        
        # Llamar al middleware para obtener usuarios reales
        users = get_organization_users(
            organization_id=org_id,
            access_token=self.access_token,
            session_token=self.session_token,
            identity_type_id=5,  # Solo auditores (usuarios de organización)
        )
        
        # Transformar al formato esperado por la UI
        # Estructura: {"user_id": int, "user_name": str, "active": bool}
        self.org_users = [
            {
                "user_id": user.get("user_id", 0),
                "user_name": user.get("user_name", ""),
                "active": user.get("active", True),
            }
            for user in users
        ]
    
    def create_user(self):
        """Abre el modal para crear un nuevo usuario."""
        self.show_create_user_modal = True
        self.new_user_name = ""
        self.new_user_email = ""
        self.new_user_mobile = ""
        self.create_user_error = ""
        self.create_user_success = ""
        self.is_creating_user = False
    
    def close_create_user_modal(self):
        """Cierra el modal de creación de usuario sin guardar."""
        self.show_create_user_modal = False
        self.new_user_name = ""
        self.new_user_email = ""
        self.new_user_mobile = ""
        self.create_user_error = ""
        self.create_user_success = ""
        self.is_creating_user = False
    
    def save_new_user(self):
        """Guarda el nuevo usuario llamando al middleware."""
        # Validaciones básicas
        if not self.new_user_name.strip():
            self.create_user_error = "El nombre de usuario es obligatorio"
            return
        if not self.new_user_email.strip():
            self.create_user_error = "El correo electrónico es obligatorio"
            return
        if not self.new_user_mobile.strip():
            self.create_user_error = "El teléfono es obligatorio"
            return
        
        self.create_user_error = ""
        self.is_creating_user = True
        
        # Obtener organization_id de la sesión
        org_id = self.organization_id
        if org_id <= 0 and self.access_token:
            org_id = self._extract_org_id_from_token(self.access_token)
        
        if org_id <= 0:
            self.create_user_error = "No se pudo determinar la organización"
            self.is_creating_user = False
            return
        
        # Llamar al API para crear el usuario
        result = create_organization_user(
            organization_id=org_id,
            user_name=self.new_user_name.strip(),
            user_email=self.new_user_email.strip(),
            user_mobile=self.new_user_mobile.strip(),
            access_token=self.access_token,
            session_token=self.session_token,
        )
        
        self.is_creating_user = False
        
        if result.get("success"):
            self.create_user_success = f"Usuario '{self.new_user_name}' creado exitosamente"
            # Recargar lista de usuarios
            self.load_org_users()
            # Limpiar campos
            self.new_user_name = ""
            self.new_user_email = ""
            self.new_user_mobile = ""
        else:
            self.create_user_error = result.get("error", "Error al crear el usuario")
    
    def set_new_user_name(self, value: str):
        """Actualiza el nombre del nuevo usuario."""
        self.new_user_name = value
    
    def set_new_user_email(self, value: str):
        """Actualiza el email del nuevo usuario."""
        self.new_user_email = value
    
    def set_new_user_mobile(self, value: str):
        """Actualiza el teléfono del nuevo usuario."""
        self.new_user_mobile = value
    
    def enable_user(self, user_id: int):
        """Habilita un usuario de la organización."""
        try:
            print(f"[DEBUG] Habilitar usuario: {user_id}")
            result = update_user_status(
                user_id=user_id,
                active=True,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            print(f"[DEBUG] Resultado: {result}")
            
            # Actualizar estado local
            for user in self.org_users:
                if user["user_id"] == user_id:
                    user["active"] = True
            self.org_users = self.org_users.copy()
        except Exception as e:
            print(f"[ERROR] Error habilitando usuario: {e}")
    
    def disable_user(self, user_id: int):
        """Deshabilita un usuario de la organización."""
        try:
            print(f"[DEBUG] Deshabilitar usuario: {user_id}")
            result = update_user_status(
                user_id=user_id,
                active=False,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            print(f"[DEBUG] Resultado: {result}")
            
            # Actualizar estado local
            for user in self.org_users:
                if user["user_id"] == user_id:
                    user["active"] = False
            self.org_users = self.org_users.copy()
        except Exception as e:
            print(f"[ERROR] Error deshabilitando usuario: {e}")
    
    def assign_user_to_projects(self, user_id: int):
        """Asigna un usuario a proyectos."""
        # TODO: Implementar modal de asignación
        print(f"[DEBUG] Asignar usuario a proyectos: {user_id}")
    
    def remove_user_from_projects(self, user_id: int):
        """Quita un usuario de proyectos."""
        # TODO: Implementar modal de desasignación
        print(f"[DEBUG] Quitar usuario de proyectos: {user_id}")
    
    def delete_user(self, user_id: int):
        """Elimina un usuario de la organización."""
        # TODO: Implementar confirmación y llamada al middleware
        print(f"[DEBUG] Eliminar usuario: {user_id}")
        self.org_users = [u for u in self.org_users if u["id"] != user_id]

    # ========== Gestión de Proyectos de la Organización ==========
    
    def load_org_projects(self):
        """Carga los proyectos de la organización actual."""
        # TODO: Implementar llamada al middleware para obtener proyectos
        # Por ahora, datos de ejemplo para la UI
        self.org_projects = [
            {"id": 1, "name": "Asistente Comercial", "description": "Modelo de lenguaje para atención al cliente", "locked": False},
        ]
    
    def create_project(self):
        """Abre el formulario para crear un nuevo proyecto."""
        # TODO: Implementar navegación a formulario de creación
        print("[DEBUG] Crear proyecto solicitado")
    
    def lock_project(self, project_id: int):
        """Bloquea un proyecto."""
        # TODO: Implementar llamada al middleware
        print(f"[DEBUG] Bloquear proyecto: {project_id}")
        for project in self.org_projects:
            if project["id"] == project_id:
                project["locked"] = True
        self.org_projects = self.org_projects.copy()
    
    def unlock_project(self, project_id: int):
        """Desbloquea un proyecto."""
        # TODO: Implementar llamada al middleware
        print(f"[DEBUG] Desbloquear proyecto: {project_id}")
        for project in self.org_projects:
            if project["id"] == project_id:
                project["locked"] = False
        self.org_projects = self.org_projects.copy()
    
    def delete_project(self, project_id: int):
        """Elimina un proyecto."""
        # TODO: Implementar confirmación y llamada al middleware
        print(f"[DEBUG] Eliminar proyecto: {project_id}")
        self.org_projects = [p for p in self.org_projects if p["id"] != project_id]
    
    def request_project_support(self, project_id: int):
        """Solicita soporte para un proyecto."""
        # TODO: Implementar formulario de soporte
        print(f"[DEBUG] Solicitar soporte para proyecto: {project_id}")

    def on_page_load(self):
        """
        Ejecuta acciones al recargar la página del backoffice.
        
        1. Carga tokens desde URL si están presentes (navegación desde frontend)
        2. Carga permisos desde sesión (Redis) o middleware (fallback)
        3. Verifica acceso al backoffice
        4. Inicializa componentes según el menú activo
        """
        # Leer tokens de query params (pasados desde el frontend)
        params = self.router.page.params
        access_token = params.get("access_token", "")
        session_token = params.get("session_token", "")
        user_id = params.get("user_id", "")
        org_id = params.get("org_id", "")
        
        # Si vienen tokens en la URL, cargarlos primero
        if access_token and session_token:
            self.access_token = access_token
            self.session_token = session_token
            self.user_id = int(user_id) if user_id else 0
            self.organization_id = int(org_id) if org_id else 0
            self.is_logged_in = True
            activity_log.log_session_activity(
                self.user_id, 
                f"session loaded from URL | org_id={self.organization_id}"
            )
        
        # Cargar permisos (obligatorio)
        activity_log.log_middleware_request("/auth/permissions", "GET")
        permission_result = self.load_permissions_from_session()
        if permission_result is not None:
            activity_log.warning(f"Permission check failed | user_id={self.user_id} | redirecting to frontend")
            return permission_result
        
        activity_log.log_session_activity(self.user_id, "permissions loaded successfully")
        
        # Continuar con la lógica de inicialización de componentes
        if self.user_active_menu == "flujos":
            organization_id = self.organization_id
            if organization_id <= 0 and self.access_token:
                organization_id = self._extract_org_id_from_token(self.access_token)
                if organization_id > 0:
                    self.organization_id = organization_id
            return FlujosState.initialize_from_session(organization_id)

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

    def _extract_identity_type_id_from_token(self, token: str) -> int:
        """Extrae identity_type_id desde el payload del JWT."""

        try:
            parts = token.split(".")
            if len(parts) < 2:
                return 0
            payload = parts[1]
            padded = payload + "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            return int(data.get("identity_type_id", 0))
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
        """
        Login deshabilitado en backoffice.
        Los usuarios deben loguearse en el frontend.
        """
        self.login_error = "El login debe realizarse desde el sitio principal"
        return
    
    def user_logout(self):
        """
        Handle user portal logout.
        Limpia la sesión y redirige al frontend.
        """
        if self.access_token and self.session_token:
            logout_user(self.access_token, self.session_token)
        
        # Limpiar SharedSessionState (se sincroniza automáticamente con Redis)
        self.clear_session()
        
        # Limpiar estado local del backoffice
        self.is_logged_in = False
        self.user_username = ""
        self.user_password = ""
        self.user_otp = ""
        self.user_permissions = []
        self.login_error = ""
        self.otp_request_message = ""
        self.user_active_menu = "inicio"
        
        # Redirigir al frontend principal
        return self.go_to_frontend()

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
    return rx.vstack(
            rx.text("Acceso de Usuario", font_size="1.3em", font_weight="bold", color=COLORS["foreground"]),
            rx.vstack(
                rx.vstack(
                    rx.text("Usuario", font_size="1.1em", color=COLORS["muted_foreground"]),
                    rx.input(
                        placeholder="Ingrese su usuario",
                        on_change=State.set_user_username,
                        value=State.user_username,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        font_size="1.05em",
                        width="100%",
                        border_radius="5px",
                    ),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Contraseña", font_size="1.1em", color=COLORS["muted_foreground"]),
                    rx.input(
                        placeholder="Ingrese su contraseña",
                        type_="password",
                        on_change=State.set_user_password,
                        value=State.user_password,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        font_size="1.05em",
                        width="100%",
                        border_radius="5px",
                    ),
                    spacing="1",
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
                rx.vstack(
                    rx.text("OTP", font_size="1.1em", color=COLORS["muted_foreground"]),
                    rx.input(
                        placeholder="Ingrese su OTP",
                        on_change=State.set_user_otp,
                        value=State.user_otp,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        font_size="1.05em",
                        width="100%",
                        border_radius="5px",
                    ),
                    spacing="1",
                ),
                spacing="2",
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


def user_action_button(icon: str, tooltip: str, on_click, color: str = COLORS["muted_foreground"]) -> rx.Component:
    """Botón de acción con icono y tooltip."""
    return rx.tooltip(
        rx.icon_button(
            rx.icon(icon, size=22),
            variant="ghost",
            size="2",
            color_scheme="gray",
            cursor="pointer",
            on_click=on_click,
            _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
        ),
        content=tooltip,
    )


def user_row(user: dict) -> rx.Component:
    """Fila de usuario con acciones.
    
    Muestra solo el user_name pero usa user_id internamente para las acciones.
    Estructura esperada: {"user_id": int, "user_name": str, "active": bool}
    
    Nota: En Reflex, para pasar argumentos dinámicos desde rx.foreach,
    se usa el formato State.method(var) sin lambda.
    
    SEGURIDAD: Los botones de acción solo se muestran si el usuario actual
    tiene permisos de gestión (identity_type_id in 1, 2, 10).
    Ver: State.can_manage_org_users
    """
    return rx.hstack(
        # Información del usuario a la izquierda (solo muestra user_name)
        rx.hstack(
            rx.text(user["user_name"], font_weight="bold", font_size="1.1em", color=COLORS["foreground"]),
            rx.cond(
                user["active"],
                rx.badge("Activo", color_scheme="green", variant="soft", size="3"),
                rx.badge("Inactivo", color_scheme="red", variant="soft", size="3"),
            ),
            spacing="3",
            align="center",
        ),
        # Acciones a la derecha (usan user_id internamente)
        # SEGURIDAD: Solo se muestran si el usuario tiene permisos de gestión
        # (identity_type_id in 1, 2, 10 - SuperAdmin, Admin Org, Agente Admin)
        rx.cond(
            State.can_manage_org_users,
            rx.hstack(
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("user-check", size=22),
                        variant="ghost",
                        size="2",
                        color_scheme="gray",
                        cursor="pointer",
                        on_click=State.enable_user(user["user_id"]),
                        _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
                    ),
                    content="Habilitar usuario",
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("user-x", size=22),
                        variant="ghost",
                        size="2",
                        color_scheme="gray",
                        cursor="pointer",
                        on_click=State.disable_user(user["user_id"]),
                        _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
                    ),
                    content="Deshabilitar usuario",
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("folder-plus", size=22),
                        variant="ghost",
                        size="2",
                        color_scheme="gray",
                        cursor="pointer",
                        on_click=State.assign_user_to_projects(user["user_id"]),
                        _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
                    ),
                    content="Asignar usuario a proyectos",
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("folder-minus", size=22),
                        variant="ghost",
                        size="2",
                        color_scheme="gray",
                        cursor="pointer",
                        on_click=State.remove_user_from_projects(user["user_id"]),
                        _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
                    ),
                    content="Quitar usuario de proyectos",
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("trash-2", size=22),
                        variant="ghost",
                        size="2",
                        color_scheme="gray",
                        cursor="pointer",
                        on_click=State.delete_user(user["user_id"]),
                        _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
                    ),
                    content="Borrar usuario",
                ),
                spacing="1",
            ),
            rx.fragment(),  # No mostrar botones si no tiene permisos
        ),
        justify="between",
        align="center",
        width="100%",
        padding="0.75em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
    )


def create_user_modal() -> rx.Component:
    """Modal para crear un nuevo usuario de la organización."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("user-plus", size=24, color=COLORS["primary"]),
                    rx.text("Crear Nuevo Usuario", font_weight="bold", font_size="1.3em"),
                    spacing="3",
                    align="center",
                ),
            ),
            rx.dialog.description(
                rx.text(
                    "Complete los datos del nuevo usuario de la organización.",
                    color=COLORS["muted_foreground"],
                    font_size="0.95em",
                ),
            ),
            rx.vstack(
                # Campo: Nombre de usuario
                rx.vstack(
                    rx.text("Nombre de usuario", font_weight="bold", color=COLORS["foreground"]),
                    rx.input(
                        placeholder="Ingrese el nombre de usuario",
                        value=State.new_user_name,
                        on_change=State.set_new_user_name,
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Campo: Correo electrónico
                rx.vstack(
                    rx.text("Correo electrónico", font_weight="bold", color=COLORS["foreground"]),
                    rx.input(
                        placeholder="correo@ejemplo.com",
                        value=State.new_user_email,
                        on_change=State.set_new_user_email,
                        type="email",
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Campo: Teléfono
                rx.vstack(
                    rx.text("Teléfono móvil", font_weight="bold", color=COLORS["foreground"]),
                    rx.input(
                        placeholder="+34 600 000 000",
                        value=State.new_user_mobile,
                        on_change=State.set_new_user_mobile,
                        type="tel",
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Mensaje de error
                rx.cond(
                    State.create_user_error != "",
                    rx.text(
                        State.create_user_error,
                        color="red",
                        font_size="0.9em",
                    ),
                ),
                # Mensaje de éxito
                rx.cond(
                    State.create_user_success != "",
                    rx.text(
                        State.create_user_success,
                        color=COLORS["primary"],
                        font_size="0.9em",
                        font_weight="bold",
                    ),
                ),
                width="100%",
                spacing="3",
                padding_y="1em",
            ),
            # Botones de acción
            rx.hstack(
                rx.button(
                    rx.icon("x", size=18, color=COLORS["foreground"]),
                    rx.text("Salir", color=COLORS["foreground"]),
                    on_click=State.close_create_user_modal,
                    variant="outline",
                    size="3",
                    color_scheme="gray",
                ),
                rx.button(
                    rx.cond(
                        State.is_creating_user,
                        rx.spinner(size="2"),
                        rx.icon("save", size=18, color="black"),
                    ),
                    rx.text("Guardar", font_weight="bold", color="black"),
                    on_click=State.save_new_user,
                    background_color=COLORS["primary"],
                    size="3",
                    disabled=State.is_creating_user,
                    _hover={"background_color": "#e67e00", "cursor": "pointer"},
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            padding="1.5em",
            max_width="450px",
        ),
        open=State.show_create_user_modal,
    )


def users_management_panel() -> rx.Component:
    """Panel de gestión de usuarios de la organización."""
    return rx.vstack(
        # Modal de creación de usuario
        create_user_modal(),
        rx.hstack(
            rx.icon("users", size=28, color=COLORS["primary"]),
            rx.heading("Gestión de Usuarios", size="6", color=COLORS["foreground"]),
            spacing="3",
            align="center",
        ),
        # SEGURIDAD: Solo mostrar si el usuario tiene permiso user_create
        rx.cond(
            State.can_user_create,
            rx.button(
                rx.icon("user-plus", size=20, color="black"),
                rx.text("Crear usuario", font_weight="bold", color="black"),
                on_click=State.create_user,
                background_color=COLORS["primary"],
                size="3",
                _hover={"background_color": "#e67e00", "cursor": "pointer"},
            ),
            rx.fragment(),
        ),
        rx.vstack(
            rx.foreach(
                State.org_users,
                user_row,
            ),
            width="100%",
            spacing="2",
        ),
        width="100%",
        padding="1.5em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
        spacing="3",
        align_items="flex-start",
    )


def project_row(project: dict) -> rx.Component:
    """Fila de proyecto con acciones."""
    return rx.hstack(
        # Información del proyecto a la izquierda
        rx.hstack(
            rx.text(project["name"], font_weight="bold", font_size="1.1em", color=COLORS["foreground"]),
            rx.cond(
                project["locked"],
                rx.badge("Bloqueado", color_scheme="red", variant="soft", size="3"),
                rx.badge("Activo", color_scheme="green", variant="soft", size="3"),
            ),
            spacing="3",
            align="center",
        ),
        # Acciones a la derecha
        rx.hstack(
            user_action_button(
                "lock",
                "Bloquear proyecto",
                lambda: State.lock_project(project["id"]),
            ),
            user_action_button(
                "unlock",
                "Desbloquear proyecto",
                lambda: State.unlock_project(project["id"]),
            ),
            user_action_button(
                "trash-2",
                "Borrar proyecto",
                lambda: State.delete_project(project["id"]),
            ),
            user_action_button(
                "headset",
                "Solicitud de soporte",
                lambda: State.request_project_support(project["id"]),
            ),
            spacing="1",
        ),
        justify="between",
        align="center",
        width="100%",
        padding="0.75em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
    )


def projects_management_panel() -> rx.Component:
    """Panel de gestión de proyectos de la organización."""
    return rx.vstack(
        rx.hstack(
            rx.icon("folder-kanban", size=28, color=COLORS["primary"]),
            rx.heading("Gestión de Proyectos", size="6", color=COLORS["foreground"]),
            spacing="3",
            align="center",
        ),
        rx.button(
            rx.icon("folder-plus", size=20, color="black"),
            rx.text("Crear proyecto", font_weight="bold", color="black"),
            on_click=State.create_project,
            color_scheme="orange",
            variant="solid",
            size="3",
        ),
        rx.vstack(
            rx.foreach(
                State.org_projects,
                project_row,
            ),
            width="100%",
            spacing="2",
        ),
        width="100%",
        padding="1.5em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
        spacing="3",
        align_items="flex-start",
    )


def organization_management_panels() -> rx.Component:
    """Paneles de gestión de usuarios y proyectos para la sección Organización."""
    return rx.vstack(
        users_management_panel(),
        projects_management_panel(),
        width="100%",
        spacing="4",
        margin_top="1.5em",
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
        # Contenido: markdown para todas las secciones (públicas e internas)
        # NOTA: Backoffice usa tamaños estándar (sin zoom) para mayor densidad de información
        # El frontend usa tamaños aumentados (+15%) para mejor legibilidad de usuarios finales
        rx.markdown(
            content_text,
            component_map={
                "h1": lambda text: rx.heading(text, size="5", color=COLORS["foreground"], margin_bottom="0.4em"),
                "h2": lambda text: rx.heading(text, size="4", color=COLORS["primary"], margin_top="0.8em", margin_bottom="0.4em"),
                "h3": lambda text: rx.heading(text, size="3", color=COLORS["foreground"], margin_top="0.6em", margin_bottom="0.3em"),
                "p": lambda text: rx.text(text, color=COLORS["muted_foreground"], font_size="1em", line_height="1.5", margin_bottom="0.5em"),
                "li": lambda text: rx.list_item(rx.text(text, color=COLORS["muted_foreground"], font_size="1em", line_height="1.4")),
                "strong": lambda text: rx.text(text, font_weight="bold", color=COLORS["foreground"], as_="span"),
                "em": lambda text: rx.text(text, font_style="italic", as_="span"),
                "blockquote": lambda text: rx.box(
                    rx.text(text, color=COLORS["primary"], font_style="italic", font_size="1em"),
                    border_left=f"4px solid {COLORS['primary']}",
                    padding_left="1em",
                    margin_y="1em",
                    background_color=f"{COLORS['primary']}10",
                    padding="0.8em",
                    border_radius="0.3em",
                ),
                "table": lambda children: rx.box(
                    children,
                    width="100%",
                    overflow_x="auto",
                    margin_y="1em",
                ),
                "th": lambda text: rx.table.column_header_cell(
                    rx.text(text, font_weight="bold", color=COLORS["foreground"], font_size="1em"),
                ),
                "td": lambda text: rx.table.cell(
                    rx.text(text, color=COLORS["muted_foreground"], font_size="1em"),
                ),
            },
        ),
        rx.cond(
            rx.cond(is_logged_in, active_item == "flujos", False),
            flujos_diagram(),
            rx.box(height="0"),
        ),
        # Paneles de gestión de usuarios y proyectos: visibles solo en menú "organizacion"
        rx.cond(
            rx.cond(is_logged_in, active_item == "organizacion", False),
            organization_management_panels(),
            rx.box(height="0"),
        ),
        rx.cond(
            rx.cond(
                is_logged_in,
                rx.cond(active_item != "flujos", active_item != "organizacion", False),
                False,
            ),
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
                rx.link("Características", color=COLORS["primary"], href="/backoffice/show-md?file=caracteristicas", is_external=True, font_size="1.3em"),
                rx.link("Precios", color=COLORS["primary"], href="/backoffice/show-md?file=precios", is_external=True, font_size="1.3em"),
                rx.link("Seguridad", color=COLORS["primary"], href="/backoffice/show-md?file=seguridad", is_external=True, font_size="1.3em"),
                spacing="2",
            ),
            rx.vstack(
                rx.text("Empresa", font_weight="bold", color=COLORS["foreground"], font_size="1.4em"),
                rx.link("Nosotros", color=COLORS["primary"], href="/backoffice/show-md?file=nosotros", is_external=True, font_size="1.3em"),
                rx.link("Blog", color=COLORS["primary"], href="/backoffice/show-md?file=blog", is_external=True, font_size="1.3em"),
                rx.link("Estado", color=COLORS["primary"], href="/backoffice/show-md?file=estado", is_external=True, font_size="1.3em"),
                spacing="2",
            ),
            rx.vstack(
                rx.text("Recursos", font_weight="bold", color=COLORS["foreground"], font_size="1.4em"),
                rx.link("Documentación", color=COLORS["primary"], href="/backoffice/show-md?file=documentacion", is_external=True, font_size="1.3em"),
                rx.link("Comunidad", color=COLORS["primary"], href="/backoffice/show-md?file=comunidad", is_external=True, font_size="1.3em"),
                rx.link("Soporte", color=COLORS["primary"], href="/backoffice/show-md?file=soporte", is_external=True, font_size="1.3em"),
                spacing="2",
            ),
            rx.vstack(
                rx.text("Legal", font_weight="bold", color=COLORS["foreground"], font_size="1.4em"),
                rx.link("Privacidad", color=COLORS["primary"], href="/backoffice/show-md?file=privacidad", is_external=True, font_size="1.3em"),
                rx.link("Términos", color=COLORS["primary"], href="/backoffice/show-md?file=terminos", is_external=True, font_size="1.3em"),
                rx.link("Contratos", color=COLORS["primary"], href="/backoffice/show-md?file=contratos", is_external=True, font_size="1.3em"),
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
                # Botón Volver al Frontend
                rx.button(
                    "Volver al Frontend",
                    on_click=State.go_to_frontend,
                    background_color="#22c55e",  # Verde del frontend
                    color="white",
                    font_size="1.1em",
                    _hover={"background_color": "#1ea34d"},
                ),
                rx.button(
                    "Desconectar",
                    on_click=State.user_logout,
                    background_color="#FF8C00",  # Naranja
                    color="white",
                    font_size="1.1em",
                    _hover={"background_color": "#FF7000"},
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
                        # Sin login_panel - el usuario ya está logado desde el frontend
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

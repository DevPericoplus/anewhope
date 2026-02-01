import base64
import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import reflex as rx

from adapters.api_client import (
    add_ticket_response,
    actualizar_tecnologia,
    asignar_tecnologia,
    create_organization_user,
    ensure_valid_tokens,
    get_organization_projects,
    get_organization_tickets,
    get_organization_users,
    get_proyecto_tecnologia,
    get_tecnologias,
    get_user_permissions,
    login_user,
    logout_user,
    refresh_tokens,
    request_login_otp,
    update_project_existence,
    update_project_status,
    update_ticket_status,
    update_user_status,
)
from pages.flujos import FlujosState, flujos_diagram, load_flujos_content
from pages.organizacion import load_organizacion_content
from pages.tecnologias import load_tecnologias_content
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
    
    # Estado para gestión de tickets de soporte
    org_tickets: list[dict] = []  # Lista de tickets de la organización
    
    # Estado del modal de gestión de ticket
    show_ticket_modal: bool = False
    selected_ticket_id: int = 0
    selected_ticket_titulo: str = ""
    selected_ticket_consulta: str = ""
    selected_ticket_estado: str = "abierto"
    selected_ticket_prioridad: str = "media"
    selected_ticket_respuesta: str = ""
    ticket_modal_error: str = ""
    ticket_modal_success: str = ""
    is_updating_ticket: bool = False
    
    # Estado para gestión de tecnologías
    tecnologias_list: list[dict] = []  # Lista de tecnologías disponibles
    selected_tech_project_id: int = 0  # Proyecto seleccionado
    selected_tecnologia_id: int = 0  # Tecnología seleccionada
    proyecto_tecnologia_asignada: dict = {}  # Asignación actual del proyecto
    tech_assign_error: str = ""
    tech_assign_success: str = ""
    is_loading_tecnologias: bool = False
    
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
    
    @rx.var
    def projects_for_tech_select(self) -> list[str]:
        """Lista de proyectos activos para el selector de tecnologías.
        
        Muestra solo el nombre del proyecto (igual que en frontend).
        """
        if not self.org_projects:
            return []
        return [
            p.get("name", p.get("nombre", "Sin nombre"))
            for p in self.org_projects
            if p.get("active", True) and p.get("existe", True) and p.get("name", p.get("nombre"))
        ]
    
    @rx.var
    def selected_tech_project_name(self) -> str:
        """Nombre del proyecto seleccionado para tecnologías."""
        if self.selected_tech_project_id <= 0:
            return ""
        for p in self.org_projects:
            if p.get("id") == self.selected_tech_project_id:
                return p.get("name", p.get("nombre", ""))
        return ""
    
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
            self.load_org_tickets()
        if menu == "tecnologias":
            self.load_org_projects()  # Para el selector de proyectos
            self.load_tecnologias()

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
        # BACKOFFICE: active_only=False para ver TODOS los usuarios (activos e inactivos)
        # Esto permite reactivar usuarios que fueron borrados lógicamente
        users = get_organization_users(
            organization_id=org_id,
            access_token=self.access_token,
            session_token=self.session_token,
            identity_type_id=5,  # Solo auditores (usuarios de organización)
            active_only=False,   # Backoffice muestra todos para poder reactivarlos
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
            # Limpiar campos
            self.new_user_name = ""
            self.new_user_email = ""
            self.new_user_mobile = ""
            # Cerrar modal
            self.show_create_user_modal = False
            # Recargar lista de usuarios (después de cerrar modal para que se vea)
            self.load_org_users()
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
        """Borrado LÓGICO de un usuario (active=false).
        
        IMPORTANTE: Este NO es un borrado físico. Solo marca el usuario
        como inactivo (active=0) en la base de datos. El usuario puede
        ser reactivado posteriormente usando el botón "Habilitar usuario".
        
        Args:
            user_id: ID del usuario a desactivar
        """
        print(f"[DEBUG] Borrado lógico de usuario: {user_id}")
        try:
            result = update_user_status(
                user_id=user_id,
                active=False,  # Borrado lógico: active = 0
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                # Actualizar estado local (el usuario sigue visible pero con badge "Inactivo")
                for user in self.org_users:
                    if user["user_id"] == user_id:
                        user["active"] = False
                self.org_users = self.org_users.copy()
                print(f"[DEBUG] Usuario {user_id} desactivado correctamente")
            else:
                print(f"[ERROR] No se pudo desactivar usuario: {result}")
        except Exception as e:
            print(f"[ERROR] delete_user: {type(e).__name__}: {e}")

    # ========== Gestión de Proyectos de la Organización ==========
    
    def load_org_projects(self):
        """Carga los proyectos de la organización actual desde la base de datos.
        
        En el backoffice se cargan TODOS los proyectos (incluyendo borrados lógicos)
        para permitir su recuperación.
        """
        try:
            org_id = self.organization_id
            if org_id <= 0 and self.access_token:
                org_id = self._extract_org_id_from_token(self.access_token)
            
            if org_id <= 0:
                self.org_projects = []
                return
            
            # En backoffice incluimos todos los proyectos (include_deleted=True)
            projects = get_organization_projects(
                organization_id=org_id,
                access_token=self.access_token,
                session_token=self.session_token,
                include_deleted=True,  # Incluir borrados lógicos
            )
            
            # Transformar al formato esperado por la UI
            # active=True: desbloqueado, active=False: bloqueado
            # existe=True: existe, existe=False: borrado lógico
            self.org_projects = [
                {
                    "id": p.get("id", 0),
                    "name": p.get("name", p.get("nombre", "Sin nombre")),
                    "description": p.get("descripcion", ""),
                    "active": p.get("active", True),
                    "existe": p.get("existe", True),
                }
                for p in projects
            ]
            print(f"[DEBUG] load_org_projects: {len(self.org_projects)} proyectos cargados")
        except Exception as e:
            print(f"[ERROR] load_org_projects: {type(e).__name__}: {e}")
            self.org_projects = []
    
    def create_project(self):
        """Abre el formulario para crear un nuevo proyecto."""
        # TODO: Implementar navegación a formulario de creación
        print("[DEBUG] Crear proyecto solicitado")
    
    def lock_project(self, project_id: int):
        """Bloquea un proyecto (active=false).
        
        IMPORTANTE: Este es un bloqueo LÓGICO, no un borrado físico.
        El proyecto permanece en la base de datos pero con active=false.
        """
        print(f"[DEBUG] Bloqueando proyecto: {project_id}")
        try:
            result = update_project_status(
                project_id=project_id,
                active=False,  # Bloquear = active=false
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                # Actualizar estado local
                for project in self.org_projects:
                    if project["id"] == project_id:
                        project["active"] = False
                self.org_projects = self.org_projects.copy()
                print(f"[DEBUG] Proyecto {project_id} bloqueado correctamente")
            else:
                print(f"[ERROR] No se pudo bloquear proyecto: {result}")
        except Exception as e:
            print(f"[ERROR] lock_project: {type(e).__name__}: {e}")
    
    def unlock_project(self, project_id: int):
        """Desbloquea un proyecto (active=true).
        
        IMPORTANTE: Reactiva un proyecto bloqueado.
        """
        print(f"[DEBUG] Desbloqueando proyecto: {project_id}")
        try:
            result = update_project_status(
                project_id=project_id,
                active=True,  # Desbloquear = active=true
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                # Actualizar estado local
                for project in self.org_projects:
                    if project["id"] == project_id:
                        project["active"] = True
                self.org_projects = self.org_projects.copy()
                print(f"[DEBUG] Proyecto {project_id} desbloqueado correctamente")
            else:
                print(f"[ERROR] No se pudo desbloquear proyecto: {result}")
        except Exception as e:
            print(f"[ERROR] unlock_project: {type(e).__name__}: {e}")
    
    def delete_project(self, project_id: int):
        """Borrado LÓGICO de un proyecto (existe=false).
        
        IMPORTANTE: Este es un BORRADO LÓGICO usando el campo 'existe'.
        El proyecto permanece en la BD pero con existe=false.
        Puede recuperarse con "Recuperar proyecto".
        """
        print(f"[DEBUG] Borrando proyecto (lógico): {project_id}")
        try:
            result = update_project_existence(
                project_id=project_id,
                existe=False,  # Borrado lógico
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                # Actualizar estado local
                for project in self.org_projects:
                    if project["id"] == project_id:
                        project["existe"] = False
                self.org_projects = self.org_projects.copy()
                print(f"[DEBUG] Proyecto {project_id} borrado lógicamente")
            else:
                print(f"[ERROR] No se pudo borrar proyecto: {result}")
        except Exception as e:
            print(f"[ERROR] delete_project: {type(e).__name__}: {e}")
    
    def restore_project(self, project_id: int):
        """Recupera un proyecto borrado lógicamente (existe=true).
        
        IMPORTANTE: Recupera un proyecto que fue borrado lógicamente.
        Pone existe=true en la BD.
        """
        print(f"[DEBUG] Recuperando proyecto: {project_id}")
        try:
            result = update_project_existence(
                project_id=project_id,
                existe=True,  # Recuperar
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                # Actualizar estado local
                for project in self.org_projects:
                    if project["id"] == project_id:
                        project["existe"] = True
                self.org_projects = self.org_projects.copy()
                print(f"[DEBUG] Proyecto {project_id} recuperado")
            else:
                print(f"[ERROR] No se pudo recuperar proyecto: {result}")
        except Exception as e:
            print(f"[ERROR] restore_project: {type(e).__name__}: {e}")
    
    def request_project_support(self, project_id: int):
        """Solicita soporte para un proyecto."""
        # TODO: Implementar formulario de soporte
        print(f"[DEBUG] Solicitar soporte para proyecto: {project_id}")

    # ========== Gestión de Tickets de Soporte ==========
    
    def load_org_tickets(self):
        """Carga los tickets de la organización desde la base de datos.
        
        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        try:
            org_id = self.organization_id
            if org_id <= 0 and self.access_token:
                org_id = self._extract_org_id_from_token(self.access_token)
            
            if org_id <= 0:
                self.org_tickets = []
                return
            
            tickets = get_organization_tickets(
                organization_id=org_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            self.org_tickets = tickets
            print(f"[DEBUG] load_org_tickets: {len(self.org_tickets)} tickets cargados")
        except Exception as e:
            print(f"[ERROR] load_org_tickets: {type(e).__name__}: {e}")
            self.org_tickets = []
    
    def open_ticket_modal(self, ticket_id: int):
        """Abre el modal para gestionar un ticket."""
        # Buscar el ticket
        ticket = None
        for t in self.org_tickets:
            if t.get("id") == ticket_id:
                ticket = t
                break
        
        if not ticket:
            print(f"[ERROR] Ticket {ticket_id} no encontrado")
            return
        
        # Cargar datos en el estado
        self.selected_ticket_id = ticket_id
        self.selected_ticket_titulo = ticket.get("titulo", "")
        self.selected_ticket_consulta = ticket.get("consulta", "")
        self.selected_ticket_estado = ticket.get("estado", "abierto")
        self.selected_ticket_prioridad = ticket.get("prioridad", "media")
        self.selected_ticket_respuesta = ticket.get("respuesta", "") or ""
        self.ticket_modal_error = ""
        self.ticket_modal_success = ""
        self.is_updating_ticket = False
        self.show_ticket_modal = True
        print(f"[DEBUG] Abriendo modal de ticket: {ticket_id}")
    
    def close_ticket_modal(self):
        """Cierra el modal de ticket."""
        self.show_ticket_modal = False
        self.selected_ticket_id = 0
        self.selected_ticket_titulo = ""
        self.selected_ticket_consulta = ""
        self.selected_ticket_estado = "abierto"
        self.selected_ticket_prioridad = "media"
        self.selected_ticket_respuesta = ""
        self.ticket_modal_error = ""
        self.ticket_modal_success = ""
        self.is_updating_ticket = False
    
    def set_ticket_estado(self, value: str):
        """Establece el estado del ticket."""
        self.selected_ticket_estado = value
    
    def set_ticket_prioridad(self, value: str):
        """Establece la prioridad del ticket."""
        self.selected_ticket_prioridad = value
    
    def set_ticket_respuesta(self, value: str):
        """Establece la respuesta del ticket."""
        self.selected_ticket_respuesta = value
    
    def save_ticket_changes(self):
        """Guarda los cambios del ticket (estado/prioridad).
        
        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        self.ticket_modal_error = ""
        self.is_updating_ticket = True
        
        try:
            result = update_ticket_status(
                ticket_id=self.selected_ticket_id,
                estado=self.selected_ticket_estado,
                prioridad=self.selected_ticket_prioridad,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            if result.get("success"):
                self.ticket_modal_success = "Ticket actualizado correctamente"
                # Actualizar en la lista local
                for t in self.org_tickets:
                    if t.get("id") == self.selected_ticket_id:
                        t["estado"] = self.selected_ticket_estado
                        t["prioridad"] = self.selected_ticket_prioridad
                self.org_tickets = self.org_tickets.copy()
            else:
                self.ticket_modal_error = "Error al actualizar el ticket"
        except Exception as e:
            self.ticket_modal_error = f"Error: {e}"
            print(f"[ERROR] save_ticket_changes: {e}")
        finally:
            self.is_updating_ticket = False
    
    def save_ticket_response(self):
        """Guarda la respuesta del ticket.
        
        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        if not self.selected_ticket_respuesta.strip():
            self.ticket_modal_error = "La respuesta no puede estar vacía"
            return
        
        self.ticket_modal_error = ""
        self.is_updating_ticket = True
        
        try:
            result = add_ticket_response(
                ticket_id=self.selected_ticket_id,
                respuesta=self.selected_ticket_respuesta,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            if result.get("success"):
                self.ticket_modal_success = "Respuesta enviada correctamente"
                # Actualizar en la lista local
                for t in self.org_tickets:
                    if t.get("id") == self.selected_ticket_id:
                        t["respuesta"] = self.selected_ticket_respuesta
                self.org_tickets = self.org_tickets.copy()
            else:
                self.ticket_modal_error = "Error al enviar la respuesta"
        except Exception as e:
            self.ticket_modal_error = f"Error: {e}"
            print(f"[ERROR] save_ticket_response: {e}")
        finally:
            self.is_updating_ticket = False

    # ========== Gestión de Tecnologías ==========
    
    def load_tecnologias(self):
        """Carga la lista de tecnologías disponibles desde la base de datos.
        
        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        try:
            self.is_loading_tecnologias = True
            result = get_tecnologias(
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            if result.get("tecnologias"):
                self.tecnologias_list = result["tecnologias"]
                print(f"[DEBUG] load_tecnologias: {len(self.tecnologias_list)} tecnologías cargadas")
            else:
                self.tecnologias_list = []
        except Exception as e:
            print(f"[ERROR] load_tecnologias: {type(e).__name__}: {e}")
            self.tecnologias_list = []
        finally:
            self.is_loading_tecnologias = False
    
    def select_tech_project(self, value: str):
        """Selecciona un proyecto para asignar tecnología.
        
        Al seleccionar carga la tecnología actual asignada (si existe).
        El valor es el nombre del proyecto (igual que en frontend).
        """
        try:
            # Buscar el proyecto por nombre
            project_id = 0
            for p in self.org_projects:
                if p.get("name", p.get("nombre")) == value:
                    project_id = p.get("id", 0)
                    break
            
            self.selected_tech_project_id = project_id
            self.tech_assign_error = ""
            self.tech_assign_success = ""
            
            if self.selected_tech_project_id > 0:
                # Cargar tecnología actual del proyecto
                result = get_proyecto_tecnologia(
                    project_id=self.selected_tech_project_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
                
                if result.get("success") and result.get("asignacion"):
                    asignacion = result["asignacion"]
                    self.proyecto_tecnologia_asignada = asignacion
                    self.selected_tecnologia_id = asignacion.get("id_tecnologia", 0)
                else:
                    self.proyecto_tecnologia_asignada = {}
                    self.selected_tecnologia_id = 0
            else:
                self.proyecto_tecnologia_asignada = {}
                self.selected_tecnologia_id = 0
        except Exception as e:
            print(f"[ERROR] select_tech_project: {type(e).__name__}: {e}")
            self.tech_assign_error = f"Error al cargar proyecto: {e}"
    
    def select_tecnologia(self, tech: dict):
        """Selecciona una tecnología.
        
        Recibe el diccionario completo de la tecnología.
        """
        tech_id = tech.get("id", 0) if isinstance(tech, dict) else 0
        is_active = tech.get("active", False) if isinstance(tech, dict) else False
        if is_active:
            self.selected_tecnologia_id = tech_id
            self.tech_assign_error = ""
            print(f"[DEBUG] Tecnología seleccionada: {tech_id}")
    
    def asignar_tecnologia_proyecto(self):
        """Asigna o actualiza la tecnología de un proyecto.
        
        En el Backoffice se permite cambiar la tecnología (UPDATE).
        
        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        self.tech_assign_error = ""
        self.tech_assign_success = ""
        
        if self.selected_tech_project_id <= 0:
            self.tech_assign_error = "Selecciona un proyecto"
            return
        
        if self.selected_tecnologia_id <= 0:
            self.tech_assign_error = "Selecciona una tecnología"
            return
        
        try:
            # Si ya tiene asignación, actualizar (UPDATE)
            if self.proyecto_tecnologia_asignada:
                result = actualizar_tecnologia(
                    project_id=self.selected_tech_project_id,
                    id_tecnologia=self.selected_tecnologia_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
                
                if result.get("success"):
                    self.tech_assign_success = "Tecnología actualizada correctamente"
                    # Actualizar estado local
                    self.proyecto_tecnologia_asignada = {
                        "id_tecnologia": self.selected_tecnologia_id,
                    }
                else:
                    self.tech_assign_error = result.get("error", "Error al actualizar tecnología")
            else:
                # Primera asignación (INSERT)
                result = asignar_tecnologia(
                    project_id=self.selected_tech_project_id,
                    id_tecnologia=self.selected_tecnologia_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
                
                if result.get("success"):
                    self.tech_assign_success = "Tecnología asignada correctamente"
                    # Actualizar estado local
                    self.proyecto_tecnologia_asignada = {
                        "id_tecnologia": self.selected_tecnologia_id,
                    }
                else:
                    self.tech_assign_error = result.get("error", "Error al asignar tecnología")
        except Exception as e:
            self.tech_assign_error = f"Error: {e}"
            print(f"[ERROR] asignar_tecnologia_proyecto: {type(e).__name__}: {e}")

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
        
        # Continuar con la lógica de inicialización de componentes según menú activo
        if self.user_active_menu == "organizacion":
            # Cargar usuarios, proyectos y tickets de la organización
            self.load_org_users()
            self.load_org_projects()
            self.load_org_tickets()
        elif self.user_active_menu == "flujos":
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
        
        # Actualizar tokens y timestamps usando método de SharedSessionState
        self.update_tokens(
            access_token=access_token,
            session_token=session_token,
            access_expires_at=int(response.get("access_expires_at", 0)),
            session_expires_at=int(response.get("session_expires_at", 0)),
        )

    def ensure_tokens_valid(self) -> bool:
        """Verifica y renueva tokens automáticamente si es necesario.
        
        Esta función debe llamarse antes de cada operación que requiera autenticación.
        Retorna True si los tokens son válidos (o se renovaron exitosamente).
        Retorna False si la sesión expiró y el usuario debe re-autenticarse.
        """
        if not self.access_token or not self.session_token:
            return False
        
        result = ensure_valid_tokens(
            access_token=self.access_token,
            session_token=self.session_token,
            access_expires_at=self.access_token_expires_at,
            session_expires_at=self.session_token_expires_at,
        )
        
        if result.get("error"):
            # Si hay error, la sesión expiró - limpiar y forzar re-login
            self.login_error = result["error"]
            self.clear_session()
            return False
        
        if result.get("renewed"):
            # Tokens renovados - actualizar en el state
            self.update_tokens(
                access_token=result["access_token"],
                session_token=result["session_token"],
                access_expires_at=result["access_expires_at"],
                session_expires_at=result["session_expires_at"],
            )
        
        return True

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
                        rx.icon("user-round-check", size=22),
                        variant="ghost",
                        size="2",
                        color_scheme="green",
                        cursor="pointer",
                        on_click=State.enable_user(user["user_id"]),
                        _hover={"color": "#22c55e", "background_color": COLORS["border"]},
                    ),
                    content="Habilitar usuario",
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("user-round-x", size=22),
                        variant="ghost",
                        size="2",
                        color_scheme="red",
                        cursor="pointer",
                        on_click=State.disable_user(user["user_id"]),
                        _hover={"color": "#ef4444", "background_color": COLORS["border"]},
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
    """Fila de proyecto con acciones.
    
    Estados del proyecto:
    - existe=False: Borrado (rojo) - máxima prioridad visual
    - active=False: Bloqueado (naranja)
    - active=True y existe=True: Activo (verde)
    """
    return rx.hstack(
        # Información del proyecto a la izquierda
        rx.hstack(
            rx.text(project["name"], font_weight="bold", font_size="1.1em", color=COLORS["foreground"]),
            # Badge de estado: Borrado > Bloqueado > Activo
            rx.cond(
                ~project["existe"],  # Si existe=False → Borrado
                rx.badge("Borrado", color_scheme="red", variant="soft", size="3"),
                rx.cond(
                    project["active"],  # Si active=True → Activo
                    rx.badge("Activo", color_scheme="green", variant="soft", size="3"),
                    rx.badge("Bloqueado", color_scheme="orange", variant="soft", size="3"),
                ),
            ),
            spacing="3",
            align="center",
        ),
        # Acciones a la derecha
        rx.hstack(
            # Recuperar proyecto (verde) - solo para proyectos borrados
            rx.tooltip(
                rx.icon_button(
                    rx.icon("archive-restore", size=22),
                    variant="ghost",
                    size="2",
                    color_scheme="green",
                    cursor="pointer",
                    on_click=State.restore_project(project["id"]),
                    _hover={"color": "#22c55e", "background_color": COLORS["border"]},
                ),
                content="Recuperar proyecto",
            ),
            # Desbloquear proyecto (verde) - activa el proyecto
            rx.tooltip(
                rx.icon_button(
                    rx.icon("lock-open", size=22),
                    variant="ghost",
                    size="2",
                    color_scheme="green",
                    cursor="pointer",
                    on_click=State.unlock_project(project["id"]),
                    _hover={"color": "#22c55e", "background_color": COLORS["border"]},
                ),
                content="Desbloquear proyecto",
            ),
            # Bloquear proyecto (naranja) - desactiva el proyecto
            rx.tooltip(
                rx.icon_button(
                    rx.icon("lock", size=22),
                    variant="ghost",
                    size="2",
                    color_scheme="orange",
                    cursor="pointer",
                    on_click=State.lock_project(project["id"]),
                    _hover={"color": "#f97316", "background_color": COLORS["border"]},
                ),
                content="Bloquear proyecto",
            ),
            # Borrar proyecto (rojo) - borrado lógico
            rx.tooltip(
                rx.icon_button(
                    rx.icon("trash-2", size=22),
                    variant="ghost",
                    size="2",
                    color_scheme="red",
                    cursor="pointer",
                    on_click=State.delete_project(project["id"]),
                    _hover={"color": "#ef4444", "background_color": COLORS["border"]},
                ),
                content="Borrar proyecto",
            ),
            # Solicitud de soporte
            rx.tooltip(
                rx.icon_button(
                    rx.icon("headset", size=22),
                    variant="ghost",
                    size="2",
                    color_scheme="gray",
                    cursor="pointer",
                    on_click=State.request_project_support(project["id"]),
                    _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
                ),
                content="Solicitud de soporte",
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
        # SEGURIDAD: Solo mostrar si el usuario tiene permiso project_create
        rx.cond(
            State.can_project_create,
            rx.button(
                rx.icon("folder-plus", size=20, color="black"),
                rx.text("Crear proyecto", font_weight="bold", color="black"),
                on_click=State.create_project,
                color_scheme="orange",
                variant="solid",
                size="3",
            ),
            rx.fragment(),
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


def ticket_row(ticket: dict) -> rx.Component:
    """Fila de ticket con acciones."""
    # Colores por estado
    estado_colors = {
        "abierto": "green",
        "en_espera": "yellow",
        "resuelto": "blue",
        "cerrado": "gray",
    }
    # Colores por prioridad
    prioridad_colors = {
        "baja": "gray",
        "media": "yellow",
        "alta": "orange",
        "urgente": "red",
    }
    
    return rx.hstack(
        # Información del ticket a la izquierda
        rx.vstack(
            rx.hstack(
                rx.text(f"#{ticket['id']}", font_weight="bold", color=COLORS["muted_foreground"]),
                rx.text(ticket["titulo"], font_weight="bold", font_size="1.05em", color=COLORS["foreground"]),
                spacing="2",
            ),
            rx.hstack(
                rx.badge(
                    ticket["estado"],
                    color_scheme=estado_colors.get(ticket.get("estado", "abierto"), "gray"),
                    variant="soft",
                    size="2",
                ),
                rx.badge(
                    ticket["prioridad"],
                    color_scheme=prioridad_colors.get(ticket.get("prioridad", "media"), "yellow"),
                    variant="soft",
                    size="2",
                ),
                rx.cond(
                    ticket.get("respuesta", "") != "",
                    rx.badge("Con respuesta", color_scheme="blue", variant="outline", size="2"),
                    rx.badge("Sin respuesta", color_scheme="gray", variant="outline", size="2"),
                ),
                spacing="2",
            ),
            spacing="1",
            align_items="flex-start",
        ),
        # Botón gestionar a la derecha
        rx.tooltip(
            rx.icon_button(
                rx.icon("pencil", size=20),
                variant="ghost",
                size="2",
                color_scheme="blue",
                cursor="pointer",
                on_click=State.open_ticket_modal(ticket["id"]),
                _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
            ),
            content="Gestionar ticket",
        ),
        justify="between",
        align="center",
        width="100%",
        padding="0.75em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
    )


def ticket_management_modal() -> rx.Component:
    """Modal para gestionar un ticket de soporte."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("headset", size=24, color=COLORS["primary"]),
                    rx.text("Gestión de Ticket", font_weight="bold", font_size="1.3em"),
                    spacing="3",
                    align="center",
                ),
            ),
            # Información del ticket
            rx.vstack(
                # Título
                rx.hstack(
                    rx.text("Motivo:", font_weight="bold", color=COLORS["muted_foreground"]),
                    rx.text(State.selected_ticket_titulo, color=COLORS["foreground"]),
                    spacing="2",
                ),
                # Consulta (solo lectura)
                rx.vstack(
                    rx.text("Consulta del cliente:", font_weight="bold", color=COLORS["muted_foreground"]),
                    rx.box(
                        rx.text(State.selected_ticket_consulta, color=COLORS["foreground"]),
                        padding="0.75em",
                        background_color=COLORS["input"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.25em",
                        width="100%",
                        max_height="100px",
                        overflow_y="auto",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Selectores de estado y prioridad
                rx.hstack(
                    rx.vstack(
                        rx.text("Estado", font_weight="bold", color=COLORS["foreground"]),
                        rx.select(
                            ["abierto", "en_espera", "resuelto", "cerrado"],
                            value=State.selected_ticket_estado,
                            on_change=State.set_ticket_estado,
                            width="150px",
                        ),
                        spacing="1",
                        align_items="flex-start",
                    ),
                    rx.vstack(
                        rx.text("Prioridad", font_weight="bold", color=COLORS["foreground"]),
                        rx.select(
                            ["baja", "media", "alta", "urgente"],
                            value=State.selected_ticket_prioridad,
                            on_change=State.set_ticket_prioridad,
                            width="150px",
                        ),
                        spacing="1",
                        align_items="flex-start",
                    ),
                    spacing="4",
                ),
                # Campo de respuesta
                rx.vstack(
                    rx.text("Respuesta", font_weight="bold", color=COLORS["foreground"]),
                    rx.text_area(
                        value=State.selected_ticket_respuesta,
                        on_change=State.set_ticket_respuesta,
                        placeholder="Escribe tu respuesta al cliente...",
                        width="100%",
                        min_height="100px",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Mensajes de error/éxito
                rx.cond(
                    State.ticket_modal_error != "",
                    rx.text(State.ticket_modal_error, color="red", font_size="0.9em"),
                ),
                rx.cond(
                    State.ticket_modal_success != "",
                    rx.text(State.ticket_modal_success, color="green", font_size="0.9em"),
                ),
                # Botones
                rx.hstack(
                    rx.button(
                        "Cancelar",
                        on_click=State.close_ticket_modal,
                        color_scheme="gray",
                        variant="outline",
                    ),
                    rx.button(
                        "Guardar Estado",
                        on_click=State.save_ticket_changes,
                        color_scheme="blue",
                        disabled=State.is_updating_ticket,
                    ),
                    rx.button(
                        "Enviar Respuesta",
                        on_click=State.save_ticket_response,
                        color_scheme="green",
                        disabled=State.is_updating_ticket,
                    ),
                    spacing="2",
                    justify="end",
                    width="100%",
                ),
                width="100%",
                spacing="3",
                padding="1em",
            ),
            max_width="500px",
            background_color=COLORS["card"],
        ),
        open=State.show_ticket_modal,
    )


def tickets_management_panel() -> rx.Component:
    """Panel de gestión de tickets de soporte."""
    return rx.vstack(
        rx.hstack(
            rx.icon("headset", size=28, color=COLORS["primary"]),
            rx.heading("Gestión de Tickets", size="6", color=COLORS["foreground"]),
            spacing="3",
            align="center",
        ),
        rx.text(
            "Tickets de soporte de la organización",
            color=COLORS["muted_foreground"],
            font_size="0.9em",
        ),
        # Modal de gestión de ticket
        ticket_management_modal(),
        # Lista de tickets
        rx.cond(
            State.org_tickets.length() > 0,
            rx.vstack(
                rx.foreach(
                    State.org_tickets,
                    ticket_row,
                ),
                width="100%",
                spacing="2",
            ),
            rx.text(
                "No hay tickets de soporte",
                color=COLORS["muted_foreground"],
                font_style="italic",
                padding="1em",
            ),
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
    """Paneles de gestión de usuarios, proyectos y tickets para la sección Organización."""
    return rx.vstack(
        users_management_panel(),
        projects_management_panel(),
        tickets_management_panel(),
        width="100%",
        spacing="4",
        margin_top="1.5em",
    )


def tecnologia_item(tech: dict) -> rx.Component:
    """Componente para mostrar una tecnología en la lista.
    
    En backoffice se puede cambiar la asignación en cualquier momento.
    """
    tech_id = tech.get("id", 0)
    tech_name = tech.get("name", "Sin nombre")
    tech_descripcion = tech.get("descripcion", "")
    is_active = tech.get("active", True)
    is_selected = State.selected_tecnologia_id == tech_id
    
    return rx.box(
        rx.hstack(
            # Indicador de selección (círculo naranja)
            rx.box(
                rx.cond(
                    is_selected,
                    rx.icon("check", size=20, color="white"),
                    rx.fragment(),
                ),
                width="32px",
                height="32px",
                border_radius="50%",
                border=rx.cond(
                    is_selected,
                    f"3px solid {COLORS['primary']}",
                    f"3px solid {COLORS['border']}",
                ),
                background_color=rx.cond(is_selected, COLORS["primary"], "transparent"),
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink="0",
            ),
            rx.vstack(
                rx.text(
                    tech_name,
                    font_weight="bold",
                    font_size="1.25em",
                    color=rx.cond(is_active, COLORS["foreground"], COLORS["muted_foreground"]),
                ),
                rx.text(
                    tech_descripcion,
                    font_size="1.05em",
                    color=COLORS["muted_foreground"],
                    opacity=rx.cond(is_active, "1", "0.6"),
                ),
                spacing="2",
                align_items="flex-start",
                flex="1",
            ),
            rx.cond(
                ~is_active,
                rx.badge("Inactiva", color_scheme="gray", size="2"),
                rx.fragment(),
            ),
            spacing="4",
            align="center",
            width="100%",
        ),
        padding="1.25em",
        background=rx.cond(
            is_selected,
            f"{COLORS['primary']}20",
            COLORS["card"],
        ),
        border=rx.cond(
            is_selected,
            f"3px solid {COLORS['primary']}",
            f"2px solid {COLORS['border']}",
        ),
        border_radius="0.75em",
        opacity=rx.cond(is_active, "1", "0.5"),
        cursor=rx.cond(is_active, "pointer", "not-allowed"),
        on_click=State.select_tecnologia(tech),
        _hover=rx.cond(
            is_active,
            {"background": f"{COLORS['primary']}15"},
            {},
        ),
        width="100%",
    )


def tecnologias_management_panel() -> rx.Component:
    """Panel de gestión de tecnologías por proyecto.
    
    En backoffice permite cambiar la tecnología asignada en cualquier momento.
    """
    return rx.vstack(
        rx.hstack(
            rx.icon("cpu", size=36, color=COLORS["primary"]),
            rx.heading("Gestión de Tecnología", size="7", color=COLORS["foreground"]),
            spacing="4",
            align_items="center",
        ),
        rx.text(
            "Selecciona un proyecto y asigna o cambia la tecnología asociada.",
            color=COLORS["muted_foreground"],
            font_size="1.1em",
        ),
        # Selector de proyecto
        rx.hstack(
            rx.text("Proyecto:", font_weight="bold", color=COLORS["foreground"], font_size="1.1em"),
            rx.select(
                State.projects_for_tech_select,
                placeholder="Selecciona un proyecto",
                value=State.selected_tech_project_name,
                on_change=State.select_tech_project,
                width="350px",
                size="3",
            ),
            spacing="4",
            align_items="center",
            margin_top="1em",
        ),
        # Lista de tecnologías
        rx.cond(
            State.selected_tech_project_id > 0,
            rx.vstack(
                rx.text(
                    "Selecciona la tecnología:",
                    font_weight="bold",
                    color=COLORS["foreground"],
                    font_size="1.15em",
                    margin_top="1em",
                ),
                rx.vstack(
                    rx.foreach(
                        State.tecnologias_list,
                        tecnologia_item,
                    ),
                    width="100%",
                    spacing="3",
                ),
                # Mostrar asignación actual
                rx.cond(
                    State.proyecto_tecnologia_asignada.length() > 0,
                    rx.hstack(
                        rx.icon("check-circle", size=24, color=COLORS["primary"]),
                        rx.text(
                            "Tecnología actualmente asignada",
                            color=COLORS["primary"],
                            font_size="1.05em",
                            font_weight="500",
                        ),
                        margin_top="0.75em",
                    ),
                    rx.fragment(),
                ),
                # Botón para cambiar asignación
                rx.button(
                    rx.icon("save", size=16),
                    "Guardar cambios",
                    on_click=State.asignar_tecnologia_proyecto,
                    color_scheme="blue",
                    margin_top="1em",
                    disabled=State.selected_tecnologia_id <= 0,
                ),
                # Mensajes de estado
                rx.cond(
                    State.tech_assign_success != "",
                    rx.callout(
                        State.tech_assign_success,
                        icon="check",
                        color_scheme="green",
                        margin_top="0.5em",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    State.tech_assign_error != "",
                    rx.callout(
                        State.tech_assign_error,
                        icon="alert-triangle",
                        color_scheme="red",
                        margin_top="0.5em",
                    ),
                    rx.fragment(),
                ),
                width="100%",
                align_items="flex-start",
            ),
            rx.text(
                "Selecciona un proyecto para ver las tecnologías disponibles.",
                color=COLORS["muted_foreground"],
                font_style="italic",
                margin_top="1em",
            ),
        ),
        width="100%",
        padding="1.5em",
        background=COLORS["card"],
        border_radius="12px",
        border=f"1px solid {COLORS['border']}",
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
        # Panel de gestión de tecnologías: visible solo en menú "tecnologias"
        rx.cond(
            rx.cond(is_logged_in, active_item == "tecnologias", False),
            tecnologias_management_panel(),
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

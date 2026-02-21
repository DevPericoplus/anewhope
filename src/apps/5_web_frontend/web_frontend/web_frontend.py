import base64
import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

# Configurar sys.path ANTES de cualquier import local
# para que los módulos puedan encontrar adapters, components, etc.
_frontend_dir = Path(__file__).parent.parent
if str(_frontend_dir) not in sys.path:
    sys.path.insert(0, str(_frontend_dir))

import reflex as rx

from adapters.api_client import (
    asignar_tecnologia,
    create_organization_project,
    create_organization_user,
    create_project_version,
    create_version_full,
    delete_organization_project,
    ensure_valid_tokens,
    get_organization_projects,
    get_organization_users,
    get_project_versions,
    get_proyecto_tecnologia,
    get_tecnologias,
    get_tecnologias_asignadas_org,
    get_user_permissions,
    login_user,
    logout_user,
    refresh_tokens,
    request_login_otp,
    request_project_support_api,
    update_project_status,
    update_user_status,
)
from pages.flujos import FlujosState, flujos_diagram, load_flujos_content
from pages.model_downloads import ModelDownloadState, model_downloads_panel
from pages.organizacion import load_organizacion_content
from pages.proyecciones import load_proyecciones_content
from pages.tecnologias import load_tecnologias_content
from low_panel_pages.show_md import show_md  # noqa: F401 - Importado para registrar la ruta
from web_frontend.shared_state import SharedSessionState
from components.explorador import explorador_panel, ExploradorState
from components.seguimiento import seguimiento_panel, SeguimientoState
from components.informes import informes_panel, InformesState

# Importar logger de actividad usando importlib (el directorio tiene número)
_activity_logger_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "reflex_shared" / "activity_logger.py"
_spec = importlib.util.spec_from_file_location("activity_logger", _activity_logger_path)
_activity_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_activity_module)

# Importar función de envío de SMS (para enviar OTP directamente a Infobip)
_common_security_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "security" / "common_security.py"
_send_message_by_sms = None
try:
    _spec_sms = importlib.util.spec_from_file_location("common_security", _common_security_path)
    _common_security_module = importlib.util.module_from_spec(_spec_sms)
    _spec_sms.loader.exec_module(_common_security_module)
    _send_message_by_sms = getattr(_common_security_module, "send_message_by_sms", None)
except Exception as e:
    logging.warning(f"No se pudo cargar send_message_by_sms: {e}")

# Importar storage_access_structure usando importlib
_storage_structure_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "storage_access_structure.py"
_storage_spec = importlib.util.spec_from_file_location("storage_access_structure", _storage_structure_path)
_storage_module = importlib.util.module_from_spec(_storage_spec)
_storage_spec.loader.exec_module(_storage_module)
get_folder_by_id_organization = _storage_module.get_folder_by_id_organization
get_folder_by_id_project = _storage_module.get_folder_by_id_project
get_folder_by_id_version = _storage_module.get_folder_by_id_version

# Importar version_reader usando importlib
_version_reader_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "utils" / "version_reader.py"
_version_spec = importlib.util.spec_from_file_location("version_reader", _version_reader_path)
_version_module = importlib.util.module_from_spec(_version_spec)
_version_spec.loader.exec_module(_version_module)
get_version = _version_module.get_version

# Obtener versión del frontend
APP_VERSION = get_version("frontend")

# Logger de actividad del frontend
activity_log = _activity_module.get_frontend_logger()
activity_log.log_startup()

# Configurar el logging root de Python para que también escriba en los archivos de log
# Esto hace que todos los loggers (incluyendo los de módulos como common_security)
# también escriban en activity.log y console.log
import logging as std_logging
from logging.handlers import RotatingFileHandler

# Solo configurar si no está ya configurado
if not std_logging.getLogger().handlers:
    # Obtener el logger root
    root_logger = std_logging.getLogger()
    root_logger.setLevel(std_logging.INFO)

    # Crear directorio de logs si no existe
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Handler para console.log (mismo que usa activity_logger)
    console_handler = RotatingFileHandler(
        logs_dir / "console.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    console_handler.setLevel(std_logging.INFO)
    console_formatter = std_logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Handler para activity.log
    activity_handler = RotatingFileHandler(
        logs_dir / "activity.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    activity_handler.setLevel(std_logging.INFO)
    activity_handler.setFormatter(console_formatter)
    root_logger.addHandler(activity_handler)

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
    
    # Estado para gestión de usuarios y proyectos de la organización
    # Estructura: {"user_id": int, "user_name": str, "active": bool}
    org_users: list[dict] = []
    org_projects: list[dict] = [
        {"id": 1, "name": "Asistente Comercial", "description": "Modelo de lenguaje para atención al cliente", "locked": False},
    ]
    
    # Estado para el modal de creación de usuario
    show_create_user_modal: bool = False
    new_user_name: str = ""
    new_user_email: str = ""
    new_user_mobile: str = ""
    create_user_error: str = ""
    create_user_success: str = ""
    is_creating_user: bool = False
    
    # Estado para el modal de creación de proyecto
    show_create_project_modal: bool = False
    new_project_name: str = ""
    new_project_description: str = ""
    create_project_error: str = ""
    create_project_success: str = ""
    is_creating_project: bool = False
    
    # Estado para el modal de asignar usuario a proyecto
    show_assign_user_modal: bool = False
    assign_user_id: int = 0
    assign_user_name: str = ""
    assign_selected_project_id: int = 0
    assign_selected_rol_id: int = 0  # Por defecto: Sin asignar
    assign_user_error: str = ""
    assign_user_success: str = ""
    is_assigning_user: bool = False
    user_current_roles: list[dict] = []  # Roles actuales del usuario en proyectos
    project_roles_base: list[dict] = []  # Catálogo maestro de roles (desde API)
    
    # Estado para el modal de quitar usuario de proyecto
    show_remove_user_modal: bool = False
    remove_user_id: int = 0
    remove_user_name: str = ""
    remove_selected_project_id: int = 0
    remove_user_error: str = ""
    remove_user_success: str = ""
    is_removing_user: bool = False
    
    # Estado para el panel de asignaciones de proyectos (solo lectura)
    project_assignments: list[dict] = []  # Lista de {proyecto, usuario, rol}
       # Estado para el modal de solicitud de soporte
    show_support_modal: bool = False
    support_project_id: int = 0
    support_project_name: str = ""
    support_titulo: str = ""  # Motivo del ticket
    support_consulta: str = ""  # Texto de la consulta
    support_error: str = ""
    support_success: str = ""
    is_creating_support: bool = False
    
    # Estado para gestión de tecnologías
    tecnologias_list: list[dict] = []  # Lista de tecnologías disponibles
    tecnologias_asignadas_list: list[dict] = []  # Proyectos con sus tecnologías asignadas
    selected_tech_project_id: int = 0  # Proyecto seleccionado para asignar tecnología
    selected_tecnologia_id: int = 0  # Tecnología seleccionada
    proyecto_tecnologia_asignada: dict = {}  # Asignación actual del proyecto
    tech_assign_error: str = ""
    tech_assign_success: str = ""
    is_loading_tecnologias: bool = False
    
    # Estado para gestión de proyecciones (versiones y contenidos)
    proyecciones_project_id: int = 0  # Proyecto seleccionado en proyecciones
    proyecciones_project_name: str = ""  # Nombre del proyecto seleccionado
    proyecciones_versions: list[dict] = []  # Lista de versiones del proyecto
    proyecciones_version_id: int = 0  # Versión seleccionada
    proyecciones_version_folder: str = ""  # Carpeta de versión (v001, v002, etc.)
    proyecciones_org_folder: str = ""  # Carpeta de organización (ORG00001, etc.)
    proyecciones_prj_folder: str = ""  # Carpeta de proyecto (PRJ0001, etc.)
    proyecciones_error: str = ""
    proyecciones_success: str = ""
    is_loading_versions: bool = False
    
    # Nota: Los siguientes campos ya vienen de SharedSessionState:
    # - user_logged_in, access_token, session_token, user_id, organization_id
    # - user_name, user_email, user_mobile, identity_type_id
    # - 45 permisos (can_training_create, can_folder_rename, etc.)
    # - Métodos: load_user_data(), clear_session(), go_to_backoffice(), etc.
    
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
        return self.identity_type_id in (1, 2, 10)
    
    @rx.var
    def projects_for_assign_select(self) -> list[str]:
        """Lista de proyectos disponibles para el selector de asignación.
        
        Muestra solo el nombre del proyecto.
        El mapeo nombre -> id se hace en set_assign_project.
        """
        return [
            project.get("name", "Sin nombre")
            for project in self.org_projects
            if project.get("name")
        ]
    
    @rx.var
    def projects_for_remove_select(self) -> list[str]:
        """Lista de proyectos donde el usuario tiene rol activo (para quitar).
        
        Muestra: "nombre_proyecto (rol)"
        Solo muestra proyectos donde el usuario tiene asignación activa.
        """
        projects = []
        for role in self.user_current_roles:
            if role.get("active", False):
                project_name = role.get("proyecto_nombre", "Proyecto")
                rol_nombre = role.get("rol_nombre", "Rol")
                projects.append(f"{project_name} ({rol_nombre})")
        return projects
    
    @rx.var
    def roles_for_select(self) -> list[str]:
        """Lista de roles disponibles para el selector.
        
        Usa los roles cargados desde la tabla proyectos_roles_base.
        Incluye "Sin asignar" (id=0) para mostrar el estado actual.
        """
        if not self.project_roles_base:
            # Fallback si no se han cargado los roles
            return ["Sin asignar", "Editor", "Lector", "Auditor"]
        
        return [
            role.get("nombre_rol", "")
            for role in self.project_roles_base
        ]
    
    @rx.var
    def selected_rol_name(self) -> str:
        """Nombre del rol seleccionado para el selector."""
        if not self.project_roles_base:
            # Fallback
            rol_mapping = {0: "Sin asignar", 3: "Editor", 4: "Lector", 5: "Auditor"}
            return rol_mapping.get(self.assign_selected_rol_id, "Sin asignar")
        
        for role in self.project_roles_base:
            if role.get("id") == self.assign_selected_rol_id:
                return role.get("nombre_rol", "")
        return "Sin asignar"
    
    @rx.var
    def selected_project_name(self) -> str:
        """Nombre del proyecto seleccionado para el selector."""
        if self.assign_selected_project_id <= 0:
            return ""
        for project in self.org_projects:
            if project.get("id") == self.assign_selected_project_id:
                return project.get("name", "")
        return ""
    
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
            self.load_project_assignments()
            self.load_project_roles_base()
        if menu == "tecnologias":
            self.load_org_projects()  # Para el selector de proyectos
            self.load_tecnologias()
            self.load_tecnologias_asignadas()  # Cargar proyectos con sus asignaciones
        if menu == "proyecciones":
            self.load_org_projects()  # Para el selector de proyectos
            self.reset_proyecciones_state()  # Limpiar estado anterior
        if menu == "descargas":
            return [
                ModelDownloadState.init_selectors,
                ModelDownloadState.load_models,
            ]

    # ========== Gestión de Usuarios de la Organización ==========
    
    def load_org_users(self):
        """Carga los usuarios de la organización actual desde la base de datos.
        
        Filtra por:
        - organization_id del usuario logueado
        - identity_type_id = 5 (auditores/usuarios base)
        """
        try:
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
                active_only=False,  # Mostrar también usuarios deshabilitados
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
            print(f"[DEBUG] load_org_users: Final org_users = {self.org_users}")
        except Exception as e:
            print(f"[ERROR] load_org_users: {type(e).__name__}: {e}")
            self.org_users = []
    
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
            update_user_status(
                user_id=user_id,
                active=True,
                access_token=self.access_token,
                session_token=self.session_token,
            )
        except Exception as e:
            print(f"[ERROR] Error habilitando usuario: {e}")
        finally:
            self.load_org_users()

    def disable_user(self, user_id: int):
        """Deshabilita un usuario de la organización."""
        try:
            update_user_status(
                user_id=user_id,
                active=False,
                access_token=self.access_token,
                session_token=self.session_token,
            )
        except Exception as e:
            print(f"[ERROR] Error deshabilitando usuario: {e}")
        finally:
            self.load_org_users()
    
    def load_project_roles_base(self):
        """Carga el catálogo maestro de roles base desde la API.
        
        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
        
        Esta información se usa en los selectores de roles y validaciones.
        """
        from adapters.api_client import get_project_roles_base
        
        try:
            roles = get_project_roles_base(
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.project_roles_base = roles
            print(f"[DEBUG] Roles base cargados: {len(roles)}")
        except Exception as e:
            print(f"[ERROR] Error cargando roles base: {e}")
            # Fallback a valores por defecto
            self.project_roles_base = [
                {"id": 0, "nombre_rol": "Sin asignar", "descripcion": "Usuario sin rol asignado"},
                {"id": 3, "nombre_rol": "Editor", "descripcion": "Puede modificar contenido"},
                {"id": 4, "nombre_rol": "Lector", "descripcion": "Solo lectura"},
                {"id": 5, "nombre_rol": "Auditor", "descripcion": "Acceso limitado para auditoría"},
            ]

    def assign_user_to_projects(self, user_id: int):
        """Abre el modal para asignar un usuario a proyectos."""
        # Buscar nombre del usuario
        user_name = ""
        for user in self.org_users:
            if user.get("user_id") == user_id:
                user_name = user.get("user_name", "")
                break
        
        # Cargar roles base si no están cargados
        if not self.project_roles_base:
            self.load_project_roles_base()
        
        # Cargar roles actuales del usuario en proyectos
        self._load_user_current_roles(user_id)
        
        # Configurar el modal
        self.assign_user_id = user_id
        self.assign_user_name = user_name
        self.assign_selected_project_id = 0
        self.assign_selected_rol_id = 0  # Sin asignar por defecto
        self.assign_user_error = ""
        self.assign_user_success = ""
        self.show_assign_user_modal = True
        print(f"[DEBUG] Abrir modal asignar usuario: {user_id} - {user_name}")
    
    def _load_user_current_roles(self, user_id: int):
        """Carga los roles actuales del usuario en proyectos."""
        from adapters.api_client import get_user_project_roles
        
        try:
            org_id = self.organization_id
            if org_id <= 0 and self.access_token:
                org_id = self._extract_org_id_from_token(self.access_token)
            
            response = get_user_project_roles(
                user_id=user_id,
                organization_id=org_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            self.user_current_roles = response.get("roles", [])
            print(f"[DEBUG] Roles actuales del usuario {user_id}: {len(self.user_current_roles)}")
        except Exception as e:
            print(f"[ERROR] Error cargando roles del usuario: {e}")
            self.user_current_roles = []
    
    def load_project_assignments(self):
        """Carga todas las asignaciones activas de usuarios a proyectos.
        
        Consulta todos los usuarios de la organización y sus roles en proyectos.
        Solo muestra asignaciones con active=True.
        
        Formato de cada elemento:
        {
            "proyecto_nombre": str,
            "usuario_nombre": str,
            "rol_nombre": str (Editor/Lector/Auditor)
        }
        """
        from adapters.api_client import get_user_project_roles
        
        try:
            org_id = self.organization_id
            if org_id <= 0 and self.access_token:
                org_id = self._extract_org_id_from_token(self.access_token)
            
            if org_id <= 0:
                self.project_assignments = []
                return
            
            # Recopilar asignaciones de todos los usuarios de la organización
            assignments = []
            rol_nombres = {3: "Editor", 4: "Lector", 5: "Auditor"}
            
            for user in self.org_users:
                user_id = user.get("user_id", 0)
                user_name = user.get("user_name", "Sin nombre")
                
                if user_id <= 0:
                    continue
                
                # Obtener roles del usuario
                response = get_user_project_roles(
                    user_id=user_id,
                    organization_id=org_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
                
                roles = response.get("roles", [])
                
                # Obtener IDs de proyectos existentes (existe=true)
                existing_project_ids = {
                    p.get("id") for p in self.org_projects if p.get("existe", True)
                }
                
                for role in roles:
                    # Solo mostrar asignaciones activas de proyectos existentes
                    project_id = role.get("id_proyecto", 0)
                    if role.get("active", False) and project_id in existing_project_ids:
                        assignments.append({
                            "proyecto_nombre": role.get("proyecto_nombre", "Sin proyecto"),
                            "usuario_nombre": user_name,
                            "rol_nombre": rol_nombres.get(role.get("id_rol", 0), "Desconocido"),
                        })
            
            # Ordenar por proyecto y luego por usuario
            self.project_assignments = sorted(
                assignments,
                key=lambda x: (x["proyecto_nombre"], x["usuario_nombre"])
            )
            print(f"[DEBUG] Asignaciones cargadas: {len(self.project_assignments)}")
            
        except Exception as e:
            print(f"[ERROR] Error cargando asignaciones de proyectos: {e}")
            self.project_assignments = []
    
    def close_assign_user_modal(self):
        """Cierra el modal de asignación de usuario."""
        self.show_assign_user_modal = False
        self.assign_user_id = 0
        self.assign_user_name = ""
        self.assign_user_error = ""
        self.assign_user_success = ""
    
    def set_assign_project(self, value: str):
        """Establece el proyecto seleccionado para asignación.
        
        Mapea el nombre del proyecto al id correspondiente
        buscando en org_projects.
        """
        if not value:
            self.assign_selected_project_id = 0
            return
        
        # Buscar el proyecto por nombre
        for project in self.org_projects:
            if project.get("name") == value:
                self.assign_selected_project_id = project.get("id", 0)
                return
        
        self.assign_selected_project_id = 0
    
    def set_assign_rol(self, value: str):
        """Establece el rol seleccionado para asignación.
        
        Mapea el nombre del rol al id correspondiente:
        - Sin asignar = 0
        - Editor = 3
        - Lector = 4
        - Auditor = 5
        """
        rol_mapping = {"Sin asignar": 0, "Editor": 3, "Lector": 4, "Auditor": 5}
        self.assign_selected_rol_id = rol_mapping.get(value, 0)
    
    def confirm_assign_user(self):
        """Confirma la asignación del usuario al proyecto."""
        from adapters.api_client import assign_user_to_project
        
        # Debug: mostrar valores actuales
        print(f"[DEBUG] confirm_assign_user: user_id={self.assign_user_id}, project_id={self.assign_selected_project_id}, rol_id={self.assign_selected_rol_id}")
        
        # Validaciones
        if self.assign_selected_project_id <= 0:
            self.assign_user_error = "Debe seleccionar un proyecto"
            print(f"[DEBUG] Error: proyecto no seleccionado (id={self.assign_selected_project_id})")
            return
        
        if self.assign_selected_rol_id == 0:
            self.assign_user_error = "Seleccione un rol: Editor, Lector o Auditor"
            print(f"[DEBUG] Error: rol 'Sin asignar' no es válido para asignación")
            return
        
        if self.assign_selected_rol_id not in (3, 4, 5):
            self.assign_user_error = "Debe seleccionar un rol válido"
            print(f"[DEBUG] Error: rol inválido (id={self.assign_selected_rol_id})")
            return
        
        self.is_assigning_user = True
        self.assign_user_error = ""
        
        try:
            org_id = self.organization_id
            if org_id <= 0 and self.access_token:
                org_id = self._extract_org_id_from_token(self.access_token)
            
            print(f"[DEBUG] Llamando API: user={self.assign_user_id}, project={self.assign_selected_project_id}, org={org_id}, rol={self.assign_selected_rol_id}")
            
            response = assign_user_to_project(
                id_usuario=self.assign_user_id,
                id_proyecto=self.assign_selected_project_id,
                id_organizacion=org_id,
                id_rol=self.assign_selected_rol_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            print(f"[DEBUG] Respuesta API: {response}")
            
            if response.get("success"):
                rol_nombre = {3: "Editor", 4: "Lector", 5: "Auditor"}.get(
                    self.assign_selected_rol_id, "Desconocido"
                )
                self.assign_user_success = f"Usuario asignado como {rol_nombre}"
                # Recargar roles del usuario y panel de asignaciones
                self._load_user_current_roles(self.assign_user_id)
                self.load_project_assignments()
            else:
                self.assign_user_error = response.get("error", "Error al asignar usuario")
                print(f"[DEBUG] Error en respuesta: {response.get('error')}")
        except Exception as e:
            self.assign_user_error = f"Error: {e}"
            print(f"[ERROR] Error asignando usuario: {e}")
        finally:
            self.is_assigning_user = False
    
    def remove_user_from_projects(self, user_id: int):
        """Abre el modal para quitar un usuario de proyectos."""
        # Buscar nombre del usuario
        user_name = ""
        for user in self.org_users:
            if user.get("user_id") == user_id:
                user_name = user.get("user_name", "")
                break
        
        # Cargar roles actuales del usuario en proyectos
        self._load_user_current_roles(user_id)
        
        # Configurar el modal
        self.remove_user_id = user_id
        self.remove_user_name = user_name
        self.remove_selected_project_id = 0
        self.remove_user_error = ""
        self.remove_user_success = ""
        self.show_remove_user_modal = True
        print(f"[DEBUG] Abrir modal quitar usuario: {user_id} - {user_name}")
    
    def close_remove_user_modal(self):
        """Cierra el modal de quitar usuario."""
        self.show_remove_user_modal = False
        self.remove_user_id = 0
        self.remove_user_name = ""
        self.remove_user_error = ""
        self.remove_user_success = ""
    
    def set_remove_project(self, value: str):
        """Establece el proyecto seleccionado para quitar usuario.
        
        Formato del valor: "nombre_proyecto (rol)"
        Busca el proyecto en user_current_roles por nombre.
        """
        if not value:
            self.remove_selected_project_id = 0
            return
        
        # Extraer nombre del proyecto (antes del paréntesis)
        project_name = value.split(" (")[0] if " (" in value else value
        
        # Buscar en los roles del usuario
        for role in self.user_current_roles:
            if role.get("proyecto_nombre") == project_name and role.get("active", False):
                self.remove_selected_project_id = role.get("id_proyecto", 0)
                return
        
        self.remove_selected_project_id = 0
    
    def confirm_remove_user(self):
        """Confirma quitar el usuario del proyecto."""
        from adapters.api_client import remove_user_from_project
        
        # Validaciones
        if self.remove_selected_project_id <= 0:
            self.remove_user_error = "Debe seleccionar un proyecto"
            return
        
        self.is_removing_user = True
        self.remove_user_error = ""
        
        try:
            org_id = self.organization_id
            if org_id <= 0 and self.access_token:
                org_id = self._extract_org_id_from_token(self.access_token)
            
            response = remove_user_from_project(
                id_usuario=self.remove_user_id,
                id_proyecto=self.remove_selected_project_id,
                id_organizacion=org_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            if response.get("success"):
                self.remove_user_success = "Usuario quitado del proyecto"
                # Recargar roles del usuario y panel de asignaciones
                self._load_user_current_roles(self.remove_user_id)
                self.load_project_assignments()
            else:
                self.remove_user_error = response.get("error", "Error al quitar usuario")
        except Exception as e:
            self.remove_user_error = f"Error: {e}"
            print(f"[ERROR] Error quitando usuario: {e}")
        finally:
            self.is_removing_user = False
    
    def delete_user(self, user_id: int):
        """Borrado LÓGICO de un usuario (active=false).
        
        IMPORTANTE: Este NO es un borrado físico. Solo marca el usuario
        como inactivo (active=0) en la base de datos. El usuario puede
        ser reactivado posteriormente desde el backoffice.
        
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
                # Recargar lista de usuarios (excluirá los inactivos)
                self.load_org_users()
                print(f"[DEBUG] Usuario {user_id} desactivado correctamente")
            else:
                print(f"[ERROR] No se pudo desactivar usuario: {result}")
        except Exception as e:
            print(f"[ERROR] delete_user: {type(e).__name__}: {e}")

    # ========== Gestión de Proyectos de la Organización ==========
    
    def load_org_projects(self):
        """Carga los proyectos de la organización actual desde la base de datos.
        
        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
        """
        try:
            org_id = self.organization_id
            if org_id <= 0 and self.access_token:
                org_id = self._extract_org_id_from_token(self.access_token)
            
            if org_id <= 0:
                self.org_projects = []
                return
            
            # Llamar al middleware para obtener proyectos
            projects = get_organization_projects(
                organization_id=org_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            # Transformar al formato esperado por la UI
            # Nota: active=True significa desbloqueado, active=False significa bloqueado
            # Nota: existe=True significa que existe, existe=False significa borrado lógico
            self.org_projects = [
                {
                    "id": project.get("id", 0),
                    "name": project.get("nombre", project.get("name", "")),
                    "description": project.get("descripcion", ""),
                    "id_flujo": project.get("id_flujo", 1),
                    "active": project.get("active", True),
                    "existe": project.get("existe", True),
                }
                for project in projects
            ]
            print(f"[DEBUG] load_org_projects: {len(self.org_projects)} proyectos cargados")
        except Exception as e:
            print(f"[ERROR] load_org_projects: {type(e).__name__}: {e}")
            self.org_projects = []
    
    def create_project(self):
        """Abre el modal para crear un nuevo proyecto."""
        self.show_create_project_modal = True
        self.new_project_name = ""
        self.new_project_description = ""
        self.create_project_error = ""
        self.create_project_success = ""
        self.is_creating_project = False
    
    def close_create_project_modal(self):
        """Cierra el modal de creación de proyecto sin guardar."""
        self.show_create_project_modal = False
        self.new_project_name = ""
        self.new_project_description = ""
        self.create_project_error = ""
        self.create_project_success = ""
        self.is_creating_project = False
    
    def set_new_project_name(self, value: str):
        """Actualiza el nombre del nuevo proyecto."""
        self.new_project_name = value
    
    def set_new_project_description(self, value: str):
        """Actualiza la descripción del nuevo proyecto."""
        self.new_project_description = value
    
    def save_new_project(self):
        """Guarda el nuevo proyecto llamando al middleware.
        
        Campos enviados:
        - nombre: del formulario
        - descripcion: del formulario
        - id_organizacion: de la sesión
        - active: True
        - id_flujo: 1 (Propuesta Cliente)
        
        El trigger en BD crea automáticamente:
        - Registro en tabla estado (versión 1)
        - Registro en tabla cambios (tipo "Alta proyecto")
        
        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
        """
        # Validaciones básicas
        if not self.new_project_name.strip():
            self.create_project_error = "El nombre del proyecto es obligatorio"
            return
        
        self.create_project_error = ""
        self.is_creating_project = True
        
        # Obtener organization_id de la sesión
        org_id = self.organization_id
        if org_id <= 0 and self.access_token:
            org_id = self._extract_org_id_from_token(self.access_token)
        
        if org_id <= 0:
            self.create_project_error = "No se pudo determinar la organización"
            self.is_creating_project = False
            return
        
        # Llamar al API para crear el proyecto
        result = create_organization_project(
            organization_id=org_id,
            project_name=self.new_project_name.strip(),
            project_description=self.new_project_description.strip(),
            access_token=self.access_token,
            session_token=self.session_token,
        )
        
        self.is_creating_project = False
        
        if result.get("success"):
            self.create_project_success = f"Proyecto '{self.new_project_name}' creado exitosamente"
            # Limpiar campos
            self.new_project_name = ""
            self.new_project_description = ""
            # Cerrar modal
            self.show_create_project_modal = False
            # Recargar lista de proyectos
            self.load_org_projects()
        else:
            self.create_project_error = result.get("error", "Error al crear el proyecto")
    
    def lock_project(self, project_id: int):
        """Bloquea un proyecto (active=false)."""
        try:
            result = update_project_status(
                project_id=project_id,
                active=False,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                self.load_org_projects()
        except Exception as e:
            print(f"[ERROR] lock_project: {type(e).__name__}: {e}")

    def unlock_project(self, project_id: int):
        """Desbloquea un proyecto (active=true)."""
        try:
            result = update_project_status(
                project_id=project_id,
                active=True,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                self.load_org_projects()
        except Exception as e:
            print(f"[ERROR] unlock_project: {type(e).__name__}: {e}")

    def delete_project(self, project_id: int):
        """Borrado lógico de un proyecto (existe=false)."""
        try:
            result = update_project_status(
                project_id=project_id,
                existe=False,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                self.load_org_projects()
                self.load_project_assignments()
        except Exception as e:
            print(f"[ERROR] delete_project: {type(e).__name__}: {e}")
    
    def request_project_support(self, project_id: int):
        """Abre el modal para solicitar soporte para un proyecto."""
        # Buscar nombre del proyecto
        project_name = ""
        for project in self.org_projects:
            if project.get("id") == project_id:
                project_name = project.get("name", "")
                break
        
        # Configurar el modal
        self.support_project_id = project_id
        self.support_project_name = project_name
        self.support_titulo = ""
        self.support_consulta = ""
        self.support_error = ""
        self.support_success = ""
        self.is_creating_support = False
        self.show_support_modal = True
        print(f"[DEBUG] Abriendo modal de soporte para proyecto: {project_id} ({project_name})")
    
    def close_support_modal(self):
        """Cierra el modal de soporte."""
        self.show_support_modal = False
        self.support_project_id = 0
        self.support_project_name = ""
        self.support_titulo = ""
        self.support_consulta = ""
        self.support_error = ""
        self.support_success = ""
        self.is_creating_support = False
    
    def set_support_titulo(self, value: str):
        """Establece el motivo del ticket."""
        self.support_titulo = value
    
    def set_support_consulta(self, value: str):
        """Establece el texto de la consulta."""
        self.support_consulta = value
    
    async def save_support_ticket(self):
        """Envía el ticket de soporte.

        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
        """
        from adapters.api_client import create_support_ticket

        # Validaciones
        if not self.support_titulo.strip():
            self.support_error = "El motivo es obligatorio"
            return
        if not self.support_consulta.strip():
            self.support_error = "La consulta es obligatoria"
            return

        self.support_error = ""
        self.is_creating_support = True

        try:
            result = create_support_ticket(
                titulo=self.support_titulo,
                consulta=self.support_consulta,
                id_proyecto=self.support_project_id if self.support_project_id > 0 else None,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            print(f"[DEBUG] Resultado crear ticket: {result}")

            if result.get("success"):
                self.support_success = f"Ticket #{result.get('ticket_id', '')} creado correctamente"
                # Cerrar modal después de un momento
                self.support_titulo = ""
                self.support_consulta = ""
                # Cerrar modal después de mostrar éxito
                await self.close_support_modal()
            else:
                self.support_error = result.get("error", "Error al crear el ticket")
        except Exception as e:
            self.support_error = f"Error: {e}"
            print(f"[ERROR] Error creando ticket: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_creating_support = False

    # ========== Métodos de gestión de tecnologías ==========

    def load_tecnologias(self):
        """Carga la lista de tecnologías disponibles."""
        from adapters.api_client import get_tecnologias
        
        self.is_loading_tecnologias = True
        try:
            result = get_tecnologias(
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.tecnologias_list = result.get("tecnologias", [])
            print(f"[DEBUG] Tecnologías cargadas: {len(self.tecnologias_list)}")
        except Exception as e:
            print(f"[ERROR] Error cargando tecnologías: {e}")
            self.tecnologias_list = []
        finally:
            self.is_loading_tecnologias = False

    def load_tecnologias_asignadas(self):
        """Carga la lista de proyectos con sus tecnologías asignadas.
        
        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
        """
        try:
            org_id = self.organization_id
            if org_id <= 0 and self.access_token:
                org_id = self._extract_org_id_from_token(self.access_token)
            
            if org_id <= 0:
                self.tecnologias_asignadas_list = []
                return
            
            result = get_tecnologias_asignadas_org(
                org_id=org_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.tecnologias_asignadas_list = result.get("asignaciones", [])
            print(f"[DEBUG] Tecnologías asignadas cargadas: {len(self.tecnologias_asignadas_list)}")
        except Exception as e:
            print(f"[ERROR] load_tecnologias_asignadas: {type(e).__name__}: {e}")
            self.tecnologias_asignadas_list = []

    # ========== Gestión de Proyecciones (Versiones y Contenidos) ==========

    def reset_proyecciones_state(self):
        """Limpia el estado de proyecciones al cambiar de menú o proyecto."""
        self.proyecciones_project_id = 0
        self.proyecciones_project_name = ""
        self.proyecciones_versions = []
        self.proyecciones_version_id = 0
        self.proyecciones_version_folder = ""
        self.proyecciones_org_folder = ""
        self.proyecciones_prj_folder = ""
        self.proyecciones_error = ""
        self.proyecciones_success = ""

    def set_proyecciones_project(self, value: str):
        """Selecciona un proyecto y carga sus versiones.

        Args:
            value: Nombre del proyecto seleccionado
        """
        if not value:
            self.reset_proyecciones_state()
            return

        # Buscar el proyecto por nombre
        for project in self.org_projects:
            if project.get("name") == value:
                self.proyecciones_project_id = project.get("id", 0)
                self.proyecciones_project_name = value

                # Generar carpetas formateadas
                self.proyecciones_org_folder = get_folder_by_id_organization(self.organization_id)
                self.proyecciones_prj_folder = get_folder_by_id_project(self.proyecciones_project_id)

                # Cargar versiones del proyecto
                self.load_proyecciones_versions()

                # Inicializar explorador con el nuevo proyecto (mostrará todas las versiones)
                return ExploradorState.reload_project_with_tokens(
                    project_id=self.proyecciones_project_id,
                    org_id=self.organization_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                    user_id=self.user_id,
                    identity_type_id=self.identity_type_id,
                )

        self.reset_proyecciones_state()

    def load_proyecciones_versions(self):
        """Carga las versiones del proyecto seleccionado."""
        from adapters.api_client import get_project_versions
        
        if self.proyecciones_project_id <= 0:
            self.proyecciones_versions = []
            return
        
        self.is_loading_versions = True
        self.proyecciones_error = ""
        
        try:
            result = get_project_versions(
                project_id=self.proyecciones_project_id,
                organization_id=self.organization_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.proyecciones_versions = result.get("versiones", [])
            print(f"[DEBUG] Versiones cargadas: {len(self.proyecciones_versions)}")
            
            # Seleccionar la primera versión si existe
            if self.proyecciones_versions:
                first_version = self.proyecciones_versions[0]
                self.proyecciones_version_id = first_version.get("id_version", 0)
                self.proyecciones_version_folder = first_version.get("version_folder", "")
                # El explorador se auto-inicializará al detectar el cambio de version_id
        except Exception as e:
            print(f"[ERROR] Error cargando versiones: {type(e).__name__}: {e}")
            self.proyecciones_error = f"Error cargando versiones: {e}"
            self.proyecciones_versions = []
        finally:
            self.is_loading_versions = False

    def set_proyecciones_version(self, value: str):
        """Selecciona una versión e inicializa el explorador.

        Args:
            value: version_folder de la versión seleccionada (ej: "v001")
        """
        print(f"[DEBUG] set_proyecciones_version llamado con value={value}")
        print(f"[DEBUG] Versiones disponibles: {[v.get('version_folder') for v in self.proyecciones_versions]}")

        for version in self.proyecciones_versions:
            if version.get("version_folder") == value:
                self.proyecciones_version_id = version.get("id_version", 0)
                self.proyecciones_version_folder = value

                print(f"[DEBUG] Versión encontrada: id={self.proyecciones_version_id}, folder={value}")
                print(f"[DEBUG] Proyecto id={self.proyecciones_project_id}")

                # El explorador se inicializa automáticamente y muestra todas las versiones del proyecto
                # Ya no hay concepto de "versión seleccionada" - se muestran todas las versiones del proyecto

    def create_new_version(self):
        """Crea una nueva versión completa (DB + fmanagement) para el proyecto seleccionado."""
        if self.proyecciones_project_id <= 0:
            self.proyecciones_error = "Selecciona un proyecto primero"
            return
        
        self.is_loading_versions = True
        self.proyecciones_error = ""
        self.proyecciones_success = ""
        yield  # Actualizar UI
        
        try:
            # Generar nombre de versión (V001, V002, etc.)
            existing_versions = len(self.proyecciones_versions)
            version_name = f"V{existing_versions + 1:03d}"
            
            # Llamar al endpoint atómico create_version_full
            result = create_version_full(
                project_id=self.proyecciones_project_id,
                organization_id=self.organization_id,
                version_name=version_name,
                user_id=self.user_id,
                user_name=self.user_name,
                identity_type_id=self.identity_type_id,
                description=f"Versión creada automáticamente por {self.user_name}",
                clone_from_version_id=self.proyecciones_version_id if self.proyecciones_version_id > 0 else None,
                initial_state="Abierta",
                protected=False,
                final_c=False,
                final_i=False,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            print(f"[DEBUG] Resultado de create_version_full: {result}")

            if result.get("success"):
                new_version_id = result.get("version_id", 0)
                self.proyecciones_success = f"✅ Versión {version_name} creada correctamente (ID: {new_version_id})"
                # Recargar versiones
                self.load_proyecciones_versions()
                # Seleccionar automáticamente la nueva versión
                self.proyecciones_version_id = new_version_id
                self.proyecciones_version_folder = version_name

                # Inicializar explorador con el proyecto (mostrará todas las versiones)
                yield ExploradorState.init_page(
                    project_id=self.proyecciones_project_id,
                    user_id=self.user_id,
                    identity_type_id=self.identity_type_id,
                    org_id=self.organization_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
            else:
                # El backend devuelve "message", no "mensaje"
                self.proyecciones_error = result.get("message") or result.get("mensaje") or "Error al crear versión"
        except Exception as e:
            print(f"[ERROR] Error creando versión completa: {type(e).__name__}: {e}")
            self.proyecciones_error = f"Error creando versión: {e}"
        finally:
            self.is_loading_versions = False
            yield  # Actualizar UI final

    @rx.var
    def proyecciones_projects_select(self) -> list[str]:
        """Lista de nombres de proyectos para el selector."""
        return [
            project.get("name", "Sin nombre")
            for project in self.org_projects
            if project.get("name") and project.get("existe", True)
        ]

    @rx.var
    def proyecciones_versions_select(self) -> list[str]:
        """Lista de versiones formateadas para el selector."""
        return [v.get("version_folder", "") for v in self.proyecciones_versions if v.get("version_folder")]

    def set_tech_project(self, value: str):
        """Establece el proyecto seleccionado para tecnología.
        
        Mapea el nombre del proyecto al id correspondiente
        buscando en org_projects.
        """
        if not value:
            self.selected_tech_project_id = 0
            return
        
        # Buscar el proyecto por nombre
        for project in self.org_projects:
            if project.get("name") == value:
                project_id = project.get("id", 0)
                self.select_tech_project(project_id)
                return
        
        self.selected_tech_project_id = 0

    def select_tech_project(self, project_id: int):
        """Selecciona un proyecto para asignar/ver tecnología."""
        from adapters.api_client import get_proyecto_tecnologia
        
        self.selected_tech_project_id = project_id
        self.tech_assign_error = ""
        self.tech_assign_success = ""
        self.selected_tecnologia_id = 0
        
        # Cargar asignación actual del proyecto
        try:
            result = get_proyecto_tecnologia(
                project_id=project_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success") and result.get("asignacion"):
                self.proyecto_tecnologia_asignada = result["asignacion"]
                self.selected_tecnologia_id = result["asignacion"].get("id_tecnologia", 0)
            else:
                self.proyecto_tecnologia_asignada = {}
            print(f"[DEBUG] Tecnología de proyecto {project_id}: {self.proyecto_tecnologia_asignada}")
        except Exception as e:
            print(f"[ERROR] Error obteniendo tecnología de proyecto: {e}")
            self.proyecto_tecnologia_asignada = {}

    def set_tecnologia(self, tech: dict):
        """Establece la tecnología seleccionada desde el click en el item.
        
        Recibe el diccionario completo de la tecnología.
        """
        tech_id = tech.get("id", 0) if isinstance(tech, dict) else 0
        # Solo permitir seleccionar tecnologías activas
        is_active = tech.get("active", False) if isinstance(tech, dict) else False
        if is_active:
            self.selected_tecnologia_id = tech_id
            self.tech_assign_error = ""
            self.tech_assign_success = ""
            print(f"[DEBUG] Tecnología seleccionada: {tech_id}")

    def select_tecnologia(self, tecnologia_id: int):
        """Selecciona una tecnología de la lista (por ID directo)."""
        self.selected_tecnologia_id = tecnologia_id
        self.tech_assign_error = ""
        self.tech_assign_success = ""

    def asignar_tecnologia_proyecto(self):
        """Asigna la tecnología seleccionada al proyecto seleccionado."""
        from adapters.api_client import asignar_tecnologia
        
        if self.selected_tech_project_id <= 0:
            self.tech_assign_error = "Selecciona un proyecto"
            return
        if self.selected_tecnologia_id <= 0:
            self.tech_assign_error = "Selecciona una tecnología"
            return
        
        # Verificar que no esté ya asignada (Frontend solo puede asignar una vez)
        if self.proyecto_tecnologia_asignada:
            self.tech_assign_error = "Este proyecto ya tiene una tecnología asignada"
            return
        
        self.tech_assign_error = ""
        try:
            result = asignar_tecnologia(
                project_id=self.selected_tech_project_id,
                id_tecnologia=self.selected_tecnologia_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            print(f"[DEBUG] Resultado asignar tecnología: {result}")
            
            if result.get("success"):
                self.tech_assign_success = "Tecnología asignada correctamente"
                self.proyecto_tecnologia_asignada = result.get("asignacion", {})
            else:
                self.tech_assign_error = result.get("error", "Error al asignar tecnología")
        except Exception as e:
            self.tech_assign_error = f"Error: {e}"
            print(f"[ERROR] Error asignando tecnología: {e}")

    def on_page_load(self):
        """
        Ejecuta acciones al recargar la página.
        
        Si el usuario viene del backoffice con parámetros de sesión en la URL,
        restaura la sesión automáticamente.
        """
        # Leer parámetros de query (pasados desde el backoffice)
        params = self.router.page.params
        session_id = params.get("session_id", "")  # NUEVO: modo seguro
        access_token = params.get("access_token", "")  # Legacy
        session_token = params.get("session_token", "")  # Legacy
        user_id = params.get("user_id", "")
        org_id = params.get("org_id", "")

        # Debug
        print(f"[DEBUG] on_page_load: session_id={bool(session_id)}, access_token={bool(access_token)}, session_token={bool(session_token)}, user_id={user_id}")
        print(f"[DEBUG] on_page_load: is_logged_in={self.is_logged_in}, current params count={len(params)}")

        # PRIORIDAD 1: Modo seguro (solo session_id en URL, tokens desde Redis)
        # PRIORIDAD 2: Modo legacy (tokens completos en URL)
        if session_id or (access_token and session_token):
            mode = "SECURE (session_id)" if session_id else "LEGACY (tokens in URL)"
            print(f"[DEBUG] Session data found in URL ({mode}), restoring session...")
            return self.restore_session_from_url(
                access_token, session_token, user_id, org_id, session_id
            )
        
        print(f"[DEBUG] No tokens in URL, is_logged_in={self.is_logged_in}")
        
        # Si el usuario ya está logueado, inicializar según el menú activo
        if self.is_logged_in:
            # Cargar datos de organización si el menú es "organizacion"
            if self.user_active_menu == "organizacion":
                self.load_org_users()
                self.load_org_projects()
                self.load_project_assignments()
                self.load_project_roles_base()
            # Inicializar flujos si el menú es "flujos"
            elif self.user_active_menu == "flujos":
                organization_id = self.organization_id
                if organization_id <= 0 and self.access_token:
                    organization_id = self._extract_org_id_from_token(self.access_token)
                    if organization_id > 0:
                        self.organization_id = organization_id
                return FlujosState.initialize_from_session(organization_id)
    
    def restore_session_from_url(
        self, access_token: str = "", session_token: str = "", user_id: str = "", org_id: str = "", session_id: str = ""
    ):
        """
        Restaura la sesión del usuario desde los parámetros de URL.
        Se usa cuando el usuario viene del backoffice.

        NUEVO: Soporta dos modos:
        1. Modo legacy: access_token + session_token en URL (menos seguro)
        2. Modo seguro: solo session_id en URL, tokens se cargan desde Redis

        Args:
            access_token: Token JWT de acceso (opcional si viene session_id)
            session_token: Token de sesión (opcional si viene session_id)
            user_id: ID del usuario
            org_id: ID de la organización
            session_id: ID de sesión para cargar tokens desde Redis (modo seguro)

        Returns:
            None si la sesión se restauró correctamente
        """
        # MODO SEGURO: Si viene session_id, cargar tokens desde Redis
        if session_id and not access_token:
            self.session_id = session_id
            self.user_id = int(user_id) if user_id else 0
            self.organization_id = int(org_id) if org_id else 0

            # Cargar tokens desde Redis
            tokens_loaded = self._load_tokens_from_redis()

            if tokens_loaded:
                print(f"[SESSION RESTORE] Tokens cargados desde Redis para session_id={session_id}")
                access_token = self.access_token
                session_token = self.session_token
            else:
                print(f"[SESSION RESTORE] No se pudieron cargar tokens desde Redis para session_id={session_id}")
                self.login_error = "No se pudo restaurar la sesión. Por favor, inicie sesión nuevamente."
                return None

        # Validar que tenemos tokens (ya sea del modo legacy o del Redis)
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
            
            # Cargar datos de la página de organización (menú por defecto)
            self.load_org_users()
            self.load_org_projects()
            self.load_project_assignments()
            self.load_project_roles_base()

            # Iniciar loop de renovación automática de tokens en background
            return State.auto_renew_tokens_loop

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
        """Handle user portal login."""
        if not self.user_username or not self.user_password:
            self.login_error = "Debe ingresar usuario y contraseña"
            activity_log.warning(f"LOGIN ATTEMPT | incomplete credentials | user={self.user_username or 'empty'}")
            return

        # Si no hay OTP, verificar si el usuario es exempt
        if not self.user_otp:
            response = request_login_otp(self.user_username, self.user_password)
            if response.get("success") and response.get("otp_exempt"):
                self.user_otp = "0000"
            else:
                self.login_error = "Debe solicitar el código OTP primero"
                return

        activity_log.log_middleware_request("/auth/login", "POST")
        response = login_user(self.user_username, self.user_password, self.user_otp)

        # Verificar si hay un error específico del middleware
        if response.get("error"):
            error_detail = response.get("detail", "Error desconocido")
            self.login_error = error_detail
            activity_log.log_user_login(self.user_username, success=False)
            return

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
        identity_type_id = int(response.get("identity_type_id", 0))
        organization_id = int(response.get("organization_id", 0))
        
        # Extraer timestamps de expiración de tokens
        access_expires_at = int(response.get("access_expires_at", 0))
        session_expires_at = int(response.get("session_expires_at", 0))
        
        # Cargar datos en SharedSessionState con low_level_permissions
        # Estos permisos determinan funcionalidades como acceso al Backoffice
        self.load_user_data(
            user_id=user_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
            user_name=self.user_username,
            user_email=response.get("email", ""),
            user_mobile=response.get("mobile", ""),
            access_token=access_token,
            session_token=session_token,
            permissions=low_level_permissions,
            access_expires_at=access_expires_at,
            session_expires_at=session_expires_at,
        )
        
        # Asegurar que organization_id esté disponible para load_org_users
        # (load_user_data puede no propagarse inmediatamente en Reflex)
        self.organization_id = organization_id
        self.access_token = access_token
        self.session_token = session_token
        self.identity_type_id = identity_type_id
        
        # Actualizar estado local del frontend
        self.is_logged_in = True
        self.login_error = ""
        self.otp_request_message = ""
        self.user_active_menu = "organizacion"
        self.user_permissions = permissions_list  # basic_permissions para UI

        # Log de login exitoso
        activity_log.log_user_login(self.user_username, success=True, user_id=user_id)

        # Cargar datos de la página de organización (menú por defecto)
        self.load_org_users()
        self.load_org_projects()
        self.load_project_assignments()
        self.load_project_roles_base()

        # Iniciar loop de renovación automática de tokens en background
        return State.auto_renew_tokens_loop
    
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
        
        # Actualizar tokens y timestamps usando método de SharedSessionState
        self.update_tokens(
            access_token=access_token,
            session_token=session_token,
            access_expires_at=int(response.get("access_expires_at", 0)),
            session_expires_at=int(response.get("session_expires_at", 0)),
        )
    
    def _load_tokens_from_redis(self) -> bool:
        """Carga tokens desde Redis si han sido actualizados por otra aplicación.

        Returns:
            True si los tokens fueron actualizados desde Redis, False si no
        """
        # SharedSessionState ya maneja la sincronización automática con Redis
        # Este método es un placeholder para compatibilidad con el loop
        return False

    def check_token_expiration(self) -> dict[str, Any]:
        """Verifica el estado de expiración de los tokens.

        Returns:
            Dict con:
            - needs_renewal: bool - Si el access token necesita renovación (< 2 minutos)
            - session_expired: bool - Si el session token ya expiró
            - seconds_until_access_expires: int - Segundos hasta que expire el access token
            - seconds_until_session_expires: int - Segundos hasta que expire el session token
        """
        import time

        now = int(time.time())

        # Calcular segundos hasta expiración
        seconds_until_access = self.access_token_expires_at - now
        seconds_until_session = self.session_token_expires_at - now

        # Session token expiró
        session_expired = seconds_until_session <= 0

        # Access token necesita renovación si expira en menos de 2 minutos (120 segundos)
        needs_renewal = seconds_until_access < 120

        return {
            "needs_renewal": needs_renewal,
            "session_expired": session_expired,
            "seconds_until_access_expires": seconds_until_access,
            "seconds_until_session_expires": seconds_until_session,
        }

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

    @rx.event(background=True)
    async def auto_renew_tokens_loop(self):
        """
        Loop en background que verifica y renueva tokens automáticamente cada 2 minutos.

        Este método se ejecuta continuamente mientras el usuario está logueado,
        verificando si los tokens están próximos a expirar y renovándolos automáticamente.
        """
        import asyncio
        import time

        while True:
            async with self:
                # Solo ejecutar si el usuario está logueado
                if not self.is_logged_in or not self.access_token or not self.session_token:
                    break

                # PASO 1: Verificar si hay tokens más recientes en Redis (sincronización entre apps)
                tokens_updated_from_redis = self._load_tokens_from_redis()
                if tokens_updated_from_redis:
                    print("[TOKEN AUTO-RENEW] Tokens sincronizados desde Redis (renovados por otra app)")

                # PASO 2: Verificar estado de los tokens
                check_result = self.check_token_expiration()

                # Si el session_token expiró, detener el loop y forzar logout
                if check_result["session_expired"]:
                    print("[TOKEN AUTO-RENEW] Session token expirado, cerrando sesión")
                    self.login_error = "Su sesión ha expirado. Por favor, inicie sesión nuevamente."
                    self.clear_session()
                    break

                # PASO 3: Si el access_token necesita renovación, intentar renovar
                if check_result["needs_renewal"]:
                    seconds_left = check_result["seconds_until_access_expires"]
                    print(f"[TOKEN AUTO-RENEW] Access token expira en {seconds_left}s, renovando...")

                    # Llamar a ensure_tokens_valid que maneja la renovación
                    success = self.ensure_tokens_valid()

                    if success:
                        print("[TOKEN AUTO-RENEW] Tokens renovados exitosamente")
                    else:
                        # Si la renovación falla, verificar si es un error fatal
                        if self.login_error and "expirado" in self.login_error.lower():
                            # Sesión realmente expirada - detener loop
                            print("[TOKEN AUTO-RENEW] Sesión expirada, deteniendo loop")
                            self.clear_session()
                            break
                        else:
                            # Error temporal o sesión no registrada - continuar con tokens actuales
                            # El usuario podrá seguir trabajando hasta que expiren realmente
                            print("[TOKEN AUTO-RENEW] Renovación falló, continuando con tokens actuales")
                            # Limpiar error para no confundir al usuario
                            self.login_error = ""
                else:
                    seconds_left = check_result["seconds_until_access_expires"]
                    print(f"[TOKEN AUTO-RENEW] Tokens válidos (expira en {seconds_left}s)")

            # Esperar 2 minutos antes de la próxima verificación
            await asyncio.sleep(120)

    def request_login_otp(self):
        """Solicita el código OTP para el login.
        
        Flujo:
        1. Frontend → Middleware: Obtiene OTP y teléfono del usuario
        2. Frontend → Infobip API: Envía SMS directamente
        """
        if not self.user_username or not self.user_password:
            self.otp_request_message = "Debe ingresar usuario y contraseña"
            return

        # Paso 1: Obtener OTP y teléfono del middleware
        response = request_login_otp(self.user_username, self.user_password)
        
        if not response.get("success"):
            error_detail = response.get("detail", "Error al obtener datos de OTP")
            self.otp_request_message = f"Error: {error_detail}"
            return

        # Usuario exento de OTP: auto-rellenar con valor dummy
        if response.get("otp_exempt"):
            self.user_otp = "0000"
            self.otp_request_message = "Usuario exento de OTP"
            self.login_error = ""
            return

        otp = response.get("otp")
        phone_number = response.get("phone_number")

        if not otp or not phone_number:
            self.otp_request_message = "No se pudieron obtener los datos de OTP"
            return

        # Paso 2: Enviar SMS directamente a Infobip
        if _send_message_by_sms is None:
            self.otp_request_message = "Función de envío de SMS no disponible"
            return

        try:
            sms_sent = _send_message_by_sms(otp, phone_number)
            if sms_sent:
                self.otp_request_message = "Código OTP enviado por SMS"
                self.login_error = ""
            else:
                self.otp_request_message = "No se pudo enviar el SMS"
        except Exception as e:
            self.otp_request_message = f"Error al enviar SMS: {e}"
    
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
                rx.text(
                    "Solicitar código OTP",
                    on_click=State.request_login_otp,
                    color=COLORS["primary"],
                    width="100%",
                    text_align="left",
                    font_size="1.1em",
                    cursor="pointer",
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
            rx.box(
                "Iniciar Sesión",
                on_click=State.user_login,
                background_color=COLORS["primary"],
                color="black",
                width="100%",
                font_weight="bold",
                font_size="1.1em",
                padding="0.6em",
                border_radius="0.5em",
                text_align="center",
                cursor="pointer",
                _hover={"opacity": "0.9"},
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
            "informes",
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
                    lambda item: rx.box(
                        item.title(),
                        on_click=lambda _, i=item: State.set_user_menu(i),
                        background_color=rx.cond(
                            State.user_active_menu == item,
                            COLORS["primary"],
                            "transparent"
                        ),
                        color=rx.cond(
                            State.user_active_menu == item,
                            "white",
                            COLORS["foreground"]
                        ),
                        width="100%",
                        padding="0.75em",
                        border_radius="0.5em",
                        cursor="pointer",
                        text_align="left",
                        font_size="1.1em",
                        font_weight="bold",
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
            color_scheme="yellow",
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
                        color_scheme="yellow",
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
                        color_scheme="yellow",
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
                        color_scheme="yellow",
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
                        color_scheme="yellow",
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
                        color_scheme="yellow",
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
                    _hover={"background_color": "#1ea550", "cursor": "pointer"},
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
        # Modal de asignar usuario a proyecto
        assign_user_to_project_modal(),
        # Modal de quitar usuario de proyecto
        remove_user_from_project_modal(),
        rx.hstack(
            rx.icon("users", size=28, color=COLORS["primary"]),
            rx.heading("Gestión de Usuarios", size="6", color=COLORS["primary"]),
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
                _hover={"background_color": "#1ea550", "cursor": "pointer"},
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
    
    El campo 'active' determina el estado:
    - active=True: Proyecto activo (desbloqueado)
    - active=False: Proyecto bloqueado
    """
    return rx.hstack(
        # Información del proyecto a la izquierda
        rx.hstack(
            rx.text(project["name"], font_weight="bold", font_size="1.1em", color=COLORS["foreground"]),
            rx.cond(
                project["active"],  # active=True → Activo, active=False → Bloqueado
                rx.badge("Activo", color_scheme="green", variant="soft", size="3"),
                rx.badge("Bloqueado", color_scheme="red", variant="soft", size="3"),
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
                "lock-open",
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


def create_project_modal() -> rx.Component:
    """Modal para crear un nuevo proyecto de la organización.
    
    Campos del formulario:
    - nombre: Nombre del proyecto (obligatorio)
    - descripcion: Descripción del proyecto (opcional)
    
    Campos automáticos (enviados por el backend):
    - id_organizacion: de la sesión de usuario
    - created_at: fecha actual del sistema
    - active: True
    - id_flujo: 1 (Propuesta Cliente - primer paso)
    
    El trigger en BD crea automáticamente:
    - Registro en tabla estado (versión 1)
    - Registro en tabla cambios (tipo "Alta proyecto")
    """
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("folder-plus", size=24, color=COLORS["primary"]),
                    rx.text("Crear Nuevo Proyecto", font_weight="bold", font_size="1.3em"),
                    spacing="3",
                    align="center",
                ),
            ),
            rx.dialog.description(
                rx.text(
                    "Complete los datos del nuevo proyecto. Se creará con estado inicial 'Propuesta Cliente'.",
                    color=COLORS["muted_foreground"],
                    font_size="0.95em",
                ),
            ),
            rx.vstack(
                # Campo: Nombre del proyecto
                rx.vstack(
                    rx.text("Nombre del proyecto", font_weight="bold", color=COLORS["foreground"]),
                    rx.input(
                        placeholder="Ingrese el nombre del proyecto",
                        value=State.new_project_name,
                        on_change=State.set_new_project_name,
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Campo: Descripción
                rx.vstack(
                    rx.text("Descripción", font_weight="bold", color=COLORS["foreground"]),
                    rx.text_area(
                        placeholder="Descripción del proyecto (opcional)",
                        value=State.new_project_description,
                        on_change=State.set_new_project_description,
                        width="100%",
                        min_height="80px",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Info: Estado inicial
                rx.hstack(
                    rx.icon("info", size=16, color=COLORS["muted_foreground"]),
                    rx.text(
                        "El proyecto se creará en el paso 'Propuesta Cliente' del flujo de trabajo.",
                        color=COLORS["muted_foreground"],
                        font_size="0.85em",
                    ),
                    spacing="2",
                    align="center",
                ),
                # Mensaje de error
                rx.cond(
                    State.create_project_error != "",
                    rx.text(
                        State.create_project_error,
                        color="red",
                        font_size="0.9em",
                    ),
                ),
                # Mensaje de éxito
                rx.cond(
                    State.create_project_success != "",
                    rx.text(
                        State.create_project_success,
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
                    rx.text("Cancelar", color=COLORS["foreground"]),
                    on_click=State.close_create_project_modal,
                    variant="outline",
                    size="3",
                    color_scheme="gray",
                ),
                rx.button(
                    rx.cond(
                        State.is_creating_project,
                        rx.spinner(size="2"),
                        rx.icon("save", size=18, color="black"),
                    ),
                    rx.text("Guardar", font_weight="bold", color="black"),
                    on_click=State.save_new_project,
                    disabled=State.is_creating_project,
                    color_scheme="green",
                    variant="solid",
                    size="3",
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            padding="1.5em",
            max_width="500px",
        ),
        open=State.show_create_project_modal,
    )


def support_ticket_modal() -> rx.Component:
    """Modal para crear un ticket de soporte.
    
    Campos del formulario:
    - titulo: Motivo del ticket (obligatorio)
    - consulta: Texto de la consulta (obligatorio)
    
    Campos informativos (automáticos):
    - estado: "abierto"
    - prioridad: "media"
    """
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("headset", size=24, color=COLORS["primary"]),
                    rx.text("Solicitud de Soporte", font_weight="bold", font_size="1.3em"),
                    spacing="3",
                    align="center",
                ),
            ),
            rx.dialog.description(
                rx.text(
                    f"Crear ticket de soporte",
                    color=COLORS["muted_foreground"],
                    font_size="0.9em",
                ),
            ),
            # Formulario
            rx.vstack(
                # Proyecto asociado (informativo)
                rx.cond(
                    State.support_project_name != "",
                    rx.hstack(
                        rx.text("Proyecto:", font_weight="bold", color=COLORS["foreground"]),
                        rx.badge(State.support_project_name, color_scheme="blue", variant="soft"),
                        spacing="2",
                        align="center",
                    ),
                ),
                # Campo motivo
                rx.vstack(
                    rx.text("Motivo *", font_weight="bold", color=COLORS["foreground"]),
                    rx.input(
                        value=State.support_titulo,
                        on_change=State.set_support_titulo,
                        placeholder="Describe brevemente el motivo de la consulta",
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Campo consulta
                rx.vstack(
                    rx.text("Consulta *", font_weight="bold", color=COLORS["foreground"]),
                    rx.text_area(
                        value=State.support_consulta,
                        on_change=State.set_support_consulta,
                        placeholder="Describe detalladamente tu consulta o problema...",
                        width="100%",
                        min_height="120px",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Info: Estado y prioridad automáticos
                rx.hstack(
                    rx.badge("Estado: Abierto", color_scheme="green", variant="soft"),
                    rx.badge("Prioridad: Media", color_scheme="yellow", variant="soft"),
                    spacing="2",
                    align="center",
                ),
                rx.text(
                    "El equipo de soporte revisará tu consulta lo antes posible.",
                    color=COLORS["muted_foreground"],
                    font_size="0.85em",
                    font_style="italic",
                ),
                # Mensaje de error
                rx.cond(
                    State.support_error != "",
                    rx.text(
                        State.support_error,
                        color="red",
                        font_size="0.9em",
                    ),
                ),
                # Mensaje de éxito
                rx.cond(
                    State.support_success != "",
                    rx.text(
                        State.support_success,
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
                    rx.text("Cancelar", color=COLORS["foreground"]),
                    on_click=State.close_support_modal,
                    variant="outline",
                    size="3",
                    color_scheme="gray",
                ),
                rx.button(
                    rx.cond(
                        State.is_creating_support,
                        rx.spinner(size="2"),
                        rx.icon("send", size=18, color="black"),
                    ),
                    rx.text("Enviar", font_weight="bold", color="black"),
                    on_click=State.save_support_ticket,
                    disabled=State.is_creating_support,
                    color_scheme="green",
                    variant="solid",
                    size="3",
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            padding="1.5em",
            max_width="550px",
        ),
        open=State.show_support_modal,
    )


def assign_user_to_project_modal() -> rx.Component:
    """Modal para asignar un usuario a un proyecto con un rol específico.
    
    Permite:
    - Seleccionar un proyecto de la organización
    - Seleccionar un rol (Editor, Lector, Auditor)
    - Ver los roles actuales del usuario en proyectos
    """
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("user-plus", size=24, color=COLORS["primary"]),
                    rx.text("Asignar Usuario a Proyecto", font_weight="bold", font_size="1.3em"),
                    spacing="3",
                    align="center",
                ),
            ),
            rx.dialog.description(
                rx.vstack(
                    rx.text(
                        f"Usuario: ",
                        color=COLORS["muted_foreground"],
                        font_size="0.95em",
                        display="inline",
                    ),
                    rx.text(
                        State.assign_user_name,
                        color=COLORS["foreground"],
                        font_weight="bold",
                        font_size="0.95em",
                    ),
                    direction="row",
                    spacing="1",
                ),
            ),
            rx.vstack(
                # Selector de proyecto
                rx.vstack(
                    rx.text("Proyecto", font_weight="bold", color=COLORS["foreground"]),
                    rx.select(
                        State.projects_for_assign_select,
                        placeholder="Seleccione un proyecto",
                        value=State.selected_project_name,
                        on_change=State.set_assign_project,
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border_color=COLORS["border"],
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Selector de rol
                rx.vstack(
                    rx.text("Rol en el proyecto", font_weight="bold", color=COLORS["foreground"]),
                    rx.select(
                        State.roles_for_select,
                        placeholder="Seleccione un rol",
                        value=State.selected_rol_name,
                        on_change=State.set_assign_rol,
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border_color=COLORS["border"],
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Info de roles
                rx.hstack(
                    rx.icon("info", size=16, color=COLORS["muted_foreground"]),
                    rx.text(
                        "Editor: puede modificar. Lector: solo lectura. Auditor: acceso limitado.",
                        color=COLORS["muted_foreground"],
                        font_size="0.85em",
                    ),
                    spacing="2",
                    align="center",
                ),
                # Mensaje de error
                rx.cond(
                    State.assign_user_error != "",
                    rx.text(
                        State.assign_user_error,
                        color="red",
                        font_size="0.9em",
                    ),
                ),
                # Mensaje de éxito
                rx.cond(
                    State.assign_user_success != "",
                    rx.text(
                        State.assign_user_success,
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
                    rx.text("Cerrar", color=COLORS["foreground"]),
                    on_click=State.close_assign_user_modal,
                    variant="outline",
                    size="3",
                    color_scheme="gray",
                ),
                rx.button(
                    rx.cond(
                        State.is_assigning_user,
                        rx.spinner(size="2"),
                        rx.icon("save", size=18, color="black"),
                    ),
                    rx.text("Asignar", font_weight="bold", color="black"),
                    on_click=State.confirm_assign_user,
                    disabled=State.is_assigning_user,
                    color_scheme="green",
                    variant="solid",
                    size="3",
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            padding="1.5em",
            max_width="500px",
        ),
        open=State.show_assign_user_modal,
    )


def remove_user_from_project_modal() -> rx.Component:
    """Modal para quitar un usuario de un proyecto.
    
    Muestra solo los proyectos donde el usuario tiene asignación activa.
    """
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("user-minus", size=24, color="orange"),
                    rx.text("Quitar Usuario de Proyecto", font_weight="bold", font_size="1.3em"),
                    spacing="3",
                    align="center",
                ),
            ),
            rx.dialog.description(
                rx.vstack(
                    rx.text(
                        f"Usuario: ",
                        color=COLORS["muted_foreground"],
                        font_size="0.95em",
                        display="inline",
                    ),
                    rx.text(
                        State.remove_user_name,
                        color=COLORS["foreground"],
                        font_weight="bold",
                        font_size="0.95em",
                    ),
                    direction="row",
                    spacing="1",
                ),
            ),
            rx.vstack(
                # Selector de proyecto
                rx.vstack(
                    rx.text("Proyecto asignado", font_weight="bold", color=COLORS["foreground"]),
                    rx.cond(
                        State.projects_for_remove_select.length() > 0,
                        rx.select(
                            State.projects_for_remove_select,
                            placeholder="Seleccione el proyecto a quitar",
                            on_change=State.set_remove_project,
                            width="100%",
                            background_color=COLORS["input"],
                            color=COLORS["foreground"],
                            border_color=COLORS["border"],
                        ),
                        rx.text(
                            "Este usuario no tiene asignaciones activas a proyectos.",
                            color=COLORS["muted_foreground"],
                            font_style="italic",
                        ),
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Advertencia
                rx.hstack(
                    rx.icon("triangle-alert", size=16, color="orange"),
                    rx.text(
                        "El usuario perderá acceso al proyecto seleccionado.",
                        color="orange",
                        font_size="0.85em",
                    ),
                    spacing="2",
                    align="center",
                ),
                # Mensaje de error
                rx.cond(
                    State.remove_user_error != "",
                    rx.text(
                        State.remove_user_error,
                        color="red",
                        font_size="0.9em",
                    ),
                ),
                # Mensaje de éxito
                rx.cond(
                    State.remove_user_success != "",
                    rx.text(
                        State.remove_user_success,
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
                    rx.text("Cerrar", color=COLORS["foreground"]),
                    on_click=State.close_remove_user_modal,
                    variant="outline",
                    size="3",
                    color_scheme="gray",
                ),
                rx.cond(
                    State.projects_for_remove_select.length() > 0,
                    rx.button(
                        rx.cond(
                            State.is_removing_user,
                            rx.spinner(size="2"),
                            rx.icon("user-x", size=18, color="black"),
                        ),
                        rx.text("Quitar", font_weight="bold", color="black"),
                        on_click=State.confirm_remove_user,
                        disabled=State.is_removing_user,
                        color_scheme="orange",
                        variant="solid",
                        size="3",
                    ),
                    rx.fragment(),
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            padding="1.5em",
            max_width="500px",
        ),
        open=State.show_remove_user_modal,
    )


def projects_management_panel() -> rx.Component:
    """Panel de gestión de proyectos de la organización."""
    return rx.vstack(
        # Modal de creación de proyecto
        create_project_modal(),
        # Modal de solicitud de soporte
        support_ticket_modal(),
        rx.hstack(
            rx.icon("folder-kanban", size=28, color=COLORS["primary"]),
            rx.heading("Gestión de Proyectos", size="6", color=COLORS["primary"]),
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
                color_scheme="green",
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


def project_assignment_row(assignment: dict) -> rx.Component:
    """Fila de asignación de proyecto (solo lectura).
    
    Muestra: Proyecto | Usuario | Rol
    """
    return rx.hstack(
        # Proyecto
        rx.hstack(
            rx.icon("folder", size=18, color=COLORS["primary"]),
            rx.text(
                assignment["proyecto_nombre"],
                font_weight="bold",
                color=COLORS["foreground"],
                font_size="1em",
            ),
            spacing="2",
            align="center",
            width="35%",
        ),
        # Usuario
        rx.hstack(
            rx.icon("user", size=18, color=COLORS["muted_foreground"]),
            rx.text(
                assignment["usuario_nombre"],
                color=COLORS["foreground"],
                font_size="0.95em",
            ),
            spacing="2",
            align="center",
            width="35%",
        ),
        # Rol
        rx.badge(
            assignment["rol_nombre"],
            color_scheme=rx.cond(
                assignment["rol_nombre"] == "Editor",
                "blue",
                rx.cond(
                    assignment["rol_nombre"] == "Lector",
                    "green",
                    "orange",  # Auditor
                ),
            ),
            size="2",
        ),
        width="100%",
        padding="0.75em 1em",
        background_color=COLORS["input"],
        border_radius="0.5em",
        justify="between",
        align="center",
    )


def project_assignments_panel() -> rx.Component:
    """Panel de asignaciones de usuarios a proyectos (solo lectura).
    
    Muestra todas las asignaciones activas de la organización.
    Se refresca automáticamente cuando se asigna o quita un usuario.
    """
    return rx.vstack(
        rx.hstack(
            rx.icon("users-round", size=28, color=COLORS["primary"]),
            rx.heading("Asignaciones de Proyectos", size="6", color=COLORS["primary"]),
            spacing="3",
            align="center",
        ),
        rx.text(
            "Vista de solo lectura - Se actualiza al asignar o quitar usuarios",
            color=COLORS["muted_foreground"],
            font_size="0.85em",
            font_style="italic",
        ),
        rx.cond(
            State.project_assignments.length() > 0,
            rx.vstack(
                # Encabezado de columnas
                rx.hstack(
                    rx.text("Proyecto", font_weight="bold", color=COLORS["muted_foreground"], width="35%"),
                    rx.text("Usuario", font_weight="bold", color=COLORS["muted_foreground"], width="35%"),
                    rx.text("Rol", font_weight="bold", color=COLORS["muted_foreground"]),
                    width="100%",
                    padding="0.5em 1em",
                ),
                rx.foreach(
                    State.project_assignments,
                    project_assignment_row,
                ),
                width="100%",
                spacing="2",
            ),
            rx.text(
                "No hay asignaciones de usuarios a proyectos",
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


def tecnologia_item(tech: dict) -> rx.Component:
    """Renderiza un item de tecnología seleccionable."""
    is_active = tech.get("active", False)
    tech_id = tech.get("id", 0)
    is_selected = State.selected_tecnologia_id == tech_id
    
    return rx.box(
        rx.hstack(
            # Indicador de selección (círculo verde)
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
                    tech.get("name", "Sin nombre"),
                    font_weight="bold",
                    color=rx.cond(is_active, COLORS["foreground"], COLORS["muted_foreground"]),
                    font_size="1.25em",
                ),
                rx.text(
                    tech.get("descripcion", ""),
                    color=COLORS["muted_foreground"],
                    font_size="1.05em",
                    opacity=rx.cond(is_active, "1", "0.6"),
                ),
                spacing="2",
                align_items="flex-start",
                flex="1",
            ),
            rx.cond(
                ~is_active,
                rx.badge("Inactiva", color_scheme="gray", variant="soft", size="2"),
                rx.fragment(),
            ),
            spacing="4",
            align="center",
            width="100%",
        ),
        padding="1.25em",
        background_color=rx.cond(
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
        on_click=State.set_tecnologia(tech),
        _hover=rx.cond(
            is_active,
            {"background_color": f"{COLORS['primary']}15"},
            {},
        ),
        width="100%",
    )


def tecnologias_management_panel() -> rx.Component:
    """Panel de gestión de tecnologías por proyecto."""
    return rx.vstack(
        rx.hstack(
            rx.icon("cpu", size=36, color=COLORS["primary"]),
            rx.heading("Asignación de Tecnología", size="7", color=COLORS["primary"]),
            spacing="4",
            align="center",
        ),
        rx.text(
            "Selecciona un proyecto y asígnale una tecnología",
            color=COLORS["muted_foreground"],
            font_size="1.1em",
        ),
        # Selector de proyectos
        rx.hstack(
            rx.text("Proyecto:", font_weight="bold", color=COLORS["foreground"], font_size="1.1em"),
            rx.select(
                State.projects_for_assign_select,
                placeholder="Seleccionar proyecto...",
                on_change=State.set_tech_project,
                width="350px",
                size="3",
                background_color=COLORS["input"],
                color=COLORS["foreground"],
                border_color=COLORS["border"],
            ),
            spacing="4",
            align="center",
        ),
        # Indicador de tecnología ya asignada
        rx.cond(
            State.proyecto_tecnologia_asignada.length() > 0,
            rx.box(
                rx.hstack(
                    rx.icon("circle-check", size=28, color=COLORS["primary"]),
                    rx.text(
                        f"Tecnología asignada: ",
                        font_weight="bold",
                        color=COLORS["foreground"],
                        font_size="1.15em",
                    ),
                    rx.text(
                        State.proyecto_tecnologia_asignada.get("tecnologia_name", ""),
                        color=COLORS["primary"],
                        font_weight="bold",
                        font_size="1.15em",
                    ),
                    spacing="3",
                ),
                padding="1.25em",
                background_color=f"{COLORS['primary']}20",
                border=f"2px solid {COLORS['primary']}",
                border_radius="0.75em",
                width="100%",
            ),
            rx.fragment(),
        ),
        # Lista de tecnologías (solo si no hay asignación o si se seleccionó proyecto)
        rx.cond(
            (State.selected_tech_project_id > 0) & (State.proyecto_tecnologia_asignada.length() == 0),
            rx.vstack(
                rx.text(
                    "Selecciona una tecnología:",
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
                    spacing="2",
                ),
                rx.cond(
                    State.tech_assign_error != "",
                    rx.text(State.tech_assign_error, color="red", font_size="0.9em"),
                ),
                rx.cond(
                    State.tech_assign_success != "",
                    rx.text(State.tech_assign_success, color="green", font_size="0.9em"),
                ),
                rx.button(
                    "Asignar Tecnología",
                    on_click=State.asignar_tecnologia_proyecto,
                    color_scheme="blue",
                    disabled=(State.selected_tecnologia_id <= 0),
                    margin_top="1em",
                ),
                width="100%",
                spacing="2",
            ),
            rx.fragment(),
        ),
        width="100%",
        padding="1.5em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
        spacing="3",
        align_items="flex-start",
    )


def tecnologia_asignada_row(item: dict) -> rx.Component:
    """Fila que muestra un proyecto y su tecnología asignada."""
    return rx.hstack(
        rx.text(
            item["project_name"],
            font_weight="medium",
            color=COLORS["foreground"],
            font_size="1em",
            flex="1",
        ),
        rx.cond(
            item["tecnologia_name"],
            rx.badge(
                item["tecnologia_name"],
                color_scheme="green",
                variant="soft",
                size="2",
            ),
            rx.badge(
                "(sin asignar)",
                color_scheme="gray",
                variant="soft",
                size="2",
            ),
        ),
        width="100%",
        padding="0.75em 1em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
        justify="between",
        align="center",
    )


def tecnologias_asignadas_panel() -> rx.Component:
    """Panel informativo que muestra proyectos con sus tecnologías asignadas."""
    return rx.vstack(
        rx.hstack(
            rx.icon("list", size=28, color=COLORS["primary"]),
            rx.heading(
                "Tecnologías asignadas a proyecto",
                size="6",
                color=COLORS["primary"],
            ),
            spacing="3",
            align="center",
        ),
        rx.cond(
            State.tecnologias_asignadas_list.length() > 0,
            rx.vstack(
                rx.foreach(
                    State.tecnologias_asignadas_list,
                    tecnologia_asignada_row,
                ),
                width="100%",
                spacing="2",
            ),
            rx.text(
                "No hay proyectos en la organización",
                color=COLORS["muted_foreground"],
                font_size="0.95em",
            ),
        ),
        width="100%",
        padding="1.5em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
        spacing="3",
        align_items="flex-start",
        margin_top="1em",
    )


def proyecciones_management_panel() -> rx.Component:
    """Panel de gestión de versiones de proyecto (3 capas)."""
    return rx.vstack(
        # ===== CAPA 1: Selector de proyecto =====
        rx.vstack(
            rx.hstack(
                rx.icon("folder-git-2", size=36, color=COLORS["primary"]),
                rx.heading("Gestión de Versiones", size="7", color=COLORS["primary"]),
                spacing="4",
                align="center",
            ),
            rx.text(
                "Administra las versiones de los proyectos y sus contenidos",
                color=COLORS["muted_foreground"],
                font_size="1.1em",
            ),
            rx.hstack(
                rx.text("Proyecto:", font_weight="bold", color=COLORS["foreground"], font_size="1.1em"),
                rx.select(
                    State.proyecciones_projects_select,
                    placeholder="Seleccionar proyecto...",
                    value=State.proyecciones_project_name,
                    on_change=State.set_proyecciones_project,
                    width="350px",
                    size="3",
                    background_color=COLORS["input"],
                    color=COLORS["foreground"],
                    border_color=COLORS["border"],
                ),
                spacing="4",
                align="center",
            ),
            width="100%",
            spacing="3",
            padding="1.5em",
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            border_radius="0.5em",
        ),
        # ===== CAPA 2: Botón crear nueva versión =====
        rx.cond(
            State.proyecciones_project_id > 0,
            rx.vstack(
                rx.hstack(
                    rx.icon("git-branch", size=28, color=COLORS["primary"]),
                    rx.heading("Gestión de Versiones", size="6", color=COLORS["primary"]),
                    rx.spacer(),
                    rx.button(
                        rx.icon("plus", size=18),
                        "Crear nueva versión",
                        on_click=State.create_new_version,
                        color_scheme="green",
                        size="3",
                        disabled=State.is_loading_versions,
                        style={"font_weight": "bold", "color": "black"},
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                rx.cond(
                    State.proyecciones_error != "",
                    rx.text(State.proyecciones_error, color="red", font_size="0.95em"),
                ),
                rx.cond(
                    State.proyecciones_success != "",
                    rx.text(State.proyecciones_success, color="green", font_size="0.95em"),
                ),
                width="100%",
                spacing="3",
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
            ),
            rx.fragment(),
        ),
        # ===== CAPA 3: Explorador de archivos (INTEGRADO) =====
        # Muestra todas las versiones del proyecto seleccionado
        rx.cond(
            State.proyecciones_project_id > 0,
            rx.vstack(
                explorador_panel(
                    ExploradorState,
                ),
                width="100%",
                spacing="3",
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="4",
    )


def organization_management_panels() -> rx.Component:
    """Paneles de gestión de usuarios y proyectos para la sección Organización."""
    return rx.vstack(
        users_management_panel(),
        projects_management_panel(),
        project_assignments_panel(),
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
    technologies_text = load_tecnologias_content()
    projections_text = load_proyecciones_content()
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
            ("informes", "Informes"),
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
            ("seguimiento", ""),  # Sin contenido markdown para seguimiento
            ("informes", ""),  # Sin contenido markdown para informes
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
        # No mostrar heading para informes (lo incluye el propio componente)
        rx.cond(
            active_item != "informes",
            rx.heading(heading_text, size="8", color=COLORS["accent"], margin_bottom="0.5em"),
            rx.box(height="0"),
        ),
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
        # EXCEPTO para "informes" y "proyecciones" que tienen su propia estructura
        rx.cond(
            rx.cond(content_text != "", active_item != "proyecciones", False),
            rx.markdown(
                content_text,
                component_map={
                    "h1": lambda text: rx.heading(text, size="7", color=COLORS["primary"], margin_bottom="0.5em"),
                    "h2": lambda text: rx.heading(text, size="6", color=COLORS["primary"], margin_top="1em", margin_bottom="0.5em"),
                    "h3": lambda text: rx.heading(text, size="5", color=COLORS["primary"], margin_top="0.8em", margin_bottom="0.4em"),
                    "p": lambda text: rx.text(text, color=COLORS["muted_foreground"], font_size="1.3em", line_height="1.6", margin_bottom="0.6em"),
                    "li": lambda text: rx.list_item(rx.text(text, color=COLORS["muted_foreground"], font_size="1.3em", line_height="1.5")),
                    "strong": lambda text: rx.text(text, font_weight="bold", color=COLORS["foreground"], as_="span"),
                    "em": lambda text: rx.text(text, font_style="italic", as_="span"),
                    "blockquote": lambda text: rx.box(
                        rx.text(text, color=COLORS["primary"], font_style="italic", font_size="1.35em"),
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
                        rx.text(text, font_weight="bold", color=COLORS["foreground"], font_size="1.25em"),
                    ),
                    "td": lambda text: rx.table.cell(
                        rx.text(text, color=COLORS["muted_foreground"], font_size="1.2em"),
                    ),
                },
            ),
            rx.box(height="0"),
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
            rx.vstack(
                tecnologias_management_panel(),
                tecnologias_asignadas_panel(),
                width="100%",
                spacing="4",
            ),
            rx.box(height="0"),
        ),
        # Panel de gestión de proyecciones: visible solo en menú "proyecciones"
        # Orden: 1) Panel de gestión, 2) Visor markdown
        rx.cond(
            rx.cond(is_logged_in, active_item == "proyecciones", False),
            rx.vstack(
                # 1. Panel de gestión de versiones (primero)
                proyecciones_management_panel(),
                # 2. Visor de contenido markdown (después)
                rx.markdown(
                    projections_text,
                    component_map={
                        "h1": lambda text: rx.heading(text, size="7", color=COLORS["primary"], margin_bottom="0.5em"),
                        "h2": lambda text: rx.heading(text, size="6", color=COLORS["primary"], margin_top="1em", margin_bottom="0.5em"),
                        "h3": lambda text: rx.heading(text, size="5", color=COLORS["primary"], margin_top="0.8em", margin_bottom="0.4em"),
                        "p": lambda text: rx.text(text, color=COLORS["muted_foreground"], font_size="1.3em", line_height="1.6", margin_bottom="0.6em"),
                        "li": lambda text: rx.list_item(rx.text(text, color=COLORS["muted_foreground"], font_size="1.3em", line_height="1.5")),
                        "strong": lambda text: rx.text(text, font_weight="bold", color=COLORS["foreground"], as_="span"),
                        "em": lambda text: rx.text(text, font_style="italic", as_="span"),
                        "blockquote": lambda text: rx.box(
                            rx.text(text, color=COLORS["primary"], font_style="italic", font_size="1.35em"),
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
                            rx.text(text, font_weight="bold", color=COLORS["foreground"], font_size="1.25em"),
                        ),
                        "td": lambda text: rx.table.cell(
                            rx.text(text, color=COLORS["muted_foreground"], font_size="1.2em"),
                        ),
                    },
                ),
                width="100%",
                spacing="4",
            ),
            rx.box(height="0"),
        ),
        # Panel de seguimiento: visible solo en menú "seguimiento"
        rx.cond(
            rx.cond(is_logged_in, active_item == "seguimiento", False),
            seguimiento_panel(),
            rx.box(height="0"),
        ),
        # Panel de informes: visible solo en menú "informes"
        rx.cond(
            rx.cond(is_logged_in, active_item == "informes", False),
            informes_panel(),
            rx.box(height="0"),
        ),
        # Panel de descargas: visible solo en menú "descargas"
        rx.cond(
            rx.cond(is_logged_in, active_item == "descargas", False),
            model_downloads_panel(),
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
        spacing=rx.cond(active_item == "seguimiento", "1", "4"),
        padding=rx.cond(active_item == "seguimiento", "0.5em 2em", "2em"),
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
                        "black",
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
                rx.heading("Resumen General", size="6", color=COLORS["primary"]),
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
                rx.heading("Proyectos", size="6", color=COLORS["primary"]),
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
                rx.heading("Tareas", size="6", color=COLORS["primary"]),
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
                rx.heading("Reportes", size="6", color=COLORS["primary"]),
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
                rx.heading("Documentos", size="6", color=COLORS["primary"]),
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
                rx.heading("Configuración", size="6", color=COLORS["primary"]),
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
        padding="0",
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
            rx.hstack(
                # Versión en la esquina inferior izquierda
                rx.text(
                    f"Version: {APP_VERSION}",
                    color=COLORS["muted_foreground"],
                    font_size="1.1em",
                ),
                rx.spacer(),
                # Copyright en el centro
                rx.text(
                    "© 2025 Myllm. Todos los derechos reservados.",
                    color=COLORS["muted_foreground"],
                    font_size="1.25em",
                ),
                rx.spacer(),
                width="100%",
                align_items="center",
            ),
            width="100%",
            padding="1em",
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
                        color="black",
                        font_weight="bold",
                        font_size="1.1em",
                        _hover={"background_color": "#FF7000"},
                    ),
                ),
                rx.button(
                    "Desconectar",
                    on_click=State.user_logout,
                    background_color=COLORS["primary"],
                    color="black",
                    font_weight="bold",
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
    theme=rx.theme(
        appearance="dark",
        accent_color="green",
    ),
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

try:
    from pages.model_downloads import model_downloads_page
    app.add_page(model_downloads_page, route="/model_downloads", title="Myllm - Descargas de Modelos")
    print("✅ Ruta /model_downloads registrada exitosamente")
except ImportError as e:
    print(f"⚠️ Warning: Could not import model_downloads_page: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error al registrar ruta /model_downloads: {e}")
    import traceback
    traceback.print_exc()

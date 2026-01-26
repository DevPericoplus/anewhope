"""
Estado compartido de sesión entre Frontend y Backoffice mediante Redis.

Este módulo contiene la clase SharedSessionState que se comparte automáticamente
entre las aplicaciones web_frontend (puerto 8005) y web_backoffice (puerto 8006)
mediante Redis. Cualquier cambio en el estado en una app se refleja inmediatamente
en la otra.

Arquitectura:
- Ambas apps usan la misma Redis DB (db: 0)
- El state se identifica por session_token único
- Login solo se hace en frontend
- Logout en cualquier app invalida la sesión en ambas
- Navegación entre apps preserva el estado completo
"""
import reflex as rx
from datetime import datetime
from typing import Optional


class SharedSessionState(rx.State):
    """
    Estado de sesión compartido entre frontend y backoffice.
    
    Todos los campos se sincronizan automáticamente vía Redis.
    Cualquier modificación en una app se refleja en la otra.
    """
    
    # ==================== INFORMACIÓN DEL USUARIO ====================
    user_id: int = 0
    organization_id: int = 0
    identity_type_id: int = 0
    user_name: str = ""
    user_email: str = ""
    user_mobile: str = ""
    is_logged_in: bool = False
    is_active: bool = False
    is_blocked: bool = False
    
    # ==================== TOKENS JWT ====================
    access_token: str = ""
    session_token: str = ""
    
    # ==================== PERMISOS DE BAJO NIVEL ====================
    # Gestión de datos
    can_data_read: bool = False
    can_data_write: bool = False
    can_data_delete: bool = False
    
    # Gestión de carpetas
    can_folder_create: bool = False
    can_folder_rename: bool = False
    can_folder_delete: bool = False
    can_folder_move: bool = False
    can_folder_list: bool = False
    
    # Gestión de ficheros
    can_file_upload: bool = False
    can_file_download: bool = False
    can_file_delete: bool = False
    can_file_rename: bool = False
    can_file_move: bool = False
    can_file_read: bool = False
    
    # Gestión de entrenamiento
    can_training_create: bool = False
    can_training_execute: bool = False
    can_training_monitor: bool = False
    can_training_stop: bool = False
    can_training_delete: bool = False
    
    # Gestión de modelos
    can_model_create: bool = False
    can_model_read: bool = False
    can_model_update: bool = False
    can_model_delete: bool = False
    can_model_publish: bool = False
    can_model_download: bool = False
    
    # Gestión de datasets
    can_dataset_create: bool = False
    can_dataset_read: bool = False
    can_dataset_update: bool = False
    can_dataset_delete: bool = False
    can_dataset_validate: bool = False
    
    # Gestión de usuarios
    can_user_create: bool = False
    can_user_read: bool = False
    can_user_update: bool = False
    can_user_delete: bool = False
    can_user_activate: bool = False
    can_user_deactivate: bool = False
    
    # Gestión de roles
    can_role_assign: bool = False
    can_role_revoke: bool = False
    can_role_create: bool = False
    can_role_delete: bool = False
    
    # Gestión de organización
    can_org_create: bool = False
    can_org_read: bool = False
    can_org_update: bool = False
    can_org_delete: bool = False
    
    # ==================== METADATA DE SESIÓN ====================
    session_id: str = ""
    login_time: str = ""
    last_activity: str = ""
    current_app: str = "frontend"  # "frontend" o "backoffice"
    
    # ==================== MÉTODOS DE GESTIÓN ====================
    
    def load_user_data(
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
        Carga los datos del usuario y sus permisos en el estado compartido.
        
        Este método debe ser llamado después del login exitoso en el frontend.
        Los datos se propagan automáticamente al backoffice vía Redis.
        
        Args:
            user_id: ID del usuario
            organization_id: ID de la organización
            identity_type_id: ID del tipo de identidad (rol)
            user_name: Nombre del usuario
            user_email: Email del usuario
            user_mobile: Teléfono del usuario
            access_token: Token JWT de acceso
            session_token: Token JWT de sesión
            permissions: Diccionario con todos los permisos de bajo nivel
        """
        # Información del usuario
        self.user_id = user_id
        self.organization_id = organization_id
        self.identity_type_id = identity_type_id
        self.user_name = user_name
        self.user_email = user_email
        self.user_mobile = user_mobile
        self.is_logged_in = True
        self.is_active = True
        self.is_blocked = False
        
        # Tokens
        self.access_token = access_token
        self.session_token = session_token
        
        # Cargar permisos
        self._load_permissions(permissions)
        
        # Metadata
        self.session_id = session_token
        self.login_time = datetime.now().isoformat()
        self.last_activity = datetime.now().isoformat()
        self.current_app = "frontend"
    
    def _load_permissions(self, permissions: dict):
        """
        Carga los permisos de bajo nivel desde el diccionario.
        
        Args:
            permissions: Diccionario con estructura de low_level_permissions
        """
        # Gestión de datos
        self.can_data_read = permissions.get("data_read", False)
        self.can_data_write = permissions.get("data_write", False)
        self.can_data_delete = permissions.get("data_delete", False)
        
        # Gestión de carpetas
        self.can_folder_create = permissions.get("folder_create", False)
        self.can_folder_rename = permissions.get("folder_rename", False)
        self.can_folder_delete = permissions.get("folder_delete", False)
        self.can_folder_move = permissions.get("folder_move", False)
        self.can_folder_list = permissions.get("folder_list", False)
        
        # Gestión de ficheros
        self.can_file_upload = permissions.get("file_upload", False)
        self.can_file_download = permissions.get("file_download", False)
        self.can_file_delete = permissions.get("file_delete", False)
        self.can_file_rename = permissions.get("file_rename", False)
        self.can_file_move = permissions.get("file_move", False)
        self.can_file_read = permissions.get("file_read", False)
        
        # Gestión de entrenamiento
        self.can_training_create = permissions.get("training_create", False)
        self.can_training_execute = permissions.get("training_execute", False)
        self.can_training_monitor = permissions.get("training_monitor", False)
        self.can_training_stop = permissions.get("training_stop", False)
        self.can_training_delete = permissions.get("training_delete", False)
        
        # Gestión de modelos
        self.can_model_create = permissions.get("model_create", False)
        self.can_model_read = permissions.get("model_read", False)
        self.can_model_update = permissions.get("model_update", False)
        self.can_model_delete = permissions.get("model_delete", False)
        self.can_model_publish = permissions.get("model_publish", False)
        self.can_model_download = permissions.get("model_download", False)
        
        # Gestión de datasets
        self.can_dataset_create = permissions.get("dataset_create", False)
        self.can_dataset_read = permissions.get("dataset_read", False)
        self.can_dataset_update = permissions.get("dataset_update", False)
        self.can_dataset_delete = permissions.get("dataset_delete", False)
        self.can_dataset_validate = permissions.get("dataset_validate", False)
        
        # Gestión de usuarios
        self.can_user_create = permissions.get("user_create", False)
        self.can_user_read = permissions.get("user_read", False)
        self.can_user_update = permissions.get("user_update", False)
        self.can_user_delete = permissions.get("user_delete", False)
        self.can_user_activate = permissions.get("user_activate", False)
        self.can_user_deactivate = permissions.get("user_deactivate", False)
        
        # Gestión de roles
        self.can_role_assign = permissions.get("role_assign", False)
        self.can_role_revoke = permissions.get("role_revoke", False)
        self.can_role_create = permissions.get("role_create", False)
        self.can_role_delete = permissions.get("role_delete", False)
        
        # Gestión de organización
        self.can_org_create = permissions.get("org_create", False)
        self.can_org_read = permissions.get("org_read", False)
        self.can_org_update = permissions.get("org_update", False)
        self.can_org_delete = permissions.get("org_delete", False)
    
    def clear_session(self):
        """
        Limpia todos los datos de sesión.
        
        Este método debe ser llamado en el logout.
        La limpieza se propaga automáticamente a ambas apps vía Redis.
        """
        # Información del usuario
        self.user_id = 0
        self.organization_id = 0
        self.identity_type_id = 0
        self.user_name = ""
        self.user_email = ""
        self.user_mobile = ""
        self.is_logged_in = False
        self.is_active = False
        self.is_blocked = False
        
        # Tokens
        self.access_token = ""
        self.session_token = ""
        
        # Resetear permisos
        self._reset_permissions()
        
        # Metadata
        self.session_id = ""
        self.login_time = ""
        self.last_activity = ""
        self.current_app = "frontend"
    
    def _reset_permissions(self):
        """Resetea todos los permisos a False."""
        # Gestión de datos
        self.can_data_read = False
        self.can_data_write = False
        self.can_data_delete = False
        
        # Gestión de carpetas
        self.can_folder_create = False
        self.can_folder_rename = False
        self.can_folder_delete = False
        self.can_folder_move = False
        self.can_folder_list = False
        
        # Gestión de ficheros
        self.can_file_upload = False
        self.can_file_download = False
        self.can_file_delete = False
        self.can_file_rename = False
        self.can_file_move = False
        self.can_file_read = False
        
        # Gestión de entrenamiento
        self.can_training_create = False
        self.can_training_execute = False
        self.can_training_monitor = False
        self.can_training_stop = False
        self.can_training_delete = False
        
        # Gestión de modelos
        self.can_model_create = False
        self.can_model_read = False
        self.can_model_update = False
        self.can_model_delete = False
        self.can_model_publish = False
        self.can_model_download = False
        
        # Gestión de datasets
        self.can_dataset_create = False
        self.can_dataset_read = False
        self.can_dataset_update = False
        self.can_dataset_delete = False
        self.can_dataset_validate = False
        
        # Gestión de usuarios
        self.can_user_create = False
        self.can_user_read = False
        self.can_user_update = False
        self.can_user_delete = False
        self.can_user_activate = False
        self.can_user_deactivate = False
        
        # Gestión de roles
        self.can_role_assign = False
        self.can_role_revoke = False
        self.can_role_create = False
        self.can_role_delete = False
        
        # Gestión de organización
        self.can_org_create = False
        self.can_org_read = False
        self.can_org_update = False
        self.can_org_delete = False
    
    def go_to_backoffice(self):
        """
        Marca que el usuario está navegando al backoffice.
        Actualiza current_app y last_activity.
        Pasa los tokens como parámetros para sincronizar la sesión.
        """
        self.current_app = "backoffice"
        self.last_activity = datetime.now().isoformat()
        # Pasar tokens en la URL para que el backoffice pueda cargar la sesión
        import urllib.parse
        params = urllib.parse.urlencode({
            "access_token": self.access_token,
            "session_token": self.session_token,
            "user_id": str(self.user_id),
            "org_id": str(self.organization_id),
        })
        return rx.redirect(f"https://tfmmyllm.ai:8443?{params}")
    
    def go_to_frontend(self):
        """
        Marca que el usuario está regresando al frontend.
        Actualiza current_app y last_activity.
        """
        self.current_app = "frontend"
        self.last_activity = datetime.now().isoformat()
        # La redirección real se maneja en el componente UI
        return rx.redirect("https://tfmmyllm.ai")
    
    def logout(self):
        """
        Cierra la sesión del usuario en ambas aplicaciones.
        Limpia el estado y redirige al frontend público.
        """
        self.clear_session()
        # Aquí deberíamos invalidar la sesión en el middleware
        # Por ahora solo limpiamos el estado local
        return rx.redirect("https://tfmmyllm.ai")
    
    @rx.var
    def can_access_backoffice(self) -> bool:
        """
        Determina si el usuario puede acceder al backoffice.
        
        Requisito: Tener permiso training_create = True
        
        Returns:
            True si el usuario puede acceder al backoffice, False en caso contrario
        """
        return self.is_logged_in and self.can_training_create
    
    @property
    def user_display_name(self) -> str:
        """
        Nombre de usuario para mostrar en la UI.
        
        Returns:
            Nombre del usuario o string vacío si no está logueado
        """
        return self.user_name if self.is_logged_in else ""
    
    @rx.var
    def user_display_email(self) -> str:
        """
        Email del usuario para mostrar en la UI.
        
        Returns:
            Email del usuario o string vacío si no está logueado
        """
        return self.user_email if self.is_logged_in else ""
    
    def update_activity(self):
        """
        Actualiza el timestamp de última actividad.
        Debe ser llamado en cada interacción significativa del usuario.
        """
        self.last_activity = datetime.now().isoformat()

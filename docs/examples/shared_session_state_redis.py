"""
State compartido entre Frontend y Backoffice usando Redis

Este state se almacena en Redis con la estructura:
  Key: reflex:session:{session_token}
  Value: JSON con todos los campos del state
  TTL: redis_token_expiration (3600 segundos = 1 hora)

Ambas aplicaciones (frontend y backoffice) comparten este state
automáticamente a través de Redis.
"""
from __future__ import annotations

import reflex as rx
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SharedSessionState(rx.State):
    """
    State compartido entre frontend y backoffice vía Redis
    
    Cuando el usuario se loga en frontend, este state se crea en Redis.
    Cuando navega a backoffice, Reflex automáticamente recupera el mismo state.
    """
    
    # ============================================================================
    # Información de usuario (compartida entre ambas apps)
    # ============================================================================
    
    user_id: int = 0
    organization_id: int = 0
    identity_type_id: int = 0
    
    user_name: str = ""
    user_email: str = ""
    user_mobile: str = ""
    
    is_logged_in: bool = False
    is_active: bool = False
    is_blocked: bool = False
    
    # ============================================================================
    # Tokens JWT (compartidos)
    # ============================================================================
    
    access_token: str = ""
    refresh_token: str = ""
    session_id: str = ""
    
    # ============================================================================
    # Permisos de bajo nivel (compartidos)
    # ============================================================================
    
    # Permisos de usuarios
    can_user_create: bool = False
    can_user_read: bool = False
    can_user_update: bool = False
    can_user_delete: bool = False
    
    # Permisos de organizaciones
    can_org_create: bool = False
    can_org_read: bool = False
    can_org_update: bool = False
    can_org_delete: bool = False
    
    # Permisos de proyectos
    can_project_create: bool = False
    can_project_read: bool = False
    can_project_update: bool = False
    can_project_delete: bool = False
    
    # Permisos de versiones
    can_version_create: bool = False
    can_version_read: bool = False
    can_version_update: bool = False
    can_version_delete: bool = False
    
    # Permisos de datasets
    can_dataset_create: bool = False
    can_dataset_read: bool = False
    can_dataset_update: bool = False
    can_dataset_delete: bool = False
    
    # Permisos de modelos
    can_model_create: bool = False
    can_model_read: bool = False
    can_model_update: bool = False
    can_model_delete: bool = False
    
    # Permisos de entrenamiento (CRÍTICO para acceso a backoffice)
    can_training_create: bool = False
    can_training_read: bool = False
    can_training_update: bool = False
    can_training_delete: bool = False
    
    # Permisos de carpetas
    can_folder_create: bool = False
    can_folder_read: bool = False
    can_folder_update: bool = False
    can_folder_delete: bool = False
    can_folder_rename: bool = False
    can_folder_move: bool = False
    can_folder_copy: bool = False
    can_folder_list: bool = False
    
    # Permisos de archivos
    can_file_create: bool = False
    can_file_read: bool = False
    can_file_update: bool = False
    can_file_delete: bool = False
    can_file_rename: bool = False
    can_file_move: bool = False
    can_file_copy: bool = False
    can_file_upload: bool = False
    can_file_download: bool = False
    
    # ============================================================================
    # Metadata de sesión
    # ============================================================================
    
    login_timestamp: str = ""
    last_activity: str = ""
    ip_address: str = ""
    user_agent: str = ""
    
    # ============================================================================
    # Control de UI
    # ============================================================================
    
    current_app: str = "frontend"  # "frontend" o "backoffice"
    
    # ============================================================================
    # Métodos compartidos
    # ============================================================================
    
    @property
    def can_access_backoffice(self) -> bool:
        """
        Determina si el usuario puede acceder al backoffice
        
        Criterio: debe tener training_create = True
        """
        return self.is_logged_in and self.can_training_create
    
    def load_user_data(
        self,
        user_data: dict,
        permissions: dict,
        tokens: dict,
    ) -> None:
        """
        Carga datos del usuario en el state (llamado después del login)
        
        Args:
            user_data: Información básica del usuario
            permissions: Permisos de bajo nivel
            tokens: JWT access y refresh tokens
        """
        # Datos básicos
        self.user_id = user_data.get("user_id", 0)
        self.organization_id = user_data.get("organization_id", 0)
        self.identity_type_id = user_data.get("identity_type_id", 0)
        self.user_name = user_data.get("user_name", "")
        self.user_email = user_data.get("user_email", "")
        self.user_mobile = user_data.get("user_mobile", "")
        self.is_logged_in = True
        self.is_active = user_data.get("active", False)
        self.is_blocked = user_data.get("blocked", False)
        
        # Tokens
        self.access_token = tokens.get("access_token", "")
        self.refresh_token = tokens.get("refresh_token", "")
        self.session_id = tokens.get("session_id", "")
        
        # Cargar todos los permisos
        self._load_permissions(permissions)
        
        logger.info(
            f"Usuario {self.user_id} ({self.user_email}) logueado. "
            f"Acceso backoffice: {self.can_access_backoffice}"
        )
    
    def _load_permissions(self, permissions: dict) -> None:
        """Carga todos los permisos de bajo nivel"""
        # Usuarios
        self.can_user_create = permissions.get("user_create", False)
        self.can_user_read = permissions.get("user_read", False)
        self.can_user_update = permissions.get("user_update", False)
        self.can_user_delete = permissions.get("user_delete", False)
        
        # Organizaciones
        self.can_org_create = permissions.get("org_create", False)
        self.can_org_read = permissions.get("org_read", False)
        self.can_org_update = permissions.get("org_update", False)
        self.can_org_delete = permissions.get("org_delete", False)
        
        # Proyectos
        self.can_project_create = permissions.get("project_create", False)
        self.can_project_read = permissions.get("project_read", False)
        self.can_project_update = permissions.get("project_update", False)
        self.can_project_delete = permissions.get("project_delete", False)
        
        # Versiones
        self.can_version_create = permissions.get("version_create", False)
        self.can_version_read = permissions.get("version_read", False)
        self.can_version_update = permissions.get("version_update", False)
        self.can_version_delete = permissions.get("version_delete", False)
        
        # Datasets
        self.can_dataset_create = permissions.get("dataset_create", False)
        self.can_dataset_read = permissions.get("dataset_read", False)
        self.can_dataset_update = permissions.get("dataset_update", False)
        self.can_dataset_delete = permissions.get("dataset_delete", False)
        
        # Modelos
        self.can_model_create = permissions.get("model_create", False)
        self.can_model_read = permissions.get("model_read", False)
        self.can_model_update = permissions.get("model_update", False)
        self.can_model_delete = permissions.get("model_delete", False)
        
        # Entrenamiento (CRÍTICO)
        self.can_training_create = permissions.get("training_create", False)
        self.can_training_read = permissions.get("training_read", False)
        self.can_training_update = permissions.get("training_update", False)
        self.can_training_delete = permissions.get("training_delete", False)
        
        # Carpetas
        self.can_folder_create = permissions.get("folder_create", False)
        self.can_folder_read = permissions.get("folder_read", False)
        self.can_folder_update = permissions.get("folder_update", False)
        self.can_folder_delete = permissions.get("folder_delete", False)
        self.can_folder_rename = permissions.get("folder_rename", False)
        self.can_folder_move = permissions.get("folder_move", False)
        self.can_folder_copy = permissions.get("folder_copy", False)
        self.can_folder_list = permissions.get("folder_list", False)
        
        # Archivos
        self.can_file_create = permissions.get("file_create", False)
        self.can_file_read = permissions.get("file_read", False)
        self.can_file_update = permissions.get("file_update", False)
        self.can_file_delete = permissions.get("file_delete", False)
        self.can_file_rename = permissions.get("file_rename", False)
        self.can_file_move = permissions.get("file_move", False)
        self.can_file_copy = permissions.get("file_copy", False)
        self.can_file_upload = permissions.get("file_upload", False)
        self.can_file_download = permissions.get("file_download", False)
    
    def clear_session(self) -> None:
        """Limpia todos los datos de sesión"""
        # Resetear datos de usuario
        self.user_id = 0
        self.organization_id = 0
        self.identity_type_id = 0
        self.user_name = ""
        self.user_email = ""
        self.user_mobile = ""
        self.is_logged_in = False
        self.is_active = False
        self.is_blocked = False
        
        # Limpiar tokens
        self.access_token = ""
        self.refresh_token = ""
        self.session_id = ""
        
        # Resetear todos los permisos
        self._reset_permissions()
        
        # Limpiar metadata
        self.login_timestamp = ""
        self.last_activity = ""
        self.ip_address = ""
        self.user_agent = ""
        self.current_app = "frontend"
        
        logger.info("Sesión limpiada")
    
    def _reset_permissions(self) -> None:
        """Resetea todos los permisos a False"""
        # Usuarios
        self.can_user_create = False
        self.can_user_read = False
        self.can_user_update = False
        self.can_user_delete = False
        
        # Organizaciones
        self.can_org_create = False
        self.can_org_read = False
        self.can_org_update = False
        self.can_org_delete = False
        
        # Proyectos
        self.can_project_create = False
        self.can_project_read = False
        self.can_project_update = False
        self.can_project_delete = False
        
        # Versiones
        self.can_version_create = False
        self.can_version_read = False
        self.can_version_update = False
        self.can_version_delete = False
        
        # Datasets
        self.can_dataset_create = False
        self.can_dataset_read = False
        self.can_dataset_update = False
        self.can_dataset_delete = False
        
        # Modelos
        self.can_model_create = False
        self.can_model_read = False
        self.can_model_update = False
        self.can_model_delete = False
        
        # Entrenamiento
        self.can_training_create = False
        self.can_training_read = False
        self.can_training_update = False
        self.can_training_delete = False
        
        # Carpetas
        self.can_folder_create = False
        self.can_folder_read = False
        self.can_folder_update = False
        self.can_folder_delete = False
        self.can_folder_rename = False
        self.can_folder_move = False
        self.can_folder_copy = False
        self.can_folder_list = False
        
        # Archivos
        self.can_file_create = False
        self.can_file_read = False
        self.can_file_update = False
        self.can_file_delete = False
        self.can_file_rename = False
        self.can_file_move = False
        self.can_file_copy = False
        self.can_file_upload = False
        self.can_file_download = False
    
    # ============================================================================
    # Event handlers para navegación
    # ============================================================================
    
    def go_to_backoffice(self) -> rx.event.EventSpec | None:
        """
        Navega al backoffice si el usuario tiene permisos
        
        Este método se puede llamar desde el frontend.
        El state se mantiene automáticamente vía Redis.
        """
        if not self.is_logged_in:
            logger.warning("Intento de acceso a backoffice sin login")
            return rx.window_alert("Debes iniciar sesión primero")
        
        if not self.can_access_backoffice:
            logger.warning(
                f"Usuario {self.user_id} sin permisos de backoffice "
                f"(training_create={self.can_training_create})"
            )
            return rx.window_alert(
                "No tienes permisos para acceder al backoffice"
            )
        
        # Actualizar metadata
        self.current_app = "backoffice"
        
        logger.info(
            f"Usuario {self.user_id} ({self.user_email}) "
            f"navegando a backoffice"
        )
        
        # Redirigir a backoffice
        # El state se sincroniza automáticamente vía Redis
        return rx.redirect("/backoffice/")
    
    def go_to_frontend(self) -> rx.event.EventSpec:
        """
        Navega de vuelta al frontend
        
        Este método se puede llamar desde el backoffice.
        El state se mantiene vía Redis.
        """
        self.current_app = "frontend"
        
        logger.info(
            f"Usuario {self.user_id} ({self.user_email}) "
            f"navegando a frontend"
        )
        
        return rx.redirect("/")
    
    def logout(self) -> rx.event.EventSpec:
        """
        Cierra sesión y limpia el state
        
        El state se elimina de Redis automáticamente después del TTL,
        o se puede limpiar explícitamente.
        """
        user_id = self.user_id
        user_email = self.user_email
        
        logger.info(f"Usuario {user_id} ({user_email}) cerrando sesión")
        
        # Limpiar state
        self.clear_session()
        
        # Redirigir al login
        return rx.redirect("/")

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
    access_token_expires_at: int = 0   # Unix timestamp de expiración
    session_token_expires_at: int = 0  # Unix timestamp de expiración
    
    # ==================== PERMISOS DE BAJO NIVEL ====================
    # Los nombres coinciden EXACTAMENTE con low_level_permissions.json
    # Esto permite validar permisos directamente desde la sesión o JWT
    # Ejemplo: if session.can_folder_rename: mostrar_opcion_renombrar()
    
    # Gestión de carpetas
    can_folder_create: bool = False
    can_folder_delete: bool = False
    can_folder_rename: bool = False
    can_folder_read: bool = False
    can_folder_list: bool = False
    
    # Gestión de ficheros
    can_file_create: bool = False
    can_file_read: bool = False
    can_file_update: bool = False
    can_file_delete: bool = False
    can_file_list: bool = False
    
    # Gestión de proyectos
    can_project_create: bool = False
    can_project_read: bool = False
    can_project_update: bool = False
    can_project_delete: bool = False
    can_project_list: bool = False
    
    # Gestión de versiones
    can_version_create: bool = False
    can_version_read: bool = False
    can_version_update: bool = False
    can_version_delete: bool = False
    can_version_list: bool = False
    
    # Gestión de entrenamiento
    can_training_create: bool = False
    can_training_read: bool = False
    can_training_update: bool = False
    can_training_delete: bool = False
    can_training_start: bool = False
    can_training_stop: bool = False
    
    # Gestión de parámetros
    can_parameters_create: bool = False
    can_parameters_read: bool = False
    can_parameters_update: bool = False
    can_parameters_delete: bool = False
    
    # Gestión de notificaciones
    can_notifications_create: bool = False
    can_notifications_read: bool = False
    can_notifications_update: bool = False
    can_notifications_delete: bool = False
    
    # Gestión de usuarios
    can_user_create: bool = False
    can_user_read: bool = False
    can_user_update: bool = False
    can_user_delete: bool = False
    can_user_enable: bool = False
    can_user_disable: bool = False
    
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
        access_expires_at: int = 0,
        session_expires_at: int = 0,
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
            access_expires_at: Unix timestamp de expiración del access_token
            session_expires_at: Unix timestamp de expiración del session_token
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
        
        # Tokens y timestamps de expiración
        self.access_token = access_token
        self.session_token = session_token
        self.access_token_expires_at = access_expires_at
        self.session_token_expires_at = session_expires_at
        
        # Cargar permisos
        self._load_permissions(permissions)
        
        # Metadata
        self.session_id = session_token
        self.login_time = datetime.now().isoformat()
        self.last_activity = datetime.now().isoformat()
        self.current_app = "frontend"

        # Guardar tokens en Redis para sincronización con backoffice
        self._save_tokens_to_redis()
    
    def _load_permissions(self, permissions: dict):
        """
        Carga los permisos de bajo nivel desde el diccionario.
        
        Los nombres de los campos coinciden EXACTAMENTE con low_level_permissions.json.
        Esto permite validar permisos directamente desde la sesión.
        
        Ejemplo de uso en la UI:
            if state.can_folder_rename:
                mostrar_opcion_renombrar_carpeta()
        
        Args:
            permissions: Diccionario con estructura de low_level_permissions
        """
        # Gestión de carpetas
        self.can_folder_create = permissions.get("folder_create", False)
        self.can_folder_delete = permissions.get("folder_delete", False)
        self.can_folder_rename = permissions.get("folder_rename", False)
        self.can_folder_read = permissions.get("folder_read", False)
        self.can_folder_list = permissions.get("folder_list", False)
        
        # Gestión de ficheros
        self.can_file_create = permissions.get("file_create", False)
        self.can_file_read = permissions.get("file_read", False)
        self.can_file_update = permissions.get("file_update", False)
        self.can_file_delete = permissions.get("file_delete", False)
        self.can_file_list = permissions.get("file_list", False)
        
        # Gestión de proyectos
        self.can_project_create = permissions.get("project_create", False)
        self.can_project_read = permissions.get("project_read", False)
        self.can_project_update = permissions.get("project_update", False)
        self.can_project_delete = permissions.get("project_delete", False)
        self.can_project_list = permissions.get("project_list", False)
        
        # Gestión de versiones
        self.can_version_create = permissions.get("version_create", False)
        self.can_version_read = permissions.get("version_read", False)
        self.can_version_update = permissions.get("version_update", False)
        self.can_version_delete = permissions.get("version_delete", False)
        self.can_version_list = permissions.get("version_list", False)
        
        # Gestión de entrenamiento
        self.can_training_create = permissions.get("training_create", False)
        self.can_training_read = permissions.get("training_read", False)
        self.can_training_update = permissions.get("training_update", False)
        self.can_training_delete = permissions.get("training_delete", False)
        self.can_training_start = permissions.get("training_start", False)
        self.can_training_stop = permissions.get("training_stop", False)
        
        # Gestión de parámetros
        self.can_parameters_create = permissions.get("parameters_create", False)
        self.can_parameters_read = permissions.get("parameters_read", False)
        self.can_parameters_update = permissions.get("parameters_update", False)
        self.can_parameters_delete = permissions.get("parameters_delete", False)
        
        # Gestión de notificaciones
        self.can_notifications_create = permissions.get("notifications_create", False)
        self.can_notifications_read = permissions.get("notifications_read", False)
        self.can_notifications_update = permissions.get("notifications_update", False)
        self.can_notifications_delete = permissions.get("notifications_delete", False)
        
        # Gestión de usuarios
        self.can_user_create = permissions.get("user_create", False)
        self.can_user_read = permissions.get("user_read", False)
        self.can_user_update = permissions.get("user_update", False)
        self.can_user_delete = permissions.get("user_delete", False)
        self.can_user_enable = permissions.get("user_enable", False)
        self.can_user_disable = permissions.get("user_disable", False)
    
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
        
        # Tokens y timestamps
        self.access_token = ""
        self.session_token = ""
        self.access_token_expires_at = 0
        self.session_token_expires_at = 0
        
        # Resetear permisos
        self._reset_permissions()
        
        # Metadata
        self.session_id = ""
        self.login_time = ""
        self.last_activity = ""
        self.current_app = "frontend"
    
    @staticmethod
    def _load_env_settings():
        """Carga env_settings.py dinámicamente."""
        import importlib.util
        from pathlib import Path
        env_settings_path = Path(__file__).resolve().parent.parent / "config" / "env_settings.py"
        spec = importlib.util.spec_from_file_location("env_settings_nav", env_settings_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _get_nav_urls(self) -> dict:
        """
        Obtiene las URLs de navegación entre apps desde env_settings.py.

        Prioridad: frontend_nav_url / backoffice_nav_url (URLs de navegación)
        Fallback:  frontend_api_url / backoffice_api_url (URLs de API)

        En dev/pro/pre, las api_url ya son las URLs públicas del navegador.
        En macbook, las api_url apuntan a localhost, por lo que se usan las nav_url.
        """
        try:
            env_settings = self._load_env_settings()
            frontend = env_settings.get_env_value(
                "frontend_nav_url",
                env_settings.get_env_value("frontend_api_url", "https://localhost"),
            )
            backoffice = env_settings.get_env_value(
                "backoffice_nav_url",
                env_settings.get_env_value("backoffice_api_url", "https://localhost:8443"),
            )
            return {"frontend": frontend, "backoffice": backoffice}
        except Exception as e:
            print(f"[NAV URLS] Error al cargar configuración: {e}, usando defaults")
            return {
                "frontend": "https://localhost",
                "backoffice": "https://localhost:8443",
            }

    def _get_redis_config(self) -> dict:
        """
        Obtiene la configuración de Redis desde env_settings.py
        (misma configuración que usa Reflex en rxconfig.py)
        """
        try:
            import sys
            import importlib.util
            from pathlib import Path

            # Cargar env_settings dinámicamente
            env_settings_path = Path(__file__).resolve().parent.parent / "config" / "env_settings.py"
            spec = importlib.util.spec_from_file_location("env_settings_redis", env_settings_path)
            env_settings = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(env_settings)

            # Leer configuración (misma lógica que rxconfig.py)
            return {
                "host": env_settings.get_env_value("redis_host", "localhost"),
                "port": int(env_settings.get_env_value("redis_port", "6379")),
                "password": env_settings.get_protected_value("redis_password", None),
                "db": int(env_settings.get_env_value("redis_db", "0")),
            }
        except Exception as e:
            print(f"[REDIS CONFIG] Error al cargar configuración: {e}, usando defaults")
            return {
                "host": "localhost",
                "port": 6379,
                "password": None,
                "db": 0,
            }

    def _save_tokens_to_redis(self):
        """
        Guarda los tokens actualizados en Redis para sincronización entre apps.

        Clave: session_tokens:{session_id}
        TTL: 45 minutos (igual que session_token)
        """
        if not self.session_id:
            return

        try:
            import redis
            import json

            # Obtener configuración de Redis
            redis_config = self._get_redis_config()

            # Conectar a Redis (con username para Redis 6+ ACL)
            redis_params = {
                "host": redis_config["host"],
                "port": redis_config["port"],
                "db": redis_config["db"],
                "decode_responses": True
            }
            if redis_config["password"]:
                redis_params["username"] = "default"
                redis_params["password"] = redis_config["password"]

            r = redis.Redis(**redis_params)

            # Preparar datos de tokens
            tokens_data = {
                "access_token": self.access_token,
                "session_token": self.session_token,
                "access_expires_at": self.access_token_expires_at,
                "session_expires_at": self.session_token_expires_at,
                "updated_at": datetime.now().isoformat(),
                "user_id": self.user_id,
                "organization_id": self.organization_id,
            }

            # Guardar en Redis con TTL de 45 minutos (2700 segundos)
            redis_key = f"session_tokens:{self.session_id}"
            r.setex(redis_key, 2700, json.dumps(tokens_data))

            print(f"[REDIS SYNC] Tokens guardados en Redis: {redis_key}")

        except Exception as e:
            # No fallar si Redis no está disponible, solo log
            print(f"[REDIS SYNC] Error al guardar tokens en Redis: {e}")

    def _load_tokens_from_redis(self) -> bool:
        """
        Carga tokens desde Redis si hay una versión más reciente.

        Returns:
            True si se cargaron tokens más recientes, False si no
        """
        if not self.session_id:
            return False

        try:
            import redis
            import json
            from datetime import datetime as dt

            # Obtener configuración de Redis
            redis_config = self._get_redis_config()

            # Conectar a Redis (con username para Redis 6+ ACL)
            redis_params = {
                "host": redis_config["host"],
                "port": redis_config["port"],
                "db": redis_config["db"],
                "decode_responses": True
            }
            if redis_config["password"]:
                redis_params["username"] = "default"
                redis_params["password"] = redis_config["password"]

            r = redis.Redis(**redis_params)

            # Leer tokens de Redis
            redis_key = f"session_tokens:{self.session_id}"
            tokens_json = r.get(redis_key)

            if not tokens_json:
                return False

            tokens_data = json.loads(tokens_json)

            # Comparar timestamps para ver si hay tokens más recientes
            redis_updated_at = tokens_data.get("updated_at", "")
            current_updated_at = self.last_activity

            # CASO 1: Si no tenemos last_activity local (primera carga), siempre cargar desde Redis
            # CASO 2: Si los tokens de Redis son más recientes, actualizarlos
            should_update = not current_updated_at or (redis_updated_at > current_updated_at)

            if should_update:
                self.access_token = tokens_data["access_token"]
                self.session_token = tokens_data["session_token"]
                self.access_token_expires_at = tokens_data["access_expires_at"]
                self.session_token_expires_at = tokens_data["session_expires_at"]
                self.last_activity = redis_updated_at

                reason = "primera carga" if not current_updated_at else "tokens más recientes"
                print(f"[REDIS SYNC] Tokens actualizados desde Redis ({reason}): {redis_key}")
                return True

            return False

        except Exception as e:
            print(f"[REDIS SYNC] Error al cargar tokens desde Redis: {e}")
            return False

    def update_tokens(
        self,
        access_token: str,
        session_token: str,
        access_expires_at: int,
        session_expires_at: int,
    ):
        """
        Actualiza los tokens tras una renovación automática.

        Este método se llama cuando el access_token está próximo a expirar
        y se renueva usando el session_token.

        IMPORTANTE: Guarda los tokens actualizados en Redis para sincronización
        entre frontend y backoffice.

        Args:
            access_token: Nuevo token JWT de acceso
            session_token: Nuevo token JWT de sesión
            access_expires_at: Unix timestamp de expiración del nuevo access_token
            session_expires_at: Unix timestamp de expiración del nuevo session_token
        """
        self.access_token = access_token
        self.session_token = session_token
        self.access_token_expires_at = access_expires_at
        self.session_token_expires_at = session_expires_at
        self.last_activity = datetime.now().isoformat()

        # Guardar tokens actualizados en Redis para sincronización entre apps
        self._save_tokens_to_redis()
    
    def _reset_permissions(self):
        """Resetea todos los permisos a False."""
        # Gestión de carpetas
        self.can_folder_create = False
        self.can_folder_delete = False
        self.can_folder_rename = False
        self.can_folder_read = False
        self.can_folder_list = False
        
        # Gestión de ficheros
        self.can_file_create = False
        self.can_file_read = False
        self.can_file_update = False
        self.can_file_delete = False
        self.can_file_list = False
        
        # Gestión de proyectos
        self.can_project_create = False
        self.can_project_read = False
        self.can_project_update = False
        self.can_project_delete = False
        self.can_project_list = False
        
        # Gestión de versiones
        self.can_version_create = False
        self.can_version_read = False
        self.can_version_update = False
        self.can_version_delete = False
        self.can_version_list = False
        
        # Gestión de entrenamiento
        self.can_training_create = False
        self.can_training_read = False
        self.can_training_update = False
        self.can_training_delete = False
        self.can_training_start = False
        self.can_training_stop = False
        
        # Gestión de parámetros
        self.can_parameters_create = False
        self.can_parameters_read = False
        self.can_parameters_update = False
        self.can_parameters_delete = False
        
        # Gestión de notificaciones
        self.can_notifications_create = False
        self.can_notifications_read = False
        self.can_notifications_update = False
        self.can_notifications_delete = False
        
        # Gestión de usuarios
        self.can_user_create = False
        self.can_user_read = False
        self.can_user_update = False
        self.can_user_delete = False
        self.can_user_enable = False
        self.can_user_disable = False
    
    def go_to_backoffice(self):
        """
        Marca que el usuario está navegando al backoffice.

        SEGURIDAD MEJORADA: Solo pasa session_id en URL (no tokens completos).
        Los tokens se cargarán desde Redis en el backoffice.
        """
        self.current_app = "backoffice"
        self.last_activity = datetime.now().isoformat()

        # Guardar tokens actualizados en Redis antes de cambiar de app
        self._save_tokens_to_redis()

        # Pasar SOLO session_id en URL (seguro)
        import urllib.parse
        params = urllib.parse.urlencode({
            "session_id": self.session_id,
            "user_id": str(self.user_id),
            "org_id": str(self.organization_id),
        })

        nav_urls = self._get_nav_urls()
        backoffice_url = nav_urls["backoffice"]
        print(f"[APP SWITCH] Redirigiendo a backoffice ({backoffice_url}) con session_id={self.session_id}")
        return rx.redirect(f"{backoffice_url}?{params}")

    def go_to_frontend(self):
        """
        Marca que el usuario está regresando al frontend.

        SEGURIDAD MEJORADA: Solo pasa session_id en URL (no tokens completos).
        Los tokens se cargarán desde Redis en el frontend.
        """
        self.current_app = "frontend"
        self.last_activity = datetime.now().isoformat()

        # Guardar tokens actualizados en Redis antes de cambiar de app
        self._save_tokens_to_redis()

        # Pasar SOLO session_id en URL (seguro)
        import urllib.parse
        params = urllib.parse.urlencode({
            "session_id": self.session_id,
            "user_id": str(self.user_id),
            "org_id": str(self.organization_id),
        })

        nav_urls = self._get_nav_urls()
        frontend_url = nav_urls["frontend"]
        redirect_url = f"{frontend_url}?{params}"
        print(f"[APP SWITCH] Redirigiendo a frontend ({frontend_url}) con session_id={self.session_id}")

        return rx.redirect(redirect_url)
    
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
    
    def check_token_expiration(self) -> dict[str, any]:
        """
        Verifica si los tokens están próximos a expirar.

        Returns:
            Diccionario con:
            - needs_renewal: bool, True si access_token expira en menos de 3 min
            - seconds_until_access_expires: int, segundos restantes del access_token
            - seconds_until_session_expires: int, segundos restantes del session_token
            - session_expired: bool, True si session_token ya expiró
        """
        import time

        now = int(time.time())

        # Calcular segundos restantes
        seconds_until_access_expires = max(0, self.access_token_expires_at - now)
        seconds_until_session_expires = max(0, self.session_token_expires_at - now)

        # Umbral de renovación: 3 minutos (180 segundos)
        RENEWAL_THRESHOLD = 180

        return {
            "needs_renewal": seconds_until_access_expires < RENEWAL_THRESHOLD and seconds_until_access_expires > 0,
            "seconds_until_access_expires": seconds_until_access_expires,
            "seconds_until_session_expires": seconds_until_session_expires,
            "session_expired": seconds_until_session_expires <= 0,
        }

    def update_activity(self):
        """
        Actualiza el timestamp de última actividad.
        Debe ser llamado en cada interacción significativa del usuario.
        """
        self.last_activity = datetime.now().isoformat()
    
    # ==================== MÉTODOS DE VALIDACIÓN DE PERMISOS ====================
    
    def has_permission(self, permission_key: str) -> bool:
        """
        Valida si el usuario tiene un permiso específico por nombre.
        
        Este método permite validar permisos dinámicamente usando el nombre
        exacto del permiso como se define en low_level_permissions.json.
        
        Ejemplo de uso:
            if state.has_permission("folder_rename"):
                mostrar_opcion_renombrar()
            
            # En un menú contextual:
            opciones = []
            if state.has_permission("file_delete"):
                opciones.append("Eliminar")
            if state.has_permission("file_update"):
                opciones.append("Editar")
        
        Args:
            permission_key: Nombre del permiso (ej: "folder_rename", "file_create")
        
        Returns:
            True si el usuario tiene el permiso, False en caso contrario
        """
        if not self.is_logged_in:
            return False
        
        # Mapeo de claves de permiso a atributos del estado
        permission_map = {
            # Carpetas
            "folder_create": self.can_folder_create,
            "folder_delete": self.can_folder_delete,
            "folder_rename": self.can_folder_rename,
            "folder_read": self.can_folder_read,
            "folder_list": self.can_folder_list,
            # Ficheros
            "file_create": self.can_file_create,
            "file_read": self.can_file_read,
            "file_update": self.can_file_update,
            "file_delete": self.can_file_delete,
            "file_list": self.can_file_list,
            # Proyectos
            "project_create": self.can_project_create,
            "project_read": self.can_project_read,
            "project_update": self.can_project_update,
            "project_delete": self.can_project_delete,
            "project_list": self.can_project_list,
            # Versiones
            "version_create": self.can_version_create,
            "version_read": self.can_version_read,
            "version_update": self.can_version_update,
            "version_delete": self.can_version_delete,
            "version_list": self.can_version_list,
            # Entrenamiento
            "training_create": self.can_training_create,
            "training_read": self.can_training_read,
            "training_update": self.can_training_update,
            "training_delete": self.can_training_delete,
            "training_start": self.can_training_start,
            "training_stop": self.can_training_stop,
            # Parámetros
            "parameters_create": self.can_parameters_create,
            "parameters_read": self.can_parameters_read,
            "parameters_update": self.can_parameters_update,
            "parameters_delete": self.can_parameters_delete,
            # Notificaciones
            "notifications_create": self.can_notifications_create,
            "notifications_read": self.can_notifications_read,
            "notifications_update": self.can_notifications_update,
            "notifications_delete": self.can_notifications_delete,
            # Usuarios
            "user_create": self.can_user_create,
            "user_read": self.can_user_read,
            "user_update": self.can_user_update,
            "user_delete": self.can_user_delete,
            "user_enable": self.can_user_enable,
            "user_disable": self.can_user_disable,
        }
        
        return permission_map.get(permission_key, False)
    
    def get_all_permissions(self) -> dict:
        """
        Obtiene todos los permisos del usuario como diccionario.
        
        Útil para debugging, logging y para pasar permisos a componentes UI.
        El formato del diccionario coincide con low_level_permissions.json.
        
        Ejemplo de uso:
            permisos = state.get_all_permissions()
            logger.info(f"Permisos de {state.user_name}: {permisos}")
            
            # Verificar múltiples permisos:
            permisos_necesarios = ["folder_create", "file_create"]
            tiene_todos = all(permisos.get(p) for p in permisos_necesarios)
        
        Returns:
            Diccionario con todos los permisos {nombre_permiso: bool}
        """
        return {
            # Carpetas
            "folder_create": self.can_folder_create,
            "folder_delete": self.can_folder_delete,
            "folder_rename": self.can_folder_rename,
            "folder_read": self.can_folder_read,
            "folder_list": self.can_folder_list,
            # Ficheros
            "file_create": self.can_file_create,
            "file_read": self.can_file_read,
            "file_update": self.can_file_update,
            "file_delete": self.can_file_delete,
            "file_list": self.can_file_list,
            # Proyectos
            "project_create": self.can_project_create,
            "project_read": self.can_project_read,
            "project_update": self.can_project_update,
            "project_delete": self.can_project_delete,
            "project_list": self.can_project_list,
            # Versiones
            "version_create": self.can_version_create,
            "version_read": self.can_version_read,
            "version_update": self.can_version_update,
            "version_delete": self.can_version_delete,
            "version_list": self.can_version_list,
            # Entrenamiento
            "training_create": self.can_training_create,
            "training_read": self.can_training_read,
            "training_update": self.can_training_update,
            "training_delete": self.can_training_delete,
            "training_start": self.can_training_start,
            "training_stop": self.can_training_stop,
            # Parámetros
            "parameters_create": self.can_parameters_create,
            "parameters_read": self.can_parameters_read,
            "parameters_update": self.can_parameters_update,
            "parameters_delete": self.can_parameters_delete,
            # Notificaciones
            "notifications_create": self.can_notifications_create,
            "notifications_read": self.can_notifications_read,
            "notifications_update": self.can_notifications_update,
            "notifications_delete": self.can_notifications_delete,
            # Usuarios
            "user_create": self.can_user_create,
            "user_read": self.can_user_read,
            "user_update": self.can_user_update,
            "user_delete": self.can_user_delete,
            "user_enable": self.can_user_enable,
            "user_disable": self.can_user_disable,
        }
    
    def has_any_permission(self, permission_keys: list) -> bool:
        """
        Verifica si el usuario tiene AL MENOS UNO de los permisos especificados.
        
        Útil para mostrar secciones de UI si el usuario tiene cualquier
        permiso relacionado.
        
        Ejemplo:
            # Mostrar sección de gestión si tiene algún permiso de usuario
            if state.has_any_permission(["user_create", "user_read", "user_update"]):
                mostrar_seccion_usuarios()
        
        Args:
            permission_keys: Lista de nombres de permisos a verificar
        
        Returns:
            True si tiene al menos uno de los permisos
        """
        return any(self.has_permission(key) for key in permission_keys)
    
    def has_all_permissions(self, permission_keys: list) -> bool:
        """
        Verifica si el usuario tiene TODOS los permisos especificados.
        
        Útil para operaciones que requieren múltiples permisos.
        
        Ejemplo:
            # Para crear y configurar un proyecto completo
            if state.has_all_permissions(["project_create", "folder_create", "file_create"]):
                habilitar_creacion_proyecto_completo()
        
        Args:
            permission_keys: Lista de nombres de permisos requeridos
        
        Returns:
            True si tiene todos los permisos especificados
        """
        return all(self.has_permission(key) for key in permission_keys)
    
    # ==================== PROPIEDADES DE PERMISOS COMPUESTOS ====================
    
    @rx.var
    def can_manage_folders(self) -> bool:
        """Indica si puede gestionar carpetas (crear, renombrar, eliminar)."""
        return self.is_logged_in and (
            self.can_folder_create or 
            self.can_folder_rename or 
            self.can_folder_delete
        )
    
    @rx.var
    def can_manage_files(self) -> bool:
        """Indica si puede gestionar ficheros (crear, editar, eliminar)."""
        return self.is_logged_in and (
            self.can_file_create or 
            self.can_file_update or 
            self.can_file_delete
        )
    
    @rx.var
    def can_manage_projects(self) -> bool:
        """Indica si puede gestionar proyectos."""
        return self.is_logged_in and (
            self.can_project_create or 
            self.can_project_update or 
            self.can_project_delete
        )
    
    @rx.var
    def can_manage_training(self) -> bool:
        """Indica si puede gestionar entrenamientos."""
        return self.is_logged_in and (
            self.can_training_create or 
            self.can_training_start or 
            self.can_training_stop
        )
    
    @rx.var
    def can_manage_users(self) -> bool:
        """Indica si puede gestionar usuarios."""
        return self.is_logged_in and (
            self.can_user_create or 
            self.can_user_update or 
            self.can_user_delete or
            self.can_user_enable or
            self.can_user_disable
        )
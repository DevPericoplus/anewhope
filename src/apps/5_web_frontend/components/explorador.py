import reflex as rx
import pydantic
import json
import logging
import os
import importlib.util
import sys
from pathlib import Path

# Imports de adaptadores API
from adapters.api_client import (
    fmanagement_list_all_project_versions,
    update_version_state,
    generate_file_upload_token,
    generate_file_download_token,
    fmanagement_create_folder,
    fmanagement_rename_folder,
    fmanagement_delete_folder,
    fmanagement_rename_file,
    fmanagement_delete_file,
    fmanagement_get_properties,
)

# Configuración de Logging (DEBE IR ANTES de importar permisos)
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "console.log")

# Configurar el logger
logger = logging.getLogger("ExploradorComponent")
logger.setLevel(logging.INFO)
# Evitar duplicar handlers si se recarga el módulo
if not logger.handlers:
    handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Importar adaptador de permisos y mapeo desde capa compartida
try:
    # Cargar adaptador de permisos
    # Path: explorador.py -> components -> 5_web_frontend -> apps -> src
    # parents[3] nos lleva a "src", luego accedemos a 2_shared_application
    _perms_adapter_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "adapters" / "user_permissions_adapter.py"
    _perms_spec = importlib.util.spec_from_file_location("user_permissions_adapter", _perms_adapter_path)
    _perms_module = importlib.util.module_from_spec(_perms_spec)
    sys.modules["user_permissions_adapter"] = _perms_module
    _perms_spec.loader.exec_module(_perms_module)
    get_user_permissions = _perms_module.get_user_permissions
    get_user_identity_type_id = _perms_module.get_user_identity_type_id

    # Cargar mapeo de permisos
    _mapping_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "explorador_permissions_mapping.py"
    _mapping_spec = importlib.util.spec_from_file_location("explorador_permissions_mapping", _mapping_path)
    _mapping_module = importlib.util.module_from_spec(_mapping_spec)
    sys.modules["explorador_permissions_mapping"] = _mapping_module
    _mapping_spec.loader.exec_module(_mapping_module)
    get_required_permission = _mapping_module.get_required_permission
    is_action_allowed = _mapping_module.is_action_allowed

    logger.info("Módulos de permisos cargados exitosamente")
except Exception as e:
    logger.error(f"Error al cargar módulos de permisos: {e}")
    import traceback
    traceback.print_exc()
    # Fallback functions
    def get_user_permissions(user_id, engine=None):
        return {}
    def get_user_identity_type_id(user_id, engine=None):
        return None
    def get_required_permission(action, item_type):
        return None
    def is_action_allowed(action, item_type, user_permissions):
        return True


def _load_storage_module():
    """Carga el módulo de almacenamiento desde infraestructura."""
    module_path = (
        Path(__file__).resolve().parents[3]
        / "src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py"
    )
    spec = importlib.util.spec_from_file_location("frontend_storage_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el módulo de almacenamiento")
    module = importlib.util.module_from_spec(spec)
    sys.modules["frontend_storage_module"] = module
    spec.loader.exec_module(module)
    return module


# Cargar módulo de almacenamiento para acceso a BD
try:
    _storage_module = _load_storage_module()
    load_mariadb_settings = _storage_module.load_mariadb_settings
except Exception as e:
    logger.warning(f"No se pudo cargar módulo de almacenamiento: {e}")
    load_mariadb_settings = None


class FolderItem(pydantic.BaseModel):
    id: str
    name: str
    depth: int
    parent_id: str = ""
    is_expanded: bool = False
    has_children: bool = False
    is_visible: bool = True
    item_type: str = "folder" # "folder" or "file"
    is_protected: bool = False # Level 0 and 1 are protected (structural protection)
    db_protected: bool = False # Database protected field from version_states (content protection)
    is_blocked: bool = False # Operational block (opacity 0.5)
    size_str: str = "" # Formatted size (e.g. "1.2 MB")
    metadata: dict = {} # Extra info
    version_state_label: str = "" # Estado de la versión (ej: "(Bloqueada)")
    version_state_color: str = "" # Color del estado (ej: "#FF8C00")
    is_final_c: bool = False # Flag cliente
    is_final_i: bool = False # Flag interno

class ExploradorState(rx.State):
    """Estado del explorador con gestión de tamaños, selección y estados de versión."""
    items: list[FolderItem] = []
    fmanagementlist: dict = {}
    selected_item_id: str = ""

    # Atributos del proyecto actual
    id_organizacion: int = 1
    id_proyecto: int = 1

    # Estados de todas las versiones del proyecto
    # Estructura: {"v001": {state, protected, size, final_c, final_i}, "v002": {...}}
    version_states: dict = {}

    # Perfil de Seguridad y Usuario
    user_id: int = 0
    user_name: str = "anonimo"
    user_identity_type_id: int = 0  # Identity type del usuario (1=SuperAdmin, 2=OrgAdmin, etc.)
    user_id_organizacion: int = 1
    user_project_id: int = 1
    is_admin: bool = False

    # Tokens de sesión (necesarios para API calls)
    access_token: str = ""
    session_token: str = ""

    # Simulación de Identidad (Impersonation)
    is_internal_user: bool = False  # False = Cliente, True = Interno

    @rx.var
    def current_role_label(self) -> str:
        return "Interno" if self.is_internal_user else "Cliente"

    def toggle_user_role(self, val: bool):
        self.is_internal_user = val
        # Aquí podremos añadir lógica específica al cambiar de rol más adelante
        self.interpretacion_estados()

    # Matriz de Permisos (todos los permisos de low_level_permissions)
    permisos: dict = {
        # Carpetas
        "folder_create": False,
        "folder_delete": False,
        "folder_rename": False,
        "folder_read": False,
        "folder_list": False,
        # Archivos
        "file_create": False,
        "file_read": False,
        "file_update": False,
        "file_delete": False,
        "file_list": False,
        # Proyectos
        "project_create": False,
        "project_read": False,
        "project_update": False,
        "project_delete": False,
        "project_list": False,
        # Versiones
        "version_create": False,
        "version_read": False,
        "version_update": False,
        "version_delete": False,
        "version_list": False,
        # Entrenamiento
        "training_create": False,
        "training_read": False,
        "training_update": False,
        "training_delete": False,
        "training_start": False,
        "training_stop": False,
        # Parámetros
        "parameters_create": False,
        "parameters_read": False,
        "parameters_update": False,
        "parameters_delete": False,
        # Notificaciones
        "notifications_create": False,
        "notifications_read": False,
        "notifications_update": False,
        "notifications_delete": False,
        # Usuarios
        "user_create": False,
        "user_read": False,
        "user_update": False,
        "user_delete": False,
        "user_enable": False,
        "user_disable": False,
    }

    @rx.var
    def is_access_authorized(self) -> bool:
        """Validación cruzada: Verifica si el usuario pertenece a la org y proyecto actual."""
        return (self.user_id_organizacion == self.id_organizacion) and (self.user_project_id == self.id_proyecto)

    @rx.var
    def can_folder_create(self) -> bool:
        """Permiso para crear carpetas."""
        return self.permisos.get("folder_create", False)

    @rx.var
    def can_folder_rename(self) -> bool:
        """Permiso para renombrar carpetas."""
        return self.permisos.get("folder_rename", False)

    @rx.var
    def can_folder_delete(self) -> bool:
        """Permiso para eliminar carpetas."""
        return self.permisos.get("folder_delete", False)

    @rx.var
    def can_folder_read(self) -> bool:
        """Permiso para leer/ver propiedades de carpetas."""
        return self.permisos.get("folder_read", False)

    @rx.var
    def can_file_create(self) -> bool:
        return self.permisos.get("file_create", False)

    @rx.var
    def can_file_read(self) -> bool:
        return self.permisos.get("file_read", False)

    @rx.var
    def can_file_update(self) -> bool:
        return self.permisos.get("file_update", False)

    @rx.var
    def can_file_delete(self) -> bool:
        return self.permisos.get("file_delete", False)

    @rx.var
    def can_file_list(self) -> bool:
        return self.permisos.get("file_list", False)

    # Identidad de Sistema (Capa 2)
    user_identity_type_id: int = 0
    is_auditor: bool = False # Flag para restricciones visuales (Auditores)

    # Tokens de autenticación (necesarios para llamadas a API)
    access_token: str = ""
    session_token: str = ""

    # Estado de carga
    is_loading: bool = False
    error_message: str = ""

    # Variables para diálogos de acciones
    show_create_folder_dialog: bool = False
    show_rename_dialog: bool = False
    show_delete_confirm_dialog: bool = False
    show_properties_dialog: bool = False

    # Item actual para la acción
    current_action_item: FolderItem | None = None
    dialog_input_value: str = ""
    properties_info: str = ""

    def apply_system_role_security(self):
        """
        Capa 2: Validacion Cruzada con Roles de Sistema (roles_by_app.json).
        - Prevalencia de FALSE: Si el rol de sistema niega, se niega.
        - Determinacion de Rol Funcional (Cliente/Interno).
        - Restricciones visuales para Auditores.
        """
        try:
            import os
            json_path = os.path.join(os.getcwd(), "data", "roles_by_app.json")
            with open(json_path, "r") as f:
                roles_data = json.load(f)
                
            # Buscar el rol del usuario
            system_role = next((r for r in roles_data if r["identity_type_id"] == self.user_identity_type_id), None)
            
            if not system_role:
                logger.warning(f"Rol de sistema {self.user_identity_type_id} no encontrado.")
                print(f"ALERTA: Rol de sistema {self.user_identity_type_id} no encontrado. Se mantienen permisos de usuario (Capa 1).")
                return

            print(f"Aplicando seguridad de capa 2 para rol: {system_role.get('description', 'Unknown')}")
            logger.info(f"Aplicando seguridad Capa 2. Rol: {system_role.get('description', 'Unknown')}")
            
            # 1. Determinación de Rol Funcional (Cliente vs Interno)
            # Se basa EXCLUSIVAMENTE en trainig_create del rol de sistema
            system_training_create = system_role["permisos"].get("trainig_create", False)
            self.is_internal_user = system_training_create
            print(f"Rol funcional determinado: {'Interno' if self.is_internal_user else 'Cliente'}")

            # 2. Validación Cruzada de Permisos (AND Lógico: User & System)
            for perm_key, user_val in self.permisos.items():
                if perm_key in system_role["permisos"]:
                    system_val = system_role["permisos"][perm_key]
                    # Si el sistema dice FALSE, forzamos FALSE aunque el usuario tenga TRUE
                    if not system_val and user_val:
                        print(f"RESTRICCIÓN: Permiso '{perm_key}' revocado por Rol de Sistema.")
                        self.permisos[perm_key] = False
            
            # Recalcular is_admin tras validación (por si version_create fue revocado)
            self.is_admin = self.permisos.get("version_create", False)

            # 3. Detección de Auditor (Tipos 5 y 13 o pattern matching estricto de solo lectura)
            # Definición explicita por ID como solicitado
            if self.user_identity_type_id in [5, 13]:
                self.is_auditor = True
                print("Modo Auditor Activado: Restricciones visuales aplicadas.")
            else:
                self.is_auditor = False

        except Exception as e:
            print(f"Error en validación de seguridad capa 2: {e}")

    def load_security_profile(self):
        """Carga el perfil de seguridad del usuario desde la base de datos.

        Consulta proyectos_roles para obtener el id_rol del usuario en el proyecto actual,
        y luego consulta low_level_permissions para obtener los permisos específicos.
        """
        try:
            # Intentar obtener user_id y organization_id del parent state (web_frontend.State)
            try:
                from web_frontend.web_frontend import State as MainState
                main_state = self.get_state(MainState)
                if main_state and main_state.user_id > 0:
                    self.user_id = main_state.user_id
                    self.id_organizacion = main_state.organization_id
                    self.user_name = main_state.user_name
                    self.access_token = main_state.access_token
                    self.session_token = main_state.session_token
                    logger.info(f"✓ Datos de sesión obtenidos: user_id={self.user_id}, org_id={self.id_organizacion}, project_id={self.id_proyecto}")
                    print(f"✓ Datos de sesión obtenidos: user_id={self.user_id}, org_id={self.id_organizacion}, project_id={self.id_proyecto}")
                else:
                    logger.warning(f"Estado principal no disponible o user_id=0")
                    print(f"⚠ Estado principal no disponible o user_id=0")
            except Exception as e:
                logger.warning(f"No se pudo obtener datos del estado principal: {e}")
                print(f"⚠ No se pudo obtener datos del estado principal: {e}")

            # Si no tenemos user_id o project_id, usar permisos por defecto de desarrollo
            if self.user_id <= 0 or self.id_proyecto <= 0:
                logger.warning(f"⚠ No se puede cargar permisos desde BD: user_id={self.user_id}, project_id={self.id_proyecto}")
                print(f"⚠ Usando permisos por defecto (modo desarrollo): user_id={self.user_id}, project_id={self.id_proyecto}")
                # Habilitar todos los permisos por defecto para desarrollo
                self._set_default_permissions()
                return

            # Cargar permisos desde la base de datos
            self._load_permissions_from_database()

        except Exception as e:
            logger.error(f"✗ Error cargando perfil de seguridad: {e}")
            print(f"✗ Error cargando perfil de seguridad: {e}")
            # En caso de error, usar permisos por defecto
            self._set_default_permissions()

    def _set_default_permissions(self):
        """Establece permisos por defecto para desarrollo."""
        self.permisos = {
            "folder_create": True,
            "folder_delete": True,
            "folder_rename": True,
            "folder_read": True,
            "folder_list": True,
            "file_create": True,
            "file_read": True,
            "file_update": True,
            "file_delete": True,
            "file_list": True,
            "version_create": True,
        }
        self.is_admin = True
        logger.info("✓ Permisos por defecto establecidos (modo desarrollo)")
        print("✓ Permisos por defecto establecidos: todos los permisos habilitados")

    def _load_permissions_from_database(self):
        """
        Consulta la base de datos para obtener permisos del usuario.

        Flujo:
        1. Obtener identity_type_id desde users usando user_id
        2. Obtener permisos desde low_level_permissions usando identity_type_id
        3. Almacenar todos los permisos en memoria

        Los permisos se cargan una vez al iniciar el explorador y se mantienen
        en memoria durante toda la sesión.
        """
        if not load_mariadb_settings:
            logger.warning("⚠ Función load_mariadb_settings no disponible")
            print("⚠ Función load_mariadb_settings no disponible")
            self._set_default_permissions()
            return

        try:
            from sqlalchemy import create_engine, text

            # Obtener configuración de la base de datos
            mariadb_config = load_mariadb_settings()
            dsn = mariadb_config.get("reader_dsn", "")

            if not dsn:
                logger.warning("⚠ No hay DSN configurado para consultar permisos")
                print("⚠ No hay DSN configurado - usando permisos por defecto")
                self._set_default_permissions()
                return

            logger.info(f"→ Cargando permisos para user_id={self.user_id}")
            print(f"→ Consultando permisos en BD para user_id={self.user_id}")
            engine = create_engine(dsn)

            with engine.connect() as conn:
                # 1. Obtener identity_type_id del usuario desde tabla users
                query_identity = text("""
                    SELECT identity_type_id
                    FROM myllm_core_db.users
                    WHERE user_id = :user_id
                    LIMIT 1
                """)

                result_identity = conn.execute(query_identity, {"user_id": self.user_id})
                row_identity = result_identity.fetchone()

                if not row_identity:
                    logger.warning(f"⚠ No se encontró usuario con user_id={self.user_id}")
                    print(f"⚠ Usuario no encontrado - usando permisos por defecto")
                    self._set_default_permissions()
                    return

                identity_type_id = row_identity[0]
                self.user_identity_type_id = identity_type_id
                logger.info(f"✓ Usuario encontrado: identity_type_id={identity_type_id}")
                print(f"✓ Identity type: {identity_type_id}")

                # 2. Obtener TODOS los permisos desde low_level_permissions
                query_perms = text("""
                    SELECT
                        folder_create, folder_delete, folder_rename, folder_read, folder_list,
                        file_create, file_read, file_update, file_delete, file_list,
                        project_create, project_read, project_update, project_delete, project_list,
                        version_create, version_read, version_update, version_delete, version_list,
                        training_create, training_read, training_update, training_delete,
                        training_start, training_stop,
                        parameters_create, parameters_read, parameters_update, parameters_delete,
                        notifications_create, notifications_read, notifications_update, notifications_delete,
                        user_create, user_read, user_update, user_delete, user_enable, user_disable
                    FROM myllm_core_db.low_level_permissions
                    WHERE id_permissions = :identity_type_id
                    LIMIT 1
                """)

                result_perms = conn.execute(query_perms, {"identity_type_id": identity_type_id})
                row_perms = result_perms.fetchone()

                if not row_perms:
                    logger.warning(f"⚠ No se encontraron permisos para identity_type_id={identity_type_id}")
                    print(f"⚠ No hay permisos en low_level_permissions - usando permisos por defecto")
                    self._set_default_permissions()
                    return

                # 3. Actualizar matriz de permisos con TODOS los valores de la BD
                self.permisos = {
                    # Carpetas
                    "folder_create": bool(row_perms[0]),
                    "folder_delete": bool(row_perms[1]),
                    "folder_rename": bool(row_perms[2]),
                    "folder_read": bool(row_perms[3]),
                    "folder_list": bool(row_perms[4]),
                    # Archivos
                    "file_create": bool(row_perms[5]),
                    "file_read": bool(row_perms[6]),
                    "file_update": bool(row_perms[7]),
                    "file_delete": bool(row_perms[8]),
                    "file_list": bool(row_perms[9]),
                    # Proyectos
                    "project_create": bool(row_perms[10]),
                    "project_read": bool(row_perms[11]),
                    "project_update": bool(row_perms[12]),
                    "project_delete": bool(row_perms[13]),
                    "project_list": bool(row_perms[14]),
                    # Versiones
                    "version_create": bool(row_perms[15]),
                    "version_read": bool(row_perms[16]),
                    "version_update": bool(row_perms[17]),
                    "version_delete": bool(row_perms[18]),
                    "version_list": bool(row_perms[19]),
                    # Entrenamiento
                    "training_create": bool(row_perms[20]),
                    "training_read": bool(row_perms[21]),
                    "training_update": bool(row_perms[22]),
                    "training_delete": bool(row_perms[23]),
                    "training_start": bool(row_perms[24]),
                    "training_stop": bool(row_perms[25]),
                    # Parámetros
                    "parameters_create": bool(row_perms[26]),
                    "parameters_read": bool(row_perms[27]),
                    "parameters_update": bool(row_perms[28]),
                    "parameters_delete": bool(row_perms[29]),
                    # Notificaciones
                    "notifications_create": bool(row_perms[30]),
                    "notifications_read": bool(row_perms[31]),
                    "notifications_update": bool(row_perms[32]),
                    "notifications_delete": bool(row_perms[33]),
                    # Usuarios
                    "user_create": bool(row_perms[34]),
                    "user_read": bool(row_perms[35]),
                    "user_update": bool(row_perms[36]),
                    "user_delete": bool(row_perms[37]),
                    "user_enable": bool(row_perms[38]),
                    "user_disable": bool(row_perms[39]),
                }

                # Determinar si es admin: Solo identity_type_id 1 o 2 pueden gestionar versiones
                self.is_admin = identity_type_id in (1, 2)

                logger.info(
                    f"✓ Permisos cargados para user_id={self.user_id}, "
                    f"identity_type_id={identity_type_id}, is_admin={self.is_admin}"
                )
                logger.info(f"Permisos explorador: folder_create={self.permisos['folder_create']}, "
                           f"file_create={self.permisos['file_create']}, "
                           f"folder_delete={self.permisos['folder_delete']}")

                print(
                    f"✓ Permisos cargados: Identity={identity_type_id}, "
                    f"Admin={self.is_admin}, "
                    f"folder_create={self.permisos['folder_create']}, "
                    f"file_create={self.permisos['file_create']}"
                )

        except Exception as e:
            logger.error(f"✗ Error consultando permisos en BD: {e}")
            print(f"✗ Error consultando permisos: {e}")
            import traceback
            traceback.print_exc()
            # En caso de error, usar permisos por defecto
            self._set_default_permissions()

    def interpretacion_estados(self):
        """
        Aplica la lógica de negocio y restricciones visuales en el explorador
        basándose en los estados de las versiones cargados desde el JSON.
        """
        # 1. Protección estructural básica (Security by Design)
        for item in self.items:
            item.is_protected = (item.depth < 2)
            item.is_blocked = False
        
        # 2. Bloqueo operativo por versión (usando los estados cargados del JSON)
        # Mapeo de estados a labels y colores
        state_labels = {
            "Abierta": ("(Abierta)", "#228B22"),  # Verde bosque
            "Bloqueada": ("(Bloqueada)", "#FF8C00"),  # Naranja oscuro
            "Protegida": ("(Entrenamiento solicitado)", "#00008B"),  # Azul oscuro - DEPRECADO mantener compatibilidad
            "Entrenar": ("(Entrenamiento solicitado)", "#00008B"),  # Azul oscuro - NUEVO estado principal
            "Final": ("(Final)", "#8B0000"),  # Rojo oscuro
        }
        
        for item in self.items:
            if item.depth == 1:
                # Es una carpeta de versión, verificamos su estado en version_states
                version_key = item.name  # ej: "v001"
                version_state_data = self.version_states.get(version_key, {})

                estado = version_state_data.get("state", "Abierta")
                protected = version_state_data.get("protected", False)
                final_c = version_state_data.get("final_c", False)
                final_i = version_state_data.get("final_i", False)

                # Asignamos el label, color y flags
                label, color = state_labels.get(estado, ("", ""))
                item.version_state_label = label
                item.version_state_color = color
                item.is_final_c = final_c
                item.is_final_i = final_i
                # CRÍTICO: Asignar el campo protected de la base de datos
                item.db_protected = protected

                es_bloqueada = protected or (estado != "Abierta")

                if es_bloqueada:
                    # Bloqueamos todos los descendientes de esta versión
                    # IMPORTANTE: NO bloqueamos la carpeta de versión misma (item.is_blocked = False)
                    # para que el menú contextual pueda aparecer y permitir desbloquearla
                    version_id = item.id

                    # Bloqueamos todos los hijos de esta versión
                    for descendant in self.items:
                        if descendant.id.startswith(version_id + "_"):
                            descendant.is_blocked = True
                
                # Actualizamos el tamaño desde el JSON (Solo si no es auditor)
                if not self.is_auditor and version_state_data.get("size", 0) > 0:
                    item.size_str = self._format_size(version_state_data.get("size", 0))
                elif self.is_auditor:
                    item.size_str = "" # Auditores no ven tamaño
        
        # 3. Actualizar visibilidad
        self._update_visibility()

    def acciones(self, accion: str, item: FolderItem):
        """
        Punto de entrada único para ejecutar acciones sobre ficheros/carpetas.

        Validaciones en orden:
        1. Permisos del usuario (desde low_level_permissions)
        2. Restricciones de versión (solo identity_type_id 1 o 2)
        3. Protección de contenido (db_protected)
        4. Protección estructural (is_protected)

        IMPORTANTE: Loggea TODAS las validaciones (éxito y fallo).
        """
        # ============================================================
        # 1. VALIDAR PERMISOS DEL USUARIO
        # ============================================================
        required_permission = get_required_permission(accion, item.item_type)

        if required_permission:
            has_permission = self.permisos.get(required_permission, False)

            if not has_permission:
                logger.warning(
                    f"[PERMISSION DENIED] user_id={self.user_id} "
                    f"identity_type_id={self.user_identity_type_id} "
                    f"accion={accion} permiso={required_permission} "
                    f"item={item.name} type={item.item_type}"
                )
                return rx.toast.error("Operación no permitida")
            else:
                logger.info(
                    f"[PERMISSION OK] user_id={self.user_id} "
                    f"accion={accion} permiso={required_permission} item={item.name}"
                )

        # ============================================================
        # 2. VALIDAR RESTRICCIONES DE VERSIÓN
        # ============================================================
        # Solo identity_type_id 1 (SuperAdmin) o 2 (OrgAdmin) pueden operar con versiones
        version_operations = ["block_version", "unblock_version", "review_version",
                             "abrir_version", "bloquear_version"]

        if accion in version_operations:
            if self.user_identity_type_id not in (1, 2):
                logger.warning(
                    f"[VERSION OPERATION DENIED] user_id={self.user_id} "
                    f"identity_type_id={self.user_identity_type_id} "
                    f"accion={accion} item={item.name}"
                )
                return rx.toast.error("Operación no permitida")
            else:
                logger.info(
                    f"[VERSION OPERATION OK] user_id={self.user_id} "
                    f"identity_type_id={self.user_identity_type_id} "
                    f"accion={accion}"
                )

        # ============================================================
        # 3. VALIDAR PROTECCIÓN DE CONTENIDO (db_protected)
        # ============================================================
        content_actions = ["create_folder", "upload_file"]

        if accion in content_actions:
            # Si el item es la versión misma (depth == 1), verificar directamente
            if item.depth == 1:
                if item.db_protected:
                    logger.warning(
                        f"[PROTECTED VERSION] accion={accion} "
                        f"version={item.name} db_protected=True"
                    )
                    return rx.toast.error("Operación no permitida")

            # Si el item está dentro de una versión (depth > 1), buscar la versión ancestro
            elif item.depth > 1:
                version_item = self._find_version_ancestor(item)
                if version_item and version_item.db_protected:
                    logger.warning(
                        f"[PROTECTED VERSION] accion={accion} "
                        f"version={version_item.name} db_protected=True"
                    )
                    return rx.toast.error("Operación no permitida")

        # ============================================================
        # 4. VALIDAR PROTECCIÓN ESTRUCTURAL (is_protected)
        # ============================================================
        admin_actions = ["block_version", "unblock_version", "review_version"]

        if item.is_protected and accion not in admin_actions and accion not in content_actions:
            logger.warning(
                f"[STRUCTURAL PROTECTION] accion={accion} "
                f"item={item.name} is_protected=True"
            )
            return rx.toast.error("Operación no permitida")

        # ============================================================
        # 5. EJECUTAR ACCIÓN (todas las validaciones pasadas)
        # ============================================================
        logger.info(
            f"[ACTION ALLOWED] user_id={self.user_id} "
            f"accion={accion} item={item.name} type={item.item_type}"
        )

        # Acciones de carpetas
        if accion == "create_folder":
            return self.abrir_dialogo_crear_carpeta(item)
        elif accion == "rename":
            return self.abrir_dialogo_renombrar(item)
        elif accion == "delete":
            return self.abrir_dialogo_confirmar_eliminar(item)
        elif accion == "properties":
            return self.abrir_dialogo_propiedades(item)

        # Acciones de archivos
        elif accion == "upload_file":
            return self.iniciar_subida_archivo(item)
        elif accion == "download":
            return self.iniciar_descarga_archivo(item)
            
        # Acciones Administrativas de Versión
        elif accion == "block_version":
            # Cambiar estado a Bloqueada y activar protección
            version_key = item.name
            if version_key in self.version_states:
                self.version_states[version_key]["state"] = "Bloqueada"
                self.version_states[version_key]["protected"] = True
            self.interpretacion_estados()

        elif accion == "unblock_version":
            # Cambiar estado a Abierta y desactivar protección
            version_key = item.name
            if version_key in self.version_states:
                self.version_states[version_key]["state"] = "Abierta"
                self.version_states[version_key]["protected"] = False
            self.interpretacion_estados()

        elif accion == "review_version":
            # Revertir estado a Abierta y limpiar flags finales
            version_key = item.name
            if version_key in self.version_states:
                self.version_states[version_key]["state"] = "Abierta"
                self.version_states[version_key]["protected"] = False
                self.version_states[version_key]["final_c"] = False
            self.interpretacion_estados()
            return rx.window_alert(f"Versión {version_key} revertida a estado Abierta para revisión.")

    def abrir_version(self, item: FolderItem):
        """Cambia el estado de una versión a 'Abierta' (protected=False) y persiste en BD."""
        version_key = item.name  # ej: "v001"

        # Extraer version_id numérico del version_key
        try:
            version_id = int(version_key.lstrip('v'))
        except ValueError:
            logger.error(f"No se pudo extraer version_id de {version_key}")
            return rx.toast.error(f"Error: formato de versión inválido")

        # Actualizar en memoria
        if version_key in self.version_states:
            self.version_states[version_key]["state"] = "Abierta"
            self.version_states[version_key]["protected"] = False
            logger.info(f"Versión {version_key} cambiada a Abierta en memoria")

        # Persistir en base de datos
        try:
            response = update_version_state(
                project_id=self.id_proyecto,
                version_id=version_id,
                state="Abierta",
                protected=False,
                updated_by_user_id=self.user_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                logger.info(f"Versión {version_key} persistida como Abierta en BD")
                self.interpretacion_estados()
                return rx.toast.success(f"Versión {version_key} abierta")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                logger.error(f"Error al persistir estado: {error_msg}")
                return rx.toast.error(f"Error al guardar: {error_msg}")

        except Exception as e:
            logger.error(f"Excepción al abrir versión: {e}")
            return rx.toast.error(f"Error al guardar cambios")

    def bloquear_version(self, item: FolderItem):
        """Cambia el estado de una versión a 'Bloqueada' (protected=True) y persiste en BD."""
        version_key = item.name  # ej: "v001"

        # Extraer version_id numérico del version_key
        try:
            version_id = int(version_key.lstrip('v'))
        except ValueError:
            logger.error(f"No se pudo extraer version_id de {version_key}")
            return rx.toast.error(f"Error: formato de versión inválido")

        # Actualizar en memoria
        if version_key in self.version_states:
            self.version_states[version_key]["state"] = "Bloqueada"
            self.version_states[version_key]["protected"] = True
            logger.info(f"Versión {version_key} cambiada a Bloqueada en memoria")

        # Persistir en base de datos
        try:
            response = update_version_state(
                project_id=self.id_proyecto,
                version_id=version_id,
                state="Bloqueada",
                protected=True,
                updated_by_user_id=self.user_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                logger.info(f"Versión {version_key} persistida como Bloqueada en BD")
                self.interpretacion_estados()
                return rx.toast.success(f"Versión {version_key} bloqueada")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                logger.error(f"Error al persistir estado: {error_msg}")
                return rx.toast.error(f"Error al guardar: {error_msg}")

        except Exception as e:
            logger.error(f"Excepción al bloquear versión: {e}")
            return rx.toast.error(f"Error al guardar cambios")

    def entrenar_version(self, item: FolderItem):
        """Cambia el estado de una versión a 'Entrenar' (protected=True, final_c=True) y persiste en BD.

        Este es el estado final del flujo del cliente:
        - El cliente solicita que la versión entre en entrenamiento
        - Se protege la versión (solo lectura)
        - Se marca final_c=True para indicar que el cliente ha finalizado su parte
        - El estado es terminal para el cliente (no puede cambiarlo)
        - Solo el backoffice puede cambiar el estado después de esto
        """
        version_key = item.name  # ej: "v001"

        # Extraer version_id numérico del version_key
        try:
            version_id = int(version_key.lstrip('v'))
        except ValueError:
            logger.error(f"No se pudo extraer version_id de {version_key}")
            return rx.toast.error(f"Error: formato de versión inválido")

        # Actualizar en memoria
        if version_key in self.version_states:
            self.version_states[version_key]["state"] = "Entrenar"
            self.version_states[version_key]["protected"] = True
            self.version_states[version_key]["final_c"] = True
            logger.info(f"Versión {version_key} cambiada a Entrenar en memoria")

        # Persistir en base de datos
        try:
            response = update_version_state(
                project_id=self.id_proyecto,
                version_id=version_id,
                state="Entrenar",
                protected=True,
                final_c=True,
                updated_by_user_id=self.user_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                logger.info(f"Versión {version_key} persistida como Entrenar en BD")
                self.interpretacion_estados()
                return rx.toast.success(f"Entrenamiento solicitado para versión {version_key}")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                logger.error(f"Error al persistir estado: {error_msg}")
                return rx.toast.error(f"Error al guardar: {error_msg}")

        except Exception as e:
            logger.error(f"Excepción al solicitar entrenamiento: {e}")
            return rx.toast.error(f"Error al guardar cambios")

    def iniciar_subida_archivo(self, item: FolderItem):
        """Inicia el proceso de subida de archivo.

        1. Extrae project_id y version_id del item
        2. Genera token de subida llamando al middleware
        3. Usa JavaScript para abrir file picker y subir directamente a fmanagement
        """
        try:
            # Usar valores del estado actual
            project_id = self.id_proyecto

            # Encontrar la versión ancestro (depth == 1)
            version_item = self._find_version_ancestor(item)
            if not version_item:
                # Si no hay ancestro, quizás el item mismo es la versión (depth == 1)
                if item.depth == 1:
                    version_item = item
                else:
                    logger.error(f"No se encontró versión para item: {item.name} (depth={item.depth})")
                    return rx.toast.error("Error: no se pudo identificar la versión")

            # Extraer version_id del nombre de la versión (ej: "v001" -> 1)
            version_name = version_item.name
            if not version_name.startswith("v") or not version_name[1:].isdigit():
                logger.error(f"Nombre de versión inválido: {version_name}")
                return rx.toast.error("Error: formato de versión inválido")

            version_id = int(version_name.lstrip('v'))

            # Calcular relative_path desde la versión hasta el item actual
            # Recorremos desde el item hacia arriba hasta llegar a la versión
            path_parts = []
            current = item
            while current.parent_id != "" and current.depth > version_item.depth:
                path_parts.insert(0, current.name)
                # Buscar el padre
                parent = next((p for p in self.items if p.id == current.parent_id), None)
                if not parent or parent.id == version_item.id:
                    break
                current = parent

            relative_path = "/".join(path_parts) if path_parts else ""

            logger.info(f"Generando token de subida: project_id={project_id}, version_id={version_id}, path={relative_path}")

            # Generar token de subida
            response = generate_file_upload_token(
                project_id=project_id,
                version_id=version_id,
                relative_path=relative_path,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if not response.get("success"):
                error_msg = response.get("message") or response.get("detail", "Error al generar token")
                logger.error(f"Error generando token: {error_msg}")
                return rx.toast.error(f"Error: {error_msg}")

            token = response.get("token")
            fmanagement_url = response.get("fmanagement_url")

            if not token or not fmanagement_url:
                logger.error("Respuesta incompleta del servidor")
                return rx.toast.error("Error: respuesta incompleta del servidor")

            # Usar JavaScript para abrir file picker y subir el archivo
            upload_script = f"""
            new Promise((resolve) => {{
                const input = document.createElement('input');
                input.type = 'file';
                input.onchange = async (e) => {{
                    const file = e.target.files[0];
                    if (!file) {{ resolve({{"status": "cancelled"}}); return; }}

                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('relative_path', '{relative_path}');

                    try {{
                        const response = await fetch('{fmanagement_url}/upload', {{
                            method: 'POST',
                            headers: {{
                                'Authorization': 'Bearer {token}'
                            }},
                            body: formData
                        }});

                        const result = await response.json();
                        if (response.ok) {{
                            resolve({{"status": "success", "filename": file.name}});
                        }} else {{
                            resolve({{"status": "error", "error": result.error || "Error desconocido"}});
                        }}
                    }} catch (error) {{
                        resolve({{"status": "error", "error": error.message}});
                    }}
                }};
                input.click();
            }})
            """

            return rx.call_script(
                upload_script,
                callback=type(self).on_upload_complete,
            )

        except Exception as e:
            logger.error(f"Error en iniciar_subida_archivo: {e}")
            return rx.toast.error(f"Error: {str(e)}")

    def on_upload_complete(self, result):
        """Callback tras completar la subida de archivo vía JavaScript.

        Recibe el resultado del Promise y refresca el explorador sin recargar la página.
        """
        if not isinstance(result, dict):
            return

        status = result.get("status", "")

        if status == "success":
            filename = result.get("filename", "")
            logger.info("Upload completado: %s — refrescando explorador", filename)
            self.load_from_api()
            return rx.toast.success(f"Archivo subido: {filename}")

        if status == "error":
            error = result.get("error", "Error desconocido")
            logger.error("Upload fallido: %s", error)
            return rx.toast.error(f"Error al subir: {error}")

        # status == "cancelled" or unknown: no action

    def iniciar_descarga_archivo(self, item: FolderItem):
        """Inicia el proceso de descarga de archivo.

        1. Extrae project_id, version_id y filename del item
        2. Genera token de descarga llamando al middleware
        3. Usa JavaScript para iniciar la descarga desde fmanagement
        """
        try:
            # Verificar que es un archivo
            if item.item_type != "file":
                logger.error(f"Item no es un archivo: {item.name}")
                return rx.toast.error("Error: solo se pueden descargar archivos")

            # Usar valores del estado actual
            project_id = self.id_proyecto

            # Encontrar la versión ancestro (depth == 1)
            version_item = self._find_version_ancestor(item)
            if not version_item:
                logger.error(f"No se encontró versión para item: {item.name}")
                return rx.toast.error("Error: no se pudo identificar la versión")

            # Extraer version_id del nombre de la versión
            version_name = version_item.name
            if not version_name.startswith("v") or not version_name[1:].isdigit():
                logger.error(f"Nombre de versión inválido: {version_name}")
                return rx.toast.error("Error: formato de versión inválido")

            version_id = int(version_name.lstrip('v'))

            # Calcular relative_path (sin incluir el nombre del archivo)
            # Recorremos desde el padre del archivo hacia arriba hasta llegar a la versión
            path_parts = []
            if item.parent_id != "":
                parent = next((p for p in self.items if p.id == item.parent_id), None)
                current = parent
                while current and current.parent_id != "" and current.depth > version_item.depth:
                    path_parts.insert(0, current.name)
                    parent = next((p for p in self.items if p.id == current.parent_id), None)
                    if not parent or parent.id == version_item.id:
                        break
                    current = parent

            relative_path = "/".join(path_parts) if path_parts else ""
            filename = item.name

            logger.info(f"Generando token de descarga: project_id={project_id}, version_id={version_id}, filename={filename}, path={relative_path}")

            # Generar token de descarga
            response = generate_file_download_token(
                project_id=project_id,
                version_id=version_id,
                filename=filename,
                relative_path=relative_path,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            # Verificar si hay tokens refrescados y actualizarlos
            from adapters.api_client import get_refreshed_tokens, clear_refreshed_tokens
            refreshed = get_refreshed_tokens()
            if refreshed:
                logger.info("[AUTO-REFRESH] Actualizando tokens en el estado después de auto-refresh")
                self.access_token = refreshed.get("access_token", self.access_token)
                self.session_token = refreshed.get("session_token", self.session_token)
                clear_refreshed_tokens()

            if not response.get("success"):
                error_msg = response.get("message") or response.get("detail", "Error al generar token")
                logger.error(f"Error generando token: {error_msg}")
                return rx.toast.error(f"Error: {error_msg}")

            download_url = response.get("download_url")

            if not download_url:
                logger.error("Respuesta incompleta del servidor")
                return rx.toast.error("Error: respuesta incompleta del servidor")

            # Usar JavaScript para iniciar la descarga
            download_script = f"""
            (function() {{
                const link = document.createElement('a');
                link.href = '{download_url}';
                link.download = '{filename}';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }})();
            """

            logger.info(f"Iniciando descarga de {filename}")
            return rx.call_script(download_script)

        except Exception as e:
            logger.error(f"Error en iniciar_descarga_archivo: {e}")
            return rx.toast.error(f"Error: {str(e)}")

    # ========================================================================
    # Métodos para diálogos y acciones de carpetas/archivos
    # ========================================================================

    def abrir_dialogo_crear_carpeta(self, item: FolderItem):
        """Abre el diálogo para crear una nueva carpeta."""
        self.current_action_item = item
        self.dialog_input_value = ""
        self.show_create_folder_dialog = True

    def cerrar_dialogo_crear_carpeta(self):
        """Cierra el diálogo de crear carpeta."""
        self.show_create_folder_dialog = False
        self.dialog_input_value = ""
        self.current_action_item = None

    def ejecutar_crear_carpeta(self):
        """Ejecuta la creación de carpeta."""
        if not self.dialog_input_value or not self.current_action_item:
            return rx.toast.error("Debe ingresar un nombre para la carpeta")

        try:
            item = self.current_action_item
            folder_name = self.dialog_input_value.strip()

            project_id = self.id_proyecto

            # Identificar la versión usando el método _find_version_ancestor
            # Si el item es la versión misma (depth == 1)
            if item.depth == 1:
                version_item = item
            # Si el item está dentro de una versión (depth > 1)
            elif item.depth > 1:
                version_item = self._find_version_ancestor(item)
                if not version_item:
                    return rx.toast.error("No se pudo identificar la versión ancestro")
            else:
                return rx.toast.error("No se puede crear carpeta en este nivel")

            # Extraer el número de versión del nombre (ej: "v001" -> 1)
            version_name = version_item.name
            if version_name.startswith("v") and version_name[1:].isdigit():
                version_id = int(version_name.lstrip('v'))
            else:
                return rx.toast.error(f"Formato de versión inválido: {version_name}")

            # Construir la ruta relativa desde la versión hasta el item actual
            # Si estamos en la versión misma, la ruta es vacía
            if item.depth == 1:
                folder_path = ""
            else:
                # Construir la ruta navegando desde el item hacia arriba hasta la versión
                path_parts = []
                current = item
                while current.depth > 1:
                    path_parts.insert(0, current.name)
                    parent = next((p for p in self.items if p.id == current.parent_id), None)
                    if not parent:
                        break
                    current = parent
                folder_path = "/".join(path_parts) if path_parts else ""

            logger.info(f"Creando carpeta: {folder_name} en {folder_path}")

            # Llamar a la API
            response = fmanagement_create_folder(
                org_id=self.id_organizacion,
                project_id=project_id,
                version_id=version_id,
                folder_path=folder_path,
                folder_name=folder_name,
                user_id=self.user_id,
                identity_type_id=self.user_identity_type_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            self.cerrar_dialogo_crear_carpeta()

            if response.get("success") or response.get("status") == "success":
                logger.info(f"Carpeta creada: {folder_name}")
                # Recargar el explorador desde fmanagement (/fmo/list)
                self.load_from_api()
                return rx.toast.success(f"Carpeta '{folder_name}' creada exitosamente")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                return rx.toast.error(f"Error: {error_msg}")

        except Exception as e:
            logger.error(f"Error en ejecutar_crear_carpeta: {e}")
            self.cerrar_dialogo_crear_carpeta()
            return rx.toast.error(f"Error: {str(e)}")

    def abrir_dialogo_renombrar(self, item: FolderItem):
        """Abre el diálogo para renombrar."""
        self.current_action_item = item
        self.dialog_input_value = item.name
        self.show_rename_dialog = True

    def cerrar_dialogo_renombrar(self):
        """Cierra el diálogo de renombrar."""
        self.show_rename_dialog = False
        self.dialog_input_value = ""
        self.current_action_item = None

    def ejecutar_renombrar(self):
        """Ejecuta el renombrado de carpeta o archivo."""
        if not self.dialog_input_value or not self.current_action_item:
            return rx.toast.error("Debe ingresar un nuevo nombre")

        try:
            item = self.current_action_item
            new_name = self.dialog_input_value.strip()

            if new_name == item.name:
                self.cerrar_dialogo_renombrar()
                return rx.toast.info("El nombre no ha cambiado")

            project_id = self.id_proyecto

            # Identificar la versión usando el método _find_version_ancestor
            # Si el item es la versión misma (depth == 1)
            if item.depth == 1:
                version_item = item
            # Si el item está dentro de una versión (depth > 1)
            elif item.depth > 1:
                version_item = self._find_version_ancestor(item)
                if not version_item:
                    return rx.toast.error("No se pudo identificar la versión ancestro")
            else:
                return rx.toast.error("No se puede renombrar este elemento")

            # Extraer el número de versión del nombre (ej: "v001" -> 1)
            version_name = version_item.name
            if version_name.startswith("v") and version_name[1:].isdigit():
                version_id = int(version_name.lstrip('v'))
            else:
                return rx.toast.error(f"Formato de versión inválido: {version_name}")

            # Construir la ruta relativa (sin incluir el nombre del item que se va a renombrar)
            if item.depth == 1:
                # No se debe permitir renombrar la versión misma
                return rx.toast.error("No se puede renombrar la versión")
            else:
                # Construir la ruta navegando desde el item hacia arriba hasta la versión
                path_parts = []
                current = item
                # Subir hasta el padre
                parent = next((p for p in self.items if p.id == current.parent_id), None)
                if parent and parent.depth > 1:
                    # Continuar subiendo hasta llegar a la versión
                    while parent.depth > 1:
                        path_parts.insert(0, parent.name)
                        grandparent = next((p for p in self.items if p.id == parent.parent_id), None)
                        if not grandparent:
                            break
                        parent = grandparent
                folder_path = "/".join(path_parts) if path_parts else ""

            logger.info(f"Renombrando {item.name} a {new_name}")

            # Llamar a la API según si es carpeta o archivo
            if item.item_type == "folder":
                response = fmanagement_rename_folder(
                    org_id=self.id_organizacion,
                    project_id=project_id,
                    version_id=version_id,
                    folder_path=folder_path,
                    old_name=item.name,
                    new_name=new_name,
                    user_id=self.user_id,
                    identity_type_id=self.user_identity_type_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
            else:  # archivo
                response = fmanagement_rename_file(
                    org_id=self.id_organizacion,
                    project_id=project_id,
                    version_id=version_id,
                    file_path=folder_path,
                    old_filename=item.name,
                    new_filename=new_name,
                    user_id=self.user_id,
                    identity_type_id=self.user_identity_type_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )

            self.cerrar_dialogo_renombrar()

            if response.get("success") or response.get("message"):
                logger.info(f"Renombrado exitoso: {item.name} -> {new_name}")
                # Recargar el explorador desde fmanagement (/fmo/list)
                self.load_from_api()
                return rx.toast.success(f"Renombrado a '{new_name}' exitosamente")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                return rx.toast.error(f"Error: {error_msg}")

        except Exception as e:
            logger.error(f"Error en ejecutar_renombrar: {e}")
            self.cerrar_dialogo_renombrar()
            return rx.toast.error(f"Error: {str(e)}")

    def abrir_dialogo_confirmar_eliminar(self, item: FolderItem):
        """Abre el diálogo de confirmación para eliminar."""
        self.current_action_item = item
        self.show_delete_confirm_dialog = True

    def cerrar_dialogo_eliminar(self):
        """Cierra el diálogo de eliminar."""
        self.show_delete_confirm_dialog = False
        self.current_action_item = None

    def ejecutar_eliminar(self):
        """Ejecuta la eliminación de carpeta o archivo."""
        if not self.current_action_item:
            return rx.toast.error("No hay elemento seleccionado")

        try:
            item = self.current_action_item
            project_id = self.id_proyecto

            # Identificar la versión usando el método _find_version_ancestor
            # Si el item es la versión misma (depth == 1)
            if item.depth == 1:
                version_item = item
            # Si el item está dentro de una versión (depth > 1)
            elif item.depth > 1:
                version_item = self._find_version_ancestor(item)
                if not version_item:
                    return rx.toast.error("No se pudo identificar la versión ancestro")
            else:
                return rx.toast.error("No se puede eliminar este elemento")

            # Extraer el número de versión del nombre (ej: "v001" -> 1)
            version_name = version_item.name
            if version_name.startswith("v") and version_name[1:].isdigit():
                version_id = int(version_name.lstrip('v'))
            else:
                return rx.toast.error(f"Formato de versión inválido: {version_name}")

            # Construir la ruta relativa (sin incluir el nombre del item que se va a eliminar)
            if item.depth == 1:
                # No se debe permitir eliminar la versión misma
                return rx.toast.error("No se puede eliminar la versión directamente")
            else:
                # Construir la ruta navegando desde el item hacia arriba hasta la versión
                path_parts = []
                current = item
                # Subir hasta el padre
                parent = next((p for p in self.items if p.id == current.parent_id), None)
                if parent and parent.depth > 1:
                    # Continuar subiendo hasta llegar a la versión
                    while parent.depth > 1:
                        path_parts.insert(0, parent.name)
                        grandparent = next((p for p in self.items if p.id == parent.parent_id), None)
                        if not grandparent:
                            break
                        parent = grandparent

                if item.item_type == "folder":
                    folder_path = "/".join(path_parts) if path_parts else ""
                    folder_name = item.name
                else:  # archivo
                    file_path = "/".join(path_parts) if path_parts else ""

            logger.info(f"Eliminando: {item.name}")

            # Llamar a la API según si es carpeta o archivo
            if item.item_type == "folder":
                response = fmanagement_delete_folder(
                    org_id=self.id_organizacion,
                    project_id=project_id,
                    version_id=version_id,
                    folder_path=folder_path,
                    folder_name=folder_name,
                    user_id=self.user_id,
                    identity_type_id=self.user_identity_type_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
            else:  # archivo
                response = fmanagement_delete_file(
                    org_id=self.id_organizacion,
                    project_id=project_id,
                    version_id=version_id,
                    file_path=file_path,
                    filename=item.name,
                    user_id=self.user_id,
                    identity_type_id=self.user_identity_type_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )

            self.cerrar_dialogo_eliminar()

            if response.get("success") or response.get("status") == "success":
                logger.info(f"Eliminado exitosamente: {item.name}")
                # Recargar el explorador desde fmanagement (/fmo/list)
                self.load_from_api()
                return rx.toast.success(f"'{item.name}' eliminado exitosamente")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                return rx.toast.error(f"Error: {error_msg}")

        except Exception as e:
            logger.error(f"Error en ejecutar_eliminar: {e}")
            self.cerrar_dialogo_eliminar()
            return rx.toast.error(f"Error: {str(e)}")

    def abrir_dialogo_propiedades(self, item: FolderItem):
        """Abre el diálogo de propiedades."""
        self.current_action_item = item
        self.properties_info = "Cargando propiedades..."
        self.show_properties_dialog = True
        # TODO: Implementar llamada a fmanagement para obtener info con comando 'file'
        return self.cargar_propiedades()

    def cerrar_dialogo_propiedades(self):
        """Cierra el diálogo de propiedades."""
        self.show_properties_dialog = False
        self.properties_info = ""
        self.current_action_item = None

    def cargar_propiedades(self):
        """Carga las propiedades del elemento usando el comando 'file' del SO."""
        if not self.current_action_item:
            return rx.toast.error("No hay elemento seleccionado")

        try:
            item = self.current_action_item
            project_id = self.id_proyecto

            # Identificar la versión usando el método _find_version_ancestor
            # Si el item es la versión misma (depth == 1)
            if item.depth == 1:
                version_item = item
            # Si el item está dentro de una versión (depth > 1)
            elif item.depth > 1:
                version_item = self._find_version_ancestor(item)
                if not version_item:
                    self.properties_info = "Error: No se pudo identificar la versión ancestro"
                    return rx.toast.error("No se pudo identificar la versión ancestro")
            else:
                self.properties_info = "Error: Nivel inválido para obtener propiedades"
                return rx.toast.error("No se pueden obtener propiedades de este elemento")

            # Extraer el número de versión del nombre (ej: "v001" -> 1)
            version_name = version_item.name
            if version_name.startswith("v") and version_name[1:].isdigit():
                version_id = int(version_name.lstrip('v'))
            else:
                self.properties_info = f"Error: Formato de versión inválido: {version_name}"
                return rx.toast.error(f"Formato de versión inválido: {version_name}")

            # Construir la ruta relativa
            if item.depth == 1:
                # Es la versión misma
                item_path = ""
                item_name = "" if item.item_type == "folder" else item.name
            else:
                # Construir la ruta navegando desde el item hacia arriba hasta la versión
                path_parts = []
                current = item
                while current.depth > 1:
                    if item.item_type == "folder":
                        # Para carpetas, incluir el nombre de la carpeta en la ruta
                        path_parts.insert(0, current.name)
                    else:
                        # Para archivos, no incluir el nombre del archivo en la ruta
                        if current.id != item.id:
                            path_parts.insert(0, current.name)
                    parent = next((p for p in self.items if p.id == current.parent_id), None)
                    if not parent or parent.depth <= 1:
                        break
                    current = parent

                item_path = "/".join(path_parts) if path_parts else ""
                item_name = "" if item.item_type == "folder" else item.name

            logger.info(f"Obteniendo propiedades de: {item.name}")

            # Llamar a la API
            response = fmanagement_get_properties(
                org_id=self.id_organizacion,
                project_id=project_id,
                version_id=version_id,
                item_path=item_path,
                item_name=item_name,
                is_folder=(item.item_type == "folder"),
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success") or response.get("status") == "success":
                # Formatear la información
                data = response.get("data") or response

                # Sanitizar el output del comando 'file' para remover la ruta interna
                file_output = data.get('file_output', 'No disponible')
                if file_output and ':' in file_output:
                    # El comando 'file' retorna: /ruta/completa/archivo.txt: tipo
                    # Extraemos solo la parte después de ':'
                    file_output = file_output.split(':', 1)[1].strip()

                info = f"═══ PROPIEDADES ═══\n\n"
                info += f"Nombre: {data.get('name', item.name)}\n"
                info += f"Tipo: {'Carpeta' if data.get('is_dir') else 'Archivo'}\n"
                info += f"Tamaño: {self._format_size(data.get('size_bytes', 0))}\n"
                info += f"Permisos: {data.get('mode', 'N/A')}\n"
                info += f"Modificado: {data.get('mod_time', 'N/A')}\n\n"
                info += f"═══ INFORMACIÓN DEL SISTEMA ═══\n\n"
                info += f"{file_output}\n"

                self.properties_info = info
                return rx.toast.success("Propiedades cargadas")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                self.properties_info = f"Error al obtener propiedades: {error_msg}"
                return rx.toast.error(f"Error: {error_msg}")

        except Exception as e:
            logger.error(f"Error en cargar_propiedades: {e}")
            self.properties_info = f"Error: {str(e)}"
            return rx.toast.error(f"Error: {str(e)}")

    def set_version_protected(self, val: bool):
        """Cambia la protección de la versión seleccionada.

        Nota: En diseño multi-versión, este método ya no tiene una versión activa.
        Considerar remover o rediseñar para trabajar con versiones específicas.
        """
        # TODO: Rediseñar para multi-versión
        logger.warning("set_version_protected llamado pero no hay versión activa en multi-versión")
        return rx.toast.warning("Función no disponible en modo multi-versión")

    @rx.var
    def available_status_options(self) -> list[str]:
        """
        Opciones de estado disponibles en Frontend.
        Frontend: Solo Abierta y Bloqueada.
        """
        return ["Abierta", "Bloqueada"]

    def set_version_final_i(self, val: bool):
        self.version_final_i = val
        self.interpretacion_estados()

    def toggle_permiso(self, nombre_permiso: str, valor: bool):
        """Actualiza un permiso específico en la matriz de memoria."""
        self.permisos[nombre_permiso] = valor
        self.interpretacion_estados()

    def solicitar_entrenamiento(self):
        """
        El cliente solicita entrenamiento.

        Nota: En diseño multi-versión, este método ya no tiene una versión activa.
        Considerar remover o rediseñar para trabajar con versiones específicas.
        """
        # TODO: Rediseñar para multi-versión
        logger.warning("solicitar_entrenamiento llamado pero no hay versión activa en multi-versión")
        return rx.toast.warning("Función no disponible en modo multi-versión. Use el menú contextual de la versión.")

    def confirmar_entrenamiento(self):
        """
        Documentación preparada para entrenamiento.

        Nota: En diseño multi-versión, este método ya no tiene una versión activa.
        Considerar remover o rediseñar para trabajar con versiones específicas.
        """
        # TODO: Rediseñar para multi-versión
        logger.warning("confirmar_entrenamiento llamado pero no hay versión activa en multi-versión")
        return rx.toast.warning("Función no disponible en modo multi-versión. Use el menú contextual de la versión.")

    # Gestión de Menú Contextual
    context_menu_item_id: str = ""

    def set_context_menu_item(self, item_id: str):
        """Establece el item actual para el menú contextual."""
        self.context_menu_item_id = item_id
        self.select_item(item_id)

    @rx.var
    def context_menu_item(self) -> FolderItem:
        """Devuelve el item sobre el que se activó el menú contextual."""
        for item in self.items:
            if item.id == self.context_menu_item_id:
                return item
        return FolderItem(id="", name="", depth=0)

    @rx.var
    def selected_item(self) -> FolderItem:
        """Devuelve el item seleccionado actualmente."""
        for item in self.items:
            if item.id == self.selected_item_id:
                return item
        return FolderItem(id="", name="", depth=0)

    def select_item(self, item_id: str):
        """
        Marca un elemento como seleccionado.
        En el diseño multi-versión, solo marca el item sin cambiar estados globales.
        """
        self.selected_item_id = item_id

    def load_all_version_states(self):
        """
        Carga los estados de todas las versiones del proyecto desde la API.

        Obtiene los estados desde version_states tabla vía API del backend.
        """
        try:
            # Obtener versiones del árbol ya cargado desde disco (NO desde BD)
            # Los items con depth==1 son las carpetas de versión (v001, v002, etc.)
            import re as _re
            version_names = sorted([
                item.name for item in self.items
                if item.depth == 1 and _re.match(r'^v\d{3}$', item.name)
            ])

            if not version_names:
                logger.warning(f"No se encontraron versiones en el árbol para proyecto {self.id_proyecto}")
                return

            logger.info(f"Versiones en árbol: {version_names}")

            # Limpiar diccionario de estados
            self.version_states = {}

            # Para cada versión del árbol, obtener su estado desde la API
            from adapters.api_client import get_version_state

            for version_key in version_names:
                version_id = int(version_key[1:])  # "v001" → 1

                state_response = get_version_state(
                    project_id=self.id_proyecto,
                    version_id=version_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )

                if state_response.get("success"):
                    state_data = state_response.get("data", {}) if state_response.get("data") else state_response.get("state", {})
                    self.version_states[version_key] = {
                        "id_organizacion": state_data.get("id_organizacion", self.id_organizacion),
                        "id_proyecto": state_data.get("id_proyecto", self.id_proyecto),
                        "state": state_data.get("state", "Abierta"),
                        "protected": state_data.get("protected", False),
                        "size": state_data.get("size_bytes", state_data.get("size", 0)),
                        "final_c": state_data.get("final_c", False),
                        "final_i": state_data.get("final_i", False),
                    }
                else:
                    # Valores por defecto si falla la carga
                    self.version_states[version_key] = {
                        "id_organizacion": self.id_organizacion,
                        "id_proyecto": self.id_proyecto,
                        "state": "Abierta",
                        "protected": False,
                        "size": 0,
                        "final_c": False,
                        "final_i": False,
                    }

            logger.info(f"Estados de versiones cargados: {list(self.version_states.keys())}")

            # Aplicar los estados a los items del explorador
            self.interpretacion_estados()

        except Exception as e:
            logger.error(f"Error cargando estados de versiones: {e}")
            print(f"Error cargando estados de versiones: {e}")

    def reload_project_with_tokens(
        self,
        project_id: int,
        org_id: int,
        access_token: str,
        session_token: str,
        user_id: int = 0,
        identity_type_id: int = 0,
    ):
        """Recarga el explorador con un nuevo proyecto.

        Args:
            project_id: ID del proyecto a cargar
            org_id: ID de la organización
            access_token: Token de acceso
            session_token: Token de sesión
            user_id: ID del usuario (requerido para operaciones CRUD)
            identity_type_id: Tipo de identidad del usuario (requerido para permisos)
        """
        logger.info(f"Recargando explorador para proyecto {project_id}...")

        # Limpiar estado anterior
        self.items = []
        self.fmanagementlist = {}
        self.version_states = {}
        self.error_message = ""

        # Actualizar IDs y tokens
        self.id_proyecto = project_id
        self.id_organizacion = org_id
        self.access_token = access_token
        self.session_token = session_token
        self.user_id = user_id
        self.user_identity_type_id = identity_type_id

        logger.info(f"✓ Contexto de usuario: user_id={self.user_id}, identity_type_id={self.user_identity_type_id}")
        print(f"✓ Contexto de usuario: user_id={self.user_id}, identity_type_id={self.user_identity_type_id}")

        # Recargar permisos para el nuevo proyecto
        self._load_permissions_from_database()

        # Cargar desde API
        if self.access_token and self.session_token and self.id_proyecto > 0:
            logger.info(f"Cargando proyecto {self.id_proyecto} desde API")
            self.load_from_api()
        else:
            logger.warning("Tokens no disponibles, no se puede cargar desde API")

    def init_page(
        self,
        project_id: int = 0,
        user_id: int = 0,
        identity_type_id: int = 0,
        org_id: int = 0,
        access_token: str = "",
        session_token: str = "",
    ):
        """Inicializa los datos al cargar la página.

        Args:
            project_id: ID del proyecto a cargar (con todas sus versiones)
            user_id: ID del usuario (opcional, si no se pasa intenta obtenerlo del MainState)
            identity_type_id: Tipo de identidad del usuario (opcional)
            org_id: ID de la organización (opcional)
            access_token: Token de acceso (opcional)
            session_token: Token de sesión (opcional)
        """
        logger.info(f"Inicializando página Explorador para proyecto {project_id}...")

        # Guardar project_id
        if project_id > 0:
            self.id_proyecto = project_id

        # Si se pasaron explícitamente user_id/identity_type_id, usarlos
        if user_id > 0:
            self.user_id = user_id
            self.user_identity_type_id = identity_type_id
            if org_id > 0:
                self.id_organizacion = org_id
            if access_token:
                self.access_token = access_token
            if session_token:
                self.session_token = session_token
            logger.info(f"✓ Contexto de usuario explícito: user_id={self.user_id}, identity_type_id={self.user_identity_type_id}")
            print(f"✓ Contexto de usuario explícito: user_id={self.user_id}, identity_type_id={self.user_identity_type_id}")
        else:
            # Cargar perfil de seguridad para obtener datos del MainState
            self.load_security_profile()

        # Intentar cargar desde API si tenemos tokens, sino usar JSON de demo
        if self.access_token and self.session_token and self.id_proyecto > 0:
            logger.info(f"Cargando proyecto {self.id_proyecto} desde API (modo producción)")
            self.load_from_api()
        else:
            logger.info("Cargando desde JSON (modo demo - sin tokens)")
            self.load_from_json()

        # Aplicar interpretación de estados
        self.interpretacion_estados()

    def load_from_json(self):
        """Carga los datos desde el fichero demo data/proyecto.json."""
        try:
            # En producción esto sería una llamada a API
            with open("data/proyecto.json", "r") as f:
                self.fmanagementlist = json.load(f)
            self.process_fmanagementlist()
        except Exception as e:
            print(f"Error cargando JSON: {e}")

    def load_from_api(self):
        """Carga todas las versiones del proyecto desde fmanagement."""
        try:
            self.is_loading = True
            self.error_message = ""
            logger.info(f"Cargando todas las versiones del proyecto: org={self.id_organizacion}, prj={self.id_proyecto}")

            # Generar nombres de carpetas
            org_folder = f"ORG{str(self.id_organizacion).zfill(5)}"
            prj_folder = f"PRJ{str(self.id_proyecto).zfill(5)}"

            # Llamar al adaptador que carga todas las versiones
            response = fmanagement_list_all_project_versions(
                org_id=self.id_organizacion,
                project_id=self.id_proyecto,
                org_folder=org_folder,
                prj_folder=prj_folder,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            # Verificar respuesta
            if response.get("status") == "success":
                self.fmanagementlist = response
                self.process_fmanagementlist()

                # Cargar estados de versión desde la API
                self.load_all_version_states()

                # Verificar que los datos se cargaron correctamente
                items_count = len(self.items) if self.items is not None else 0
                states_count = len(self.version_states) if self.version_states is not None else 0
                logger.info(f"Datos cargados exitosamente: {items_count} items totales")
                print(f"✓ Explorador cargado: {items_count} items, {states_count} versiones")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido al cargar datos")
                self.error_message = error_msg
                logger.error(f"Error al cargar datos: {error_msg}")
                print(f"✗ Error al cargar explorador: {error_msg}")

        except Exception as e:
            self.error_message = f"Error al cargar datos: {str(e)}"
            logger.error(f"Excepción al cargar desde API: {e}")
            print(f"✗ Excepción al cargar explorador: {e}")
        finally:
            self.is_loading = False

    def process_fmanagementlist(self):
        """Procesa la estructura fmanagementlist para aplanarla con reglas de seguridad y tamaños."""
        if not self.fmanagementlist or "items" not in self.fmanagementlist:
            return

        self.items = []
        self._flatten_recursive(self.fmanagementlist["items"])
        self._update_visibility()

    def _format_size(self, bytes_val):
        """Formatea bytes a la unidad más adecuada."""
        if not bytes_val: return ""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"

    def _flatten_recursive(self, json_items, depth=0, parent_id=""):
        """Función interna para aplanar el JSON marcando niveles protegidos y capturando tamaños."""
        for i, item in enumerate(json_items):
            item_id = f"{parent_id}_{i}" if parent_id else str(i)
            is_dir = item.get("is_dir", True)

            # Niveles 0 (Proyecto) y 1 (Versión) están protegidos (Security by Design)
            is_protected = depth < 2

            # Gestionar tamaño
            bytes_val = item.get("size_bytes", 0)
            size_str = self._format_size(bytes_val) # Permitimos tamaño en ficheros y carpetas

            # Check if item has children (must check for None before len())
            item_children = item.get("items")
            has_children = is_dir and item_children is not None and len(item_children) > 0

            new_item = FolderItem(
                id=item_id,
                name=item.get("name", "unnamed"),
                depth=depth,
                parent_id=parent_id,
                is_expanded=depth < 1,
                has_children=has_children,
                item_type="folder" if is_dir else "file",
                is_visible=True,
                is_protected=is_protected,
                size_str=size_str,
                metadata=item
            )
            self.items.append(new_item)

            # Recurse into children only if they exist and are not None
            if is_dir and item_children is not None:
                self._flatten_recursive(item_children, depth + 1, item_id)

    def toggle_folder(self, item_id: str):
        """Cambia el estado de expansión y actualiza la visibilidad de los hijos."""
        for item in self.items:
            if item.id == item_id:
                item.is_expanded = not item.is_expanded
                break
        
        self._update_visibility()

    def _update_visibility(self):
        """Ajusta la visibilidad de todos los items basándose en la expansión de sus padres."""
        # Un mapa rápido para saber si un padre está expandido y es visible
        # Los elementos raíz (sin parent_id) siempre son visibles
        for item in self.items:
            if item.parent_id == "":
                item.is_visible = True
            else:
                # Buscamos al padre
                parent = next((p for p in self.items if p.id == item.parent_id), None)
                if parent:
                    item.is_visible = parent.is_visible and parent.is_expanded
                else:
                    item.is_visible = False

    def _find_version_ancestor(self, item: FolderItem) -> FolderItem | None:
        """Encuentra la versión ancestro (depth == 1) de un item."""
        # Buscar en la jerarquía hacia arriba hasta encontrar depth == 1
        current_item = item
        while current_item.parent_id != "":
            parent = next((p for p in self.items if p.id == current_item.parent_id), None)
            if not parent:
                break
            if parent.depth == 1:
                return parent
            current_item = parent
        return None

def render_item(item: FolderItem) -> rx.Component:
    """Renderiza una única fila del explorador."""
    return rx.cond(
        item.is_visible,
        rx.hstack(
            # Espaciador de niveles (Jerarquía)
            rx.box(width=(item.depth * 20).to(str) + "px"),
            
            # Botón de expansión (+/-)
            rx.cond(
                item.has_children,
                rx.box(
                    rx.icon(
                        tag=rx.cond(item.is_expanded, "minus", "plus"),
                        size=10,
                        color="#444",
                    ),
                    border="1px solid #999",
                    bg="white",
                    width="14px",
                    height="14px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    cursor="pointer",
                    on_click=lambda: ExploradorState.toggle_folder(item.id),
                    margin_right="6px",
                ),
                rx.box(width="20px") # Espacio para alinear si no hay botón
            ),
            
            # Icono (Carpeta o Fichero con extensión personalizada)
            rx.cond(
                item.item_type == "folder",
                rx.icon(tag="folder", fill="#F8D775", color="#C6A15B", size=24),
                rx.cond(
                    item.name.contains(".txt"),
                    rx.image(src="/txt_icon.png", width="24px", height="24px", object_fit="contain"),
                    rx.cond(
                        item.name.contains(".go"),
                        rx.icon(tag="file-code-2", color="#00ADD8", size=24),
                        rx.cond(
                            item.name.contains(".md"),
                            rx.icon(tag="book-open", color="#000", size=24),
                            rx.cond(
                                item.name.contains(".tiff"),
                                rx.image(src="/tiff_icon.png", width="24px", height="24px", object_fit="contain"),
                                rx.cond(
                                    item.name.contains(".svg"),
                                    rx.image(src="/svg_icon.png", width="24px", height="24px", object_fit="contain"),
                                    rx.cond(
                                        item.name.contains(".html"),
                                        rx.image(src="/html_icon.png", width="24px", height="24px", object_fit="contain"),
                                        rx.cond(
                                            item.name.contains(".pdf"),
                                            rx.image(src="/pdf_icon.png", width="24px", height="24px", object_fit="contain"),
                                            rx.cond(
                                                item.name.contains(".zip"),
                                                rx.image(src="/zip_icon.png", width="24px", height="24px", object_fit="contain"),
                                                rx.cond(
                                                    item.name.contains(".mp3"),
                                                    rx.image(src="/mp3_icon.png", width="24px", height="24px", object_fit="contain"),
                                                    rx.cond(
                                                        item.name.contains(".docx"),
                                                        rx.image(src="/docx_icon.png", width="24px", height="24px", object_fit="contain"),
                                                        rx.cond(
                                                            item.name.contains(".xlsx"),
                                                            rx.image(src="/xlsx_icon.png", width="24px", height="24px", object_fit="contain"),
                                                            rx.cond(
                                                                item.name.contains(".pptx"),
                                                                rx.image(src="/pptx_icon.png", width="24px", height="24px", object_fit="contain"),
                                                                rx.cond(
                                                                    item.name.contains(".jpg"),
                                                                    rx.image(src="/jpg_icon.png", width="24px", height="24px", object_fit="contain"),
                                                                    rx.cond(
                                                                        item.name.contains(".bmp"),
                                                                        rx.image(src="/bmp_icon.png", width="24px", height="24px", object_fit="contain"),
                                                                        rx.cond(
                                                                            item.name.contains(".doc"),
                                                                            rx.image(src="/doc_icon.png", width="24px", height="24px", object_fit="contain"),
                                                                            rx.cond(
                                                                                item.name.contains(".xls"),
                                                                                rx.image(src="/xls_icon.png", width="24px", height="24px", object_fit="contain"),
                                                                                rx.cond(
                                                                                    item.name.contains(".ppt"),
                                                                                    rx.image(src="/ppt_icon.png", width="24px", height="24px", object_fit="contain"),
                                                                                    rx.icon(tag="file-text", color="#888", size=24)
                                                                                ),
                                                                            ),
                                                                        ),
                                                                    ),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            
            # Lock icon for protected levels
            rx.cond(
                item.is_protected,
                rx.icon(tag="lock", size=12, color="#aaa", margin_left="4px"),
            ),

            # Nombre del Directorio/Fichero
            rx.text(
                item.name,
                font_family="Tahoma, sans-serif",
                font_size="18px",
                color=rx.cond(item.is_protected, "#555", "black"),
                font_weight=rx.cond(item.depth == 0, "bold", "normal"),
                margin_left="4px",
                white_space="nowrap",
            ),

            # Indicador de estado para carpetas de versión (usa los datos del item)
            rx.cond(
                (item.depth == 1) & (item.version_state_label != ""),
                rx.text(
                    f" {item.version_state_label}",
                    color=item.version_state_color,
                    font_weight="bold",
                    font_size="17px",
                    margin_left="4px",
                ),
            ),

            rx.spacer(),

            # Tamaño (en la misma fila para visualización rápida)
            rx.cond(
                item.size_str != "",
                rx.text(
                    item.size_str,
                    font_size="16px",
                    color="#888",
                    padding_right="8px"
                ),
            ),
            
            spacing="0",
            align_items="center",
            padding_y="6px",
            padding_x="8px",
            bg=rx.cond(ExploradorState.selected_item_id == item.id, "#cfe8ff", "transparent"),
            opacity=rx.cond(item.is_blocked, "0.5", "1.0"),
            _hover={"bg": "#e5f3ff", "outline": "1px dotted #999"},
            width="100%",
            cursor="default",
            on_click=lambda: ExploradorState.select_item(item.id),
        ),
        rx.fragment()
    )

def render_item_with_context_menu(item: FolderItem):
    """
    Renderiza un elemento del explorador envuelto en menú contextual.
    Muestra menú:
    1. Si es carpeta normal habilitada.
    2. Si es carpeta de versión bloqueada PERO usuario es ADMIN (para desbloquear).
    """
    # Condición de menú carpeta
    should_show_menu_folder = (
        (item.item_type == "folder") & 
        (item.depth > 0) & 
        (~item.is_blocked | ((item.depth == 1) & ExploradorState.is_admin)) &
        ~ExploradorState.is_auditor # Auditores sin menú
    )
    
    # Condición de menú fichero: Fichero Y No Bloqueado
    should_show_menu_file = (
        (item.item_type != "folder") & 
        ~item.is_blocked &
        ~ExploradorState.is_auditor # Auditores sin menú
    )

    return rx.cond(
        should_show_menu_folder,
        # OPCIÓN 1: MENÚ CONTEXTUAL CARPETA
        rx.context_menu.root(
            rx.context_menu.trigger(
                rx.box(render_item(item), width="100%"),
                as_child=True,
            ),
            rx.context_menu.content(
                # SECCIÓN VERSIÓN: Abrir / Bloquear / Entrenar (solo para depth == 1)
                # REGLA: Ocultar opciones cuando is_final_c=True (cliente solicitó entrenamiento)
                rx.cond(
                    item.depth == 1,
                    rx.fragment(
                        # Abrir - Solo si NO ha solicitado entrenamiento (final_c=False)
                        rx.cond(
                            ~item.is_final_c,
                            rx.context_menu.item(
                                rx.hstack(rx.icon(tag="folder-open", size=16), rx.text("Abrir"), spacing="2"),
                                on_click=lambda: ExploradorState.abrir_version(item),
                            ),
                        ),
                        # Bloquear - Solo si NO ha solicitado entrenamiento (final_c=False)
                        rx.cond(
                            ~item.is_final_c,
                            rx.context_menu.item(
                                rx.hstack(rx.icon(tag="lock", size=16), rx.text("Bloquear"), spacing="2"),
                                on_click=lambda: ExploradorState.bloquear_version(item),
                            ),
                        ),
                        # Entrenar - Solo si NO ha solicitado entrenamiento (final_c=False)
                        rx.cond(
                            ~item.is_final_c,
                            rx.context_menu.item(
                                rx.hstack(rx.icon(tag="graduation-cap", size=16), rx.text("Entrenar"), spacing="2"),
                                on_click=lambda: ExploradorState.entrenar_version(item),
                            ),
                        ),
                        # Separador - Solo si hay opciones visibles
                        rx.cond(
                            ~item.is_final_c,
                            rx.context_menu.separator(),
                        ),
                    )
                ),
                # SECCIÓN ESTÁNDAR CARPETA
                rx.cond(
                    ExploradorState.can_folder_create & ~item.is_blocked,
                    rx.context_menu.item(
                        rx.hstack(rx.icon(tag="folder-plus", size=16), rx.text("Crear Carpeta"), spacing="2"),
                        on_click=lambda: ExploradorState.acciones("create_folder", item),
                    ),
                ),
                rx.cond(
                    ExploradorState.can_file_create & ~item.is_blocked,
                    rx.context_menu.item(
                        rx.hstack(rx.icon(tag="upload", size=16), rx.text("Subir archivo"), spacing="2"),
                        on_click=lambda: ExploradorState.acciones("upload_file", item),
                    ),
                ),
                rx.cond(
                    ExploradorState.can_folder_rename & ~item.is_protected & ~item.is_blocked,
                    rx.context_menu.item(
                        rx.hstack(rx.icon(tag="pencil", size=16), rx.text("Renombrar"), spacing="2"),
                        on_click=lambda: ExploradorState.acciones("rename", item),
                    ),
                ),
                rx.context_menu.separator(),
                rx.cond(
                    ExploradorState.can_folder_delete & ~item.is_protected & ~item.is_blocked,
                    rx.context_menu.item(
                        rx.hstack(rx.icon(tag="trash-2", size=16, color="red"), rx.text("Eliminar", color="red"), spacing="2"),
                        on_click=lambda: ExploradorState.acciones("delete", item),
                        color="red",
                    ),
                ),
                rx.context_menu.separator(),
                rx.cond(
                    ExploradorState.can_folder_read,
                    rx.context_menu.item(
                        rx.hstack(rx.icon(tag="info", size=16), rx.text("Propiedades"), spacing="2"),
                        on_click=lambda: ExploradorState.acciones("properties", item),
                    ),
                ),
            ),
        ),
        # OPCIÓN 2 y 3
        rx.cond(
            should_show_menu_file,
            # MENÚ CONTEXTUAL FICHERO
            rx.context_menu.root(
                rx.context_menu.trigger(
                    rx.box(render_item(item), width="100%"),
                    as_child=True,
                ),
                rx.context_menu.content(
                    # Descargar (Si tiene lectura)
                    rx.cond(
                        ExploradorState.can_file_read,
                        rx.context_menu.item(
                            rx.hstack(rx.icon(tag="download", size=16), rx.text("Descargar"), spacing="2"),
                            on_click=lambda: ExploradorState.acciones("download", item),
                        ),
                    ),
                    # Renombrar (Si tiene update)
                    rx.cond(
                        ExploradorState.can_file_update,
                        rx.context_menu.item(
                            rx.hstack(rx.icon(tag="pencil", size=16), rx.text("Renombrar"), spacing="2"),
                            on_click=lambda: ExploradorState.acciones("rename", item),
                        ),
                    ),
                    rx.context_menu.separator(),
                    # Eliminar (Si tiene delete)
                    rx.cond(
                        ExploradorState.can_file_delete,
                        rx.context_menu.item(
                            rx.hstack(rx.icon(tag="trash-2", size=16, color="red"), rx.text("Eliminar", color="red"), spacing="2"),
                            on_click=lambda: ExploradorState.acciones("delete", item),
                            color="red",
                        ),
                    ),
                    rx.context_menu.separator(),
                     # Propiedades (Siempre visible si tiene lectura)
                    rx.cond(
                        ExploradorState.can_file_read,
                        rx.context_menu.item(
                            rx.hstack(rx.icon(tag="info", size=16), rx.text("Propiedades"), spacing="2"),
                            on_click=lambda: ExploradorState.acciones("properties", item),
                        ),
                    ),
                ),
            ),
            # OPCIÓN 3: RENDER SIMPLE (Bloqueado o sin permisos)
            render_item(item)
        )
    )

def render_menu_option(label: str, icon_tag: str, action_key: str, is_danger: bool = False):
    """Renderiza una opción individual del menú contextual con validación de permisos."""
    # Mapeo de acciones a permisos de carpeta
    permiso_map = {
        "create_folder": "folder_create",
        "rename": "folder_rename",
        "delete": "folder_delete",
        "properties": "folder_read"
    }
    
    permiso_key = permiso_map.get(action_key)
    tiene_permiso = ExploradorState.permisos[permiso_key] if permiso_key else True
    
    # Regla: No permitir editar/borrar si el item está protegido
    es_accion_escritura = action_key in ["rename", "delete", "create_folder"]
    item_permitido = rx.cond(
        es_accion_escritura,
        ~ExploradorState.menu_item.is_protected,
        True
    )
    
    return rx.cond(
        tiene_permiso & item_permitido,
        rx.hstack(
            rx.icon(tag=icon_tag, size=16),
            rx.text(label, font_size="13px", color="red" if is_danger else "black"),
            on_click=[
                ExploradorState.acciones(action_key, ExploradorState.menu_item), 
                ExploradorState.close_context_menu
            ],
            _hover={"bg": "#fff0f0" if is_danger else "#eef6ff"},
            padding="8px",
            width="100%",
            border_radius="4px",
            cursor="pointer",
            spacing="2",
        )
    )

def render_context_menu():
    """Renderiza el contenedor del menú contextual flotante."""
    return rx.box(
        rx.vstack(
            render_menu_option("Crear Carpeta", "folder-plus", "create_folder"),
            rx.divider(),
            render_menu_option("Renombrar", "pencil", "rename"),
            render_menu_option("Eliminar", "trash-2", "delete", is_danger=True),
            rx.divider(),
            render_menu_option("Propiedades", "info", "properties"),
            spacing="0",
            width="100%",
            align_items="start",
        ),
        position="fixed",
        left=f"{ExploradorState.menu_x}px",
        top=f"{ExploradorState.menu_y}px",
        z_index="1000",
        bg="white",
        border="1px solid #ddd",
        border_radius="6px",
        box_shadow="0 4px 12px rgba(0,0,0,0.15)",
        padding="4px",
        min_width="180px",
        on_mouse_leave=ExploradorState.close_context_menu,
    )

def create_folder_dialog() -> rx.Component:
    """Diálogo para crear carpeta."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Crear nueva carpeta"),
            rx.dialog.description(
                "Ingresa el nombre de la nueva carpeta",
                margin_bottom="1em",
            ),
            rx.vstack(
                rx.input(
                    placeholder="Nombre de la carpeta",
                    value=ExploradorState.dialog_input_value,
                    on_change=lambda val: ExploradorState.set_dialog_input_value(val),
                    width="100%",
                    auto_focus=True,
                ),
                rx.hstack(
                    rx.button(
                        "Cancelar",
                        variant="soft",
                        color_scheme="gray",
                        on_click=ExploradorState.cerrar_dialogo_crear_carpeta,
                    ),
                    rx.button(
                        "Crear",
                        on_click=ExploradorState.ejecutar_crear_carpeta,
                        color_scheme="green",
                        style={"font_weight": "bold", "color": "black"},
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
        ),
        open=ExploradorState.show_create_folder_dialog,
    )

def rename_dialog() -> rx.Component:
    """Diálogo para renombrar."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Renombrar"),
            rx.dialog.description(
                "Ingresa el nuevo nombre",
                margin_bottom="1em",
            ),
            rx.vstack(
                rx.input(
                    placeholder="Nuevo nombre",
                    value=ExploradorState.dialog_input_value,
                    on_change=lambda val: ExploradorState.set_dialog_input_value(val),
                    width="100%",
                    auto_focus=True,
                ),
                rx.hstack(
                    rx.button(
                        "Cancelar",
                        variant="soft",
                        color_scheme="gray",
                        on_click=ExploradorState.cerrar_dialogo_renombrar,
                    ),
                    rx.button(
                        "Renombrar",
                        on_click=ExploradorState.ejecutar_renombrar,
                        color_scheme="green",
                        style={"font_weight": "bold", "color": "black"},
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
        ),
        open=ExploradorState.show_rename_dialog,
    )

def delete_confirm_dialog() -> rx.Component:
    """Diálogo de confirmación para eliminar."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Confirmar eliminación"),
            rx.dialog.description(
                "¿Estás seguro de que deseas eliminar este elemento? Esta acción no se puede deshacer.",
                margin_bottom="1em",
                color="red",
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "Cancelar",
                        variant="soft",
                        color_scheme="gray",
                        on_click=ExploradorState.cerrar_dialogo_eliminar,
                    ),
                ),
                rx.dialog.close(
                    rx.button(
                        "Eliminar",
                        color_scheme="red",
                        on_click=ExploradorState.ejecutar_eliminar,
                    ),
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
        ),
        open=ExploradorState.show_delete_confirm_dialog,
    )

def properties_dialog() -> rx.Component:
    """Diálogo de propiedades."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Propiedades"),
            rx.vstack(
                rx.text(
                    ExploradorState.properties_info,
                    white_space="pre-wrap",
                    font_family="monospace",
                    font_size="14px",
                ),
                rx.dialog.close(
                    rx.button(
                        "Cerrar",
                        on_click=ExploradorState.cerrar_dialogo_propiedades,
                        color_scheme="green",
                        style={"font_weight": "bold", "color": "black"},
                        width="100%",
                    ),
                ),
                spacing="4",
                width="100%",
            ),
        ),
        open=ExploradorState.show_properties_dialog,
    )

def explorador_panel(state) -> rx.Component:
    """Panel del explorador adaptado para nuestra estructura.

    Sistema de permisos:
    - Los permisos vienen de low_level_permissions usando identity_type_id del usuario
    - Prefijos: folder_ para carpetas, file_ para archivos
    - Los menús contextuales filtran opciones según permisos (security by design)

    Flujo de operaciones file system:
    Frontend/Backoffice → Middleware → Broker → Backend Core → fmanagement

    Persistencia de datos:
    - Acciones a nivel de versión (cambios de estado) → tabla version_states
    - Acciones con carpetas/archivos (crear, renombrar, eliminar) → tabla cambios
      * tipo_cambio: 'folder_create', 'folder_rename', 'folder_delete', 'file_create', 'file_update', 'file_delete'
      * descripcion: Detalle de la acción realizada
      * fecha_cambio: Fecha de la operación
      * id_version, id_proyecto, id_organizacion: Contexto

    Nota: En frontend solo se muestra el botón "El cliente solicita entrenamiento".
    """
    return rx.box(
        rx.vstack(
            # Header con título del explorador
            rx.hstack(
                rx.heading("Explorador de versiones del proyecto", size="6", color="#22c55e"),
                rx.spacer(),
                width="100%",
                align_items="center",
                margin_bottom="1em",
            ),

            # Contenedor del Explorador (Estilo Windows)
            rx.box(
                rx.vstack(
                    rx.foreach(
                        ExploradorState.items,
                        render_item_with_context_menu
                    ),
                    spacing="0",
                    align_items="start",
                    width="100%",
                ),
                bg="white",
                border="1px solid #828790",
                padding="10px",
                width="100%",
                height="80vh",
                overflow_y="auto",
                box_shadow="inset 2px 2px 5px rgba(0,0,0,0.05)",
            ),

            width="100%",
            padding="20px",
            align_items="start",
        ),

        # Diálogos modales
        create_folder_dialog(),
        rename_dialog(),
        delete_confirm_dialog(),
        properties_dialog(),

        width="100%",
        on_mount=ExploradorState.init_page,
    )

def explorador_page_internal() -> rx.Component:
    return rx.hstack(
        # Columna 1: Reservada
        rx.center(
            rx.vstack(
                rx.heading("Explorador", size="7", color="#333"),
                rx.divider(),
                rx.cond(
                    ExploradorState.is_access_authorized,
                    rx.badge(f"Usuario: {ExploradorState.user_name}", color_scheme="green"),
                    rx.badge("Sin Autorización", color_scheme="red"),
                ),
                rx.spacer(),
                rx.button(
                    "Cargar Contexto", 
                    on_click=ExploradorState.init_page,
                    color_scheme="blue"
                ),
                rx.link(
                    rx.button("Volver al Inicio", variant="ghost", color_scheme="gray"),
                    href="/"
                ),
                spacing="4",
                align="center",
                padding="20px",
            ),
            flex="1",
            height="100vh",
            border_right="2px solid #ddd",
            bg="#fdfdfd",
        ),
        
        rx.cond(
            ExploradorState.is_access_authorized,
            rx.fragment(
                # Columnas 2 y 3: Área del Explorador (Solo si está autorizado)
                rx.box(
                    rx.vstack(
                        rx.heading("Explorador de versiones", size="6", margin_bottom="1em", color="#444"),
                        
                        # Contenedor del Explorador (Estilo Windows)
                        rx.box(
                            rx.vstack(
                                rx.foreach(
                                    ExploradorState.items,
                                    render_item_with_context_menu
                                ),
                                spacing="0",
                                align_items="start",
                                width="100%",
                            ),
                            bg="white",
                            border="1px solid #828790",
                            padding="10px",
                            width="100%",
                            height="60vh",
                            overflow_y="auto",
                            box_shadow="inset 2px 2px 5px rgba(0,0,0,0.05)",
                        ),
                        # Selector de estados por versiones
                        rx.box(
                            rx.vstack(
                                # Control de Identidad (Impersonation)
                                rx.hstack(
                                    rx.text("Simulación de Rol:", font_weight="bold", color="#333"),
                                    rx.spacer(),
                                    rx.text("Cliente", font_size="13px", color="#666"),
                                    rx.switch(
                                        is_checked=ExploradorState.is_internal_user,
                                        on_change=ExploradorState.toggle_user_role,
                                        color_scheme="purple",
                                    ),
                                    rx.text("Interno", font_size="13px", color="#666"),
                                    rx.badge(
                                        ExploradorState.current_role_label, 
                                        color_scheme=rx.cond(ExploradorState.is_internal_user, "purple", "gray"),
                                        variant="solid",
                                        margin_left="10px"
                                    ),
                                    width="100%",
                                    align_items="center",
                                    padding_bottom="15px",
                                    border_bottom="1px solid #eee",
                                ),
                                
                                rx.heading("Selector de estados por versiones", size="4", color="#555"),
                                rx.hstack(
                                    rx.vstack(
                                        rx.text("Estado:", font_size="13px", color="#666"),
                                        rx.select(
                                            ExploradorState.available_status_options,
                                            value=ExploradorState.version_state,
                                            on_change=ExploradorState.set_version_state,
                                            width="150px",
                                            size="2",
                                            background_color="#3a3a3a",
                                            color="#f2f2f5",
                                            border_color="#555",
                                        ),
                                        align_items="start",
                                    ),
                                    rx.vstack(
                                rx.text("Protección:", font_size="13px", color="#666"),
                                rx.hstack(
                                    rx.checkbox(
                                        checked=ExploradorState.version_protected,
                                        on_change=ExploradorState.set_version_protected,
                                    ),
                                    rx.text("Protegida", color="black", font_weight="bold", font_size="13px"),
                                    spacing="2",
                                ),
                                align_items="start",
                            ),
                            rx.vstack(
                                rx.text("Capa Cliente:", font_size="13px", color="#666"),
                                rx.hstack(
                                    rx.checkbox(
                                        checked=ExploradorState.version_final_c,
                                        on_change=ExploradorState.set_version_final_c,
                                    ),
                                    rx.text("Cliente", color="black", font_weight="bold", font_size="13px"),
                                    spacing="2",
                                ),
                                align_items="start",
                            ),
                            rx.vstack(
                                rx.text("Capa Interno:", font_size="13px", color="#666"),
                                rx.hstack(
                                    rx.checkbox(
                                        checked=ExploradorState.version_final_i,
                                        on_change=ExploradorState.set_version_final_i,
                                    ),
                                    rx.text("Interno", color="black", font_weight="bold", font_size="13px"),
                                    spacing="2",
                                ),
                                align_items="start",
                            ),
                                    spacing="6",
                                    width="100%",
                                    align_items="end",
                                ),
                                # Botones de Transición de Estado
                                rx.divider(margin_y="10px"),
                                # Nota: Panel de simulación deshabilitado en modo multi-versión
                                # Use el menú contextual de cada versión para cambiar estados
                                rx.vstack(
                                    # Botones de Flujo (Visibles siempre, habilitados según rol)
                                    rx.button(
                                        rx.hstack(
                                            rx.icon(tag="shield-check", size=16),
                                            rx.text("El cliente solicita entrenamiento"),
                                            spacing="2",
                                        ),
                                        on_click=ExploradorState.solicitar_entrenamiento,
                                        color_scheme="blue",
                                        width="100%",
                                        size="2",
                                        disabled=ExploradorState.is_internal_user, # Deshabilitado si es Interno
                                    ),
                                    rx.button(
                                        rx.hstack(
                                            rx.icon(tag="check-circle", size=16),
                                            rx.text("Documentación preparada para entrenamiento"),
                                            spacing="2",
                                        ),
                                        on_click=ExploradorState.confirmar_entrenamiento,
                                        color_scheme="green",
                                        style={"font_weight": "bold", "color": "black"},
                                        width="100%",
                                        size="2",
                                        disabled=~ExploradorState.is_internal_user, # Deshabilitado si es Cliente
                                    ),
                                    spacing="2",
                                    width="100%",
                                ),
                                spacing="4",
                                width="100%",
                            ),
                            bg="white",
                            border="1px solid #ddd",
                            border_radius="8px",
                            padding="20px",
                            width="100%",
                            margin_top="20px",
                            box_shadow="0 2px 4px rgba(0,0,0,0.05)",
                        ),
                        
                        # Panel de Gestión de Permisos CRUD
                        rx.box(
                            rx.vstack(
                                rx.heading("Gestión de Permisos CRUD (Simulación)", size="4", color="#555"),
                                rx.hstack(
                                    # Columna Carpetas
                                    rx.vstack(
                                        rx.text("Carpetas", font_weight="bold", font_size="13px", color="#444"),
                                        rx.hstack(rx.checkbox(checked=ExploradorState.permisos["folder_create"], on_change=lambda v: ExploradorState.toggle_permiso("folder_create", v)), rx.text("Crear", color="black", font_weight="bold", font_size="13px"), spacing="2"),
                                        rx.hstack(rx.checkbox(checked=ExploradorState.permisos["folder_delete"], on_change=lambda v: ExploradorState.toggle_permiso("folder_delete", v)), rx.text("Eliminar", color="black", font_weight="bold", font_size="13px"), spacing="2"),
                                        rx.hstack(rx.checkbox(checked=ExploradorState.permisos["folder_rename"], on_change=lambda v: ExploradorState.toggle_permiso("folder_rename", v)), rx.text("Renombrar", color="black", font_weight="bold", font_size="13px"), spacing="2"),
                                        rx.hstack(rx.checkbox(checked=ExploradorState.permisos["folder_read"], on_change=lambda v: ExploradorState.toggle_permiso("folder_read", v)), rx.text("Leer", color="black", font_weight="bold", font_size="13px"), spacing="2"),
                                        rx.hstack(rx.checkbox(checked=ExploradorState.permisos["folder_list"], on_change=lambda v: ExploradorState.toggle_permiso("folder_list", v)), rx.text("Listar", color="black", font_weight="bold", font_size="13px"), spacing="2"),
                                        align_items="start",
                                        spacing="2",
                                    ),
                                    rx.divider(orientation="vertical", height="150px"),
                                    # Columna Ficheros
                                    rx.vstack(
                                        rx.text("Ficheros", font_weight="bold", font_size="13px", color="#444"),
                                        rx.hstack(rx.checkbox(checked=ExploradorState.permisos["file_create"], on_change=lambda v: ExploradorState.toggle_permiso("file_create", v)), rx.text("Crear", color="black", font_weight="bold", font_size="13px"), spacing="2"),
                                        rx.hstack(rx.checkbox(checked=ExploradorState.permisos["file_read"], on_change=lambda v: ExploradorState.toggle_permiso("file_read", v)), rx.text("Leer", color="black", font_weight="bold", font_size="13px"), spacing="2"),
                                        rx.hstack(rx.checkbox(checked=ExploradorState.permisos["file_update"], on_change=lambda v: ExploradorState.toggle_permiso("file_update", v)), rx.text("Actualizar", color="black", font_weight="bold", font_size="13px"), spacing="2"),
                                        rx.hstack(rx.checkbox(checked=ExploradorState.permisos["file_delete"], on_change=lambda v: ExploradorState.toggle_permiso("file_delete", v)), rx.text("Eliminar", color="black", font_weight="bold", font_size="13px"), spacing="2"),
                                        rx.hstack(rx.checkbox(checked=ExploradorState.permisos["file_list"], on_change=lambda v: ExploradorState.toggle_permiso("file_list", v)), rx.text("Listar", color="black", font_weight="bold", font_size="13px"), spacing="2"),
                                        align_items="start",
                                        spacing="2",
                                    ),
                                    spacing="8",
                                    width="100%",
                                    padding_top="10px",
                                ),
                                spacing="4",
                                width="100%",
                            ),
                            bg="white",
                            border="1px solid #ddd",
                            border_radius="8px",
                            padding="20px",
                            width="100%",
                            margin_top="20px",
                            box_shadow="0 2px 4px rgba(0,0,0,0.05)",
                        ),
                        
                        width="100%",
                        padding="60px",
                        align_items="start",
                    ),
                    flex="2",
                    height="100vh",
                    bg="#ececec",
                    overflow_y="auto",
                ),
                # Columna 3: Detalles del Fichero
                rx.box(
                    rx.vstack(
                        rx.heading("Detalles", size="6", margin_bottom="1em", color="#444"),
                        
                        rx.cond(
                            ExploradorState.selected_item_id != "",
                            rx.vstack(
                                rx.center(
                                    rx.cond(
                                        ExploradorState.selected_item.item_type == "folder",
                                        rx.icon(tag="folder", size=80, color="#F8D775"),
                                        rx.icon(tag="file-text", size=80, color="#888"),
                                    ),
                                    width="100%",
                                    padding="20px",
                                ),
                                rx.vstack(
                                    rx.text("Nombre: ", ExploradorState.selected_item.name, font_weight="bold"),
                                    rx.text(
                                        rx.cond(
                                            ExploradorState.selected_item.item_type == "folder",
                                            "Tipo: Carpeta",
                                            "Tipo: Archivo"
                                        )
                                    ),
                                    rx.cond(
                                        ExploradorState.selected_item.size_str != "",
                                        rx.text("Tamaño: ", ExploradorState.selected_item.size_str),
                                    ),
                                    rx.divider(),
                                    rx.cond(
                                        ExploradorState.selected_item.is_protected,
                                        rx.badge("Protegido", color_scheme="red"),
                                        rx.badge("Editable", color_scheme="green"),
                                    ),
                                    rx.divider(),
                                    
                                    # Botones de Acción
                                    rx.text("Acciones disponibles:", font_size="12px", color="#666"),
                                    rx.hstack(
                                        rx.button(
                                            rx.icon(tag="download", size=16),
                                            "Descargar",
                                            on_click=lambda: ExploradorState.acciones("download", ExploradorState.selected_item),
                                            color_scheme="blue",
                                            size="2",
                                        ),
                                        rx.button(
                                            rx.icon(tag="pencil", size=16),
                                            "Renombrar",
                                            on_click=lambda: ExploradorState.acciones("rename", ExploradorState.selected_item),
                                            color_scheme="gray",
                                            size="2",
                                            disabled=ExploradorState.selected_item.is_protected,
                                        ),
                                        rx.button(
                                            rx.icon(tag="trash-2", size=16),
                                            "Eliminar",
                                            on_click=lambda: ExploradorState.acciones("delete", ExploradorState.selected_item),
                                            color_scheme="red",
                                            size="2",
                                            disabled=ExploradorState.selected_item.is_protected,
                                        ),
                                        spacing="2",
                                        width="100%",
                                    ),

                                    align_items="start",
                                    width="100%",
                                ),
                                spacing="4",
                                width="100%",
                            ),
                            rx.center(
                                rx.text("Selecciona un elemento para ver sus detalles", color="#999"),
                                height="50vh",
                            )
                        ),
                        
                        width="100%",
                        padding="60px",
                        align_items="start",
                    ),
                    flex="1",
                    height="100vh",
                    bg="#f5f5f5",
                    border_left="2px solid #ddd",
                ),
            ),
            # Mensaje de Acceso Denegado
            rx.center(
                rx.vstack(
                    rx.icon(tag="shield-alert", size=100, color="red"),
                    rx.heading("Acceso No Autorizado", size="8", color="red"),
                    rx.text("No tienes permisos para acceder a los datos de este Proyecto/Organización.", font_size="18px"),
                    rx.text(f"ID Organización Solicitada: {ExploradorState.id_organizacion} | Tu ID: {ExploradorState.user_id_organizacion}", color="#888"),
                    rx.text(f"ID Proyecto Solicitado: {ExploradorState.id_proyecto} | Tu ID: {ExploradorState.user_project_id}", color="#888"),
                    rx.button("Reintentar Carga", on_click=ExploradorState.init_page, margin_top="2em"),
                    spacing="4",
                    align="center",
                ),
                flex="3",
                height="100vh",
                bg="#fff5f5",
            )
        ),

        width="100%",
        height="100vh",
        spacing="0",
        on_mount=ExploradorState.init_page,
    )

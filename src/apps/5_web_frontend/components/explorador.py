import reflex as rx
import pydantic
import json
import logging
import os

# Imports de adaptadores API
from adapters.api_client import (
    fmanagement_list_all_project_versions,
    get_project_versions,
    update_version_state,
)

# Configuración de Logging
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

class FolderItem(pydantic.BaseModel):
    id: str
    name: str
    depth: int
    parent_id: str = ""
    is_expanded: bool = False
    has_children: bool = False
    is_visible: bool = True
    item_type: str = "folder" # "folder" or "file"
    is_protected: bool = False # Level 0 and 1 are protected
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
    user_id_organizacion: int = 1
    user_project_id: int = 1
    is_admin: bool = False
    
    # Simulación de Identidad (Impersonation)
    is_internal_user: bool = False  # False = Cliente, True = Interno

    @rx.var
    def current_role_label(self) -> str:
        return "Interno" if self.is_internal_user else "Cliente"

    def toggle_user_role(self, val: bool):
        self.is_internal_user = val
        # Aquí podremos añadir lógica específica al cambiar de rol más adelante
        self.interpretacion_estados()
    
    # Matriz de Permisos
    permisos: dict = {
        "folder_create": False, "folder_delete": False, "folder_rename": False,
        "folder_read": False, "folder_list": False,
        "file_create": False, "file_read": False, "file_update": False,
        "file_delete": False, "file_list": False,
        "version_create": False
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
        """Carga el perfil de seguridad del usuario desde data/seguridad.json."""
        try:
            # Usar ruta absoluta para evitar problemas de CWD
            import os
            base_path = os.getcwd()
            json_path = os.path.join(base_path, "data", "seguridad.json")
            
            print(f"Intentando cargar seguridad desde: {json_path}")
            
            with open(json_path, "r") as f:
                data = json.load(f)
                usuario = data.get("usuario", {})
                
                self.user_id = usuario.get("user_id", 1)
                self.user_name = usuario.get("user_name", "anonimo")
                self.user_identity_type_id = usuario.get("identity_type_id", 0) # Nuevo campo
                # Defaults a 1 para evitar bloqueos en desarrollo si falla la lectura parcial
                self.user_id_organizacion = usuario.get("id_organizacion", 1)
                self.user_project_id = usuario.get("project_id", 1)
                
                # Carga de matriz de permisos
                logger.info(f"Aplicando seguridad Capa 1: Usuario '{self.user_name}' (ID: {self.user_id})")
                self.permisos = usuario.get("permisos", self.permisos)
                logger.debug(f"Permisos base (Capa 1): {self.permisos}")
                
                # APLICAR CAPA 2 DE SEGURIDAD
                self.apply_system_role_security()
                
                print(f"Perfil cargado: Org={self.user_id_organizacion}, Proy={self.user_project_id}, Admin={self.is_admin}, Auditor={self.is_auditor}")
                
                if not self.is_access_authorized:
                    print(f"ALERTA DE SEGURIDAD: Usuario {self.user_name} no autorizado para este proyecto.")
        except Exception as e:
            logger.error(f"Error cargando perfil de seguridad: {e}")
            print(f"Error cargando perfil de seguridad: {e}")
            # En caso de error crítico, asegurar valores de desarrollo
            self.user_id_organizacion = 1
            self.user_project_id = 1

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
            "Protegida": ("(Entrenamiento Solicitado)", "#00008B"),  # Azul oscuro
            "Final": ("(Versión Final)", "#8B0000"),  # Rojo oscuro
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
        Valida las protecciones antes de proceder.
        """
        # Excepciones a la protección: Acciones de administración de versiones
        admin_actions = ["block_version", "unblock_version", "review_version"]
        
        if item.is_protected and accion not in admin_actions:
            logger.warning(f"Acción '{accion}' denegada por protección en item '{item.name}'")
            return rx.window_alert(f"Acción '{accion}' denegada: El elemento '{item.name}' está protegido.")
        
        logger.info(f"Ejecutando acción: {accion} sobre {item.name}")
        if accion == "delete":
            return rx.window_alert(f"Simulando borrado de: {item.name}")
        elif accion == "rename":
            return rx.window_alert(f"Simulando cambio de nombre de: {item.name}")
        elif accion == "upload_file":
            return rx.window_alert(f"Simulando subida de archivo a: {item.name}")
        elif accion == "download":
            return rx.window_alert(f"Iniciando descarga de: {item.name}")
            
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
                error_msg = response.get("mensaje", "Error desconocido")
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
                error_msg = response.get("mensaje", "Error desconocido")
                logger.error(f"Error al persistir estado: {error_msg}")
                return rx.toast.error(f"Error al guardar: {error_msg}")

        except Exception as e:
            logger.error(f"Excepción al bloquear versión: {e}")
            return rx.toast.error(f"Error al guardar cambios")

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
            # Obtener versiones del proyecto
            versions_response = get_project_versions(
                project_id=self.id_proyecto,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            versiones = versions_response.get("versiones", [])

            if not versiones:
                logger.warning(f"No se encontraron versiones para proyecto {self.id_proyecto}")
                return

            # Limpiar diccionario de estados
            self.version_states = {}

            # Para cada versión, obtener su estado desde la API
            for version_info in versiones:
                version_id = version_info.get("id_version", 0)
                version_key = f"v{str(version_id).zfill(3)}"

                # Obtener estado de esta versión desde la API
                from adapters.api_client import get_version_state

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
                        "id_organizacion": version_info.get("id_organizacion", self.id_organizacion),
                        "id_proyecto": version_info.get("id_proyecto", self.id_proyecto),
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

    def reload_project_with_tokens(self, project_id: int, org_id: int, access_token: str, session_token: str):
        """Recarga el explorador con un nuevo proyecto.

        Args:
            project_id: ID del proyecto a cargar
            org_id: ID de la organización
            access_token: Token de acceso
            session_token: Token de sesión
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

        # Cargar desde API
        if self.access_token and self.session_token and self.id_proyecto > 0:
            logger.info(f"Cargando proyecto {self.id_proyecto} desde API")
            self.load_from_api()
        else:
            logger.warning("Tokens no disponibles, no se puede cargar desde API")

    def init_page(self, project_id: int = 0):
        """Inicializa los datos al cargar la página.

        Args:
            project_id: ID del proyecto a cargar (con todas sus versiones)
        """
        logger.info(f"Inicializando página Explorador para proyecto {project_id}...")

        # Guardar project_id
        if project_id > 0:
            self.id_proyecto = project_id

        # Cargar perfil de seguridad primero para obtener tokens si existen
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
            org_folder = f"ORG{str(self.id_organizacion).zfill(4)}"
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
                error_msg = response.get("mensaje", "Error desconocido al cargar datos")
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
                        rx.icon(tag="code-2", color="#00ADD8", size=24),
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
                # SECCIÓN VERSIÓN: Abrir / Bloquear (solo para depth == 1)
                rx.cond(
                    item.depth == 1,
                    rx.fragment(
                        rx.context_menu.item(
                            rx.hstack(rx.icon(tag="lock-open", size=16), rx.text("Abrir"), spacing="2"),
                            on_click=lambda: ExploradorState.abrir_version(item),
                        ),
                        rx.context_menu.item(
                            rx.hstack(rx.icon(tag="lock", size=16), rx.text("Bloquear"), spacing="2"),
                            on_click=lambda: ExploradorState.bloquear_version(item),
                        ),
                        rx.context_menu.separator(),
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
                rx.heading("Explorador de versiones del proyecto", size="6", color="white"),
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

"""Componente Explorador de Archivos - Backoffice.

Este componente gestiona la navegación y operaciones CRUD sobre la estructura
de archivos de proyectos y versiones, integrándose con fmanagement y la base
de datos de estados de versión.

Adaptado desde reflex_components_templates para usar APIs reales en lugar de
JSON mockeados.

NOTA: Este componente es idéntico al de Frontend. Ambos usan la misma
infraestructura de APIs y SharedSessionState.
"""

import reflex as rx
import pydantic
import logging
from typing import Any
import sys
import importlib.util
from pathlib import Path

# Imports de la capa compartida
from web_backoffice.shared_state import SharedSessionState

# Imports de API client
from adapters.api_client import (
    fmanagement_list,
    fmanagement_list_for_explorador,
    fmanagement_list_all_project_versions,
    fmanagement_operation,
    fmanagement_create_folder,
    fmanagement_rename_folder,
    fmanagement_rename_file,
    fmanagement_delete_folder,
    fmanagement_delete_file,
    fmanagement_get_properties,
    generate_file_upload_token,
    generate_file_download_token,
    get_version_state,
    update_version_state,
)

# ============================================================================
# Configuración de Logging (DEBE IR ANTES de importar permisos)
# ============================================================================

logger = logging.getLogger("backoffice")

# ============================================================================
# Importar sistema de permisos desde capa compartida
# ============================================================================

# Importar explorador_permissions_mapping.py desde 2_shared_application
try:
    # Path: explorador.py -> components -> 6_web_backoffice -> apps -> src
    # parents[3] nos lleva a "src", luego accedemos a 2_shared_application
    _mapping_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "explorador_permissions_mapping.py"
    _mapping_spec = importlib.util.spec_from_file_location("explorador_permissions_mapping", _mapping_path)
    _mapping_module = importlib.util.module_from_spec(_mapping_spec)
    sys.modules["explorador_permissions_mapping"] = _mapping_module
    _mapping_spec.loader.exec_module(_mapping_module)

    # Importar funciones de mapeo
    get_required_permission = _mapping_module.get_required_permission
    is_action_allowed = _mapping_module.is_action_allowed
    get_action_details = _mapping_module.get_action_details

    logger.info("[PERMISSIONS] Módulo de mapeo de permisos cargado correctamente")
except Exception as e:
    logger.error(f"[PERMISSIONS] Error cargando módulo de mapeo: {e}")
    import traceback
    traceback.print_exc()
    # Definir fallback si falla la carga
    def get_required_permission(action: str, item_type: str) -> str | None:
        return None
    def is_action_allowed(action: str, item_type: str, user_permissions: dict) -> bool:
        return True
    def get_action_details(action: str, item_type: str) -> dict | None:
        return None


# ============================================================================
# Modelos de Datos
# ============================================================================


class FolderItem(pydantic.BaseModel):
    """Item individual del explorador (carpeta o archivo).
    
    Attributes:
        id: Identificador único del item
        name: Nombre del archivo/carpeta
        depth: Nivel de profundidad (0=proyecto, 1=versión, 2+=contenido)
        parent_id: ID del item padre
        is_expanded: Si está expandido (solo carpetas)
        has_children: Si tiene hijos (solo carpetas)
        is_visible: Si es visible en la UI
        item_type: "folder" o "file"
        is_protected: Si está protegido (niveles 0 y 1 por Security by Design)
        is_blocked: Si está bloqueado operativamente (versión bloqueada)
        size_str: Tamaño formateado (ej: "1.2 MB")
        metadata: Información adicional
        version_state_label: Etiqueta de estado de versión (ej: "(Bloqueada)")
        version_state_color: Color del estado (ej: "#FF8C00")
        is_final_c: Flag de finalización por cliente
        is_final_i: Flag de finalización por interno
    """

    id: str
    name: str
    depth: int
    parent_id: str = ""
    is_expanded: bool = False
    has_children: bool = False
    is_visible: bool = True
    item_type: str = "folder"  # "folder" or "file"
    is_protected: bool = False  # Level 0 and 1 are protected (structural protection)
    db_protected: bool = False  # Database protected field from version_states (content protection)
    is_blocked: bool = False  # Operational block (opacity 0.5)
    size_str: str = ""  # Formatted size (e.g. "1.2 MB")
    metadata: dict = {}  # Extra info
    version_state_label: str = ""  # Estado de la versión (ej: "(Bloqueada)")
    version_state_color: str = ""  # Color del estado (ej: "#FF8C00")
    is_final_c: bool = False  # Flag cliente
    is_final_i: bool = False  # Flag interno


# ============================================================================
# Estado del Explorador
# ============================================================================


class ExploradorState(SharedSessionState):
    """Estado del explorador heredando de SharedSessionState.
    
    Heredamos automáticamente de SharedSessionState:
    - user_id, organization_id, identity_type_id
    - user_name, user_email, user_mobile
    - is_logged_in, is_active, is_blocked
    - access_token, session_token
    - 38 permisos can_* (can_folder_create, can_file_read, etc.)
    
    Añadimos campos específicos del explorador:
    - items: Lista de items del árbol de archivos
    - fmanagementlist: Estructura jerárquica de fmanagement
    - version_states: Estados de todas las versiones del proyecto
    - Campos de contexto de versión actual
    """

    # Estructura de archivos
    items: list[FolderItem] = []
    fmanagementlist: dict = {}
    selected_item_id: str = ""

    # Menú contextual global
    context_menu_open: bool = False
    context_menu_item_id: str = ""
    context_menu_x: int = 0
    context_menu_y: int = 0

    # Contexto de proyecto actual
    id_proyecto: int = 0
    id_organizacion: int = 0  # Alias para organization_id (mantener compatibilidad)

    # Estados de todas las versiones del proyecto
    # Estructura: {"v001": {state, protected, size, final_c, final_i}, "v002": {...}}
    version_states: dict = {}  # {version_key: state_data}

    # Variables para diálogos de acciones
    show_create_folder_dialog: bool = False
    show_rename_dialog: bool = False
    show_delete_confirm_dialog: bool = False
    show_properties_dialog: bool = False
    current_action_item: dict = {}
    dialog_input_value: str = ""
    properties_info: str = ""

    # ========================================================================
    # Propiedades Computadas
    # ========================================================================

    @rx.var
    def is_internal_user(self) -> bool:
        """En Backoffice siempre es usuario Interno.

        El backoffice es la interfaz para personal interno, por lo que
        independientemente de los permisos del usuario, siempre
        se considera como usuario interno.
        """
        return True  # Backoffice = Interno

    @rx.var
    def current_role_label(self) -> str:
        """Etiqueta del rol actual (Cliente/Interno)."""
        return "Interno" if self.is_internal_user else "Cliente"

    @rx.var
    def is_admin(self) -> bool:
        """Verifica si el usuario es administrador (identity_type_id 1 o 2)."""
        return self.identity_type_id in [1, 2]

    @rx.var
    def available_status_options(self) -> list[str]:
        """Opciones de estado disponibles en Backoffice.

        Backoffice: Abierta, Bloqueada, Entrenar, Final.
        Nota: "Protegida" deprecado, usar "Entrenar".
        """
        return ["Abierta", "Bloqueada", "Entrenar", "Final"]

    @rx.var
    def can_change_state(self) -> bool:
        """Verifica si el usuario puede cambiar el estado de la versión.

        Backoffice: Todos los internos pueden cambiar estados (soporte)
        """
        return self.is_internal_user

    @rx.var
    def is_access_authorized(self) -> bool:
        """Validación cruzada: Usuario pertenece a la organización y proyecto.
        
        Heredado de SharedSessionState:
        - organization_id: int
        """
        return self.organization_id > 0 and self.id_proyecto > 0

    # ========================================================================
    # Métodos de Inicialización (A IMPLEMENTAR EN PASO 6.4b)
    # ========================================================================

    def init_page(
        self,
        project_id: int = 0,
        user_id: int = 0,
        identity_type_id: int = 0,
        org_id: int = 0,
        access_token: str = "",
        session_token: str = "",
    ):
        """Inicializa el explorador para un proyecto (con todas sus versiones).

        Args:
            project_id: ID del proyecto a cargar (con todas sus versiones)
            user_id: ID del usuario (opcional, si no se pasa intenta obtenerlo del state)
            identity_type_id: Tipo de identidad del usuario (opcional)
            org_id: ID de la organización (opcional)
            access_token: Token de acceso (opcional)
            session_token: Token de sesión (opcional)
        """
        logger.info(
            "Inicializando explorador: project_id=%s, user_id=%s",
            project_id,
            user_id if user_id > 0 else self.user_id,
        )

        # Actualizar contexto si se proporcionan los parámetros
        if project_id > 0:
            self.id_proyecto = project_id
        if user_id > 0:
            self.user_id = user_id
        if identity_type_id > 0:
            self.identity_type_id = identity_type_id
        if org_id > 0:
            self.organization_id = org_id
            self.id_organizacion = org_id  # Mantener ambas sincronizadas
        if access_token:
            self.access_token = access_token
        if session_token:
            self.session_token = session_token

        # Cargar datos desde APIs (todas las versiones del proyecto)
        # load_from_api() ya llama internamente a interpretacion_estados()
        if self.id_proyecto > 0 and self.access_token and self.session_token:
            self.load_from_api()
        else:
            logger.warning("Faltan parámetros para cargar desde API")

        logger.info("Explorador inicializado correctamente")
        yield  # Actualizar UI

    def reload_project(self, project_id: int):
        """Recarga el explorador con un nuevo proyecto.

        Este método es llamado desde otros estados para actualizar
        el explorador cuando cambia el proyecto seleccionado.

        Args:
            project_id: ID del proyecto
        """
        logger.info(
            "Recargando explorador: project_id=%s, user_id=%s",
            project_id,
            self.user_id,
        )

        # Guardar contexto
        self.id_proyecto = project_id

        # Cargar datos desde APIs (todas las versiones)
        # load_from_api() ya llama internamente a interpretacion_estados()
        self.load_from_api()

        logger.info("Explorador recargado correctamente")
        yield  # Actualizar UI

    def reload_project_with_tokens(self, project_id: int, org_id: int, access_token: str, session_token: str):
        """Recarga el explorador con un nuevo proyecto incluyendo tokens.

        Args:
            project_id: ID del proyecto a cargar
            org_id: ID de la organización
            access_token: Token de acceso
            session_token: Token de sesión
        """
        print(f"[DEBUG EXPLORADOR] Recargando explorador para proyecto {project_id} con org_id={org_id}")

        # Actualizar IDs y tokens
        self.id_proyecto = project_id
        self.id_organizacion = org_id  # Usar alias en lugar de organization_id heredado
        print(f"[DEBUG EXPLORADOR] id_organizacion establecido a: {self.id_organizacion}")
        self.access_token = access_token
        self.session_token = session_token

        # Cargar desde API
        if self.access_token and self.session_token and self.id_proyecto > 0:
            print(f"[DEBUG EXPLORADOR] Cargando proyecto {self.id_proyecto} desde API con org_id={self.id_organizacion}")
            self.load_from_api()
        else:
            logger.warning("Tokens no disponibles, no se puede cargar desde API")

    # ========================================================================
    # Métodos de Carga de Datos
    # ========================================================================

    def load_from_api(self):
        """Carga todas las versiones del proyecto desde fmanagement API.

        Flujo: Backoffice → Middleware → Backend Core → MariaDB (versiones)
               Backoffice → Middleware → Broker → Backend Core → fmanagement (contenido)

        Construye los nombres de carpetas según convención:
        - org_folder: "ORG{organization_id:05d}"  (ej: "ORG00001")
        - prj_folder: "PRJ{id_proyecto:05d}"      (ej: "PRJ00001")
        """
        try:
            # Construir nombres de carpetas - usar la variable que esté establecida
            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            org_folder = f"ORG{str(org_id_to_use).zfill(5)}"
            prj_folder = f"PRJ{str(self.id_proyecto).zfill(5)}"

            logger.info(
                "Cargando todas las versiones del proyecto: org=%s, prj=%s (org_id=%s)",
                org_folder,
                prj_folder,
                org_id_to_use,
            )

            # Usar el adaptador que carga todas las versiones
            response = fmanagement_list_all_project_versions(
                org_id=org_id_to_use,
                project_id=self.id_proyecto,
                org_folder=org_folder,
                prj_folder=prj_folder,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("status") == "success":
                # El adaptador ya devuelve el formato correcto
                self.fmanagementlist = response
                logger.info("Estructura cargada: path=%s", response.get("path", ""))

                # Procesar estructura
                self.process_fmanagementlist()

                # Cargar estados de versión desde la API
                self.load_all_version_states()

                # Aplicar lógica de estados visuales (protección, bloqueo, etiquetas)
                self.interpretacion_estados()

                logger.info(f"Explorador cargado: {len(self.items)} items, {len(self.version_states)} versiones")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                logger.error("Error cargando fmanagement: %s", error_msg)
                self.fmanagementlist = {"items": []}

        except Exception as e:
            logger.exception("Excepción cargando desde fmanagement API: %s", e)
            self.fmanagementlist = {"items": []}

    def load_all_version_states(self):
        """Carga los estados de todas las versiones del proyecto desde la API.

        Obtiene los estados desde version_states tabla vía API del backend.
        """
        logger.info(f"load_all_version_states() - project_id={self.id_proyecto}, id_organizacion={self.id_organizacion}")
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
            for version_key in version_names:
                version_id = int(version_key[1:])  # "v001" → 1

                # Obtener estado de esta versión
                org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
                state_response = get_version_state(
                    project_id=self.id_proyecto,
                    version_id=version_id,
                    organization_id=org_id_to_use,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )

                if state_response.get("success"):
                    state_data = state_response.get("data", {}) if state_response.get("data") else state_response.get("state", {})
                    self.version_states[version_key] = {
                        "id_organizacion": state_data.get("id_organizacion", self.organization_id),
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
                        "id_organizacion": self.organization_id,
                        "id_proyecto": self.id_proyecto,
                        "state": "Abierta",
                        "protected": False,
                        "size": 0,
                        "final_c": False,
                        "final_i": False,
                    }

            logger.info(f"Estados de versiones cargados: {list(self.version_states.keys())}")

        except Exception as e:
            logger.exception("Error cargando estados de versiones: %s", e)

    # ========================================================================
    # Operaciones CRUD
    # ========================================================================

    def solicitar_entrenamiento(self):
        """Cliente solicita entrenamiento: Abierta → Protegida (final_c=True).

        Solo disponible para clientes (is_internal_user=False) cuando la versión
        está en estado "Abierta". Esta transición es IRREVERSIBLE excepto por admin.
        """
        if self.is_internal_user:
            return rx.toast.error("Esta acción es solo para clientes")

        if self.version_state != "Abierta":
            return rx.toast.error(f"Solo se puede solicitar entrenamiento en estado 'Abierta'. Estado actual: {self.version_state}")

        # Llamar API para actualizar estado
        try:
            from adapters.api_client import update_version_state

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            result = update_version_state(
                project_id=self.id_proyecto,
                version_id=self.id_version_int,
                state="Protegida",
                final_c=True,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token
            )

            if result.get("success"):
                # Recargar estado
                self.load_version_state_from_api()
                self.interpretacion_estados()
                yield
                return rx.toast.success("Entrenamiento solicitado: versión protegida")
            else:
                return rx.toast.error(f"Error: {result.get('message', 'Error desconocido')}")

        except Exception as e:
            logger.exception("Error solicitando entrenamiento: %s", e)
            return rx.toast.error(f"Error al solicitar entrenamiento: {str(e)}")

    def confirmar_entrenamiento(self):
        """Interno confirma entrenamiento: Protegida → Final (final_i=True).

        Solo disponible para internos (is_internal_user=True) cuando la versión
        está en estado "Protegida". Esta transición es IRREVERSIBLE y cierra
        definitivamente la versión.
        """
        if not self.is_internal_user:
            return rx.toast.error("Esta acción es solo para usuarios internos")

        if self.version_state != "Protegida":
            return rx.toast.error(f"Solo se puede confirmar entrenamiento en estado 'Protegida'. Estado actual: {self.version_state}")

        # Llamar API para actualizar estado
        try:
            from adapters.api_client import update_version_state

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            result = update_version_state(
                project_id=self.id_proyecto,
                version_id=self.id_version_int,
                state="Final",
                final_i=True,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token
            )

            if result.get("success"):
                # Recargar estado
                self.load_version_state_from_api()
                self.interpretacion_estados()
                yield
                return rx.toast.success("Entrenamiento confirmado: versión final")
            else:
                return rx.toast.error(f"Error: {result.get('message', 'Error desconocido')}")

        except Exception as e:
            logger.exception("Error confirmando entrenamiento: %s", e)
            return rx.toast.error(f"Error al confirmar entrenamiento: {str(e)}")

    def _resolve_version_item(self, item_or_id):
        """Resuelve item_or_id a un FolderItem y su version_key.

        Maneja los tres formatos posibles que Reflex puede enviar:
        - str: ID del item (búsqueda en self.items)
        - dict: Item serializado por Reflex (extrae el id y busca)
        - FolderItem: Objeto directo
        """
        logger.info(
            "[_resolve_version_item] Recibido: type=%s value=%r items_count=%d item_ids=%s",
            type(item_or_id).__name__,
            item_or_id,
            len(self.items),
            [i.id for i in self.items[:10]] if self.items else "[]",
        )
        if isinstance(item_or_id, dict):
            item_or_id = item_or_id.get("id", "")
            logger.info("[_resolve_version_item] Dict → id extraído: %r", item_or_id)
        if isinstance(item_or_id, str):
            item = next((i for i in self.items if i.id == item_or_id), None)
            if not item:
                logger.error(
                    "[_resolve_version_item] Item NO encontrado: id=%r en items=%s",
                    item_or_id,
                    [i.id for i in self.items],
                )
                return None, None
            logger.info("[_resolve_version_item] Item encontrado: id=%s name=%s", item.id, item.name)
            return item, item.name
        # FolderItem directo
        logger.info("[_resolve_version_item] FolderItem directo: %r", item_or_id)
        return item_or_id, item_or_id.name

    def abrir_version(self, item_or_id):
        """Cambia el estado de una versión a 'Abierta' (protected=False)."""
        item, version_key = self._resolve_version_item(item_or_id)
        if not item:
            return rx.toast.error("Item no encontrado")

        try:
            from adapters.api_client import update_version_state

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            result = update_version_state(
                project_id=self.id_proyecto,
                version_id=int(version_key.replace("v", "")),  # Convertir "v001" a 1
                state="Abierta",
                protected=False,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token
            )

            if result.get("success"):
                # Actualizar estado local
                if version_key in self.version_states:
                    self.version_states[version_key]["state"] = "Abierta"
                    self.version_states[version_key]["protected"] = False

                self.interpretacion_estados()
                yield
                return rx.toast.success(f"Versión {version_key} abierta")
            else:
                return rx.toast.error(f"Error: {result.get('message', 'Error desconocido')}")

        except Exception as e:
            logger.exception("Error abriendo versión: %s", e)
            return rx.toast.error(f"Error al abrir versión: {str(e)}")

    def bloquear_version(self, item_or_id):
        """Cambia el estado de una versión a 'Bloqueada' (protected=True)."""
        item, version_key = self._resolve_version_item(item_or_id)
        if not item:
            return rx.toast.error("Item no encontrado")

        try:
            from adapters.api_client import update_version_state

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            result = update_version_state(
                project_id=self.id_proyecto,
                version_id=int(version_key.replace("v", "")),
                state="Bloqueada",
                protected=True,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token
            )

            if result.get("success"):
                # Actualizar estado local
                if version_key in self.version_states:
                    self.version_states[version_key]["state"] = "Bloqueada"
                    self.version_states[version_key]["protected"] = True

                self.interpretacion_estados()
                yield
                return rx.toast.success(f"Versión {version_key} bloqueada")
            else:
                return rx.toast.error(f"Error: {result.get('message', 'Error desconocido')}")

        except Exception as e:
            logger.exception("Error bloqueando versión: %s", e)
            return rx.toast.error(f"Error al bloquear versión: {str(e)}")

    def entrenar_version(self, item_or_id):
        """Cambia el estado de una versión a 'Entrenar' (protected=True, final_c=True).

        Este método reemplaza a proteger_version() con la nueva nomenclatura.
        Estado "Entrenar" indica que el cliente ha solicitado entrenamiento.
        """
        item, version_key = self._resolve_version_item(item_or_id)
        if not item:
            return rx.toast.error("Item no encontrado")

        try:
            from adapters.api_client import update_version_state

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            result = update_version_state(
                project_id=self.id_proyecto,
                version_id=int(version_key.replace("v", "")),
                state="Entrenar",
                protected=True,
                final_c=True,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token
            )

            if result.get("success"):
                # Actualizar estado local
                if version_key in self.version_states:
                    self.version_states[version_key]["state"] = "Entrenar"
                    self.version_states[version_key]["protected"] = True
                    self.version_states[version_key]["final_c"] = True

                self.interpretacion_estados()
                yield
                return rx.toast.success(f"Entrenamiento solicitado para versión {version_key}")
            else:
                return rx.toast.error(f"Error: {result.get('message', 'Error desconocido')}")

        except Exception as e:
            logger.exception("Error solicitando entrenamiento: %s", e)
            return rx.toast.error(f"Error al solicitar entrenamiento: {str(e)}")

    def proteger_version(self, item_or_id):
        """DEPRECADO: Usar entrenar_version() en su lugar.

        Mantenido por compatibilidad con código legacy.
        """
        return self.entrenar_version(item_or_id)

    def finalizar_version(self, item_or_id):
        """Cambia el estado de una versión a 'Final' (protected=True, final_c=True, final_i=True)."""
        item, version_key = self._resolve_version_item(item_or_id)
        if not item:
            return rx.toast.error("Item no encontrado")

        try:
            from adapters.api_client import update_version_state

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            result = update_version_state(
                project_id=self.id_proyecto,
                version_id=int(version_key.replace("v", "")),
                state="Final",
                protected=True,
                final_c=True,
                final_i=True,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token
            )

            if result.get("success"):
                # Actualizar estado local
                if version_key in self.version_states:
                    self.version_states[version_key]["state"] = "Final"
                    self.version_states[version_key]["protected"] = True
                    self.version_states[version_key]["final_c"] = True
                    self.version_states[version_key]["final_i"] = True

                self.interpretacion_estados()
                yield
                return rx.toast.success(f"Versión {version_key} finalizada")
            else:
                return rx.toast.error(f"Error: {result.get('message', 'Error desconocido')}")

        except Exception as e:
            logger.exception("Error finalizando versión: %s", e)
            return rx.toast.error(f"Error al finalizar versión: {str(e)}")

    def set_version_state(self, val: str):
        """Cambia el estado de la versión mediante selector (interno: soporte al cliente).

        Backoffice: Permite cambiar a cualquier estado para dar soporte
        """
        if not self.is_internal_user:
            return rx.toast.error("Esta función es solo para usuarios internos")

        try:
            from adapters.api_client import update_version_state

            # Determinar protected, final_c, final_i según el nuevo estado
            protected = (val != "Abierta")
            final_c = (val in ["Protegida", "Final"])
            final_i = (val == "Final")

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            result = update_version_state(
                project_id=self.id_proyecto,
                version_id=self.id_version_int,
                state=val,
                protected=protected,
                final_c=final_c,
                final_i=final_i,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token
            )

            logger.info(f"[DEBUG] Resultado de update_version_state: {result}")

            if result.get("success"):
                logger.info(f"[DEBUG] Antes de recargar - version_state: {self.version_state}, protected: {self.version_protected}")

                # Actualizar estado inmediatamente desde el resultado de update
                if result.get("data"):
                    update_data = result.get("data")
                    self.version_state = update_data.get("state", val)
                    self.version_protected = update_data.get("protected", protected)
                    self.version_final_c = update_data.get("final_c", final_c)
                    self.version_final_i = update_data.get("final_i", final_i)
                    logger.info(f"[DEBUG] Estado actualizado desde update_data: {self.version_state}")
                else:
                    # Fallback: actualizar directamente con los valores enviados
                    self.version_state = val
                    self.version_protected = protected
                    self.version_final_c = final_c
                    self.version_final_i = final_i
                    logger.info(f"[DEBUG] Estado actualizado directamente: {self.version_state}")

                # Recargar desde API para confirmar (y actualizar cache)
                self.load_version_state_from_api()

                logger.info(f"[DEBUG] Después de recargar - version_state: {self.version_state}, protected: {self.version_protected}")

                self.interpretacion_estados()

                logger.info(f"[DEBUG] Después de interpretacion_estados - items bloqueados: {sum(1 for item in self.items if item.is_blocked)}/{len(self.items)}")

                yield
                return rx.toast.success(f"Estado cambiado a {val}")
            else:
                return rx.toast.error(f"Error: {result.get('message', 'Error desconocido')}")

        except Exception as e:
            logger.exception("Error cambiando estado: %s", e)
            return rx.toast.error(f"Error al cambiar estado: {str(e)}")

    def set_version_protected(self, val: bool):
        """Cambia la protección de la versión mediante checkbox (interno: soporte)."""
        if not self.is_internal_user:
            return rx.toast.error("Esta función es solo para usuarios internos")

        try:
            from adapters.api_client import update_version_state

            # Ajustar estado según protected
            new_state = "Bloqueada" if val else "Abierta"

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            result = update_version_state(
                project_id=self.id_proyecto,
                version_id=self.id_version_int,
                state=new_state,
                protected=val,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token
            )

            if result.get("success"):
                self.load_version_state_from_api()
                self.interpretacion_estados()
                yield
                return rx.toast.success(f"Protección {'activada' if val else 'desactivada'}")
            else:
                return rx.toast.error(f"Error: {result.get('message', 'Error desconocido')}")

        except Exception as e:
            logger.exception("Error cambiando protección: %s", e)
            return rx.toast.error(f"Error al cambiar protección: {str(e)}")

    def set_version_final_c(self, val: bool):
        """Cambia el flag final_c (interno: control directo para soporte)."""
        if not self.is_internal_user:
            return rx.toast.error("Esta función es solo para usuarios internos")

        try:
            from adapters.api_client import update_version_state

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            result = update_version_state(
                project_id=self.id_proyecto,
                version_id=self.id_version_int,
                final_c=val,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token
            )

            if result.get("success"):
                self.load_version_state_from_api()
                self.interpretacion_estados()
                yield
                return rx.toast.success(f"final_c {'activado' if val else 'desactivado'}")
            else:
                return rx.toast.error(f"Error: {result.get('message', 'Error desconocido')}")

        except Exception as e:
            logger.exception("Error cambiando final_c: %s", e)
            return rx.toast.error(f"Error al cambiar final_c: {str(e)}")

    def set_version_final_i(self, val: bool):
        """Cambia el flag final_i (interno: control directo para soporte)."""
        if not self.is_internal_user:
            return rx.toast.error("Esta función es solo para usuarios internos")

        try:
            from adapters.api_client import update_version_state

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            result = update_version_state(
                project_id=self.id_proyecto,
                version_id=self.id_version_int,
                final_i=val,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token
            )

            if result.get("success"):
                self.load_version_state_from_api()
                self.interpretacion_estados()
                yield
                return rx.toast.success(f"final_i {'activado' if val else 'desactivado'}")
            else:
                return rx.toast.error(f"Error: {result.get('message', 'Error desconocido')}")

        except Exception as e:
            logger.exception("Error cambiando final_i: %s", e)
            return rx.toast.error(f"Error al cambiar final_i: {str(e)}")

    def acciones(self, accion: str, item_or_id: FolderItem | str):
        """Ejecuta una acción sobre un item del explorador.

        Este método es el punto de entrada único para todas las operaciones CRUD
        sobre archivos y carpetas, así como operaciones administrativas sobre
        versiones (bloquear/desbloquear).

        Security by Design:
        - Valida PERMISOS del usuario (low_level_permissions desde base de datos)
        - Valida RESTRICCIONES DE VERSIÓN (solo identity_type_id 1 o 2)
        - Valida protección de contenido (db_protected)
        - Valida protección estructural (niveles 0 y 1)
        - Valida estado operativo (is_blocked)

        IMPORTANTE: TODAS las validaciones se loggean (éxito y fallo).

        Args:
            accion: Nombre de la acción (delete, rename, upload_file, download,
                    block_version, unblock_version, create_folder, properties)
            item_or_id: Item (FolderItem) o ID del item (str) sobre el que se ejecuta la acción
        """
        # Resolver item: puede llegar como str (id), dict (serializado) o FolderItem
        if isinstance(item_or_id, dict):
            item_or_id = item_or_id.get("id", "")
        if isinstance(item_or_id, str):
            item = None
            for i in self.items:
                if i.id == item_or_id:
                    item = i
                    break
            if not item:
                logger.error("Item no encontrado: %s", item_or_id)
                return rx.window_alert(f"Error: Item no encontrado")
        else:
            item = item_or_id

        # ====================================================================
        # VALIDACIÓN 1: PERMISOS DEL USUARIO (low_level_permissions)
        # ====================================================================

        # Obtener el permiso requerido para esta acción
        required_permission = get_required_permission(accion, item.item_type)

        if required_permission:
            # Obtener permisos del usuario desde SharedSessionState
            user_permissions = self.get_all_permissions()
            has_permission = user_permissions.get(required_permission, False)

            if not has_permission:
                logger.warning(
                    "[PERMISSION DENIED] user_id=%s identity_type_id=%s "
                    "accion=%s permiso=%s item=%s type=%s",
                    self.user_id,
                    self.identity_type_id,
                    accion,
                    required_permission,
                    item.name,
                    item.item_type,
                )
                return rx.toast.error(
                    f"Operación no permitida: Requiere permiso '{required_permission}'"
                )
            else:
                logger.info(
                    "[PERMISSION GRANTED] user_id=%s identity_type_id=%s "
                    "accion=%s permiso=%s item=%s type=%s",
                    self.user_id,
                    self.identity_type_id,
                    accion,
                    required_permission,
                    item.name,
                    item.item_type,
                )

        # ====================================================================
        # VALIDACIÓN 2: RESTRICCIONES DE VERSIÓN (solo identity_type_id 1 o 2)
        # ====================================================================

        version_operations = [
            "block_version",
            "unblock_version",
            "review_version",
            "abrir_version",
            "bloquear_version",
            "entrenar_version",
            "proteger_version",
            "finalizar_version",
        ]

        if accion in version_operations:
            if self.identity_type_id not in (1, 2):
                logger.warning(
                    "[VERSION OPERATION DENIED] user_id=%s identity_type_id=%s "
                    "accion=%s item=%s - Solo SuperAdmin (1) u OrgAdmin (2) pueden gestionar versiones",
                    self.user_id,
                    self.identity_type_id,
                    accion,
                    item.name,
                )
                return rx.toast.error(
                    "Operación no permitida: Solo administradores pueden gestionar versiones"
                )
            else:
                logger.info(
                    "[VERSION OPERATION ALLOWED] user_id=%s identity_type_id=%s "
                    "accion=%s item=%s",
                    self.user_id,
                    self.identity_type_id,
                    accion,
                    item.name,
                )

        # Excepciones a la protección: Acciones administrativas de versión
        admin_actions = ["block_version", "unblock_version", "review_version"]

        # Acciones de contenido: crear carpetas/archivos dentro de una versión
        content_actions = ["create_folder", "upload_file"]

        # ====================================================================
        # VALIDACIÓN 3: PROTECCIÓN DE CONTENIDO (db_protected)
        # ====================================================================

        if accion in content_actions:
            # Si el item es la versión misma (depth == 1), verificar directamente
            if item.depth == 1:
                if item.db_protected:
                    logger.warning(
                        "[CONTENT PROTECTION] Acción '%s' denegada: versión '%s' protegida en BD "
                        "(user_id=%s identity_type_id=%s)",
                        accion,
                        item.name,
                        self.user_id,
                        self.identity_type_id,
                    )
                    return rx.window_alert(
                        f"Acción '{accion}' denegada: La versión '{item.name}' está protegida."
                    )
                else:
                    logger.info(
                        "[CONTENT PROTECTION] Acción '%s' permitida: versión '%s' NO protegida "
                        "(user_id=%s)",
                        accion,
                        item.name,
                        self.user_id,
                    )

            # Si el item está dentro de una versión (depth > 1), buscar la versión ancestro
            elif item.depth > 1:
                # Buscar la versión en la jerarquía (depth == 1)
                version_item = self._find_version_ancestor(item)
                if version_item and version_item.db_protected:
                    logger.warning(
                        "[CONTENT PROTECTION] Acción '%s' denegada: versión ancestro '%s' protegida en BD "
                        "(user_id=%s item=%s)",
                        accion,
                        version_item.name,
                        self.user_id,
                        item.name,
                    )
                    return rx.window_alert(
                        f"Acción '{accion}' denegada: La versión '{version_item.name}' está protegida."
                    )
                elif version_item:
                    logger.info(
                        "[CONTENT PROTECTION] Acción '%s' permitida: versión ancestro '%s' NO protegida "
                        "(user_id=%s item=%s)",
                        accion,
                        version_item.name,
                        self.user_id,
                        item.name,
                    )

        # ====================================================================
        # VALIDACIÓN 4: PROTECCIÓN ESTRUCTURAL (Security by Design)
        # ====================================================================

        if item.is_protected and accion not in admin_actions and accion not in content_actions:
            logger.warning(
                "[STRUCTURAL PROTECTION] Acción '%s' denegada: item='%s' depth=%s is_protected=True "
                "(user_id=%s)",
                accion,
                item.name,
                item.depth,
                self.user_id,
            )
            return rx.window_alert(
                f"Acción '{accion}' denegada: El elemento '{item.name}' está protegido."
            )

        # ====================================================================
        # VALIDACIÓN 5: BLOQUEO OPERATIVO (is_blocked)
        # ====================================================================

        if item.is_blocked and accion not in admin_actions:
            logger.warning(
                "[OPERATIONAL BLOCK] Acción '%s' denegada: item='%s' is_blocked=True "
                "(user_id=%s version_state=%s)",
                accion,
                item.name,
                self.user_id,
                getattr(item, "version_state_label", "N/A"),
            )
            return rx.window_alert(
                f"Versión bloqueada: No se pueden realizar operaciones sobre '{item.name}'."
            )

        # ====================================================================
        # TODAS LAS VALIDACIONES PASARON - EJECUTAR ACCIÓN
        # ====================================================================

        logger.info(
            "[ACTION ALLOWED] Ejecutando acción: %s sobre %s (user_id=%s identity_type_id=%s)",
            accion,
            item.name,
            self.user_id,
            self.identity_type_id,
        )

        # ====================================================================
        # OPERACIONES CON DIÁLOGOS
        # ====================================================================

        if accion == "create_folder":
            return self.abrir_dialogo_crear_carpeta(item)

        elif accion == "rename":
            return self.abrir_dialogo_renombrar(item)

        elif accion == "delete":
            return self.abrir_dialogo_confirmar_eliminar(item)

        elif accion == "properties":
            return self.abrir_dialogo_propiedades(item)

        elif accion == "upload_file":
            return self.iniciar_subida_archivo(item)

        elif accion == "download":
            return self.iniciar_descarga_archivo(item)

        # ====================================================================
        # OPERACIONES ADMINISTRATIVAS DE VERSIÓN
        # ====================================================================

        elif accion == "block_version":
            logger.info(
                "[BLOCK_VERSION] Bloqueando versión: %s (user_id=%s identity_type_id=%s project_id=%s)",
                self.id_version,
                self.user_id,
                self.identity_type_id,
                self.id_proyecto,
            )

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            response = update_version_state(
                project_id=self.id_proyecto,
                version_id=self.id_version_int,
                state="Bloqueada",
                protected=True,
                updated_by_user_id=self.user_id,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                logger.info(
                    "[BLOCK_VERSION SUCCESS] Versión bloqueada: %s (user_id=%s)",
                    self.id_version,
                    self.user_id,
                )
                self.load_version_state_from_api()
                self.interpretacion_estados()
                return rx.toast.success("Versión bloqueada")
            else:
                error_msg = response.get("message", "Error desconocido")
                logger.error(
                    "[BLOCK_VERSION ERROR] Error bloqueando versión %s: %s (user_id=%s)",
                    self.id_version,
                    error_msg,
                    self.user_id,
                )
                return rx.toast.error(f"Error: {error_msg}")

        elif accion == "unblock_version":
            logger.info(
                "[UNBLOCK_VERSION] Desbloqueando versión: %s (user_id=%s identity_type_id=%s)",
                self.id_version,
                self.user_id,
                self.identity_type_id,
            )

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            response = update_version_state(
                project_id=self.id_proyecto,
                version_id=self.id_version_int,
                state="Abierta",
                protected=False,
                updated_by_user_id=self.user_id,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                logger.info(
                    "[UNBLOCK_VERSION SUCCESS] Versión desbloqueada: %s (user_id=%s)",
                    self.id_version,
                    self.user_id,
                )
                self.load_version_state_from_api()
                self.interpretacion_estados()
                return rx.toast.success("Versión desbloqueada")
            else:
                error_msg = response.get("message", "Error desconocido")
                logger.error(
                    "[UNBLOCK_VERSION ERROR] Error desbloqueando versión %s: %s (user_id=%s)",
                    self.id_version,
                    error_msg,
                    self.user_id,
                )
                return rx.toast.error(f"Error: {error_msg}")

        # ====================================================================
        # ACCIÓN NO RECONOCIDA
        # ====================================================================

        else:
            logger.warning("Acción no reconocida: %s", accion)
            return rx.window_alert(f"Acción '{accion}' no implementada")

    # ========================================================================
    # Lógica de Negocio
    # ========================================================================

    def interpretacion_estados(self):
        """Aplica la lógica de negocio y restricciones visuales en el explorador.
        
        Esta es la lógica central de Security by Design:
        1. Protección estructural básica (niveles 0 y 1)
        2. Bloqueo operativo por versión (según estados)
        3. Reglas para panel de simulación
        """
        # 1. Protección estructural básica (Security by Design)
        for item in self.items:
            item.is_protected = item.depth < 2
            item.is_blocked = False

        # 2. Bloqueo operativo por versión
        state_labels = {
            "Abierta": ("(Abierta)", "#228B22"),  # Verde
            "Bloqueada": ("(Bloqueada)", "#FF8C00"),  # Naranja
            "Entrenar": ("(Entrenamiento Solicitado)", "#00008B"),  # Azul oscuro
            "Protegida": ("(Entrenamiento Solicitado)", "#00008B"),  # Azul oscuro (alias)
            "Final": ("(Versión Final)", "#8B0000"),  # Rojo oscuro
        }

        for item in self.items:
            if item.depth == 1:
                # Es una carpeta de versión
                version_key = item.name  # ej: "v001"
                version_state_data = self.version_states.get(version_key, {})

                estado = version_state_data.get("state", "Abierta")
                protected = version_state_data.get("protected", False)
                final_c = version_state_data.get("final_c", False)
                final_i = version_state_data.get("final_i", False)

                # Asignar label, color y flags
                label, color = state_labels.get(estado, ("", ""))
                item.version_state_label = label
                item.version_state_color = color
                item.is_final_c = final_c
                item.is_final_i = final_i
                # CRÍTICO: Asignar el campo protected de la base de datos
                item.db_protected = protected

                es_bloqueada = protected or (estado != "Abierta")

                if es_bloqueada:
                    # NO bloquear la carpeta de versión misma (solo descendientes)
                    # Esto permite que el menú contextual siga mostrándose en la versión
                    version_id = item.id

                    # Bloquear solo los hijos (no el propio item de versión)
                    for descendant in self.items:
                        if descendant.id.startswith(version_id + "_"):
                            descendant.is_blocked = True

                # Actualizar tamaño
                if version_state_data.get("size", 0) > 0:
                    item.size_str = self._format_size(version_state_data.get("size", 0))

        # 3. Actualizar visibilidad
        self._update_visibility()

    def process_fmanagementlist(self):
        """Procesa la estructura fmanagementlist para aplanarla.

        Preserva el estado de expansión de los items existentes para que al
        refrescar después de una operación (crear carpeta, renombrar, etc.)
        la vista no colapse los nodos que el usuario tenía abiertos.
        """
        if not self.fmanagementlist or "items" not in self.fmanagementlist:
            return

        expanded_ids = {item.id for item in self.items if item.is_expanded}

        self.items = []
        self._flatten_recursive(self.fmanagementlist["items"])

        if expanded_ids:
            for item in self.items:
                if item.id in expanded_ids:
                    item.is_expanded = True

        self._update_visibility()

    def _flatten_recursive(self, json_items, depth=0, parent_id=""):
        """Función interna para aplanar el JSON."""
        for i, item in enumerate(json_items):
            item_id = f"{parent_id}_{i}" if parent_id else str(i)
            is_dir = item.get("is_dir", True)

            # Niveles 0 (Proyecto) y 1 (Versión) están protegidos
            is_protected = depth < 2

            # Gestionar tamaño
            bytes_val = item.get("size_bytes", 0)
            size_str = self._format_size(bytes_val)

            new_item = FolderItem(
                id=item_id,
                name=item.get("name", "unnamed"),
                depth=depth,
                parent_id=parent_id,
                is_expanded=depth < 1,
                has_children=is_dir and "items" in item and item["items"] is not None and len(item["items"]) > 0,
                is_visible=True,
                item_type="folder" if is_dir else "file",
                is_protected=is_protected,
                is_blocked=False,
                size_str=size_str,
                metadata=item.get("metadata", {}),
            )

            self.items.append(new_item)

            # Recursión para hijos (solo si items no es None)
            if is_dir and "items" in item and item["items"] is not None:
                self._flatten_recursive(item["items"], depth + 1, item_id)

    def _update_visibility(self):
        """Actualiza la visibilidad de los items según el estado de expansión."""
        for item in self.items:
            if item.depth == 0:
                item.is_visible = True
            else:
                # Buscar padre
                parent = next(
                    (i for i in self.items if i.id == item.parent_id), None
                )
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

    def _format_size(self, bytes_val):
        """Formatea bytes a la unidad más adecuada."""
        if not bytes_val:
            return ""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"

    # ========================================================================
    # Métodos para diálogos y acciones de carpetas/archivos
    # ========================================================================

    def abrir_dialogo_crear_carpeta(self, item_or_id):
        """Abre el diálogo para crear una nueva carpeta."""
        if isinstance(item_or_id, str):
            item = next((i for i in self.items if i.id == item_or_id), None)
            if not item:
                return rx.toast.error("Item no encontrado")
        else:
            item = item_or_id
        self.current_action_item = item.dict() if hasattr(item, "dict") else dict(item)
        self.dialog_input_value = ""
        self.show_create_folder_dialog = True

    def cerrar_dialogo_crear_carpeta(self):
        """Cierra el diálogo de crear carpeta."""
        self.show_create_folder_dialog = False
        self.dialog_input_value = ""
        self.current_action_item = {}

    def ejecutar_crear_carpeta(self):
        """Ejecuta la creación de carpeta."""
        if not self.dialog_input_value or not self.current_action_item:
            return rx.toast.error("Debe ingresar un nombre para la carpeta")

        try:
            item_data = self.current_action_item
            item = FolderItem(**item_data)
            folder_name = self.dialog_input_value.strip()

            project_id = self.id_proyecto

            # Identificar la versión
            if item.depth == 1:
                version_item = item
            elif item.depth > 1:
                version_item = self._find_version_ancestor(item)
                if not version_item:
                    return rx.toast.error("No se pudo identificar la versión ancestro")
            else:
                return rx.toast.error("No se puede crear carpeta en este nivel")

            # Extraer el número de versión del nombre
            version_name = version_item.name
            if version_name.startswith("v") and version_name[1:].isdigit():
                version_id = int(version_name.lstrip("v"))
            else:
                return rx.toast.error(f"Formato de versión inválido: {version_name}")

            # Construir la ruta relativa
            if item.depth == 1:
                folder_path = ""
            else:
                path_parts = []
                current = item
                while current.depth > 1:
                    path_parts.insert(0, current.name)
                    parent = next((p for p in self.items if p.id == current.parent_id), None)
                    if not parent:
                        break
                    current = parent
                folder_path = "/".join(path_parts) if path_parts else ""

            logger.info("Creando carpeta: %s en %s", folder_name, folder_path)

            response = fmanagement_create_folder(
                org_id=self.organization_id,
                project_id=project_id,
                version_id=version_id,
                folder_path=folder_path,
                folder_name=folder_name,
                user_id=self.user_id,
                identity_type_id=self.identity_type_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            self.cerrar_dialogo_crear_carpeta()

            if response.get("success") or response.get("status") == "success":
                logger.info("Carpeta creada: %s", folder_name)
                self.load_from_api()
                return rx.toast.success(f"Carpeta '{folder_name}' creada exitosamente")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                return rx.toast.error(f"Error: {error_msg}")

        except Exception as e:
            logger.error("Error en ejecutar_crear_carpeta: %s", e)
            self.cerrar_dialogo_crear_carpeta()
            return rx.toast.error(f"Error: {str(e)}")

    def abrir_dialogo_renombrar(self, item_or_id):
        """Abre el diálogo para renombrar."""
        if isinstance(item_or_id, str):
            item = next((i for i in self.items if i.id == item_or_id), None)
            if not item:
                return rx.toast.error("Item no encontrado")
        else:
            item = item_or_id
        self.current_action_item = item.dict() if hasattr(item, "dict") else dict(item)
        self.dialog_input_value = item.name
        self.show_rename_dialog = True

    def cerrar_dialogo_renombrar(self):
        """Cierra el diálogo de renombrar."""
        self.show_rename_dialog = False
        self.dialog_input_value = ""
        self.current_action_item = {}

    def ejecutar_renombrar(self):
        """Ejecuta el renombrado de carpeta o archivo."""
        if not self.dialog_input_value or not self.current_action_item:
            return rx.toast.error("Debe ingresar un nuevo nombre")

        try:
            item_data = self.current_action_item
            item = FolderItem(**item_data)
            new_name = self.dialog_input_value.strip()

            if new_name == item.name:
                self.cerrar_dialogo_renombrar()
                return rx.toast.info("El nombre no ha cambiado")

            project_id = self.id_proyecto

            if item.depth == 1:
                version_item = item
            elif item.depth > 1:
                version_item = self._find_version_ancestor(item)
                if not version_item:
                    return rx.toast.error("No se pudo identificar la versión ancestro")
            else:
                return rx.toast.error("No se puede renombrar este elemento")

            version_name = version_item.name
            if version_name.startswith("v") and version_name[1:].isdigit():
                version_id = int(version_name.lstrip("v"))
            else:
                return rx.toast.error(f"Formato de versión inválido: {version_name}")

            # No se debe permitir renombrar la versión misma
            if item.depth == 1:
                return rx.toast.error("No se puede renombrar la versión")
            else:
                path_parts = []
                current = item
                parent = next((p for p in self.items if p.id == current.parent_id), None)
                if parent and parent.depth > 1:
                    while parent.depth > 1:
                        path_parts.insert(0, parent.name)
                        grandparent = next((p for p in self.items if p.id == parent.parent_id), None)
                        if not grandparent:
                            break
                        parent = grandparent
                folder_path = "/".join(path_parts) if path_parts else ""

            logger.info("Renombrando %s a %s", item.name, new_name)

            if item.item_type == "folder":
                response = fmanagement_rename_folder(
                    org_id=self.organization_id,
                    project_id=project_id,
                    version_id=version_id,
                    folder_path=folder_path,
                    old_name=item.name,
                    new_name=new_name,
                    user_id=self.user_id,
                    identity_type_id=self.identity_type_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
            else:
                response = fmanagement_rename_file(
                    org_id=self.organization_id,
                    project_id=project_id,
                    version_id=version_id,
                    file_path=folder_path,
                    old_filename=item.name,
                    new_filename=new_name,
                    user_id=self.user_id,
                    identity_type_id=self.identity_type_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )

            self.cerrar_dialogo_renombrar()

            if response.get("success") or response.get("message"):
                logger.info("Renombrado exitoso: %s -> %s", item.name, new_name)
                self.load_from_api()
                return rx.toast.success(f"Renombrado a '{new_name}' exitosamente")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                return rx.toast.error(f"Error: {error_msg}")

        except Exception as e:
            logger.error("Error en ejecutar_renombrar: %s", e)
            self.cerrar_dialogo_renombrar()
            return rx.toast.error(f"Error: {str(e)}")

    def abrir_dialogo_confirmar_eliminar(self, item_or_id):
        """Abre el diálogo de confirmación para eliminar."""
        if isinstance(item_or_id, str):
            item = next((i for i in self.items if i.id == item_or_id), None)
            if not item:
                return rx.toast.error("Item no encontrado")
        else:
            item = item_or_id
        self.current_action_item = item.dict() if hasattr(item, "dict") else dict(item)
        self.show_delete_confirm_dialog = True

    def cerrar_dialogo_eliminar(self):
        """Cierra el diálogo de eliminar."""
        self.show_delete_confirm_dialog = False
        self.current_action_item = {}

    def ejecutar_eliminar(self):
        """Ejecuta la eliminación de carpeta o archivo."""
        if not self.current_action_item:
            return rx.toast.error("No hay elemento seleccionado")

        try:
            item_data = self.current_action_item
            item = FolderItem(**item_data)
            project_id = self.id_proyecto

            if item.depth == 1:
                version_item = item
            elif item.depth > 1:
                version_item = self._find_version_ancestor(item)
                if not version_item:
                    return rx.toast.error("No se pudo identificar la versión ancestro")
            else:
                return rx.toast.error("No se puede eliminar este elemento")

            version_name = version_item.name
            if version_name.startswith("v") and version_name[1:].isdigit():
                version_id = int(version_name.lstrip("v"))
            else:
                return rx.toast.error(f"Formato de versión inválido: {version_name}")

            if item.depth == 1:
                return rx.toast.error("No se puede eliminar la versión directamente")
            else:
                path_parts = []
                current = item
                parent = next((p for p in self.items if p.id == current.parent_id), None)
                if parent and parent.depth > 1:
                    while parent.depth > 1:
                        path_parts.insert(0, parent.name)
                        grandparent = next((p for p in self.items if p.id == parent.parent_id), None)
                        if not grandparent:
                            break
                        parent = grandparent

                if item.item_type == "folder":
                    folder_path = "/".join(path_parts) if path_parts else ""
                    folder_name = item.name
                else:
                    file_path = "/".join(path_parts) if path_parts else ""

            logger.info("Eliminando: %s", item.name)

            if item.item_type == "folder":
                response = fmanagement_delete_folder(
                    org_id=self.organization_id,
                    project_id=project_id,
                    version_id=version_id,
                    folder_path=folder_path,
                    folder_name=folder_name,
                    user_id=self.user_id,
                    identity_type_id=self.identity_type_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
            else:
                response = fmanagement_delete_file(
                    org_id=self.organization_id,
                    project_id=project_id,
                    version_id=version_id,
                    file_path=file_path,
                    filename=item.name,
                    user_id=self.user_id,
                    identity_type_id=self.identity_type_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )

            self.cerrar_dialogo_eliminar()

            if response.get("success") or response.get("status") == "success":
                logger.info("Eliminado exitosamente: %s", item.name)
                self.load_from_api()
                return rx.toast.success(f"'{item.name}' eliminado exitosamente")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                return rx.toast.error(f"Error: {error_msg}")

        except Exception as e:
            logger.error("Error en ejecutar_eliminar: %s", e)
            self.cerrar_dialogo_eliminar()
            return rx.toast.error(f"Error: {str(e)}")

    def abrir_dialogo_propiedades(self, item_or_id):
        """Abre el diálogo de propiedades."""
        if isinstance(item_or_id, str):
            item = next((i for i in self.items if i.id == item_or_id), None)
            if not item:
                return rx.toast.error("Item no encontrado")
        else:
            item = item_or_id
        self.current_action_item = item.dict() if hasattr(item, "dict") else dict(item)
        self.properties_info = "Cargando propiedades..."
        self.show_properties_dialog = True
        return self.cargar_propiedades()

    def cerrar_dialogo_propiedades(self):
        """Cierra el diálogo de propiedades."""
        self.show_properties_dialog = False
        self.properties_info = ""
        self.current_action_item = {}

    def cargar_propiedades(self):
        """Carga las propiedades del elemento usando el comando 'file' del SO."""
        if not self.current_action_item:
            return rx.toast.error("No hay elemento seleccionado")

        try:
            item_data = self.current_action_item
            item = FolderItem(**item_data)
            project_id = self.id_proyecto

            if item.depth == 1:
                version_item = item
            elif item.depth > 1:
                version_item = self._find_version_ancestor(item)
                if not version_item:
                    self.properties_info = "Error: No se pudo identificar la versión ancestro"
                    return rx.toast.error("No se pudo identificar la versión ancestro")
            else:
                self.properties_info = "Error: Nivel inválido para obtener propiedades"
                return rx.toast.error("No se pueden obtener propiedades de este elemento")

            version_name = version_item.name
            if version_name.startswith("v") and version_name[1:].isdigit():
                version_id = int(version_name.lstrip("v"))
            else:
                self.properties_info = f"Error: Formato de versión inválido: {version_name}"
                return rx.toast.error(f"Formato de versión inválido: {version_name}")

            # Construir la ruta relativa
            if item.depth == 1:
                item_path = ""
                item_name = "" if item.item_type == "folder" else item.name
            else:
                path_parts = []
                current = item
                while current.depth > 1:
                    if item.item_type == "folder":
                        path_parts.insert(0, current.name)
                    else:
                        if current.id != item.id:
                            path_parts.insert(0, current.name)
                    parent = next((p for p in self.items if p.id == current.parent_id), None)
                    if not parent or parent.depth <= 1:
                        break
                    current = parent

                item_path = "/".join(path_parts) if path_parts else ""
                item_name = "" if item.item_type == "folder" else item.name

            logger.info("Obteniendo propiedades de: %s", item.name)

            response = fmanagement_get_properties(
                org_id=self.organization_id,
                project_id=project_id,
                version_id=version_id,
                item_path=item_path,
                item_name=item_name,
                is_folder=(item.item_type == "folder"),
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success") or response.get("status") == "success":
                data = response.get("data") or response

                # Sanitizar el output del comando 'file'
                file_output = data.get("file_output", "No disponible")
                if file_output and ":" in file_output:
                    file_output = file_output.split(":", 1)[1].strip()

                info = "═══ PROPIEDADES ═══\n\n"
                info += f"Nombre: {data.get('name', item.name)}\n"
                info += f"Tipo: {'Carpeta' if data.get('is_dir') else 'Archivo'}\n"
                info += f"Tamaño: {self._format_size(data.get('size_bytes', 0))}\n"
                info += f"Permisos: {data.get('mode', 'N/A')}\n"
                info += f"Modificado: {data.get('mod_time', 'N/A')}\n\n"
                info += "═══ INFORMACIÓN DEL SISTEMA ═══\n\n"
                info += f"{file_output}\n"

                self.properties_info = info
                return rx.toast.success("Propiedades cargadas")
            else:
                error_msg = response.get("message") or response.get("detail", "Error desconocido")
                self.properties_info = f"Error al obtener propiedades: {error_msg}"
                return rx.toast.error(f"Error: {error_msg}")

        except Exception as e:
            logger.error("Error en cargar_propiedades: %s", e)
            self.properties_info = f"Error: {str(e)}"
            return rx.toast.error(f"Error: {str(e)}")

    def iniciar_subida_archivo(self, item_or_id):
        """Inicia el proceso de subida de archivo."""
        if isinstance(item_or_id, str):
            item = next((i for i in self.items if i.id == item_or_id), None)
            if not item:
                return rx.toast.error("Item no encontrado")
        else:
            item = item_or_id

        try:
            project_id = self.id_proyecto

            version_item = self._find_version_ancestor(item)
            if not version_item:
                if item.depth == 1:
                    version_item = item
                else:
                    logger.error("No se encontró versión para item: %s (depth=%s)", item.name, item.depth)
                    return rx.toast.error("Error: no se pudo identificar la versión")

            version_name = version_item.name
            if not version_name.startswith("v") or not version_name[1:].isdigit():
                logger.error("Nombre de versión inválido: %s", version_name)
                return rx.toast.error("Error: formato de versión inválido")

            version_id = int(version_name.lstrip("v"))

            # Calcular relative_path
            path_parts = []
            current = item
            while current.parent_id != "" and current.depth > version_item.depth:
                path_parts.insert(0, current.name)
                parent = next((p for p in self.items if p.id == current.parent_id), None)
                if not parent or parent.id == version_item.id:
                    break
                current = parent

            relative_path = "/".join(path_parts) if path_parts else ""

            logger.info(
                "Generando token de subida: project_id=%s, version_id=%s, path=%s",
                project_id, version_id, relative_path,
            )

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            response = generate_file_upload_token(
                project_id=project_id,
                version_id=version_id,
                relative_path=relative_path,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if not response.get("success"):
                error_msg = response.get("message") or response.get("detail", "Error al generar token")
                logger.error("Error generando token: %s", error_msg)
                return rx.toast.error(f"Error: {error_msg}")

            token = response.get("token")
            fmanagement_url = response.get("fmanagement_url")

            if not token or not fmanagement_url:
                logger.error("Respuesta incompleta del servidor")
                return rx.toast.error("Error: respuesta incompleta del servidor")

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
            logger.error("Error en iniciar_subida_archivo: %s", e)
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

    def iniciar_descarga_archivo(self, item_or_id):
        """Inicia el proceso de descarga de archivo."""
        if isinstance(item_or_id, str):
            item = next((i for i in self.items if i.id == item_or_id), None)
            if not item:
                return rx.toast.error("Item no encontrado")
        else:
            item = item_or_id

        try:
            if item.item_type != "file":
                logger.error("Item no es un archivo: %s", item.name)
                return rx.toast.error("Error: solo se pueden descargar archivos")

            project_id = self.id_proyecto

            version_item = self._find_version_ancestor(item)
            if not version_item:
                logger.error("No se encontró versión para item: %s", item.name)
                return rx.toast.error("Error: no se pudo identificar la versión")

            version_name = version_item.name
            if not version_name.startswith("v") or not version_name[1:].isdigit():
                logger.error("Nombre de versión inválido: %s", version_name)
                return rx.toast.error("Error: formato de versión inválido")

            version_id = int(version_name.lstrip("v"))

            # Calcular relative_path (sin incluir el nombre del archivo)
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

            logger.info(
                "Generando token de descarga: project_id=%s, version_id=%s, filename=%s, path=%s",
                project_id, version_id, filename, relative_path,
            )

            org_id_to_use = self.id_organizacion if self.id_organizacion > 0 else self.organization_id
            response = generate_file_download_token(
                project_id=project_id,
                version_id=version_id,
                filename=filename,
                relative_path=relative_path,
                organization_id=org_id_to_use,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if not response.get("success"):
                error_msg = response.get("message") or response.get("detail", "Error al generar token")
                logger.error("Error generando token: %s", error_msg)
                return rx.toast.error(f"Error: {error_msg}")

            download_url = response.get("download_url")

            if not download_url:
                logger.error("Respuesta incompleta del servidor")
                return rx.toast.error("Error: respuesta incompleta del servidor")

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

            logger.info("Iniciando descarga de %s", filename)
            return rx.call_script(download_script)

        except Exception as e:
            logger.error("Error en iniciar_descarga_archivo: %s", e)
            return rx.toast.error(f"Error: {str(e)}")

    def toggle_expand(self, item_id: str):
        """Colapsa/expande una carpeta."""
        for item in self.items:
            if item.id == item_id:
                item.is_expanded = not item.is_expanded
                logger.info("Toggle expand: %s → %s", item.name, item.is_expanded)
                break
        self._update_visibility()
        yield  # Actualizar UI

    def toggle_folder(self, item_id: str):
        """Expande o colapsa una carpeta (alias de toggle_expand)."""
        return self.toggle_expand(item_id)

    def select_item(self, item_id: str):
        """Selecciona un item."""
        self.selected_item_id = item_id
        logger.info("Item seleccionado: %s", item_id)
        yield  # Actualizar UI

    def handle_item_click(self, item_id: str):
        """Maneja el click en un item (carpeta o archivo).

        Si es carpeta: expande/colapsa
        Si es archivo: selecciona
        """
        for item in self.items:
            if item.id == item_id:
                if item.item_type == "folder":
                    # Es carpeta: toggle expand
                    item.is_expanded = not item.is_expanded
                    logger.info("Toggle expand: %s → %s", item.name, item.is_expanded)
                    self._update_visibility()
                else:
                    # Es archivo: seleccionar
                    self.selected_item_id = item_id
                    logger.info("Item seleccionado: %s", item_id)
                break
        yield  # Actualizar UI

    def open_context_menu(self, item_id: str):
        """Abre el menú contextual para un item específico."""
        self.context_menu_item_id = item_id
        self.context_menu_open = True
        logger.info("Menú contextual abierto para: %s", item_id)

    def close_context_menu(self):
        """Cierra el menú contextual."""
        self.context_menu_open = False
        self.context_menu_item_id = ""

    @rx.var
    def context_menu_item(self) -> FolderItem | None:
        """Retorna el item actualmente seleccionado en el menú contextual."""
        for item in self.items:
            if item.id == self.context_menu_item_id:
                return item
        return None


# ============================================================================
# Componentes UI
# ============================================================================
# NOTA: Los componentes UI completos (~590 líneas) deben copiarse del archivo
# original cuando se necesite renderizado visual:
# /Users/administrator/develop/reflex_components_templates/reflex_components_templates/pages/explorador/explorador.py
#
# Componentes a copiar (líneas 800-1405 aproximadamente):
# - explorador_panel() - Componente principal con 3 paneles
# - render_folder_item() - Renderiza item individual del árbol
# - render_context_menu() - Menú contextual con acciones
# - render_version_state_badge() - Badge de estado de versión
# - render_file_icon() - Iconos según tipo de archivo
# - render_panel_simulacion() - Panel de simulación de estados
# - render_toggle_role() - Toggle Cliente/Interno
# - Otros componentes auxiliares
#
# IMPORTANTE: Los componentes UI usan Reflex components (rx.box, rx.text, rx.menu, etc.)
# y no requieren modificación, solo copia directa del original.


def render_item(item: FolderItem) -> rx.Component:
    """Renderiza un item del explorador sin menú contextual."""
    return rx.cond(
        item.is_visible,
        rx.hstack(
        # Espaciador de niveles
        rx.box(width=f"{item.depth * 20}px"),
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
                on_click=ExploradorState.toggle_folder(item.id),
                margin_right="6px",
            ),
            rx.box(width="20px"),  # Espacio para alinear si no hay botón
        ),
        # Icono (Carpeta o Fichero con extensión personalizada)
        rx.cond(
            item.item_type == "folder",
            rx.icon(tag="folder", fill="#F8D775", color="#C6A15B", size=24),
            rx.cond(
                item.name.contains(".txt"),
                rx.image(src="/txt_icon.png", width="24px", height="24px", object_fit="contain"),
                rx.cond(
                    item.name.contains(".pdf"),
                    rx.image(src="/pdf_icon.png", width="24px", height="24px", object_fit="contain"),
                    rx.cond(
                        item.name.contains(".docx"),
                        rx.image(src="/docx_icon.png", width="24px", height="24px", object_fit="contain"),
                        rx.cond(
                            item.name.contains(".doc"),
                            rx.image(src="/doc_icon.png", width="24px", height="24px", object_fit="contain"),
                            rx.cond(
                                item.name.contains(".xlsx"),
                                rx.image(src="/xlsx_icon.png", width="24px", height="24px", object_fit="contain"),
                                rx.cond(
                                    item.name.contains(".xls"),
                                    rx.image(src="/xls_icon.png", width="24px", height="24px", object_fit="contain"),
                                    rx.cond(
                                        item.name.contains(".pptx"),
                                        rx.image(src="/pptx_icon.png", width="24px", height="24px", object_fit="contain"),
                                        rx.cond(
                                            item.name.contains(".ppt"),
                                            rx.image(src="/ppt_icon.png", width="24px", height="24px", object_fit="contain"),
                                            rx.cond(
                                                item.name.contains(".jpg"),
                                                rx.image(src="/jpg_icon.png", width="24px", height="24px", object_fit="contain"),
                                                rx.cond(
                                                    item.name.contains(".bmp"),
                                                    rx.image(src="/bmp_icon.png", width="24px", height="24px", object_fit="contain"),
                                                    rx.cond(
                                                        item.name.contains(".html"),
                                                        rx.image(src="/html_icon.png", width="24px", height="24px", object_fit="contain"),
                                                        rx.cond(
                                                            item.name.contains(".svg"),
                                                            rx.image(src="/svg_icon.png", width="24px", height="24px", object_fit="contain"),
                                                            rx.cond(
                                                                item.name.contains(".tiff"),
                                                                rx.image(src="/tiff_icon.png", width="24px", height="24px", object_fit="contain"),
                                                                rx.cond(
                                                                    item.name.contains(".zip"),
                                                                    rx.image(src="/zip_icon.png", width="24px", height="24px", object_fit="contain"),
                                                                    rx.cond(
                                                                        item.name.contains(".mp3"),
                                                                        rx.image(src="/mp3_icon.png", width="24px", height="24px", object_fit="contain"),
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
        # Indicador de estado para carpetas de versión
        rx.cond(
            (item.depth == 1) & (item.version_state_label != ""),
            rx.text(
                item.version_state_label,
                color=item.version_state_color,
                font_weight="bold",
                font_size="17px",
                margin_left="4px",
            ),
        ),
        rx.spacer(),
        # Tamaño
        rx.cond(
            item.size_str != "",
            rx.text(
                item.size_str,
                font_size="16px",
                color="#888",
                padding_right="8px",
            ),
        ),
        # Indicadores: candado sutil para protegido, badge naranja para bloqueado
        rx.cond(
            item.is_protected,
            rx.icon(tag="lock", size=12, color="#aaa", margin_left="4px"),
            rx.fragment(),
        ),
        rx.cond(
            item.is_blocked,
            rx.badge("Bloqueado", color_scheme="orange", size="1"),
            rx.fragment(),
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
        on_click=ExploradorState.select_item(item.id),
        ),
        rx.fragment()
    )


def create_folder_menu_items(item_obj: FolderItem):
    """Crea los menu items para una carpeta, capturando correctamente el item."""
    return [
        # Opciones de versión (depth == 1) - Backoffice
        rx.cond(
            item_obj.depth == 1,
            rx.fragment(
                rx.context_menu.item(
                    rx.hstack(rx.icon(tag="lock-open", size=16), rx.text("Abrir"), spacing="2"),
                    on_click=ExploradorState.abrir_version(item_obj.id),
                ),
                rx.context_menu.item(
                    rx.hstack(rx.icon(tag="lock", size=16), rx.text("Bloquear"), spacing="2"),
                    on_click=ExploradorState.bloquear_version(item_obj.id),
                ),
                rx.context_menu.item(
                    rx.hstack(rx.icon(tag="graduation-cap", size=16), rx.text("Entrenar"), spacing="2"),
                    on_click=ExploradorState.entrenar_version(item_obj.id),
                ),
                rx.context_menu.item(
                    rx.hstack(rx.icon(tag="circle-check", size=16), rx.text("Finalizar"), spacing="2"),
                    on_click=ExploradorState.finalizar_version(item_obj.id),
                ),
                rx.context_menu.separator(),
            ),
        ),
        # Opciones estándar de carpeta
        rx.cond(
            ExploradorState.can_folder_create & ~item_obj.is_blocked,
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="folder-plus", size=16), rx.text("Crear Carpeta"), spacing="2"),
                on_click=ExploradorState.acciones("create_folder", item_obj.id),
            ),
        ),
        rx.cond(
            ExploradorState.can_file_create & ~item_obj.is_blocked,
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="upload", size=16), rx.text("Subir archivo"), spacing="2"),
                on_click=ExploradorState.acciones("upload_file", item_obj.id),
            ),
        ),
        rx.cond(
            ExploradorState.can_folder_rename & ~item_obj.is_protected & ~item_obj.is_blocked,
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="pencil", size=16), rx.text("Renombrar"), spacing="2"),
                on_click=ExploradorState.acciones("rename", item_obj.id),
            ),
        ),
        rx.context_menu.separator(),
        rx.cond(
            ExploradorState.can_folder_delete & ~item_obj.is_protected & ~item_obj.is_blocked,
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="trash-2", size=16, color="red"), rx.text("Eliminar", color="red"), spacing="2"),
                on_click=ExploradorState.acciones("delete", item_obj.id),
                color="red",
            ),
        ),
        rx.context_menu.separator(),
        rx.cond(
            ExploradorState.can_folder_read,
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="info", size=16), rx.text("Propiedades"), spacing="2"),
                on_click=ExploradorState.acciones("properties", item_obj.id),
            ),
        ),
    ]


def create_file_menu_items(item_obj: FolderItem):
    """Crea los menu items para un archivo."""
    return [
        rx.cond(
            ExploradorState.can_file_read,
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="download", size=16), rx.text("Descargar"), spacing="2"),
                on_click=ExploradorState.acciones("download", item_obj.id),
            ),
        ),
        rx.cond(
            ExploradorState.can_file_update,
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="pencil", size=16), rx.text("Renombrar"), spacing="2"),
                on_click=ExploradorState.acciones("rename", item_obj.id),
            ),
        ),
        rx.context_menu.separator(),
        rx.cond(
            ExploradorState.can_file_delete,
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="trash-2", size=16, color="red"), rx.text("Eliminar", color="red"), spacing="2"),
                on_click=ExploradorState.acciones("delete", item_obj.id),
                color="red",
            ),
        ),
        rx.context_menu.separator(),
        rx.cond(
            ExploradorState.can_file_read,
            rx.context_menu.item(
                rx.hstack(rx.icon(tag="info", size=16), rx.text("Propiedades"), spacing="2"),
                on_click=ExploradorState.acciones("properties", item_obj.id),
            ),
        ),
    ]


def render_item_with_menu_button(item: FolderItem) -> rx.Component:
    """Renderiza un item con botón de menú visible (⋮) en lugar de menú contextual."""
    # Condición para mostrar menú en carpetas
    should_show_menu_folder = (
        (item.item_type == "folder") &
        (item.depth > 0) &
        (~item.is_blocked | ((item.depth == 1) & ExploradorState.is_internal_user))
    )

    # Condición para mostrar menú en archivos
    should_show_menu_file = (
        (item.item_type != "folder") &
        ~item.is_blocked
    )

    should_show_menu = should_show_menu_folder | should_show_menu_file

    return rx.hstack(
        # Espaciador de niveles
        rx.box(width=f"{item.depth * 20}px"),
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
                on_click=ExploradorState.toggle_folder(item.id),
                margin_right="6px",
            ),
            rx.box(width="20px"),
        ),
        # Icono (Carpeta o Fichero con extensión personalizada)
        rx.cond(
            item.item_type == "folder",
            rx.icon(tag="folder", fill="#F8D775", color="#C6A15B", size=24),
            rx.cond(
                item.name.contains(".txt"),
                rx.image(src="/txt_icon.png", width="24px", height="24px", object_fit="contain"),
                rx.cond(
                    item.name.contains(".pdf"),
                    rx.image(src="/pdf_icon.png", width="24px", height="24px", object_fit="contain"),
                    rx.cond(
                        item.name.contains(".docx"),
                        rx.image(src="/docx_icon.png", width="24px", height="24px", object_fit="contain"),
                        rx.cond(
                            item.name.contains(".doc"),
                            rx.image(src="/doc_icon.png", width="24px", height="24px", object_fit="contain"),
                            rx.cond(
                                item.name.contains(".xlsx"),
                                rx.image(src="/xlsx_icon.png", width="24px", height="24px", object_fit="contain"),
                                rx.cond(
                                    item.name.contains(".xls"),
                                    rx.image(src="/xls_icon.png", width="24px", height="24px", object_fit="contain"),
                                    rx.cond(
                                        item.name.contains(".pptx"),
                                        rx.image(src="/pptx_icon.png", width="24px", height="24px", object_fit="contain"),
                                        rx.cond(
                                            item.name.contains(".ppt"),
                                            rx.image(src="/ppt_icon.png", width="24px", height="24px", object_fit="contain"),
                                            rx.cond(
                                                item.name.contains(".jpg"),
                                                rx.image(src="/jpg_icon.png", width="24px", height="24px", object_fit="contain"),
                                                rx.cond(
                                                    item.name.contains(".bmp"),
                                                    rx.image(src="/bmp_icon.png", width="24px", height="24px", object_fit="contain"),
                                                    rx.cond(
                                                        item.name.contains(".html"),
                                                        rx.image(src="/html_icon.png", width="24px", height="24px", object_fit="contain"),
                                                        rx.cond(
                                                            item.name.contains(".svg"),
                                                            rx.image(src="/svg_icon.png", width="24px", height="24px", object_fit="contain"),
                                                            rx.cond(
                                                                item.name.contains(".tiff"),
                                                                rx.image(src="/tiff_icon.png", width="24px", height="24px", object_fit="contain"),
                                                                rx.cond(
                                                                    item.name.contains(".zip"),
                                                                    rx.image(src="/zip_icon.png", width="24px", height="24px", object_fit="contain"),
                                                                    rx.cond(
                                                                        item.name.contains(".mp3"),
                                                                        rx.image(src="/mp3_icon.png", width="24px", height="24px", object_fit="contain"),
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
        # Indicador de estado para carpetas de versión
        rx.cond(
            (item.depth == 1) & (item.version_state_label != ""),
            rx.text(
                item.version_state_label,
                color=item.version_state_color,
                font_weight="bold",
                font_size="17px",
                margin_left="4px",
            ),
        ),
        # Tamaño
        rx.cond(
            item.size_str != "",
            rx.text(
                item.size_str,
                font_size="16px",
                color="#888",
                padding_right="8px",
            ),
        ),
        # Indicadores: candado sutil para protegido, badge naranja para bloqueado
        rx.cond(
            item.is_protected,
            rx.icon(tag="lock", size=12, color="#aaa", margin_left="4px"),
            rx.fragment(),
        ),
        rx.cond(
            item.is_blocked,
            rx.badge("Bloqueado", color_scheme="orange", size="1"),
            rx.fragment(),
        ),
        rx.spacer(),  # Empuja el menú a la derecha
        # Botón de menú (solo si debe mostrarse)
        rx.cond(
            should_show_menu,
            rx.menu.root(
                rx.menu.trigger(
                    rx.icon_button(
                        rx.icon("ellipsis-vertical", size=16),
                        variant="ghost",
                        size="1",
                        color_scheme="gray",
                    ),
                ),
                rx.menu.content(
                    rx.cond(
                        item.item_type == "folder",
                        rx.fragment(*create_folder_menu_items(item)),
                        rx.fragment(*create_file_menu_items(item)),
                    ),
                ),
            ),
            rx.fragment(),
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
        on_click=ExploradorState.select_item(item.id),
    )


def render_item_with_context_menu(item: FolderItem) -> rx.Component:
    """Renderiza un item con menú contextual según tipo y permisos."""
    # Condición para mostrar menú en carpetas
    should_show_menu_folder = (
        (item.item_type == "folder") &
        (item.depth > 0) &
        (~item.is_blocked | ((item.depth == 1) & ExploradorState.is_internal_user))
    )

    # Condición para mostrar menú en archivos
    should_show_menu_file = (
        (item.item_type != "folder") &
        ~item.is_blocked
    )

    return rx.cond(
        should_show_menu_folder,
        # MENÚ CONTEXTUAL PARA CARPETAS
        rx.context_menu.root(
            rx.context_menu.trigger(
                rx.box(render_item(item), width="100%"),
                as_child=True,
            ),
            rx.context_menu.content(
                *create_folder_menu_items(item),
            ),
        ),
        rx.cond(
            should_show_menu_file,
            # MENÚ CONTEXTUAL PARA ARCHIVOS
            rx.context_menu.root(
                rx.context_menu.trigger(
                    rx.box(render_item(item), width="100%"),
                    as_child=True,
                ),
                rx.context_menu.content(
                    *create_file_menu_items(item),
                ),
            ),
            # RENDER SIMPLE (sin menú)
            render_item(item)
        )
    )


# ============================================================================
# Componentes de Diálogo UI (adaptados al color scheme del backoffice)
# ============================================================================


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
                        color_scheme="orange",
                        style={"font_weight": "bold", "color": "black"},
                        on_click=ExploradorState.ejecutar_crear_carpeta,
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
                        color_scheme="orange",
                        style={"font_weight": "bold", "color": "black"},
                        on_click=ExploradorState.ejecutar_renombrar,
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
                        style={"font_weight": "bold", "color": "black"},
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
                        color_scheme="orange",
                        style={"font_weight": "bold", "color": "black"},
                        on_click=ExploradorState.cerrar_dialogo_propiedades,
                        width="100%",
                    ),
                ),
                spacing="4",
                width="100%",
            ),
        ),
        open=ExploradorState.show_properties_dialog,
    )


def explorador_panel(state: ExploradorState) -> rx.Component:
    """Panel del explorador adaptado para backoffice.

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

    Nota: En backoffice solo se muestra el botón "Documentación preparada para entrenamiento".

    Args:
        state: Estado del explorador (ExploradorState)

    Returns:
        Componente Reflex renderizable
    """
    return rx.box(
        rx.vstack(
            # Header con título del explorador
            rx.hstack(
                rx.heading("Explorador de versiones del proyecto", size="6", color="#FF8C00"),
                rx.spacer(),
                width="100%",
                align_items="center",
                margin_bottom="1em",
            ),

            # Contenedor del Explorador (Estilo Windows)
            rx.box(
                rx.vstack(
                    rx.foreach(
                        state.items,
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

            # Diálogos modales
            create_folder_dialog(),
            rename_dialog(),
            delete_confirm_dialog(),
            properties_dialog(),

            width="100%",
            padding="20px",
            align_items="start",
        ),
        width="100%",
    )

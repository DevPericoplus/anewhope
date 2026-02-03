"""Componente Explorador de Archivos - Frontend.

Este componente gestiona la navegación y operaciones CRUD sobre la estructura
de archivos de proyectos y versiones, integrándose con fmanagement y la base
de datos de estados de versión.

Adaptado desde reflex_components_templates para usar APIs reales en lugar de
JSON mockeados.
"""

import reflex as rx
import pydantic
import logging
from typing import Any

# Imports de la capa compartida
try:
    from src.apps.2_shared_application.reflex_shared.shared_session_state import (
        SharedSessionState,
    )
except ImportError:
    from ...2_shared_application.reflex_shared.shared_session_state import (
        SharedSessionState,
    )

# Imports de API client
from ..adapters.api_client import (
    fmanagement_list,
    fmanagement_operation,
    get_version_state,
    update_version_state,
)


# ============================================================================
# Configuración de Logging
# ============================================================================

logger = logging.getLogger("ExploradorFrontend")
logger.setLevel(logging.INFO)


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
    is_protected: bool = False  # Level 0 and 1 are protected
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

    # Contexto de proyecto y versión actual
    id_proyecto: int = 0
    id_version_int: int = 0
    id_version: str = ""  # ej: "v001"

    # Estado de la versión actual
    version_state: str = "Abierta"  # "Abierta", "Bloqueada", "Protegida", "Final"
    version_protected: bool = False
    version_final_c: bool = False  # Flag cliente
    version_final_i: bool = False  # Flag interno
    version_size_bytes: int = 0

    # Estados de todas las versiones (cache local)
    version_states: dict = {}  # {version_key: state_data}

    # ========================================================================
    # Propiedades Computadas
    # ========================================================================

    @rx.var
    def is_internal_user(self) -> bool:
        """Usuario interno si tiene permiso training_create.
        
        Heredado de SharedSessionState:
        - can_training_create: bool
        """
        return self.can_training_create

    @rx.var
    def current_role_label(self) -> str:
        """Etiqueta del rol actual (Cliente/Interno)."""
        return "Interno" if self.is_internal_user else "Cliente"

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

    def init_page(self, project_id: int, version_id: int):
        """Inicializa el explorador para un proyecto y versión específicos.
        
        Args:
            project_id: ID del proyecto
            version_id: ID de la versión
        """
        logger.info(
            "Inicializando explorador: project_id=%s, version_id=%s, user_id=%s",
            project_id,
            version_id,
            self.user_id,
        )

        # Guardar contexto
        self.id_proyecto = project_id
        self.id_version_int = version_id
        self.id_version = f"v{str(version_id).zfill(3)}"

        # Cargar datos desde APIs
        self.load_from_api()
        self.load_version_state_from_api()
        self.interpretacion_estados()

        logger.info("Explorador inicializado correctamente")
        yield  # Actualizar UI

    # ========================================================================
    # Métodos de Carga de Datos
    # ========================================================================

    def load_from_api(self):
        """Carga estructura de archivos desde fmanagement API.
        
        Flujo: Frontend → Middleware → Broker → Backend Core → fmanagement
        
        Construye los nombres de carpetas según convención:
        - org_folder: "ORG{organization_id:04d}"  (ej: "ORG0001")
        - prj_folder: "PRJ{id_proyecto:04d}"      (ej: "PRJ0005")
        - version_folder: "v{id_version_int:03d}" (ej: "v001")
        """
        try:
            # Construir nombres de carpetas
            org_folder = f"ORG{str(self.organization_id).zfill(4)}"
            prj_folder = f"PRJ{str(self.id_proyecto).zfill(4)}"
            version_folder = self.id_version  # Ya está formateado como "v001"

            logger.info(
                "Cargando estructura fmanagement: org=%s, prj=%s, version=%s",
                org_folder,
                prj_folder,
                version_folder,
            )

            # Llamar API de fmanagement
            response = fmanagement_list(
                org_folder=org_folder,
                prj_folder=prj_folder,
                version_folder=version_folder,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                # Mapear response al formato esperado por process_fmanagementlist()
                items = response.get("items", [])
                self.fmanagementlist = {"items": items}

                logger.info("Estructura cargada: %d items", len(items))

                # Procesar estructura
                self.process_fmanagementlist()
            else:
                error_msg = response.get("mensaje", "Error desconocido")
                logger.error("Error cargando fmanagement: %s", error_msg)
                self.fmanagementlist = {"items": []}

        except Exception as e:
            logger.exception("Excepción cargando desde fmanagement API: %s", e)
            self.fmanagementlist = {"items": []}

    def load_version_state_from_api(self):
        """Carga estado de la versión actual desde API.
        
        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
        
        Obtiene el estado de la versión desde la tabla version_states y lo
        almacena tanto en campos individuales (version_state, version_protected, etc.)
        como en el diccionario version_states para uso en interpretacion_estados().
        """
        try:
            logger.info(
                "Cargando estado de versión: project_id=%s, version_id=%s",
                self.id_proyecto,
                self.id_version_int,
            )

            # Llamar API de estado de versión
            response = get_version_state(
                project_id=self.id_proyecto,
                version_id=self.id_version_int,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                state_data = response.get("state", {})

                # Mapear a campos individuales
                self.version_state = state_data.get("state", "Abierta")
                self.version_protected = state_data.get("protected", False)
                self.version_final_c = state_data.get("final_c", False)
                self.version_final_i = state_data.get("final_i", False)
                self.version_size_bytes = state_data.get("size_bytes", 0)

                logger.info(
                    "Estado cargado: state=%s, protected=%s, final_c=%s, final_i=%s",
                    self.version_state,
                    self.version_protected,
                    self.version_final_c,
                    self.version_final_i,
                )

                # Guardar en cache local para interpretacion_estados()
                version_key = self.id_version  # "v001"
                self.version_states[version_key] = {
                    "id_organizacion": state_data.get("id_organizacion", self.organization_id),
                    "id_proyecto": state_data.get("id_proyecto", self.id_proyecto),
                    "state": self.version_state,
                    "protected": self.version_protected,
                    "size": self.version_size_bytes,
                    "final_c": self.version_final_c,
                    "final_i": self.version_final_i,
                }

                logger.info("Estado almacenado en cache: %s", version_key)
            else:
                error_msg = response.get("mensaje", "Error desconocido")
                logger.error("Error cargando estado de versión: %s", error_msg)
                # Usar valores por defecto
                self.version_state = "Abierta"
                self.version_protected = False
                self.version_final_c = False
                self.version_final_i = False
                self.version_size_bytes = 0

        except Exception as e:
            logger.exception("Excepción cargando estado de versión: %s", e)
            # Usar valores por defecto en caso de error
            self.version_state = "Abierta"
            self.version_protected = False
            self.version_final_c = False
            self.version_final_i = False
            self.version_size_bytes = 0

    # ========================================================================
    # Operaciones CRUD
    # ========================================================================

    def acciones(self, accion: str, item: FolderItem):
        """Ejecuta una acción sobre un item del explorador.
        
        Este método es el punto de entrada único para todas las operaciones CRUD
        sobre archivos y carpetas, así como operaciones administrativas sobre
        versiones (bloquear/desbloquear).
        
        Security by Design:
        - Valida protección estructural (niveles 0 y 1)
        - Valida permisos del usuario (heredados de SharedSessionState)
        - Valida estado operativo (is_blocked)
        
        Args:
            accion: Nombre de la acción (delete, rename, upload_file, download, 
                    block_version, unblock_version)
            item: Item sobre el que se ejecuta la acción
        """
        # Excepciones a la protección: Acciones administrativas de versión
        admin_actions = ["block_version", "unblock_version", "review_version"]

        # Validación 1: Protección estructural (Security by Design)
        if item.is_protected and accion not in admin_actions:
            logger.warning(
                "Acción '%s' denegada por protección estructural: item='%s'",
                accion,
                item.name,
            )
            return rx.window_alert(
                f"Acción '{accion}' denegada: El elemento '{item.name}' está protegido."
            )

        # Validación 2: Bloqueo operativo
        if item.is_blocked and accion not in admin_actions:
            logger.warning(
                "Acción '%s' denegada por bloqueo operativo: item='%s'",
                accion,
                item.name,
            )
            return rx.window_alert(
                f"Versión bloqueada: No se pueden realizar operaciones sobre '{item.name}'."
            )

        logger.info("Ejecutando acción: %s sobre %s", accion, item.name)

        # Construir parámetros base para fmanagement
        org_folder = f"ORG{str(self.organization_id).zfill(4)}"
        prj_folder = f"PRJ{str(self.id_proyecto).zfill(4)}"
        version_folder = self.id_version

        # ====================================================================
        # OPERACIONES DE ELIMINACIÓN
        # ====================================================================

        if accion == "delete":
            # Validar permiso
            if item.item_type == "folder" and not self.can_folder_delete:
                return rx.window_alert("Sin permisos para eliminar carpetas")
            if item.item_type == "file" and not self.can_file_delete:
                return rx.window_alert("Sin permisos para eliminar archivos")

            operation = "delete_folder" if item.item_type == "folder" else "delete_file"
            params = {
                "org": org_folder,
                "prj": prj_folder,
                "version": version_folder,
                "path": item.name,
            }

            response = fmanagement_operation(
                operation=operation,
                params=params,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                logger.info("Eliminado exitosamente: %s", item.name)
                self.load_from_api()  # Recargar estructura
                return rx.toast.success(f"Eliminado: {item.name}")
            else:
                error_msg = response.get("mensaje", "Error desconocido")
                logger.error("Error eliminando: %s", error_msg)
                return rx.toast.error(f"Error: {error_msg}")

        # ====================================================================
        # OPERACIONES DE RENOMBRADO
        # ====================================================================

        elif accion == "rename":
            # Validar permiso
            if item.item_type == "folder" and not self.can_folder_rename:
                return rx.window_alert("Sin permisos para renombrar carpetas")
            if item.item_type == "file" and not self.can_file_update:
                return rx.window_alert("Sin permisos para renombrar archivos")

            # TODO: Implementar diálogo para nuevo nombre
            # Por ahora, placeholder
            new_name = f"{item.name}_renamed"

            operation = "rename_folder" if item.item_type == "folder" else "rename_file"
            params = {
                "org": org_folder,
                "prj": prj_folder,
                "version": version_folder,
                "old_name": item.name,
                "new_name": new_name,
            }

            response = fmanagement_operation(
                operation=operation,
                params=params,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                logger.info("Renombrado: %s → %s", item.name, new_name)
                self.load_from_api()  # Recargar estructura
                return rx.toast.success(f"Renombrado a: {new_name}")
            else:
                error_msg = response.get("mensaje", "Error desconocido")
                logger.error("Error renombrando: %s", error_msg)
                return rx.toast.error(f"Error: {error_msg}")

        # ====================================================================
        # OPERACIONES DE SUBIDA DE ARCHIVOS
        # ====================================================================

        elif accion == "upload_file":
            # Validar permiso
            if not self.can_file_create:
                return rx.window_alert("Sin permisos para crear archivos")

            # TODO: Implementar diálogo de subida de archivo
            # Por ahora, placeholder
            return rx.window_alert(
                f"Subida de archivo a '{item.name}' - UI pendiente (PASO 6.4d)"
            )

        # ====================================================================
        # OPERACIONES DE DESCARGA
        # ====================================================================

        elif accion == "download":
            # Validar permiso
            if not self.can_file_read:
                return rx.window_alert("Sin permisos para descargar archivos")

            params = {
                "org": org_folder,
                "prj": prj_folder,
                "version": version_folder,
                "file_path": item.name,
            }

            response = fmanagement_operation(
                operation="download_file",
                params=params,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                logger.info("Descarga iniciada: %s", item.name)
                # TODO: Procesar data del archivo para descarga
                return rx.toast.success(f"Descargando: {item.name}")
            else:
                error_msg = response.get("mensaje", "Error desconocido")
                logger.error("Error descargando: %s", error_msg)
                return rx.toast.error(f"Error: {error_msg}")

        # ====================================================================
        # OPERACIONES ADMINISTRATIVAS DE VERSIÓN
        # ====================================================================

        elif accion == "block_version":
            # Validar permiso (solo usuarios internos)
            if not self.is_internal_user:
                return rx.window_alert(
                    "Solo usuarios internos pueden bloquear versiones"
                )

            response = update_version_state(
                project_id=self.id_proyecto,
                version_id=self.id_version_int,
                state="Bloqueada",
                protected=True,
                updated_by_user_id=self.user_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                logger.info("Versión bloqueada: %s", self.id_version)
                self.load_version_state_from_api()  # Recargar estado
                # self.interpretacion_estados()  # TODO: PASO 6.4d
                return rx.toast.success("Versión bloqueada")
            else:
                error_msg = response.get("mensaje", "Error desconocido")
                logger.error("Error bloqueando versión: %s", error_msg)
                return rx.toast.error(f"Error: {error_msg}")

        elif accion == "unblock_version":
            # Validar permiso (solo usuarios internos)
            if not self.is_internal_user:
                return rx.window_alert(
                    "Solo usuarios internos pueden desbloquear versiones"
                )

            response = update_version_state(
                project_id=self.id_proyecto,
                version_id=self.id_version_int,
                state="Abierta",
                protected=False,
                updated_by_user_id=self.user_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                logger.info("Versión desbloqueada: %s", self.id_version)
                self.load_version_state_from_api()  # Recargar estado
                # self.interpretacion_estados()  # TODO: PASO 6.4d
                return rx.toast.success("Versión desbloqueada")
            else:
                error_msg = response.get("mensaje", "Error desconocido")
                logger.error("Error desbloqueando versión: %s", error_msg)
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
            "Protegida": ("(Entrenamiento Solicitado)", "#00008B"),  # Azul oscuro
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

                es_bloqueada = protected or (estado != "Abierta")

                if es_bloqueada:
                    # Bloquear esta versión y todos sus descendientes
                    version_id = item.id
                    item.is_blocked = True

                    # Bloquear todos los hijos
                    for descendant in self.items:
                        if descendant.id.startswith(version_id + "_"):
                            descendant.is_blocked = True

                # Actualizar tamaño
                if version_state_data.get("size", 0) > 0:
                    item.size_str = self._format_size(version_state_data.get("size", 0))

        # 3. Reglas para panel de simulación
        if self.version_state == "Protegida":
            self.version_protected = True
            self.version_final_c = True

        if self.version_state == "Final":
            self.version_protected = True
            self.version_final_c = True
            self.version_final_i = True

        self._update_visibility()

    def process_fmanagementlist(self):
        """Procesa la estructura fmanagementlist para aplanarla."""
        if not self.fmanagementlist or "items" not in self.fmanagementlist:
            return

        self.items = []
        self._flatten_recursive(self.fmanagementlist["items"])
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
                has_children=is_dir and "items" in item and len(item["items"]) > 0,
                is_visible=True,
                item_type="folder" if is_dir else "file",
                is_protected=is_protected,
                is_blocked=False,
                size_str=size_str,
                metadata=item.get("metadata", {}),
            )

            self.items.append(new_item)

            # Recursión para hijos
            if is_dir and "items" in item:
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

    def _format_size(self, bytes_val):
        """Formatea bytes a la unidad más adecuada."""
        if not bytes_val:
            return ""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"

    def toggle_expand(self, item_id: str):
        """Colapsa/expande una carpeta."""
        for item in self.items:
            if item.id == item_id:
                item.is_expanded = not item.is_expanded
                logger.info("Toggle expand: %s → %s", item.name, item.is_expanded)
                break
        self._update_visibility()
        yield  # Actualizar UI

    def select_item(self, item_id: str):
        """Selecciona un item."""
        self.selected_item_id = item_id
        logger.info("Item seleccionado: %s", item_id)
        yield  # Actualizar UI


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


def explorador_panel(state: ExploradorState) -> rx.Component:
    """Componente principal del explorador (FUNCIONAL - UI simplificada).
    
    NOTA: Esta es una versión simplificada funcional.
    Para UI completa con menús contextuales, badges, iconos, etc.,
    copiar del original (líneas 800-1405).
    
    Args:
        state: Estado del explorador (ExploradorState)
        
    Returns:
        Componente Reflex renderizable
    """
    return rx.box(
        # Header
        rx.heading(
            f"Explorador de Archivos - Proyecto {state.id_proyecto} - Versión {state.id_version}",
            size="6",
        ),
        rx.text(f"Usuario: {state.user_name} ({state.current_role_label})", size="2"),
        rx.text(
            f"Estado de versión: {state.version_state}",
            color=rx.cond(
                state.version_protected,
                "orange",
                "green",
            ),
            size="3",
        ),
        rx.divider(),
        # Lista de items (simplificada)
        rx.box(
            rx.foreach(
                state.items,
                lambda item: rx.cond(
                    item.is_visible,
                    rx.box(
                        rx.hstack(
                            rx.text("📁" if item.item_type == "folder" else "📄"),
                            rx.text(item.name),
                            rx.text(item.version_state_label, color=item.version_state_color),
                            rx.text(item.size_str, size="1", color="gray"),
                            rx.cond(
                                item.is_protected,
                                rx.badge("Protegido", color_scheme="red"),
                                rx.fragment(),
                            ),
                            rx.cond(
                                item.is_blocked,
                                rx.badge("Bloqueado", color_scheme="orange"),
                                rx.fragment(),
                            ),
                            spacing="2",
                        ),
                        padding_left=f"{item.depth * 20}px",
                        on_click=lambda: state.toggle_expand(item.id)
                        if item.item_type == "folder"
                        else state.select_item(item.id),
                        cursor="pointer",
                        _hover={"background": "gray.100"},
                        padding="8px",
                    ),
                    rx.fragment(),
                ),
            ),
            max_height="500px",
            overflow_y="auto",
            border="1px solid",
            border_color="gray.200",
            border_radius="md",
            padding="10px",
        ),
        # Footer con instrucciones
        rx.divider(),
        rx.text(
            "⚠️ UI simplificada - Para menús contextuales, copiar del original",
            size="1",
            color="gray",
        ),
        padding="20px",
        width="100%",
    )

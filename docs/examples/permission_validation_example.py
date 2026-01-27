"""
Ejemplo de validación de permisos en menú contextual.

Este archivo demuestra cómo usar los permisos de bajo nivel almacenados
en SharedSessionState para mostrar/ocultar opciones en un menú contextual.

Los permisos se cargan automáticamente durante el login y están disponibles
en el estado compartido vía Redis.

IMPORTANTE: Los nombres de permisos coinciden EXACTAMENTE con low_level_permissions.json
Ver también: docs/examples/permission_validation_from_session.py para más ejemplos.

Uso:
    - Los permisos están en State.can_<permission_name>
    - Ejemplo: State.can_folder_rename, State.can_file_delete, etc.
    - Validación dinámica: State.has_permission("folder_rename")
"""
import reflex as rx
from typing import List

# Importar el estado compartido (hereda de SharedSessionState)
# En la aplicación real sería: from web_frontend.web_frontend import State
# Aquí mostramos la estructura para referencia


class ExampleMenuState(rx.State):
    """
    Estado de ejemplo que hereda permisos de SharedSessionState.
    
    En la aplicación real, el State del frontend ya hereda estos campos
    (nombres alineados con low_level_permissions.json):
    
    Carpetas: can_folder_create, can_folder_delete, can_folder_rename, can_folder_read, can_folder_list
    Ficheros: can_file_create, can_file_read, can_file_update, can_file_delete, can_file_list
    Proyectos: can_project_create, can_project_read, can_project_update, can_project_delete, can_project_list
    Versiones: can_version_create, can_version_read, can_version_update, can_version_delete, can_version_list
    Entrenamiento: can_training_create, can_training_read, can_training_update, can_training_delete, can_training_start, can_training_stop
    Parámetros: can_parameters_create, can_parameters_read, can_parameters_update, can_parameters_delete
    Notificaciones: can_notifications_create, can_notifications_read, can_notifications_update, can_notifications_delete
    Usuarios: can_user_create, can_user_read, can_user_update, can_user_delete, can_user_enable, can_user_disable
    """
    
    # Estos campos vienen de SharedSessionState (solo para referencia)
    # Nombres alineados con low_level_permissions.json
    can_folder_create: bool = False
    can_folder_delete: bool = False
    can_folder_rename: bool = False
    can_folder_read: bool = False
    can_folder_list: bool = False
    can_file_create: bool = False
    can_file_read: bool = False
    can_file_update: bool = False
    can_file_delete: bool = False
    can_file_list: bool = False
    
    # Estado del menú contextual
    show_context_menu: bool = False
    selected_item: str = ""
    selected_item_type: str = ""  # "folder" o "file"
    
    def show_menu(self, item_name: str, item_type: str):
        """Muestra el menú contextual para un item."""
        self.selected_item = item_name
        self.selected_item_type = item_type
        self.show_context_menu = True
    
    def hide_menu(self):
        """Oculta el menú contextual."""
        self.show_context_menu = False
        self.selected_item = ""
        self.selected_item_type = ""
    
    def rename_item(self):
        """Renombra el item seleccionado (requiere permiso)."""
        # La validación del permiso ya se hizo en el frontend al mostrar la opción
        # Pero también se valida en el backend al ejecutar la acción
        print(f"Renombrando {self.selected_item_type}: {self.selected_item}")
        self.hide_menu()
    
    def delete_item(self):
        """Elimina el item seleccionado (requiere permiso)."""
        print(f"Eliminando {self.selected_item_type}: {self.selected_item}")
        self.hide_menu()


def context_menu_option(
    label: str,
    icon: str,
    on_click: callable,
    is_visible: rx.Var[bool],
) -> rx.Component:
    """
    Crea una opción de menú contextual que solo se muestra si el usuario tiene permiso.
    
    Args:
        label: Texto de la opción
        icon: Icono de la opción (emoji o nombre de icono)
        on_click: Handler al hacer clic
        is_visible: Var booleano que indica si el usuario tiene permiso
    
    Returns:
        Componente de opción de menú (o vacío si no tiene permiso)
    """
    return rx.cond(
        is_visible,
        rx.menu.item(
            rx.hstack(
                rx.text(icon, size="2"),
                rx.text(label, size="2"),
                spacing="2",
                align="center",
            ),
            on_click=on_click,
            cursor="pointer",
        ),
        rx.fragment(),  # No renderiza nada si no tiene permiso
    )


def folder_context_menu(state: ExampleMenuState) -> rx.Component:
    """
    Menú contextual para carpetas con opciones basadas en permisos.
    
    Las opciones se muestran/ocultan según los permisos del usuario:
    - Renombrar: requiere can_folder_rename
    - Eliminar: requiere can_folder_delete
    - Nueva subcarpeta: requiere can_folder_create
    """
    return rx.menu.root(
        rx.menu.trigger(
            rx.button(
                "⋮",
                variant="ghost",
                size="1",
            )
        ),
        rx.menu.content(
            # Opción "Renombrar" - Solo visible si can_folder_rename es True
            context_menu_option(
                label="Renombrar carpeta",
                icon="✏️",
                on_click=state.rename_item,
                is_visible=state.can_folder_rename,
            ),
            
            # Opción "Eliminar" - Solo visible si can_folder_delete es True
            context_menu_option(
                label="Eliminar carpeta",
                icon="🗑️",
                on_click=state.delete_item,
                is_visible=state.can_folder_delete,
            ),
            
            # Opción "Nueva subcarpeta" - Solo visible si can_folder_create es True
            context_menu_option(
                label="Nueva subcarpeta",
                icon="📁",
                on_click=state.hide_menu,  # Placeholder
                is_visible=state.can_folder_create,
            ),
            
            # Separador si hay al menos una opción de movimiento
            rx.cond(
                state.can_file_move,
                rx.menu.separator(),
                rx.fragment(),
            ),
            
            # Opción "Mover" - Solo visible si can_file_move es True
            context_menu_option(
                label="Mover a...",
                icon="📦",
                on_click=state.hide_menu,  # Placeholder
                is_visible=state.can_file_move,
            ),
        ),
    )


def file_context_menu(state: ExampleMenuState) -> rx.Component:
    """
    Menú contextual para archivos con opciones basadas en permisos.
    
    Las opciones se muestran/ocultan según los permisos del usuario:
    - Renombrar: requiere can_file_rename
    - Eliminar: requiere can_file_delete
    - Mover: requiere can_file_move
    """
    return rx.menu.root(
        rx.menu.trigger(
            rx.button(
                "⋮",
                variant="ghost",
                size="1",
            )
        ),
        rx.menu.content(
            # Opción "Renombrar" - Solo visible si can_file_rename es True
            context_menu_option(
                label="Renombrar archivo",
                icon="✏️",
                on_click=state.rename_item,
                is_visible=state.can_file_rename,
            ),
            
            # Opción "Eliminar" - Solo visible si can_file_delete es True
            context_menu_option(
                label="Eliminar archivo",
                icon="🗑️",
                on_click=state.delete_item,
                is_visible=state.can_file_delete,
            ),
            
            # Opción "Mover" - Solo visible si can_file_move es True
            context_menu_option(
                label="Mover a...",
                icon="📦",
                on_click=state.hide_menu,  # Placeholder
                is_visible=state.can_file_move,
            ),
        ),
    )


def example_folder_list() -> rx.Component:
    """
    Ejemplo de lista de carpetas con menú contextual basado en permisos.
    
    Cada carpeta tiene un menú contextual que muestra solo las opciones
    para las que el usuario tiene permisos.
    """
    # Datos de ejemplo
    folders = ["Documentos", "Imágenes", "Proyectos"]
    
    return rx.vstack(
        rx.heading("Explorador de archivos", size="4"),
        rx.text(
            "Las opciones del menú contextual se muestran según tus permisos.",
            size="2",
            color="gray",
        ),
        rx.divider(),
        
        # Lista de carpetas
        rx.foreach(
            folders,
            lambda folder_name: rx.hstack(
                rx.icon("folder", size=20),
                rx.text(folder_name, flex="1"),
                folder_context_menu(ExampleMenuState),
                padding="2",
                border_radius="md",
                _hover={"background": "gray.100"},
                width="100%",
            ),
        ),
        
        spacing="3",
        padding="4",
        width="100%",
        max_width="400px",
    )


# ============================================================
# VALIDACIÓN EN BACKEND (complemento a la validación frontend)
# ============================================================

def validate_permission_backend_example():
    """
    Ejemplo de validación de permisos en el backend.
    
    Aunque el frontend oculta las opciones sin permiso, el backend
    SIEMPRE debe validar los permisos antes de ejecutar una acción.
    
    El middleware proporciona el método has_low_level_permission():
    
    ```python
    # En routermiddleware.py
    def has_low_level_permission(
        self, session: SessionContext, permission_key: str
    ) -> bool:
        '''Valida un permiso de bajo nivel usando el contexto de sesión.'''
        
        if not permission_key:
            return False
        permissions = self._get_low_level_permissions_for_role(
            session.identity_type_id
        )
        value = permissions.get(permission_key)
        allowed = bool(value)
        self._logger.info(
            "Permiso bajo nivel user_id=%s org_id=%s role_id=%s key=%s allowed=%s",
            session.user_id,
            session.organization_id,
            session.identity_type_id,
            permission_key,
            allowed,
        )
        return allowed
    ```
    
    Uso en un endpoint del middleware:
    
    ```python
    @app.post("/folders/{folder_id}/rename")
    async def rename_folder(
        folder_id: int,
        new_name: str,
        router: RouterMiddleware = Depends(get_router_middleware),
        session: SessionContext = Depends(get_session_context),
    ):
        # Validar permiso antes de ejecutar
        if not router.has_low_level_permission(session, "folder_rename"):
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para renombrar carpetas"
            )
        
        # Ejecutar la acción delegando a fmanagement
        # ...
    ```
    """
    pass


# ============================================================
# LISTA DE PERMISOS DISPONIBLES EN SharedSessionState
# ============================================================

AVAILABLE_PERMISSIONS = """
Permisos de bajo nivel disponibles en SharedSessionState:

GESTIÓN DE DATOS:
- can_data_read
- can_data_write
- can_data_delete

GESTIÓN DE CARPETAS:
- can_folder_create
- can_folder_rename    ← Ejemplo del usuario
- can_folder_delete
- can_folder_move
- can_folder_list

GESTIÓN DE FICHEROS:
- can_file_upload
- can_file_download
- can_file_delete
- can_file_rename
- can_file_move
- can_file_read

GESTIÓN DE ENTRENAMIENTO:
- can_training_create
- can_training_execute
- can_training_monitor
- can_training_stop
- can_training_delete

GESTIÓN DE MODELOS:
- can_model_create
- can_model_read
- can_model_update
- can_model_delete
- can_model_publish
- can_model_download

GESTIÓN DE DATASETS:
- can_dataset_create
- can_dataset_read
- can_dataset_update
- can_dataset_delete
- can_dataset_validate

GESTIÓN DE USUARIOS:
- can_user_create
- can_user_read
- can_user_update
- can_user_delete
- can_user_activate
- can_user_deactivate

GESTIÓN DE ROLES:
- can_role_assign
- can_role_revoke
- can_role_create
- can_role_delete

GESTIÓN DE ORGANIZACIÓN:
- can_org_create
- can_org_read
- can_org_update
- can_org_delete

TOTAL: 45 permisos de bajo nivel
"""

if __name__ == "__main__":
    print(AVAILABLE_PERMISSIONS)

"""
Mapeo de acciones del explorador a permisos de la tabla low_level_permissions.

Este módulo define la relación entre las acciones que un usuario puede realizar
en el explorador (menú contextual) y los permisos requeridos en la base de datos.

Campos en la tabla low_level_permissions (MariaDB myllm_core_db):
================================================

CARPETAS (folders):
- folder_create: Crear nueva carpeta
- folder_delete: Eliminar carpeta
- folder_rename: Renombrar carpeta
- folder_read: Leer contenido/propiedades de carpeta
- folder_list: Listar carpetas

ARCHIVOS (files):
- file_create: Crear/subir archivo
- file_read: Leer/descargar archivo
- file_update: Modificar/renombrar archivo existente
- file_delete: Eliminar archivo
- file_list: Listar archivos

PROYECTOS:
- project_create, project_read, project_update, project_delete, project_list

VERSIONES:
- version_create, version_read, version_update, version_delete, version_list

ENTRENAMIENTO:
- training_create, training_read, training_update, training_delete
- training_start, training_stop

PARÁMETROS:
- parameters_create, parameters_read, parameters_update, parameters_delete

NOTIFICACIONES:
- notifications_create, notifications_read, notifications_update, notifications_delete

USUARIOS:
- user_create, user_read, user_update, user_delete, user_enable, user_disable
"""

from typing import Final

# ============================================================================
# MAPEO: Acción del explorador → Permiso requerido
# ============================================================================

# Mapeo para CARPETAS (folders)
FOLDER_ACTION_TO_PERMISSION: Final[dict[str, str]] = {
    "create_folder": "folder_create",      # Crear nueva carpeta dentro de esta
    "rename": "folder_rename",             # Renombrar la carpeta
    "delete": "folder_delete",             # Eliminar la carpeta
    "properties": "folder_read",           # Ver propiedades de la carpeta
    "download": "folder_read",             # Descargar carpeta comprimida
}

# Mapeo para ARCHIVOS (files)
FILE_ACTION_TO_PERMISSION: Final[dict[str, str]] = {
    "upload_file": "file_create",          # Subir nuevo archivo
    "rename": "file_update",               # Renombrar archivo (es update porque el archivo ya existe)
    "delete": "file_delete",               # Eliminar archivo
    "download": "file_read",               # Descargar archivo
    "properties": "file_read",             # Ver propiedades del archivo
    "edit": "file_update",                 # Editar contenido del archivo
}

# Mapeo completo (unión de carpetas y archivos)
ACTION_TO_PERMISSION: Final[dict[str, tuple[str, str]]] = {
    # Formato: "accion": ("permiso_folder", "permiso_file")
    # Si solo aplica a uno, el otro es ""
    "create_folder": ("folder_create", ""),
    "upload_file": ("", "file_create"),
    "rename": ("folder_rename", "file_update"),
    "delete": ("folder_delete", "file_delete"),
    "download": ("folder_read", "file_read"),
    "properties": ("folder_read", "file_read"),
    "edit": ("", "file_update"),
}


# ============================================================================
# FUNCIONES DE AYUDA
# ============================================================================

def get_required_permission(action: str, item_type: str) -> str | None:
    """
    Obtiene el permiso requerido para una acción sobre un tipo de item.

    Args:
        action: Nombre de la acción (ej: "create_folder", "rename", "delete")
        item_type: Tipo de item ("folder" o "file")

    Returns:
        Nombre del permiso requerido (ej: "folder_create") o None si no se encuentra

    Example:
        >>> get_required_permission("create_folder", "folder")
        'folder_create'
        >>> get_required_permission("rename", "file")
        'file_update'
    """
    if action not in ACTION_TO_PERMISSION:
        return None

    folder_perm, file_perm = ACTION_TO_PERMISSION[action]

    if item_type == "folder":
        return folder_perm if folder_perm else None
    elif item_type == "file":
        return file_perm if file_perm else None

    return None


def get_all_folder_permissions() -> list[str]:
    """Retorna lista de todos los permisos relacionados con carpetas."""
    return [
        "folder_create",
        "folder_delete",
        "folder_rename",
        "folder_read",
        "folder_list",
    ]


def get_all_file_permissions() -> list[str]:
    """Retorna lista de todos los permisos relacionados con archivos."""
    return [
        "file_create",
        "file_read",
        "file_update",
        "file_delete",
        "file_list",
    ]


def get_all_explorador_permissions() -> list[str]:
    """Retorna lista de todos los permisos usados en el explorador."""
    return get_all_folder_permissions() + get_all_file_permissions()


# ============================================================================
# MAPEO DETALLADO: Acción → Descripción → Permiso
# ============================================================================

EXPLORADOR_ACTIONS_DETAIL: Final[list[dict[str, str]]] = [
    # === ACCIONES DE CARPETAS ===
    {
        "action": "create_folder",
        "display_name": "Crear Carpeta",
        "description": "Crear una nueva carpeta dentro de esta ubicación",
        "permission": "folder_create",
        "applies_to": "folder",
        "icon": "folder-plus",
    },
    {
        "action": "rename",
        "display_name": "Renombrar",
        "description": "Cambiar el nombre de la carpeta",
        "permission": "folder_rename",
        "applies_to": "folder",
        "icon": "edit",
    },
    {
        "action": "delete",
        "display_name": "Eliminar",
        "description": "Eliminar la carpeta y todo su contenido",
        "permission": "folder_delete",
        "applies_to": "folder",
        "icon": "trash",
    },
    {
        "action": "properties",
        "display_name": "Propiedades",
        "description": "Ver información detallada de la carpeta",
        "permission": "folder_read",
        "applies_to": "folder",
        "icon": "info",
    },
    {
        "action": "download",
        "display_name": "Descargar",
        "description": "Descargar carpeta como archivo comprimido",
        "permission": "folder_read",
        "applies_to": "folder",
        "icon": "download",
    },
    # === ACCIONES DE ARCHIVOS ===
    {
        "action": "upload_file",
        "display_name": "Subir Archivo",
        "description": "Subir un nuevo archivo a esta ubicación",
        "permission": "file_create",
        "applies_to": "folder",  # Se ejecuta en carpeta pero crea archivo
        "icon": "upload",
    },
    {
        "action": "rename",
        "display_name": "Renombrar",
        "description": "Cambiar el nombre del archivo",
        "permission": "file_update",
        "applies_to": "file",
        "icon": "edit",
    },
    {
        "action": "delete",
        "display_name": "Eliminar",
        "description": "Eliminar el archivo",
        "permission": "file_delete",
        "applies_to": "file",
        "icon": "trash",
    },
    {
        "action": "download",
        "display_name": "Descargar",
        "description": "Descargar el archivo",
        "permission": "file_read",
        "applies_to": "file",
        "icon": "download",
    },
    {
        "action": "properties",
        "display_name": "Propiedades",
        "description": "Ver información detallada del archivo",
        "permission": "file_read",
        "applies_to": "file",
        "icon": "info",
    },
    {
        "action": "edit",
        "display_name": "Editar",
        "description": "Editar el contenido del archivo",
        "permission": "file_update",
        "applies_to": "file",
        "icon": "edit-2",
    },
]


def get_action_details(action: str, item_type: str) -> dict[str, str] | None:
    """
    Obtiene los detalles completos de una acción.

    Args:
        action: Nombre de la acción
        item_type: Tipo de item ("folder" o "file")

    Returns:
        Diccionario con detalles de la acción o None si no se encuentra
    """
    for detail in EXPLORADOR_ACTIONS_DETAIL:
        if detail["action"] == action and detail["applies_to"] == item_type:
            return detail
    return None


# ============================================================================
# VALIDACIÓN: Verificar si una acción está permitida
# ============================================================================

def is_action_allowed(
    action: str,
    item_type: str,
    user_permissions: dict[str, bool],
) -> bool:
    """
    Verifica si un usuario puede realizar una acción basándose en sus permisos.

    Args:
        action: Nombre de la acción (ej: "create_folder")
        item_type: Tipo de item ("folder" o "file")
        user_permissions: Diccionario de permisos del usuario
                          {permission_key: bool}

    Returns:
        True si la acción está permitida, False en caso contrario

    Example:
        >>> perms = {"folder_create": True, "folder_delete": False}
        >>> is_action_allowed("create_folder", "folder", perms)
        True
        >>> is_action_allowed("delete", "folder", perms)
        False
    """
    required_permission = get_required_permission(action, item_type)

    if not required_permission:
        # Acción no reconocida o no tiene permiso asociado
        return False

    return user_permissions.get(required_permission, False)


def filter_allowed_actions(
    actions: list[str],
    item_type: str,
    user_permissions: dict[str, bool],
) -> list[str]:
    """
    Filtra una lista de acciones para retornar solo las permitidas.

    Args:
        actions: Lista de nombres de acciones
        item_type: Tipo de item ("folder" o "file")
        user_permissions: Diccionario de permisos del usuario

    Returns:
        Lista de acciones permitidas

    Example:
        >>> actions = ["create_folder", "rename", "delete"]
        >>> perms = {"folder_create": True, "folder_rename": True, "folder_delete": False}
        >>> filter_allowed_actions(actions, "folder", perms)
        ['create_folder', 'rename']
    """
    return [
        action
        for action in actions
        if is_action_allowed(action, item_type, user_permissions)
    ]

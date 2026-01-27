"""
Ejemplo: Validación de permisos desde datos de sesión.

Este ejemplo muestra cómo validar permisos usando los datos de sesión
o el contenido del token JWT para mostrar/ocultar opciones en la UI.

Caso de uso típico: Mostrar opción "Renombrar carpeta" en un menú
contextual solo si el usuario tiene el permiso folder_rename=True.

Los nombres de permisos coinciden EXACTAMENTE con low_level_permissions.json.
"""

import reflex as rx
from web_frontend.shared_state import SharedSessionState


# ==============================================================================
# EJEMPLO 1: Validación simple de un permiso específico
# ==============================================================================

def menu_contextual_carpeta(state: SharedSessionState):
    """
    Menú contextual de carpeta que muestra opciones según permisos.
    
    Caso de uso del usuario:
    "mostrar un menu contextual la opcion de renombrar una carpeta
    y hemos de validar con los datos de sesion o con el token si ese
    usuario para esa organizacion tiene en low_level_permissions
    el campo o atributo folder_rename a true"
    """
    opciones = []
    
    # Verificar permiso folder_rename directamente desde el estado de sesión
    if state.can_folder_rename:
        opciones.append("Renombrar carpeta")
    
    if state.can_folder_delete:
        opciones.append("Eliminar carpeta")
    
    if state.can_folder_create:
        opciones.append("Crear subcarpeta")
    
    # Solo mostrar el menú si hay al menos una opción disponible
    if state.can_folder_read:
        opciones.append("Ver propiedades")
    
    return opciones


# ==============================================================================
# EJEMPLO 2: Validación usando el método has_permission()
# ==============================================================================

def menu_contextual_archivo(state: SharedSessionState):
    """
    Menú contextual de archivo usando validación dinámica.
    
    El método has_permission() permite validar permisos usando
    el nombre exacto del permiso como aparece en low_level_permissions.json.
    """
    opciones = []
    
    # Validación dinámica por nombre de permiso
    if state.has_permission("file_read"):
        opciones.append("Abrir")
    
    if state.has_permission("file_update"):
        opciones.append("Editar")
    
    if state.has_permission("file_delete"):
        opciones.append("Eliminar")
    
    # Verificar permiso que no existe - retorna False
    if state.has_permission("file_copy"):  # No existe este permiso
        opciones.append("Copiar")  # No se añade
    
    return opciones


# ==============================================================================
# EJEMPLO 3: Verificar múltiples permisos
# ==============================================================================

def puede_gestionar_proyecto_completo(state: SharedSessionState) -> bool:
    """
    Verifica si el usuario puede gestionar un proyecto completo.
    
    Requiere todos los permisos necesarios para crear y configurar
    un proyecto con carpetas y archivos.
    """
    permisos_necesarios = [
        "project_create",
        "folder_create",
        "file_create",
        "version_create",
    ]
    
    return state.has_all_permissions(permisos_necesarios)


def mostrar_seccion_entrenamiento(state: SharedSessionState) -> bool:
    """
    Determina si mostrar la sección de entrenamiento.
    
    Se muestra si el usuario tiene cualquier permiso de entrenamiento.
    """
    permisos_entrenamiento = [
        "training_create",
        "training_read",
        "training_start",
        "training_stop",
    ]
    
    return state.has_any_permission(permisos_entrenamiento)


# ==============================================================================
# EJEMPLO 4: Componente Reflex con validación de permisos
# ==============================================================================

def folder_context_menu(state: SharedSessionState, folder_name: str):
    """
    Componente Reflex que renderiza un menú contextual de carpeta.
    
    Las opciones se muestran condicionalmente según los permisos del usuario.
    """
    return rx.menu.root(
        rx.menu.trigger(
            rx.button(folder_name, variant="ghost")
        ),
        rx.menu.content(
            # Opción "Renombrar" - solo si tiene permiso folder_rename
            rx.cond(
                state.can_folder_rename,
                rx.menu.item("Renombrar"),
            ),
            # Opción "Eliminar" - solo si tiene permiso folder_delete
            rx.cond(
                state.can_folder_delete,
                rx.menu.item("Eliminar", color="red"),
            ),
            # Opción "Crear subcarpeta" - solo si tiene permiso folder_create
            rx.cond(
                state.can_folder_create,
                rx.menu.item("Crear subcarpeta"),
            ),
            # Separador solo si hay opciones de modificación
            rx.cond(
                state.can_manage_folders,  # Propiedad compuesta
                rx.menu.separator(),
            ),
            # Opción "Propiedades" - siempre visible si puede leer
            rx.cond(
                state.can_folder_read,
                rx.menu.item("Propiedades"),
            ),
        ),
    )


# ==============================================================================
# EJEMPLO 5: Logging de permisos para debugging
# ==============================================================================

def log_permisos_usuario(state: SharedSessionState):
    """
    Registra los permisos del usuario para debugging.
    
    Útil para verificar qué permisos tiene el usuario actual.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not state.is_logged_in:
        logger.info("Usuario no autenticado - sin permisos")
        return
    
    # Obtener todos los permisos como diccionario
    todos_permisos = state.get_all_permissions()
    
    # Filtrar solo los permisos activos (True)
    permisos_activos = {k: v for k, v in todos_permisos.items() if v}
    
    logger.info(
        f"Usuario {state.user_name} (org: {state.organization_id}, "
        f"role: {state.identity_type_id}) - "
        f"Permisos activos: {list(permisos_activos.keys())}"
    )


# ==============================================================================
# EJEMPLO 6: Validación desde el JWT (para referencia)
# ==============================================================================

def extraer_permisos_desde_jwt(token: str) -> dict:
    """
    Nota: En la arquitectura actual, el JWT NO contiene los permisos directamente.
    
    El JWT solo contiene:
    - user_id
    - organization_id
    - identity_type_id (rol)
    - session_id
    - exp, iat, jti
    
    Los permisos se obtienen consultando al middleware con:
    - GET /auth/permissions (con access_token y session_token)
    
    El middleware usa el identity_type_id para buscar los permisos en:
    - roles.json → obtiene identity_type_group_permissions
    - low_level_permissions.json → obtiene los permisos específicos
    
    Esto permite que los permisos puedan cambiar sin invalidar el JWT.
    """
    import json
    import base64
    
    # Decodificar payload del JWT (solo para referencia)
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    
    payload = parts[1]
    padded = payload + "=" * (-len(payload) % 4)
    data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    
    # El JWT contiene el identity_type_id que determina los permisos
    return {
        "user_id": data.get("user_id"),
        "organization_id": data.get("organization_id"),
        "identity_type_id": data.get("identity_type_id"),  # El rol/tipo de identidad
        # NO contiene los permisos individuales
    }


# ==============================================================================
# EJEMPLO 7: Tabla de referencia de permisos
# ==============================================================================

"""
Referencia de permisos disponibles en low_level_permissions.json:

CARPETAS:
- folder_create    : Crear carpetas
- folder_delete    : Eliminar carpetas
- folder_rename    : Renombrar carpetas
- folder_read      : Ver contenido de carpetas
- folder_list      : Listar carpetas

FICHEROS:
- file_create      : Crear/subir ficheros
- file_read        : Leer contenido de ficheros
- file_update      : Modificar ficheros
- file_delete      : Eliminar ficheros
- file_list        : Listar ficheros

PROYECTOS:
- project_create   : Crear proyectos
- project_read     : Ver proyectos
- project_update   : Modificar proyectos
- project_delete   : Eliminar proyectos
- project_list     : Listar proyectos

VERSIONES:
- version_create   : Crear versiones
- version_read     : Ver versiones
- version_update   : Modificar versiones
- version_delete   : Eliminar versiones
- version_list     : Listar versiones

ENTRENAMIENTO:
- training_create  : Crear entrenamientos
- training_read    : Ver entrenamientos
- training_update  : Modificar entrenamientos
- training_delete  : Eliminar entrenamientos
- training_start   : Iniciar entrenamiento
- training_stop    : Detener entrenamiento

PARÁMETROS:
- parameters_create: Crear parámetros
- parameters_read  : Ver parámetros
- parameters_update: Modificar parámetros
- parameters_delete: Eliminar parámetros

NOTIFICACIONES:
- notifications_create: Crear notificaciones
- notifications_read  : Ver notificaciones
- notifications_update: Modificar notificaciones
- notifications_delete: Eliminar notificaciones

USUARIOS:
- user_create      : Crear usuarios
- user_read        : Ver usuarios
- user_update      : Modificar usuarios
- user_delete      : Eliminar usuarios
- user_enable      : Activar usuarios
- user_disable     : Desactivar usuarios
"""

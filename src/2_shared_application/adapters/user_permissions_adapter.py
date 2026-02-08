"""
Adaptador para obtener permisos de usuarios desde MariaDB.

Este adaptador accede a las tablas:
- users: para obtener identity_type_id del usuario
- low_level_permissions: para obtener los permisos del rol

Uso:
    from adapters.user_permissions_adapter import get_user_permissions

    permissions = get_user_permissions(user_id=5)
    if permissions.get("folder_create"):
        # Usuario puede crear carpetas
"""

from sqlalchemy import create_engine, text
from typing import Any


def get_user_permissions(
    user_id: int,
    engine=None,
) -> dict[str, bool]:
    """
    Obtiene los permisos de bajo nivel para un usuario específico.

    Realiza un JOIN entre users y low_level_permissions para obtener
    todos los permisos del usuario basándose en su identity_type_id.

    Args:
        user_id: ID del usuario
        engine: SQLAlchemy engine (opcional, se crea uno si no se provee)

    Returns:
        Diccionario con los permisos del usuario:
        {
            "folder_create": True,
            "folder_delete": False,
            "file_create": True,
            ...
        }

        Si el usuario no existe o no tiene permisos, retorna diccionario vacío.

    Example:
        >>> permissions = get_user_permissions(user_id=5)
        >>> if permissions.get("folder_create"):
        ...     print("Puede crear carpetas")
    """
    if engine is None:
        from src.apps.backend.config.mariadb_settings import load_mariadb_settings
        settings = load_mariadb_settings()

        # Construir DSN
        host = settings.get("host", "localhost")
        port = settings.get("port", 3306)
        user = settings.get("reader_user", "")
        password = settings.get("reader_password", "")
        database = settings.get("core_database", "myllm_core_db")

        dsn = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(dsn)

    query = text("""
        SELECT
            llp.folder_create,
            llp.folder_delete,
            llp.folder_rename,
            llp.folder_read,
            llp.folder_list,
            llp.file_create,
            llp.file_read,
            llp.file_update,
            llp.file_delete,
            llp.file_list,
            llp.project_create,
            llp.project_read,
            llp.project_update,
            llp.project_delete,
            llp.project_list,
            llp.version_create,
            llp.version_read,
            llp.version_update,
            llp.version_delete,
            llp.version_list,
            llp.training_create,
            llp.training_read,
            llp.training_update,
            llp.training_delete,
            llp.training_start,
            llp.training_stop,
            llp.parameters_create,
            llp.parameters_read,
            llp.parameters_update,
            llp.parameters_delete,
            llp.notifications_create,
            llp.notifications_read,
            llp.notifications_update,
            llp.notifications_delete,
            llp.user_create,
            llp.user_read,
            llp.user_update,
            llp.user_delete,
            llp.user_enable,
            llp.user_disable
        FROM users u
        INNER JOIN low_level_permissions llp
            ON u.identity_type_id = llp.id_permissions
        WHERE u.user_id = :user_id
        LIMIT 1
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id})
            row = result.fetchone()

            if not row:
                # Usuario no encontrado o sin permisos
                return {}

            # Convertir row a diccionario con valores booleanos
            permissions = {
                # Carpetas
                "folder_create": bool(row.folder_create),
                "folder_delete": bool(row.folder_delete),
                "folder_rename": bool(row.folder_rename),
                "folder_read": bool(row.folder_read),
                "folder_list": bool(row.folder_list),
                # Archivos
                "file_create": bool(row.file_create),
                "file_read": bool(row.file_read),
                "file_update": bool(row.file_update),
                "file_delete": bool(row.file_delete),
                "file_list": bool(row.file_list),
                # Proyectos
                "project_create": bool(row.project_create),
                "project_read": bool(row.project_read),
                "project_update": bool(row.project_update),
                "project_delete": bool(row.project_delete),
                "project_list": bool(row.project_list),
                # Versiones
                "version_create": bool(row.version_create),
                "version_read": bool(row.version_read),
                "version_update": bool(row.version_update),
                "version_delete": bool(row.version_delete),
                "version_list": bool(row.version_list),
                # Entrenamiento
                "training_create": bool(row.training_create),
                "training_read": bool(row.training_read),
                "training_update": bool(row.training_update),
                "training_delete": bool(row.training_delete),
                "training_start": bool(row.training_start),
                "training_stop": bool(row.training_stop),
                # Parámetros
                "parameters_create": bool(row.parameters_create),
                "parameters_read": bool(row.parameters_read),
                "parameters_update": bool(row.parameters_update),
                "parameters_delete": bool(row.parameters_delete),
                # Notificaciones
                "notifications_create": bool(row.notifications_create),
                "notifications_read": bool(row.notifications_read),
                "notifications_update": bool(row.notifications_update),
                "notifications_delete": bool(row.notifications_delete),
                # Usuarios
                "user_create": bool(row.user_create),
                "user_read": bool(row.user_read),
                "user_update": bool(row.user_update),
                "user_delete": bool(row.user_delete),
                "user_enable": bool(row.user_enable),
                "user_disable": bool(row.user_disable),
            }

            return permissions

    except Exception as e:
        print(f"Error al obtener permisos del usuario {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return {}


def get_user_identity_type_id(user_id: int, engine=None) -> int | None:
    """
    Obtiene el identity_type_id de un usuario.

    Args:
        user_id: ID del usuario
        engine: SQLAlchemy engine (opcional)

    Returns:
        identity_type_id del usuario o None si no se encuentra
    """
    if engine is None:
        from src.apps.backend.config.mariadb_settings import load_mariadb_settings
        settings = load_mariadb_settings()

        host = settings.get("host", "localhost")
        port = settings.get("port", 3306)
        user = settings.get("reader_user", "")
        password = settings.get("reader_password", "")
        database = settings.get("core_database", "myllm_core_db")

        dsn = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(dsn)

    query = text("""
        SELECT identity_type_id
        FROM users
        WHERE user_id = :user_id
        LIMIT 1
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id})
            row = result.fetchone()

            if row:
                return int(row.identity_type_id)
            return None

    except Exception as e:
        print(f"Error al obtener identity_type_id del usuario {user_id}: {e}")
        return None


def check_user_permission(
    user_id: int,
    permission_key: str,
    engine=None,
) -> bool:
    """
    Verifica si un usuario tiene un permiso específico.

    Args:
        user_id: ID del usuario
        permission_key: Clave del permiso (ej: "folder_create")
        engine: SQLAlchemy engine (opcional)

    Returns:
        True si tiene el permiso, False en caso contrario

    Example:
        >>> if check_user_permission(user_id=5, permission_key="folder_create"):
        ...     # Usuario puede crear carpetas
    """
    permissions = get_user_permissions(user_id=user_id, engine=engine)
    return permissions.get(permission_key, False)

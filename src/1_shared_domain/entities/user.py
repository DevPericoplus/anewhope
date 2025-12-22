"""Funciones para gestión de usuarios en el sistema."""
import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _get_users_file_path() -> Path:
    """
    Obtiene la ruta del archivo JSON de usuarios (datos mock).

    Returns:
        Ruta al archivo users.json.
    """
    return (
        Path(__file__).parent.parent.parent
        / "2_shared_application"
        / "moks"
        / "users.json"
    )


def _load_users() -> list[dict[str, Any]]:
    """
    Carga los usuarios desde el archivo JSON.

    Returns:
        Lista de usuarios como diccionarios.
    """
    data_file = _get_users_file_path()
    if not data_file.exists():
        logger.warning(f"El archivo de usuarios no existe: {data_file}")
        return []

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error al cargar usuarios desde {data_file}: {e}")
        return []


def get_user_by_email_exist(user_email: str) -> bool:
    """
    Verifica si existe un usuario con el email dado.

    La comparación ignora mayúsculas/minúsculas.

    Args:
        user_email: Email del usuario a verificar.

    Returns:
        True si el usuario existe, False en caso contrario.
    """
    users = _load_users()
    if not users:
        return False

    normalized_input = user_email.strip().lower()
    for user in users:
        user_email_value = user.get("user_email", "")
        if user_email_value.strip().lower() == normalized_input:
            return True
    return False


def get_user_by_mobile_exist(user_mobile: str) -> bool:
    """
    Verifica si existe un usuario con el teléfono dado.

    La comparación normaliza espacios y caracteres especiales.

    Args:
        user_mobile: Teléfono del usuario a verificar.

    Returns:
        True si el usuario existe, False en caso contrario.
    """
    users = _load_users()
    if not users:
        return False

    # Normalizar el teléfono: eliminar espacios, guiones y paréntesis
    normalized_input = "".join(c for c in user_mobile.strip() if c.isdigit() or c == "+")
    for user in users:
        user_mobile_value = user.get("user_mobile", "")
        normalized_mobile = "".join(c for c in user_mobile_value.strip() if c.isdigit() or c == "+")
        if normalized_mobile == normalized_input:
            return True
    return False


def get_user_by_name_exist(user_name: str) -> bool:
    """
    Verifica si existe un usuario con el nombre de usuario dado.

    La comparación ignora mayúsculas/minúsculas.

    Args:
        user_name: Nombre de usuario a verificar.

    Returns:
        True si el usuario existe, False en caso contrario.
    """
    users = _load_users()
    if not users:
        return False

    normalized_input = user_name.strip().lower()
    for user in users:
        user_name_value = user.get("user_name", "")
        if user_name_value.strip().lower() == normalized_input:
            return True
    return False


def get_user_by_email(user_email: str) -> Optional[dict[str, Any]]:
    """
    Obtiene un usuario por su email.

    La comparación ignora mayúsculas/minúsculas.

    Args:
        user_email: Email del usuario a buscar.

    Returns:
        Diccionario con los datos del usuario si existe, None en caso contrario.
    """
    users = _load_users()
    if not users:
        return None

    normalized_input = user_email.strip().lower()
    for user in users:
        user_email_value = user.get("user_email", "")
        if user_email_value.strip().lower() == normalized_input:
            return user
    return None


def update_user_password_and_otp(user_email: str, new_password: str, new_otp: str) -> bool:
    """
    Actualiza la contraseña y el OTP de un usuario existente.

    Args:
        user_email: Email del usuario a actualizar.
        new_password: Nueva contraseña (ya cifrada).
        new_otp: Nuevo código OTP.

    Returns:
        True si la actualización fue exitosa, False en caso contrario.
    """
    data_file = _get_users_file_path()
    users = _load_users()
    if not users:
        logger.warning("No hay usuarios en el archivo")
        return False

    normalized_input = user_email.strip().lower()
    user_found = False
    
    for user in users:
        user_email_value = user.get("user_email", "")
        if user_email_value.strip().lower() == normalized_input:
            user["user_password"] = new_password
            user["user_otp"] = new_otp
            user_found = True
            logger.info(f"Usuario {user_email} actualizado: contraseña y OTP modificados")
            break
    
    if not user_found:
        logger.warning(f"Usuario con email {user_email} no encontrado")
        return False
    
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        return True
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Error al guardar usuario actualizado en {data_file}: {e}")
        return False


def create_user(user_data: dict[str, Any]) -> bool:
    """
    Crea una nueva entrada de usuario en el archivo users.json.

    Asigna un user_id único y secuencial.

    Args:
        user_data: Diccionario con los datos del usuario a agregar.

    Returns:
        True si la creación fue exitosa, False en caso contrario.
    """
    data_file = _get_users_file_path()
    users = _load_users()

    # Determinar el siguiente user_id
    if users:
        existing_ids = [
            user.get("user_id", 0)
            for user in users
            if isinstance(user.get("user_id"), int)
        ]
        next_id = max(existing_ids, default=0) + 1
    else:
        next_id = 1

    # Construir diccionario de nuevo usuario
    user_dict = {
        "user_id": next_id,
        "organization_id": user_data.get("organization_id", 1),
        "identity_type_id": user_data.get("identity_type_id", 1),
        "user_name": user_data.get("user_name", "").strip(),
        "user_password": user_data.get("user_password", ""),
        "user_email": user_data.get("user_email", "").strip().lower(),
        "user_mobile": user_data.get("user_mobile", "").strip(),
        "user_otp": user_data.get("user_otp", ""),
        "active": user_data.get("active", True),
        "blocked": user_data.get("blocked", False),
        "contact_info": user_data.get("contact_info", {}),
        "billing_info": user_data.get("billing_info", {}),
    }

    users.append(user_dict)
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        logger.info(f"Usuario creado exitosamente con ID: {next_id}")
        return True
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Error al guardar usuario en {data_file}: {e}")
        return False


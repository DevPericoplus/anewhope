"""Funciones para gestión de usuarios en el sistema."""
import importlib.util
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _load_env_settings_module(module_name: str) -> Any:
    """Carga el módulo de configuración compartida."""

    module_path = (
        Path(__file__).resolve().parents[3]
        / "src/2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el módulo de configuración")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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
    
    IMPORTANTE: Ahora incluye retry automático para sincronización con broker.

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
    user_id = None
    
    for user in users:
        user_email_value = user.get("user_email", "")
        if user_email_value.strip().lower() == normalized_input:
            user["user_password"] = new_password
            user["user_otp"] = new_otp
            user_id = user.get("user_id")
            user_found = True
            logger.info(
                f"Usuario {user_email} (ID: {user_id}) actualizado: "
                f"contraseña y OTP modificados"
            )
            break
    
    if not user_found:
        logger.warning(f"Usuario con email {user_email} no encontrado")
        return False
    
    # SINCRONIZAR CON BROKER CON RETRY
    if _should_sync_users_with_broker():
        max_retries = 3
        sync_success = False
        
        for attempt in range(max_retries):
            if _sync_users_to_broker(users):
                logger.debug(
                    f"Usuario {user_id} sincronizado con broker "
                    f"(intento {attempt + 1}/{max_retries})"
                )
                sync_success = True
                break
            else:
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt
                    logger.warning(
                        f"Fallo al sincronizar usuario {user_id} con broker "
                        f"(intento {attempt + 1}/{max_retries}). "
                        f"Reintentando en {sleep_time}s..."
                    )
                    time.sleep(sleep_time)
        
        if not sync_success:
            logger.error(
                f"No se pudo sincronizar usuario {user_id} con broker backend "
                f"tras {max_retries} intentos. OTP NO será actualizado para "
                f"mantener consistencia."
            )
            return False  # NO guardar en JSON si todos los intentos fallaron

    # GUARDAR EN JSON
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        logger.info(f"Usuario {user_id} guardado en JSON con nuevo OTP")
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Error al guardar usuario actualizado en {data_file}: {e}")
        
        # Si ya sincronizamos con broker pero falló JSON, inconsistencia crítica
        if _should_sync_users_with_broker():
            logger.critical(
                f"INCONSISTENCIA CRÍTICA: Usuario {user_id} actualizado en broker "
                f"pero falló guardado en JSON. OTP desincronizado. "
                f"Requiere corrección manual o sincronización periódica."
            )
        
        return False

    # VALIDAR SINCRONIZACIÓN
    validate_users_otp_sync()
    return True


def validate_users_otp_sync() -> bool:
    """
    Verifica que los OTPs de users.json coinciden con la tabla users en MariaDB.

    Returns:
        True si no hay discrepancias, False si se detectan.
    """
    if not _should_sync_users_with_broker():
        return True
    users = _load_users()
    if not users:
        return True
    broker_users = _fetch_users_from_broker()
    if not broker_users:
        logger.warning("No se pudo validar OTPs con broker backend")
        _append_frontend_secure_log(
            "Validacion OTP sincronizacion,ERROR,No se pudo consultar broker"
        )
        return False

    broker_map = {
        int(user.get("user_id", 0)): str(user.get("user_otp", ""))
        for user in broker_users
        if int(user.get("user_id", 0)) > 0
    }
    mismatches = []
    for user in users:
        user_id = int(user.get("user_id", 0))
        if user_id <= 0:
            continue
        json_otp = str(user.get("user_otp", ""))
        db_otp = broker_map.get(user_id)
        if db_otp is None:
            continue
        if json_otp != db_otp:
            mismatches.append((user_id, json_otp, db_otp))
    for user_id, json_otp, db_otp in mismatches:
        logger.warning(
            "OTP desalineado user_id=%s json=%s db=%s", user_id, json_otp, db_otp
        )
    if mismatches:
        mismatch_ids = "|".join(str(item[0]) for item in mismatches)
        _append_frontend_secure_log(
            f"Validacion OTP sincronizacion,DESALINEADO,{mismatch_ids}"
        )
    else:
        _append_frontend_secure_log("Validacion OTP sincronizacion,OK")
    return not mismatches


def _should_sync_users_with_broker() -> bool:
    """Determina si se debe sincronizar usuarios con el broker backend."""

    storage_mode = os.environ.get("STORAGE_MODE")
    if storage_mode is None:
        storage_mode = _load_protected_storage_mode()
    return storage_mode in {"mock_and_db", "db_only"}


def _load_protected_storage_mode() -> str:
    """Carga el storage_mode desde protected_values.py."""

    env_settings = _load_env_settings_module("shared_env_settings")
    return env_settings.get_env_value("STORAGE_MODE", "mock")


def _get_broker_base_url() -> str:
    """Obtiene la URL base del broker backend."""

    env_settings = _load_env_settings_module("shared_env_settings")
    protected_base_url = env_settings.get_protected_value(
        "broker_backend_base_url", "http://localhost:8008"
    )
    return os.environ.get("BROKER_BACKEND_BASE_URL", protected_base_url).rstrip("/")


def _request_broker(
    method: str, path: str, payload: Any | None = None
) -> list[dict[str, Any]]:
    """Ejecuta una petición al broker backend."""

    url = f"{_get_broker_base_url()}{path}"
    body = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return list(data or [])
    except urllib.error.URLError as exc:
        logger.error(f"Error al conectar con broker backend: {exc}")
        return []
    except json.JSONDecodeError:
        logger.error("Respuesta del broker backend no es JSON válido")
        return []


def _fetch_users_from_broker() -> list[dict[str, Any]]:
    """Obtiene usuarios desde broker backend."""

    return _request_broker("GET", "/users")


def _sync_users_to_broker(users: list[dict[str, Any]]) -> bool:
    """
    Sincroniza usuarios hacia broker backend con validación estricta.
    
    Returns:
        True si la sincronización fue exitosa, False en caso contrario.
    """
    try:
        response = _request_broker("PUT", "/users", payload=users)
        
        # Validación estricta de la respuesta
        if response is None:
            logger.error("Broker retornó None (posible timeout o error de servidor)")
            return False
        
        # Si el broker retorna dict con "success", verificarlo
        if isinstance(response, dict):
            success = response.get("success", False)
            if success:
                logger.debug("Broker confirmó sincronización exitosa")
                return True
            else:
                error_detail = response.get("detail", "Unknown error")
                logger.error(f"Broker indicó fallo en sincronización: {error_detail}")
                return False
        
        # Si retorna lista, considerar éxito (retro-compatibilidad)
        if isinstance(response, list):
            logger.debug("Broker retornó lista (sincronización asumida como exitosa)")
            return True
        
        # Cualquier otro tipo de respuesta es inválida
        logger.error(f"Broker retornó tipo inválido: {type(response)}")
        return False
        
    except Exception as exc:
        logger.error(f"Excepción al sincronizar con broker: {exc}", exc_info=True)
        return False


def _append_frontend_secure_log(message: str) -> None:
    """Añade una entrada al log de seguridad del frontend."""

    root_path = Path(__file__).resolve().parents[3]
    log_path = root_path / "src/apps/5_web_frontend/logs/frontend_secure.log"
    timestamp = datetime.now().strftime("%Y-%m-%d-%H:%M")
    log_line = f"{timestamp},,,{message}\n"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as file_handler:
            file_handler.write(log_line)
    except OSError as exc:
        logger.error("No se pudo escribir log frontend_secure: %s", exc)


def create_user(user_data: dict[str, Any]) -> bool:
    """
    Crea una nueva entrada de usuario en el archivo users.json.
    
    IMPORTANTE: Ahora sincroniza inmediatamente con broker/MariaDB si es necesario.

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
    
    # SINCRONIZAR CON BROKER PRIMERO (si es necesario)
    if _should_sync_users_with_broker():
        logger.info(f"Sincronizando nuevo usuario (ID: {next_id}) con broker...")
        if not _sync_users_to_broker(users):
            logger.error(
                f"No se pudo sincronizar nuevo usuario con broker. "
                f"Usuario NO será creado para mantener consistencia."
            )
            return False  # NO guardar en JSON si broker falló
        logger.debug(f"Usuario {next_id} sincronizado exitosamente con broker")
    
    # GUARDAR EN JSON DESPUÉS (solo si broker tuvo éxito o no es necesario)
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        logger.info(f"Usuario creado exitosamente con ID: {next_id}")
        
        # Validar sincronización
        validate_users_otp_sync()
        
        return True
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Error al guardar usuario en {data_file}: {e}")
        
        # Si ya sincronizamos con broker pero falló el JSON, tenemos un problema
        if _should_sync_users_with_broker():
            logger.critical(
                f"INCONSISTENCIA CRÍTICA: Usuario {next_id} guardado en broker "
                f"pero falló guardado en JSON. Requiere corrección manual."
            )
        
        return False


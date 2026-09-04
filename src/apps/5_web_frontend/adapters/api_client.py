"""Adaptador para comunicación con la capa de dominio y middleware."""
import importlib.util
import json
import jwt
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_env_settings_module():
    """Carga el módulo de configuración compartida."""

    module_path = (
        Path(__file__).resolve().parents[4]
        / "src/2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location("env_settings_frontend", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el módulo de configuración")
    module = importlib.util.module_from_spec(spec)
    sys.modules["env_settings_frontend"] = module
    spec.loader.exec_module(module)
    return module


_env_settings = _load_env_settings_module()


def _load_storage_structure_module():
    """Carga helpers de carpetas de storage (ORG##### / USER#####)."""

    module_path = (
        Path(__file__).resolve().parents[3]
        / "2_shared_application"
        / "storage_access_structure.py"
    )
    spec = importlib.util.spec_from_file_location(
        "storage_access_structure_frontend_api", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar storage_access_structure")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_storage_structure = _load_storage_structure_module()


def _account_storage_folder(org_id: int, user_id: int = 0) -> str:
    """Raíz de cuenta: ORG##### o USER#####."""

    return _storage_structure.get_account_storage_folder(org_id, user_id)


def _project_storage_folder(project_id: int) -> str:
    """Carpeta de proyecto PRJ#####."""

    return _storage_structure.get_folder_by_id_project(project_id)


def _version_storage_folder(version_id: int) -> str:
    """Carpeta de versión v###."""

    return _storage_structure.get_folder_by_id_version(version_id)

# Ruta al módulo de dominio de usuarios y organizaciones
_domain_entities_path = (
    Path(__file__).parent.parent.parent.parent / "1_shared_domain" / "entities"
)
_user_module_path = _domain_entities_path / "user.py"

# Cargar el módulo de dominio de usuarios
_create_user_function = None
_get_user_by_name_exist_function = None
if _user_module_path.exists():
    try:
        spec = importlib.util.spec_from_file_location("user", _user_module_path)
        if spec and spec.loader:
            user_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(user_module)
            _create_user_function = user_module.create_user
            _get_user_by_name_exist_function = getattr(user_module, "get_user_by_name_exist", None)
    except Exception as e:
        logger.error(f"Error al cargar el módulo de usuarios: {e}")

def check_user_name_exists(user_name: str) -> bool:
    """
    Verifica si existe un usuario con el nombre de usuario dado.
    
    Flujo: Frontend (aquí) → Middleware → Broker → Backend Core → JSON/MariaDB
    
    Args:
        user_name: Nombre de usuario a verificar.
    
    Returns:
        True si el usuario existe, False en caso contrario.
    """
    try:
        response = _request_middleware("POST", "/users/check-exists", payload={"user_name": user_name})
        return response.get("exists", False)
    except Exception as e:
        logger.error(f"Error al verificar nombre de usuario: {e}")
        return False


def get_user_by_email(email: str) -> dict[str, Any] | None:
    """
    Obtiene datos de un usuario por email.
    
    Flujo: Frontend (aquí) → Middleware → Broker → Backend Core → JSON/MariaDB
    
    Args:
        email: Email del usuario a buscar.
    
    Returns:
        Diccionario con datos del usuario o None si no existe.
    """
    try:
        response = _request_middleware("POST", "/users/by-email", payload={"email": email})
        if response.get("found", False):
            return {
                "user_id": response.get("user_id"),
                "user_name": response.get("user_name"),
                "user_email": response.get("user_email"),
                "user_mobile": response.get("user_mobile"),
                "organization_id": response.get("organization_id"),
            }
        return None
    except Exception as e:
        logger.error(f"Error al obtener usuario por email: {e}")
        return None


def update_user_password_and_otp(email: str, new_password: str, new_otp: str) -> bool:
    """
    Actualiza contraseña y OTP de un usuario.
    
    Flujo: Frontend (aquí) → Middleware → Broker → Backend Core → JSON/MariaDB
    
    Args:
        email: Email del usuario.
        new_password: Nueva contraseña (ya cifrada).
        new_otp: Nuevo código OTP.
    
    Returns:
        True si se actualizó correctamente, False en caso contrario.
    """
    try:
        response = _request_middleware(
            "POST",
            "/users/update-password",
            payload={
                "email": email,
                "new_password": new_password,
                "new_otp": new_otp,
            },
        )
        return response.get("success", False)
    except Exception as e:
        logger.error(f"Error al actualizar contraseña: {e}")
        return False


def save_user_to_json(user_extended: Any, account_kind: str | None = None) -> bool:
    """
    Guarda un usuario UserExtended a través del middleware.

    Args:
        user_extended: Objeto UserExtended a guardar.
        account_kind: Alta pública: individual u organization.
    
    Returns:
        True si el usuario se guardó exitosamente, False en caso contrario.
    """
    try:
        # Convertir UserExtended a diccionario
        user_dict = _user_extended_to_dict(user_extended)
        if account_kind:
            user_dict["account_kind"] = account_kind
        response = _request_middleware("POST", "/users", payload=user_dict)
        return isinstance(response.get("user_id"), int)
    except Exception as e:
        logger.error(f"Error al guardar usuario a través del adaptador: {e}")
        return False


def _user_extended_to_dict(user_extended: Any) -> dict[str, Any]:
    """
    Convierte un objeto UserExtended a un diccionario.
    
    Args:
        user_extended: Objeto UserExtended a convertir.
    
    Returns:
        Diccionario con los datos del usuario.
    """
    # Extraer información de contacto
    contact_info = user_extended.contact_info
    billing_info = user_extended.billing_info
    
    return {
        "user_id": user_extended.id,
        "organization_id": user_extended.id_org,
        "identity_type_id": user_extended.id_type,
        "user_name": user_extended.user_name,
        "user_password": user_extended.user_password,
        "user_email": user_extended.user_email,
        "user_mobile": user_extended.user_mobile,
        "user_otp": user_extended.user_otp,
        "active": user_extended.active,
        "blocked": user_extended.blocked,
        "contact_info": {
            "first_name": contact_info.first_name,
            "sur_name": contact_info.sur_name,
            "country": contact_info.country,
            "state": contact_info.state,
            "zip_code": contact_info.zip_code,
            "address": contact_info.address,
        },
        "billing_info": {
            "first_name": billing_info.first_name,
            "sur_name": billing_info.sur_name,
            "country": billing_info.country,
            "state": billing_info.state,
            "zip_code": billing_info.zip_code,
            "address": billing_info.address,
        },
    }




def check_organization_name_exists(organization_name: str) -> bool:
    """
    Verifica si existe una organización con el nombre dado.

    Args:
        organization_name: Nombre de la organización a verificar.
    
    Returns:
        True si la organización existe, False en caso contrario.
    """
    response = _request_middleware(
        "POST",
        "/organizations/check-name",
        payload={"organization_name": organization_name},
    )
    return bool(response.get("exists", False))


def save_organization_to_json(organization_data: dict[str, Any]) -> int | None:
    """
    Guarda una organización mediante el middleware.

    Args:
        organization_data: Diccionario con los datos de la organización.
            Debe contener las siguientes claves:
            - organization_name (str): Nombre de la organización
            - organization_email (str): Email de la organización
            - organization_tlf (str, opcional): Teléfono de la organización
            - organization_address (str, opcional): Dirección de la organización
            - organization_country (str, opcional): País de la organización
            - organization_state (str, opcional): Estado/Provincia de la organización
    
    Returns:
        organization_id (int) si la organización se guardó exitosamente, None en caso contrario.
    """
    response = _request_middleware("POST", "/organizations", payload=organization_data)
    organization_id = response.get("organization_id")
    if isinstance(organization_id, int):
        return organization_id
    logger.error("No se pudo crear la organización en el middleware")
    return None


def create_organization(organization_data: dict[str, Any]) -> dict[str, Any] | None:
    """Crea una organización y devuelve id + acrónimo de login."""
    response = _request_middleware("POST", "/organizations", payload=organization_data)
    organization_id = response.get("organization_id")
    if isinstance(organization_id, int):
        return {
            "organization_id": organization_id,
            "organization_acronym": str(response.get("organization_acronym") or ""),
        }
    logger.error("No se pudo crear la organización en el middleware")
    return None


def get_my_profile(access_token: str, session_token: str) -> dict[str, Any]:
    """Obtiene la ficha del usuario autenticado."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Session-Token": session_token,
    }
    return _request_middleware("GET", "/users/me", headers=headers)


def update_my_profile(
    access_token: str,
    session_token: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Actualiza email, móvil y contacto del usuario autenticado."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Session-Token": session_token,
    }
    return _request_middleware("PATCH", "/users/me", payload=payload, headers=headers)


def update_my_organization(
    access_token: str,
    session_token: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Actualiza datos de organización (solo administrador identity 2)."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Session-Token": session_token,
    }
    return _request_middleware(
        "PATCH", "/organizations/me", payload=payload, headers=headers
    )


def _get_middleware_base_url() -> str:
    """Obtiene la URL base del middleware desde el entorno.
    
    Prioridad:
    1. Variable de entorno MIDDLEWARE_BASE_URL
    2. Valor de env.yaml (middleware_base_url)
    3. Fallback a localhost:8007
    """

    return _env_settings.get_env_value("MIDDLEWARE_BASE_URL", "http://localhost:8007").rstrip("/")


# Variable global para almacenar tokens temporalmente durante el refresh
_temp_tokens: dict[str, str] = {}


def get_refreshed_tokens() -> dict[str, str]:
    """Retorna los tokens refrescados si existen, sino retorna un dict vacío.

    El componente de Reflex debe llamar esta función después de cada operación
    para verificar si hay tokens actualizados que deben guardarse en el estado.

    Returns:
        Dict con 'access_token' y 'session_token' si hay tokens refrescados,
        dict vacío si no hay tokens refrescados.
    """
    if _temp_tokens:
        logger.info("[AUTO-REFRESH] Retornando tokens refrescados al componente")
        return _temp_tokens.copy()
    return {}


def clear_refreshed_tokens():
    """Limpia los tokens refrescados después de que el componente los haya guardado.

    El componente debe llamar esta función después de actualizar su estado con
    los tokens refrescados.
    """
    global _temp_tokens
    if _temp_tokens:
        logger.info("[AUTO-REFRESH] Limpiando tokens refrescados")
        _temp_tokens.clear()


def _refresh_access_token_internal(session_token: str) -> dict[str, Any] | None:
    """Intenta refrescar el access token usando el session token.

    Returns:
        Dict con nuevos tokens si el refresh fue exitoso, None si falló
    """
    try:
        url = f"{_get_middleware_base_url()}/refresh-token"
        request_headers = {
            "Content-Type": "application/json",
            "X-Session-Token": session_token,
            "X-Client-App": "frontend",
        }

        request = urllib.request.Request(url, method="POST", headers=request_headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            logger.info("[AUTO-REFRESH] Tokens renovados automáticamente")
            return result
    except Exception as exc:
        logger.warning(f"[AUTO-REFRESH] Falló el refresh automático: {exc}")
        return None


def _request_middleware(
    method: str, path: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None, _retry_count: int = 0
) -> dict[str, Any]:
    """Realiza una petición HTTP al middleware y retorna JSON.

    Incluye lógica de refresh automático de tokens cuando expiran.
    """

    url = f"{_get_middleware_base_url()}{path}"
    body = None
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "frontend",
    }
    if headers:
        request_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Si es 401 (Unauthorized) y no es el endpoint de refresh, intentar renovar tokens
        if exc.code == 401 and path != "/refresh-token" and _retry_count == 0:
            # Extraer session_token de los headers
            session_token = request_headers.get("X-Session-Token")

            if session_token:
                logger.info(f"[AUTO-REFRESH] Token expirado detectado, intentando renovar...")
                new_tokens = _refresh_access_token_internal(session_token)

                if new_tokens and not new_tokens.get("error"):
                    # Actualizar tokens temporalmente para esta petición
                    _temp_tokens["access_token"] = new_tokens.get("access_token", "")
                    _temp_tokens["session_token"] = new_tokens.get("session_token", "")

                    # Actualizar headers con nuevos tokens
                    if "Authorization" in request_headers:
                        request_headers["Authorization"] = f"Bearer {_temp_tokens['access_token']}"
                    if "X-Session-Token" in request_headers:
                        request_headers["X-Session-Token"] = _temp_tokens["session_token"]

                    # Reintentar la petición original con nuevos tokens
                    logger.info("[AUTO-REFRESH] Reintentando petición con nuevos tokens")
                    return _request_middleware(method, path, payload, request_headers, _retry_count=1)
                else:
                    logger.warning("[AUTO-REFRESH] No se pudo renovar tokens, sesión expirada")
                    return {
                        "error": True,
                        "detail": "Tu sesión ha expirado. Por favor, vuelve a iniciar sesión.",
                        "status_code": 401,
                        "session_expired": True
                    }

        # Si no es 401 o el retry ya se intentó, manejar el error normalmente
        try:
            error_payload = exc.read().decode("utf-8")
            logger.error(f"Error HTTP desde middleware: {exc.code} - {error_payload}")
            # Intentar parsear el error como JSON para extraer el mensaje
            try:
                error_data = json.loads(error_payload)
                error_message = error_data.get("detail", "Error desconocido")
            except json.JSONDecodeError:
                error_message = error_payload

            # Mejorar mensaje para 401
            if exc.code == 401:
                error_message = "Tu sesión ha expirado. Por favor, vuelve a iniciar sesión."

            return {"error": True, "detail": error_message, "status_code": exc.code}
        except Exception:
            logger.error(f"Error HTTP desde middleware: {exc.code}")
            return {"error": True, "detail": "Error en la comunicación con el middleware", "status_code": exc.code}
    except urllib.error.URLError as exc:
        logger.error(f"No se pudo contactar con el middleware: {exc}")
        return {"error": True, "detail": "No se pudo contactar con el middleware"}
    except json.JSONDecodeError:
        logger.error("Respuesta del middleware no es JSON válido")
        return {"error": True, "detail": "Respuesta inválida del servidor"}


def _request_middleware_raw(
    method: str, path: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None
) -> tuple[bytes, str]:
    """Realiza una petición HTTP al middleware y retorna los bytes y el content-type."""

    url = f"{_get_middleware_base_url()}{path}"
    body = None
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "frontend",
    }
    if headers:
        request_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type", "")
            return response.read(), content_type
    except urllib.error.HTTPError as exc:
        logger.error(f"Error HTTP desde middleware (RAW): {exc.code}")
        raise
    except urllib.error.URLError as exc:
        logger.error(f"No se pudo contactar con el middleware (RAW): {exc}")
        raise


def login_user(user_name: str, password: str, otp: str) -> dict[str, Any]:
    """Solicita autenticación al middleware."""

    payload = {"user_name": user_name, "password": password, "otp": otp}
    return _request_middleware("POST", "/login", payload=payload)


def request_login_otp(user_name: str, password: str) -> dict[str, Any]:
    """Solicita los datos de OTP al middleware para enviar SMS.
    
    El middleware devuelve el OTP y teléfono del usuario.
    El frontend es responsable de enviar el SMS directamente a Infobip.
    
    Returns:
        {"success": bool, "otp": str, "phone_number": str} si éxito
        {"success": false, "detail": str} si error
    """
    payload = {"user_name": user_name, "password": password}
    return _request_middleware("POST", "/login/request-otp", payload=payload)


def refresh_tokens(session_token: str) -> dict[str, Any]:
    """Solicita renovación de tokens al middleware."""

    return _request_middleware(
        "POST", "/refresh-token", headers={"X-Session-Token": session_token}
    )


# ============================================================================
# RENOVACIÓN AUTOMÁTICA DE TOKENS
# ============================================================================

import time

# Umbral de renovación: 2 minutos antes de expirar
RENEWAL_THRESHOLD_SECONDS = 120


def _should_renew_token(expires_at: int) -> bool:
    """Verifica si el token está próximo a expirar.
    
    Args:
        expires_at: Unix timestamp de expiración del token
        
    Returns:
        True si el token expira en menos de RENEWAL_THRESHOLD_SECONDS
    """
    if expires_at <= 0:
        return False
    return time.time() > (expires_at - RENEWAL_THRESHOLD_SECONDS)


def ensure_valid_tokens(
    access_token: str,
    session_token: str,
    access_expires_at: int,
    session_expires_at: int,
) -> dict[str, Any]:
    """Garantiza tokens válidos, renovando si es necesario.
    
    Esta función debe llamarse antes de cada request al middleware.
    Si el access_token está próximo a expirar y el session_token es válido,
    renueva ambos tokens automáticamente.
    
    Args:
        access_token: Token de acceso actual
        session_token: Token de sesión actual
        access_expires_at: Unix timestamp de expiración del access_token
        session_expires_at: Unix timestamp de expiración del session_token
        
    Returns:
        Dict con:
        - renewed: bool indicando si se renovaron los tokens
        - access_token: Token de acceso (renovado o el mismo)
        - session_token: Token de sesión (renovado o el mismo)
        - access_expires_at: Timestamp de expiración (renovado o el mismo)
        - session_expires_at: Timestamp de expiración (renovado o el mismo)
        - error: Mensaje de error si falló la renovación
    """
    result = {
        "renewed": False,
        "access_token": access_token,
        "session_token": session_token,
        "access_expires_at": access_expires_at,
        "session_expires_at": session_expires_at,
        "error": "",
    }
    
    # Si el access_token no está próximo a expirar, no hacer nada
    if not _should_renew_token(access_expires_at):
        return result
    
    # Si el session_token también expiró, no podemos renovar
    if _should_renew_token(session_expires_at):
        result["error"] = "La sesión ha expirado, por favor inicie sesión nuevamente"
        return result
    
    # Intentar renovar usando el session_token
    try:
        response = refresh_tokens(session_token)

        if response.get("access_token") and response.get("session_token"):
            result["renewed"] = True
            result["access_token"] = response["access_token"]
            result["session_token"] = response["session_token"]
            result["access_expires_at"] = response.get("access_expires_at", 0)
            result["session_expires_at"] = response.get("session_expires_at", 0)
            logger.info("Tokens renovados automáticamente")
        else:
            # Si el middleware rechaza la renovación, mantener tokens actuales
            # y extender threshold para intentar de nuevo más tarde
            error_detail = response.get("detail", "respuesta incompleta")
            result["error"] = ""  # No marcar como error fatal aún
            result["retry_later"] = True  # Flag para retry
            logger.warning(f"Renovación de tokens rechazada: {error_detail}")
    except Exception as e:
        # Errores de red u otros problemas técnicos
        error_str = str(e)
        if "401" in error_str and "no está registrada" in error_str.lower():
            # Sesión expirada en el middleware - necesita re-login
            result["error"] = "Su sesión ha expirado en el servidor. Por favor, recargue la página para iniciar sesión nuevamente."
        else:
            # Otros errores - intentar de nuevo
            result["error"] = ""
            result["retry_later"] = True
        logger.error(f"Error al renovar tokens: {e}")
    
    return result


def logout_user(access_token: str, session_token: str) -> dict[str, Any]:
    """Solicita cierre de sesión al middleware."""

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Session-Token": session_token,
    }
    return _request_middleware("POST", "/logout", headers=headers)


def get_user_permissions(access_token: str, session_token: str) -> dict[str, Any]:
    """Consulta permisos del usuario en el middleware."""

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Session-Token": session_token,
    }
    response = _request_middleware("GET", "/permissions", headers=headers)
    low_level = response.get("low_level_permissions") or {}
    logger.info(
        "Consulta permisos middleware user_id=%s org_id=%s role_id=%s low_level=%s",
        response.get("user_id"),
        response.get("organization_id"),
        response.get("identity_type_id"),
        bool(low_level),
    )
    return response


def log_security_action(
    action: str, entity_id: int | None, ip: str, user_agent: str
) -> bool:
    """Registra una acción de seguridad en el middleware."""

    payload = {
        "action": action,
        "entity_id": entity_id,
        "ip": ip,
        "user_agent": user_agent,
    }
    response = _request_middleware("POST", "/security/log", payload=payload)
    return bool(response.get("success"))


def get_organization_users(
    organization_id: int,
    access_token: str | None = None,
    session_token: str | None = None,
    identity_type_id: int = 5,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Obtiene los usuarios de una organización filtrados por identity_type_id.
    
    Args:
        organization_id: ID de la organización
        access_token: Token de acceso JWT
        session_token: Token de sesión
        identity_type_id: Filtrar por tipo de identidad (default: 5 = auditores)
        active_only: Si True, solo retorna usuarios activos (default: True)
                     El backoffice usa False para ver también usuarios inactivos
    
    Returns:
        Lista de usuarios con user_id, user_name y active
    """
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token
    
    path = f"/organizations/{organization_id}/users?identity_type_id={identity_type_id}&active_only={str(active_only).lower()}"
    response = _request_middleware("GET", path, headers=headers)
    
    users = response.get("users", [])
    logger.info(f"Obtenidos {len(users)} usuarios de organización {organization_id} (active_only={active_only})")
    return users


def update_user_status(
    user_id: int,
    active: bool,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """
    Actualiza el estado activo/inactivo de un usuario.
    
    Args:
        user_id: ID del usuario a modificar
        active: True para habilitar, False para deshabilitar
        access_token: Token de acceso JWT
        session_token: Token de sesión
    
    Returns:
        Diccionario con user_id, active y message
    
    Raises:
        Exception: Si hay error en la petición
    """
    url = f"{_get_middleware_base_url()}/users/{user_id}/status"
    body = json.dumps({"active": active}).encode("utf-8")
    
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "frontend",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    logger.info(f"Enviando PATCH a {url} con body: {{'active': {active}}}")
    
    request = urllib.request.Request(url, data=body, headers=request_headers, method="PATCH")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            action = "habilitado" if active else "deshabilitado"
            logger.info(f"Usuario {user_id} {action}: {result}")
            return result
    except urllib.error.HTTPError as exc:
        error_msg = f"Error HTTP {exc.code}"
        try:
            error_payload = exc.read().decode("utf-8")
            error_msg = f"{error_msg}: {error_payload}"
        except Exception:
            pass
        logger.error(f"Error actualizando usuario: {error_msg}")
        raise Exception(error_msg) from exc
    except urllib.error.URLError as exc:
        logger.error(f"No se pudo contactar con el middleware: {exc}")
        raise Exception(f"Error de conexión: {exc}") from exc


def create_organization_user(
    organization_id: int,
    user_name: str,
    user_email: str,
    user_mobile: str,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """
    Crea un nuevo usuario dentro de una organización.
    
    El usuario se crea con:
    - identity_type_id = 5 (usuario estándar de organización)
    - password generada automáticamente (cifrada)
    - OTP generado aleatoriamente
    - active = True, blocked = False
    - contact_info y billing_info con valores por defecto
    
    Args:
        organization_id: ID de la organización a la que pertenece el usuario
        user_name: Nombre de usuario
        user_email: Correo electrónico
        user_mobile: Teléfono móvil
        access_token: Token de acceso JWT (opcional, para autenticación)
        session_token: Token de sesión (opcional, para autenticación)
    
    Returns:
        Diccionario con:
        - success (bool): True si se creó exitosamente
        - user_id (int): ID del usuario creado (si success=True)
        - error (str): Mensaje de error (si success=False)
    """
    import secrets
    
    # Generar OTP aleatorio de 4 dígitos
    new_otp = f"{secrets.randbelow(10000):04d}"
    
    # Generar contraseña temporal aleatoria
    temp_password = secrets.token_urlsafe(16)
    
    # Cifrar la contraseña usando el módulo de seguridad
    encrypted_password = _encrypt_password(temp_password)
    if not encrypted_password:
        return {"success": False, "error": "Error al generar contraseña segura"}
    
    # Preparar payload para el middleware
    payload = {
        "organization_id": organization_id,
        "identity_type_id": 5,  # Usuario estándar de organización
        "user_name": user_name,
        "user_password": encrypted_password,
        "user_email": user_email,
        "user_mobile": user_mobile,
        "user_otp": new_otp,
        "active": True,
        "blocked": False,
        "contact_info": {
            "first_name": user_name,
            "sur_name": "Usuario de la organizacion",
            "country": "",
            "state": "",
            "zip_code": "",
            "address": "",
        },
        "billing_info": {
            "first_name": user_name,
            "sur_name": "Usuario de la organizacion",
            "country": "",
            "state": "",
            "zip_code": "",
            "address": "",
        },
    }
    
    # Construir headers con autenticación
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token
    
    # Llamar al endpoint de creación de usuarios
    response = _request_middleware("POST", "/users", payload=payload, headers=headers)
    
    if response.get("user_id"):
        logger.info(f"Usuario creado exitosamente: user_id={response['user_id']}")
        return {
            "success": True,
            "user_id": response["user_id"],
            "organization_id": response.get("organization_id", organization_id),
        }
    
    error_msg = response.get("detail", "Error desconocido al crear usuario")
    logger.error(f"Error al crear usuario: {error_msg}")
    return {"success": False, "error": error_msg}


def _encrypt_password(plain_password: str) -> str | None:
    """
    Cifra una contraseña usando Fernet.
    
    Args:
        plain_password: Contraseña en texto plano
    
    Returns:
        Contraseña cifrada como string, o None si hay error
    """
    try:
        # Cargar el módulo de seguridad
        security_module_path = (
            Path(__file__).resolve().parents[3]
            / "2_shared_application/security/custom_cipher_lib.py"
        )
        
        spec = importlib.util.spec_from_file_location("custom_cipher_lib", security_module_path)
        if spec is None or spec.loader is None:
            logger.error("No se pudo cargar el módulo de cifrado")
            return None
        
        cipher_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cipher_module)
        
        # Cargar la clave Fernet desde protected_values.py (valores sensibles)
        fernet_key = _env_settings.get_protected_value("fernet_key", "")
        if not fernet_key:
            # Fallback a variable de entorno
            fernet_key = _env_settings.get_env_value("FERNET_KEY", "")
        if not fernet_key:
            logger.error("No se encontró fernet_key en protected_values.py ni en variables de entorno")
            return None
        
        # Crear instancia Fernet y cifrar
        from cryptography.fernet import Fernet
        fernet_instance = Fernet(fernet_key.encode())
        encrypted_bytes = fernet_instance.encrypt(plain_password.encode())
        return encrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.error(f"Error al cifrar contraseña: {e}")
        return None


# ============================================================================
# Funciones de gestión de proyectos
# ============================================================================


def get_organization_projects(
    organization_id: int,
    access_token: str = "",
    session_token: str = "",
) -> list[dict[str, Any]]:
    """
    Obtiene los proyectos de una organización.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        organization_id: ID de la organización
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        Lista de proyectos con estructura:
        [{"id": int, "nombre": str, "descripcion": str, "bloqueado": bool, "id_flujo": int, "active": bool}]
    """
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "GET",
        f"/projects/organization/{organization_id}",
        headers=headers,
    )
    
    if isinstance(response, list):
        return response
    
    return response.get("projects", [])


def create_organization_project(
    organization_id: int,
    project_name: str,
    project_description: str = "",
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Crea un nuevo proyecto en la organización.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    El trigger en BD crea automáticamente:
    - Registro en tabla estado (versión 1, campos según id_flujo=1)
    - Registro en tabla cambios (tipo "Alta proyecto")
    
    Args:
        organization_id: ID de la organización
        project_name: Nombre del proyecto
        project_description: Descripción del proyecto (opcional)
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        {"success": True, "project_id": int} o {"success": False, "error": str}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload = {
        "nombre": project_name,
        "descripcion": project_description,
        "id_organizacion": organization_id,
        "active": True,
        "id_flujo": 1,  # Propuesta Cliente (primer paso del flujo)
    }
    
    response = _request_middleware(
        "POST",
        "/projects",
        payload=payload,
        headers=headers,
    )
    
    if response.get("project_id") or response.get("id"):
        project_id = response.get("project_id") or response.get("id")
        logger.info(f"Proyecto creado exitosamente: project_id={project_id}")
        return {
            "success": True,
            "project_id": project_id,
        }
    
    error_msg = response.get("detail", "Error desconocido al crear proyecto")
    logger.error(f"Error al crear proyecto: {error_msg}")
    return {"success": False, "error": error_msg}


def update_project_status(
    project_id: int,
    active: bool | None = None,
    id_flujo: int | None = None,
    existe: bool | None = None,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Actualiza el estado de un proyecto (activo, flujo, existencia).
    
    IMPORTANTE:
    - 'active' controla el bloqueo: True=activo, False=bloqueado
    - 'existe' controla el borrado lógico: True=existe, False=borrado
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    El trigger en BD registra cambios automáticamente en tabla cambios.
    
    Args:
        project_id: ID del proyecto
        active: Estado activo (True=desbloqueado, False=bloqueado)
        id_flujo: Nuevo paso del flujo (opcional)
        existe: Existencia lógica (True=existe, False=borrado lógico)
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        {"success": True, "updated": True, "project_id": int} o {"success": False, "error": str}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload: dict[str, Any] = {}
    if active is not None:
        payload["active"] = active
    if id_flujo is not None:
        payload["id_flujo"] = id_flujo
    if existe is not None:
        payload["existe"] = existe
    
    response = _request_middleware(
        "PATCH",
        f"/projects/{project_id}",
        payload=payload,
        headers=headers,
    )
    
    if response.get("success") or response.get("updated"):
        logger.info(f"Proyecto actualizado: project_id={project_id}")
        return {"success": True}
    
    error_msg = response.get("detail", "Error al actualizar proyecto")
    logger.error(f"Error al actualizar proyecto: {error_msg}")
    return {"success": False, "error": error_msg}


def delete_organization_project(
    project_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Elimina un proyecto.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    El trigger BEFORE DELETE en BD registra cambio en tabla cambios:
    - tipo "Borrado de proyecto"
    
    Args:
        project_id: ID del proyecto a eliminar
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        {"success": True} o {"success": False, "error": str}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "DELETE",
        f"/projects/{project_id}",
        headers=headers,
    )
    
    if response.get("success") or response.get("deleted"):
        logger.info(f"Proyecto eliminado: project_id={project_id}")
        return {"success": True}
    
    error_msg = response.get("detail", "Error al eliminar proyecto")
    logger.error(f"Error al eliminar proyecto: {error_msg}")
    return {"success": False, "error": error_msg}


def request_project_support_api(
    project_id: int,
    description: str = "",
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Solicita soporte para un proyecto.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Registra cambio en tabla cambios:
    - tipo "Solicitud soporte proyecto"
    
    Args:
        project_id: ID del proyecto
        description: Descripción de la solicitud
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        {"success": True} o {"success": False, "error": str}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload = {
        "project_id": project_id,
        "tipo_cambio": "Solicitud soporte proyecto",
        "descripcion": description or "Solicitud de soporte técnico",
    }
    
    response = _request_middleware(
        "POST",
        f"/projects/{project_id}/support",
        payload=payload,
        headers=headers,
    )
    
    if response.get("success"):
        logger.info(f"Solicitud de soporte registrada: project_id={project_id}")
        return {"success": True}
    
    error_msg = response.get("detail", "Error al solicitar soporte")
    logger.error(f"Error al solicitar soporte: {error_msg}")
    return {"success": False, "error": error_msg}


# ============================================================================
# GESTIÓN DE ROLES DE USUARIO EN PROYECTOS
# ============================================================================


def get_project_roles_base(
    access_token: str = "",
    session_token: str = "",
) -> list[dict[str, Any]]:
    """
    Obtiene el catálogo maestro de roles base para proyectos.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Esta información es reutilizable para selectores de roles
    y validaciones de seguridad.
    
    Args:
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        Lista de roles: [{"id": int, "nombre_rol": str, "descripcion": str}, ...]
    """
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "GET",
        "/project-roles-base",
        headers=headers,
    )
    
    if response is None:
        return []
    
    return response.get("roles", [])


def get_project_roles_base(
    access_token: str = "",
    session_token: str = "",
) -> list[dict[str, Any]]:
    """
    Obtiene el catálogo maestro de roles base para proyectos.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Esta información es reutilizable para selectores de roles
    y validaciones de seguridad.
    
    Args:
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        Lista de roles: [{"id": int, "nombre_rol": str, "descripcion": str}, ...]
    """
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "GET",
        "/project-roles-base",
        headers=headers,
    )
    
    return response.get("roles", [])


def get_user_project_roles(
    user_id: int,
    organization_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene los roles de un usuario en proyectos de una organización.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        user_id: ID del usuario
        organization_id: ID de la organización
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        {"user_id": int, "organization_id": int, "roles": [...], "total": int}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "GET",
        f"/users/{user_id}/project-roles?organization_id={organization_id}",
        headers=headers,
    )
    
    return response


def assign_user_to_project(
    id_usuario: int,
    id_proyecto: int,
    id_organizacion: int,
    id_rol: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Asigna un usuario a un proyecto con un rol específico.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Roles válidos:
        - 3: Editor
        - 4: Lector
        - 5: Auditor
    
    Args:
        id_usuario: ID del usuario a asignar
        id_proyecto: ID del proyecto
        id_organizacion: ID de la organización
        id_rol: ID del rol (3=Editor, 4=Lector, 5=Auditor)
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        {"success": bool, "message": str, "created": bool, ...}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload = {
        "id_usuario": id_usuario,
        "id_proyecto": id_proyecto,
        "id_organizacion": id_organizacion,
        "id_rol": id_rol,
    }
    
    response = _request_middleware(
        "POST",
        "/project-roles/assign",
        payload=payload,
        headers=headers,
    )
    
    if response.get("success"):
        logger.info(
            f"Usuario asignado a proyecto: user={id_usuario}, "
            f"project={id_proyecto}, rol={id_rol}"
        )
        return response
    
    error_msg = response.get("detail", "Error al asignar usuario")
    logger.error(f"Error al asignar usuario: {error_msg}")
    return {"success": False, "error": error_msg}


def remove_user_from_project(
    id_usuario: int,
    id_proyecto: int,
    id_organizacion: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Quita un usuario de un proyecto (desactiva la asignación).
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        id_usuario: ID del usuario a quitar
        id_proyecto: ID del proyecto
        id_organizacion: ID de la organización
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        {"success": bool, "message": str, ...}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload = {
        "id_usuario": id_usuario,
        "id_proyecto": id_proyecto,
        "id_organizacion": id_organizacion,
    }
    
    response = _request_middleware(
        "POST",
        "/project-roles/remove",
        payload=payload,
        headers=headers,
    )
    
    if response.get("success"):
        logger.info(
            f"Usuario quitado de proyecto: user={id_usuario}, project={id_proyecto}"
        )
        return response
    
    error_msg = response.get("detail", "Error al quitar usuario")
    logger.error(f"Error al quitar usuario: {error_msg}")
    return {"success": False, "error": error_msg}


def _build_auth_headers(access_token: str = "", session_token: str = "") -> dict[str, str]:
    """
    Construye headers de autenticación para las peticiones.

    Verifica proactivamente si el access token está próximo a expirar (menos de 2 minutos)
    y si es así, lo refresca automáticamente antes de construir los headers.

    Args:
        access_token: Token JWT de acceso
        session_token: Token de sesión

    Returns:
        Diccionario con headers de autenticación
    """
    # Usar tokens refrescados si existen (tienen prioridad)
    actual_access = _temp_tokens.get("access_token") or access_token
    actual_session = _temp_tokens.get("session_token") or session_token

    # Verificar si el access token está próximo a expirar (menos de 2 minutos)
    if actual_access and actual_session:
        try:
            # Decodificar sin verificar para leer la expiración
            decoded = jwt.decode(actual_access, options={"verify_signature": False})
            exp = decoded.get("exp", 0)
            time_until_expiry = exp - time.time()

            # Si expira en menos de 2 minutos, refrescar proactivamente
            if time_until_expiry < 120:  # 2 minutos
                logger.info(f"[AUTO-REFRESH] Token expira en {int(time_until_expiry)}s, refrescando proactivamente...")
                new_tokens = _refresh_access_token_internal(actual_session)

                if new_tokens and not new_tokens.get("error"):
                    _temp_tokens["access_token"] = new_tokens.get("access_token", "")
                    _temp_tokens["session_token"] = new_tokens.get("session_token", "")
                    actual_access = _temp_tokens["access_token"]
                    actual_session = _temp_tokens["session_token"]
                    logger.info("[AUTO-REFRESH] Tokens refrescados proactivamente")
                else:
                    logger.warning("[AUTO-REFRESH] No se pudo refrescar tokens proactivamente")
        except Exception as e:
            # Si hay error al decodificar, continuar con el token original
            logger.debug(f"[AUTO-REFRESH] No se pudo verificar expiración del token: {e}")

    headers: dict[str, str] = {}
    if actual_access:
        headers["Authorization"] = f"Bearer {actual_access}"
    if actual_session:
        headers["X-Session-Token"] = actual_session
    return headers


# ============================================================================
# TICKETS DE SOPORTE
# ============================================================================


def create_support_ticket(
    titulo: str,
    consulta: str,
    id_proyecto: int | None = None,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Crea un nuevo ticket de soporte.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    El ticket se crea con:
    - estado: "abierto" (automático)
    - prioridad: "media" (automático)
    - cliente_id: usuario de la sesión (automático)
    
    Args:
        titulo: Motivo del ticket (obligatorio)
        consulta: Texto de la consulta (obligatorio)
        id_proyecto: ID del proyecto relacionado (opcional)
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        {"success": True, "ticket_id": int, "mensaje": str} o {"success": False, "error": str}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload: dict[str, Any] = {
        "titulo": titulo.strip(),
        "consulta": consulta.strip(),
    }
    if id_proyecto:
        payload["id_proyecto"] = id_proyecto
    
    response = _request_middleware(
        "POST",
        "/tickets",
        payload=payload,
        headers=headers,
    )
    
    if isinstance(response, dict):
        if response.get("success") or response.get("ticket_id"):
            return {
                "success": True,
                "ticket_id": response.get("ticket_id", 0),
                "mensaje": response.get("mensaje", "Ticket creado"),
            }
        return {"success": False, "error": response.get("error", "Error desconocido")}
    
    return {"success": False, "error": "Respuesta inválida del servidor"}


# ============================================================================
# GESTIÓN DE CONVERSACIONES Y CAMBIOS
# ============================================================================


def get_organization_tickets(
    organization_id: int,
    access_token: str = "",
    session_token: str = "",
) -> list[dict[str, Any]]:
    """
    Obtiene los tickets de una organización.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

    Returns:
        Lista de tickets
    """
    headers = _build_auth_headers(access_token, session_token)

    response = _request_middleware(
        "GET",
        f"/tickets/organization/{organization_id}",
        headers=headers,
    )

    if isinstance(response, list):
        return response
    return response.get("tickets", []) if isinstance(response, dict) else []


def get_user_conversation(
    user_id: int,
    org_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Busca conversación abierta de un usuario.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

    Returns:
        {"found": bool, "id_conversacion": int}
    """
    headers = _build_auth_headers(access_token, session_token)

    response = _request_middleware(
        "GET",
        f"/conversations/user/{user_id}?org_id={org_id}",
        headers=headers,
    )

    if isinstance(response, dict):
        return response
    return {"found": False, "id_conversacion": 0}


def create_conversation(
    id_organizacion: int,
    id_usuario_cliente: int,
    asunto: str = "Consulta sobre proyecto",
    prioridad: str = "media",
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Crea una nueva conversación.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

    Returns:
        {"success": True, "id_conversacion": int}
    """
    headers = _build_auth_headers(access_token, session_token)

    response = _request_middleware(
        "POST",
        "/conversations",
        payload={
            "id_organizacion": id_organizacion,
            "id_usuario_cliente": id_usuario_cliente,
            "asunto": asunto,
            "prioridad": prioridad,
        },
        headers=headers,
    )

    return dict(response) if isinstance(response, dict) else {}


def get_conversation_messages(
    conversation_id: int,
    access_token: str = "",
    session_token: str = "",
) -> list[dict[str, Any]]:
    """
    Obtiene los mensajes de una conversación.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

    Returns:
        Lista de mensajes
    """
    headers = _build_auth_headers(access_token, session_token)

    response = _request_middleware(
        "GET",
        f"/conversations/{conversation_id}/messages",
        headers=headers,
    )

    if isinstance(response, list):
        return response
    return response.get("messages", []) if isinstance(response, dict) else []


def send_conversation_message(
    conversation_id: int,
    id_usuario_emisor: int,
    tipo_emisor: str,
    texto_mensaje: str,
    id_ticket_referenciado: int | None = None,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Envía un mensaje en una conversación.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

    Returns:
        {"success": True, "id_mensaje": int}
    """
    headers = _build_auth_headers(access_token, session_token)

    payload: dict[str, Any] = {
        "id_usuario_emisor": id_usuario_emisor,
        "tipo_emisor": tipo_emisor,
        "texto_mensaje": texto_mensaje,
    }
    if id_ticket_referenciado is not None:
        payload["id_ticket_referenciado"] = id_ticket_referenciado

    response = _request_middleware(
        "POST",
        f"/conversations/{conversation_id}/messages",
        payload=payload,
        headers=headers,
    )

    return dict(response) if isinstance(response, dict) else {}


def mark_conversation_read(
    conversation_id: int,
    tipo_lector: str,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Marca mensajes como leídos.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

    Returns:
        {"success": True}
    """
    headers = _build_auth_headers(access_token, session_token)

    response = _request_middleware(
        "POST",
        f"/conversations/{conversation_id}/mark-read",
        payload={"tipo_lector": tipo_lector},
        headers=headers,
    )

    return dict(response) if isinstance(response, dict) else {}


def get_cambios_calendar(
    org_id: int,
    mes: int | None = None,
    anio: int | None = None,
    proyecto_id: int | None = None,
    access_token: str = "",
    session_token: str = "",
) -> list[dict[str, Any]]:
    """
    Obtiene eventos del calendario agrupados por día.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

    Returns:
        Lista de eventos agrupados por día
    """
    headers = _build_auth_headers(access_token, session_token)

    params = []
    if mes is not None:
        params.append(f"mes={mes}")
    if anio is not None:
        params.append(f"anio={anio}")
    if proyecto_id is not None:
        params.append(f"proyecto_id={proyecto_id}")
    qs = f"?{'&'.join(params)}" if params else ""

    response = _request_middleware(
        "GET",
        f"/cambios/organization/{org_id}{qs}",
        headers=headers,
    )

    if isinstance(response, list):
        return response
    return []


# ============================================================================
# GESTIÓN DE TECNOLOGÍAS
# ============================================================================


def get_tecnologias(
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene la lista de tecnologías disponibles.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

    Returns:
        {"tecnologias": [...], "total": int}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "GET",
        "/tecnologias",
        headers=headers,
    )
    
    return dict(response) if isinstance(response, dict) else {"tecnologias": [], "total": 0}


def get_proyecto_tecnologia(
    project_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene la tecnología asignada a un proyecto.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Returns:
        {"success": True, "asignacion": {...} o None}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "GET",
        f"/proyectos/{project_id}/tecnologia",
        headers=headers,
    )
    
    return dict(response) if isinstance(response, dict) else {"success": False, "asignacion": None}


def asignar_tecnologia(
    project_id: int,
    id_tecnologia: int,
    coste_base: str = "17% sobre base",
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Asigna una tecnología a un proyecto (primera asignación).
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Returns:
        {"success": True, "asignacion": {...}}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload = {
        "id_tecnologia": id_tecnologia,
        "coste_base": coste_base,
    }
    
    response = _request_middleware(
        "POST",
        f"/proyectos/{project_id}/tecnologia",
        payload=payload,
        headers=headers,
    )
    
    return dict(response) if isinstance(response, dict) else {"success": False}


def actualizar_tecnologia(
    project_id: int,
    id_tecnologia: int,
    coste_base: str = "17% sobre base",
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Actualiza la tecnología de un proyecto (solo Backoffice).
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Returns:
        {"success": True, "asignacion": {...}}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload = {
        "id_tecnologia": id_tecnologia,
        "coste_base": coste_base,
    }
    
    response = _request_middleware(
        "PATCH",
        f"/proyectos/{project_id}/tecnologia",
        payload=payload,
        headers=headers,
    )
    
    return dict(response) if isinstance(response, dict) else {"success": False}


def get_tecnologias_asignadas_org(
    org_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene todas las tecnologías asignadas a proyectos de una organización.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Returns:
        {"asignaciones": [{"project_id": int, "project_name": str, 
                          "tecnologia_id": int|None, "tecnologia_name": str|None}], 
         "total": int}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "GET",
        f"/organizaciones/{org_id}/tecnologias-asignadas",
        headers=headers,
    )
    
    return dict(response) if isinstance(response, dict) else {"asignaciones": [], "total": 0}


# ============================================================================
# GESTIÓN DE VERSIONES
# ============================================================================


def get_project_versions(
    project_id: int,
    organization_id: int = 0,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene todas las versiones de un proyecto.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        project_id: ID del proyecto
        organization_id: ID de la organización (requerido por el middleware)
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {"versiones": [{"id_version": int, "id_proyecto": int, 
                        "id_organizacion": int, "version_folder": str}], 
         "total": int}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "GET",
        f"/proyectos/{project_id}/versiones?org_id={organization_id}",
        headers=headers,
    )
    
    return dict(response) if isinstance(response, dict) else {"versiones": [], "total": 0}


def create_project_version(
    project_id: int,
    organization_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Crea una nueva versión para un proyecto.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        project_id: ID del proyecto
        organization_id: ID de la organización
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {"success": bool, "version": VersionDto | None, "mensaje": str | None}
    """
    headers = _build_auth_headers(access_token, session_token)
    payload = {
        "id_proyecto": project_id,
        "id_organizacion": organization_id,
    }
    
    response = _request_middleware(
        "POST",
        f"/proyectos/{project_id}/versiones",
        headers=headers,
        payload=payload,
    )
    
    return dict(response) if isinstance(response, dict) else {"success": False}


# ============================================================================
# Gestión de Estados de Versión
# ============================================================================


def get_version_state(
    project_id: int,
    version_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene el estado actual de una versión.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        project_id: ID del proyecto
        version_id: ID de la versión
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {
            "success": bool,
            "state": {
                "id": int,
                "id_organizacion": int,
                "id_proyecto": int,
                "id_version": int,
                "state": str,  # "Abierta", "Bloqueada", "Protegida", "Final"
                "protected": bool,
                "size_bytes": int,
                "final_c": bool,
                "final_i": bool,
                "created_at": str,
                "updated_at": str,
                "updated_by_user_id": int | None
            } | None,
            "mensaje": str | None
        }
    """
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "GET",
        f"/proyectos/{project_id}/versiones/{version_id}/estado",
        headers=headers,
    )
    
    return dict(response) if isinstance(response, dict) else {"success": False}


def update_version_state(
    project_id: int,
    version_id: int,
    state: str | None = None,
    protected: bool | None = None,
    size_bytes: int | None = None,
    final_c: bool | None = None,
    final_i: bool | None = None,
    updated_by_user_id: int | None = None,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Actualiza el estado de una versión.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        project_id: ID del proyecto
        version_id: ID de la versión
        state: Nuevo estado ("Abierta", "Bloqueada", "Protegida", "Final")
        protected: Marca de protección
        size_bytes: Tamaño en bytes
        final_c: Finalización por cliente
        final_i: Finalización por interno
        updated_by_user_id: ID del usuario que actualiza
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {
            "success": bool,
            "state": VersionStateDto | None,
            "mensaje": str | None
        }
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload = {}
    if state is not None:
        payload["state"] = state
    if protected is not None:
        payload["protected"] = protected
    if size_bytes is not None:
        payload["size_bytes"] = size_bytes
    if final_c is not None:
        payload["final_c"] = final_c
    if final_i is not None:
        payload["final_i"] = final_i
    if updated_by_user_id is not None:
        payload["updated_by_user_id"] = updated_by_user_id
    
    response = _request_middleware(
        "PATCH",
        f"/proyectos/{project_id}/versiones/{version_id}/estado",
        headers=headers,
        payload=payload,
    )
    
    return dict(response) if isinstance(response, dict) else {"success": False}


def get_version_events(
    project_id: int,
    version_id: int,
    limit: int = 50,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene el historial de eventos de una versión.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        project_id: ID del proyecto
        version_id: ID de la versión
        limit: Número máximo de eventos a retornar
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {
            "success": bool,
            "events": [
                {
                    "id": int,
                    "id_organizacion": int,
                    "id_proyecto": int,
                    "id_version": int,
                    "evento": str,
                    "mensaje": str | None,
                    "user_id": int,
                    "user_name": str | None,
                    "old_state": str | None,
                    "new_state": str | None,
                    "metadata": dict | None,
                    "timestamp": str
                }
            ],
            "total": int,
            "mensaje": str | None
        }
    """
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "GET",
        f"/proyectos/{project_id}/versiones/{version_id}/eventos?limit={limit}",
        headers=headers,
    )
    
    return dict(response) if isinstance(response, dict) else {"success": False, "events": [], "total": 0}


def create_version_full(
    project_id: int,
    organization_id: int,
    version_name: str,
    user_id: int,
    user_name: str,
    identity_type_id: int,
    description: str | None = None,
    clone_from_version_id: int | None = None,
    initial_state: str = "Abierta",
    protected: bool = False,
    final_c: bool = False,
    final_i: bool = False,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Crea una nueva versión completa (DB + fmanagement).
    
    Esta operación es atómica:
    1. Inserta en tabla versiones
    2. Inserta en tabla version_states
    3. Inserta en tabla version_events
    4. Crea carpeta física vía fmanagement (clonando si se especifica)
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB + fmanagement
    
    Args:
        project_id: ID del proyecto
        organization_id: ID de la organización
        version_name: Nombre de la versión (ej: "V001")
        user_id: ID del usuario que crea
        user_name: Nombre del usuario que crea
        identity_type_id: ID del tipo de identidad del usuario (1=SuperAdmin, 2=OrgAdmin, etc.)
        description: Descripción opcional
        clone_from_version_id: ID de versión a clonar (opcional)
        initial_state: Estado inicial ("Abierta", "Bloqueada", "Protegida", "Final")
        protected: Marca de protección
        final_c: Finalización por cliente
        final_i: Finalización por interno
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {
            "success": bool,
            "version": VersionDto | None,
            "state": VersionStateDto | None,
            "mensaje": str | None
        }
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload = {
        "id_organizacion": organization_id,
        "nombre_version": version_name,
        "user_id": user_id,
        "user_name": user_name,
        "identity_type_id": identity_type_id,
        "initial_state": initial_state,
        "protected": protected,
        "final_c": final_c,
        "final_i": final_i,
    }
    
    if description is not None:
        payload["descripcion"] = description
    if clone_from_version_id is not None:
        payload["clone_from_version_id"] = clone_from_version_id
    
    response = _request_middleware(
        "POST",
        f"/proyectos/{project_id}/versiones/crear-completa",
        headers=headers,
        payload=payload,
    )
    
    return dict(response) if isinstance(response, dict) else {"success": False}


# ============================================================================
# Integración con fmanagement
# ============================================================================


def fmanagement_list(
    org_folder: str,
    prj_folder: str,
    version_folder: str,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Lista estructura de archivos vía fmanagement.

    Flujo: Frontend → Middleware → Broker → Backend Core → fmanagement

    Args:
        org_folder: Carpeta de organización (ej: "ORG00001")
        prj_folder: Carpeta de proyecto (ej: "PRJ0001")
        version_folder: Carpeta de versión (ej: "V001")
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        {
            "success": bool,
            "items": [
                {
                    "name": str,
                    "type": str,  # "folder" | "file"
                    "path": str,
                    "size": int | None,
                    "modified": str | None
                }
            ],
            "mensaje": str | None
        }
    """
    headers = _build_auth_headers(access_token, session_token)

    payload = {
        "org_folder": org_folder,
        "prj_folder": prj_folder,
        "version_folder": version_folder,
    }

    response = _request_middleware(
        "POST",
        "/fmanagement/list",
        headers=headers,
        payload=payload,
    )

    return dict(response) if isinstance(response, dict) else {"success": False, "items": []}


def fmanagement_list_for_explorador(
    org_id: int,
    project_id: int,
    version_name: str,
    org_folder: str = "",
    prj_folder: str = "",
    owner_user_id: int = 0,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Lista estructura de archivos y la convierte al formato del componente explorador.

    Esta función combina fmanagement_list con el adaptador para retornar
    directamente el formato jerárquico que espera el explorador.

    Flujo: Frontend → Middleware → Broker → Backend Core → fmanagement → Adaptador

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_name: Nombre de la versión (ej: "v001")
        org_folder: Carpeta de organización (ej: "ORG00001"), se genera si no se provee
        prj_folder: Carpeta de proyecto (ej: "PRJ00001"), se genera si no se provee
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        Estructura jerárquica para el explorador:
        {
            "status": "success",
            "path": str,
            "items": [
                {
                    "name": str (proyecto),
                    "is_dir": true,
                    "size_bytes": int,
                    "items": [
                        {
                            "name": str (versión),
                            "is_dir": true,
                            "size_bytes": int,
                            "items": [...contenido...]
                        }
                    ]
                }
            ]
        }
    """
    # Generar nombres de carpetas si no se proveen
    if not org_folder:
        org_folder = _account_storage_folder(org_id, owner_user_id)
    if not prj_folder:
        prj_folder = _project_storage_folder(project_id)

    # Llamar a fmanagement_list
    fmanagement_response = fmanagement_list(
        org_folder=org_folder,
        prj_folder=prj_folder,
        version_folder=version_name,
        access_token=access_token,
        session_token=session_token,
    )

    # Importar y usar el adaptador
    try:
        adapter_path = (
            Path(__file__).resolve().parents[3]
            / "2_shared_application/adapters/fmanagement_to_explorador.py"
        )
        spec = importlib.util.spec_from_file_location("fmanagement_adapter", adapter_path)
        if spec is None or spec.loader is None:
            logger.error("No se pudo cargar el adaptador de fmanagement")
            return {"status": "error", "path": "", "items": []}

        adapter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter_module)

        # Convertir respuesta al formato del explorador
        explorador_data = adapter_module.convert_fmanagement_to_explorador(
            fmanagement_response=fmanagement_response,
            org_id=org_id,
            project_id=project_id,
            version_name=version_name,
            org_folder=org_folder,
            prj_folder=prj_folder,
        )

        return explorador_data
    except Exception as e:
        logger.error(f"Error al convertir respuesta de fmanagement: {e}")
        return {
            "status": "error",
            "path": "",
            "items": [],
            "mensaje": f"Error al procesar estructura de archivos: {e}"
        }


def _calculate_structure_size(items: list[dict]) -> int:
    """Calcula el tamaño total de una estructura jerárquica de fmanagement.

    Args:
        items: Lista de items (carpetas y archivos) de fmanagement

    Returns:
        Tamaño total en bytes
    """
    total_size = 0
    print(f"DEBUG _calculate_structure_size: Procesando {len(items)} items")
    for item in items:
        is_dir = item.get("is_dir", True)
        item_name = item.get("name", "unnamed")
        print(f"  - Item: {item_name}, is_dir: {is_dir}, tiene 'items': {'items' in item}, tiene 'size_bytes': {'size_bytes' in item}")
        if is_dir:
            # Es una carpeta, sumar recursivamente
            child_items = item.get("items")
            if child_items is not None:
                print(f"    Carpeta {item_name} tiene {len(child_items)} items hijos")
                total_size += _calculate_structure_size(child_items)
            else:
                print(f"    Carpeta {item_name} tiene items=None")
        else:
            # Es un archivo, sumar su tamaño
            file_size = item.get("size_bytes", 0)
            print(f"    Archivo {item_name} tiene {file_size} bytes")
            total_size += file_size
    print(f"DEBUG _calculate_structure_size: Total calculado = {total_size} bytes")
    return total_size


def fmanagement_list_all_project_versions(
    org_id: int,
    project_id: int,
    org_folder: str = "",
    prj_folder: str = "",
    owner_user_id: int = 0,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Lista todas las versiones de un proyecto con sus estructuras de archivos.

    Esta función descubre las versiones directamente desde DISCO vía fmanagement
    (no desde la BD), y carga el contenido de cada una, construyendo una
    estructura jerárquica completa para el explorador.

    Flujo: Frontend → Middleware → Broker → Backend Core → fmanagement (disco)

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        org_folder: Carpeta de organización (ej: "ORG00001"), se genera si no se provee
        prj_folder: Carpeta de proyecto (ej: "PRJ00001"), se genera si no se provee
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        Estructura jerárquica completa para el explorador:
        {
            "status": "success",
            "path": str,
            "items": [
                {
                    "name": str (proyecto),
                    "is_dir": true,
                    "size_bytes": int,
                    "items": [
                        {
                            "name": "v001",
                            "is_dir": true,
                            "size_bytes": int,
                            "items": [...contenido v001...]
                        },
                        {
                            "name": "v002",
                            "is_dir": true,
                            "size_bytes": int,
                            "items": [...contenido v002...]
                        }
                    ]
                }
            ]
        }
    """
    # Generar nombres de carpetas si no se proveen
    if not org_folder:
        org_folder = _account_storage_folder(org_id, owner_user_id)
    if not prj_folder:
        prj_folder = _project_storage_folder(project_id)

    # 1. Obtener lista de versiones desde DISCO vía fmanagement (no desde BD)
    #    Llamamos a fmanagement_list con version_folder="" para listar el
    #    directorio del proyecto, que contiene las carpetas de versión (v001, v002, etc.)
    import re as _re

    project_listing = fmanagement_list(
        org_folder=org_folder,
        prj_folder=prj_folder,
        version_folder="",
        access_token=access_token,
        session_token=session_token,
    )

    # Extraer carpetas de versión del listado de disco (filtrar por patrón v\d{3})
    disk_items = project_listing.get("items", [])
    version_folders = sorted(
        [item["name"] for item in disk_items
         if item.get("is_dir") and _re.match(r'^v\d{3}$', item.get("name", ""))],
    )

    if not version_folders:
        logger.warning(f"No se encontraron versiones en disco para el proyecto {project_id}")
        return {
            "status": "success",
            "path": f"/data/external/{org_folder}/{prj_folder}",
            "items": [{
                "name": prj_folder,
                "is_dir": True,
                "size_bytes": 0,
                "items": []
            }]
        }

    logger.info(f"Versiones encontradas en disco: {version_folders}")

    # 2. Para cada versión en disco, obtener su contenido desde fmanagement
    versions_data = []

    for version_name in version_folders:
        logger.info(f"Cargando contenido de versión {version_name} para proyecto {project_id}")

        # Llamar a fmanagement_list para esta versión
        fmanagement_response = fmanagement_list(
            org_folder=org_folder,
            prj_folder=prj_folder,
            version_folder=version_name,
            access_token=access_token,
            session_token=session_token,
        )

        versions_data.append({
            "version_name": version_name,
            "fmanagement_response": fmanagement_response
        })

    # 3. Usar el adaptador para convertir todas las versiones al formato del explorador
    try:
        adapter_path = (
            Path(__file__).resolve().parents[3]
            / "2_shared_application/adapters/fmanagement_to_explorador.py"
        )
        spec = importlib.util.spec_from_file_location("fmanagement_adapter", adapter_path)
        if spec is None or spec.loader is None:
            logger.error("No se pudo cargar el adaptador de fmanagement")
            return {"status": "error", "path": "", "items": []}

        adapter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter_module)

        # Convertir todas las versiones al formato del explorador
        explorador_data = adapter_module.convert_multiple_versions_to_explorador(
            versions_data=versions_data,
            org_id=org_id,
            project_id=project_id,
            org_folder=org_folder,
            prj_folder=prj_folder,
        )

        # 4. Calcular y actualizar tamaños de cada versión en la BD
        print(f"DEBUG: Verificando actualización de tamaños. Status: {explorador_data.get('status')}, Items: {len(explorador_data.get('items', []))}")
        if explorador_data.get("status") == "success" and explorador_data.get("items"):
            project_item = explorador_data["items"][0]
            version_items = project_item.get("items", [])
            print(f"DEBUG: Encontrados {len(version_items)} items de versiones para procesar")

            for version_item in version_items:
                version_name = version_item.get("name", "")  # ej: "v001"
                print(f"DEBUG: Procesando item: {version_name}, is_dir: {version_item.get('is_dir')}")
                if version_name.startswith("v"):
                    try:
                        version_id = int(version_name[1:])  # Convertir "v001" a 1
                        print(f"DEBUG: Calculando tamaño para versión {version_id} ({version_name})")

                        # Calcular tamaño total de esta versión
                        version_size = _calculate_structure_size(version_item.get("items", []))
                        print(f"DEBUG: Tamaño calculado para {version_name}: {version_size} bytes")

                        # Actualizar size_bytes en la BD
                        update_result = update_version_state(
                            project_id=project_id,
                            version_id=version_id,
                            size_bytes=version_size,
                            access_token=access_token,
                            session_token=session_token,
                        )
                        print(f"DEBUG: Resultado de actualización: {update_result}")

                        if update_result.get("success"):
                            logger.info(f"Tamaño actualizado para {version_name}: {version_size} bytes")
                            print(f"✓ Tamaño actualizado para {version_name}: {version_size} bytes")
                        else:
                            logger.warning(f"No se pudo actualizar tamaño para {version_name}")
                            print(f"✗ No se pudo actualizar tamaño para {version_name}: {update_result}")
                    except (ValueError, Exception) as e:
                        logger.error(f"Error procesando tamaño de {version_name}: {e}")
                        print(f"✗ Error procesando tamaño de {version_name}: {e}")

        logger.info(f"Estructura cargada: proyecto {prj_folder} con {len(version_folders)} versiones (desde disco)")
        return explorador_data

    except Exception as e:
        logger.error(f"Error al convertir respuesta de fmanagement para múltiples versiones: {e}")
        return {
            "status": "error",
            "path": "",
            "items": [],
            "mensaje": f"Error al procesar estructura de archivos: {e}"
        }


def fmanagement_operation(
    operation: str,
    params: dict[str, Any],
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Ejecuta una operación genérica en fmanagement.
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload = {
        "operation": operation,
        "params": params,
    }
    
    response = _request_middleware(
        "POST",
        "/fmanagement/operation",
        headers=headers,
        payload=payload,
    )
    
    return dict(response) if isinstance(response, dict) else {"success": False}


def fmanagement_download(
    params: dict[str, Any],
    access_token: str = "",
    session_token: str = "",
) -> bytes:
    """Descarga un archivo vía fmanagement."""
    headers = _build_auth_headers(access_token, session_token)
    
    payload = {
        "operation": "download_file",
        "params": params,
    }
    
    content, _ = _request_middleware_raw(
        "POST",
        "/fmanagement/download",
        headers=headers,
        payload=payload,
    )
    return content


def fmanagement_diff(
    params: dict[str, Any],
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Compara versiones vía fmanagement."""
    headers = _build_auth_headers(access_token, session_token)
    
    response = _request_middleware(
        "POST",
        "/fmanagement/diff",
        headers=headers,
        payload=params,
    )
    return dict(response) if isinstance(response, dict) else {"success": False}


def fmanagement_transfer(
    params: dict[str, Any],
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Transfiere versiones vía fmanagement."""
    headers = _build_auth_headers(access_token, session_token)

    response = _request_middleware(
        "POST",
        "/fmanagement/transfer",
        headers=headers,
        payload=params,
    )
    return dict(response) if isinstance(response, dict) else {"success": False}


def generate_file_upload_token(
    project_id: int,
    version_id: int,
    relative_path: str = "",
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Genera un token JWT temporal para subida de archivos.

    Args:
        project_id: ID del proyecto
        version_id: ID de la versión
        relative_path: Ruta relativa dentro de la versión
        access_token: Token de acceso del usuario
        session_token: Token de sesión del usuario

    Returns:
        Dict con:
        - success: bool
        - token: str (JWT token)
        - fmanagement_url: str (URL de fmanagement)
        - expires_in: int (segundos)
        - expires_at: int (timestamp)
    """
    headers = _build_auth_headers(access_token, session_token)

    payload = {
        "project_id": project_id,
        "version_id": version_id,
        "operation": "upload",
        "relative_path": relative_path,
    }

    response = _request_middleware(
        "POST",
        "/files/generate-token",
        headers=headers,
        payload=payload,
    )
    return dict(response) if isinstance(response, dict) else {"success": False}


def generate_file_download_token(
    project_id: int,
    version_id: int,
    filename: str,
    relative_path: str = "",
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Genera un token JWT temporal para descarga de archivos.

    Args:
        project_id: ID del proyecto
        version_id: ID de la versión
        filename: Nombre del archivo a descargar
        relative_path: Ruta relativa dentro de la versión
        access_token: Token de acceso del usuario
        session_token: Token de sesión del usuario

    Returns:
        Dict con:
        - success: bool
        - token: str (JWT token)
        - fmanagement_url: str (URL de fmanagement)
        - expires_in: int (segundos)
        - expires_at: int (timestamp)
        - download_url: str (URL completa para descargar)
    """
    headers = _build_auth_headers(access_token, session_token)

    payload = {
        "project_id": project_id,
        "version_id": version_id,
        "operation": "download",
        "relative_path": relative_path,
    }

    response = _request_middleware(
        "POST",
        "/files/generate-token",
        headers=headers,
        payload=payload,
    )

    # Si fue exitoso, construir la URL de descarga completa
    if response.get("success") and response.get("token") and response.get("fmanagement_url"):
        import urllib.parse
        token = response["token"]
        fmanagement_url = response["fmanagement_url"]
        encoded_filename = urllib.parse.quote(filename)
        download_url = f"{fmanagement_url}/download?token={token}&filename={encoded_filename}"
        response["download_url"] = download_url

    return dict(response) if isinstance(response, dict) else {"success": False}


def fmanagement_create_folder(
    org_id: int,
    project_id: int,
    version_id: int,
    folder_path: str,
    folder_name: str,
    user_id: int,
    identity_type_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Crea una carpeta en fmanagement.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        folder_path: Ruta relativa donde crear la carpeta
        folder_name: Nombre de la nueva carpeta
        user_id: ID del usuario
        identity_type_id: Tipo de identidad del usuario
        access_token: Token de acceso
        session_token: Token de sesión

    Returns:
        Dict con success, message, path
    """
    headers = _build_auth_headers(access_token, session_token)

    # Construir ruta completa
    org_folder = _account_storage_folder(org_id, user_id)
    prj_folder = _project_storage_folder(project_id)
    version_folder = _version_storage_folder(version_id)

    # Si folder_path está vacío, crear en la raíz de la versión
    subfolders = f"{folder_path}/{folder_name}" if folder_path else folder_name

    payload = {
        "operation": "create_folder",
        "params": {
            "iduser": user_id,
            "orgpath": org_folder,
            "prjpath": prj_folder,
            "versionpath": version_folder,
            "subfolders": subfolders,
            "identity_type_id": identity_type_id,
        }
    }

    response = _request_middleware(
        "POST",
        "/fmanagement/operation",
        headers=headers,
        payload=payload,
    )
    return dict(response) if isinstance(response, dict) else {"success": False}


def fmanagement_rename_folder(
    org_id: int,
    project_id: int,
    version_id: int,
    folder_path: str,
    old_name: str,
    new_name: str,
    user_id: int,
    identity_type_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Renombra una carpeta en fmanagement.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        folder_path: Ruta relativa de la carpeta
        old_name: Nombre actual de la carpeta
        new_name: Nuevo nombre de la carpeta
        user_id: ID del usuario
        identity_type_id: Tipo de identidad del usuario
        access_token: Token de acceso
        session_token: Token de sesión

    Returns:
        Dict con success, message, old, new
    """
    headers = _build_auth_headers(access_token, session_token)

    org_folder = _account_storage_folder(org_id, user_id)
    prj_folder = _project_storage_folder(project_id)
    version_folder = _version_storage_folder(version_id)

    # subfolders debe incluir el nombre actual
    subfolders = f"{folder_path}/{old_name}" if folder_path else old_name

    payload = {
        "operation": "rename_folder",
        "params": {
            "iduser": user_id,
            "orgpath": org_folder,
            "prjpath": prj_folder,
            "versionpath": version_folder,
            "subfolders": subfolders,
            "new_filename": new_name,
            "identity_type_id": identity_type_id,
        }
    }

    response = _request_middleware(
        "POST",
        "/fmanagement/operation",
        headers=headers,
        payload=payload,
    )
    return dict(response) if isinstance(response, dict) else {"success": False}


def fmanagement_delete_folder(
    org_id: int,
    project_id: int,
    version_id: int,
    folder_path: str,
    folder_name: str,
    user_id: int,
    identity_type_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Elimina una carpeta en fmanagement.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        folder_path: Ruta relativa de la carpeta
        folder_name: Nombre de la carpeta a eliminar
        user_id: ID del usuario
        identity_type_id: Tipo de identidad del usuario
        access_token: Token de acceso
        session_token: Token de sesión

    Returns:
        Dict con success, message, path
    """
    headers = _build_auth_headers(access_token, session_token)

    org_folder = _account_storage_folder(org_id, user_id)
    prj_folder = _project_storage_folder(project_id)
    version_folder = _version_storage_folder(version_id)

    subfolders = f"{folder_path}/{folder_name}" if folder_path else folder_name

    payload = {
        "operation": "delete_folder",
        "params": {
            "iduser": user_id,
            "orgpath": org_folder,
            "prjpath": prj_folder,
            "versionpath": version_folder,
            "subfolders": subfolders,
            "identity_type_id": identity_type_id,
        }
    }

    response = _request_middleware(
        "POST",
        "/fmanagement/operation",
        headers=headers,
        payload=payload,
    )
    return dict(response) if isinstance(response, dict) else {"success": False}


def fmanagement_rename_file(
    org_id: int,
    project_id: int,
    version_id: int,
    file_path: str,
    old_filename: str,
    new_filename: str,
    user_id: int,
    identity_type_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Renombra un archivo en fmanagement.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        file_path: Ruta relativa del archivo
        old_filename: Nombre actual del archivo (con extensión)
        new_filename: Nuevo nombre del archivo (con extensión)
        user_id: ID del usuario
        identity_type_id: Tipo de identidad del usuario
        access_token: Token de acceso
        session_token: Token de sesión

    Returns:
        Dict con success, message, old, new
    """
    headers = _build_auth_headers(access_token, session_token)

    org_folder = _account_storage_folder(org_id, user_id)
    prj_folder = _project_storage_folder(project_id)
    version_folder = _version_storage_folder(version_id)

    # Extraer nombre y extensión del archivo actual
    import os
    name_part, ext_part = os.path.splitext(old_filename)
    new_name_part, new_ext_part = os.path.splitext(new_filename)

    payload = {
        "operation": "rename_file",
        "params": {
            "iduser": user_id,
            "orgpath": org_folder,
            "prjpath": prj_folder,
            "versionpath": version_folder,
            "subfolders": file_path,
            "filename": name_part,
            "extfile": ext_part.lstrip('.'),
            "new_filename": new_name_part,
            "new_extfile": new_ext_part.lstrip('.'),
            "operation": "rename",
            "identity_type_id": identity_type_id,
        }
    }

    response = _request_middleware(
        "POST",
        "/fmanagement/operation",
        headers=headers,
        payload=payload,
    )
    return dict(response) if isinstance(response, dict) else {"success": False}


def fmanagement_delete_file(
    org_id: int,
    project_id: int,
    version_id: int,
    file_path: str,
    filename: str,
    user_id: int,
    identity_type_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Elimina un archivo en fmanagement.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        file_path: Ruta relativa del archivo
        filename: Nombre del archivo a eliminar (con extensión)
        user_id: ID del usuario
        identity_type_id: Tipo de identidad del usuario
        access_token: Token de acceso
        session_token: Token de sesión

    Returns:
        Dict con success, message, path
    """
    headers = _build_auth_headers(access_token, session_token)

    org_folder = _account_storage_folder(org_id, user_id)
    prj_folder = _project_storage_folder(project_id)
    version_folder = _version_storage_folder(version_id)

    import os
    name_part, ext_part = os.path.splitext(filename)

    payload = {
        "operation": "delete_file",
        "params": {
            "iduser": user_id,
            "orgpath": org_folder,
            "prjpath": prj_folder,
            "versionpath": version_folder,
            "subfolders": file_path,
            "filename": name_part,
            "extfile": ext_part.lstrip('.'),
            "operation": "delete",
            "identity_type_id": identity_type_id,
        }
    }

    response = _request_middleware(
        "POST",
        "/fmanagement/operation",
        headers=headers,
        payload=payload,
    )
    return dict(response) if isinstance(response, dict) else {"success": False}


def fmanagement_get_properties(
    org_id: int,
    project_id: int,
    version_id: int,
    item_path: str,
    item_name: str,
    is_folder: bool,
    user_id: int = 0,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Obtiene las propiedades de un archivo o carpeta usando el comando 'file'.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        item_path: Ruta relativa del elemento
        item_name: Nombre del elemento
        is_folder: True si es carpeta, False si es archivo
        access_token: Token de acceso
        session_token: Token de sesión

    Returns:
        Dict con propiedades: name, path, size_bytes, mode, mod_time, file_output
    """
    headers = _build_auth_headers(access_token, session_token)

    org_folder = _account_storage_folder(org_id, user_id)
    prj_folder = _project_storage_folder(project_id)
    version_folder = _version_storage_folder(version_id)

    payload = {
        "operation": "get_properties",
        "params": {
            "orgpath": org_folder,
            "prjpath": prj_folder,
            "versionpath": version_folder,
            "subfolders": item_path,
            "filename": "" if is_folder else item_name,
        }
    }

    response = _request_middleware(
        "POST",
        "/fmanagement/operation",
        headers=headers,
        payload=payload,
    )
    return dict(response) if isinstance(response, dict) else {"success": False}


def list_informe_files(
    org_id: int,
    project_id: int,
    version_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Lista los archivos markdown de informes para una versión.

    Flujo: Frontend → Middleware → Broker → Backend Core → filesystem

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        {"archivos": [{"filename": str, "display_name": str}], "total": int}
    """
    headers = _build_auth_headers(access_token, session_token)

    response = _request_middleware(
        "GET",
        f"/informes/{org_id}/{project_id}/{version_id}/files",
        headers=headers,
    )

    return dict(response) if isinstance(response, dict) else {"archivos": [], "total": 0}


def get_informe_content(
    org_id: int,
    project_id: int,
    version_id: int,
    display_name: str,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene el contenido de un archivo markdown de informe.

    Flujo: Frontend → Middleware → Broker → Backend Core → filesystem

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        display_name: Nombre del archivo a leer
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        {"content": str, "display_name": str}
    """
    from urllib.parse import quote
    headers = _build_auth_headers(access_token, session_token)

    response = _request_middleware(
        "GET",
        f"/informes/{org_id}/{project_id}/{version_id}/content?file={quote(display_name)}",
        headers=headers,
    )

    return dict(response) if isinstance(response, dict) else {"content": "", "display_name": ""}

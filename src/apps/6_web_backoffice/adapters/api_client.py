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
    spec = importlib.util.spec_from_file_location("env_settings_backoffice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el módulo de configuración")
    module = importlib.util.module_from_spec(spec)
    sys.modules["env_settings_backoffice"] = module
    spec.loader.exec_module(module)
    return module


_env_settings = _load_env_settings_module()

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
    
    Utiliza la función get_user_by_name_exist del módulo de dominio.
    
    Args:
        user_name: Nombre de usuario a verificar.
    
    Returns:
        True si el usuario existe, False en caso contrario.
    """
    if _get_user_by_name_exist_function is None:
        logger.warning("La función get_user_by_name_exist no está disponible")
        return False
    
    try:
        return _get_user_by_name_exist_function(user_name)
    except Exception as e:
        logger.error(f"Error al verificar nombre de usuario: {e}")
        return False


def save_user_to_json(user_extended: Any) -> bool:
    """
    Guarda un usuario UserExtended a través del middleware.

    Args:
        user_extended: Objeto UserExtended a guardar.
    
    Returns:
        True si el usuario se guardó exitosamente, False en caso contrario.
    """
    try:
        # Convertir UserExtended a diccionario
        user_dict = _user_extended_to_dict(user_extended)
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
            "X-Client-App": "backoffice",
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
        "X-Client-App": "backoffice",
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
                detail = error_data.get("detail", "Error desconocido")

                # Si detail es un array de errores de validación de Pydantic, convertirlo a string
                if isinstance(detail, list) and len(detail) > 0:
                    if isinstance(detail[0], dict) and "msg" in detail[0]:
                        # Es un error de validación de Pydantic
                        error_messages = [f"{err.get('loc', [''])[0]}: {err.get('msg', '')}" for err in detail]
                        error_message = "Errores de validación: " + "; ".join(error_messages)
                    else:
                        error_message = str(detail)
                else:
                    error_message = str(detail) if not isinstance(detail, str) else detail
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


def login_user(user_name: str, password: str, otp: str) -> dict[str, Any]:
    """Solicita autenticación al middleware."""

    payload = {"user_name": user_name, "password": password, "otp": otp}
    return _request_middleware("POST", "/login", payload=payload)


def request_login_otp(user_name: str, password: str) -> dict[str, Any]:
    """Solicita el envío del OTP al middleware."""

    payload = {"user_name": user_name, "password": password}
    return _request_middleware("POST", "/login/request-otp", payload=payload)


def refresh_tokens(session_token: str) -> dict[str, Any]:
    """Solicita renovación de tokens al middleware."""

    return _request_middleware(
        "POST", "/refresh-token", headers={"X-Session-Token": session_token}
    )


def _build_auth_headers(access_token: str = "", session_token: str = "") -> dict[str, str]:
    """Construye headers de autenticación para las peticiones.

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


# Umbral de renovación: 2 minutos antes de expirar
RENEWAL_THRESHOLD_SECONDS = 120


def _should_renew_token(expires_at: int) -> bool:
    """Verifica si el token está próximo a expirar.
    
    Args:
        expires_at: Unix timestamp de expiración del token
        
    Returns:
        True si el token expira en menos de RENEWAL_THRESHOLD_SECONDS
    """
    import time
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
    active_only: bool = False,
) -> list[dict[str, Any]]:
    """
    Obtiene los usuarios de una organización filtrados por identity_type_id.
    
    Args:
        organization_id: ID de la organización
        access_token: Token de acceso JWT
        session_token: Token de sesión
        identity_type_id: Filtrar por tipo de identidad (default: 5 = auditores)
        active_only: Si True, solo retorna usuarios activos (default: False en backoffice)
                     El backoffice muestra TODOS los usuarios para poder reactivarlos
    
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


def get_organization_projects(
    organization_id: int,
    access_token: str | None = None,
    session_token: str | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    """
    Obtiene los proyectos de una organización.
    
    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        organization_id: ID de la organización
        access_token: Token JWT de acceso
        session_token: Token de sesión
        include_deleted: Si True, incluye proyectos con existe=false (borrados lógicos)
    
    Returns:
        Lista de proyectos con estructura:
        [{"id": int, "name": str, "descripcion": str, "active": bool, "existe": bool, "id_flujo": int}]
    """
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token
    
    # Añadir query param para incluir borrados
    path = f"/projects/organization/{organization_id}"
    if include_deleted:
        path += "?include_deleted=true"
    
    response = _request_middleware("GET", path, headers=headers)
    
    if isinstance(response, list):
        projects = response
    else:
        projects = response.get("projects", [])
    
    logger.info(f"Obtenidos {len(projects)} proyectos de organización {organization_id}")
    return projects


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
        "X-Client-App": "backoffice",
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


def update_project_status(
    project_id: int,
    active: bool,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """
    Actualiza el estado activo/bloqueado de un proyecto.
    
    IMPORTANTE: Este es un bloqueo LÓGICO, no un borrado físico.
    - active=True: Proyecto desbloqueado (activo)
    - active=False: Proyecto bloqueado (inactivo)
    
    Args:
        project_id: ID del proyecto a modificar
        active: True para desbloquear, False para bloquear
        access_token: Token de acceso JWT
        session_token: Token de sesión
    
    Returns:
        Diccionario con project_id, success y updated
    
    Raises:
        Exception: Si hay error en la petición
    """
    url = f"{_get_middleware_base_url()}/projects/{project_id}"
    body = json.dumps({"active": active}).encode("utf-8")
    
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    action = "desbloqueando" if active else "bloqueando"
    logger.info(f"Enviando PATCH a {url} - {action} proyecto")
    
    request = urllib.request.Request(url, data=body, headers=request_headers, method="PATCH")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            action_done = "desbloqueado" if active else "bloqueado"
            logger.info(f"Proyecto {project_id} {action_done}: {result}")
            return result
    except urllib.error.HTTPError as exc:
        error_msg = f"Error HTTP {exc.code}"
        try:
            error_payload = exc.read().decode("utf-8")
            error_msg = f"{error_msg}: {error_payload}"
        except Exception:
            pass
        logger.error(f"Error actualizando proyecto: {error_msg}")
        raise Exception(error_msg) from exc
    except urllib.error.URLError as exc:
        logger.error(f"No se pudo contactar con el middleware: {exc}")
        raise Exception(f"Error de conexión: {exc}") from exc


def update_project_existence(
    project_id: int,
    existe: bool,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """
    Actualiza la existencia lógica de un proyecto.
    
    IMPORTANTE: Este es un borrado/recuperación LÓGICO, no físico.
    - existe=True: Proyecto existe (recuperado)
    - existe=False: Proyecto borrado lógicamente
    
    Args:
        project_id: ID del proyecto a modificar
        existe: True para recuperar, False para borrar lógicamente
        access_token: Token de acceso JWT
        session_token: Token de sesión
    
    Returns:
        Diccionario con project_id, success y updated
    
    Raises:
        Exception: Si hay error en la petición
    """
    url = f"{_get_middleware_base_url()}/projects/{project_id}"
    body = json.dumps({"existe": existe}).encode("utf-8")
    
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    action = "recuperando" if existe else "borrando lógicamente"
    logger.info(f"Enviando PATCH a {url} - {action} proyecto")
    
    request = urllib.request.Request(url, data=body, headers=request_headers, method="PATCH")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            action_done = "recuperado" if existe else "borrado lógicamente"
            logger.info(f"Proyecto {project_id} {action_done}: {result}")
            return result
    except urllib.error.HTTPError as exc:
        error_msg = f"Error HTTP {exc.code}"
        try:
            error_payload = exc.read().decode("utf-8")
            error_msg = f"{error_msg}: {error_payload}"
        except Exception:
            pass
        logger.error(f"Error actualizando existencia proyecto: {error_msg}")
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
# TICKETS DE SOPORTE
# ============================================================================


def get_organization_tickets(
    organization_id: int,
    access_token: str | None = None,
    session_token: str | None = None,
) -> list[dict[str, Any]]:
    """
    Obtiene los tickets de una organización.
    
    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        organization_id: ID de la organización
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        Lista de tickets
    """
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token
    
    response = _request_middleware(
        "GET", f"/tickets/organization/{organization_id}", headers=headers
    )
    
    if isinstance(response, dict) and "tickets" in response:
        return response.get("tickets", [])
    if isinstance(response, list):
        return response
    return []


def update_ticket_status(
    ticket_id: int,
    estado: str | None = None,
    prioridad: str | None = None,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """
    Actualiza el estado/prioridad de un ticket.
    
    Args:
        ticket_id: ID del ticket
        estado: Nuevo estado (abierto/en_espera/resuelto/cerrado)
        prioridad: Nueva prioridad (baja/media/alta/urgente)
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        {"success": True, "updated": bool, "ticket_id": int}
    """
    url = f"{_get_middleware_base_url()}/tickets/{ticket_id}"
    
    payload: dict[str, Any] = {}
    if estado:
        payload["estado"] = estado
    if prioridad:
        payload["prioridad"] = prioridad
    
    body = json.dumps(payload).encode("utf-8")
    
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    logger.info(f"Enviando PATCH a {url}")
    
    request = urllib.request.Request(url, data=body, headers=request_headers, method="PATCH")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            logger.info(f"Ticket {ticket_id} actualizado: {result}")
            return result
    except urllib.error.HTTPError as exc:
        error_msg = f"Error HTTP {exc.code}"
        try:
            error_payload = exc.read().decode("utf-8")
            error_msg = f"{error_msg}: {error_payload}"
        except Exception:
            pass
        logger.error(f"Error actualizando ticket: {error_msg}")
        raise Exception(error_msg) from exc
    except urllib.error.URLError as exc:
        logger.error(f"No se pudo contactar con el middleware: {exc}")
        raise Exception(f"Error de conexión: {exc}") from exc


def add_ticket_response(
    ticket_id: int,
    respuesta: str,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """
    Añade respuesta a un ticket.
    
    Args:
        ticket_id: ID del ticket
        respuesta: Texto de la respuesta
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        {"success": True, "updated": bool, "ticket_id": int}
    """
    url = f"{_get_middleware_base_url()}/tickets/{ticket_id}/respuesta"
    body = json.dumps({"respuesta": respuesta}).encode("utf-8")
    
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    logger.info(f"Enviando POST a {url}")
    
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            logger.info(f"Respuesta añadida a ticket {ticket_id}: {result}")
            return result
    except urllib.error.HTTPError as exc:
        error_msg = f"Error HTTP {exc.code}"
        try:
            error_payload = exc.read().decode("utf-8")
            error_msg = f"{error_msg}: {error_payload}"
        except Exception:
            pass
        logger.error(f"Error añadiendo respuesta: {error_msg}")
        raise Exception(error_msg) from exc
    except urllib.error.URLError as exc:
        logger.error(f"No se pudo contactar con el middleware: {exc}")
        raise Exception(f"Error de conexión: {exc}") from exc


# ============================================================================
# GESTIÓN DE TECNOLOGÍAS
# ============================================================================


def get_tecnologias(
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene la lista de tecnologías disponibles.
    
    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    
    Returns:
        {"tecnologias": [...], "total": int}
    """
    url = f"{_get_middleware_base_url()}/tecnologias"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    request = urllib.request.Request(url, headers=request_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        logger.error(f"Error obteniendo tecnologías: {exc}")
        return {"tecnologias": [], "total": 0}


def get_proyecto_tecnologia(
    project_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene la tecnología asignada a un proyecto.
    
    Returns:
        {"success": True, "asignacion": {...} o None}
    """
    url = f"{_get_middleware_base_url()}/proyectos/{project_id}/tecnologia"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    request = urllib.request.Request(url, headers=request_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        logger.error(f"Error obteniendo tecnología de proyecto: {exc}")
        return {"success": False, "asignacion": None}


def asignar_tecnologia(
    project_id: int,
    id_tecnologia: int,
    coste_base: str = "17% sobre base",
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Asigna una tecnología a un proyecto (primera asignación).
    
    Returns:
        {"success": True, "asignacion": {...}}
    """
    url = f"{_get_middleware_base_url()}/proyectos/{project_id}/tecnologia"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    payload = json.dumps({
        "id_tecnologia": id_tecnologia,
        "coste_base": coste_base,
    }).encode("utf-8")
    
    request = urllib.request.Request(url, data=payload, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_msg = f"Error HTTP {exc.code}"
        try:
            error_payload = exc.read().decode("utf-8")
            error_msg = f"{error_msg}: {error_payload}"
        except Exception:
            pass
        logger.error(f"Error asignando tecnología: {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as exc:
        logger.error(f"Error asignando tecnología: {exc}")
        return {"success": False, "error": str(exc)}


def actualizar_tecnologia(
    project_id: int,
    id_tecnologia: int,
    coste_base: str = "17% sobre base",
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Actualiza la tecnología de un proyecto (solo Backoffice).
    
    Returns:
        {"success": True, "asignacion": {...}}
    """
    url = f"{_get_middleware_base_url()}/proyectos/{project_id}/tecnologia"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    payload = json.dumps({
        "id_tecnologia": id_tecnologia,
        "coste_base": coste_base,
    }).encode("utf-8")
    
    request = urllib.request.Request(url, data=payload, headers=request_headers, method="PATCH")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_msg = f"Error HTTP {exc.code}"
        try:
            error_payload = exc.read().decode("utf-8")
            error_msg = f"{error_msg}: {error_payload}"
        except Exception:
            pass
        logger.error(f"Error actualizando tecnología: {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as exc:
        logger.error(f"Error actualizando tecnología: {exc}")
        return {"success": False, "error": str(exc)}


def get_tecnologias_asignadas_org(
    organization_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene todas las tecnologías asignadas a proyectos de una organización.
    
    Args:
        organization_id: ID de la organización
        access_token: Token de acceso JWT
        session_token: Token de sesión
        
    Returns:
        {"asignaciones": [...], "total": int}
        Cada asignación tiene: project_id, project_name, tecnologia_id, tecnologia_name
    """
    url = f"{_get_middleware_base_url()}/organizaciones/{organization_id}/tecnologias-asignadas"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    request = urllib.request.Request(url, headers=request_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_msg = f"Error HTTP desde middleware: {exc.code}"
        try:
            error_payload = exc.read().decode("utf-8")
            error_msg = f"{error_msg} - {error_payload}"
        except Exception:
            pass
        print(error_msg)
        return {"asignaciones": [], "total": 0}
    except Exception as exc:
        print(f"Error consultando tecnologías asignadas: {exc}")
        return {"asignaciones": [], "total": 0}


# ============================================================================
# GESTIÓN DE VERSIONES
# ============================================================================


def get_project_versions(
    project_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene todas las versiones de un proyecto.
    
    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        project_id: ID del proyecto
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {"versiones": [{"id_version": int, "id_proyecto": int, 
                        "id_organizacion": int, "version_folder": str}], 
         "total": int}
    """
    url = f"{_get_middleware_base_url()}/proyectos/{project_id}/versiones"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    request = urllib.request.Request(url, headers=request_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_msg = f"Error HTTP desde middleware: {exc.code}"
        try:
            error_payload = exc.read().decode("utf-8")
            error_msg = f"{error_msg} - {error_payload}"
        except Exception:
            pass
        print(error_msg)
        return {"versiones": [], "total": 0}
    except Exception as exc:
        print(f"Error consultando versiones: {exc}")
        return {"versiones": [], "total": 0}


def create_project_version(
    project_id: int,
    organization_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Crea una nueva versión para un proyecto.
    
    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        project_id: ID del proyecto
        organization_id: ID de la organización
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {"success": bool, "version": VersionDto | None, "mensaje": str | None}
    """
    url = f"{_get_middleware_base_url()}/proyectos/{project_id}/versiones"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    payload = json.dumps({
        "id_proyecto": project_id,
        "id_organizacion": organization_id,
    }).encode("utf-8")
    
    request = urllib.request.Request(url, data=payload, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_msg = f"Error HTTP desde middleware: {exc.code}"
        try:
            error_payload = exc.read().decode("utf-8")
            error_msg = f"{error_msg} - {error_payload}"
        except Exception:
            pass
        print(error_msg)
        return {"success": False, "mensaje": error_msg}
    except Exception as exc:
        print(f"Error creando versión: {exc}")
        return {"success": False, "mensaje": str(exc)}


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
    
    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        project_id: ID del proyecto
        version_id: ID de la versión
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {"success": bool, "state": VersionStateDto | None, "mensaje": str | None}
    """
    url = f"{_get_middleware_base_url()}/proyectos/{project_id}/versiones/{version_id}/estado"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    request = urllib.request.Request(url, headers=request_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error HTTP: {exc.code} al obtener estado versión")
        print(f"  URL: {url}")
        print(f"  Respuesta: {error_body}")
        return {"success": False, "mensaje": f"Error HTTP: {exc.code}"}
    except Exception as exc:
        print(f"Error obteniendo estado versión: {exc}")
        return {"success": False, "mensaje": str(exc)}


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
    
    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    
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
        {"success": bool, "state": VersionStateDto | None, "mensaje": str | None}
    """
    url = f"{_get_middleware_base_url()}/proyectos/{project_id}/versiones/{version_id}/estado"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    payload_dict = {}
    if state is not None:
        payload_dict["state"] = state
    if protected is not None:
        payload_dict["protected"] = protected
    if size_bytes is not None:
        payload_dict["size_bytes"] = size_bytes
    if final_c is not None:
        payload_dict["final_c"] = final_c
    if final_i is not None:
        payload_dict["final_i"] = final_i
    if updated_by_user_id is not None:
        payload_dict["updated_by_user_id"] = updated_by_user_id
    
    payload = json.dumps(payload_dict).encode("utf-8")
    
    request = urllib.request.Request(url, data=payload, headers=request_headers, method="PATCH")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error HTTP: {exc.code} al actualizar estado versión")
        print(f"  URL: {url}")
        print(f"  Payload: {payload.decode('utf-8')}")
        print(f"  Respuesta: {error_body}")
        return {"success": False, "mensaje": f"Error HTTP: {exc.code}"}
    except Exception as exc:
        print(f"Error actualizando estado versión: {exc}")
        return {"success": False, "mensaje": str(exc)}


def get_version_events(
    project_id: int,
    version_id: int,
    limit: int = 50,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Obtiene el historial de eventos de una versión.
    
    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        project_id: ID del proyecto
        version_id: ID de la versión
        limit: Número máximo de eventos a retornar
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {"success": bool, "events": list[VersionEventDto], "total": int, "mensaje": str | None}
    """
    url = f"{_get_middleware_base_url()}/proyectos/{project_id}/versiones/{version_id}/eventos?limit={limit}"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    request = urllib.request.Request(url, headers=request_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error HTTP: {exc.code} al obtener eventos versión")
        print(f"  URL: {url}")
        print(f"  Respuesta: {error_body}")
        return {"success": False, "events": [], "total": 0, "mensaje": f"Error HTTP: {exc.code}"}
    except Exception as exc:
        print(f"Error obteniendo eventos versión: {exc}")
        return {"success": False, "events": [], "total": 0, "mensaje": str(exc)}


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
    
    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB + fmanagement
    
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
        {"success": bool, "version": VersionDto | None, "state": VersionStateDto | None, "mensaje": str | None}
    """
    url = f"{_get_middleware_base_url()}/proyectos/{project_id}/versiones/crear-completa"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    payload_dict = {
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
        payload_dict["descripcion"] = description
    if clone_from_version_id is not None:
        payload_dict["clone_from_version_id"] = clone_from_version_id
    
    payload = json.dumps(payload_dict).encode("utf-8")
    
    request = urllib.request.Request(url, data=payload, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:  # Más tiempo por operación compleja
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error HTTP: {exc.code} al crear versión completa")
        print(f"  URL: {url}")
        print(f"  Payload: {payload.decode('utf-8')}")
        print(f"  Respuesta: {error_body}")
        return {"success": False, "mensaje": f"Error HTTP: {exc.code}"}
    except Exception as exc:
        print(f"Error creando versión completa: {exc}")
        return {"success": False, "mensaje": str(exc)}


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
    
    Flujo: Backoffice → Middleware → Broker → Backend Core → fmanagement
    
    Args:
        org_folder: Carpeta de organización (ej: "ORG00001")
        prj_folder: Carpeta de proyecto (ej: "PRJ0001")
        version_folder: Carpeta de versión (ej: "V001")
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {"success": bool, "items": list[FmanagementItemDto], "mensaje": str | None}
    """
    url = f"{_get_middleware_base_url()}/fmanagement/list"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    payload = json.dumps({
        "org_folder": org_folder,
        "prj_folder": prj_folder,
        "version_folder": version_folder,
    }).encode("utf-8")
    
    request = urllib.request.Request(url, data=payload, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error HTTP: {exc.code} al listar fmanagement")
        print(f"  URL: {url}")
        print(f"  Payload: {payload.decode('utf-8')}")
        print(f"  Respuesta: {error_body}")
        return {"success": False, "items": [], "mensaje": f"Error HTTP: {exc.code}"}
    except Exception as exc:
        print(f"Error listando fmanagement: {exc}")
        return {"success": False, "items": [], "mensaje": str(exc)}


def fmanagement_list_for_explorador(
    org_id: int,
    project_id: int,
    version_name: str,
    org_folder: str = "",
    prj_folder: str = "",
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Lista estructura de archivos y la convierte al formato del componente explorador.

    Esta función combina fmanagement_list con el adaptador para retornar
    directamente el formato jerárquico que espera el explorador.

    Flujo: Backoffice → Middleware → Broker → Backend Core → fmanagement → Adaptador

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
        org_folder = f"ORG{str(org_id).zfill(5)}"
    if not prj_folder:
        prj_folder = f"PRJ{str(project_id).zfill(5)}"

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
    for item in items:
        if item.get("is_dir", True):
            # Es una carpeta, sumar recursivamente
            total_size += _calculate_structure_size(item.get("items", []))
        else:
            # Es un archivo, sumar su tamaño
            total_size += item.get("size_bytes", 0)
    return total_size


def fmanagement_list_all_project_versions(
    org_id: int,
    project_id: int,
    org_folder: str = "",
    prj_folder: str = "",
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Lista todas las versiones de un proyecto con sus estructuras de archivos.

    Esta función obtiene todas las versiones del proyecto y carga el contenido
    de cada una usando fmanagement, construyendo una estructura jerárquica
    completa para el explorador.

    Flujo: Backoffice → Middleware → Backend Core → MariaDB (versiones)
           Backoffice → Middleware → Broker → Backend Core → fmanagement (contenido)

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
        org_folder = f"ORG{str(org_id).zfill(5)}"
    if not prj_folder:
        prj_folder = f"PRJ{str(project_id).zfill(5)}"

    # 1. Obtener lista de versiones del proyecto
    versions_response = get_project_versions(
        project_id=project_id,
        access_token=access_token,
        session_token=session_token,
    )

    versiones = versions_response.get("versiones", [])

    if not versiones:
        logger.warning(f"No se encontraron versiones para el proyecto {project_id}")
        return {
            "status": "success",
            "path": f"/data/files/external/{org_folder}/{prj_folder}",
            "items": [{
                "name": prj_folder,
                "is_dir": True,
                "size_bytes": 0,
                "items": []
            }]
        }

    # 2. Para cada versión, obtener su contenido desde fmanagement
    versions_data = []

    for version_info in versiones:
        version_id = version_info.get("id_version", 0)
        version_name = f"v{str(version_id).zfill(3)}"  # v001, v002, etc.

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
        if explorador_data.get("status") == "success" and explorador_data.get("items"):
            project_item = explorador_data["items"][0]
            version_items = project_item.get("items", [])

            for version_item in version_items:
                version_name = version_item.get("name", "")  # ej: "v001"
                if version_name.startswith("v"):
                    try:
                        version_id = int(version_name[1:])  # Convertir "v001" a 1

                        # Calcular tamaño total de esta versión
                        version_size = _calculate_structure_size(version_item.get("items", []))

                        # Actualizar size_bytes en la BD
                        update_result = update_version_state(
                            project_id=project_id,
                            version_id=version_id,
                            size_bytes=version_size,
                            access_token=access_token,
                            session_token=session_token,
                        )

                        if update_result.get("success"):
                            logger.info(f"Tamaño actualizado para {version_name}: {version_size} bytes")
                        else:
                            logger.warning(f"No se pudo actualizar tamaño para {version_name}")
                    except (ValueError, Exception) as e:
                        logger.error(f"Error procesando tamaño de {version_name}: {e}")

        logger.info(f"Estructura cargada: proyecto {prj_folder} con {len(versiones)} versiones")
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

    Operaciones soportadas:
    - create_folder
    - rename_folder
    - delete_folder
    - create_file
    - rename_file
    - delete_file
    - download_file

    Flujo: Backoffice → Middleware → Broker → Backend Core → fmanagement

    Args:
        operation: Nombre de la operación
        params: Parámetros específicos de la operación
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT
        
    Returns:
        {"success": bool, "data": dict | None, "mensaje": str | None}
    """
    url = f"{_get_middleware_base_url()}/fmanagement/operation"
    request_headers = {
        "Content-Type": "application/json",
        "X-Client-App": "backoffice",
    }
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        request_headers["X-Session-Token"] = session_token
    
    payload = json.dumps({
        "operation": operation,
        "params": params,
    }).encode("utf-8")
    
    request = urllib.request.Request(url, data=payload, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error HTTP: {exc.code} en operación fmanagement")
        print(f"  URL: {url}")
        print(f"  Operation: {operation}")
        print(f"  Params: {params}")
        print(f"  Respuesta: {error_body}")
        return {"success": False, "mensaje": f"Error HTTP: {exc.code}"}
    except Exception as exc:
        print(f"Error en operación fmanagement: {exc}")
        return {"success": False, "mensaje": str(exc)}


# =============================================================================
# FMANAGEMENT CRUD OPERATIONS (crear, renombrar, eliminar, propiedades)
# =============================================================================


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
        Dict con success, token, fmanagement_url, expires_in, expires_at
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
        Dict con success, token, fmanagement_url, download_url
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

    org_folder = f"ORG{org_id:05d}"
    prj_folder = f"PRJ{project_id:05d}"
    version_folder = f"v{version_id:03d}"

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

    org_folder = f"ORG{org_id:05d}"
    prj_folder = f"PRJ{project_id:05d}"
    version_folder = f"v{version_id:03d}"

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

    org_folder = f"ORG{org_id:05d}"
    prj_folder = f"PRJ{project_id:05d}"
    version_folder = f"v{version_id:03d}"

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

    org_folder = f"ORG{org_id:05d}"
    prj_folder = f"PRJ{project_id:05d}"
    version_folder = f"v{version_id:03d}"

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

    org_folder = f"ORG{org_id:05d}"
    prj_folder = f"PRJ{project_id:05d}"
    version_folder = f"v{version_id:03d}"

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

    org_folder = f"ORG{org_id:05d}"
    prj_folder = f"PRJ{project_id:05d}"
    version_folder = f"v{version_id:03d}"

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


# =============================================================================
# OLLAMA AI ASSISTANT API FUNCTIONS
# =============================================================================

def check_ollama_health(access_token: str, session_token: str) -> dict:
    """
    Verifica el estado de Ollama en el trainer.

    Flujo: Backoffice → Middleware → Broker → Trainer
    """
    middleware_base_url = os.environ.get("MIDDLEWARE_BASE_URL", "http://localhost:8007")
    url = f"{middleware_base_url}/trainer/ollama/health"

    request_headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Session-Token": session_token,
        "X-Client-App": "backoffice",
        "Content-Type": "application/json",
    }

    request = urllib.request.Request(url, headers=request_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error checking Ollama health: {exc.code}")
        print(f"  Response: {error_body}")
        return {"status": "error", "detail": error_body}
    except Exception as exc:
        print(f"Error checking Ollama health: {exc}")
        return {"status": "error", "detail": str(exc)}


def get_ollama_models(access_token: str, session_token: str) -> dict:
    """
    Obtiene la lista de modelos disponibles en Ollama.

    Flujo: Backoffice → Middleware → Broker → Trainer
    """
    middleware_base_url = os.environ.get("MIDDLEWARE_BASE_URL", "http://localhost:8007")
    url = f"{middleware_base_url}/trainer/ollama/models"

    request_headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Session-Token": session_token,
        "X-Client-App": "backoffice",
        "Content-Type": "application/json",
    }

    request = urllib.request.Request(url, headers=request_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error getting Ollama models: {exc.code}")
        print(f"  Response: {error_body}")
        return {"models": []}
    except Exception as exc:
        print(f"Error getting Ollama models: {exc}")
        return {"models": []}


def generate_with_ollama(
    model: str,
    prompt: str,
    access_token: str,
    session_token: str,
    temperature: float = 0.7,
    num_predict: int = 500,
) -> dict:
    """
    Genera texto con Ollama usando el endpoint generate.

    Flujo: Backoffice → Middleware → Broker → Trainer
    """
    middleware_base_url = os.environ.get("MIDDLEWARE_BASE_URL", "http://localhost:8007")
    url = f"{middleware_base_url}/trainer/ollama/generate"

    request_headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Session-Token": session_token,
        "X-Client-App": "backoffice",
        "Content-Type": "application/json",
    }

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        }
    }).encode("utf-8")

    request = urllib.request.Request(url, data=payload, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=1800) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error generating with Ollama: {exc.code}")
        print(f"  Response: {error_body}")
        return {"response": "", "error": error_body}
    except Exception as exc:
        print(f"Error generating with Ollama: {exc}")
        return {"response": "", "error": str(exc)}


def chat_with_ollama(
    model: str,
    message: str,
    access_token: str,
    session_token: str,
    temperature: float = 0.7,
) -> dict:
    """
    Chatea con Ollama usando el endpoint chat (fallback para generate).

    Flujo: Backoffice → Middleware → Broker → Trainer
    """
    middleware_base_url = os.environ.get("MIDDLEWARE_BASE_URL", "http://localhost:8007")
    url = f"{middleware_base_url}/trainer/ollama/chat"

    request_headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Session-Token": session_token,
        "X-Client-App": "backoffice",
        "Content-Type": "application/json",
    }

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": False,
        "options": {
            "temperature": temperature,
        }
    }).encode("utf-8")

    request = urllib.request.Request(url, data=payload, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=1800) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error chatting with Ollama: {exc.code}")
        print(f"  Response: {error_body}")
        return {"message": {"content": ""}, "error": error_body}
    except Exception as exc:
        print(f"Error chatting with Ollama: {exc}")
        return {"message": {"content": ""}, "error": str(exc)}


# ============================================================================
# ANÁLISIS DE DOCUMENTACIÓN - Envío al Trainer
# ============================================================================


def send_documentacion_to_trainer(
    payload: dict[str, Any],
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Envía solicitud de análisis de documentación al trainer.

    Flujo: Backoffice → Middleware → Broker → Trainer

    Args:
        payload: Datos del job con prompt_final, ids de org/prj/ver, etc.
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        Respuesta ACK del trainer con success, message y received_at
    """
    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "POST",
        "/training/documentacion",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def send_metadatos_to_trainer(
    payload: dict[str, Any],
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Envía solicitud de análisis de metadatos al trainer.

    Flujo: Backoffice → Middleware → Broker → Trainer

    Args:
        payload: Datos del job con prompt_final, ids de org/prj/ver, etc.
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        Respuesta ACK del trainer con success, message y received_at
    """
    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "POST",
        "/training/metadatos",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


# ============================================================================
# ASSIGNMENTS MANAGER - Gestor de asignaciones (SuperAdmin)
# ============================================================================

def get_all_organizations(
    access_token: str | None = None,
    session_token: str | None = None,
) -> list[dict[str, Any]]:
    """Gets all organizations."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware("GET", "/assignments/organizations", headers=headers)
    return response if isinstance(response, list) else []


def get_internal_users(
    access_token: str | None = None,
    session_token: str | None = None,
) -> list[dict[str, Any]]:
    """Gets internal users for assignment selectors."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware("GET", "/assignments/internal-users", headers=headers)
    return response if isinstance(response, list) else []


def get_roles(
    access_token: str | None = None,
    session_token: str | None = None,
) -> list[dict[str, Any]]:
    """Gets roles for assignment selectors."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware("GET", "/assignments/roles", headers=headers)
    return response if isinstance(response, list) else []


def get_organization_assignments(
    organization_id: int,
    access_token: str | None = None,
    session_token: str | None = None,
) -> list[dict[str, Any]]:
    """Gets assignments for an organization."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "GET",
        f"/assignments/organizations/{organization_id}",
        headers=headers,
    )
    return response if isinstance(response, list) else []


def create_organization_assignment(
    user_id: int,
    organization_id: int,
    role_id: int,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Creates organization assignment."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    payload = {
        "user_id": user_id,
        "organization_id": organization_id,
        "role_id": role_id,
    }
    response = _request_middleware(
        "POST",
        "/assignments/organizations",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def update_organization_assignment(
    assignment_id: int,
    active: bool,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Updates organization assignment active status."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "PATCH",
        f"/assignments/organizations/{assignment_id}?active={active}",
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def delete_organization_assignment(
    assignment_id: int,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Deletes organization assignment permanently."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "DELETE",
        f"/assignments/organizations/{assignment_id}",
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def validate_org_prerequisite(
    user_id: int,
    organization_id: int,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Validates if user has active org role."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "GET",
        f"/assignments/validate-org-prerequisite?user_id={user_id}&organization_id={organization_id}",
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def get_project_assignments(
    project_id: int,
    access_token: str | None = None,
    session_token: str | None = None,
) -> list[dict[str, Any]]:
    """Gets assignments for a project."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "GET",
        f"/assignments/projects/{project_id}",
        headers=headers,
    )
    return response if isinstance(response, list) else []


def create_project_assignment(
    user_id: int,
    organization_id: int,
    project_id: int,
    role_id: int,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Creates project assignment."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    payload = {
        "user_id": user_id,
        "organization_id": organization_id,
        "project_id": project_id,
        "role_id": role_id,
    }
    response = _request_middleware(
        "POST",
        "/assignments/projects",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def update_project_assignment(
    assignment_id: int,
    active: bool,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Updates project assignment active status."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "PATCH",
        f"/assignments/projects/{assignment_id}?active={active}",
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def delete_project_assignment(
    assignment_id: int,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Deletes project assignment permanently."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "DELETE",
        f"/assignments/projects/{assignment_id}",
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


# ============================================================================
# PROMPTS MANAGEMENT - Gestión de Prompts (SuperAdmin)
# ============================================================================

def get_prompts(
    category: str,
    access_token: str | None = None,
    session_token: str | None = None,
) -> list[dict[str, Any]]:
    """Gets all prompts for a category."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "GET",
        f"/prompts/{category}",
        headers=headers,
    )
    return response if isinstance(response, list) else []


def get_prompt(
    category: str,
    id_prompt: int,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Gets a specific prompt by ID."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "GET",
        f"/prompts/{category}/{id_prompt}",
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def create_prompt(
    category: str,
    name: str,
    description: str | None,
    prompt: str,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Creates a new prompt."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    payload = {
        "name": name,
        "description": description,
        "prompt": prompt,
    }
    response = _request_middleware(
        "POST",
        f"/prompts/{category}",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def update_prompt(
    category: str,
    id_prompt: int,
    name: str,
    description: str | None,
    prompt: str,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Updates an existing prompt."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    payload = {
        "name": name,
        "description": description,
        "prompt": prompt,
    }
    response = _request_middleware(
        "PUT",
        f"/prompts/{category}/{id_prompt}",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def toggle_prompt(
    category: str,
    id_prompt: int,
    active: bool,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Toggles prompt active status."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    payload = {"active": active}
    response = _request_middleware(
        "PATCH",
        f"/prompts/{category}/{id_prompt}/toggle",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


# ============================================================================
# PROJECT VERSION STATES - Estado de Proyectos
# ============================================================================


def get_project_version_state_by_id(
    state_id: int,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Obtiene estado de versión por ID."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "GET",
        f"/project-version-states/{state_id}",
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def update_proposal_phase(
    state_id: int,
    aceptacion_cliente: bool,
    aceptacion_interna: bool,
    access_token: str | None = None,
    session_token: str | None = None,
    revision_interna: bool | None = None,
    propuesta_mejoras: bool | None = None,
) -> dict[str, Any]:
    """Actualiza fase de propuesta (aceptaciones)."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    payload = {
        "aceptacion_cliente": aceptacion_cliente,
        "aceptacion_interna": aceptacion_interna,
    }

    if revision_interna is not None:
        payload["revision_interna"] = revision_interna
    if propuesta_mejoras is not None:
        payload["propuesta_mejoras"] = propuesta_mejoras

    response = _request_middleware(
        "PATCH",
        f"/project-version-states/{state_id}/proposal",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def update_training_phase(
    state_id: int,
    completado: bool,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Actualiza fase de entrenamiento."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    payload = {"completado": completado}
    response = _request_middleware(
        "PATCH",
        f"/project-version-states/{state_id}/training",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def update_evaluation_phase(
    state_id: int,
    evaluacion: bool,
    reentrenamiento: bool,
    optimizacion: bool,
    calidad_aprobada: bool,
    access_token: str | None = None,
    session_token: str | None = None,
    evaluacion_entrenamiento: bool | None = None,
) -> dict[str, Any]:
    """Actualiza fase de evaluación."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    payload = {
        "evaluacion": evaluacion,
        "reentrenamiento": reentrenamiento,
        "optimizacion": optimizacion,
        "calidad_aprobada": calidad_aprobada,
    }

    if evaluacion_entrenamiento is not None:
        payload["evaluacion_entrenamiento"] = evaluacion_entrenamiento

    response = _request_middleware(
        "PATCH",
        f"/project-version-states/{state_id}/evaluation",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def update_generation_phase(
    state_id: int,
    generacion_completada: bool | None = None,
    access_token: str | None = None,
    session_token: str | None = None,
    generacion_solicitada: bool | None = None,
) -> dict[str, Any]:
    """Actualiza fase de generación."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    payload = {}

    if generacion_completada is not None:
        payload["generacion_completada"] = generacion_completada

    if generacion_solicitada is not None:
        payload["generacion_solicitada"] = generacion_solicitada

    response = _request_middleware(
        "PATCH",
        f"/project-version-states/{state_id}/generation",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def update_notification_phase(
    state_id: int,
    notificacion_enviada: bool,
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Actualiza fase de notificación."""
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    payload = {"notificacion_enviada": notificacion_enviada}
    response = _request_middleware(
        "PATCH",
        f"/project-version-states/{state_id}/notification",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def get_pending_training_versions(
    access_token: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Obtiene versiones con entrenamiento inicial solicitado.

    Returns:
        {"versions": [...], "total": int}
    """
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "GET",
        "/training/pending-versions",
        headers=headers,
    )
    return response if isinstance(response, dict) else {"versions": [], "total": 0}


def get_training_params(
    org_id: int,
    project_id: int,
    version_id: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Obtiene parámetros de entrenamiento (defaults o último job).

    Endpoint inteligente que devuelve los parámetros por defecto si es
    primer entrenamiento, o los del último job si ya hubo entrenamientos.
    Incluye flags es_primer_entrenamiento/es_reentrenamiento y lista de
    modelos disponibles.

    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB

    Args:
        org_id: ID de la organización.
        project_id: ID del proyecto.
        version_id: ID de la versión.
        access_token: Token de acceso JWT.
        session_token: Token de sesión JWT.

    Returns:
        Diccionario con parámetros, flags y modelos disponibles.
    """
    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "GET",
        f"/training/params/{org_id}/{project_id}/{version_id}",
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def send_entrenamiento_to_trainer(
    payload: dict[str, Any],
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Envía solicitud de entrenamiento inicial al trainer.

    Flujo: Backoffice → Middleware → Broker → Trainer

    Args:
        payload: Datos con ids de org/prj/ver, pat_version y parámetros.
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        Respuesta ACK del trainer con success, message y received_at
    """
    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    print(f"[BACKOFFICE API_CLIENT] ===== ENVIANDO A MIDDLEWARE =====")
    print(f"[BACKOFFICE API_CLIENT] Payload: {payload}")
    print(f"[BACKOFFICE API_CLIENT] Headers: {headers}")

    response = _request_middleware(
        "POST",
        "/training/entrenamientos",
        payload=payload,
        headers=headers,
    )

    print(f"[BACKOFFICE API_CLIENT] ===== RESPUESTA DEL MIDDLEWARE =====")
    print(f"[BACKOFFICE API_CLIENT] Response type: {type(response)}")
    print(f"[BACKOFFICE API_CLIENT] Response: {response}")
    if isinstance(response, dict):
        print(f"[BACKOFFICE API_CLIENT] id_entrenamiento: {response.get('id_entrenamiento', 'NO EXISTE')}")
        print(f"[BACKOFFICE API_CLIENT] collection_name: {response.get('collection_name', 'NO EXISTE')}")
        print(f"[BACKOFFICE API_CLIENT] numero_secuencia: {response.get('numero_secuencia', 'NO EXISTE')}")
    print(f"[BACKOFFICE API_CLIENT] ===========================================")

    return response if isinstance(response, dict) else {}


def send_autonomous_training_to_trainer(
    payload: dict[str, Any],
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Envía solicitud de entrenamiento autónomo al trainer.

    El entrenamiento autónomo ejecuta las fases 6-9:
        Fase 6: Generación de Dataset desde ChromaDB
        Fases 7-8: Fine-tuning con LoRA (solo test/production)
        Fase 9: Exportación a GGUF y empaquetado (solo test/production)

    Flujo: Backoffice → Middleware → Broker → Trainer

    Args:
        payload: Datos con ids y collection_name del RAG previo.
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        Respuesta ACK del trainer con success, message, training_mode
    """
    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    print(f"[BACKOFFICE API_CLIENT] ===== ENVIANDO AUTONOMOUS TRAINING =====")
    print(f"[BACKOFFICE API_CLIENT] Payload: {payload}")
    print(f"[BACKOFFICE API_CLIENT] Headers: {headers}")

    response = _request_middleware(
        "POST",
        "/training/entrenamientos/autonomous",
        payload=payload,
        headers=headers,
    )

    print(f"[BACKOFFICE API_CLIENT] ===== RESPUESTA AUTONOMOUS =====")
    print(f"[BACKOFFICE API_CLIENT] Response: {response}")
    print(f"[BACKOFFICE API_CLIENT] ======================================")

    return response if isinstance(response, dict) else {}


def get_autonomous_training_progress(
    id_entrenamiento: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Consulta el progreso del entrenamiento autónomo (fases 6-9).

    Flujo: Backoffice → Middleware → Broker → Backend Core

    Args:
        id_entrenamiento: ID del entrenamiento autónomo a consultar.
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        Respuesta con success, data (subphases del entrenamiento autónomo)
    """
    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "GET",
        f"/training/entrenamientos/{id_entrenamiento}/autonomous/progress",
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def download_autonomous_package(
    id_entrenamiento: int,
    access_token: str = "",
    session_token: str = "",
) -> bytes | None:
    """Descarga el paquete ZIP del modelo autónomo generado.

    Flujo: Backoffice → Middleware → Broker → Trainer

    Args:
        id_entrenamiento: ID del entrenamiento autónomo
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        Bytes del archivo ZIP o None si hay error
    """
    import httpx

    middleware_url = _get_middleware_url()
    url = f"{middleware_url}/training/entrenamientos/{id_entrenamiento}/autonomous/package"

    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    print(f"[BACKOFFICE API_CLIENT] Descargando paquete desde: {url}")

    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.get(url, headers=headers)

            if response.status_code == 200:
                print(f"[BACKOFFICE API_CLIENT] Paquete descargado: {len(response.content)} bytes")
                return response.content
            else:
                print(f"[BACKOFFICE API_CLIENT] Error descargando: {response.status_code}")
                return None

    except Exception as exc:
        print(f"[BACKOFFICE API_CLIENT] Excepción descargando paquete: {exc}")
        return None


def list_autonomous_packages(
    id_organizacion: int | None = None,
    id_proyecto: int | None = None,
    id_version: int | None = None,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Lista los paquetes autónomos disponibles para descargar.

    Flujo: Backoffice → Middleware → Broker → Trainer

    Args:
        id_organizacion: Filtrar por organización (opcional)
        id_proyecto: Filtrar por proyecto (opcional)
        id_version: Filtrar por versión (opcional)
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        Diccionario con success y lista de paquetes
    """
    params = {}
    if id_organizacion is not None:
        params["id_organizacion"] = id_organizacion
    if id_proyecto is not None:
        params["id_proyecto"] = id_proyecto
    if id_version is not None:
        params["id_version"] = id_version

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    path = "/training/entrenamientos/autonomous/packages"
    if query_string:
        path += f"?{query_string}"

    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware("GET", path, headers=headers)
    return response if isinstance(response, dict) else {}


def cancel_entrenamiento_training(
    payload: dict[str, Any],
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Cancela un entrenamiento en progreso.

    Flujo: Backoffice → Middleware → Broker → Backend Core

    Args:
        payload: Datos con id_entrenamiento y motivo.
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        Respuesta con success y message
    """
    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "PATCH",
        "/training/entrenamientos/cancel",
        payload=payload,
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


def get_training_progress(
    id_entrenamiento: int,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Consulta el progreso actual de un entrenamiento.

    Flujo: Backoffice → Middleware → Backend Core

    Args:
        id_entrenamiento: ID del entrenamiento a consultar.
        access_token: Token de acceso JWT
        session_token: Token de sesión JWT

    Returns:
        Respuesta con success, data (phases y last_update)
    """
    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    response = _request_middleware(
        "GET",
        f"/training/entrenamientos/{id_entrenamiento}/progress",
        headers=headers,
    )
    return response if isinstance(response, dict) else {}


# ============================================================================
# FUNCIONES DE HEALTH CHECK PARA PÁGINA SISTEMA
# ============================================================================

def check_service_health(url: str, timeout: int = 5) -> dict:
    """
    Verifica si un servicio está disponible haciendo una petición HTTP simple.

    Args:
        url: URL del servicio a verificar
        timeout: Timeout en segundos

    Returns:
        Dict con status: "healthy" o "error"
    """
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status == 200:
                return {"status": "healthy"}
            else:
                return {"status": "error", "detail": f"HTTP {response.status}"}
    except urllib.error.HTTPError as exc:
        return {"status": "error", "detail": f"HTTP {exc.code}"}
    except urllib.error.URLError as exc:
        return {"status": "error", "detail": f"Connection error: {exc.reason}"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def check_frontend_health() -> dict:
    """Verifica el estado del servicio Frontend."""
    frontend_host = os.environ.get("FRONTEND_HOST", "localhost")
    frontend_port = os.environ.get("FRONTEND_PORT", "8005")
    try:
        request = urllib.request.Request(f"http://{frontend_host}:{frontend_port}/", method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return {"status": "healthy"}
    except urllib.error.HTTPError as exc:
        # 404 es OK para servicios Reflex, significa que están corriendo
        if exc.code == 404:
            return {"status": "healthy"}
        return {"status": "error", "detail": f"HTTP {exc.code}"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def check_backoffice_health() -> dict:
    """Verifica el estado del servicio Backoffice."""
    # El backoffice no puede verificarse a sí mismo via HTTP (causaría deadlock)
    # Si este código se está ejecutando, el backoffice está activo
    backoffice_host = os.environ.get("BACKOFFICE_HOST", "localhost")
    backoffice_port = os.environ.get("BACKOFFICE_PORT", "8006")

    import socket
    try:
        # Verificar si el puerto está abierto usando socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((backoffice_host, int(backoffice_port)))
        sock.close()

        if result == 0:
            return {"status": "healthy"}
        else:
            return {"status": "error", "detail": "Puerto no accesible"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def check_middleware_health() -> dict:
    """Verifica el estado del Middleware."""
    middleware_base_url = os.environ.get("MIDDLEWARE_BASE_URL", "http://localhost:8007")
    return check_service_health(f"{middleware_base_url}/docs")


def check_redis_health() -> dict:
    """Verifica el estado de Redis verificando si el backend está operativo."""
    # Redis no tiene endpoint directo, verificamos que el backend core esté funcionando
    # ya que el backend depende de Redis para funcionar
    core_backend_base_url = os.environ.get("CORE_BACKEND_BASE_URL", "http://localhost:8003")
    result = check_service_health(f"{core_backend_base_url}/docs")
    if result.get("status") == "healthy":
        return {"status": "healthy", "detail": "Backend Core operativo (usa Redis)"}
    return result


def check_sms_api_health() -> dict:
    """Verifica si la API de SMS (Infobip) es alcanzable."""
    sms_api_url = os.environ.get("SMS_API_URL", "")

    if not sms_api_url:
        return {"status": "error", "detail": "No configurado"}

    try:
        import ssl
        # Crear contexto SSL que no verifica certificados (necesario para algunos entornos)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Hacer petición HTTPS para verificar si la API es alcanzable
        # Infobip puede devolver 401/403 sin autenticación, pero eso significa que está alcanzable
        request = urllib.request.Request(sms_api_url, method="GET")
        with urllib.request.urlopen(request, timeout=5, context=ssl_context) as response:
            # Cualquier respuesta exitosa (2xx) es OK
            if 200 <= response.status < 300:
                return {"status": "healthy"}
            else:
                return {"status": "error", "detail": f"HTTP {response.status}"}
    except urllib.error.HTTPError as exc:
        # 401/403 son OK - significa que el servidor está alcanzable pero requiere autenticación
        if exc.code in [401, 403]:
            return {"status": "healthy", "detail": "Alcanzable (requiere auth)"}
        return {"status": "error", "detail": f"HTTP {exc.code}"}
    except urllib.error.URLError as exc:
        return {"status": "error", "detail": f"Connection error: {exc.reason}"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def check_broker_health() -> dict:
    """Verifica el estado del Broker."""
    broker_backend_base_url = os.environ.get("BROKER_BACKEND_BASE_URL", "http://localhost:8008")
    return check_service_health(f"{broker_backend_base_url}/docs")


def check_backend_core_health() -> dict:
    """Verifica el estado del Backend Core."""
    core_backend_base_url = os.environ.get("CORE_BACKEND_BASE_URL", "http://localhost:8003")
    return check_service_health(f"{core_backend_base_url}/docs")


def check_fmanagement_health() -> dict:
    """Verifica el estado de fmanagement."""
    # fmanagement es un servicio Go, verificamos que responda
    fmanagement_base_url = os.environ.get("FMANAGEMENT_BASE_URL", "http://localhost:1666")
    try:
        request = urllib.request.Request(f"{fmanagement_base_url}/", method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            # Cualquier respuesta (incluso 404) significa que está activo
            return {"status": "healthy"}
    except urllib.error.HTTPError as exc:
        # 404 es OK, significa que el servicio está corriendo
        if exc.code == 404:
            return {"status": "healthy"}
        return {"status": "error", "detail": f"HTTP {exc.code}"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def check_mariadb_health() -> dict:
    """Verifica el estado de MariaDB verificando si el backend está operativo."""
    # MariaDB no tiene endpoint directo, verificamos que el backend core esté funcionando
    # ya que el backend depende de MariaDB para funcionar
    core_backend_base_url = os.environ.get("CORE_BACKEND_BASE_URL", "http://localhost:8003")
    result = check_service_health(f"{core_backend_base_url}/docs")
    if result.get("status") == "healthy":
        return {"status": "healthy", "detail": "Backend Core operativo (usa MariaDB)"}
    return result


def check_trainer_health() -> dict:
    """Verifica el estado del Backend IA/Trainer."""
    trainer_base_url = os.environ.get("TRAINER_BASE_URL", "http://localhost:8004")
    return check_service_health(f"{trainer_base_url}/docs")


def check_chromadb_health() -> dict:
    """Verifica el estado de ChromaDB."""
    chroma_host = os.environ.get("CHROMA_HOST", "localhost")
    chroma_port = os.environ.get("CHROMA_PORT", "8100")
    return check_service_health(f"http://{chroma_host}:{chroma_port}/api/v2/heartbeat")

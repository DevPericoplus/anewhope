"""Adaptador para comunicación con la capa de dominio y middleware."""
import importlib.util
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

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
    """Obtiene la URL base del middleware desde el entorno."""

    return os.environ.get("MIDDLEWARE_BASE_URL", "http://localhost:8007").rstrip("/")


def _request_middleware(
    method: str, path: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None
) -> dict[str, Any]:
    """Realiza una petición HTTP al middleware y retorna JSON."""

    url = f"{_get_middleware_base_url()}{path}"
    body = None
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            error_payload = exc.read().decode("utf-8")
            logger.error(f"Error HTTP desde middleware: {exc.code} - {error_payload}")
        except Exception:
            logger.error(f"Error HTTP desde middleware: {exc.code}")
        return {}
    except urllib.error.URLError as exc:
        logger.error(f"No se pudo contactar con el middleware: {exc}")
        return {}
    except json.JSONDecodeError:
        logger.error("Respuesta del middleware no es JSON válido")
        return {}


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
    return _request_middleware("GET", "/permissions", headers=headers)


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


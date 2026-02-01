"""Adaptador para comunicación con la capa de dominio y middleware."""
import importlib.util
import json
import logging
import os
import sys
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


def _request_middleware(
    method: str, path: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None
) -> dict[str, Any]:
    """Realiza una petición HTTP al middleware y retorna JSON."""

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
    locked: bool | None = None,
    active: bool | None = None,
    id_flujo: int | None = None,
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    Actualiza el estado de un proyecto (bloqueo, activo, flujo).
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    El trigger en BD registra cambios automáticamente en tabla cambios:
    - Cambio de id_flujo → "Cambio de flujo"
    - Cambio de bloqueado → "Bloquear proyecto" / "Desbloquear proyecto"
    
    Args:
        project_id: ID del proyecto
        locked: Nuevo estado de bloqueo (opcional)
        active: Nuevo estado de activo (opcional)
        id_flujo: Nuevo paso del flujo (opcional)
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        {"success": True} o {"success": False, "error": str}
    """
    headers = _build_auth_headers(access_token, session_token)
    
    payload: dict[str, Any] = {}
    if locked is not None:
        payload["bloqueado"] = locked
    if active is not None:
        payload["active"] = active
    if id_flujo is not None:
        payload["id_flujo"] = id_flujo
    
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
    
    Args:
        access_token: Token JWT de acceso
        session_token: Token de sesión
    
    Returns:
        Diccionario con headers de autenticación
    """
    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token
    return headers

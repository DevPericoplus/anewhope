"""Cliente HTTP para LAIM Web → Middleware.

Todas las peticiones se envían al middleware (puerto 8007) siguiendo
el flujo arquitectónico obligatorio:

  LAIM Web (8009) → Middleware (8007) → Broker (8008) → Backend Core (8003)
                                                       → fmanagement (1666)

El único atajo permitido es fmanagement para operaciones de ficheros,
gestionado internamente por el backend core.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import time

import httpx

RENEWAL_THRESHOLD_SECONDS = 120

# Cargar env_settings para obtener URL del middleware
_env_settings_path = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "2_shared_application"
    / "config"
    / "env_settings.py"
)
_spec = importlib.util.spec_from_file_location("env_settings", _env_settings_path)
_env_settings = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("env_settings", _env_settings)
_spec.loader.exec_module(_env_settings)


def _get_middleware_base_url() -> str:
    """Obtiene la URL base del middleware desde env.yaml."""
    return _env_settings.get_env_value("middleware_base_url", "http://localhost:8007")


def _request_middleware(
    method: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
    access_token: str = "",
    session_token: str = "",
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Ejecuta una petición HTTP al middleware.

    Propaga headers de autenticación y trazabilidad.
    """
    base_url = _get_middleware_base_url()
    url = f"{base_url}{endpoint}"

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Client-App": "laimweb",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method=method,
                url=url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        try:
            body = exc.response.json()
            if isinstance(body, dict):
                detail = body.get("detail", body.get("error", detail))
        except ValueError:
            pass
        return {
            "success": False,
            "error": str(detail),
        }
    except httpx.RequestError as exc:
        return {"success": False, "error": f"Error de conexión: {exc}"}


def laim_login(username: str, password: str) -> dict[str, Any]:
    """Autentica un usuario a través del middleware.

    Flujo: LAIM Web → Middleware /laim/login → Broker → Backend Core
    """
    return _request_middleware(
        "POST",
        "/laim/login",
        payload={"username": username, "password": password},
    )


def laim_register(
    username: str,
    password: str,
    password_confirm: str,
    email: str,
    full_name: str,
    mobile: str | None = None,
    hcaptcha_token: str = "",
) -> dict[str, Any]:
    """Registro público de usuario LAIM."""
    payload: dict[str, Any] = {
        "username": username,
        "password": password,
        "password_confirm": password_confirm,
        "email": email,
        "full_name": full_name,
        "hcaptcha_token": hcaptcha_token,
    }
    if mobile:
        payload["mobile"] = mobile
    return _request_middleware("POST", "/laim/register", payload=payload)


def laim_logout(access_token: str, session_token: str) -> dict[str, Any]:
    """Cierra sesión LAIM."""
    return _request_middleware(
        "POST",
        "/laim/logout",
        access_token=access_token,
        session_token=session_token,
    )


def laim_refresh_token(session_token: str) -> dict[str, Any]:
    """Renueva tokens LAIM."""
    return _request_middleware(
        "POST",
        "/laim/refresh-token",
        session_token=session_token,
    )


def _should_renew_token(expires_at: int) -> bool:
    """Indica si un token debe renovarse antes de expirar."""
    if expires_at <= 0:
        return False
    return time.time() > (expires_at - RENEWAL_THRESHOLD_SECONDS)


def ensure_valid_tokens(
    access_token: str,
    session_token: str,
    access_expires_at: int,
    session_expires_at: int,
) -> dict[str, Any]:
    """Garantiza tokens válidos renovándolos si es necesario."""
    result: dict[str, Any] = {
        "renewed": False,
        "access_token": access_token,
        "session_token": session_token,
        "access_expires_at": access_expires_at,
        "session_expires_at": session_expires_at,
        "error": "",
    }

    if not _should_renew_token(access_expires_at):
        return result

    if _should_renew_token(session_expires_at):
        result["error"] = "La sesión ha expirado, por favor inicie sesión nuevamente"
        return result

    response = laim_refresh_token(session_token)
    if response.get("success") and response.get("access_token"):
        result["renewed"] = True
        result["access_token"] = response["access_token"]
        result["session_token"] = response.get("session_token", session_token)
        result["access_expires_at"] = int(response.get("access_expires_at", 0))
        result["session_expires_at"] = int(response.get("session_expires_at", 0))
        return result

    result["error"] = response.get("error", "No se pudieron renovar los tokens")
    return result


def laim_get_session_permissions(
    identity_type_id: int,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Obtiene permisos de bajo nivel para el rol."""
    return _request_middleware(
        "GET",
        f"/laim/session/permissions?identity_type_id={identity_type_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_get_status(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Obtiene el estado del sistema LAIM.

    Flujo: LAIM Web → Middleware /laim/status → Broker → Backend Core
    """
    return _request_middleware(
        "GET",
        "/laim/status",
        access_token=access_token,
        session_token=session_token,
    )

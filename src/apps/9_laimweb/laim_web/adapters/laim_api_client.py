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

import httpx

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
        return {
            "success": False,
            "error": f"HTTP {exc.response.status_code}: {exc.response.text}",
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

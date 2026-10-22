"""Puente de Configuración → General hacia los endpoints support_ops ya existentes.

El navegador no llama a ``/api/support/*``. Un administrador (identidad 1 o 2)
hace que laimweb acuñe ``operation=support_ops`` con ``LAIM_SUPPORT_SECRET`` y
reenvíe el JSON en claro a middleware, igual que el salto interno tras descifrar
el canal de laim_maintenance.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

from laim_web.adapters.laim_api_client import laim_support_forward
from laim_web.support_gateway import mint_support_token, support_secret

ADMIN_IDENTITY_TYPE_IDS = {1, 2}
_SECRET_FIELDS = {
    "user_password",
    "user_otp",
    "password",
    "password_confirm",
    "master_key",
    "master_key_cipher",
}


def portal_environment_name() -> str:
    """Nombre del entorno de este portal. No hay selector silicon/dev/pre."""
    for key in ("ANEWHOPE_ENV", "ENVIRONMENT", "environment"):
        value = (os.environ.get(key) or "").strip()
        if value:
            return value
    return "portal"


def visible_account(item: dict[str, Any] | None) -> dict[str, Any]:
    """Fila de usuario para el modal. Un ``estado`` ausente queda vacío."""
    raw = item or {}
    estado = raw.get("estado")
    blocked = raw.get("blocked", False)
    if isinstance(blocked, str):
        blocked = blocked.strip().lower() in {"1", "true", "yes", "bloqueado"}
    visible = {
        key: value
        for key, value in raw.items()
        if key not in _SECRET_FIELDS and key not in {"estado", "blocked"}
    }
    visible["user_id"] = int(raw.get("user_id") or 0)
    visible["user_name"] = str(raw.get("user_name") or "")
    visible["user_email"] = str(raw.get("user_email") or "")
    visible["user_mobile"] = str(raw.get("user_mobile") or "")
    visible["full_name"] = str(raw.get("full_name") or "")
    visible["estado"] = "" if estado is None else str(estado)
    visible["blocked"] = bool(blocked)
    return visible


def users_list_path(query: str) -> str:
    text = (query or "").strip()
    if not text:
        return "/laim/support/users"
    return "/laim/support/users?" + urlencode({"query": text})


def support_admin_call(
    identity_type_id: int,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Acuña support_ops y reenvía. La sesión del portal no viaja en Authorization."""
    if int(identity_type_id or 0) not in ADMIN_IDENTITY_TYPE_IDS:
        return {
            "success": False,
            "error": "Esta acción solo está disponible para un administrador.",
        }
    secret = support_secret()
    if not secret:
        return {"success": False, "error": "LAIM_SUPPORT_SECRET no configurado"}
    token = mint_support_token(secret)
    return laim_support_forward(
        method,
        path,
        authorization=f"Bearer {token}",
        payload=payload,
    )

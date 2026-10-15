"""Operador laim_maintenance: listar/editar cuentas de laimweb (laim_users)."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

_AUTH = Path(__file__).resolve().parent / "laim_auth_service.py"
_spec = importlib.util.spec_from_file_location("laim_auth_service_users_ops", _AUTH)
if _spec is None or _spec.loader is None:
    raise ImportError("No se pudo cargar laim_auth_service")
_auth = importlib.util.module_from_spec(_spec)
sys.modules["laim_auth_service_users_ops"] = _auth
_spec.loader.exec_module(_auth)

encrypt_password = _auth.encrypt_password
MSG_RESET_MISMATCH = _auth.MSG_RESET_MISMATCH
MSG_RESET_TOO_SHORT = _auth.MSG_RESET_TOO_SHORT
LaimAuthService = _auth.LaimAuthService  # fallback a laim_core_db en runtime

MSG_PASSWORD_UPDATED = "La contraseña se ha actualizado con éxito"
MSG_USER_TAKEN = "El nombre de usuario ya existe"
MSG_EMAIL_TAKEN = "La dirección de e-mail ya está registrada"
MSG_NOT_FOUND = "Usuario no encontrado"
MSG_USERNAME_REQUIRED = "El usuario es obligatorio."
MSG_EMAIL_REQUIRED = "El e-mail es obligatorio."


def _split_full_name(full_name: str) -> tuple[str | None, str | None]:
    parts = (full_name or "").strip().split()
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


class LaimUsersOpsService:
    """Misma persistencia y Fernet que el alta público; sin devolver la clave."""

    def __init__(self, user_repo: Any | None = None) -> None:
        self._logger = logging.getLogger("LaimUsersOpsService")
        if user_repo is not None:
            self._user_repo = user_repo
            return
        self._user_repo = LaimAuthService()._user_repo

    def list_users(self, query: str = "") -> dict[str, Any]:
        items = self._user_repo.list_portal_users(query)
        return {"success": True, "items": items}

    def get_user(self, user_id: int) -> dict[str, Any]:
        item = self._user_repo.get_portal_account(user_id)
        if item is None:
            return {"success": False, "error": MSG_NOT_FOUND}
        return {"success": True, "item": item}

    def update_profile(
        self,
        user_id: int,
        user_name: str,
        user_email: str,
        user_mobile: str | None = None,
        full_name: str = "",
    ) -> dict[str, Any]:
        current = self._user_repo.get_portal_account(user_id)
        if current is None:
            return {"success": False, "error": MSG_NOT_FOUND}
        name = (user_name or "").strip()
        email = (user_email or "").strip()
        if len(name) < 3:
            return {"success": False, "error": MSG_USERNAME_REQUIRED}
        if len(email) < 5:
            return {"success": False, "error": MSG_EMAIL_REQUIRED}
        mobile = (user_mobile or "").strip()
        if len(mobile) > 20:
            return {"success": False, "error": "El móvil no puede superar 20 caracteres"}
        if self._user_repo.username_taken_by_other(name, user_id):
            return {"success": False, "error": MSG_USER_TAKEN}
        if self._user_repo.email_taken_by_other(email, user_id):
            return {"success": False, "error": MSG_EMAIL_TAKEN}
        first_name, sur_name = _split_full_name(full_name)
        self._user_repo.update_portal_profile(
            user_id=user_id,
            user_name=name,
            user_email=email,
            user_mobile=mobile or None,
            first_name=first_name,
            sur_name=sur_name,
        )
        self._user_repo.append_auth_log(
            user_name=name,
            event="profile_change",
            status="success",
            details={"action": "operator_update", "user_id": user_id},
        )
        item = self._user_repo.get_portal_account(user_id)
        return {"success": True, "item": item}

    def update_password(
        self, user_id: int, password: str, password_confirm: str
    ) -> dict[str, Any]:
        current = self._user_repo.get_user_by_id(user_id)
        if current is None:
            return {"success": False, "error": MSG_NOT_FOUND}
        if password != password_confirm:
            return {"success": False, "error": MSG_RESET_MISMATCH}
        if len(password) < 8:
            return {"success": False, "error": MSG_RESET_TOO_SHORT}
        encrypted = encrypt_password(password)
        self._user_repo.update_user_password(user_id, encrypted)
        self._user_repo.append_auth_log(
            user_name=current.user_name,
            event="password_change",
            status="success",
            details={"action": "operator_password", "user_id": user_id},
        )
        return {"success": True, "message": MSG_PASSWORD_UPDATED}

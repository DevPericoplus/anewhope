"""Estado de sesión compartido para LAIM Web con prefijo Redis ``laim:``.

Usa la misma infraestructura Redis que frontend/backoffice pero aísla las claves
de tokens para evitar colisiones entre aplicaciones.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _load_shared_session_state_class():
    """Carga SharedSessionState sin importar paquetes numéricos."""
    shared_state_path = (
        Path(__file__).resolve().parent / "shared_session_state.py"
    )
    spec = importlib.util.spec_from_file_location(
        "shared_session_state_laim", shared_state_path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["shared_session_state_laim"] = module
    spec.loader.exec_module(module)
    return module.SharedSessionState


SharedSessionState = _load_shared_session_state_class()

LAIM_REDIS_KEY_PREFIX = "laim:session_tokens:"


class LaimSharedSessionState(SharedSessionState):
    """Sesión LAIM Web sincronizada vía Redis con prefijo dedicado."""

    current_app: str = "laimweb"

    def _redis_tokens_key(self) -> str:
        """Clave Redis para tokens de la sesión LAIM."""
        return f"{LAIM_REDIS_KEY_PREFIX}{self.session_id}"

    def load_user_data(
        self,
        user_id: int,
        organization_id: int,
        identity_type_id: int,
        user_name: str,
        user_email: str,
        user_mobile: str,
        access_token: str,
        session_token: str,
        permissions: dict[str, Any],
        access_expires_at: int = 0,
        session_expires_at: int = 0,
        session_id: str = "",
    ) -> None:
        """Carga datos de usuario tras login LAIM."""
        self.user_id = user_id
        self.organization_id = organization_id
        self.identity_type_id = identity_type_id
        self.user_name = user_name
        self.user_email = user_email
        self.user_mobile = user_mobile
        self.is_logged_in = True
        self.is_active = True
        self.is_blocked = False

        self.access_token = access_token
        self.session_token = session_token
        self.access_token_expires_at = access_expires_at
        self.session_token_expires_at = session_expires_at

        self._load_permissions(permissions)

        self.session_id = session_id or session_token
        self.login_time = datetime.now().isoformat()
        self.last_activity = datetime.now().isoformat()
        self.current_app = "laimweb"

        self._save_tokens_to_redis()

    def clear_session(self) -> None:
        """Limpia sesión LAIM y elimina tokens en Redis."""
        session_id = self.session_id
        super().clear_session()
        self.current_app = "laimweb"
        if session_id:
            self._delete_tokens_from_redis(session_id)

    def _save_tokens_to_redis(self) -> None:
        """Guarda tokens en Redis con prefijo ``laim:``."""
        if not self.session_id:
            return

        try:
            import redis

            redis_config = self._get_redis_config()
            redis_params = {
                "host": redis_config["host"],
                "port": redis_config["port"],
                "db": redis_config["db"],
                "decode_responses": True,
            }
            if redis_config["password"]:
                redis_params["username"] = "default"
                redis_params["password"] = redis_config["password"]

            client = redis.Redis(**redis_params)
            tokens_data = {
                "access_token": self.access_token,
                "session_token": self.session_token,
                "access_expires_at": self.access_token_expires_at,
                "session_expires_at": self.session_token_expires_at,
                "updated_at": datetime.now().isoformat(),
                "user_id": self.user_id,
                "organization_id": self.organization_id,
            }
            redis_key = self._redis_tokens_key()
            client.setex(redis_key, 2700, json.dumps(tokens_data))
            print(f"[LAIM REDIS SYNC] Tokens guardados: {redis_key}")
        except Exception as exc:
            print(f"[LAIM REDIS SYNC] Error al guardar tokens: {exc}")

    def _load_tokens_from_redis(self) -> bool:
        """Carga tokens desde Redis si hay una versión más reciente."""
        if not self.session_id:
            return False

        try:
            import redis

            redis_config = self._get_redis_config()
            redis_params = {
                "host": redis_config["host"],
                "port": redis_config["port"],
                "db": redis_config["db"],
                "decode_responses": True,
            }
            if redis_config["password"]:
                redis_params["username"] = "default"
                redis_params["password"] = redis_config["password"]

            client = redis.Redis(**redis_params)
            redis_key = self._redis_tokens_key()
            tokens_json = client.get(redis_key)
            if not tokens_json:
                return False

            tokens_data = json.loads(tokens_json)
            redis_updated_at = tokens_data.get("updated_at", "")
            current_updated_at = self.last_activity
            should_update = not current_updated_at or (
                redis_updated_at > current_updated_at
            )

            if should_update:
                self.access_token = tokens_data["access_token"]
                self.session_token = tokens_data["session_token"]
                self.access_token_expires_at = tokens_data["access_expires_at"]
                self.session_token_expires_at = tokens_data["session_expires_at"]
                self.last_activity = redis_updated_at
                print(f"[LAIM REDIS SYNC] Tokens actualizados: {redis_key}")
                return True
            return False
        except Exception as exc:
            print(f"[LAIM REDIS SYNC] Error al cargar tokens: {exc}")
            return False

    def _delete_tokens_from_redis(self, session_id: str) -> None:
        """Elimina tokens LAIM de Redis al cerrar sesión."""
        try:
            import redis

            redis_config = self._get_redis_config()
            redis_params = {
                "host": redis_config["host"],
                "port": redis_config["port"],
                "db": redis_config["db"],
                "decode_responses": True,
            }
            if redis_config["password"]:
                redis_params["username"] = "default"
                redis_params["password"] = redis_config["password"]

            client = redis.Redis(**redis_params)
            redis_key = f"{LAIM_REDIS_KEY_PREFIX}{session_id}"
            client.delete(redis_key)
            print(f"[LAIM REDIS SYNC] Tokens eliminados: {redis_key}")
        except Exception as exc:
            print(f"[LAIM REDIS SYNC] Error al eliminar tokens: {exc}")

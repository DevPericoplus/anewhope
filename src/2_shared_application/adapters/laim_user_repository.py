"""Repositorio de usuarios y auth logs LAIM (laim_core_db)."""

from __future__ import annotations

import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class LaimUserRecord:
    """Registro de usuario LAIM."""

    user_id: int
    organization_id: int
    identity_type_id: int
    user_name: str
    user_password: str
    user_email: str
    user_mobile: str
    user_otp: str
    active: bool
    blocked: bool


class LaimUserRepository:
    """Acceso a laim_users, laim_organizations y laim_auth_logs."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._logger = logging.getLogger("LaimUserRepository")

    def get_user_by_name(self, user_name: str) -> LaimUserRecord | None:
        """Obtiene usuario por nombre."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT user_id, organization_id, identity_type_id,
                           user_name, user_password, user_email, user_mobile,
                           user_otp, active, blocked
                    FROM laim_users
                    WHERE user_name = :user_name
                    LIMIT 1
                    """
                ),
                {"user_name": user_name},
            ).mappings().fetchone()
        if row is None:
            return None
        return self._row_to_user(dict(row))

    def get_user_by_email(self, user_email: str) -> LaimUserRecord | None:
        """Obtiene usuario por email."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT user_id, organization_id, identity_type_id,
                           user_name, user_password, user_email, user_mobile,
                           user_otp, active, blocked
                    FROM laim_users
                    WHERE LOWER(user_email) = LOWER(:user_email)
                    LIMIT 1
                    """
                ),
                {"user_email": user_email.strip()},
            ).mappings().fetchone()
        if row is None:
            return None
        return self._row_to_user(dict(row))

    def user_exists(self, user_name: str, user_email: str) -> bool:
        """Verifica unicidad de username o email."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT COUNT(*) AS total
                    FROM laim_users
                    WHERE user_name = :user_name
                       OR LOWER(user_email) = LOWER(:user_email)
                    """
                ),
                {"user_name": user_name, "user_email": user_email.strip()},
            ).mappings().fetchone()
        return bool(row and int(row["total"]) > 0)

    def get_organization_id_by_name(self, organization_name: str) -> int | None:
        """Obtiene ID de organización por nombre."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT organization_id
                    FROM laim_organizations
                    WHERE LOWER(organization_name) = LOWER(:name)
                      AND active = 1
                    LIMIT 1
                    """
                ),
                {"name": organization_name},
            ).mappings().fetchone()
        if row is None:
            return None
        return int(row["organization_id"])

    def create_user(
        self,
        organization_id: int,
        identity_type_id: int,
        user_name: str,
        encrypted_password: str,
        user_email: str,
        user_mobile: str | None,
        first_name: str | None,
        sur_name: str | None,
    ) -> int:
        """Crea usuario LAIM con contact info."""
        user_otp = f"{secrets.randbelow(10000):04d}"
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_users (
                        organization_id, identity_type_id, user_name, user_password,
                        user_email, user_mobile, user_otp, active, blocked
                    ) VALUES (
                        :organization_id, :identity_type_id, :user_name, :user_password,
                        :user_email, :user_mobile, :user_otp, 1, 0
                    )
                    """
                ),
                {
                    "organization_id": organization_id,
                    "identity_type_id": identity_type_id,
                    "user_name": user_name.strip(),
                    "user_password": encrypted_password,
                    "user_email": user_email.strip().lower(),
                    "user_mobile": (user_mobile or "").strip() or None,
                    "user_otp": user_otp,
                },
            )
            user_id = int(result.lastrowid)
            conn.execute(
                text(
                    """
                    INSERT INTO laim_user_contact_info (
                        user_id, first_name, sur_name
                    ) VALUES (:user_id, :first_name, :sur_name)
                    """
                ),
                {
                    "user_id": user_id,
                    "first_name": first_name,
                    "sur_name": sur_name,
                },
            )
        self._logger.info(
            "Usuario LAIM creado user_id=%s user_name=%s org_id=%s",
            user_id,
            user_name,
            organization_id,
        )
        return user_id

    def set_user_blocked(self, user_name: str, blocked: bool = True) -> None:
        """Marca usuario como bloqueado."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE laim_users SET blocked = :blocked WHERE user_name = :user_name"
                ),
                {"blocked": 1 if blocked else 0, "user_name": user_name},
            )

    def count_recent_failed_attempts(
        self, user_name: str, minutes: int = 10, max_attempts: int = 3
    ) -> int:
        """Cuenta intentos fallidos recientes."""
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT COUNT(*) AS total
                    FROM laim_auth_logs
                    WHERE user_name = :user_name
                      AND event IN ('login_attempt', 'login_failed')
                      AND status IN ('failed', 'failure')
                      AND timestamp >= :since
                    """
                ),
                {"user_name": user_name, "since": since.replace(tzinfo=None)},
            ).mappings().fetchone()
        total = int(row["total"]) if row else 0
        return total if total < max_attempts else max_attempts

    def append_auth_log(
        self,
        user_name: str,
        event: str,
        status: str,
        ip_address: str = "",
        session_id: str | None = None,
        user_agent: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Registra evento de autenticación."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_auth_logs (
                        user_name, event, status, ip_address, session_id, user_agent, details
                    ) VALUES (
                        :user_name, :event, :status, :ip_address, :session_id, :user_agent, :details
                    )
                    """
                ),
                {
                    "user_name": user_name,
                    "event": event,
                    "status": status,
                    "ip_address": ip_address or None,
                    "session_id": session_id,
                    "user_agent": user_agent or None,
                    "details": json.dumps(details or {}, ensure_ascii=False),
                },
            )

    def get_low_level_permissions(self, identity_type_id: int) -> dict[str, bool]:
        """Obtiene permisos de bajo nivel para un rol."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM laim_low_level_permissions WHERE id_permissions = :id"),
                {"id": identity_type_id},
            ).mappings().fetchone()
        if row is None:
            return {}
        permissions: dict[str, bool] = {}
        for key, value in dict(row).items():
            if key == "id_permissions":
                continue
            permissions[key] = bool(value)
        return permissions

    @staticmethod
    def _row_to_user(row: dict[str, Any]) -> LaimUserRecord:
        """Convierte fila SQL a LaimUserRecord."""
        return LaimUserRecord(
            user_id=int(row["user_id"]),
            organization_id=int(row["organization_id"]),
            identity_type_id=int(row["identity_type_id"]),
            user_name=str(row["user_name"]),
            user_password=str(row["user_password"]),
            user_email=str(row["user_email"]),
            user_mobile=str(row.get("user_mobile") or ""),
            user_otp=str(row.get("user_otp") or ""),
            active=bool(row.get("active")),
            blocked=bool(row.get("blocked")),
        )

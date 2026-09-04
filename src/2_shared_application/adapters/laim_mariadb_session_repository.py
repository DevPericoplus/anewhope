"""Repositorio MariaDB de sesiones LAIM (laim_sessions)."""

from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


_SESSION_ENTITY_ALIASES = (
    "src.shared_domain.entities.session",
    "_session_entities_repo",
    "_session_entities_service",
    "_session_entities_jwt",
    "ddd_session_entities",
    "_laim_session_entities",
)


def _load_session_entities():
    """Carga entities/session.py una sola vez (evita clases Session duplicadas)."""
    for name in _SESSION_ENTITY_ALIASES:
        existing = sys.modules.get(name)
        if existing is not None and hasattr(existing, "Session"):
            for alias in _SESSION_ENTITY_ALIASES:
                sys.modules.setdefault(alias, existing)
            return existing

    module_path = (
        Path(__file__).resolve().parents[2] / "1_shared_domain/entities/session.py"
    )
    spec = importlib.util.spec_from_file_location(
        "src.shared_domain.entities.session", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar session entities")
    module = importlib.util.module_from_spec(spec)
    for alias in _SESSION_ENTITY_ALIASES:
        sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


_session_entities = _load_session_entities()
Session = _session_entities.Session
SessionStatus = _session_entities.SessionStatus
SessionTokenBinding = _session_entities.SessionTokenBinding


class LaimMariaDbSessionRepository:
    """Persistencia de sesiones LAIM en laim_core_db.laim_sessions."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._logger = logging.getLogger("LaimMariaDbSessionRepository")

    def get_by_session_id(self, session_id: str) -> Session | None:
        """Obtiene una sesión por ID."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT session_id, user_id, organization_id, identity_type_id,
                           access_token_jti, session_token_jti, status,
                           created_at, last_activity, expires_at, ip_address, user_agent
                    FROM laim_sessions
                    WHERE session_id = :session_id
                    """
                ),
                {"session_id": session_id},
            ).mappings().fetchone()
        if row is None:
            return None
        return self._row_to_session(dict(row))

    def list_by_user_id(self, user_id: int) -> tuple[Session, ...]:
        """Lista sesiones de un usuario."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT session_id, user_id, organization_id, identity_type_id,
                           access_token_jti, session_token_jti, status,
                           created_at, last_activity, expires_at, ip_address, user_agent
                    FROM laim_sessions
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            ).mappings().fetchall()
        return tuple(self._row_to_session(dict(row)) for row in rows)

    def save(self, session: Session) -> Session:
        """Inserta o actualiza una sesión."""
        params = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "organization_id": session.organization_id,
            "identity_type_id": session.identity_type_id,
            "access_token_jti": session.tokens.access_token_jti,
            "session_token_jti": session.tokens.session_token_jti,
            "status": session.status.value,
            "created_at": session.created_at.replace(tzinfo=None),
            "last_activity": session.last_activity.replace(tzinfo=None),
            "expires_at": session.expires_at.replace(tzinfo=None),
            "ip_address": session.ip_address or None,
            "user_agent": session.user_agent or None,
        }
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_sessions (
                        session_id, user_id, organization_id, identity_type_id,
                        access_token_jti, session_token_jti, status,
                        created_at, last_activity, expires_at, ip_address, user_agent
                    ) VALUES (
                        :session_id, :user_id, :organization_id, :identity_type_id,
                        :access_token_jti, :session_token_jti, :status,
                        :created_at, :last_activity, :expires_at, :ip_address, :user_agent
                    )
                    ON DUPLICATE KEY UPDATE
                        access_token_jti = VALUES(access_token_jti),
                        session_token_jti = VALUES(session_token_jti),
                        status = VALUES(status),
                        last_activity = VALUES(last_activity),
                        expires_at = VALUES(expires_at),
                        ip_address = VALUES(ip_address),
                        user_agent = VALUES(user_agent)
                    """
                ),
                params,
            )
        self._logger.info(
            "Sesión LAIM persistida session_id=%s user_id=%s",
            session.session_id,
            session.user_id,
        )
        return session

    def update_status(
        self, session_id: str, status: SessionStatus, updated_at: datetime | None = None
    ) -> bool:
        """Actualiza el estado de una sesión."""
        activity = (updated_at or datetime.now(timezone.utc)).replace(tzinfo=None)
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE laim_sessions
                    SET status = :status, last_activity = :last_activity
                    WHERE session_id = :session_id
                    """
                ),
                {
                    "status": status.value,
                    "last_activity": activity,
                    "session_id": session_id,
                },
            )
        return result.rowcount > 0

    def update_activity(self, session_id: str, last_activity: datetime) -> bool:
        """Actualiza última actividad."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE laim_sessions
                    SET last_activity = :last_activity
                    WHERE session_id = :session_id
                    """
                ),
                {
                    "last_activity": last_activity.replace(tzinfo=None),
                    "session_id": session_id,
                },
            )
        return result.rowcount > 0

    @staticmethod
    def _row_to_session(row: dict[str, Any]) -> Session:
        """Convierte fila SQL a entidad Session."""
        return Session(
            session_id=str(row["session_id"]),
            user_id=int(row["user_id"]),
            organization_id=int(row["organization_id"]),
            identity_type_id=int(row["identity_type_id"]),
            tokens=SessionTokenBinding(
                access_token_jti=str(row.get("access_token_jti") or ""),
                session_token_jti=str(row.get("session_token_jti") or ""),
            ),
            status=SessionStatus(str(row["status"])),
            created_at=_ensure_utc(row["created_at"]),
            last_activity=_ensure_utc(row["last_activity"]),
            expires_at=_ensure_utc(row["expires_at"]),
            ip_address=str(row.get("ip_address") or ""),
            user_agent=str(row.get("user_agent") or ""),
        )


def _ensure_utc(value: datetime) -> datetime:
    """Normaliza datetime a UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_laim_session_engine(
    settings: dict[str, Any],
    *,
    role: str = "writer",
) -> Engine:
    """Crea engine SQLAlchemy para laim_core_db."""
    admin_dsn = str(settings.get("admin_dsn") or "").strip()
    writer_dsn = str(settings.get("writer_dsn") or "").strip()
    if role == "admin" and admin_dsn:
        return create_engine(admin_dsn, pool_pre_ping=True)
    if role == "writer" and writer_dsn:
        return create_engine(writer_dsn, pool_pre_ping=True)

    host = settings.get("host", "localhost")
    port = settings.get("port", 3306)
    database = settings.get("database", "laim_core_db")
    if role == "admin":
        user_raw = settings.get("admin_user") or settings.get("writer_user", "")
        password_raw = settings.get("admin_password") or settings.get(
            "writer_password", ""
        )
    else:
        user_raw = settings.get("writer_user", "")
        password_raw = settings.get("writer_password", "")
    user = quote_plus(str(user_raw))
    password = quote_plus(str(password_raw))
    dsn = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    return create_engine(dsn, pool_pre_ping=True)

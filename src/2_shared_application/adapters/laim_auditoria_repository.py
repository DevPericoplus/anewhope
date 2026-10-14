"""Persistencia MariaDB de las tablas auditoria_* del portal laimweb."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from pathlib import Path
import importlib.util
import sys

_domain_path = Path(__file__).resolve().parents[1] / "domain" / "laim_auditoria.py"
_spec = importlib.util.spec_from_file_location("laim_auditoria_domain_repo", _domain_path)
_domain = importlib.util.module_from_spec(_spec)
sys.modules["laim_auditoria_domain_repo"] = _domain
_spec.loader.exec_module(_domain)

VISITA_IDLE_SECONDS = _domain.VISITA_IDLE_SECONDS

USUARIOS_TABLE = "auditoria_usuarios"
VISITAS_TABLE = "auditoria_visitas"
PAGINAS_TABLE = "auditoria_paginas"
INSTALADORES_TABLE = "auditoria_instaladores"
FORO_TABLE = "auditoria_foro"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    parsed = datetime.fromisoformat(str(value).replace(" ", "T"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


class LaimAuditoriaRepository:
    """Inserts append-only y UPSERT de visitas/tramos de página."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._logger = logging.getLogger("LaimAuditoriaRepository")

    def record_usuario(
        self,
        accion: str,
        user_name: str,
        user_id: int | None = None,
        session_id: str | None = None,
    ) -> int:
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    INSERT INTO {USUARIOS_TABLE} (accion, user_id, user_name, session_id)
                    VALUES (:accion, :user_id, :user_name, :session_id)
                    """
                ),
                {
                    "accion": accion,
                    "user_id": user_id,
                    "user_name": user_name,
                    "session_id": session_id or None,
                },
            )
            return int(result.lastrowid)

    def record_instalador(
        self,
        accion: str,
        edition: str,
        platform: str,
        version: str = "",
        filename: str = "",
        user_id: int | None = None,
    ) -> int:
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    INSERT INTO {INSTALADORES_TABLE}
                        (accion, edition, platform, version, filename, user_id)
                    VALUES
                        (:accion, :edition, :platform, :version, :filename, :user_id)
                    """
                ),
                {
                    "accion": accion,
                    "edition": edition,
                    "platform": platform,
                    "version": version or "",
                    "filename": filename or "",
                    "user_id": user_id,
                },
            )
            return int(result.lastrowid)

    def record_foro(
        self,
        accion: str,
        user_id: int,
        thread_id: int,
        post_id: int | None = None,
        subcategory_id: str = "",
    ) -> int:
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    INSERT INTO {FORO_TABLE}
                        (accion, user_id, thread_id, post_id, subcategory_id)
                    VALUES
                        (:accion, :user_id, :thread_id, :post_id, :subcategory_id)
                    """
                ),
                {
                    "accion": accion,
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "post_id": post_id,
                    "subcategory_id": subcategory_id or "",
                },
            )
            return int(result.lastrowid)

    def get_latest_visita(self, session_id: str) -> dict[str, Any] | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT id, user_id, session_id, started_at, last_seen_at, segundos
                    FROM {VISITAS_TABLE}
                    WHERE session_id = :session_id
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"session_id": session_id},
            ).mappings().fetchone()
        return dict(row) if row is not None else None

    def upsert_visita(
        self,
        user_id: int,
        session_id: str,
        now: datetime | None = None,
        idle_seconds: int = VISITA_IDLE_SECONDS,
    ) -> dict[str, Any]:
        moment = now or _utcnow()
        latest = self.get_latest_visita(session_id)
        if latest is None or self._is_stale(latest.get("last_seen_at"), moment, idle_seconds):
            return self._insert_visita(user_id, session_id, moment)
        return self._touch_visita(int(latest["id"]), latest.get("started_at"), moment)

    def get_open_pagina(self, session_id: str) -> dict[str, Any] | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT id, user_id, session_id, seccion, started_at, ended_at, segundos
                    FROM {PAGINAS_TABLE}
                    WHERE session_id = :session_id AND ended_at IS NULL
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"session_id": session_id},
            ).mappings().fetchone()
        return dict(row) if row is not None else None

    def heartbeat_pagina(
        self,
        user_id: int,
        session_id: str,
        seccion: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        moment = now or _utcnow()
        opened = self.get_open_pagina(session_id)
        if opened is None:
            return self._insert_pagina(user_id, session_id, seccion, moment)
        if str(opened.get("seccion")) != seccion:
            self._close_pagina(int(opened["id"]), opened.get("started_at"), moment)
            return self._insert_pagina(user_id, session_id, seccion, moment)
        return self._touch_pagina(int(opened["id"]), opened.get("started_at"), moment)

    def close_visita_and_pagina(
        self,
        session_id: str,
        now: datetime | None = None,
    ) -> None:
        moment = now or _utcnow()
        opened = self.get_open_pagina(session_id)
        if opened is not None:
            self._close_pagina(int(opened["id"]), opened.get("started_at"), moment)
        latest = self.get_latest_visita(session_id)
        if latest is not None:
            self._touch_visita(int(latest["id"]), latest.get("started_at"), moment)

    def _is_stale(self, last_seen: Any, now: datetime, idle_seconds: int) -> bool:
        if last_seen is None:
            return True
        return (now - _as_dt(last_seen)).total_seconds() > idle_seconds

    def _seconds_since(self, started_at: Any, now: datetime) -> int:
        started = _as_dt(started_at) if started_at is not None else now
        return max(0, int((now - started).total_seconds()))

    def _insert_visita(
        self, user_id: int, session_id: str, moment: datetime
    ) -> dict[str, Any]:
        iso = moment.isoformat()
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    INSERT INTO {VISITAS_TABLE}
                        (user_id, session_id, started_at, last_seen_at, segundos)
                    VALUES
                        (:user_id, :session_id, :started_at, :last_seen_at, 0)
                    """
                ),
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "started_at": iso,
                    "last_seen_at": iso,
                },
            )
            visita_id = int(result.lastrowid)
        return {
            "id": visita_id,
            "user_id": user_id,
            "session_id": session_id,
            "started_at": iso,
            "last_seen_at": iso,
            "segundos": 0,
            "opened": True,
        }

    def _touch_visita(
        self, visita_id: int, started_at: Any, moment: datetime
    ) -> dict[str, Any]:
        segundos = self._seconds_since(started_at, moment)
        iso = moment.isoformat()
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    UPDATE {VISITAS_TABLE}
                    SET last_seen_at = :last_seen_at, segundos = :segundos
                    WHERE id = :id
                    """
                ),
                {"last_seen_at": iso, "segundos": segundos, "id": visita_id},
            )
        return {"id": visita_id, "last_seen_at": iso, "segundos": segundos, "opened": False}

    def _insert_pagina(
        self, user_id: int, session_id: str, seccion: str, moment: datetime
    ) -> dict[str, Any]:
        iso = moment.isoformat()
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    INSERT INTO {PAGINAS_TABLE}
                        (user_id, session_id, seccion, started_at, ended_at, segundos)
                    VALUES
                        (:user_id, :session_id, :seccion, :started_at, NULL, 0)
                    """
                ),
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "seccion": seccion,
                    "started_at": iso,
                },
            )
            pagina_id = int(result.lastrowid)
        return {
            "id": pagina_id,
            "user_id": user_id,
            "session_id": session_id,
            "seccion": seccion,
            "started_at": iso,
            "ended_at": None,
            "segundos": 0,
        }

    def _touch_pagina(
        self, pagina_id: int, started_at: Any, moment: datetime
    ) -> dict[str, Any]:
        segundos = self._seconds_since(started_at, moment)
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    UPDATE {PAGINAS_TABLE}
                    SET segundos = :segundos
                    WHERE id = :id AND ended_at IS NULL
                    """
                ),
                {"segundos": segundos, "id": pagina_id},
            )
        return {"id": pagina_id, "segundos": segundos}

    def _close_pagina(self, pagina_id: int, started_at: Any, moment: datetime) -> None:
        segundos = self._seconds_since(started_at, moment)
        iso = moment.isoformat()
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    UPDATE {PAGINAS_TABLE}
                    SET ended_at = :ended_at, segundos = :segundos
                    WHERE id = :id
                    """
                ),
                {"ended_at": iso, "segundos": segundos, "id": pagina_id},
            )

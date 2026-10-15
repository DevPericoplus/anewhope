"""Persistencia de instalaciones LAIM (migraciones 030 + 031)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

VALID_OS = ("windows", "mac", "linux")
VALID_EDITIONS = ("community_edition", "advance")
ORIGIN_MANUAL = "manual"
ORIGIN_LAIM = "laim"
STATUS_PENDING = "pending_recognition"
STATUS_REGISTERED = "registered"
STATUS_REJECTED = "rejected"
EVENT_REGISTERED = "registered"


def _utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _email_key(email: str) -> str:
    return (email or "").strip().lower()


@dataclass(frozen=True, slots=True)
class Installation:
    installation_id: int
    serial_number: str
    user_id: int
    hostname: str
    display_name: str
    operating_system: str
    edition: str
    origin: str
    status: str
    license_id: Optional[int]
    proposed_at: datetime
    registered_at: Optional[datetime]
    recognized_at: Optional[datetime]
    rejected_at: Optional[datetime]
    updated_at: datetime

    def as_public_dict(self) -> dict[str, Any]:
        """Campos de identity.dat visibles. Nunca master_key_cipher."""
        return {
            "installation_id": self.installation_id,
            "user_id": self.user_id,
            "serial_number": self.serial_number,
            "hostname": self.hostname,
            "display_name": self.display_name,
            "operating_system": self.operating_system,
            "edition": self.edition,
            "origin": self.origin,
            "status": self.status,
            "proposed_at": self.proposed_at.isoformat(),
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "recognized_at": self.recognized_at.isoformat() if self.recognized_at else None,
            "updated_at": self.updated_at.isoformat(),
        }


class LaimInstallationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_by_id(self, installation_id: int) -> Installation | None:
        return self._one("installation_id = :id", {"id": installation_id})

    def get_by_serial(self, serial_number: str) -> Installation | None:
        return self._one("serial_number = :serial", {"serial": serial_number.strip()})

    def list_for_user(self, user_id: int) -> list[Installation]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"{self._select()} WHERE user_id = :user_id "
                    "AND status <> 'rejected' ORDER BY installation_id ASC"
                ),
                {"user_id": user_id},
            ).mappings().fetchall()
        return [self._from_row(dict(r)) for r in rows]

    def list_all(self, limit: int = 200) -> list[Installation]:
        cap = max(1, min(int(limit), 500))
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"{self._select()} WHERE status <> 'rejected' "
                    "ORDER BY installation_id DESC LIMIT :lim"
                ),
                {"lim": cap},
            ).mappings().fetchall()
        return [self._from_row(dict(r)) for r in rows]

    def insert(
        self,
        *,
        serial_number: str,
        user_id: int,
        hostname: str,
        operating_system: str,
        edition: str,
        origin: str,
        status: str,
        display_name: str = "",
    ) -> Installation:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_installations (
                        serial_number, user_id, hostname, display_name,
                        operating_system, edition, origin, status
                    ) VALUES (
                        :serial_number, :user_id, :hostname, :display_name,
                        :operating_system, :edition, :origin, :status
                    )
                    """
                ),
                {
                    "serial_number": serial_number.strip(),
                    "user_id": user_id,
                    "hostname": hostname.strip(),
                    "display_name": (display_name or "").strip()[:80],
                    "operating_system": operating_system,
                    "edition": edition,
                    "origin": origin,
                    "status": status,
                },
            )
        item = self.get_by_serial(serial_number)
        assert item is not None
        return item

    def set_registered(self, installation_id: int, license_id: int, *, recognized: bool) -> None:
        extra = ", recognized_at = CURRENT_TIMESTAMP" if recognized else ""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    UPDATE laim_installations
                    SET status = :st,
                        license_id = :lid,
                        registered_at = CURRENT_TIMESTAMP
                        {extra}
                    WHERE installation_id = :id
                    """
                ),
                {"st": STATUS_REGISTERED, "lid": license_id, "id": installation_id},
            )

    def update_mutable(
        self,
        installation_id: int,
        operating_system: str,
        edition: str,
        display_name: str | None = None,
    ) -> None:
        if display_name is None:
            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE laim_installations
                        SET operating_system = :os, edition = :edition,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE installation_id = :id
                        """
                    ),
                    {"os": operating_system, "edition": edition, "id": installation_id},
                )
            return
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE laim_installations
                    SET operating_system = :os, edition = :edition,
                        display_name = :alias, updated_at = CURRENT_TIMESTAMP
                    WHERE installation_id = :id
                    """
                ),
                {
                    "os": operating_system,
                    "edition": edition,
                    "alias": (display_name or "").strip()[:80],
                    "id": installation_id,
                },
            )

    def delete(self, installation_id: int) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("DELETE FROM laim_installations WHERE installation_id = :id"),
                {"id": installation_id},
            )

    def is_register_blocked(self, email: str) -> bool:
        key = _email_key(email)
        if not key:
            return False
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT blocked_at FROM laim_installation_register_guards "
                    "WHERE user_email = :email"
                ),
                {"email": key},
            ).mappings().fetchone()
        return row is not None and row.get("blocked_at") is not None

    def record_failed_attempt(self, email: str, reason: str) -> int:
        key = _email_key(email)
        if not key:
            return 0
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT fail_count FROM laim_installation_register_guards "
                    "WHERE user_email = :email"
                ),
                {"email": key},
            ).mappings().fetchone()
            if row is None:
                conn.execute(
                    text(
                        """
                        INSERT INTO laim_installation_register_guards
                            (user_email, fail_count, last_reason)
                        VALUES (:email, 1, :reason)
                        """
                    ),
                    {"email": key, "reason": (reason or "")[:255]},
                )
                return 1
            count = int(row["fail_count"]) + 1
            conn.execute(
                text(
                    """
                    UPDATE laim_installation_register_guards
                    SET fail_count = :n, last_reason = :reason,
                        last_fail_at = CURRENT_TIMESTAMP
                    WHERE user_email = :email
                    """
                ),
                {"n": count, "reason": (reason or "")[:255], "email": key},
            )
            return count

    def block_register(self, email: str) -> None:
        key = _email_key(email)
        if not key:
            return
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE laim_installation_register_guards
                    SET blocked_at = CURRENT_TIMESTAMP
                    WHERE user_email = :email AND blocked_at IS NULL
                    """
                ),
                {"email": key},
            )

    def reset_register_attempts(self, email: str) -> None:
        key = _email_key(email)
        if not key:
            return
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE laim_installation_register_guards
                    SET fail_count = 0, blocked_at = NULL, last_reason = ''
                    WHERE user_email = :email
                    """
                ),
                {"email": key},
            )

    def insert_notification(self, user_id: int, installation_id: int) -> int:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_installation_notifications (user_id, installation_id)
                    VALUES (:user_id, :installation_id)
                    """
                ),
                {"user_id": user_id, "installation_id": installation_id},
            )
            row = conn.execute(
                text(
                    "SELECT notification_id FROM laim_installation_notifications "
                    "WHERE user_id = :user_id AND installation_id = :installation_id "
                    "ORDER BY notification_id DESC LIMIT 1"
                ),
                {"user_id": user_id, "installation_id": installation_id},
            ).mappings().fetchone()
        return int(row["notification_id"]) if row else 0

    def list_pending_notifications(self, user_id: int) -> list[dict[str, Any]]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT n.notification_id, n.installation_id, n.created_at,
                           i.hostname, i.display_name, i.operating_system
                    FROM laim_installation_notifications n
                    JOIN laim_installations i ON i.installation_id = n.installation_id
                    WHERE n.user_id = :user_id AND n.acked_at IS NULL
                      AND i.status = 'pending_recognition'
                    ORDER BY n.notification_id ASC
                    """
                ),
                {"user_id": user_id},
            ).mappings().fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            created = _utc(row["created_at"])
            out.append(
                {
                    "id": int(row["notification_id"]),
                    "installation_id": int(row["installation_id"]),
                    "hostname": str(row["hostname"] or ""),
                    "display_name": str(row.get("display_name") or ""),
                    "operating_system": str(row["operating_system"] or ""),
                    "created_at": created.isoformat() if created else "",
                }
            )
        return out

    def ack_notification(self, notification_id: int, user_id: int) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE laim_installation_notifications
                    SET acked_at = CURRENT_TIMESTAMP
                    WHERE notification_id = :id AND user_id = :user_id
                      AND acked_at IS NULL
                    """
                ),
                {"id": notification_id, "user_id": user_id},
            )
        return int(result.rowcount or 0) > 0

    def insert_metric_event(
        self,
        *,
        installation_id: int,
        user_id: int,
        operating_system: str,
        edition: str,
        origin: str,
        event_type: str = EVENT_REGISTERED,
    ) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_installation_metric_events (
                        installation_id, user_id, operating_system,
                        edition, origin, event_type
                    ) VALUES (
                        :installation_id, :user_id, :operating_system,
                        :edition, :origin, :event_type
                    )
                    """
                ),
                {
                    "installation_id": installation_id,
                    "user_id": user_id,
                    "operating_system": operating_system,
                    "edition": edition,
                    "origin": origin,
                    "event_type": event_type,
                },
            )

    def list_metric_events(self, event_type: str = EVENT_REGISTERED) -> list[dict[str, Any]]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT event_id, installation_id, user_id, operating_system,
                           edition, origin, event_type, occurred_at
                    FROM laim_installation_metric_events
                    WHERE event_type = :et
                    ORDER BY occurred_at ASC, event_id ASC
                    """
                ),
                {"et": event_type},
            ).mappings().fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            occurred = _utc(row["occurred_at"]) or datetime.now(timezone.utc)
            out.append(
                {
                    "event_id": int(row["event_id"]),
                    "installation_id": int(row["installation_id"]),
                    "user_id": int(row["user_id"]),
                    "operating_system": str(row["operating_system"]),
                    "edition": str(row["edition"]),
                    "origin": str(row["origin"]),
                    "event_type": str(row["event_type"]),
                    "occurred_at": occurred,
                }
            )
        return out

    def _select(self) -> str:
        return """
            SELECT installation_id, serial_number, user_id, hostname, display_name,
                   operating_system, edition, origin, status, license_id,
                   proposed_at, registered_at, recognized_at, rejected_at, updated_at
            FROM laim_installations
        """

    def _one(self, where: str, params: dict[str, Any]) -> Installation | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(f"{self._select()} WHERE {where} LIMIT 1"),
                params,
            ).mappings().fetchone()
        if row is None:
            return None
        return self._from_row(dict(row))

    @staticmethod
    def _from_row(row: dict[str, Any]) -> Installation:
        return Installation(
            installation_id=int(row["installation_id"]),
            serial_number=str(row["serial_number"]),
            user_id=int(row["user_id"]),
            hostname=str(row["hostname"]),
            display_name=str(row.get("display_name") or ""),
            operating_system=str(row["operating_system"]),
            edition=str(row["edition"]),
            origin=str(row["origin"]),
            status=str(row["status"]),
            license_id=int(row["license_id"]) if row.get("license_id") else None,
            proposed_at=_utc(row["proposed_at"]) or datetime.now(timezone.utc),
            registered_at=_utc(row.get("registered_at")),
            recognized_at=_utc(row.get("recognized_at")),
            rejected_at=_utc(row.get("rejected_at")),
            updated_at=_utc(row["updated_at"]) or datetime.now(timezone.utc),
        )

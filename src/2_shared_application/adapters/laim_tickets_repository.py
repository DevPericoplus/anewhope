"""Repositorio MariaDB para tickets de soporte LAIM."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from pathlib import Path
import importlib.util
import sys

_states_path = Path(__file__).resolve().parents[1] / "domain" / "laim_ticket_states.py"
_spec = importlib.util.spec_from_file_location("laim_ticket_states_repo", _states_path)
_states = importlib.util.module_from_spec(_spec)
sys.modules["laim_ticket_states_repo"] = _states
_spec.loader.exec_module(_states)

ESTADO_CLAVE_TO_ID = _states.ESTADO_CLAVE_TO_ID
ESTADO_ID_TO_CLAVE = _states.ESTADO_ID_TO_CLAVE
ESTADO_ABIERTO = _states.ESTADO_ABIERTO
ESTADO_CERRADO = _states.ESTADO_CERRADO
DEFAULT_EDITION = _states.DEFAULT_EDITION

TICKETS_TABLE = "laim_tickets"
MENSAJES_TABLE = "laim_ticket_mensajes"
EVENTOS_TABLE = "laim_ticket_eventos"
ESTADOS_TABLE = "laim_ticket_estados"
NOTIF_TABLE = "laim_ticket_notificaciones"
NOTIF_TIPOS = frozenset(
    {"ticket_created", "ticket_replied", "ticket_status", "ticket_reopened"}
)

_TICKET_COLUMNS = """
    t.id, t.id_estado, e.clave AS estado_clave, e.nombre AS estado_nombre,
    t.user_id, t.user_name, t.user_email, t.organization_id, t.edition,
    t.subject, t.body, t.opened_at, t.closed_at, t.updated_at
"""


class LaimTicketsRepository:
    """Persistencia de tickets, mensajes y eventos."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._logger = logging.getLogger("LaimTicketsRepository")

    def create_ticket(
        self,
        user_id: int,
        user_name: str,
        user_email: str,
        organization_id: int | None,
        edition: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        """Crea ticket + primer mensaje + evento created."""
        estado_id = ESTADO_CLAVE_TO_ID[ESTADO_ABIERTO]
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    INSERT INTO {TICKETS_TABLE} (
                        id_estado, user_id, user_name, user_email,
                        organization_id, edition, subject, body
                    ) VALUES (
                        :id_estado, :user_id, :user_name, :user_email,
                        :organization_id, :edition, :subject, :body
                    )
                    """
                ),
                {
                    "id_estado": estado_id,
                    "user_id": user_id,
                    "user_name": user_name,
                    "user_email": user_email,
                    "organization_id": organization_id,
                    "edition": edition or DEFAULT_EDITION,
                    "subject": subject,
                    "body": body,
                },
            )
            ticket_id = int(result.lastrowid)
            conn.execute(
                text(
                    f"""
                    INSERT INTO {MENSAJES_TABLE} (
                        ticket_id, autor, actor_name, cuerpo
                    ) VALUES (
                        :ticket_id, 'usuario', :actor_name, :cuerpo
                    )
                    """
                ),
                {
                    "ticket_id": ticket_id,
                    "actor_name": user_name,
                    "cuerpo": body,
                },
            )
            conn.execute(
                text(
                    f"""
                    INSERT INTO {EVENTOS_TABLE} (
                        ticket_id, tipo, estado_desde, estado_hasta, actor
                    ) VALUES (
                        :ticket_id, 'created', NULL, :estado_hasta, :actor
                    )
                    """
                ),
                {
                    "ticket_id": ticket_id,
                    "estado_hasta": estado_id,
                    "actor": user_name,
                },
            )
            row = self._fetch_ticket(conn, ticket_id)
        assert row is not None
        return row

    def list_tickets(
        self,
        user_id: int | None = None,
        estado_clave: str | None = None,
        query: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Lista tickets. Si user_id se informa, solo los de ese usuario."""
        clauses = ["1=1"]
        params: dict[str, Any] = {"limit": max(1, min(int(limit), 200))}
        if user_id is not None:
            clauses.append("t.user_id = :user_id")
            params["user_id"] = int(user_id)
        if estado_clave:
            estado_id = ESTADO_CLAVE_TO_ID.get(estado_clave.strip().lower())
            if estado_id is None:
                return []
            clauses.append("t.id_estado = :id_estado")
            params["id_estado"] = estado_id
        if query:
            clauses.append(
                "(t.subject LIKE :query OR t.user_name LIKE :query OR t.user_email LIKE :query)"
            )
            params["query"] = f"%{query.strip()}%"
        sql = f"""
            SELECT {_TICKET_COLUMNS}
            FROM {TICKETS_TABLE} t
            INNER JOIN {ESTADOS_TABLE} e ON e.id = t.id_estado
            WHERE {' AND '.join(clauses)}
            ORDER BY t.opened_at DESC, t.id DESC
            LIMIT :limit
        """
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().fetchall()
        return [dict(row) for row in rows]

    def get_ticket(self, ticket_id: int) -> dict[str, Any] | None:
        """Cabecera de un ticket."""
        with self._engine.connect() as conn:
            return self._fetch_ticket(conn, ticket_id)

    def list_messages(self, ticket_id: int) -> list[dict[str, Any]]:
        """Hilo público ordenado cronológicamente."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, ticket_id, autor, actor_name, cuerpo, created_at
                    FROM {MENSAJES_TABLE}
                    WHERE ticket_id = :ticket_id
                    ORDER BY created_at ASC, id ASC
                    """
                ),
                {"ticket_id": ticket_id},
            ).mappings().fetchall()
        return [dict(row) for row in rows]

    def list_events(self, ticket_id: int) -> list[dict[str, Any]]:
        """Eventos de sistema ordenados cronológicamente."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, ticket_id, tipo, estado_desde, estado_hasta, actor, created_at
                    FROM {EVENTOS_TABLE}
                    WHERE ticket_id = :ticket_id
                    ORDER BY created_at ASC, id ASC
                    """
                ),
                {"ticket_id": ticket_id},
            ).mappings().fetchall()
        out = []
        for row in rows:
            item = dict(row)
            if item.get("estado_desde"):
                item["estado_desde_clave"] = ESTADO_ID_TO_CLAVE.get(int(item["estado_desde"]))
            if item.get("estado_hasta"):
                item["estado_hasta_clave"] = ESTADO_ID_TO_CLAVE.get(int(item["estado_hasta"]))
            out.append(item)
        return out

    def add_message_and_maybe_state(
        self,
        ticket_id: int,
        autor: str,
        actor_name: str,
        cuerpo: str,
        new_estado_clave: str | None,
        event_tipo: str,
    ) -> dict[str, Any] | None:
        """Añade un mensaje público y, si cambia, el estado + evento."""
        with self._engine.begin() as conn:
            current = self._fetch_ticket(conn, ticket_id)
            if current is None:
                return None
            conn.execute(
                text(
                    f"""
                    INSERT INTO {MENSAJES_TABLE} (
                        ticket_id, autor, actor_name, cuerpo
                    ) VALUES (
                        :ticket_id, :autor, :actor_name, :cuerpo
                    )
                    """
                ),
                {
                    "ticket_id": ticket_id,
                    "autor": autor,
                    "actor_name": actor_name,
                    "cuerpo": cuerpo,
                },
            )
            from_id = int(current["id_estado"])
            to_id = from_id
            if new_estado_clave:
                to_id = ESTADO_CLAVE_TO_ID[new_estado_clave]
                self._apply_estado(conn, ticket_id, from_id, to_id)
            conn.execute(
                text(
                    f"""
                    INSERT INTO {EVENTOS_TABLE} (
                        ticket_id, tipo, estado_desde, estado_hasta, actor
                    ) VALUES (
                        :ticket_id, :tipo, :estado_desde, :estado_hasta, :actor
                    )
                    """
                ),
                {
                    "ticket_id": ticket_id,
                    "tipo": event_tipo,
                    "estado_desde": from_id,
                    "estado_hasta": to_id,
                    "actor": actor_name[:128],
                },
            )
            return self._fetch_ticket(conn, ticket_id)

    def change_estado(
        self,
        ticket_id: int,
        new_estado_clave: str,
        actor: str,
        event_tipo: str,
    ) -> dict[str, Any] | None:
        """Cambia el estado y registra evento (sin mensaje)."""
        to_id = ESTADO_CLAVE_TO_ID[new_estado_clave]
        with self._engine.begin() as conn:
            current = self._fetch_ticket(conn, ticket_id)
            if current is None:
                return None
            from_id = int(current["id_estado"])
            self._apply_estado(conn, ticket_id, from_id, to_id)
            conn.execute(
                text(
                    f"""
                    INSERT INTO {EVENTOS_TABLE} (
                        ticket_id, tipo, estado_desde, estado_hasta, actor
                    ) VALUES (
                        :ticket_id, :tipo, :estado_desde, :estado_hasta, :actor
                    )
                    """
                ),
                {
                    "ticket_id": ticket_id,
                    "tipo": event_tipo,
                    "estado_desde": from_id,
                    "estado_hasta": to_id,
                    "actor": (actor or "laim_maintenance")[:128],
                },
            )
            return self._fetch_ticket(conn, ticket_id)

    def count_by_estado(self) -> dict[str, int]:
        """Conteos del dashboard de operador."""
        counts = {clave: 0 for clave in ESTADO_CLAVE_TO_ID}
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT e.clave, COUNT(*) AS n
                    FROM {TICKETS_TABLE} t
                    INNER JOIN {ESTADOS_TABLE} e ON e.id = t.id_estado
                    GROUP BY e.clave
                    """
                )
            ).mappings().fetchall()
        total = 0
        for row in rows:
            clave = str(row["clave"])
            n = int(row["n"])
            counts[clave] = n
            total += n
        counts["total"] = total
        return counts

    def add_notification(
        self,
        ticket_id: int,
        destinatario: str,
        user_id: int | None,
        tipo: str,
    ) -> dict[str, Any]:
        """Inserta un aviso no leído para el otro lado del ticket."""
        if destinatario not in {"usuario", "operador"}:
            raise ValueError(f"destinatario desconocido: {destinatario!r}")
        if tipo not in NOTIF_TIPOS:
            raise ValueError(f"tipo de notificación desconocido: {tipo!r}")
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    INSERT INTO {NOTIF_TABLE} (
                        ticket_id, destinatario, user_id, tipo, leida
                    ) VALUES (
                        :ticket_id, :destinatario, :user_id, :tipo, 0
                    )
                    """
                ),
                {
                    "ticket_id": int(ticket_id),
                    "destinatario": destinatario,
                    "user_id": int(user_id) if user_id else None,
                    "tipo": tipo,
                },
            )
            return {
                "id": int(result.lastrowid),
                "ticket_id": int(ticket_id),
                "destinatario": destinatario,
                "user_id": int(user_id) if user_id else None,
                "tipo": tipo,
                "leida": 0,
            }

    def list_pending_notifications(
        self,
        destinatario: str,
        user_id: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Avisos no leídos. El poll no los marca leídos."""
        clauses = ["n.destinatario = :destinatario", "n.leida = 0"]
        params: dict[str, Any] = {
            "destinatario": destinatario,
            "limit": max(1, min(int(limit), 200)),
        }
        if destinatario == "usuario":
            clauses.append("n.user_id = :user_id")
            params["user_id"] = int(user_id or 0)
        sql = f"""
            SELECT n.id, n.ticket_id, n.destinatario, n.user_id, n.tipo,
                   n.leida, n.created_at, t.subject, e.clave AS estado_clave
            FROM {NOTIF_TABLE} n
            INNER JOIN {TICKETS_TABLE} t ON t.id = n.ticket_id
            INNER JOIN {ESTADOS_TABLE} e ON e.id = t.id_estado
            WHERE {' AND '.join(clauses)}
            ORDER BY n.created_at ASC, n.id ASC
            LIMIT :limit
        """
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().fetchall()
        return [dict(row) for row in rows]

    def ack_notification(
        self,
        notif_id: int,
        destinatario: str,
        user_id: int | None = None,
    ) -> bool:
        """Marca leída solo si pertenece al destinatario (y user_id si usuario)."""
        clauses = ["id = :id", "destinatario = :destinatario", "leida = 0"]
        params: dict[str, Any] = {
            "id": int(notif_id),
            "destinatario": destinatario,
        }
        if destinatario == "usuario":
            clauses.append("user_id = :user_id")
            params["user_id"] = int(user_id or 0)
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    UPDATE {NOTIF_TABLE}
                    SET leida = 1
                    WHERE {' AND '.join(clauses)}
                    """
                ),
                params,
            )
        return int(getattr(result, "rowcount", 0) or 0) > 0

    def _apply_estado(self, conn: Any, ticket_id: int, from_id: int, to_id: int) -> None:
        closed_at_sql = "NULL"
        if to_id == ESTADO_CLAVE_TO_ID[ESTADO_CERRADO]:
            closed_at_sql = "CURRENT_TIMESTAMP"
        elif from_id == ESTADO_CLAVE_TO_ID[ESTADO_CERRADO]:
            closed_at_sql = "NULL"
        conn.execute(
            text(
                f"""
                UPDATE {TICKETS_TABLE}
                SET id_estado = :id_estado, closed_at = {closed_at_sql}
                WHERE id = :ticket_id
                """
            ),
            {"id_estado": to_id, "ticket_id": ticket_id},
        )

    def _fetch_ticket(self, conn: Any, ticket_id: int) -> dict[str, Any] | None:
        row = conn.execute(
            text(
                f"""
                SELECT {_TICKET_COLUMNS}
                FROM {TICKETS_TABLE} t
                INNER JOIN {ESTADOS_TABLE} e ON e.id = t.id_estado
                WHERE t.id = :ticket_id
                """
            ),
            {"ticket_id": ticket_id},
        ).mappings().fetchone()
        return dict(row) if row else None

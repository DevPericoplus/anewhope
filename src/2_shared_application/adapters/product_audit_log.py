"""Auditoría de instalación/actualización de producto y plugins laim.

Persistencia real (laim_product_audit_log, migración 024) — ver
anewhope/AGENTS.md § 37.4. No hay todavía ningún endpoint real de
instalación/actualización que llame a esto (`/check_last_version` y la
descarga de parches siguen solo diseñados, ver AGENTS.md § 37) — este
módulo existe para que ese futuro endpoint solo tenga que llamar a
`record()`, no diseñar la persistencia desde cero.

Mismo patrón que ProductLicenseRepository / LaimMariaDbSessionRepository:
un engine inyectado, sin ORM.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

VALID_OPERATIONS = ("install", "update")
VALID_TARGET_TYPES = ("product", "plugin")
VALID_RESULTS = ("success", "failed")


class ProductAuditLogError(Exception):
    """Error de negocio al registrar una entrada de auditoría."""


@dataclass(frozen=True, slots=True)
class AuditEntry:
    audit_id: int
    serial_number: str
    owner_type: str
    owner_id: int
    operation: str
    target_type: str
    plugin_name: Optional[str]
    edition: str
    version_from: Optional[str]
    version_to: str
    platform: str
    result: str
    error_detail: Optional[str]
    occurred_at: datetime

    @classmethod
    def _from_row(cls, row: Any) -> "AuditEntry":
        occurred_at = row["occurred_at"]
        if isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(occurred_at)
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        return cls(
            audit_id=int(row["audit_id"]),
            serial_number=str(row["serial_number"]),
            owner_type=str(row["owner_type"]),
            owner_id=int(row["owner_id"]),
            operation=str(row["operation"]),
            target_type=str(row["target_type"]),
            plugin_name=row["plugin_name"],
            edition=str(row["edition"]),
            version_from=row["version_from"],
            version_to=str(row["version_to"]),
            platform=str(row["platform"]),
            result=str(row["result"]),
            error_detail=row["error_detail"],
            occurred_at=occurred_at,
        )


class ProductAuditLogRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def record(
        self,
        serial_number: str,
        owner_type: str,
        owner_id: int,
        operation: str,
        target_type: str,
        edition: str,
        version_to: str,
        platform: str,
        result: str,
        plugin_name: Optional[str] = None,
        version_from: Optional[str] = None,
        error_detail: Optional[str] = None,
    ) -> AuditEntry:
        """Registra una operación de instalación/actualización.

        Nunca lanza para "resultado malo" — un result="failed" es un
        registro válido, no una excepción; ProductAuditLogError es solo
        para parámetros mal formados (ediciones/operaciones inválidas), no
        para el resultado de la operación auditada.
        """
        if operation not in VALID_OPERATIONS:
            raise ProductAuditLogError(f"operation inválida: {operation!r}")
        if target_type not in VALID_TARGET_TYPES:
            raise ProductAuditLogError(f"target_type inválido: {target_type!r}")
        if result not in VALID_RESULTS:
            raise ProductAuditLogError(f"result inválido: {result!r}")
        if target_type == "plugin" and not plugin_name:
            raise ProductAuditLogError("plugin_name requerido cuando target_type='plugin'")
        if target_type == "product" and plugin_name:
            raise ProductAuditLogError("plugin_name no debe informarse cuando target_type='product'")

        with self._engine.begin() as conn:
            result_proxy = conn.execute(
                text(
                    """
                    INSERT INTO laim_product_audit_log
                        (serial_number, owner_type, owner_id, operation, target_type,
                         plugin_name, edition, version_from, version_to, platform,
                         result, error_detail)
                    VALUES
                        (:serial_number, :owner_type, :owner_id, :operation, :target_type,
                         :plugin_name, :edition, :version_from, :version_to, :platform,
                         :result, :error_detail)
                    """
                ),
                {
                    "serial_number": serial_number,
                    "owner_type": owner_type,
                    "owner_id": owner_id,
                    "operation": operation,
                    "target_type": target_type,
                    "plugin_name": plugin_name,
                    "edition": edition,
                    "version_from": version_from,
                    "version_to": version_to,
                    "platform": platform,
                    "result": result,
                    "error_detail": error_detail,
                },
            )
            audit_id = result_proxy.lastrowid

        row = self._get_by_id(audit_id)
        assert row is not None  # acabamos de insertarla
        return row

    def _get_by_id(self, audit_id: int) -> Optional[AuditEntry]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM laim_product_audit_log WHERE audit_id = :audit_id"),
                {"audit_id": audit_id},
            ).mappings().fetchone()
        return AuditEntry._from_row(row) if row is not None else None

    def list_for_serial(self, serial_number: str, limit: int = 100) -> tuple[AuditEntry, ...]:
        """Historial de un serial concreto — para "hacerles seguimiento", tal y como pidió el usuario."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT * FROM laim_product_audit_log
                    WHERE serial_number = :serial_number
                    ORDER BY occurred_at DESC
                    LIMIT :limit
                    """
                ),
                {"serial_number": serial_number, "limit": limit},
            ).mappings().fetchall()
        return tuple(AuditEntry._from_row(row) for row in rows)

    def counts_by_edition_result(self) -> tuple[dict[str, Any], ...]:
        """Agregación base para el futuro cuadro de mando (§ 37.4) — conteo
        por edición/operación/resultado. Un primer bloque, no el diseño
        final del dashboard, que sigue sin hacerse."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT edition, operation, result, COUNT(*) AS total
                    FROM laim_product_audit_log
                    GROUP BY edition, operation, result
                    ORDER BY edition, operation, result
                    """
                )
            ).mappings().fetchall()
        return tuple(dict(row) for row in rows)

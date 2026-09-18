"""Entidades de dominio y persistencia para registro de licencias de producto laim.

Cubre el flujo descrito en laim_maintenance/README.md § Fase 2: cada
instalación de laim genera un número de serie (`laim init`, ver
laim/internal/utils/serial.go), que el usuario registra aquí desde laimweb.
community_edition es gratuita — un serial nuevo se marca "FREE" de inmediato.
advance es de pago; un serial registrado para advance queda "PENDING" hasta
que el flujo de pago (todavía sin diseñar, ver anewhope/AGENTS.md § 37.5) lo
active con una vigencia (fecha_inicio/fecha_fin).

Persistencia real en MariaDB (`laim_product_licenses` +
`laim_product_license_plugins`, migración 023) — sustituye al mock JSON
original. Sin llamadores en el repo cuando se hizo el cambio, así que no hay
integración existente que romper; ver anewhope/AGENTS.md § 37.5 para el
contexto completo del diseño de vigencia y el modelo SaaS futuro (renovación
selectiva por-plugin, prorrateo) que esta tabla deja abierto sin implementar.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

VALID_EDITIONS = ("community_edition", "advance")
STATUS_FREE = "FREE"
STATUS_PENDING = "PENDING"
STATUS_ACTIVE = "ACTIVE"
STATUS_EXPIRED = "EXPIRED"
STATUS_CANCELLED = "CANCELLED"


class ProductLicenseError(Exception):
    """Error de negocio al registrar/consultar una licencia de producto."""


@dataclass(frozen=True, slots=True)
class PluginEntitlement:
    """Vigencia de un plugin advance concreto, independiente del core.

    Permite exactamente el caso descrito por el usuario: un core advance
    vigente con solo un subconjunto de sus plugins advance también vigentes,
    cada uno con su propia fecha_fin.
    """

    plugin_name: str
    fecha_inicio: datetime
    fecha_fin: datetime

    @classmethod
    def from_row(cls, row: Any) -> "PluginEntitlement":
        return cls(
            plugin_name=str(row["plugin_name"]),
            fecha_inicio=_ensure_utc(row["fecha_inicio"]),
            fecha_fin=_ensure_utc(row["fecha_fin"]),
        )

    def is_active(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return self.fecha_inicio <= now <= self.fecha_fin


@dataclass(frozen=True, slots=True)
class ProductLicense:
    """Representa el registro de un serial de instalación de laim.

    owner_type es "user" u "organization"; owner_id es el id correspondiente
    en cada caso (una organización puede agrupar varias licencias, cada una
    con su propio serial).

    fecha_inicio/fecha_fin son la vigencia de "advance" en el core del
    producto — None en community_edition, no aplica. laimweb es la fuente de
    verdad de esta vigencia (is_advance_active la evalúa contra "now" real,
    server-side); los campos equivalentes que se persisten en identity.dat
    del lado laim son solo para UX local, nunca el punto de aplicación real
    — ver laim/AGENTS.md § Sistema de actualización.
    """

    license_id: int
    serial_number: str
    edition: str
    status: str
    owner_type: str
    owner_id: int
    fecha_inicio: Optional[datetime]
    fecha_fin: Optional[datetime]
    registered_at: datetime
    plugins: tuple[PluginEntitlement, ...] = ()

    def is_advance_active(self, now: Optional[datetime] = None) -> bool:
        """True si el core advance está vigente ahora mismo.

        Tras fecha_fin sin renovación, se comporta como community_edition —
        el registro se conserva (status EXPIRED), no se borra ni se oculta.
        """
        if self.edition != "advance" or self.status != STATUS_ACTIVE:
            return False
        if self.fecha_inicio is None or self.fecha_fin is None:
            return False
        now = now or datetime.now(timezone.utc)
        return self.fecha_inicio <= now <= self.fecha_fin

    def active_plugin_names(self, now: Optional[datetime] = None) -> tuple[str, ...]:
        """Plugins advance vigentes ahora mismo, independientes de si el core lo está."""
        now = now or datetime.now(timezone.utc)
        return tuple(p.plugin_name for p in self.plugins if p.is_active(now))

    @classmethod
    def _from_row(cls, row: Any, plugins: tuple[PluginEntitlement, ...] = ()) -> "ProductLicense":
        return cls(
            license_id=int(row["license_id"]),
            serial_number=str(row["serial_number"]),
            edition=str(row["edition"]),
            status=str(row["status"]),
            owner_type=str(row["owner_type"]),
            owner_id=int(row["owner_id"]),
            fecha_inicio=_ensure_utc(row["fecha_inicio"]) if row["fecha_inicio"] else None,
            fecha_fin=_ensure_utc(row["fecha_fin"]) if row["fecha_fin"] else None,
            registered_at=_ensure_utc(row["registered_at"]),
            plugins=plugins,
        )


def _ensure_utc(value: Any) -> datetime:
    """Normaliza a datetime UTC. Acepta tanto datetime (PyMySQL/MariaDB, el
    caso real) como str ISO 8601 (algunos drivers/columnas SQLite en tests
    no deserializan TIMESTAMP a datetime automáticamente) — no asumir un
    único tipo de retorno del driver."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ProductLicenseRepository:
    """Persistencia MariaDB para ProductLicense — mismo patrón que
    LaimMariaDbSessionRepository (2_shared_application/adapters), un engine
    inyectado, sin ORM."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_by_serial(self, serial_number: str) -> Optional[ProductLicense]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT license_id, serial_number, edition, status, owner_type,
                           owner_id, fecha_inicio, fecha_fin, registered_at
                    FROM laim_product_licenses
                    WHERE serial_number = :serial_number
                    """
                ),
                {"serial_number": serial_number},
            ).mappings().fetchone()
        if row is None:
            return None
        return ProductLicense._from_row(row, self._plugins_for(row["license_id"]))

    def list_for_owner(self, owner_type: str, owner_id: int) -> tuple[ProductLicense, ...]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT license_id, serial_number, edition, status, owner_type,
                           owner_id, fecha_inicio, fecha_fin, registered_at
                    FROM laim_product_licenses
                    WHERE owner_type = :owner_type AND owner_id = :owner_id
                    """
                ),
                {"owner_type": owner_type, "owner_id": owner_id},
            ).mappings().fetchall()
        return tuple(
            ProductLicense._from_row(row, self._plugins_for(row["license_id"]))
            for row in rows
        )

    def register(
        self,
        serial_number: str,
        edition: str,
        owner_type: str,
        owner_id: int,
    ) -> ProductLicense:
        """Registra un serial nuevo.

        community_edition -> status FREE de inmediato. advance -> status
        PENDING (el proceso de cobro está pendiente de diseñar; esta función
        no lo asume — solo dejar el registro a la espera). Un serial ya
        registrado no puede volver a registrarse — rechazo explícito, no
        silencio.
        """
        serial_number = serial_number.strip()
        if not serial_number:
            raise ProductLicenseError("El número de serie no puede estar vacío.")
        if edition not in VALID_EDITIONS:
            raise ProductLicenseError(f"Edición inválida: {edition!r} (válidas: {VALID_EDITIONS}).")
        if owner_type not in ("user", "organization"):
            raise ProductLicenseError(f"owner_type inválido: {owner_type!r}.")
        if self.get_by_serial(serial_number) is not None:
            raise ProductLicenseError(f"El serial {serial_number!r} ya está registrado.")

        status = STATUS_FREE if edition == "community_edition" else STATUS_PENDING
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_product_licenses
                        (serial_number, edition, status, owner_type, owner_id)
                    VALUES
                        (:serial_number, :edition, :status, :owner_type, :owner_id)
                    """
                ),
                {
                    "serial_number": serial_number,
                    "edition": edition,
                    "status": status,
                    "owner_type": owner_type,
                    "owner_id": owner_id,
                },
            )

        logger.info(
            "Licencia registrada: serial=%s edition=%s status=%s",
            serial_number, edition, status,
        )
        license_ = self.get_by_serial(serial_number)
        assert license_ is not None  # acabamos de insertarla
        return license_

    def _plugins_for(self, license_id: int) -> tuple[PluginEntitlement, ...]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT plugin_name, fecha_inicio, fecha_fin
                    FROM laim_product_license_plugins
                    WHERE license_id = :license_id
                    """
                ),
                {"license_id": license_id},
            ).mappings().fetchall()
        return tuple(PluginEntitlement.from_row(row) for row in rows)

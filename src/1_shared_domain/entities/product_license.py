"""Entidades de dominio y funciones para registro de licencias de producto laim.

Cubre el flujo descrito en laim_maintenance/README.md § Fase 2: cada
instalación de laim genera un número de serie (`laim init`, ver
laim/internal/utils/serial.go), que el usuario registra aquí desde laimweb.
community_edition es gratuita — un serial nuevo se marca "FREE" de inmediato.
advance es de pago y su proceso de cobro está pendiente de diseñar — un
serial registrado para advance queda "PENDING" sin más lógica todavía (la UI
de laimweb no ofrece ni siquiera el formulario, solo un aviso "En
construcción").

Mismo estilo de persistencia mock que organization.py (fichero JSON bajo
2_shared_application/moks/) — no hay todavía una tabla/migración real
definida para licencias; sustituir por persistencia real es un paso futuro
explícito, no algo que este módulo deba adivinar.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

VALID_EDITIONS = ("community_edition", "advance")
STATUS_FREE = "FREE"
STATUS_PENDING = "PENDING"


class ProductLicenseError(Exception):
    """Error de negocio al registrar/consultar una licencia de producto."""


@dataclass(frozen=True, slots=True)
class ProductLicense:
    """Representa el registro de un serial de instalación de laim.

    owner_type es "user" u "organization"; owner_id es el id correspondiente
    en cada caso (permite que una organización agrupe varias licencias,
    cada una con su propio serial, tal y como pidió el usuario).
    """

    serial_number: str
    edition: str
    status: str
    owner_type: str
    owner_id: int
    registered_at: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProductLicense":
        return cls(
            serial_number=str(data.get("serial_number", "")),
            edition=str(data.get("edition", "")),
            status=str(data.get("status", "")),
            owner_type=str(data.get("owner_type", "user")),
            owner_id=int(data.get("owner_id", 0)),
            registered_at=str(data.get("registered_at", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "serial_number": self.serial_number,
            "edition": self.edition,
            "status": self.status,
            "owner_type": self.owner_type,
            "owner_id": self.owner_id,
            "registered_at": self.registered_at,
        }


def _get_licenses_file_path() -> Path:
    """Ruta al fichero JSON de licencias (datos mock)."""
    return Path(__file__).parent.parent.parent / "2_shared_application" / "moks" / "product_licenses.json"


def _load_licenses() -> list[dict[str, Any]]:
    data_file = _get_licenses_file_path()
    if not data_file.exists():
        return []
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error al cargar licencias desde {data_file}: {e}")
        return []


def _save_licenses(licenses: list[dict[str, Any]]) -> None:
    data_file = _get_licenses_file_path()
    data_file.parent.mkdir(parents=True, exist_ok=True)
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(licenses, f, indent=2, ensure_ascii=False)


def get_license_by_serial(serial_number: str) -> Optional[ProductLicense]:
    """Busca una licencia ya registrada por su número de serie."""
    for entry in _load_licenses():
        if entry.get("serial_number") == serial_number:
            return ProductLicense.from_dict(entry)
    return None


def register_license(
    serial_number: str,
    edition: str,
    owner_type: str,
    owner_id: int,
    registered_at: str,
) -> ProductLicense:
    """Registra un serial nuevo.

    community_edition -> status FREE de inmediato (gratuita).
    advance -> status PENDING (de pago; el proceso de cobro está pendiente de
    diseñar, ver laim/AGENTS.md § Modalidades de producto). No hay
    formulario real en laimweb para este caso todavía — esta función existe
    para cuando lo haya, no para ser invocada desde advance hoy.

    Un serial ya registrado no puede volver a registrarse (ni siquiera por
    el mismo propietario) — es idempotente por rechazo, no por silencio.
    """
    serial_number = serial_number.strip()
    if not serial_number:
        raise ProductLicenseError("El número de serie no puede estar vacío.")
    if edition not in VALID_EDITIONS:
        raise ProductLicenseError(f"Edición inválida: {edition!r} (válidas: {VALID_EDITIONS}).")
    if owner_type not in ("user", "organization"):
        raise ProductLicenseError(f"owner_type inválido: {owner_type!r}.")

    if get_license_by_serial(serial_number) is not None:
        raise ProductLicenseError(f"El serial {serial_number!r} ya está registrado.")

    status = STATUS_FREE if edition == "community_edition" else STATUS_PENDING
    license_ = ProductLicense(
        serial_number=serial_number,
        edition=edition,
        status=status,
        owner_type=owner_type,
        owner_id=owner_id,
        registered_at=registered_at,
    )

    licenses = _load_licenses()
    licenses.append(license_.to_dict())
    _save_licenses(licenses)

    logger.info(f"Licencia registrada: serial={serial_number} edition={edition} status={status}")
    return license_


def list_licenses_for_owner(owner_type: str, owner_id: int) -> list[ProductLicense]:
    """Lista las licencias de un usuario o de una organización (varias licencias por organización)."""
    return [
        ProductLicense.from_dict(entry)
        for entry in _load_licenses()
        if entry.get("owner_type") == owner_type and int(entry.get("owner_id", 0)) == owner_id
    ]

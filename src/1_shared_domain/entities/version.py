"""Entidad de dominio para versiones de proyecto."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class VersionStatus(str, Enum):
    """Estados válidos de una versión de proyecto."""

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED_CLIENT = "approved_client"
    APPROVED_MYLLM = "approved_myllm"
    READY_FOR_TRAINING = "ready_for_training"
    TRAINING = "training"
    TRAINED = "trained"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class Version:
    """
    Representa una versión dentro de un proyecto.
    
    Las versiones contienen snapshots de la estructura de archivos
    y configuraciones que se usan para entrenar modelos LLM.
    Cada versión tiene un estado que indica su posición en el
    flujo de aprobación y entrenamiento.
    
    Nomenclatura:
        - V001, V002, etc. para versiones regulares
        - VC01, VC02, etc. para versiones candidatas
    
    Relaciones:
        - Pertenece a un Project (project_id)
        - Creada por un User (created_by_user_id)
        - Puede ser aprobada por cliente y por myllm (approved_by_*)
    """

    version_id: int
    project_id: int
    version_name: str
    version_description: str
    status: VersionStatus
    created_by_user_id: int
    approved_by_client_user_id: int | None
    approved_by_myllm_user_id: int | None
    storage_path: str
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        """Valida los campos después de la inicialización."""
        _require_positive_int(self.version_id, "version_id")
        _require_positive_int(self.project_id, "project_id")
        _require_non_empty_str(self.version_name, "version_name")
        _require_positive_int(self.created_by_user_id, "created_by_user_id")
        if not isinstance(self.status, VersionStatus):
            raise ValueError("status debe ser VersionStatus")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Version":
        """Crea una versión desde un diccionario de datos."""

        return cls(
            version_id=_require_mapping_int(data, "version_id"),
            project_id=_require_mapping_int(data, "project_id"),
            version_name=_require_mapping_str(data, "version_name"),
            version_description=data.get("version_description", ""),
            status=VersionStatus(data.get("status", "draft")),
            created_by_user_id=_require_mapping_int(data, "created_by_user_id"),
            approved_by_client_user_id=data.get("approved_by_client_user_id"),
            approved_by_myllm_user_id=data.get("approved_by_myllm_user_id"),
            storage_path=data.get("storage_path", ""),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convierte la versión a diccionario serializable."""

        return {
            "version_id": self.version_id,
            "project_id": self.project_id,
            "version_name": self.version_name,
            "version_description": self.version_description,
            "status": self.status.value,
            "created_by_user_id": self.created_by_user_id,
            "approved_by_client_user_id": self.approved_by_client_user_id,
            "approved_by_myllm_user_id": self.approved_by_myllm_user_id,
            "storage_path": self.storage_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def is_approved_by_client(self) -> bool:
        """Indica si la versión fue aprobada por el cliente."""
        return self.approved_by_client_user_id is not None

    def is_approved_by_myllm(self) -> bool:
        """Indica si la versión fue aprobada por myllm."""
        return self.approved_by_myllm_user_id is not None

    def is_ready_for_training(self) -> bool:
        """Indica si la versión está lista para entrenar."""
        return self.status == VersionStatus.READY_FOR_TRAINING

    def can_be_modified(self) -> bool:
        """Indica si la versión puede ser modificada."""
        return self.status in (VersionStatus.DRAFT, VersionStatus.IN_REVIEW)

    def can_start_training(self) -> bool:
        """Indica si se puede iniciar el entrenamiento."""
        return (
            self.is_approved_by_client()
            and self.is_approved_by_myllm()
            and self.status == VersionStatus.READY_FOR_TRAINING
        )


class Versions:
    """Contenedor de versiones, independiente del origen de datos."""

    def __init__(self, items: list[Version]) -> None:
        self._items = tuple(items)

    @property
    def items(self) -> tuple[Version, ...]:
        """Retorna las versiones en memoria."""
        return self._items

    def get_by_id(self, version_id: int) -> Version | None:
        """Obtiene una versión por su ID."""
        for version in self._items:
            if version.version_id == version_id:
                return version
        return None

    def filter_by_project(self, project_id: int) -> tuple[Version, ...]:
        """Retorna versiones de un proyecto específico."""
        return tuple(
            version
            for version in self._items
            if version.project_id == project_id
        )

    def get_latest_by_project(self, project_id: int) -> Version | None:
        """Obtiene la versión más reciente de un proyecto."""
        project_versions = self.filter_by_project(project_id)
        if not project_versions:
            return None
        return max(project_versions, key=lambda v: v.version_id)

    def filter_ready_for_training(self) -> tuple[Version, ...]:
        """Retorna versiones listas para entrenar."""
        return tuple(
            version
            for version in self._items
            if version.is_ready_for_training()
        )

    @classmethod
    def from_records(cls, records: list[Mapping[str, Any]]) -> "Versions":
        """Construye el contenedor desde registros externos."""
        return cls([Version.from_dict(record) for record in records])


# === Funciones auxiliares de validación ===

def _require_positive_int(value: Any, field_name: str) -> None:
    """Valida que el valor sea un entero positivo."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"'{field_name}' debe ser un entero")
    if value <= 0:
        raise ValueError(f"'{field_name}' debe ser positivo")


def _require_non_empty_str(value: Any, field_name: str) -> None:
    """Valida que el valor sea un string no vacío."""
    if not isinstance(value, str):
        raise ValueError(f"'{field_name}' debe ser un string")
    if not value.strip():
        raise ValueError(f"'{field_name}' no puede estar vacío")


def _require_mapping_int(data: Mapping[str, Any], key: str) -> int:
    """Obtiene un entero obligatorio desde un mapeo."""
    if key not in data:
        raise ValueError(f"falta la clave '{key}'")
    value = data[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"'{key}' debe ser un entero")
    return value


def _require_mapping_str(data: Mapping[str, Any], key: str) -> str:
    """Obtiene un string obligatorio desde un mapeo."""
    if key not in data:
        raise ValueError(f"falta la clave '{key}'")
    value = data[key]
    if not isinstance(value, str):
        raise ValueError(f"'{key}' debe ser un string")
    return value


def _now_iso() -> str:
    """Retorna la fecha/hora actual en formato ISO."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

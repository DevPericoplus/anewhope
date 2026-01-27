"""Entidad de dominio para proyectos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class ProjectStatus(str, Enum):
    """Estados válidos de un proyecto."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class Project:
    """
    Representa un proyecto dentro de una organización.
    
    El proyecto es el contenedor principal donde se almacenan
    versiones, archivos y configuraciones para el entrenamiento
    de modelos LLM.
    
    Relaciones:
        - Pertenece a una Organization (organization_id)
        - Contiene múltiples Version
        - Creado por un User (created_by_user_id)
    """

    project_id: int
    organization_id: int
    project_name: str
    project_description: str
    created_by_user_id: int
    status: ProjectStatus
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        """Valida los campos después de la inicialización."""
        _require_positive_int(self.project_id, "project_id")
        _require_positive_int(self.organization_id, "organization_id")
        _require_non_empty_str(self.project_name, "project_name")
        _require_positive_int(self.created_by_user_id, "created_by_user_id")
        if not isinstance(self.status, ProjectStatus):
            raise ValueError("status debe ser ProjectStatus")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Project":
        """Crea un proyecto desde un diccionario de datos."""

        return cls(
            project_id=_require_mapping_int(data, "project_id"),
            organization_id=_require_mapping_int(data, "organization_id"),
            project_name=_require_mapping_str(data, "project_name"),
            project_description=data.get("project_description", ""),
            created_by_user_id=_require_mapping_int(data, "created_by_user_id"),
            status=ProjectStatus(data.get("status", "draft")),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convierte el proyecto a diccionario serializable."""

        return {
            "project_id": self.project_id,
            "organization_id": self.organization_id,
            "project_name": self.project_name,
            "project_description": self.project_description,
            "created_by_user_id": self.created_by_user_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def is_active(self) -> bool:
        """Indica si el proyecto está activo."""
        return self.status == ProjectStatus.ACTIVE

    def can_create_version(self) -> bool:
        """Indica si se pueden crear versiones en el proyecto."""
        return self.status in (ProjectStatus.DRAFT, ProjectStatus.ACTIVE)


class Projects:
    """Contenedor de proyectos, independiente del origen de datos."""

    def __init__(self, items: list[Project]) -> None:
        self._items = tuple(items)

    @property
    def items(self) -> tuple[Project, ...]:
        """Retorna los proyectos en memoria."""
        return self._items

    def get_by_id(self, project_id: int) -> Project | None:
        """Obtiene un proyecto por su ID."""
        for project in self._items:
            if project.project_id == project_id:
                return project
        return None

    def filter_by_organization(self, organization_id: int) -> tuple[Project, ...]:
        """Retorna proyectos de una organización específica."""
        return tuple(
            project
            for project in self._items
            if project.organization_id == organization_id
        )

    def filter_by_user(self, user_id: int) -> tuple[Project, ...]:
        """Retorna proyectos creados por un usuario específico."""
        return tuple(
            project
            for project in self._items
            if project.created_by_user_id == user_id
        )

    @classmethod
    def from_records(cls, records: list[Mapping[str, Any]]) -> "Projects":
        """Construye el contenedor desde registros externos."""
        return cls([Project.from_dict(record) for record in records])


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

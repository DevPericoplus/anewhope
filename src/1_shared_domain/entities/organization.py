"""Entidades de dominio y funciones para gestión de organizaciones."""

from __future__ import annotations

import json
import logging
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Entidades de dominio
# ============================================================================


@dataclass(frozen=True, slots=True)
class Organization:
    """Representa una organización en el sistema.

    Es la unidad principal de agrupación de usuarios, proyectos y versiones.
    Los usuarios internos (backoffice) acceden a organizaciones a través
    de asignaciones en ``asignaciones_organizaciones_internas``.
    """

    organization_id: int
    organization_name: str
    active: bool = True

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Organization":
        """Crea una Organization desde un diccionario."""
        return cls(
            organization_id=int(data.get("organization_id", 0)),
            organization_name=str(data.get("organization_name", "")),
            active=bool(data.get("active", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convierte la entidad a diccionario."""
        return {
            "organization_id": self.organization_id,
            "organization_name": self.organization_name,
            "active": self.active,
        }


@dataclass(frozen=True, slots=True)
class OrganizationAccess:
    """Value Object: acceso de un usuario interno a una organización.

    Representa la relación entre un usuario interno y una organización
    otorgada en la página de Asignaciones del backoffice.
    """

    organization_id: int
    organization_name: str
    role_id: int = 0
    role_name: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OrganizationAccess":
        """Crea un OrganizationAccess desde un diccionario."""
        return cls(
            organization_id=int(data.get("organization_id", 0)),
            organization_name=str(data.get("organization_name", "")),
            role_id=int(data.get("role_id", 0)),
            role_name=str(data.get("role_name", "")),
        )

    def to_selector_dict(self) -> dict[str, Any]:
        """Formato simplificado para selectores de UI (id + name)."""
        return {
            "id": self.organization_id,
            "name": self.organization_name,
        }


@dataclass(frozen=True, slots=True)
class ProjectAccess:
    """Value Object: acceso de un usuario interno a un proyecto.

    Representa la relación entre un usuario interno y un proyecto
    otorgada en la página de Asignaciones del backoffice.
    """

    project_id: int
    project_name: str
    organization_id: int = 0
    role_id: int = 0
    role_name: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProjectAccess":
        """Crea un ProjectAccess desde un diccionario."""
        return cls(
            project_id=int(data.get("project_id", 0)),
            project_name=str(data.get("project_name", "")),
            organization_id=int(data.get("organization_id", 0)),
            role_id=int(data.get("role_id", 0)),
            role_name=str(data.get("role_name", "")),
        )

    def to_selector_dict(self) -> dict[str, Any]:
        """Formato simplificado para selectores de UI (id + name)."""
        return {
            "id": self.project_id,
            "name": self.project_name,
        }


# ============================================================================
# Funciones legacy (mantenidas para compatibilidad con frontend)
# ============================================================================


def _normalize_text(text: str) -> str:
    """
    Normaliza un texto eliminando acentos y convirtiendo a minúsculas.

    Args:
        text: Texto a normalizar.

    Returns:
        Texto normalizado sin acentos y en minúsculas.
    """
    text = text.strip().lower()
    # Descomponer Unicode para que los acentos sean codepoints separados, luego eliminar caracteres combinantes
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return text


def _get_organizations_file_path() -> Path:
    """
    Obtiene la ruta del archivo JSON de organizaciones (datos mock).

    Returns:
        Ruta al archivo organizations.json.
    """
    return Path(__file__).parent.parent.parent / "2_shared_application" / "moks" / "organizations.json"


def _load_organizations() -> list[dict[str, Any]]:
    """
    Carga las organizaciones desde el archivo JSON.

    Returns:
        Lista de organizaciones como diccionarios.
    """
    data_file = _get_organizations_file_path()
    if not data_file.exists():
        logger.warning(f"El archivo de organizaciones no existe: {data_file}")
        return []

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error al cargar organizaciones desde {data_file}: {e}")
        return []


def get_organization_by_name_exist(organization_name: str) -> bool:
    """
    Verifica si existe una organización con el nombre dado.

    La comparación ignora mayúsculas/minúsculas y también ignora diacríticos
    (vocales acentuadas, etc.).

    Args:
        organization_name: Nombre de la organización a verificar.

    Returns:
        True si la organización existe, False en caso contrario.
    """
    orgs = _load_organizations()
    if not orgs:
        return False

    normalized_input = _normalize_text(organization_name)
    for org in orgs:
        org_name = org.get("organization_name", "")
        if _normalize_text(org_name) == normalized_input:
            return True
    return False


def create_organization(organization: Any) -> bool:
    """
    Crea una nueva entrada de organización en el archivo organizations.json.

    Asigna un organization_id único y secuencial.

    Args:
        organization: Objeto Organization a agregar. Debe tener organization_id=None.

    Returns:
        True si la creación fue exitosa, False en caso contrario.
    """
    data_file = _get_organizations_file_path()
    orgs = _load_organizations()

    # Determinar el siguiente organization_id
    if orgs:
        existing_ids = [
            org.get("organization_id", 0)
            for org in orgs
            if isinstance(org.get("organization_id"), int)
        ]
        next_id = max(existing_ids, default=0) + 1
    else:
        next_id = 1

    # Construir diccionario de nueva organización
    org_dict = {
        "organization_id": next_id,
        "organization_name": getattr(organization, "_organization_name", None)
        or getattr(organization, "organization_name", None),
        "organization_email": getattr(organization, "_organization_email", None)
        or getattr(organization, "organization_email", None),
        "organization_tlf": getattr(organization, "_organization_tlf", None)
        or getattr(organization, "organization_tlf", None),
        "organization_address": getattr(organization, "_organization_address", None)
        or getattr(organization, "organization_address", None),
        "organization_country": getattr(organization, "_organization_country", None)
        or getattr(organization, "organization_country", None),
        "organization_state": getattr(organization, "_organization_state", None)
        or getattr(organization, "organization_state", None),
    }

    # Reemplazar o establecer el id en el objeto organization si es posible
    if hasattr(organization, "_organization_id"):
        setattr(organization, "_organization_id", next_id)
    elif hasattr(organization, "organization_id"):
        setattr(organization, "organization_id", next_id)

    orgs.append(org_dict)
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(orgs, f, indent=2, ensure_ascii=False)
        logger.info(f"Organización creada exitosamente con ID: {next_id}")
        return True
    except (OSError, json.JSONEncodeError) as e:
        logger.error(f"Error al guardar organización en {data_file}: {e}")
        return False

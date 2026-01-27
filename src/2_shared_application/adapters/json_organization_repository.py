"""
Implementación del repositorio de organizaciones usando JSON como almacenamiento.

Este adaptador implementa el contrato OrganizationRepository definido en interfaces/
y proporciona acceso a datos de organizaciones desde el archivo organizations.json.

Nota: Este módulo reemplaza las funciones que estaban en
1_shared_domain/entities/organization.py, siguiendo el principio de
separación de responsabilidades de Clean Architecture.
"""

from __future__ import annotations

import json
import logging
import unicodedata
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JsonOrganizationRepository:
    """
    Implementación del repositorio de organizaciones usando JSON.
    
    Este adaptador implementa el contrato OrganizationRepository y proporciona
    métodos para acceder y modificar organizaciones almacenadas en organizations.json.
    
    Attributes:
        _data_path: Ruta al archivo organizations.json
    """
    
    def __init__(self, data_path: Path | None = None) -> None:
        """
        Inicializa el repositorio.
        
        Args:
            data_path: Ruta al archivo JSON. Si es None, usa la ruta por defecto.
        """
        self._data_path = data_path or self._get_default_path()
        self._logger = logging.getLogger("json_organization_repository")
    
    def _get_default_path(self) -> Path:
        """Obtiene la ruta por defecto del archivo de organizaciones."""
        return Path(__file__).resolve().parents[1] / "moks/organizations.json"
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza texto eliminando acentos y convirtiendo a minúsculas."""
        text = text.strip().lower()
        text = "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
        return text
    
    def _load_organizations(self) -> list[dict[str, Any]]:
        """Carga las organizaciones desde el archivo JSON."""
        if not self._data_path.exists():
            self._logger.warning(
                f"El archivo de organizaciones no existe: {self._data_path}"
            )
            return []
        
        try:
            with self._data_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            self._logger.error(
                f"Error al cargar organizaciones desde {self._data_path}: {e}"
            )
            return []
    
    def _save_organizations(self, organizations: list[dict[str, Any]]) -> bool:
        """Guarda las organizaciones en el archivo JSON."""
        try:
            self._data_path.parent.mkdir(parents=True, exist_ok=True)
            with self._data_path.open("w", encoding="utf-8") as f:
                json.dump(organizations, f, indent=2, ensure_ascii=False)
            return True
        except (OSError, TypeError, ValueError) as e:
            self._logger.error(
                f"Error al guardar organizaciones en {self._data_path}: {e}"
            )
            return False
    
    # === Métodos del contrato OrganizationRepository ===
    
    def get_by_id(self, organization_id: int) -> dict[str, Any] | None:
        """Obtiene una organización por su identificador."""
        organizations = self._load_organizations()
        for org in organizations:
            if org.get("organization_id") == organization_id:
                return org
        return None
    
    def get_by_name(self, organization_name: str) -> dict[str, Any] | None:
        """Obtiene una organización por su nombre."""
        organizations = self._load_organizations()
        if not organizations:
            return None
        
        normalized_input = self._normalize_text(organization_name)
        for org in organizations:
            org_name = org.get("organization_name", "")
            if self._normalize_text(org_name) == normalized_input:
                return org
        return None
    
    def exists_by_name(self, organization_name: str) -> bool:
        """Verifica si existe una organización por nombre."""
        return self.get_by_name(organization_name) is not None
    
    def save(self, organization_data: dict[str, Any]) -> dict[str, Any] | None:
        """Crea o actualiza una organización."""
        organizations = self._load_organizations()
        org_id = organization_data.get("organization_id")
        
        if org_id:
            # Actualizar organización existente
            for i, org in enumerate(organizations):
                if org.get("organization_id") == org_id:
                    organizations[i] = {**org, **organization_data}
                    break
            else:
                # No encontrado, agregar como nuevo
                organizations.append(organization_data)
        else:
            # Nueva organización, asignar ID
            existing_ids = [
                o.get("organization_id", 0)
                for o in organizations
                if isinstance(o.get("organization_id"), int)
            ]
            next_id = max(existing_ids, default=0) + 1
            organization_data["organization_id"] = next_id
            organizations.append(organization_data)
        
        if self._save_organizations(organizations):
            self._logger.info(
                f"Organización guardada con ID: {organization_data.get('organization_id')}"
            )
            return organization_data
        return None
    
    def get_all(self) -> list[dict[str, Any]]:
        """Obtiene todas las organizaciones."""
        return self._load_organizations()
    
    def count(self) -> int:
        """Retorna el número total de organizaciones."""
        return len(self._load_organizations())
    
    def delete(self, organization_id: int) -> bool:
        """Elimina una organización por su identificador."""
        organizations = self._load_organizations()
        original_count = len(organizations)
        organizations = [
            o for o in organizations
            if o.get("organization_id") != organization_id
        ]
        
        if len(organizations) == original_count:
            return False  # No se encontró la organización
        
        return self._save_organizations(organizations)

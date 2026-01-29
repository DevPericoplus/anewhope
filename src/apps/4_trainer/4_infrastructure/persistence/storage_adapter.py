"""Adaptadores de persistencia para backend IA (trainer)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _load_storage_structure_module():
    """Carga el módulo de estructura de almacenamiento compartido."""
    module_path = (
        Path(__file__).resolve().parents[5]
        / "src/2_shared_application/storage_access_structure.py"
    )
    spec = importlib.util.spec_from_file_location("storage_access_structure_trainer", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar storage_access_structure")
    module = importlib.util.module_from_spec(spec)
    sys.modules["storage_access_structure_trainer"] = module
    spec.loader.exec_module(module)
    return module


_storage_structure = _load_storage_structure_module()
get_folder_by_id_organization = _storage_structure.get_folder_by_id_organization
get_folder_by_id_project = _storage_structure.get_folder_by_id_project


class StorageAdapterError(Exception):
    """Error al interactuar con la persistencia."""


@dataclass(frozen=True, slots=True)
class FmanagementSettings:
    """Configuración para la API externa de file management."""

    base_url: str
    base_path: str


def load_fmanagement_settings() -> FmanagementSettings:
    """Carga configuración de fmanagement desde entorno."""

    base_url = os.environ.get("FMANAGEMENT_BASE_URL", "http://localhost:1666")
    base_path = os.environ.get("FMANAGEMENT_BASE_PATH", "/data/files/external")
    return FmanagementSettings(
        base_url=base_url.rstrip("/"),
        base_path=base_path,
    )


def build_storage_paths(
    id_organization: int, id_project: int, version_path: str, subfolders: str = ""
) -> dict[str, str]:
    """Construye rutas para operaciones de ficheros a partir de IDs."""

    return {
        "orgpath": get_folder_by_id_organization(id_organization),
        "prjpath": get_folder_by_id_project(id_project),
        "versionpath": version_path,
        "subfolders": subfolders,
    }


def _load_env_settings_module(module_name: str) -> Any:
    """Carga el módulo de configuración compartida."""

    module_path = (
        Path(__file__).resolve().parents[5]
        / "src/2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise StorageAdapterError("No se pudo cargar el módulo de configuración")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_mariadb_settings() -> dict[str, Any]:
    """Carga configuración de MariaDB desde entorno o protected_values."""

    env_settings = _load_env_settings_module("backend_trainer_env_settings")
    protected = env_settings.load_protected_settings()
    if not protected:
        raise StorageAdapterError(
            "No se pudo cargar la configuración de MariaDB desde protected_values"
        )

    return {
        "host": os.environ.get("MARIADB_HOST", protected.get("mariadb_host", "")),
        "port": int(
            os.environ.get("MARIADB_PORT", protected.get("mariadb_port", 3306))
        ),
        "core_database": os.environ.get(
            "MARIADB_CORE_DATABASE", protected.get("mariadb_core_database", "")
        ),
        "projects_database": os.environ.get(
            "MARIADB_PROJECTS_DATABASE", protected.get("mariadb_ai_database", "")
        ),
        "admin_user": os.environ.get(
            "MARIADB_ADMIN_USER", protected.get("mariadb_admin_user", "")
        ),
        "admin_password": os.environ.get(
            "MARIADB_ADMIN_PASSWORD", protected.get("mariadb_admin_password", "")
        ),
        "writer_user": os.environ.get(
            "MARIADB_WRITER_USER", protected.get("mariadb_writer_user", "")
        ),
        "writer_password": os.environ.get(
            "MARIADB_WRITER_PASSWORD",
            protected.get("mariadb_writer_password", ""),
        ),
        "reader_user": os.environ.get(
            "MARIADB_READER_USER", protected.get("mariadb_reader_user", "")
        ),
        "reader_password": os.environ.get(
            "MARIADB_READER_PASSWORD",
            protected.get("mariadb_reader_password", ""),
        ),
        "cli_path": os.environ.get(
            "MARIADB_CLI_PATH", protected.get("mariadb_cli_path", "")
        ),
    }


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    """Lee un JSON tipo lista de forma segura."""

    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
    except json.JSONDecodeError as exc:
        raise StorageAdapterError("El archivo JSON no es válido") from exc
    if not isinstance(data, list):
        raise StorageAdapterError("El JSON debe contener una lista")
    return data


def _write_json_list(path: Path, payload: list[dict[str, Any]]) -> None:
    """Escribe un JSON tipo lista de forma segura."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)

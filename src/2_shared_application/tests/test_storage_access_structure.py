"""Tests para helpers de estructura de almacenamiento."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_env_settings_module() -> object:
    """Carga el módulo de configuración de entorno."""

    module_path = (
        Path(__file__).resolve().parents[2]
        / "2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location("env_settings", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar env_settings.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["env_settings"] = module
    spec.loader.exec_module(module)
    return module


def _load_storage_helpers_module() -> object:
    """Carga el módulo storage_access_structure desde ruta."""

    # Primero cargar las variables de entorno
    env_settings = _load_env_settings_module()
    env_settings.load_env_file()
    
    module_path = (
        Path(__file__).resolve().parents[2]
        / "2_shared_application/storage_access_structure.py"
    )
    spec = importlib.util.spec_from_file_location(
        "shared_storage_access_structure", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar storage_access_structure")
    module = importlib.util.module_from_spec(spec)
    sys.modules["shared_storage_access_structure"] = module
    spec.loader.exec_module(module)
    return module


def test_get_folder_by_id_organization() -> None:
    """Valida formato ORG con relleno de ceros."""

    helpers_module = _load_storage_helpers_module()
    assert helpers_module.get_folder_by_id_organization(1) == "ORG0001"
    assert helpers_module.get_folder_by_id_organization(25) == "ORG0025"
    assert helpers_module.get_folder_by_id_organization(1234) == "ORG1234"


def test_get_folder_by_id_project() -> None:
    """Valida formato PRJ con relleno de ceros."""

    helpers_module = _load_storage_helpers_module()
    assert helpers_module.get_folder_by_id_project(1) == "PRJ0001"
    assert helpers_module.get_folder_by_id_project(7) == "PRJ0007"
    assert helpers_module.get_folder_by_id_project(9999) == "PRJ9999"

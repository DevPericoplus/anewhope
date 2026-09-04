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
    assert helpers_module.get_folder_by_id_organization(1) == "ORG00001"
    assert helpers_module.get_folder_by_id_organization(25) == "ORG00025"
    assert helpers_module.get_folder_by_id_organization(1234) == "ORG01234"


def test_get_folder_by_id_user() -> None:
    """Valida formato USER con relleno de ceros."""

    helpers_module = _load_storage_helpers_module()
    assert helpers_module.get_folder_by_id_user(1) == "USER00001"
    assert helpers_module.get_folder_by_id_user(12) == "USER00012"


def test_get_account_storage_folder() -> None:
    """Org usa ORG#####; individual usa USER#####."""

    helpers_module = _load_storage_helpers_module()
    assert helpers_module.get_account_storage_folder(1, 9) == "ORG00001"
    assert helpers_module.get_account_storage_folder(0, 9) == "USER00009"
    assert helpers_module.get_account_storage_folder(None, 9) == "USER00009"


def test_get_folder_by_id_project() -> None:
    """Valida formato PRJ con relleno de ceros."""

    helpers_module = _load_storage_helpers_module()
    assert helpers_module.get_folder_by_id_project(1) == "PRJ00001"
    assert helpers_module.get_folder_by_id_project(7) == "PRJ00007"
    assert helpers_module.get_folder_by_id_project(9999) == "PRJ09999"


def test_build_fmo_path_segments_organization() -> None:
    """Proyecto de organización usa raíz ORG#####."""

    helpers_module = _load_storage_helpers_module()
    segments = helpers_module.build_fmo_path_segments(
        organization_id=1,
        user_id=9,
        project_id=3,
        version_id=2,
        subfolders="docs",
    )
    assert segments["orgpath"] == "ORG00001"
    assert segments["prjpath"] == "PRJ00003"
    assert segments["versionpath"] == "v002"
    assert segments["subfolders"] == "docs"


def test_build_fmo_path_segments_individual() -> None:
    """Proyecto individual usa raíz USER##### del dueño."""

    helpers_module = _load_storage_helpers_module()
    segments = helpers_module.build_fmo_path_segments(
        organization_id=0,
        user_id=12,
        project_id=7,
        version_path="v001",
    )
    assert segments["orgpath"] == "USER00012"
    assert segments["prjpath"] == "PRJ00007"
    assert segments["versionpath"] == "v001"

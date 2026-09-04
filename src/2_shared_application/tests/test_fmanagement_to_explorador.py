"""Tests del adaptador fmanagement → explorador (raíz ORG/USER)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_adapter():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "adapters"
        / "fmanagement_to_explorador.py"
    )
    spec = importlib.util.spec_from_file_location(
        "fmanagement_to_explorador_test", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar fmanagement_to_explorador")
    module = importlib.util.module_from_spec(spec)
    sys.modules["fmanagement_to_explorador_test"] = module
    spec.loader.exec_module(module)
    return module


def test_convert_uses_user_root_when_org_id_is_zero() -> None:
    """Sin org_folder y org_id=0, el path usa USER#####."""

    adapter = _load_adapter()
    result = adapter.convert_fmanagement_to_explorador(
        fmanagement_response={"success": True, "items": []},
        org_id=0,
        project_id=7,
        version_name="v001",
        org_folder="",
        prj_folder="",
    )
    assert result["status"] == "success"
    assert result["path"] == "/data/external/USER00000/PRJ00007"
    assert result["items"][0]["name"] == "PRJ00007"


def test_convert_keeps_explicit_user_folder() -> None:
    """Si llega USER#####, no se reescribe a ORG."""

    adapter = _load_adapter()
    result = adapter.convert_fmanagement_to_explorador(
        fmanagement_response={"success": True, "items": []},
        org_id=0,
        project_id=3,
        version_name="v001",
        org_folder="USER00012",
        prj_folder="PRJ00003",
    )
    assert result["path"] == "/data/external/USER00012/PRJ00003"
    assert result["items"][0]["name"] == "PRJ00003"

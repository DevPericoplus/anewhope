"""Carga de organizaciones compatible con schema previo a 020."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch


def _load_storage_adapter() -> Any:
    """Carga storage_adapter sin importar el paquete numerado."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / "4_infrastructure"
        / "persistence"
        / "storage_adapter.py"
    )
    spec = importlib.util.spec_from_file_location(
        "storage_adapter_orgs_test", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar storage_adapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


storage_adapter = _load_storage_adapter()


def test_load_organizations_without_acronym_column() -> None:
    """Si falta organization_acronym, el SELECT no incluye esa columna."""
    settings = {"reader_user": "reader"}
    org_row = (1, "myllm", "a@b.c", "", "", "", "", 1)

    def _fake_fetch(_settings: dict[str, Any], query: str, **_kwargs: Any) -> list:
        if "information_schema.COLUMNS" in query:
            return [(0,)]
        assert "organization_acronym" not in query
        return [org_row]

    with (
        patch.object(storage_adapter, "load_mariadb_settings", return_value=settings),
        patch.object(storage_adapter, "_fetch_mariadb_rows", side_effect=_fake_fetch),
    ):
        records = storage_adapter._load_organizations_from_mariadb()

    assert records[0]["organization_id"] == 1
    assert records[0]["organization_acronym"] == ""


def test_load_organizations_with_acronym_column() -> None:
    """Si existe organization_acronym, se mapea en el registro."""
    settings = {"reader_user": "reader"}
    org_row = (1, "myllm", "a@b.c", "", "", "", "", 1, "myllm")

    def _fake_fetch(_settings: dict[str, Any], query: str, **_kwargs: Any) -> list:
        if "information_schema.COLUMNS" in query:
            return [(1,)]
        assert "organization_acronym" in query
        return [org_row]

    with (
        patch.object(storage_adapter, "load_mariadb_settings", return_value=settings),
        patch.object(storage_adapter, "_fetch_mariadb_rows", side_effect=_fake_fetch),
    ):
        records = storage_adapter._load_organizations_from_mariadb()

    assert records[0]["organization_acronym"] == "myllm"

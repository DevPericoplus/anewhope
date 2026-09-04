"""Tests del dueño de storage resuelto en Core para el Trainer."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock


def _load_routercore() -> Any:
    """Carga routercore sin importar el paquete numerado."""
    module_path = Path(__file__).resolve().parents[1] / "routercore.py"
    spec = importlib.util.spec_from_file_location(
        "routercore_trainer_context", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar routercore")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


routercore = _load_routercore()


class _FakeResult:
    """Resultado SQL mínimo con fetchone."""

    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row


def test_lookup_storage_owner_keeps_org_project() -> None:
    """Proyecto de organización no busca dueño individual."""
    conn = MagicMock()
    conn.execute.return_value = _FakeResult((5, "Demo"))
    lookup = routercore.BackendCoreRouter._lookup_project_storage_owner
    org_id, owner_id, name = lookup(None, conn, lambda sql: sql, 4, "Proyecto 4")
    assert org_id == 5
    assert owner_id == 0
    assert name == "Demo"
    assert conn.execute.call_count == 1


def test_lookup_storage_owner_resolves_individual_user() -> None:
    """Proyecto sin org toma el dueño de proyectos_roles."""
    conn = MagicMock()
    conn.execute.side_effect = [
        _FakeResult((0, "Personal")),
        _FakeResult((12,)),
    ]
    lookup = routercore.BackendCoreRouter._lookup_project_storage_owner
    org_id, owner_id, name = lookup(None, conn, lambda sql: sql, 8, "Proyecto 8")
    assert org_id == 0
    assert owner_id == 12
    assert name == "Personal"
    assert conn.execute.call_count == 2

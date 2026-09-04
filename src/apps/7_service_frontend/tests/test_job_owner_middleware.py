"""Tests de inyección del dueño de job hacia el Trainer."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def _load_routermiddleware() -> Any:
    """Carga routermiddleware sin depender de otros tests."""
    module_path = Path(__file__).resolve().parents[1] / "routermiddleware.py"
    spec = importlib.util.spec_from_file_location(
        "routermiddleware_job_owner", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar routermiddleware")
    module = importlib.util.module_from_spec(spec)
    sys.modules["routermiddleware_job_owner"] = module
    spec.loader.exec_module(module)
    return module


routermiddleware = _load_routermiddleware()


def _session(*, user_id: int, organization_id: int = 0) -> Any:
    """Construye un SessionContext mínimo."""
    return routermiddleware.SessionContext(
        user_id=user_id,
        organization_id=organization_id,
        identity_type_id=6,
        access_payload={},
        session_payload={},
    )


def test_ensure_job_owner_fills_id_user_from_session() -> None:
    """Si el payload no trae id_user, se usa el de la sesión."""
    payload: dict[str, Any] = {"id_organizacion": 0, "id_proyecto": 4}
    routermiddleware.RouterMiddleware._ensure_job_owner_user_id(
        payload, _session(user_id=12)
    )
    assert payload["id_user"] == 12


def test_ensure_job_owner_keeps_explicit_id_user() -> None:
    """Un id_user explícito no se sobrescribe con la sesión."""
    payload: dict[str, Any] = {"id_user": 9, "id_organizacion": 1}
    routermiddleware.RouterMiddleware._ensure_job_owner_user_id(
        payload, _session(user_id=1, organization_id=1)
    )
    assert payload["id_user"] == 9

"""Tests TDD del repositorio de casos de contacto LAIM."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO_PATH = (
    Path(__file__).resolve().parents[1] / "adapters" / "laim_contact_repository.py"
)


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def _load_repository_module():
    name = "laim_contact_repository_casos_test"
    spec = importlib.util.spec_from_file_location(name, _REPO_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # noqa: SLF001 — carga TDD aislada
    return module


def test_create_case_inserts_casos_contacto_with_estado_abierto() -> None:
    module = _load_repository_module()
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    insert_result = MagicMock()
    insert_result.lastrowid = 17
    conn.execute.return_value = insert_result

    repository = module.LaimContactRepository(engine)
    case_id, image_id = repository.create_message_with_image(
        usage_mode="local",
        affected_user_info="usuario_demo",
        message_body="Descripción suficientemente larga del problema.",
        reply_email="user@example.com",
        user_id=None,
        user_name=None,
        organization_id=None,
        ip_address="192.168.64.10",
        user_agent="pytest",
    )

    assert case_id == 17
    assert image_id is None
    sql = str(conn.execute.call_args.args[0])
    params = conn.execute.call_args.args[1]
    assert "casos_contacto" in sql
    assert "id_estado" in sql
    assert params["id_estado"] == module.ESTADO_CASO_ABIERTO_ID
    assert params["id_estado"] == 1


def test_estado_abierto_constant_is_one() -> None:
    module = _load_repository_module()
    assert module.ESTADO_CASO_ABIERTO_ID == 1

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


def test_estado_descartado_constant_is_five() -> None:
    module = _load_repository_module()
    assert module.ESTADO_CASO_DESCARTADO_ID == 5
    assert module.ESTADO_CLAVE_TO_ID["descartado"] == 5
    assert module.ESTADO_CLAVE_TO_ID["abierto"] == 1
    assert module.ESTADO_CLAVE_TO_ID["gestionando"] == 2
    assert module.ESTADO_CLAVE_TO_ID["resuelto"] == 4


def test_list_messages_filters_by_estado_and_omits_image_blob() -> None:
    module = _load_repository_module()
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    row = {
        "id": 9,
        "id_estado": 1,
        "estado_clave": "abierto",
        "estado_nombre": "Abierto",
        "usage_mode": "local",
        "affected_user_info": "ana",
        "message_preview": "No arranca el binario",
        "reply_email": "ana@example.com",
        "user_id": None,
        "user_name": None,
        "user_mobile": None,
        "organization_id": None,
        "has_image": 1,
        "created_at": "2026-10-08 10:00:00",
        "updated_at": "2026-10-08 10:00:00",
    }
    conn.execute.return_value.mappings.return_value.fetchall.return_value = [row]

    repository = module.LaimContactRepository(engine)
    items = repository.list_messages(estado_clave="abierto", limit=20)

    assert len(items) == 1
    assert items[0]["id"] == 9
    assert items[0]["estado_clave"] == "abierto"
    assert items[0]["has_image"] == 1
    sql = str(conn.execute.call_args.args[0])
    assert "casos_contacto" in sql
    assert "image_data" not in sql
    assert "estados_casos_contacto" in sql
    params = conn.execute.call_args.args[1]
    assert params["id_estado"] == 1
    assert params["limit"] == 20


def test_list_messages_search_includes_email_user_and_mobile() -> None:
    module = _load_repository_module()
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    conn.execute.return_value.mappings.return_value.fetchall.return_value = []

    repository = module.LaimContactRepository(engine)
    repository.list_messages(query="555123", limit=10)

    sql = str(conn.execute.call_args.args[0])
    params = conn.execute.call_args.args[1]
    assert "reply_email" in sql
    assert "user_name" in sql
    assert "user_mobile" in sql
    assert "affected_user_info" in sql
    assert params["query"] == "%555123%"


def test_update_estado_writes_audit_and_returns_case() -> None:
    module = _load_repository_module()
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    current = {
        "id": 4,
        "id_estado": 1,
        "estado_clave": "abierto",
        "estado_nombre": "Abierto",
        "usage_mode": "local",
        "affected_user_info": None,
        "message_body": "texto",
        "reply_email": "a@b.com",
        "user_id": None,
        "user_name": None,
        "organization_id": None,
        "created_at": "2026-10-08 10:00:00",
        "updated_at": "2026-10-08 10:00:00",
    }
    updated = {**current, "id_estado": 2, "estado_clave": "gestionando", "estado_nombre": "Gestionando"}
    select_current = MagicMock()
    select_current.mappings.return_value.fetchone.return_value = current
    select_updated = MagicMock()
    select_updated.mappings.return_value.fetchone.return_value = updated
    conn.execute.side_effect = [select_current, MagicMock(), MagicMock(), select_updated]

    repository = module.LaimContactRepository(engine)
    result = repository.update_estado(4, id_estado=2, actor="laim_maintenance")

    assert result is not None
    assert result["id_estado"] == 2
    sqls = [str(call.args[0]) for call in conn.execute.call_args_list]
    assert any("UPDATE" in sql and "casos_contacto" in sql for sql in sqls)
    assert any("casos_contacto_auditoria" in sql for sql in sqls)


def test_update_estado_unknown_case_returns_none() -> None:
    module = _load_repository_module()
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    missing = MagicMock()
    missing.mappings.return_value.fetchone.return_value = None
    conn.execute.return_value = missing

    repository = module.LaimContactRepository(engine)
    assert repository.update_estado(99, id_estado=5, actor="laim_maintenance") is None


def test_get_with_image_selects_blob_only_for_detail() -> None:
    module = _load_repository_module()
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    case_row = {
        "id": 3,
        "id_estado": 1,
        "estado_clave": "abierto",
        "estado_nombre": "Abierto",
        "usage_mode": "share",
        "affected_user_info": "",
        "message_body": "cuerpo completo",
        "reply_email": "x@y.com",
        "user_id": 8,
        "user_name": "pepe",
        "user_mobile": "600111222",
        "organization_id": 1,
        "created_at": "2026-10-08 10:00:00",
        "updated_at": "2026-10-08 10:00:00",
    }
    image_row = {
        "id": 1,
        "file_name": "cap.png",
        "mime_type": "image/png",
        "file_size": 12,
        "image_data": b"png-bytes",
    }
    case_result = MagicMock()
    case_result.mappings.return_value.fetchone.return_value = case_row
    image_result = MagicMock()
    image_result.mappings.return_value.fetchone.return_value = image_row
    conn.execute.side_effect = [case_result, image_result]

    repository = module.LaimContactRepository(engine)
    detail = repository.get_with_image(3)

    assert detail is not None
    assert detail["message_body"] == "cuerpo completo"
    assert detail["image"]["file_name"] == "cap.png"
    assert detail["image"]["image_data"] == b"png-bytes"


def test_replace_keywords_deletes_then_inserts() -> None:
    module = _load_repository_module()
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn

    repository = module.LaimContactRepository(engine)
    repository.replace_keywords(11, ["instalacion", "macos"], fuente="ia")

    sqls = [str(call.args[0]) for call in conn.execute.call_args_list]
    assert any("DELETE" in sql and "casos_contacto_etiquetas" in sql for sql in sqls)
    assert sum(1 for sql in sqls if "INSERT" in sql and "casos_contacto_etiquetas" in sql) == 2

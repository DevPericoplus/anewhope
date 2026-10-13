"""Tests TDD del repositorio de tickets."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO_PATH = Path(__file__).resolve().parents[1] / "adapters" / "laim_tickets_repository.py"


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def _load():
    name = "laim_tickets_repository_test"
    spec = importlib.util.spec_from_file_location(name, _REPO_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_create_ticket_inserts_ticket_message_and_event() -> None:
    module = _load()
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    insert_result = MagicMock()
    insert_result.lastrowid = 11
    conn.execute.return_value = insert_result
    fetch = MagicMock()
    fetch.mappings.return_value.fetchone.return_value = {
        "id": 11,
        "id_estado": 1,
        "estado_clave": "abierto",
        "estado_nombre": "Abierto",
        "user_id": 9,
        "user_name": "laimone",
        "user_email": "one@laim.app",
        "organization_id": 1,
        "edition": "community_edition",
        "subject": "asunto",
        "body": "cuerpo largo",
        "opened_at": "now",
        "closed_at": None,
        "updated_at": "now",
    }
    # last execute is the fetch
    conn.execute.side_effect = [insert_result, MagicMock(), MagicMock(), fetch]

    repo = module.LaimTicketsRepository(engine)
    row = repo.create_ticket(
        user_id=9,
        user_name="laimone",
        user_email="one@laim.app",
        organization_id=1,
        edition="community_edition",
        subject="asunto",
        body="cuerpo largo",
    )
    assert row["id"] == 11
    sqls = [str(call.args[0]) for call in conn.execute.call_args_list]
    assert any("laim_tickets" in sql and "INSERT" in sql.upper() for sql in sqls)
    assert any("laim_ticket_mensajes" in sql for sql in sqls)
    assert any("laim_ticket_eventos" in sql for sql in sqls)


def test_list_tickets_filters_by_user() -> None:
    module = _load()
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    result = MagicMock()
    result.mappings.return_value.fetchall.return_value = []
    conn.execute.return_value = result
    repo = module.LaimTicketsRepository(engine)
    repo.list_tickets(user_id=9)
    sql = str(conn.execute.call_args.args[0])
    params = conn.execute.call_args.args[1]
    assert "t.user_id = :user_id" in sql
    assert params["user_id"] == 9
    assert "image_data" not in sql


def test_migration_028_declares_notifications_table() -> None:
    sql_path = (
        Path(__file__).resolve().parents[3]
        / "infrastructure"
        / "database"
        / "migrations"
        / "028_laim_tickets.sql"
    )
    text = sql_path.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS `laim_ticket_notificaciones`" in text
    assert "ticket_created" in text
    assert "GRANT SELECT ON `laim_core_db`.`laim_ticket_notificaciones`" in text


def test_add_notification_inserts_unread_row() -> None:
    module = _load()
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    insert_result = MagicMock()
    insert_result.lastrowid = 21
    conn.execute.return_value = insert_result
    repo = module.LaimTicketsRepository(engine)
    row = repo.add_notification(
        ticket_id=7,
        destinatario="operador",
        user_id=None,
        tipo="ticket_created",
    )
    assert row["id"] == 21
    sql = str(conn.execute.call_args.args[0])
    params = conn.execute.call_args.args[1]
    assert "laim_ticket_notificaciones" in sql
    assert params["ticket_id"] == 7
    assert params["destinatario"] == "operador"
    assert params["tipo"] == "ticket_created"


def test_list_pending_filters_unread_by_destinatario() -> None:
    module = _load()
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    result = MagicMock()
    result.mappings.return_value.fetchall.return_value = []
    conn.execute.return_value = result
    repo = module.LaimTicketsRepository(engine)
    repo.list_pending_notifications(destinatario="usuario", user_id=9)
    sql = str(conn.execute.call_args.args[0])
    params = conn.execute.call_args.args[1]
    assert "laim_ticket_notificaciones" in sql
    assert "leida = 0" in sql
    assert params["destinatario"] == "usuario"
    assert params["user_id"] == 9


def test_ack_notification_marks_own_row() -> None:
    module = _load()
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    result = MagicMock()
    result.rowcount = 1
    conn.execute.return_value = result
    repo = module.LaimTicketsRepository(engine)
    assert repo.ack_notification(21, destinatario="usuario", user_id=9) is True
    sql = str(conn.execute.call_args.args[0])
    params = conn.execute.call_args.args[1]
    assert "leida = 1" in sql
    assert params["id"] == 21
    assert params["user_id"] == 9

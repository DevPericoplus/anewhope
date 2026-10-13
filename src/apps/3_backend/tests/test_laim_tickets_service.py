"""Tests TDD del servicio de tickets de soporte."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def _load_service():
    import importlib.util
    import sys
    from pathlib import Path

    module_path = Path(__file__).resolve().parents[1] / "laim_tickets_service.py"
    spec = importlib.util.spec_from_file_location("laim_tickets_service_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_tickets_service_test"] = module
    spec.loader.exec_module(module)
    return module


def _user() -> dict:
    return {"user_id": 9, "user_name": "laimone", "user_email": "one@laim.app", "organization_id": 1}


def test_create_ticket_requires_session() -> None:
    module = _load_service()
    service = module.LaimTicketsService(repository=MagicMock())
    result = service.create_ticket({"subject": "Falla al instalar", "body": "No arranca el cliente."}, {})
    assert result["success"] is False
    assert "sesión" in result["error"].lower()


def test_create_ticket_forces_community_edition() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.create_ticket.return_value = {
        "id": 3,
        "estado_clave": "abierto",
        "estado_nombre": "Abierto",
        "user_id": 9,
        "user_name": "laimone",
        "user_email": "one@laim.app",
        "organization_id": 1,
        "edition": "community_edition",
        "subject": "Falla al instalar",
        "body": "No arranca el cliente.",
        "opened_at": "2026-10-13",
        "closed_at": None,
        "updated_at": "2026-10-13",
    }
    service = module.LaimTicketsService(repository=repository)
    result = service.create_ticket(
        {"subject": "Falla al instalar", "body": "No arranca el cliente."},
        _user(),
    )
    assert result["success"] is True
    assert result["ticket"]["id"] == 3
    assert result["ticket"]["edition"] == "community_edition"
    assert result["ticket"]["readonly"] is False
    assert repository.create_ticket.call_args.kwargs["edition"] == "community_edition"


def test_ticket_detail_events_use_state_claves() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 1,
        "user_id": 9,
        "user_name": "laimone",
        "user_email": "one@laim.app",
        "estado_clave": "abierto",
        "estado_nombre": "Abierto",
        "edition": "community_edition",
        "subject": "primer ticket",
        "body": "hola",
        "opened_at": "2026-10-13",
        "updated_at": "2026-10-13",
    }
    repository.list_messages.return_value = []
    repository.list_events.return_value = [
        {"id": 1, "tipo": "created", "estado_desde": None, "estado_hasta": 1, "actor": "laimone", "created_at": "2026-10-13"}
    ]
    service = module.LaimTicketsService(repository=repository)
    result = service.get_ticket(1)
    assert result["success"] is True
    event = result["events"][0]
    assert event["estado_hasta"] == "abierto"
    assert event["estado_desde"] == ""
    assert event["estado_hasta"] != 1


def test_get_my_ticket_hides_others() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {"id": 4, "user_id": 2, "estado_clave": "abierto", "estado_nombre": "Abierto"}
    repository.list_messages.return_value = []
    repository.list_events.return_value = []
    service = module.LaimTicketsService(repository=repository)
    result = service.get_my_ticket(4, user_id=9)
    assert result["success"] is False
    assert "no encontrado" in result["error"].lower()
    repository.ack_ticket_notifications.assert_not_called()


def test_get_my_ticket_acks_all_pending_for_that_ticket() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 4,
        "user_id": 9,
        "estado_clave": "esperando_usuario",
        "estado_nombre": "Esperando usuario",
    }
    repository.list_messages.return_value = []
    repository.list_events.return_value = []
    repository.ack_ticket_notifications.return_value = 2
    service = module.LaimTicketsService(repository=repository)
    result = service.get_my_ticket(4, user_id=9)
    assert result["success"] is True
    repository.ack_ticket_notifications.assert_called_once_with(
        4, destinatario="usuario", user_id=9
    )


def test_user_reply_on_waiting_moves_state() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 4,
        "user_id": 9,
        "user_name": "laimone",
        "estado_clave": "esperando_usuario",
        "estado_nombre": "Esperando usuario",
    }
    repository.add_message_and_maybe_state.return_value = {"id": 4}
    repository.list_messages.return_value = []
    repository.list_events.return_value = []
    service = module.LaimTicketsService(repository=repository)
    result = service.reply_as_user(4, 9, "laimone", "Aquí van los logs.")
    assert result["success"] is True
    kwargs = repository.add_message_and_maybe_state.call_args.kwargs
    assert kwargs["autor"] == "usuario"
    assert kwargs["new_estado_clave"] == "en_curso"


def test_user_reply_rejected_when_closed() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 4,
        "user_id": 9,
        "user_name": "laimone",
        "estado_clave": "cerrado",
        "estado_nombre": "Cerrado",
    }
    service = module.LaimTicketsService(repository=repository)
    result = service.reply_as_user(4, 9, "laimone", "otra cosa")
    assert result["success"] is False
    repository.add_message_and_maybe_state.assert_not_called()


def test_operator_can_wait_from_open_and_notifies_user() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 4,
        "user_id": 9,
        "estado_clave": "abierto",
        "estado_nombre": "Abierto",
    }
    repository.change_estado.return_value = {
        "id": 4,
        "user_id": 9,
        "estado_clave": "esperando_usuario",
    }
    repository.list_messages.return_value = []
    repository.list_events.return_value = []
    service = module.LaimTicketsService(repository=repository)
    result = service.change_status(4, "esperando_usuario", "op")
    assert result["success"] is True
    assert repository.change_estado.call_args.args[1] == "esperando_usuario"
    kwargs = repository.add_notification.call_args.kwargs
    assert kwargs["destinatario"] == "usuario"
    assert kwargs["tipo"] == "ticket_status"


def test_reopen_only_closed() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 4,
        "user_id": 9,
        "estado_clave": "cerrado",
        "estado_nombre": "Cerrado",
    }
    repository.change_estado.return_value = {"id": 4, "estado_clave": "en_curso"}
    repository.list_messages.return_value = []
    repository.list_events.return_value = []
    service = module.LaimTicketsService(repository=repository)
    result = service.reopen(4, "op")
    assert result["success"] is True
    assert repository.change_estado.call_args.args[1] == "en_curso"
    assert repository.change_estado.call_args.args[3] == "reopened"


def test_create_ticket_notifies_operator() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.create_ticket.return_value = {
        "id": 3,
        "user_id": 9,
        "estado_clave": "abierto",
        "estado_nombre": "Abierto",
        "edition": "community_edition",
        "subject": "Falla al instalar",
        "body": "No arranca el cliente.",
        "opened_at": "2026-10-13",
        "closed_at": None,
        "updated_at": "2026-10-13",
    }
    service = module.LaimTicketsService(repository=repository)
    result = service.create_ticket(
        {"subject": "Falla al instalar", "body": "No arranca el cliente."},
        _user(),
    )
    assert result["success"] is True
    repository.add_notification.assert_called_once()
    kwargs = repository.add_notification.call_args.kwargs
    assert kwargs["ticket_id"] == 3
    assert kwargs["destinatario"] == "operador"
    assert kwargs["tipo"] == "ticket_created"
    assert kwargs["user_id"] is None


def test_user_reply_notifies_operator() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 4,
        "user_id": 9,
        "user_name": "laimone",
        "estado_clave": "esperando_usuario",
        "estado_nombre": "Esperando usuario",
    }
    repository.add_message_and_maybe_state.return_value = {"id": 4, "user_id": 9}
    repository.list_messages.return_value = []
    repository.list_events.return_value = []
    service = module.LaimTicketsService(repository=repository)
    result = service.reply_as_user(4, 9, "laimone", "Aquí van los logs.")
    assert result["success"] is True
    kwargs = repository.add_notification.call_args.kwargs
    assert kwargs["destinatario"] == "operador"
    assert kwargs["tipo"] == "ticket_replied"


def test_operator_reply_notifies_user() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 4,
        "user_id": 9,
        "estado_clave": "abierto",
        "estado_nombre": "Abierto",
    }
    repository.add_message_and_maybe_state.return_value = {"id": 4, "user_id": 9}
    repository.list_messages.return_value = []
    repository.list_events.return_value = []
    service = module.LaimTicketsService(repository=repository)
    result = service.reply_as_operator(4, "op", "Revisamos el caso.")
    assert result["success"] is True
    kwargs = repository.add_notification.call_args.kwargs
    assert kwargs["destinatario"] == "usuario"
    assert kwargs["user_id"] == 9
    assert kwargs["tipo"] == "ticket_replied"


def test_close_does_not_notify_user() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 4,
        "user_id": 9,
        "estado_clave": "en_curso",
        "estado_nombre": "En curso",
    }
    repository.change_estado.return_value = {"id": 4, "user_id": 9, "estado_clave": "cerrado"}
    repository.list_messages.return_value = []
    repository.list_events.return_value = []
    service = module.LaimTicketsService(repository=repository)
    result = service.change_status(4, "cerrado", "op")
    assert result["success"] is True
    repository.add_notification.assert_not_called()


def test_change_status_notifies_user() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 4,
        "user_id": 9,
        "estado_clave": "en_curso",
        "estado_nombre": "En curso",
    }
    repository.change_estado.return_value = {"id": 4, "user_id": 9, "estado_clave": "esperando_usuario"}
    repository.list_messages.return_value = []
    repository.list_events.return_value = []
    service = module.LaimTicketsService(repository=repository)
    result = service.change_status(4, "esperando_usuario", "op")
    assert result["success"] is True
    kwargs = repository.add_notification.call_args.kwargs
    assert kwargs["destinatario"] == "usuario"
    assert kwargs["tipo"] == "ticket_status"


def test_reopen_notifies_user() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 4,
        "user_id": 9,
        "estado_clave": "cerrado",
        "estado_nombre": "Cerrado",
    }
    repository.change_estado.return_value = {"id": 4, "user_id": 9, "estado_clave": "en_curso"}
    repository.list_messages.return_value = []
    repository.list_events.return_value = []
    service = module.LaimTicketsService(repository=repository)
    result = service.reopen(4, "op")
    assert result["success"] is True
    kwargs = repository.add_notification.call_args.kwargs
    assert kwargs["tipo"] == "ticket_reopened"
    assert kwargs["destinatario"] == "usuario"


def test_notify_failure_does_not_fail_create() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.create_ticket.return_value = {
        "id": 3,
        "user_id": 9,
        "estado_clave": "abierto",
        "estado_nombre": "Abierto",
        "edition": "community_edition",
        "subject": "Falla al instalar",
        "body": "No arranca el cliente.",
        "opened_at": "2026-10-13",
        "closed_at": None,
        "updated_at": "2026-10-13",
    }
    repository.add_notification.side_effect = RuntimeError("db down")
    service = module.LaimTicketsService(repository=repository)
    result = service.create_ticket(
        {"subject": "Falla al instalar", "body": "No arranca el cliente."},
        _user(),
    )
    assert result["success"] is True


def test_list_and_ack_my_notifications() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.list_pending_notifications.return_value = [
        {"id": 21, "ticket_id": 4, "tipo": "ticket_replied", "subject": "falla"}
    ]
    repository.ack_notification.return_value = True
    service = module.LaimTicketsService(repository=repository)
    listed = service.list_my_notifications(9)
    assert listed["success"] is True
    assert listed["items"][0]["ticket_id"] == 4
    acked = service.ack_my_notification(21, 9)
    assert acked["success"] is True
    repository.ack_notification.assert_called_once_with(
        21, destinatario="usuario", user_id=9
    )


def test_ack_my_notification_rejects_foreign() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.ack_notification.return_value = False
    service = module.LaimTicketsService(repository=repository)
    result = service.ack_my_notification(21, 9)
    assert result["success"] is False


def test_public_actor_hides_internal_operator_name() -> None:
    module = _load_service()
    assert module.PUBLIC_OPERATOR_ACTOR == "Soporte LAIM"
    assert module.public_actor_name("laim_maintenance", "operador") == "Soporte LAIM"
    assert module.public_actor_name("", "operador") == "Soporte LAIM"
    assert module.public_actor_name("laimone", "usuario") == "laimone"


def test_operator_reply_persists_public_support_name() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.get_ticket.return_value = {
        "id": 4,
        "user_id": 9,
        "estado_clave": "abierto",
        "estado_nombre": "Abierto",
    }
    repository.add_message_and_maybe_state.return_value = {"id": 4, "user_id": 9}
    repository.list_messages.return_value = [
        {
            "autor": "operador",
            "actor_name": "laim_maintenance",
            "cuerpo": "Revisamos el caso.",
            "created_at": "2026-10-13",
        }
    ]
    repository.list_events.return_value = [
        {"id": 1, "tipo": "replied", "estado_desde": 1, "estado_hasta": 2, "actor": "laim_maintenance"}
    ]
    service = module.LaimTicketsService(repository=repository)
    result = service.reply_as_operator(4, "laim_maintenance", "Revisamos el caso.")
    assert result["success"] is True
    assert repository.add_message_and_maybe_state.call_args.kwargs["actor_name"] == "Soporte LAIM"
    assert result["messages"][0]["actor_name"] == "Soporte LAIM"
    assert result["events"][0]["actor"] == "Soporte LAIM"


def test_list_and_ack_operator_notifications() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.list_pending_notifications.return_value = [
        {"id": 22, "ticket_id": 3, "tipo": "ticket_created", "subject": "falla"}
    ]
    repository.ack_notification.return_value = True
    service = module.LaimTicketsService(repository=repository)
    listed = service.list_operator_notifications()
    assert listed["success"] is True
    assert listed["items"][0]["ticket_id"] == 3
    repository.list_pending_notifications.assert_called_once_with(destinatario="operador")
    acked = service.ack_operator_notification(22)
    assert acked["success"] is True
    repository.ack_notification.assert_called_once_with(22, destinatario="operador")

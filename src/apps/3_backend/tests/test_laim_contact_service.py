"""Tests del servicio de contacto LAIM."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def _load_contact_service():
    import importlib.util
    import sys
    from pathlib import Path

    module_path = (
        Path(__file__).resolve().parents[1]
        / "laim_contact_service.py"
    )
    spec = importlib.util.spec_from_file_location("laim_contact_service_test", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_contact_service_test"] = module
    spec.loader.exec_module(module)
    return module


def test_create_contact_message_success_without_image() -> None:
    module = _load_contact_service()
    repository = MagicMock()
    repository.create_message_with_image.return_value = (42, None)
    service = module.LaimContactService(repository=repository)

    result = service.create_contact_message(
        {
            "usage_mode": "local",
            "affected_user_info": "usuario_demo",
            "message_body": "Descripción suficientemente larga del problema.",
            "reply_email": "user@example.com",
        }
    )

    assert result["success"] is True
    assert result["message_id"] == 42
    assert result["numero_caso"] == 42
    assert result["id_estado"] == 1
    assert result["image_id"] is None
    call_kwargs = repository.create_message_with_image.call_args.kwargs
    assert call_kwargs["id_estado"] == 1


def test_create_contact_message_rejects_invalid_usage_mode() -> None:
    module = _load_contact_service()
    service = module.LaimContactService(repository=MagicMock())

    result = service.create_contact_message(
        {
            "usage_mode": "invalid",
            "message_body": "Descripción suficientemente larga del problema.",
            "reply_email": "user@example.com",
        }
    )

    assert result["success"] is False
    assert "Modo de uso" in result["error"]


def test_create_contact_message_with_png_screenshot() -> None:
    module = _load_contact_service()
    repository = MagicMock()
    repository.create_message_with_image.return_value = (7, 3)
    service = module.LaimContactService(repository=repository)

    png_bytes = b"\x89PNG\r\n\x1a\n"
    encoded = base64.b64encode(png_bytes).decode("ascii")

    result = service.create_contact_message(
        {
            "usage_mode": "remote",
            "affected_user_info": "",
            "message_body": "No puedo conectar con el servidor remoto.",
            "reply_email": "ops@example.com",
            "screenshot": {
                "file_name": "error.png",
                "mime_type": "image/png",
                "data_base64": encoded,
            },
        }
    )

    assert result["success"] is True
    assert result["message_id"] == 7
    assert result["numero_caso"] == 7
    assert result["id_estado"] == 1
    assert result["image_id"] == 3
    assert repository.create_message_with_image.call_args.kwargs["id_estado"] == 1


def test_list_support_messages_rejects_unknown_estado() -> None:
    module = _load_contact_service()
    service = module.LaimContactService(repository=MagicMock())

    result = service.list_support_messages(estado_clave="inventado")

    assert result["success"] is False
    assert result["items"] == []


def test_list_support_messages_delegates_to_repository() -> None:
    module = _load_contact_service()
    repository = MagicMock()
    repository.list_messages.return_value = [{"id": 1, "estado_clave": "abierto"}]
    service = module.LaimContactService(repository=repository)

    result = service.list_support_messages(estado_clave="abierto", query="ana")

    assert result["success"] is True
    assert result["items"][0]["id"] == 1
    repository.list_messages.assert_called_once()
    assert repository.list_messages.call_args.kwargs["estado_clave"] == "abierto"
    assert repository.list_messages.call_args.kwargs["query"] == "ana"


def test_update_support_estado_maps_clave_and_rejects_unknown() -> None:
    module = _load_contact_service()
    repository = MagicMock()
    repository.update_estado.return_value = {"id": 4, "id_estado": 5, "estado_clave": "descartado"}
    service = module.LaimContactService(repository=repository)

    ok = service.update_support_estado(4, "descartado", actor="laim_maintenance")
    assert ok["success"] is True
    assert repository.update_estado.call_args.kwargs["id_estado"] == 5

    bad = service.update_support_estado(4, "no-existe")
    assert bad["success"] is False


def test_get_support_message_not_found() -> None:
    module = _load_contact_service()
    repository = MagicMock()
    repository.get_with_image.return_value = None
    service = module.LaimContactService(repository=repository)

    result = service.get_support_message(99)
    assert result["success"] is False

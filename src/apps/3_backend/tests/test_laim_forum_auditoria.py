"""Hooks de auditoría en creación de hilos y respuestas."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")
    monkeypatch.setenv("laim_forum_active", "true")


def _load_forum():
    module_path = Path(__file__).resolve().parents[1] / "laim_forum_service.py"
    spec = importlib.util.spec_from_file_location("laim_forum_service_auditoria_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_forum_service_auditoria_test"] = module
    spec.loader.exec_module(module)
    return module


def _session() -> dict:
    return {
        "user_id": 10,
        "user_name": "demo_user",
        "organization_id": 1,
        "identity_type_id": 4,
    }


def _ok_repo() -> MagicMock:
    repository = MagicMock()
    repository.is_user_banned.return_value = False
    repository.get_subcategory.return_value = {"id": "general", "activa": True}
    repository.list_allowed_urls.return_value = []
    repository.list_word_rules.return_value = []
    return repository


def test_create_thread_writes_crear_hilo() -> None:
    module = _load_forum()
    repository = _ok_repo()
    repository.create_thread.return_value = 42
    auditoria = MagicMock()
    service = module.LaimForumService(
        repository=repository, image_storage=MagicMock(), auditoria=auditoria
    )
    result = service.create_thread(
        {
            "subcategory_id": "general",
            "titulo": "Hilo de prueba",
            "cuerpo_md": "Contenido del hilo de prueba",
        },
        _session(),
    )
    assert result["success"] is True
    assert result["thread_id"] == 42
    kwargs = auditoria.safe_record_foro.call_args.kwargs
    assert kwargs["accion"] == "crear_hilo"
    assert kwargs["thread_id"] == 42
    assert kwargs["user_id"] == 10


def test_create_post_writes_crear_respuesta() -> None:
    module = _load_forum()
    repository = _ok_repo()
    repository.get_thread.return_value = {
        "id": 42,
        "user_id": 10,
        "user_name": "demo_user",
        "titulo": "Hilo",
        "subcategory_id": "general",
        "cerrado": False,
    }
    repository.create_post.return_value = 7
    auditoria = MagicMock()
    service = module.LaimForumService(
        repository=repository, image_storage=MagicMock(), auditoria=auditoria
    )
    result = service.create_post(42, {"cuerpo_md": "Una respuesta"}, _session())
    assert result["success"] is True
    kwargs = auditoria.safe_record_foro.call_args.kwargs
    assert kwargs["accion"] == "crear_respuesta"
    assert kwargs["post_id"] == 7


def test_create_thread_succeeds_when_auditoria_raises() -> None:
    module = _load_forum()
    repository = _ok_repo()
    repository.create_thread.return_value = 3
    auditoria = MagicMock()
    auditoria.safe_record_foro.side_effect = RuntimeError("down")
    service = module.LaimForumService(
        repository=repository, image_storage=MagicMock(), auditoria=auditoria
    )
    result = service.create_thread(
        {
            "subcategory_id": "general",
            "titulo": "Hilo de prueba",
            "cuerpo_md": "Contenido del hilo de prueba",
        },
        _session(),
    )
    assert result["success"] is True
    assert result["thread_id"] == 3

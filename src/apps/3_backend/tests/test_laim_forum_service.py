"""Tests del servicio de foro LAIM."""

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


def _load_forum_service():
    module_path = Path(__file__).resolve().parents[1] / "laim_forum_service.py"
    spec = importlib.util.spec_from_file_location("laim_forum_service_test", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_forum_service_test"] = module
    spec.loader.exec_module(module)
    return module


def _session() -> dict:
    return {
        "user_id": 10,
        "user_name": "demo_user",
        "organization_id": 1,
        "identity_type_id": 4,
    }


def test_get_health_with_mock_repository() -> None:
    module = _load_forum_service()
    repository = MagicMock()
    repository.get_health_stats.return_value = {
        "categorias": 2,
        "subcategorias": 5,
        "hilos": 12,
        "respuestas": 40,
    }
    service = module.LaimForumService(repository=repository, image_storage=MagicMock())

    result = service.get_health()

    assert result["success"] is True
    assert result["activo"] is True
    assert result["hilos"] == 12


def test_create_thread_rejects_banned_user() -> None:
    module = _load_forum_service()
    repository = MagicMock()
    repository.is_user_banned.return_value = True
    service = module.LaimForumService(repository=repository, image_storage=MagicMock())

    result = service.create_thread(
        {
            "subcategory_id": "general",
            "titulo": "Hilo de prueba",
            "cuerpo_md": "Contenido del hilo de prueba",
        },
        _session(),
    )

    assert result["success"] is False
    assert "baneado" in result["error"].lower()
    repository.create_thread.assert_not_called()


def test_rate_post_rejects_self_rating() -> None:
    module = _load_forum_service()
    repository = MagicMock()
    repository.get_post.return_value = {
        "id": 1,
        "thread_id": 2,
        "user_id": 10,
        "user_name": "demo_user",
        "cuerpo_md": "texto",
    }
    service = module.LaimForumService(repository=repository, image_storage=MagicMock())

    result = service.rate_post(1, {"valoracion": 5}, _session())

    assert result["success"] is False
    repository.upsert_post_rating.assert_not_called()


def test_admin_only_upsert_category() -> None:
    module = _load_forum_service()
    repository = MagicMock()
    service = module.LaimForumService(repository=repository, image_storage=MagicMock())
    session = _session()

    denied = service.upsert_category(
        {"id": "cat1", "nombre": "General", "descripcion": "", "orden": 1, "activa": True},
        session,
    )
    assert denied["success"] is False

    session["identity_type_id"] = 1
    allowed = service.upsert_category(
        {"id": "cat1", "nombre": "General", "descripcion": "", "orden": 1, "activa": True},
        session,
    )
    assert allowed["success"] is True
    repository.upsert_category.assert_called_once()

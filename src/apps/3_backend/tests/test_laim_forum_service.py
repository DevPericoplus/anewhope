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


def test_rate_thread_rejects_self_rating() -> None:
    module = _load_forum_service()
    repository = MagicMock()
    repository.get_thread.return_value = {
        "id": 5,
        "user_id": 10,
        "user_name": "demo_user",
        "titulo": "Hilo",
        "cuerpo_md": "texto",
        "rating_avg": 0.0,
        "rating_count": 0,
    }
    service = module.LaimForumService(repository=repository, image_storage=MagicMock())

    result = service.rate_thread(5, {"valoracion": 4}, _session())

    assert result["success"] is False
    repository.upsert_thread_rating.assert_not_called()


def test_rate_thread_updates_aggregate() -> None:
    module = _load_forum_service()
    repository = MagicMock()
    repository.get_thread.side_effect = [
        {
            "id": 5,
            "user_id": 99,
            "user_name": "autor",
            "titulo": "Hilo",
            "cuerpo_md": "texto",
            "rating_avg": 0.0,
            "rating_count": 0,
        },
        {
            "id": 5,
            "user_id": 99,
            "user_name": "autor",
            "titulo": "Hilo",
            "cuerpo_md": "texto",
            "rating_avg": 4.0,
            "rating_count": 1,
        },
    ]
    service = module.LaimForumService(repository=repository, image_storage=MagicMock())

    result = service.rate_thread(5, {"valoracion": 4}, _session())

    assert result["success"] is True
    assert result["my_rating"] == 4
    assert result["thread"]["rating_avg"] == 4.0
    repository.upsert_thread_rating.assert_called_once_with(
        thread_id=5,
        user_id=10,
        valoracion=4,
    )


def test_get_thread_includes_my_rating_when_session() -> None:
    module = _load_forum_service()
    repository = MagicMock()
    repository.get_thread.return_value = {
        "id": 5,
        "user_id": 99,
        "rating_avg": 3.5,
        "rating_count": 2,
    }
    repository.get_user_thread_rating.return_value = 4
    service = module.LaimForumService(repository=repository, image_storage=MagicMock())

    result = service.get_thread(5, _session())

    assert result["success"] is True
    assert result["thread"]["my_rating"] == 4
    repository.get_user_thread_rating.assert_called_once_with(5, 10)


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


def test_forum_persistence_does_not_use_json_files() -> None:
    """El subsistema foro no persiste datos en ficheros JSON."""
    import re

    repo_root = Path(__file__).resolve().parents[3]
    repo_path = repo_root / "2_shared_application/adapters/laim_forum_repository.py"
    service_path = repo_root / "apps/3_backend/laim_forum_service.py"
    mixin_path = repo_root / "apps/9_laimweb/laim_web/laim_forum_mixin.py"

    json_file_pattern = re.compile(r"""['"][^'"]+\.json['"]""")

    for path in (repo_path, service_path, mixin_path):
        source = path.read_text(encoding="utf-8")
        assert "json.load" not in source
        assert "json.dump" not in source
        assert json_file_pattern.search(source) is None

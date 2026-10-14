"""Tests TDD del servicio de auditoría del portal."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def _load_service():
    module_path = Path(__file__).resolve().parents[1] / "laim_auditoria_service.py"
    spec = importlib.util.spec_from_file_location("laim_auditoria_service_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_auditoria_service_test"] = module
    spec.loader.exec_module(module)
    return module


def test_heartbeat_requires_session() -> None:
    module = _load_service()
    service = module.LaimAuditoriaService(repository=MagicMock())
    result = service.heartbeat(0, "")
    assert result["success"] is False
    assert "sesión" in result["error"].lower()


def test_instalador_allows_anonymous() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.record_instalador.return_value = 4
    service = module.LaimAuditoriaService(repository=repository)
    result = service.record_instalador(
        "copia_script",
        "community_edition",
        "mac_silicon",
        user_id=None,
    )
    assert result["success"] is True
    assert repository.record_instalador.call_args.kwargs["user_id"] is None


def test_empty_source_does_not_record_download() -> None:
    module = _load_service()
    repository = MagicMock()
    service = module.LaimAuditoriaService(repository=repository)
    result = service.record_download_if_source(
        "",
        "community_edition",
        "linux_deb",
        version="2.0.1",
        filename="laim.deb",
    )
    assert result["skipped"] is True
    repository.record_instalador.assert_not_called()


def test_install_script_source_records_download() -> None:
    module = _load_service()
    repository = MagicMock()
    repository.record_instalador.return_value = 8
    service = module.LaimAuditoriaService(repository=repository)
    result = service.record_download_if_source(
        "install-script",
        "community_edition",
        "linux_deb",
        version="2.0.1",
        filename="laim.deb",
        user_id=None,
    )
    assert result["success"] is True
    assert repository.record_instalador.call_args.args[0] == "descarga"


def test_heartbeat_skips_when_too_soon() -> None:
    module = _load_service()
    repository = MagicMock()
    now = datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)
    repository.get_latest_visita.return_value = {
        "id": 1,
        "last_seen_at": now - timedelta(seconds=10),
    }
    service = module.LaimAuditoriaService(repository=repository)
    result = service.heartbeat(9, "sess-a", seccion="home", now=now)
    assert result["skipped"] is True
    repository.upsert_visita.assert_not_called()


def test_invalid_seccion_rejected() -> None:
    module = _load_service()
    service = module.LaimAuditoriaService(repository=MagicMock())
    result = service.change_seccion(9, "sess-a", "inventada")
    assert result["success"] is False

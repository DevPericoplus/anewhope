"""Tests del acceso a datos de negocio via Broker (sin MariaDB)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_TRAINER_DIR = Path(__file__).resolve().parent.parent
if str(_TRAINER_DIR) not in sys.path:
    sys.path.insert(0, str(_TRAINER_DIR))


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla el Trainer de MariaDB y fuerza URL del Broker."""
    monkeypatch.setenv("STORAGE_MODE", "mock")
    monkeypatch.setenv("BROKER_BACKEND_BASE_URL", "http://broker.test:8008")


def test_broker_client_prefers_env_url(mock_env: None) -> None:
    """El cliente del Trainer usa BROKER_BACKEND_BASE_URL, no protected_values."""
    from broker_client import TrainerBrokerClient

    client = TrainerBrokerClient()
    assert client._broker_url == "http://broker.test:8008"


def test_fetch_job_context_uses_broker(mock_env: None) -> None:
    """Las lecturas de nombres van al Broker, no a pymysql."""
    from trainer_core_lookup import fetch_job_context

    fake = MagicMock()
    fake.get_job_context.return_value = {
        "organization_name": "Acme",
        "project_name": "Demo",
        "prompt": "fusion",
        "prompt_name": "formateador_documental_documentos",
    }

    result = fetch_job_context(
        organization_id=1,
        project_id=2,
        prompt_name="formateador_documental_documentos",
        client=fake,
    )

    fake.get_job_context.assert_called_once_with(
        organization_id=1,
        project_id=2,
        prompt_name="formateador_documental_documentos",
        owner_user_id=0,
    )
    assert result["organization_name"] == "Acme"
    assert result["prompt"] == "fusion"


def test_notify_job_complete_uses_broker(mock_env: None) -> None:
    """El cierre de jobs se envía al Broker."""
    from trainer_core_lookup import notify_job_complete

    fake = MagicMock()
    fake.complete_job.return_value = {"success": True, "id_cambio": 9}

    result = notify_job_complete(
        job_id=5,
        id_organizacion=1,
        id_proyecto=2,
        id_version=3,
        descripcion="ok",
        referencia_salida="/tmp/out.md",
        tipo_cambio="evaluacion_documental",
        client=fake,
    )

    fake.complete_job.assert_called_once()
    assert result["success"] is True


def test_fetch_job_context_fallback_on_error(mock_env: None) -> None:
    """Si el Broker falla, se devuelve fallback sin lanzar."""
    from broker_client import TrainerBrokerClientError
    from trainer_core_lookup import fetch_job_context

    fake = MagicMock()
    fake.get_job_context.side_effect = TrainerBrokerClientError("down")

    result = fetch_job_context(organization_id=7, project_id=8, client=fake)
    assert result["organization_name"] == "Organización 7"
    assert result["project_name"] == "Proyecto 8"
    assert result["prompt"] == ""
    assert result["account_folder"] == "ORG00007"


def test_resolve_account_folder_uses_core_folder(mock_env: None) -> None:
    """La carpeta de cuenta la resuelve Core, no el Trainer."""
    from trainer_core_lookup import resolve_account_folder

    fake = MagicMock()
    fake.get_job_context.return_value = {
        "organization_id": 0,
        "owner_user_id": 9,
        "account_folder": "USER00009",
        "organization_name": "",
        "project_name": "Demo",
        "prompt": "",
    }

    folder, ctx = resolve_account_folder(
        organization_id=0,
        owner_user_id=9,
        project_id=4,
        client=fake,
    )

    fake.get_job_context.assert_called_once_with(
        organization_id=0,
        project_id=4,
        prompt_name="",
        owner_user_id=9,
    )
    assert folder == "USER00009"
    assert ctx["account_folder"] == "USER00009"


def test_resolve_account_folder_fallback_local_helper(mock_env: None) -> None:
    """Si Core no envía carpeta, se usa el helper compartido."""
    from broker_client import TrainerBrokerClientError
    from trainer_core_lookup import resolve_account_folder

    fake = MagicMock()
    fake.get_job_context.side_effect = TrainerBrokerClientError("down")

    folder, ctx = resolve_account_folder(
        organization_id=0,
        owner_user_id=12,
        project_id=3,
        client=fake,
    )
    assert folder == "USER00012"
    assert ctx["account_folder"] == "USER00012"

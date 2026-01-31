"""Tests de integración frontend ↔ middleware."""

from __future__ import annotations

import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from adapters import api_client


@dataclass
class DummyUserExtended:
    """Representación mínima de UserExtended para pruebas."""

    id: int
    id_org: int
    id_type: int
    user_name: str
    user_password: str
    user_email: str
    user_mobile: str
    user_otp: str
    active: bool
    blocked: bool
    contact_info: Any
    billing_info: Any


@dataclass
class DummyContactInfo:
    """Contacto mínimo."""

    first_name: str
    sur_name: str
    country: str
    state: str
    zip_code: str
    address: str


@pytest.fixture
def middleware_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Crea un cliente de prueba del middleware."""

    users_path = tmp_path / "users.json"
    orgs_path = tmp_path / "organizations.json"
    roles_path = tmp_path / "manage_roles_by_org.json"
    log_path = tmp_path / "middleware_secure.log"

    users_path.write_text("[]", encoding="utf-8")
    orgs_path.write_text("[]", encoding="utf-8")
    roles_path.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("USERS_DATA_PATH", str(users_path))
    monkeypatch.setenv("ORGANIZATIONS_DATA_PATH", str(orgs_path))
    monkeypatch.setenv("MANAGE_ROLES_BY_ORG_PATH", str(roles_path))
    monkeypatch.setenv("SECURITY_LOG_PATH", str(log_path))
    monkeypatch.setenv("STORAGE_MODE", "mock")

    service_dir = Path(__file__).resolve().parents[2] / "7_service_frontend"
    if str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))

    middleware_apife = importlib.import_module("apife")
    return TestClient(middleware_apife.app)


def _request_via_client(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    response = client.request(method, path, json=payload, headers=headers)
    if response.status_code >= 400:
        return {}
    return response.json()


def test_frontend_creates_org_and_user(middleware_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica alta de organización y usuario vía middleware."""

    monkeypatch.setattr(
        api_client,
        "_request_middleware",
        lambda method, path, payload=None, headers=None: _request_via_client(
            middleware_client, method, path, payload, headers
        ),
    )

    assert api_client.check_organization_name_exists("Acme") is False

    org_id = api_client.save_organization_to_json(
        {
            "organization_name": "Acme",
            "organization_email": "acme@example.com",
            "organization_tlf": "+34000000000",
            "organization_address": "Calle Uno",
            "organization_country": "España",
            "organization_state": "Madrid",
        }
    )
    assert org_id == 1
    assert api_client.check_organization_name_exists("Acme") is True

    contact = DummyContactInfo(
        first_name="Test",
        sur_name="User",
        country="España",
        state="Madrid",
        zip_code="28001",
        address="Calle Uno",
    )
    # Nota: id_type=None para que el middleware asigne automáticamente
    # identity_type_id=2 (admin) al primer usuario de la organización.
    # Si se especifica id_type=5, el middleware lo respeta (auditor).
    user_extended = DummyUserExtended(
        id=1,
        id_org=org_id,
        id_type=None,  # Primer usuario → será admin (2) automáticamente
        user_name="demo",
        user_password="secret",
        user_email="demo@example.com",
        user_mobile="+34000000001",
        user_otp="1234",
        active=True,
        blocked=False,
        contact_info=contact,
        billing_info=contact,
    )

    assert api_client.save_user_to_json(user_extended) is True

    roles_path = Path(os.environ["MANAGE_ROLES_BY_ORG_PATH"])
    roles = json.loads(roles_path.read_text(encoding="utf-8"))
    assert roles[0]["id_organization"] == org_id
    # El primer usuario de una organización nueva es admin (2)
    assert roles[0]["identity_type_id"] == 2


def test_frontend_security_log_calls_middleware(
    middleware_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifica que el frontend envía logs al middleware."""

    monkeypatch.setattr(
        api_client,
        "_request_middleware",
        lambda method, path, payload=None, headers=None: _request_via_client(
            middleware_client, method, path, payload, headers
        ),
    )

    result = api_client.log_security_action(
        "Created user", 123, "10.0.0.1", "pytest"
    )
    assert result is True

"""Tests para creación automática de agentes."""

import json
from pathlib import Path

from src.2_shared_application.security.add_agents_by_proyects import (
    add_agents_for_project,
)


def _write_users(path: Path, users: list[dict]) -> None:
    path.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def test_add_agents_for_project_creates_four_agents(tmp_path, monkeypatch):
    """Genera cuatro agentes con roles esperados."""

    users_path = tmp_path / "users.json"
    _write_users(
        users_path,
        [
            {
                "user_id": 1,
                "organization_id": 10,
                "identity_type_id": 2,
                "user_name": "admin_org",
                "contact_info": {
                    "country": "Oceano",
                    "state": "Oceano",
                    "zip_code": "Oceano",
                    "address": "Oceano",
                },
            }
        ],
    )
    monkeypatch.setenv("STORAGE_MODE", "mock")

    agents = add_agents_for_project(
        organization_id=10,
        organization_name="Oceano",
        project_name="Playa",
        users_path=users_path,
        encrypt_password=lambda value: f"enc-{value}",
        otp_generator=lambda: "1234",
    )

    assert len(agents) == 4
    assert {agent["identity_type_id"] for agent in agents} == {10, 11, 12, 13}
    assert agents[0]["user_id"] == 2
    assert agents[1]["user_id"] == 3
    assert agents[0]["user_email"].endswith("@myllm.ai")
    assert agents[0]["contact_info"]["country"] == "Oceano"

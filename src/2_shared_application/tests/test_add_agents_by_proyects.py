"""Tests para creación automática de agentes."""

import importlib.util
import json
import sys
from pathlib import Path


def _load_env_settings_module() -> object:
    """Carga el módulo de configuración de entorno."""

    module_path = (
        Path(__file__).resolve().parents[2]
        / "2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location("env_settings", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar env_settings.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["env_settings"] = module
    spec.loader.exec_module(module)
    return module


def _load_add_agents_module() -> object:
    """Carga el módulo de agentes desde ruta."""

    # Primero cargar las variables de entorno
    env_settings = _load_env_settings_module()
    env_settings.load_env_file()
    
    module_path = (
        Path(__file__).resolve().parents[2]
        / "2_shared_application/security/add_agents_by_proyects.py"
    )
    spec = importlib.util.spec_from_file_location(
        "shared_add_agents_by_proyects", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar add_agents_by_proyects")
    module = importlib.util.module_from_spec(spec)
    sys.modules["shared_add_agents_by_proyects"] = module
    spec.loader.exec_module(module)
    return module


def _write_users(path: Path, users: list[dict]) -> None:
    path.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def test_add_agents_for_project_creates_four_agents(tmp_path, monkeypatch):
    """Genera cuatro agentes con roles esperados."""

    add_agents_module = _load_add_agents_module()
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

    agents = add_agents_module.add_agents_for_project(
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

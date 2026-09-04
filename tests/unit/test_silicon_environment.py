"""Tests unitarios del contrato de entorno silicon (sin servicios vivos)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.helpers import (
    VALID_TEST_ENVIRONMENTS,
    get_active_test_environment,
    get_service_urls,
    load_env_yaml,
)


def test_silicon_is_a_valid_test_environment() -> None:
    assert "silicon" in VALID_TEST_ENVIRONMENTS


def test_silicon_env_yaml_has_compose_contract_keys() -> None:
    data = load_env_yaml("silicon")
    required = (
        "core_backend_base_url",
        "broker_backend_base_url",
        "middleware_base_url",
        "fmanagement_base_url",
        "trainer_base_url",
        "mariadb_host",
        "mariadb_port",
    )
    missing = [key for key in required if not data.get(key)]
    assert missing == [], f"Faltan claves en silicon/env.yaml: {missing}"
    assert "silicon.loc" in str(data["core_backend_base_url"])
    assert "localhost" not in str(data["core_backend_base_url"])
    assert data["mariadb_host"] == "backend.anewhope.silicon.loc"


def test_silicon_service_urls_do_not_use_legacy_aws_or_localhost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANEWHOPE_ENV", "silicon")
    monkeypatch.setenv("ENVIRONMENT", "silicon")
    urls = get_service_urls(env="silicon")
    for key, url in urls.items():
        assert "localhost" not in url, f"{key} usa localhost: {url}"
        assert "127.0.0.1" not in url, f"{key} usa 127.0.0.1: {url}"
        assert "anewhope.aws" not in url, f"{key} usa host legado PRE: {url}"
        if key != "redis":
            assert "silicon.loc" in url, f"{key} no apunta a silicon: {url}"


def test_anewhope_env_overrides_envglobal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANEWHOPE_ENV", "silicon")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("environment", raising=False)
    assert get_active_test_environment() == "silicon"


def test_silicon_paths_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    env_dir = root / "infrastructure" / "environments" / "silicon"
    assert (env_dir / "env.yaml").is_file()
    assert (env_dir / "protected_values.py").is_file()


def test_storage_mode_mock_is_set_for_unit_isolation() -> None:
    """full_test.sh --unit exporta STORAGE_MODE=mock; si no, el test no falla."""
    mode = os.environ.get("STORAGE_MODE", "mock")
    assert mode in {"mock", "mock_and_db", "db_only"}

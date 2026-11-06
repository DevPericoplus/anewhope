"""GET /laim/captcha/health: solo el estado, sin hosts, y con caché corta."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def _load_router():
    path = Path(__file__).resolve().parents[1] / "router_laim_auth.py"
    spec = importlib.util.spec_from_file_location("router_laim_auth_health_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["router_laim_auth_health_test"] = module
    spec.loader.exec_module(module)
    return module


def _client(module) -> TestClient:
    app = FastAPI()
    app.include_router(module.router)
    return TestClient(app)


def test_health_returns_only_status_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_router()
    cap = module._laim_auth_module._cap_siteverify
    calls = []

    def fake_check(config, logger):
        calls.append(config)
        return cap.CapHealthResult("down", "Cap frontend.example.loc:3301: /health 503")

    monkeypatch.setattr(cap, "check_health", fake_check)
    monkeypatch.setattr(module.LaimAuthService, "_cap_config", staticmethod(lambda: cap.CapConfig()))
    module._cap_health_cache.update({"at": 0.0, "status": ""})
    client = _client(module)

    first = client.get("/laim/captcha/health")
    second = client.get("/laim/captcha/health")

    assert first.status_code == 200
    assert first.json() == {"status": "down"}
    assert "frontend" not in first.text
    assert second.json() == {"status": "down"}
    assert len(calls) == 1


def test_health_never_fails_the_request(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_router()

    def boom():
        raise RuntimeError("config rota")

    monkeypatch.setattr(module.LaimAuthService, "_cap_config", staticmethod(boom))
    module._cap_health_cache.update({"at": 0.0, "status": ""})
    response = _client(module).get("/laim/captcha/health")
    assert response.status_code == 200
    assert response.json() == {"status": "unknown"}

"""Tests de integración ASGI del endurecimiento de APIs en el borde."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[4]
_MODULE_PATH = _ROOT / "src/2_shared_application/security/api_hardening.py"


def _load_hardening():
    name = "api_hardening_asgi_test"
    spec = importlib.util.spec_from_file_location(name, _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # noqa: SLF001 — carga TDD aislada
    return module


@pytest.fixture
def hardening():
    return _load_hardening()


def _edge_app(hardening, *, environment: str = "silicon", rate_limit: bool = True) -> FastAPI:
    app = FastAPI(title="edge-test")

    @app.get("/ok")
    def ok() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/login")
    def login() -> dict[str, str]:
        return {"status": "accepted"}

    @app.get("/boom")
    def boom() -> dict[str, str]:
        raise RuntimeError("dsn=mysql://secret@backend/myllm_core_db")

    @app.get("/denied")
    def denied() -> dict[str, str]:
        raise HTTPException(status_code=403, detail="Sin permiso")

    settings = hardening.ApiHardeningSettings(
        service_name="middleware",
        environment=environment,
        rate_limit_enabled=rate_limit,
        edge_limit=5,
        auth_limit=2,
        json_max_bytes=64,
    )
    limiter = hardening.SlidingWindowRateLimiter(limit=5, window_seconds=60.0)
    app.add_middleware(
        hardening.ApiHardeningMiddleware,
        settings=settings,
        limiter=limiter,
    )
    return app


def test_security_headers_on_success(hardening) -> None:
    client = TestClient(_edge_app(hardening, rate_limit=False))
    response = client.get("/ok")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]


def test_rate_limit_returns_429_with_retry_after(hardening) -> None:
    client = TestClient(_edge_app(hardening, rate_limit=True))
    assert client.get("/ok").status_code == 200
    assert client.get("/ok").status_code == 200
    assert client.get("/ok").status_code == 200
    assert client.get("/ok").status_code == 200
    assert client.get("/ok").status_code == 200
    limited = client.get("/ok")
    assert limited.status_code == 429
    assert limited.headers["retry-after"]
    assert "Demasiadas" in limited.json()["detail"]


def test_auth_bucket_is_stricter_than_generic(hardening) -> None:
    client = TestClient(_edge_app(hardening, rate_limit=True))
    assert client.post("/login").status_code == 200
    assert client.post("/login").status_code == 200
    assert client.post("/login").status_code == 429
    assert client.get("/ok").status_code == 200


def test_oversized_json_is_413(hardening) -> None:
    client = TestClient(_edge_app(hardening, rate_limit=False))
    response = client.post("/login", content=b"x" * 80, headers={"content-type": "application/json"})
    assert response.status_code == 413


def test_http_exception_is_not_rewritten(hardening) -> None:
    client = TestClient(_edge_app(hardening, rate_limit=False))
    response = client.get("/denied")
    assert response.status_code == 403
    assert response.json()["detail"] == "Sin permiso"


def test_unhandled_500_is_sanitized_in_silicon(hardening, monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")
    app = FastAPI()

    @app.get("/boom")
    def boom() -> dict[str, str]:
        raise RuntimeError("dsn=mysql://secret@backend/myllm_core_db")

    hardening.harden_fastapi_app(app, service_name="middleware", environment="silicon")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
    assert "secret" not in response.json()["detail"]
    assert "mysql" not in response.json()["detail"]

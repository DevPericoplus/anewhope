"""Tests del endpoint de logging de seguridad en el middleware."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import importlib.util
import sys


class DummyInterface:
    """Interfaz dummy para el middleware."""

    async def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Devuelve el payload sin cambios."""

        return payload


def _load_apife_module() -> Any:
    """Carga el módulo apife usando importlib."""

    module_path = (
        Path(__file__).resolve().parents[1] / "apife.py"
    )
    spec = importlib.util.spec_from_file_location("apife", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar apife")
    module = importlib.util.module_from_spec(spec)
    sys.modules["apife"] = module
    spec.loader.exec_module(module)
    return module


apife = _load_apife_module()


class DummyRouter(apife.RouterMiddleware):
    """Router dummy con logging a ruta temporal."""

    def __init__(self, log_path: Path) -> None:
        super().__init__(interface=DummyInterface(), jwt_settings=apife.get_jwt_settings())
        self._log_path = log_path

    def _get_security_log_path(self) -> Path:
        return self._log_path


def _create_test_app(log_path: Path) -> FastAPI:
    """Crea una app de prueba inyectando router dummy."""

    app = FastAPI()

    def _get_router() -> DummyRouter:
        return DummyRouter(log_path)

    app.dependency_overrides[apife.get_router_middleware] = _get_router
    app.include_router(apife.app.router)
    return app


def test_security_log_endpoint_writes_log(tmp_path: Path) -> None:
    """Verifica que el endpoint escribe el log de seguridad."""

    log_path = tmp_path / "middleware_secure.log"
    client = TestClient(_create_test_app(log_path))

    response = client.post(
        "/security/log",
        json={
            "action": "Created user",
            "entity_id": 123,
            "ip": "10.0.0.1",
            "user_agent": "pytest",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "Created user" in content
    assert "10.0.0.1" in content
    assert "pytest" in content

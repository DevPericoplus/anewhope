"""Tests del log de actividad del middleware."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient


class DummyInterface:
    """Interfaz dummy para el middleware."""

    async def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Devuelve el payload sin cambios."""

        return payload


def _load_apife_module() -> Any:
    """Carga el módulo apife usando importlib."""

    module_path = Path(__file__).resolve().parents[1] / "apife.py"
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

    def _get_activity_log_path(self) -> Path:
        return self._log_path


def _create_test_app(log_path: Path) -> FastAPI:
    """Crea una app de prueba inyectando router dummy."""

    app = FastAPI()

    def _get_router() -> DummyRouter:
        return DummyRouter(log_path)

    app.dependency_overrides[apife.get_router_middleware] = _get_router
    app.include_router(apife.app.router)
    return app


def test_activity_log_writes_entry(tmp_path: Path, monkeypatch: Any) -> None:
    """Verifica que las operaciones escriben el log de actividad."""

    log_path = tmp_path / "middleware_activiy.log"
    orgs_path = tmp_path / "organizations.json"
    orgs_path.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("ORGANIZATIONS_DATA_PATH", str(orgs_path))

    client = TestClient(_create_test_app(log_path))
    response = client.post(
        "/organizations/check-name",
        json={"organization_name": "demo"},
    )

    assert response.status_code == 200
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "Validar organización" in content

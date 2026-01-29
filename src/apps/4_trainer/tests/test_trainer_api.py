"""Tests de integración para el backend IA (trainer).

Este módulo contiene tests para verificar:
- Endpoints de la API del trainer
- Propagación del header X-Client-App
- Validación de permisos de entrenamiento
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _load_trainer_app():
    """Carga el módulo apitrainer dinámicamente (evita error por nombre numérico)."""
    module_path = Path(__file__).resolve().parent.parent / "apitrainer.py"
    spec = importlib.util.spec_from_file_location("apitrainer_test", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar apitrainer")
    module = importlib.util.module_from_spec(spec)
    sys.modules["apitrainer_test"] = module
    spec.loader.exec_module(module)
    return module.app


@pytest.fixture
def mock_env(monkeypatch):
    """Configura variables de entorno para tests."""
    monkeypatch.setenv("STORAGE_MODE", "mock")
    monkeypatch.setenv("FMANAGEMENT_BASE_URL", "http://localhost:1666")


@pytest.fixture
def client(mock_env):
    """Crea cliente de pruebas para la API del trainer."""
    app = _load_trainer_app()
    return TestClient(app)


class TestTrainerHealthCheck:
    """Tests del endpoint de health check."""

    def test_health_check_returns_healthy(self, client):
        """Verifica que el health check retorna estado healthy."""
        response = client.get("/trainer/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "backend-ia-trainer"
        assert "version" in data


class TestTrainerXClientApp:
    """Tests de propagación del header X-Client-App."""

    def test_endpoint_extracts_x_client_app(self, client):
        """Verifica que el endpoint extrae correctamente el header X-Client-App."""
        response = client.get(
            "/trainer/health",
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200

    def test_endpoint_works_without_x_client_app(self, client):
        """Verifica que el endpoint funciona sin el header (valor por defecto)."""
        response = client.get("/trainer/health")
        assert response.status_code == 200


class TestVersionClone:
    """Tests del endpoint de clonado de versión."""

    def test_clone_version_requires_body(self, client):
        """Verifica que el endpoint requiere body."""
        response = client.post("/trainer/version/clone")
        assert response.status_code == 422  # Validation error

    def test_clone_version_with_valid_payload(self, client):
        """Verifica clonado con payload válido."""
        payload = {
            "id_user": 1,
            "id_organization": 1,
            "id_project": 1,
            "version_path": "V001",
        }
        response = client.post(
            "/trainer/version/clone",
            json=payload,
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestTrainingOperations:
    """Tests de operaciones de entrenamiento."""

    def test_start_training_requires_body(self, client):
        """Verifica que start_training requiere body."""
        response = client.post("/trainer/training/start")
        assert response.status_code == 422

    def test_start_training_with_valid_payload(self, client):
        """Verifica inicio de entrenamiento con payload válido."""
        payload = {
            "id_user": 1,
            "id_organization": 1,
            "id_project": 1,
            "version_path": "V001",
        }
        response = client.post(
            "/trainer/training/start",
            json=payload,
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_stop_training_requires_training_id(self, client):
        """Verifica que stop_training requiere training_id."""
        response = client.post("/trainer/training/stop", json={})
        assert response.status_code == 422

    def test_get_training_status(self, client):
        """Verifica obtención de estado de entrenamiento."""
        response = client.get(
            "/trainer/training/1/status",
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "training_id" in data
        assert "status" in data


class TestModels:
    """Tests de operaciones de modelos."""

    def test_list_models(self, client):
        """Verifica listado de modelos."""
        response = client.get(
            "/trainer/models",
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "total" in data

    def test_get_model_metrics(self, client):
        """Verifica obtención de métricas de modelo."""
        response = client.get(
            "/trainer/models/1/metrics",
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "model_id" in data
        assert "metrics" in data


class TestTrainingPermissions:
    """Tests de permisos de entrenamiento."""

    def test_get_permissions_requires_identity_type_id(self, client):
        """Verifica que se requiere identity_type_id."""
        response = client.get("/trainer/permissions")
        assert response.status_code == 422

    def test_get_permissions_with_valid_role(self, client):
        """Verifica obtención de permisos con rol válido."""
        response = client.get(
            "/trainer/permissions?identity_type_id=1",
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["identity_type_id"] == 1
        assert "permissions" in data
        # Verifica que se retornan los permisos de entrenamiento
        permissions = data["permissions"]
        assert "training_create" in permissions
        assert "training_read" in permissions
        assert "training_start" in permissions
        assert "training_stop" in permissions

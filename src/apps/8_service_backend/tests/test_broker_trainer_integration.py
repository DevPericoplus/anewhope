"""Tests de integración Broker → Trainer.

Este módulo contiene tests para verificar:
- Integración del broker con el backend IA (trainer)
- Propagación del header X-Client-App a través del broker
- Endpoints de entrenamiento expuestos por el broker
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_env(monkeypatch):
    """Configura variables de entorno para tests."""
    monkeypatch.setenv("STORAGE_MODE", "mock")
    monkeypatch.setenv("CORE_BACKEND_BASE_URL", "http://localhost:8003")
    monkeypatch.setenv("TRAINER_BACKEND_BASE_URL", "http://localhost:8004")


@pytest.fixture
def mock_trainer_client():
    """Mock del cliente del trainer."""
    client = MagicMock()
    client.health_check.return_value = {
        "status": "healthy",
        "service": "backend-ia-trainer",
        "version": "1.0.0",
    }
    client.clone_version.return_value = {
        "success": True,
        "cloned_path": "/training/org1/prj1/V001",
        "message": "Versión clonada",
    }
    client.start_training.return_value = {
        "success": True,
        "training_id": 1,
        "message": "Entrenamiento iniciado",
    }
    client.stop_training.return_value = {
        "success": True,
        "message": "Entrenamiento detenido",
    }
    client.get_training_status.return_value = {
        "training_id": 1,
        "status": "running",
        "progress": 0.5,
        "metrics": {},
        "started_at": "2026-01-27T10:00:00",
        "finished_at": None,
    }
    client.list_models.return_value = {
        "models": [],
        "total": 0,
    }
    client.get_model_metrics.return_value = {
        "model_id": 1,
        "metrics": {"accuracy": 0.95},
        "training_history": [],
    }
    client.get_training_permissions.return_value = {
        "identity_type_id": 1,
        "permissions": {
            "training_create": True,
            "training_read": True,
            "training_start": True,
            "training_stop": True,
        },
    }
    return client


@pytest.fixture
def mock_core_client():
    """Mock del cliente del core."""
    client = MagicMock()
    client.fetch_users.return_value = []
    client.fetch_organizations.return_value = []
    client.get_permissions.return_value = {
        "identity_type_id": 1,
        "permissions": [],
        "low_level_permissions": {},
    }
    return client


@pytest.fixture
def client(mock_env, mock_core_client, mock_trainer_client):
    """Crea cliente de pruebas para la API del broker con mocks."""
    with patch(
        "src.apps.8_service_backend.apibe.get_core_client",
        return_value=mock_core_client,
    ):
        with patch(
            "src.apps.8_service_backend.apibe.get_trainer_client",
            return_value=mock_trainer_client,
        ):
            from src.apps.8_service_backend.apibe import app
            yield TestClient(app)


class TestBrokerTrainerHealth:
    """Tests del endpoint de health check del trainer vía broker."""

    def test_trainer_health_via_broker(self, client, mock_trainer_client):
        """Verifica health check del trainer a través del broker."""
        response = client.get(
            "/training/health",
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        mock_trainer_client.health_check.assert_called_once()


class TestBrokerVersionClone:
    """Tests del clonado de versión vía broker."""

    def test_clone_version_via_broker(self, client, mock_trainer_client):
        """Verifica clonado de versión a través del broker."""
        payload = {
            "id_user": 1,
            "id_organization": 1,
            "id_project": 1,
            "version_path": "V001",
        }
        response = client.post(
            "/training/clone-version",
            json=payload,
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_trainer_client.clone_version.assert_called_once()


class TestBrokerTrainingOperations:
    """Tests de operaciones de entrenamiento vía broker."""

    def test_start_training_via_broker(self, client, mock_trainer_client):
        """Verifica inicio de entrenamiento a través del broker."""
        payload = {
            "id_user": 1,
            "id_organization": 1,
            "id_project": 1,
            "version_path": "V001",
        }
        response = client.post(
            "/training/start",
            json=payload,
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["training_id"] == 1
        mock_trainer_client.start_training.assert_called_once()

    def test_stop_training_via_broker(self, client, mock_trainer_client):
        """Verifica detención de entrenamiento a través del broker."""
        payload = {
            "training_id": 1,
        }
        response = client.post(
            "/training/stop",
            json=payload,
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_trainer_client.stop_training.assert_called_once()

    def test_get_training_status_via_broker(self, client, mock_trainer_client):
        """Verifica obtención de estado a través del broker."""
        response = client.get(
            "/training/1/status",
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["training_id"] == 1
        assert data["status"] == "running"
        mock_trainer_client.get_training_status.assert_called_once()


class TestBrokerXClientAppPropagation:
    """Tests de propagación del header X-Client-App."""

    def test_x_client_app_propagated_to_trainer(self, client, mock_trainer_client):
        """Verifica que el header X-Client-App se propaga al trainer."""
        response = client.get(
            "/training/health",
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        # Verificar que set_client_app fue llamado en el cliente
        mock_trainer_client.set_client_app.assert_called()

    def test_works_without_x_client_app(self, client):
        """Verifica que funciona sin el header (valor por defecto)."""
        response = client.get("/training/health")
        assert response.status_code == 200


class TestBrokerModels:
    """Tests de operaciones de modelos vía broker."""

    def test_list_models_via_broker(self, client, mock_trainer_client):
        """Verifica listado de modelos a través del broker."""
        response = client.get(
            "/training/models",
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        mock_trainer_client.list_models.assert_called_once()

    def test_get_model_metrics_via_broker(self, client, mock_trainer_client):
        """Verifica obtención de métricas a través del broker."""
        response = client.get(
            "/training/models/1/metrics",
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == 1
        mock_trainer_client.get_model_metrics.assert_called_once()


class TestBrokerTrainingPermissions:
    """Tests de permisos de entrenamiento vía broker."""

    def test_get_training_permissions_via_broker(self, client, mock_trainer_client):
        """Verifica obtención de permisos a través del broker."""
        response = client.get(
            "/training/permissions?identity_type_id=1",
            headers={"X-Client-App": "frontend"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["identity_type_id"] == 1
        assert "permissions" in data
        mock_trainer_client.get_training_permissions.assert_called_once()

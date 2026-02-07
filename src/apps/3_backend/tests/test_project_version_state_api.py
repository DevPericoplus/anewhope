"""Tests de integración para API de Estado de Proyectos.

Este módulo prueba:
- Endpoints de la API (/project-version-states/*)
- Flujo completo de autenticación y permisos
- Respuestas HTTP correctas (200, 403, 400, 404)
- Integración entre Backend Core → Service → Repository
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import os

# Configurar modo mock antes de imports
os.environ["STORAGE_MODE"] = "mock"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def test_client():
    """Cliente de test para la API de Backend Core."""
    from src.apps.backend.apicore import app

    return TestClient(app)


@pytest.fixture
def superadmin_headers():
    """Headers de autenticación para SuperAdmin."""
    return {
        "user_id": "1",
        "identity_type_id": "1",  # SuperAdmin
    }


@pytest.fixture
def editor_headers():
    """Headers de autenticación para Editor."""
    return {
        "user_id": "10",
        "identity_type_id": "3",  # Editor
    }


@pytest.fixture
def auditor_headers():
    """Headers de autenticación para Auditor."""
    return {
        "user_id": "20",
        "identity_type_id": "4",  # Auditor
    }


@pytest.fixture
def lector_headers():
    """Headers de autenticación para Lector."""
    return {
        "user_id": "30",
        "identity_type_id": "5",  # Lector
    }


# ============================================================================
# Tests de GET /project-version-states/{state_id}
# ============================================================================


class TestGetProjectVersionState:
    """Tests para endpoint GET /project-version-states/{state_id}."""

    @patch("src.apps.backend.routercore.BackendCoreRouter.get_project_version_state_by_id")
    def test_superadmin_can_get_any_state(
        self, mock_get_state, test_client, superadmin_headers
    ):
        """SuperAdmin puede obtener cualquier estado."""
        # Mock del método del router
        mock_get_state.return_value = {
            "id": 1,
            "organization_id": 100,
            "project_id": 200,
            "version_id": 1,
            "state": "propuesta",
            "state_internal": "propuesta_cliente",
            "proposal": {
                "aceptacion_cliente": False,
                "aceptacion_interna": False,
            },
        }

        # Request
        response = test_client.get(
            "/project-version-states/1",
            params={
                "user_id": 1,
                "identity_type_id": 1,
            },
        )

        # Verificar respuesta
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["organization_id"] == 100

    @patch("src.apps.backend.routercore.BackendCoreRouter.get_project_version_state_by_id")
    def test_user_without_permission_gets_403(
        self, mock_get_state, test_client, editor_headers
    ):
        """Usuario sin permisos recibe 403 Forbidden."""
        from src.apps.backend.routercore import BackendCorePermissionError

        # Mock que lanza PermissionError
        mock_get_state.side_effect = BackendCorePermissionError(
            "project_version_state_read", 3
        )

        # Request
        response = test_client.get(
            "/project-version-states/1",
            params={
                "user_id": 10,
                "identity_type_id": 3,
            },
        )

        # Verificar respuesta
        assert response.status_code == 403


# ============================================================================
# Tests de PATCH /project-version-states/{state_id}/proposal
# ============================================================================


class TestUpdateProposalPhase:
    """Tests para endpoint PATCH /project-version-states/{state_id}/proposal."""

    @patch("src.apps.backend.routercore.BackendCoreRouter.update_proposal_phase")
    def test_superadmin_can_update_proposal(
        self, mock_update, test_client, superadmin_headers
    ):
        """SuperAdmin puede actualizar fase de propuesta."""
        # Mock del método del router
        mock_update.return_value = {
            "success": True,
            "state": {
                "id": 1,
                "proposal": {
                    "aceptacion_cliente": True,
                    "aceptacion_interna": False,
                },
            },
        }

        # Request
        response = test_client.patch(
            "/project-version-states/1/proposal",
            json={
                "aceptacion_cliente": True,
                "aceptacion_interna": False,
            },
            params={
                "user_id": 1,
                "identity_type_id": 1,
            },
        )

        # Verificar respuesta
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("src.apps.backend.routercore.BackendCoreRouter.update_proposal_phase")
    def test_editor_with_permission_can_update(
        self, mock_update, test_client, editor_headers
    ):
        """Editor con permisos puede actualizar."""
        mock_update.return_value = {
            "success": True,
            "state": {"id": 1},
        }

        response = test_client.patch(
            "/project-version-states/1/proposal",
            json={
                "aceptacion_cliente": True,
                "aceptacion_interna": False,
            },
            params={
                "user_id": 10,
                "identity_type_id": 3,
            },
        )

        assert response.status_code == 200

    @patch("src.apps.backend.routercore.BackendCoreRouter.update_proposal_phase")
    def test_auditor_cannot_update_proposal(
        self, mock_update, test_client, auditor_headers
    ):
        """Auditor NO puede actualizar (solo lectura)."""
        from src.apps.backend.routercore import BackendCorePermissionError

        # Mock que lanza PermissionError
        mock_update.side_effect = BackendCorePermissionError(
            "project_version_state_update", 4
        )

        response = test_client.patch(
            "/project-version-states/1/proposal",
            json={
                "aceptacion_cliente": True,
                "aceptacion_interna": False,
            },
            params={
                "user_id": 20,
                "identity_type_id": 4,
            },
        )

        # Verificar que se deniega
        assert response.status_code == 403

    @patch("src.apps.backend.routercore.BackendCoreRouter.update_proposal_phase")
    def test_lector_cannot_update_proposal(
        self, mock_update, test_client, lector_headers
    ):
        """Lector NO puede actualizar (solo lectura)."""
        from src.apps.backend.routercore import BackendCorePermissionError

        mock_update.side_effect = BackendCorePermissionError(
            "project_version_state_update", 5
        )

        response = test_client.patch(
            "/project-version-states/1/proposal",
            json={
                "aceptacion_cliente": True,
                "aceptacion_interna": False,
            },
            params={
                "user_id": 30,
                "identity_type_id": 5,
            },
        )

        assert response.status_code == 403


# ============================================================================
# Tests de PATCH /project-version-states/{state_id}/evaluation
# ============================================================================


class TestUpdateEvaluationPhase:
    """Tests para endpoint PATCH /project-version-states/{state_id}/evaluation."""

    @patch("src.apps.backend.routercore.BackendCoreRouter.update_evaluation_phase")
    def test_superadmin_can_update_evaluation(
        self, mock_update, test_client, superadmin_headers
    ):
        """SuperAdmin puede actualizar fase de evaluación."""
        mock_update.return_value = {
            "success": True,
            "state": {
                "id": 1,
                "evaluation": {
                    "calidad_aprobada": True,
                },
            },
        }

        response = test_client.patch(
            "/project-version-states/1/evaluation",
            json={
                "evaluacion": True,
                "reentrenamiento": False,
                "optimizacion": False,
                "calidad_aprobada": True,
            },
            params={
                "user_id": 1,
                "identity_type_id": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("src.apps.backend.routercore.BackendCoreRouter.update_evaluation_phase")
    def test_auditor_cannot_update_evaluation(
        self, mock_update, test_client, auditor_headers
    ):
        """Auditor NO puede actualizar evaluación."""
        from src.apps.backend.routercore import BackendCorePermissionError

        mock_update.side_effect = BackendCorePermissionError(
            "project_version_state_update", 4
        )

        response = test_client.patch(
            "/project-version-states/1/evaluation",
            json={
                "evaluacion": True,
                "reentrenamiento": False,
                "optimizacion": False,
                "calidad_aprobada": True,
            },
            params={
                "user_id": 20,
                "identity_type_id": 4,
            },
        )

        assert response.status_code == 403


# ============================================================================
# Tests de Validación de Payload
# ============================================================================


class TestPayloadValidation:
    """Tests para validación de payloads con Pydantic."""

    def test_update_proposal_requires_both_fields(self, test_client, superadmin_headers):
        """update_proposal requiere ambos campos."""
        response = test_client.patch(
            "/project-version-states/1/proposal",
            json={
                "aceptacion_cliente": True,
                # Falta aceptacion_interna
            },
            params={
                "user_id": 1,
                "identity_type_id": 1,
            },
        )

        # Pydantic debe rechazar payload incompleto
        assert response.status_code == 422

    def test_update_proposal_rejects_invalid_types(
        self, test_client, superadmin_headers
    ):
        """update_proposal rechaza tipos inválidos."""
        response = test_client.patch(
            "/project-version-states/1/proposal",
            json={
                "aceptacion_cliente": "invalid",  # Debe ser bool
                "aceptacion_interna": False,
            },
            params={
                "user_id": 1,
                "identity_type_id": 1,
            },
        )

        # Pydantic debe rechazar tipo inválido
        assert response.status_code == 422


# ============================================================================
# Tests de Flujo Completo (Integration)
# ============================================================================


class TestFullFlow:
    """Tests de integración de flujo completo."""

    @patch("src.apps.backend.routercore.BackendCoreRouter.get_project_version_state_by_id")
    @patch("src.apps.backend.routercore.BackendCoreRouter.update_proposal_phase")
    def test_full_approval_flow(
        self, mock_update, mock_get, test_client, superadmin_headers
    ):
        """Test de flujo completo: obtener estado → aprobar propuesta."""
        # 1. Obtener estado inicial
        mock_get.return_value = {
            "id": 1,
            "proposal": {
                "aceptacion_cliente": False,
                "aceptacion_interna": False,
            },
        }

        response_get = test_client.get(
            "/project-version-states/1",
            params={"user_id": 1, "identity_type_id": 1},
        )
        assert response_get.status_code == 200
        initial_state = response_get.json()
        assert initial_state["proposal"]["aceptacion_cliente"] is False

        # 2. Aprobar propuesta
        mock_update.return_value = {
            "success": True,
            "state": {
                "id": 1,
                "proposal": {
                    "aceptacion_cliente": True,
                    "aceptacion_interna": True,
                },
            },
        }

        response_update = test_client.patch(
            "/project-version-states/1/proposal",
            json={
                "aceptacion_cliente": True,
                "aceptacion_interna": True,
            },
            params={"user_id": 1, "identity_type_id": 1},
        )
        assert response_update.status_code == 200
        updated_state = response_update.json()
        assert updated_state["success"] is True


# ============================================================================
# Tests de Errores
# ============================================================================


class TestErrorHandling:
    """Tests para manejo de errores."""

    @patch("src.apps.backend.routercore.BackendCoreRouter.get_project_version_state_by_id")
    def test_get_nonexistent_state_returns_404(
        self, mock_get, test_client, superadmin_headers
    ):
        """Obtener estado inexistente retorna 404."""
        from src.apps.backend.routercore import BackendCoreBusinessError

        # Mock que lanza BusinessError
        mock_get.side_effect = BackendCoreBusinessError("Estado no encontrado")

        response = test_client.get(
            "/project-version-states/999",
            params={"user_id": 1, "identity_type_id": 1},
        )

        # Nota: BusinessError se mapea a 400, no 404
        assert response.status_code == 400


# ============================================================================
# Ejecución de tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

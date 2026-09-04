"""Tests para ProjectVersionStateService (Application Layer).

Este módulo prueba:
- Validación de permisos (read y write)
- Orquestación entre dominio y repositorio
- Manejo de excepciones
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

# Agregar paths necesarios
domain_path = Path(__file__).resolve().parents[2] / "1_shared_domain/entities"
sys.path.insert(0, str(domain_path))

from project_version_state import (
    ProposalPhase,
    TrainingPhase,
    EvaluationPhase,
    GenerationPhase,
    NotificationPhase,
    ProjectVersionState,
    StateInternal,
    ExplorerState,
)

# Importar Service
from src.shared_application.services.project_version_state_service import (
    ProjectVersionStateService,
    PermissionDeniedError,
    NotFoundError,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repository():
    """Mock del Repository."""
    return Mock()


@pytest.fixture
def mock_db_engine():
    """Mock del DB Engine para consultas de permisos."""
    return MagicMock()


@pytest.fixture
def sample_project_version_state():
    """Instancia de ejemplo de ProjectVersionState."""
    return ProjectVersionState(
        id=1,
        organization_id=100,
        project_id=200,
        version_id=1,
        state=ExplorerState.STABLE,
        state_internal=StateInternal.PROPUESTA_CLIENTE,
        proposal=ProposalPhase(aceptacion_cliente=False, aceptacion_interna=False),
        training=TrainingPhase(solicitado=False, completado=False),
        evaluation=EvaluationPhase(
            evaluacion_en_curso=False,
            reentrenamiento_en_curso=False,
            optimizacion_en_curso=False,
            calidad_aprobada=False,
        ),
        generation=GenerationPhase(solicitada=False, completada=False),
        notification=NotificationPhase(enviada=False),
    )


# ============================================================================
# Tests de Permisos - Read Permission
# ============================================================================


class TestReadPermissions:
    """Tests para validación de permisos de lectura."""

    def test_superadmin_can_read_any_state(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """SuperAdmin (identity_type_id=1) puede leer cualquier estado."""
        mock_repository.get_by_id.return_value = sample_project_version_state
        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # SuperAdmin (identity_type_id=1) intenta leer estado
        result = service.get_state_by_id(
            state_id=1,
            requesting_user_id=999,
            requesting_user_identity_type=1,  # SuperAdmin
        )

        # Debe retornar el estado sin verificar asignaciones
        assert result is not None
        assert result.id == 1

    def test_user_with_org_assignment_can_read(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """Usuario con asignación a organización puede leer estado."""
        mock_repository.get_by_id.return_value = sample_project_version_state

        # Mock de consulta SQL que retorna asignación activa
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.count = 1  # Tiene asignación
        mock_conn.execute.return_value.fetchone.return_value = mock_result
        mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # Usuario con identity_type_id=2 (Admin) intenta leer
        result = service.get_state_by_id(
            state_id=1,
            requesting_user_id=10,
            requesting_user_identity_type=2,  # Admin
        )

        # Debe permitir lectura
        assert result is not None
        assert result.id == 1

    def test_user_without_assignment_cannot_read(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """Usuario sin asignación NO puede leer estado."""
        mock_repository.get_by_id.return_value = sample_project_version_state

        # Mock de consulta SQL que retorna 0 asignaciones
        mock_conn = MagicMock()
        mock_result_org = Mock()
        mock_result_org.count = 0  # Sin asignación a organización
        mock_result_prj = Mock()
        mock_result_prj.count = 0  # Sin asignación a proyecto

        # Primera llamada retorna org, segunda retorna prj
        mock_conn.execute.return_value.fetchone.side_effect = [
            mock_result_org,
            mock_result_prj,
        ]
        mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # Usuario sin asignación intenta leer
        with pytest.raises(PermissionDeniedError):
            service.get_state_by_id(
                state_id=1,
                requesting_user_id=10,
                requesting_user_identity_type=3,  # Editor
            )


# ============================================================================
# Tests de Permisos - Write Permission
# ============================================================================


class TestWritePermissions:
    """Tests para validación de permisos de escritura."""

    def test_auditor_cannot_write(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """Auditor (identity_type_id=4) NO puede escribir."""
        mock_repository.get_by_id.return_value = sample_project_version_state
        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # Auditor intenta aprobar propuesta
        with pytest.raises(PermissionDeniedError):
            service.approve_proposal_by_client(
                state_id=1,
                requesting_user_id=10,
                requesting_user_identity_type=4,  # Auditor
            )

    def test_lector_cannot_write(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """Lector (identity_type_id=5) NO puede escribir."""
        mock_repository.get_by_id.return_value = sample_project_version_state
        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # Lector intenta aprobar propuesta
        with pytest.raises(PermissionDeniedError):
            service.approve_proposal_by_client(
                state_id=1,
                requesting_user_id=10,
                requesting_user_identity_type=5,  # Lector
            )

    def test_superadmin_can_write_without_assignment(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """SuperAdmin puede escribir sin necesidad de asignación."""
        mock_repository.get_by_id.return_value = sample_project_version_state
        mock_repository.save.return_value = sample_project_version_state

        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # SuperAdmin aprueba propuesta
        result = service.approve_proposal_by_client(
            state_id=1,
            requesting_user_id=1,
            requesting_user_identity_type=1,  # SuperAdmin
        )

        # Debe permitir escritura
        assert result is not None
        mock_repository.save.assert_called_once()

    def test_editor_with_assignment_can_write(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """Editor con asignación activa puede escribir."""
        mock_repository.get_by_id.return_value = sample_project_version_state
        mock_repository.save.return_value = sample_project_version_state

        # Mock de consulta SQL que retorna asignación activa con rol de escritura
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.count = 1  # Tiene asignación con rol de escritura
        mock_conn.execute.return_value.fetchone.return_value = mock_result
        mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # Editor (identity_type_id=3) aprueba propuesta
        result = service.approve_proposal_by_client(
            state_id=1,
            requesting_user_id=10,
            requesting_user_identity_type=3,  # Editor
        )

        # Debe permitir escritura
        assert result is not None
        mock_repository.save.assert_called_once()

    def test_editor_without_write_role_cannot_write(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """Editor sin rol de escritura NO puede escribir."""
        mock_repository.get_by_id.return_value = sample_project_version_state

        # Mock de consulta SQL que retorna 0 asignaciones con rol de escritura
        mock_conn = MagicMock()
        mock_result_org = Mock()
        mock_result_org.count = 0  # Sin asignación con rol de escritura
        mock_result_prj = Mock()
        mock_result_prj.count = 0

        mock_conn.execute.return_value.fetchone.side_effect = [
            mock_result_org,
            mock_result_prj,
        ]
        mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # Editor intenta aprobar sin rol de escritura
        with pytest.raises(PermissionDeniedError):
            service.approve_proposal_by_client(
                state_id=1,
                requesting_user_id=10,
                requesting_user_identity_type=3,  # Editor
            )


# ============================================================================
# Tests de Operaciones - Proposal Phase
# ============================================================================


class TestProposalPhaseOperations:
    """Tests para operaciones de la fase de propuesta."""

    def test_approve_proposal_by_client_updates_and_saves(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """Aprobar propuesta por cliente actualiza y persiste."""
        mock_repository.get_by_id.return_value = sample_project_version_state
        mock_repository.save.return_value = sample_project_version_state

        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # SuperAdmin aprueba por cliente
        result = service.approve_proposal_by_client(
            state_id=1,
            requesting_user_id=1,
            requesting_user_identity_type=1,  # SuperAdmin
        )

        # Verificar que se llamó a save
        mock_repository.save.assert_called_once()

        # Verificar que el estado pasado a save tiene aceptacion_cliente=True
        saved_state = mock_repository.save.call_args[0][0]
        assert saved_state.proposal.aceptacion_cliente is True

    def test_approve_proposal_by_internal_updates_and_saves(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """Aprobar propuesta por interno actualiza y persiste."""
        mock_repository.get_by_id.return_value = sample_project_version_state
        mock_repository.save.return_value = sample_project_version_state

        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # SuperAdmin aprueba por interno
        result = service.approve_proposal_by_internal(
            state_id=1,
            requesting_user_id=1,
            requesting_user_identity_type=1,
        )

        # Verificar que se llamó a save
        mock_repository.save.assert_called_once()

        # Verificar aceptacion_interna=True
        saved_state = mock_repository.save.call_args[0][0]
        assert saved_state.proposal.aceptacion_interna is True

    def test_revoke_client_approval_updates_and_saves(
        self, mock_repository, mock_db_engine
    ):
        """Revocar aprobación de cliente actualiza y persiste."""
        # Estado con ambas aprobaciones activas
        state = ProjectVersionState(
            id=1,
            organization_id=100,
            project_id=200,
            version_id=1,
            state=ExplorerState.STABLE,
            state_internal=StateInternal.ACEPTACION_INTERNA,
            proposal=ProposalPhase(aceptacion_cliente=True, aceptacion_interna=True),
            training=TrainingPhase(solicitado=False, completado=False),
            evaluation=EvaluationPhase(
                evaluacion_en_curso=False,
                reentrenamiento_en_curso=False,
                optimizacion_en_curso=False,
                calidad_aprobada=False,
            ),
            generation=GenerationPhase(solicitada=False, completada=False),
            notification=NotificationPhase(enviada=False),
        )

        mock_repository.get_by_id.return_value = state
        mock_repository.save.return_value = state

        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # SuperAdmin revoca aprobación del cliente
        result = service.revoke_client_approval(
            state_id=1,
            requesting_user_id=1,
            requesting_user_identity_type=1,
        )

        # Verificar que se llamó a save
        mock_repository.save.assert_called_once()

        # Verificar aceptacion_cliente=False
        saved_state = mock_repository.save.call_args[0][0]
        assert saved_state.proposal.aceptacion_cliente is False


# ============================================================================
# Tests de Operaciones - Training Phase
# ============================================================================


class TestTrainingPhaseOperations:
    """Tests para operaciones de la fase de entrenamiento."""

    def test_complete_training_updates_and_saves(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """Completar entrenamiento actualiza y persiste."""
        sample_project_version_state.training = TrainingPhase(
            solicitado=True, completado=False
        )
        mock_repository.get_by_id.return_value = sample_project_version_state
        mock_repository.save.return_value = sample_project_version_state

        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # SuperAdmin completa entrenamiento
        result = service.complete_training(
            state_id=1,
            requesting_user_id=1,
            requesting_user_identity_type=1,
        )

        # Verificar que se llamó a save
        mock_repository.save.assert_called_once()

        # Verificar entrenamiento_completado=True
        saved_state = mock_repository.save.call_args[0][0]
        assert saved_state.training.completado is True


# ============================================================================
# Tests de Operaciones - Evaluation Phase
# ============================================================================


class TestEvaluationPhaseOperations:
    """Tests para operaciones de la fase de evaluación."""

    def test_approve_quality_updates_and_saves(
        self, mock_repository, mock_db_engine, sample_project_version_state
    ):
        """Aprobar control de calidad actualiza y persiste."""
        sample_project_version_state.training = TrainingPhase(
            solicitado=True, completado=True
        )
        mock_repository.get_by_id.return_value = sample_project_version_state
        mock_repository.save.return_value = sample_project_version_state

        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        # SuperAdmin aprueba calidad
        result = service.approve_quality(
            state_id=1,
            requesting_user_id=1,
            requesting_user_identity_type=1,
        )

        # Verificar que se llamó a save
        mock_repository.save.assert_called_once()

        # Verificar calidad_aprobada=True
        saved_state = mock_repository.save.call_args[0][0]
        assert saved_state.evaluation.calidad_aprobada is True


# ============================================================================
# Tests de Errores
# ============================================================================


class TestErrorHandling:
    """Tests para manejo de errores."""

    def test_get_state_by_id_returns_none_if_not_found(
        self, mock_repository, mock_db_engine
    ):
        """get_state_by_id retorna None si no existe."""
        mock_repository.get_by_id.return_value = None
        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        result = service.get_state_by_id(
            state_id=999,
            requesting_user_id=1,
            requesting_user_identity_type=1,
        )

        assert result is None

    def test_approve_proposal_raises_not_found_if_state_missing(
        self, mock_repository, mock_db_engine
    ):
        """aprobar propuesta lanza NotFoundError si estado no existe."""
        mock_repository.get_by_id.return_value = None
        service = ProjectVersionStateService(mock_repository, mock_db_engine)

        with pytest.raises(NotFoundError):
            service.approve_proposal_by_client(
                state_id=999,
                requesting_user_id=1,
                requesting_user_identity_type=1,
            )


# ============================================================================
# Ejecución de tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

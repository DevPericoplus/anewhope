"""Tests para entidades de dominio de ProjectVersionState."""

import pytest
from datetime import datetime
import sys
from pathlib import Path

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


def _sample_state() -> ProjectVersionState:
    """Construye un estado de versión con valores por defecto actuales."""
    return ProjectVersionState(
        id=1,
        organization_id=1,
        project_id=1,
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


class TestProposalPhase:
    """Tests para ProposalPhase Value Object."""

    def test_proposal_phase_is_frozen(self) -> None:
        """Verifica que ProposalPhase es inmutable."""
        phase = ProposalPhase(aceptacion_cliente=False, aceptacion_interna=False)

        with pytest.raises(AttributeError):
            phase.aceptacion_cliente = True

    def test_approve_by_client_returns_new_object(self) -> None:
        """Verifica que approve_by_client retorna nuevo objeto sin mutar original."""
        phase = ProposalPhase(aceptacion_cliente=False, aceptacion_interna=False)

        approved = phase.approve_by_client()

        assert approved.aceptacion_cliente is True
        assert approved.aceptacion_interna is False
        assert phase.aceptacion_cliente is False
        assert phase.aceptacion_interna is False

    def test_approve_by_internal_returns_new_object(self) -> None:
        """Verifica que approve_by_internal retorna nuevo objeto."""
        phase = ProposalPhase(aceptacion_cliente=False, aceptacion_interna=False)

        approved = phase.approve_by_internal()

        assert approved.aceptacion_cliente is False
        assert approved.aceptacion_interna is True
        assert phase.aceptacion_interna is False

    def test_revoke_client_approval(self) -> None:
        """Verifica que se puede revocar aprobación del cliente."""
        phase = ProposalPhase(aceptacion_cliente=True, aceptacion_interna=True)

        revoked = phase.revoke_client_approval()

        assert revoked.aceptacion_cliente is False
        assert revoked.aceptacion_interna is True

    def test_revoke_internal_approval(self) -> None:
        """Verifica que se puede revocar aprobación interna."""
        phase = ProposalPhase(aceptacion_cliente=True, aceptacion_interna=True)

        revoked = phase.revoke_internal_approval()

        assert revoked.aceptacion_cliente is True
        assert revoked.aceptacion_interna is False

    def test_is_approved(self) -> None:
        """Verifica que is_approved detecta doble aceptación."""
        phase_not_approved = ProposalPhase(
            aceptacion_cliente=True, aceptacion_interna=False
        )
        phase_fully_approved = ProposalPhase(
            aceptacion_cliente=True, aceptacion_interna=True
        )

        assert phase_not_approved.is_approved is False
        assert phase_fully_approved.is_approved is True


class TestTrainingPhase:
    """Tests para TrainingPhase Value Object."""

    def test_training_phase_is_frozen(self) -> None:
        """Verifica que TrainingPhase es inmutable."""
        phase = TrainingPhase(solicitado=False, completado=False)

        with pytest.raises(AttributeError):
            phase.solicitado = True

    def test_mark_completed_returns_new_object(self) -> None:
        """Verifica que mark_completed retorna nuevo objeto."""
        phase = TrainingPhase(solicitado=True, completado=False)

        completed = phase.mark_completed()

        assert completed.solicitado is True
        assert completed.completado is True
        assert phase.completado is False


class TestEvaluationPhase:
    """Tests para EvaluationPhase Value Object."""

    def test_evaluation_phase_is_frozen(self) -> None:
        """Verifica que EvaluationPhase es inmutable."""
        phase = EvaluationPhase(
            evaluacion_en_curso=False,
            reentrenamiento_en_curso=False,
            optimizacion_en_curso=False,
            calidad_aprobada=False,
        )

        with pytest.raises(AttributeError):
            phase.evaluacion_en_curso = True

    def test_approve_quality_returns_new_object(self) -> None:
        """Verifica que approve_quality retorna nuevo objeto."""
        phase = EvaluationPhase(
            evaluacion_en_curso=True,
            reentrenamiento_en_curso=False,
            optimizacion_en_curso=False,
            calidad_aprobada=False,
        )

        approved = phase.approve_quality()

        assert approved.calidad_aprobada is True
        assert phase.calidad_aprobada is False


class TestGenerationPhase:
    """Tests para GenerationPhase Value Object."""

    def test_generation_phase_is_frozen(self) -> None:
        """Verifica que GenerationPhase es inmutable."""
        phase = GenerationPhase(solicitada=False, completada=False)

        with pytest.raises(AttributeError):
            phase.solicitada = True

    def test_mark_completed_returns_new_object(self) -> None:
        """Verifica que mark_completed retorna nuevo objeto."""
        phase = GenerationPhase(solicitada=True, completada=False)

        completed = phase.mark_completed("/tmp/model.gguf")

        assert completed.completada is True
        assert completed.ruta_fichero == "/tmp/model.gguf"
        assert phase.completada is False


class TestNotificationPhase:
    """Tests para NotificationPhase Value Object."""

    def test_notification_phase_is_frozen(self) -> None:
        """Verifica que NotificationPhase es inmutable."""
        phase = NotificationPhase(enviada=False)

        with pytest.raises(AttributeError):
            phase.enviada = True

    def test_mark_sent_returns_new_object(self) -> None:
        """Verifica que mark_sent retorna nuevo objeto."""
        phase = NotificationPhase(enviada=False)

        sent = phase.mark_sent()

        assert sent.enviada is True
        assert phase.enviada is False


class TestProjectVersionState:
    """Tests para ProjectVersionState Aggregate Root."""

    def test_can_create_project_version_state(self) -> None:
        """Verifica que se puede crear instancia de ProjectVersionState."""
        state = _sample_state()

        assert state.id == 1
        assert state.organization_id == 1
        assert state.state == ExplorerState.STABLE

    def test_approve_proposal_by_client_updates_proposal_phase(self) -> None:
        """Verifica que aprobar por cliente actualiza la fase de propuesta."""
        state = _sample_state()

        state.approve_proposal_by_client(user_id=1)

        assert state.proposal.aceptacion_cliente is True
        assert state.proposal.aceptacion_interna is False

    def test_state_tracks_updated_by(self) -> None:
        """Verifica que updated_by se actualiza al hacer cambios."""
        state = _sample_state()

        state.approve_proposal_by_client(user_id=10)

        assert state.updated_by == 10
        assert isinstance(state.updated_at, datetime)

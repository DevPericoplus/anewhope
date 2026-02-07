"""Tests para entidades de dominio de ProjectVersionState.

Este módulo prueba:
- Inmutabilidad de Value Objects
- Métodos de transición de estado
- Validaciones de negocio en el dominio
"""

import pytest
from datetime import datetime, timezone
import sys
from pathlib import Path

# Agregar path de entidades de dominio
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


# ============================================================================
# Tests de Value Objects - ProposalPhase
# ============================================================================


class TestProposalPhase:
    """Tests para ProposalPhase Value Object."""

    def test_proposal_phase_is_frozen(self):
        """Verifica que ProposalPhase es inmutable."""
        phase = ProposalPhase(aceptacion_cliente=False, aceptacion_interna=False)

        with pytest.raises(AttributeError):
            phase.aceptacion_cliente = True

    def test_approve_by_client_returns_new_object(self):
        """Verifica que approve_by_client retorna nuevo objeto sin mutar original."""
        phase = ProposalPhase(aceptacion_cliente=False, aceptacion_interna=False)

        # Aprobar por cliente
        approved = phase.approve_by_client(user_id=1)

        # Verificar que retorna nuevo objeto
        assert approved.aceptacion_cliente is True
        assert approved.aceptacion_interna is False

        # Verificar que original NO se modificó (inmutabilidad)
        assert phase.aceptacion_cliente is False
        assert phase.aceptacion_interna is False

    def test_approve_by_internal_returns_new_object(self):
        """Verifica que approve_by_internal retorna nuevo objeto."""
        phase = ProposalPhase(aceptacion_cliente=False, aceptacion_interna=False)

        approved = phase.approve_by_internal(user_id=1)

        assert approved.aceptacion_cliente is False
        assert approved.aceptacion_interna is True
        assert phase.aceptacion_interna is False  # Original inmutable

    def test_revoke_client_approval(self):
        """Verifica que se puede revocar aprobación del cliente."""
        phase = ProposalPhase(aceptacion_cliente=True, aceptacion_interna=True)

        revoked = phase.revoke_client_approval(user_id=1)

        assert revoked.aceptacion_cliente is False
        assert revoked.aceptacion_interna is True

    def test_revoke_internal_approval(self):
        """Verifica que se puede revocar aprobación interna."""
        phase = ProposalPhase(aceptacion_cliente=True, aceptacion_interna=True)

        revoked = phase.revoke_internal_approval(user_id=1)

        assert revoked.aceptacion_cliente is True
        assert revoked.aceptacion_interna is False

    def test_is_fully_approved(self):
        """Verifica que is_fully_approved detecta cuando ambas aprobaciones están activas."""
        phase_not_approved = ProposalPhase(
            aceptacion_cliente=True, aceptacion_interna=False
        )
        phase_fully_approved = ProposalPhase(
            aceptacion_cliente=True, aceptacion_interna=True
        )

        assert phase_not_approved.is_fully_approved() is False
        assert phase_fully_approved.is_fully_approved() is True


# ============================================================================
# Tests de Value Objects - TrainingPhase
# ============================================================================


class TestTrainingPhase:
    """Tests para TrainingPhase Value Object."""

    def test_training_phase_is_frozen(self):
        """Verifica que TrainingPhase es inmutable."""
        phase = TrainingPhase(
            entrenamiento_solicitado=False, entrenamiento_completado=False
        )

        with pytest.raises(AttributeError):
            phase.entrenamiento_solicitado = True

    def test_request_training_returns_new_object(self):
        """Verifica que request_training retorna nuevo objeto."""
        phase = TrainingPhase(
            entrenamiento_solicitado=False, entrenamiento_completado=False
        )

        requested = phase.request_training(user_id=1)

        assert requested.entrenamiento_solicitado is True
        assert requested.entrenamiento_completado is False
        assert phase.entrenamiento_solicitado is False  # Original inmutable

    def test_complete_training_returns_new_object(self):
        """Verifica que complete_training retorna nuevo objeto."""
        phase = TrainingPhase(entrenamiento_solicitado=True, entrenamiento_completado=False)

        completed = phase.complete_training(user_id=1)

        assert completed.entrenamiento_solicitado is True
        assert completed.entrenamiento_completado is True
        assert phase.entrenamiento_completado is False  # Original inmutable

    def test_reset_training(self):
        """Verifica que reset_training resetea ambos campos."""
        phase = TrainingPhase(entrenamiento_solicitado=True, entrenamiento_completado=True)

        reset = phase.reset_training(user_id=1)

        assert reset.entrenamiento_solicitado is False
        assert reset.entrenamiento_completado is False


# ============================================================================
# Tests de Value Objects - EvaluationPhase
# ============================================================================


class TestEvaluationPhase:
    """Tests para EvaluationPhase Value Object."""

    def test_evaluation_phase_is_frozen(self):
        """Verifica que EvaluationPhase es inmutable."""
        phase = EvaluationPhase(
            evaluacion=False,
            reentrenamiento=False,
            optimizacion=False,
            calidad_aprobada=False,
        )

        with pytest.raises(AttributeError):
            phase.evaluacion = True

    def test_start_evaluation_returns_new_object(self):
        """Verifica que start_evaluation retorna nuevo objeto."""
        phase = EvaluationPhase(
            evaluacion=False,
            reentrenamiento=False,
            optimizacion=False,
            calidad_aprobada=False,
        )

        started = phase.start_evaluation(user_id=1)

        assert started.evaluacion is True
        assert phase.evaluacion is False  # Original inmutable

    def test_approve_quality_returns_new_object(self):
        """Verifica que approve_quality retorna nuevo objeto."""
        phase = EvaluationPhase(
            evaluacion=True,
            reentrenamiento=False,
            optimizacion=False,
            calidad_aprobada=False,
        )

        approved = phase.approve_quality(user_id=1)

        assert approved.calidad_aprobada is True
        assert phase.calidad_aprobada is False  # Original inmutable

    def test_reject_quality_triggers_retraining(self):
        """Verifica que reject_quality activa reentrenamiento."""
        phase = EvaluationPhase(
            evaluacion=True,
            reentrenamiento=False,
            optimizacion=False,
            calidad_aprobada=False,
        )

        rejected = phase.reject_quality(user_id=1)

        assert rejected.calidad_aprobada is False
        assert rejected.reentrenamiento is True


# ============================================================================
# Tests de Value Objects - GenerationPhase
# ============================================================================


class TestGenerationPhase:
    """Tests para GenerationPhase Value Object."""

    def test_generation_phase_is_frozen(self):
        """Verifica que GenerationPhase es inmutable."""
        phase = GenerationPhase(
            generacion_solicitada=False, generacion_completada=False
        )

        with pytest.raises(AttributeError):
            phase.generacion_solicitada = True

    def test_request_generation_returns_new_object(self):
        """Verifica que request_generation retorna nuevo objeto."""
        phase = GenerationPhase(
            generacion_solicitada=False, generacion_completada=False
        )

        requested = phase.request_generation(user_id=1)

        assert requested.generacion_solicitada is True
        assert phase.generacion_solicitada is False  # Original inmutable

    def test_complete_generation_returns_new_object(self):
        """Verifica que complete_generation retorna nuevo objeto."""
        phase = GenerationPhase(generacion_solicitada=True, generacion_completada=False)

        completed = phase.complete_generation(user_id=1)

        assert completed.generacion_completada is True
        assert phase.generacion_completada is False  # Original inmutable


# ============================================================================
# Tests de Value Objects - NotificationPhase
# ============================================================================


class TestNotificationPhase:
    """Tests para NotificationPhase Value Object."""

    def test_notification_phase_is_frozen(self):
        """Verifica que NotificationPhase es inmutable."""
        phase = NotificationPhase(notificacion_enviada=False)

        with pytest.raises(AttributeError):
            phase.notificacion_enviada = True

    def test_send_notification_returns_new_object(self):
        """Verifica que send_notification retorna nuevo objeto."""
        phase = NotificationPhase(notificacion_enviada=False)

        sent = phase.send_notification(user_id=1)

        assert sent.notificacion_enviada is True
        assert phase.notificacion_enviada is False  # Original inmutable


# ============================================================================
# Tests de Aggregate Root - ProjectVersionState
# ============================================================================


class TestProjectVersionState:
    """Tests para ProjectVersionState Aggregate Root."""

    def test_can_create_project_version_state(self):
        """Verifica que se puede crear instancia de ProjectVersionState."""
        state = ProjectVersionState(
            id=1,
            organization_id=1,
            project_id=1,
            version_id=1,
            state=ExplorerState.PROPUESTA,
            state_internal=StateInternal.PROPUESTA_CLIENTE,
            proposal=ProposalPhase(aceptacion_cliente=False, aceptacion_interna=False),
            training=TrainingPhase(
                entrenamiento_solicitado=False, entrenamiento_completado=False
            ),
            evaluation=EvaluationPhase(
                evaluacion=False,
                reentrenamiento=False,
                optimizacion=False,
                calidad_aprobada=False,
            ),
            generation=GenerationPhase(
                generacion_solicitada=False, generacion_completada=False
            ),
            notification=NotificationPhase(notificacion_enviada=False),
        )

        assert state.id == 1
        assert state.organization_id == 1
        assert state.state == ExplorerState.PROPUESTA

    def test_approve_proposal_by_client_updates_proposal_phase(self):
        """Verifica que aprobar por cliente actualiza la fase de propuesta."""
        state = ProjectVersionState(
            id=1,
            organization_id=1,
            project_id=1,
            version_id=1,
            state=ExplorerState.PROPUESTA,
            state_internal=StateInternal.PROPUESTA_CLIENTE,
            proposal=ProposalPhase(aceptacion_cliente=False, aceptacion_interna=False),
            training=TrainingPhase(
                entrenamiento_solicitado=False, entrenamiento_completado=False
            ),
            evaluation=EvaluationPhase(
                evaluacion=False,
                reentrenamiento=False,
                optimizacion=False,
                calidad_aprobada=False,
            ),
            generation=GenerationPhase(
                generacion_solicitada=False, generacion_completada=False
            ),
            notification=NotificationPhase(notificacion_enviada=False),
        )

        # Aprobar por cliente
        state.approve_proposal_by_client(user_id=1)

        # Verificar que proposal se actualizó
        assert state.proposal.aceptacion_cliente is True
        assert state.proposal.aceptacion_interna is False

    def test_state_tracks_updated_by(self):
        """Verifica que updated_by se actualiza al hacer cambios."""
        state = ProjectVersionState(
            id=1,
            organization_id=1,
            project_id=1,
            version_id=1,
            state=ExplorerState.PROPUESTA,
            state_internal=StateInternal.PROPUESTA_CLIENTE,
            proposal=ProposalPhase(aceptacion_cliente=False, aceptacion_interna=False),
            training=TrainingPhase(
                entrenamiento_solicitado=False, entrenamiento_completado=False
            ),
            evaluation=EvaluationPhase(
                evaluacion=False,
                reentrenamiento=False,
                optimizacion=False,
                calidad_aprobada=False,
            ),
            generation=GenerationPhase(
                generacion_solicitada=False, generacion_completada=False
            ),
            notification=NotificationPhase(notificacion_enviada=False),
            updated_by=None,
        )

        # Aprobar y verificar que updated_by se setea
        state.approve_proposal_by_client(user_id=10)

        assert state.updated_by == 10


# ============================================================================
# Ejecución de tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

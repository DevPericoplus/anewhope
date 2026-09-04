"""Tests para MariaDBProjectVersionStateRepository (Infrastructure Layer).

Este módulo prueba:
- Conversión de row SQL a entidad de dominio
- Conversión de entidad de dominio a SQL
- Operaciones CRUD del repositorio
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from src.shared_application.adapters.mariadb_project_version_state_repository import (
    EvaluationPhase,
    ExplorerState,
    GenerationPhase,
    MariaDBProjectVersionStateRepository,
    NotificationPhase,
    ProjectVersionState,
    ProposalPhase,
    StateInternal,
    TrainingPhase,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_engine():
    """Mock del SQLAlchemy Engine."""
    return MagicMock()


@pytest.fixture
def mock_sql_row():
    """Mock de un row SQL de estado_version."""
    row = Mock()
    row.id = 1
    row.id_organizacion = 100
    row.id_proyecto = 200
    row.id_version = 1
    row.state = "stable"
    row.state_internal = "propuesta_cliente"

    # Fase de propuesta
    row.final_c = 0
    row.final_i = 0

    # Fase de entrenamiento
    row.entrenamiento_inicial_solicitado = 0
    row.entrenamiento_inicial_completado = 0

    # Fase de evaluación
    row.evaluacion_entrenamiento = 0
    row.reentrenamiento = 0
    row.optimizacion = 0
    row.control_calidad_aprobado = 0

    # Fase de generación
    row.generacion_llm_solicitada = 0
    row.generacion_llm_completada = 0

    # Fase de notificación
    row.notificacion_descarga_enviada = 0

    # Auditoría
    row.updated_by = None
    row.updated_at = None
    row.protected = 0
    row.size = 0
    row.created_at = None

    return row


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
        updated_by=None,
        updated_at=None,
    )


# ============================================================================
# Tests de Conversión SQL Row → Entity
# ============================================================================


class TestRowToEntity:
    """Tests para conversión de row SQL a entidad de dominio."""

    def test_row_to_entity_converts_all_fields(self, mock_engine, mock_sql_row):
        """Verifica que _row_to_entity convierte todos los campos correctamente."""
        repository = MariaDBProjectVersionStateRepository(mock_engine)

        entity = repository._row_to_entity(mock_sql_row)

        # Verificar campos básicos
        assert entity.id == 1
        assert entity.organization_id == 100
        assert entity.project_id == 200
        assert entity.version_id == 1
        assert entity.state == ExplorerState.STABLE
        assert entity.state_internal == StateInternal.PROPUESTA_CLIENTE

        # Verificar Value Objects
        assert isinstance(entity.proposal, ProposalPhase)
        assert isinstance(entity.training, TrainingPhase)
        assert isinstance(entity.evaluation, EvaluationPhase)
        assert isinstance(entity.generation, GenerationPhase)
        assert isinstance(entity.notification, NotificationPhase)

    def test_row_to_entity_converts_proposal_phase(self, mock_engine, mock_sql_row):
        """Verifica conversión de ProposalPhase."""
        mock_sql_row.final_c = 1
        mock_sql_row.final_i = 0

        repository = MariaDBProjectVersionStateRepository(mock_engine)
        entity = repository._row_to_entity(mock_sql_row)

        assert entity.proposal.aceptacion_cliente is True
        assert entity.proposal.aceptacion_interna is False

    def test_row_to_entity_converts_training_phase(self, mock_engine, mock_sql_row):
        """Verifica conversión de TrainingPhase."""
        mock_sql_row.entrenamiento_inicial_solicitado = 1
        mock_sql_row.entrenamiento_inicial_completado = 1

        repository = MariaDBProjectVersionStateRepository(mock_engine)
        entity = repository._row_to_entity(mock_sql_row)

        assert entity.training.solicitado is True
        assert entity.training.completado is True

    def test_row_to_entity_converts_evaluation_phase(self, mock_engine, mock_sql_row):
        """Verifica conversión de EvaluationPhase."""
        mock_sql_row.evaluacion_entrenamiento = 1
        mock_sql_row.reentrenamiento = 0
        mock_sql_row.optimizacion = 1
        mock_sql_row.control_calidad_aprobado = 1

        repository = MariaDBProjectVersionStateRepository(mock_engine)
        entity = repository._row_to_entity(mock_sql_row)

        assert entity.evaluation.evaluacion_en_curso is True
        assert entity.evaluation.reentrenamiento_en_curso is False
        assert entity.evaluation.optimizacion_en_curso is True
        assert entity.evaluation.calidad_aprobada is True

    def test_row_to_entity_converts_generation_phase(self, mock_engine, mock_sql_row):
        """Verifica conversión de GenerationPhase."""
        mock_sql_row.generacion_llm_solicitada = 1
        mock_sql_row.generacion_llm_completada = 0

        repository = MariaDBProjectVersionStateRepository(mock_engine)
        entity = repository._row_to_entity(mock_sql_row)

        assert entity.generation.solicitada is True
        assert entity.generation.completada is False

    def test_row_to_entity_converts_notification_phase(
        self, mock_engine, mock_sql_row
    ):
        """Verifica conversión de NotificationPhase."""
        mock_sql_row.notificacion_descarga_enviada = 1

        repository = MariaDBProjectVersionStateRepository(mock_engine)
        entity = repository._row_to_entity(mock_sql_row)

        assert entity.notification.enviada is True

    def test_row_to_entity_converts_audit_fields(self, mock_engine, mock_sql_row):
        """Verifica conversión de campos de auditoría."""
        mock_sql_row.updated_by = 10
        mock_sql_row.updated_at = datetime(2024, 1, 15, 10, 30, 0)

        repository = MariaDBProjectVersionStateRepository(mock_engine)
        entity = repository._row_to_entity(mock_sql_row)

        assert entity.updated_by == 10
        assert entity.updated_at == datetime(2024, 1, 15, 10, 30, 0)


# ============================================================================
# Tests de Operación get_by_id
# ============================================================================


class TestGetById:
    """Tests para operación get_by_id."""

    def test_get_by_id_returns_entity_when_found(self, mock_engine, mock_sql_row):
        """get_by_id retorna entidad cuando existe."""
        # Mock de conexión y resultado
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_sql_row
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        repository = MariaDBProjectVersionStateRepository(mock_engine)

        entity = repository.get_by_id(1)

        # Verificar que se ejecutó query
        mock_conn.execute.assert_called_once()

        # Verificar que retorna entidad
        assert entity is not None
        assert entity.id == 1

    def test_get_by_id_returns_none_when_not_found(self, mock_engine):
        """get_by_id retorna None cuando no existe."""
        # Mock de conexión que retorna None
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        repository = MariaDBProjectVersionStateRepository(mock_engine)

        entity = repository.get_by_id(999)

        assert entity is None


# ============================================================================
# Tests de Operación save
# ============================================================================


class TestSave:
    """Tests para operación save (UPDATE)."""

    def test_save_executes_update_query(
        self, mock_engine, sample_project_version_state
    ):
        """save ejecuta UPDATE query con todos los campos."""
        # Mock de conexión
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        repository = MariaDBProjectVersionStateRepository(mock_engine)

        # Ejecutar save
        repository.save(sample_project_version_state)

        # Verificar que se ejecutó SELECT de existencia + UPDATE
        assert mock_conn.execute.call_count >= 1
        mock_conn.commit.assert_called_once()

    def test_save_updates_proposal_phase_fields(
        self, mock_engine, sample_project_version_state
    ):
        """save actualiza campos de ProposalPhase."""
        # Modificar propuesta
        sample_project_version_state.proposal = ProposalPhase(
            aceptacion_cliente=True, aceptacion_interna=True
        )

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        repository = MariaDBProjectVersionStateRepository(mock_engine)
        repository.save(sample_project_version_state)

        # Verificar que se llamó a execute con parámetros correctos
        call_args = mock_conn.execute.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]

        assert params["final_c"] == 1
        assert params["final_i"] == 1

    def test_save_updates_training_phase_fields(
        self, mock_engine, sample_project_version_state
    ):
        """save actualiza campos de TrainingPhase."""
        # Modificar entrenamiento
        sample_project_version_state.training = TrainingPhase(
            solicitado=True, completado=True
        )

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        repository = MariaDBProjectVersionStateRepository(mock_engine)
        repository.save(sample_project_version_state)

        call_args = mock_conn.execute.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]

        assert params["entrenamiento_inicial_solicitado"] == 1
        assert params["entrenamiento_inicial_completado"] == 1

    def test_save_updates_evaluation_phase_fields(
        self, mock_engine, sample_project_version_state
    ):
        """save actualiza campos de EvaluationPhase."""
        # Modificar evaluación
        sample_project_version_state.evaluation = EvaluationPhase(
            evaluacion_en_curso=True,
            reentrenamiento_en_curso=False,
            optimizacion_en_curso=True,
            calidad_aprobada=True,
        )

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        repository = MariaDBProjectVersionStateRepository(mock_engine)
        repository.save(sample_project_version_state)

        call_args = mock_conn.execute.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]

        assert params["evaluacion_entrenamiento"] == 1
        assert params["reentrenamiento"] == 0
        assert params["optimizacion"] == 1
        assert params["control_calidad_aprobado"] == 1

    def test_save_updates_audit_fields(self, mock_engine, sample_project_version_state):
        """save actualiza campos de auditoría."""
        # Modificar auditoría
        sample_project_version_state.updated_by = 10

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        repository = MariaDBProjectVersionStateRepository(mock_engine)
        repository.save(sample_project_version_state)

        call_args = mock_conn.execute.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]

        assert params["updated_by"] == 10


# ============================================================================
# Tests de Operación get_by_version
# ============================================================================


class TestGetByVersion:
    """Tests para operación get_by_version."""

    def test_get_by_version_returns_entity_when_found(
        self, mock_engine, mock_sql_row
    ):
        """get_by_version retorna entidad cuando existe."""
        # Mock de conexión y resultado
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_sql_row
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        repository = MariaDBProjectVersionStateRepository(mock_engine)

        entity = repository.get_by_version(
            organization_id=100, project_id=200, version_id=1
        )

        # Verificar que retorna entidad
        assert entity is not None
        assert entity.organization_id == 100
        assert entity.project_id == 200
        assert entity.version_id == 1

    def test_get_by_version_returns_none_when_not_found(self, mock_engine):
        """get_by_version retorna None cuando no existe."""
        # Mock de conexión que retorna None
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        repository = MariaDBProjectVersionStateRepository(mock_engine)

        entity = repository.get_by_version(
            organization_id=999, project_id=999, version_id=999
        )

        assert entity is None


# ============================================================================
# Tests de Round-trip (Entity → SQL → Entity)
# ============================================================================


class TestRoundTrip:
    """Tests para verificar round-trip entity → SQL → entity."""

    def test_entity_to_sql_to_entity_preserves_data(
        self, mock_engine, sample_project_version_state, mock_sql_row
    ):
        """Verificar que convertir entity → SQL → entity preserva datos."""
        # 1. Convertir entity → SQL (save)
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        repository = MariaDBProjectVersionStateRepository(mock_engine)
        repository.save(sample_project_version_state)

        # Obtener parámetros del UPDATE
        call_args = mock_conn.execute.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]

        # 2. Simular que esos valores se guardaron en DB y se leen (mock_sql_row)
        mock_sql_row.final_c = params["final_c"]
        mock_sql_row.final_i = params["final_i"]
        mock_sql_row.entrenamiento_inicial_solicitado = params[
            "entrenamiento_inicial_solicitado"
        ]
        mock_sql_row.entrenamiento_inicial_completado = params[
            "entrenamiento_inicial_completado"
        ]
        mock_sql_row.control_calidad_aprobado = params["control_calidad_aprobado"]
        mock_sql_row.generacion_llm_solicitada = params["generacion_llm_solicitada"]
        mock_sql_row.generacion_llm_completada = params["generacion_llm_completada"]
        mock_sql_row.notificacion_descarga_enviada = params[
            "notificacion_descarga_enviada"
        ]

        # 3. Convertir SQL → entity (_row_to_entity)
        reconstructed_entity = repository._row_to_entity(mock_sql_row)

        # 4. Verificar que los datos son consistentes
        assert (
            reconstructed_entity.proposal.aceptacion_cliente
            == sample_project_version_state.proposal.aceptacion_cliente
        )
        assert (
            reconstructed_entity.training.solicitado
            == sample_project_version_state.training.solicitado
        )
        assert (
            reconstructed_entity.evaluation.calidad_aprobada
            == sample_project_version_state.evaluation.calidad_aprobada
        )


# ============================================================================
# Ejecución de tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

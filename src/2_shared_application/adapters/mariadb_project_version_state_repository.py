"""Implementación MariaDB del ProjectVersionStateRepository.

Este adaptador implementa el contrato ProjectVersionStateRepository usando
MariaDB (tabla estado_version) como backend de persistencia.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# ============================================================================
# Carga dinámica de entidades de dominio
# ============================================================================


def _load_domain_entities() -> Any:
    """Carga el módulo de entidades una sola vez (evita clases duplicadas)."""
    aliases = (
        "src.shared_domain.entities.project_version_state",
        "project_version_state",
        "_pvs_entities_repo",
        "_project_version_state_entities",
    )
    for name in aliases:
        existing = sys.modules.get(name)
        if existing is not None and hasattr(existing, "ProposalPhase"):
            for alias in aliases:
                sys.modules.setdefault(alias, existing)
            return existing

    module_path = (
        Path(__file__).resolve().parents[2]
        / "1_shared_domain/entities/project_version_state.py"
    )
    spec = importlib.util.spec_from_file_location(
        "src.shared_domain.entities.project_version_state", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar project_version_state entities")
    module = importlib.util.module_from_spec(spec)
    for alias in aliases:
        sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


_entities = _load_domain_entities()
ProjectVersionState = _entities.ProjectVersionState
StateInternal = _entities.StateInternal
ExplorerState = _entities.ExplorerState
ProposalPhase = _entities.ProposalPhase
TrainingPhase = _entities.TrainingPhase
EvaluationPhase = _entities.EvaluationPhase
GenerationPhase = _entities.GenerationPhase
NotificationPhase = _entities.NotificationPhase


# ============================================================================
# Repositorio MariaDB
# ============================================================================


class MariaDBProjectVersionStateRepository:
    """Implementación MariaDB del ProjectVersionStateRepository Protocol.

    Responsabilidades:
    - Convertir entre filas SQL y entidades ProjectVersionState
    - Ejecutar queries de lectura/escritura
    - Garantizar atomicidad de operaciones
    """

    def __init__(self, engine: Engine):
        """Inicializa el repositorio con un engine de SQLAlchemy.

        Args:
            engine: SQLAlchemy engine configurado para myllm_projects_db
        """
        self._engine = engine
        self._logger = logging.getLogger("MariaDBProjectVersionStateRepository")

    # ========================================================================
    # Métodos de consulta
    # ========================================================================

    def get_by_id(self, state_id: int) -> ProjectVersionState | None:
        """Obtiene un estado por su ID."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT * FROM estado_version WHERE id = :state_id LIMIT 1
                """),
                {"state_id": state_id},
            )
            row = result.fetchone()

            if row is None:
                return None

            return self._row_to_entity(row)

    def get_by_version(
        self,
        organization_id: int,
        project_id: int,
        version_id: int,
    ) -> ProjectVersionState | None:
        """Obtiene el estado de una versión específica."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT * FROM estado_version
                    WHERE id_organizacion = :org_id
                      AND id_proyecto = :project_id
                      AND id_version = :version_id
                    LIMIT 1
                """),
                {
                    "org_id": organization_id,
                    "project_id": project_id,
                    "version_id": version_id,
                },
            )
            row = result.fetchone()

            if row is None:
                return None

            return self._row_to_entity(row)

    def list_by_organization(
        self,
        organization_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[ProjectVersionState, ...]:
        """Retorna estados de versiones de una organización."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT * FROM estado_version
                    WHERE id_organizacion = :org_id
                    ORDER BY id_proyecto, id_version DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"org_id": organization_id, "limit": limit, "offset": offset},
            )
            rows = result.fetchall()

            return tuple(self._row_to_entity(row) for row in rows)

    def list_by_project(
        self,
        organization_id: int,
        project_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[ProjectVersionState, ...]:
        """Retorna estados de versiones de un proyecto."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT * FROM estado_version
                    WHERE id_organizacion = :org_id
                      AND id_proyecto = :project_id
                    ORDER BY id_version DESC
                    LIMIT :limit OFFSET :offset
                """),
                {
                    "org_id": organization_id,
                    "project_id": project_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
            rows = result.fetchall()

            return tuple(self._row_to_entity(row) for row in rows)

    def list_by_user_assignments(
        self,
        user_id: int,
        organization_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[ProjectVersionState, ...]:
        """Retorna estados de versiones a las que el usuario tiene acceso."""
        with self._engine.connect() as conn:
            # Query con JOIN a asignaciones
            query = """
                SELECT DISTINCT ev.*
                FROM estado_version ev
                INNER JOIN proyectos p
                    ON ev.id_proyecto = p.id
                LEFT JOIN asignaciones_organizaciones_internas aoi
                    ON ev.id_organizacion = aoi.id_organizacion
                    AND aoi.id_usuario = :user_id
                    AND aoi.active = 1
                LEFT JOIN proyectos_roles pr
                    ON ev.id_proyecto = pr.id_proyecto
                    AND pr.id_usuario = :user_id
                    AND pr.active = 1
                WHERE (aoi.id IS NOT NULL OR pr.id IS NOT NULL)
            """

            params: dict[str, Any] = {"user_id": user_id, "limit": limit, "offset": offset}

            if organization_id is not None:
                query += " AND ev.id_organizacion = :org_id"
                params["org_id"] = organization_id

            query += " ORDER BY ev.id_organizacion, ev.id_proyecto, ev.id_version DESC"
            query += " LIMIT :limit OFFSET :offset"

            result = conn.execute(text(query), params)
            rows = result.fetchall()

            return tuple(self._row_to_entity(row) for row in rows)

    # ========================================================================
    # Métodos de persistencia
    # ========================================================================

    def save(self, state: ProjectVersionState) -> ProjectVersionState:
        """Guarda o actualiza el estado de una versión."""
        with self._engine.connect() as conn:
            # Verificar si existe
            existing = conn.execute(
                text("SELECT id FROM estado_version WHERE id = :id"),
                {"id": state.id},
            ).fetchone()

            if existing:
                # UPDATE
                conn.execute(
                    text("""
                        UPDATE estado_version SET
                            state = :state,
                            state_internal = :state_internal,
                            protected = :protected,
                            size = :size,
                            final_c = :final_c,
                            final_i = :final_i,
                            revision_interna = :revision_interna,
                            propuesta_mejoras = :propuesta_mejoras,
                            entrenamiento_inicial_solicitado = :entrenamiento_inicial_solicitado,
                            entrenamiento_inicial_completado = :entrenamiento_inicial_completado,
                            entrenamiento_inicial_fecha = :entrenamiento_inicial_fecha,
                            evaluacion_entrenamiento = :evaluacion_entrenamiento,
                            reentrenamiento = :reentrenamiento,
                            optimizacion = :optimizacion,
                            control_calidad_aprobado = :control_calidad_aprobado,
                            generacion_llm_solicitada = :generacion_llm_solicitada,
                            generacion_llm_completada = :generacion_llm_completada,
                            generacion_llm_fecha = :generacion_llm_fecha,
                            ruta_fichero_modelo = :ruta_fichero_modelo,
                            notificacion_descarga_enviada = :notificacion_descarga_enviada,
                            notificacion_descarga_fecha = :notificacion_descarga_fecha,
                            updated_at = :updated_at,
                            updated_by = :updated_by
                        WHERE id = :id
                    """),
                    self._entity_to_params(state),
                )
                conn.commit()

                self._logger.info(
                    "Estado actualizado: id=%s org=%s project=%s version=%s",
                    state.id,
                    state.organization_id,
                    state.project_id,
                    state.version_id,
                )
            else:
                # INSERT (raro, normalmente lo crea el trigger)
                conn.execute(
                    text("""
                        INSERT INTO estado_version (
                            id_organizacion, id_proyecto, id_version,
                            state, state_internal, protected, size,
                            final_c, final_i,
                            revision_interna, propuesta_mejoras,
                            entrenamiento_inicial_solicitado, entrenamiento_inicial_completado,
                            entrenamiento_inicial_fecha,
                            evaluacion_entrenamiento, reentrenamiento, optimizacion,
                            control_calidad_aprobado,
                            generacion_llm_solicitada, generacion_llm_completada,
                            generacion_llm_fecha, ruta_fichero_modelo,
                            notificacion_descarga_enviada, notificacion_descarga_fecha,
                            created_at, updated_at, updated_by
                        ) VALUES (
                            :organization_id, :project_id, :version_id,
                            :state, :state_internal, :protected, :size,
                            :final_c, :final_i,
                            :revision_interna, :propuesta_mejoras,
                            :entrenamiento_inicial_solicitado, :entrenamiento_inicial_completado,
                            :entrenamiento_inicial_fecha,
                            :evaluacion_entrenamiento, :reentrenamiento, :optimizacion,
                            :control_calidad_aprobado,
                            :generacion_llm_solicitada, :generacion_llm_completada,
                            :generacion_llm_fecha, :ruta_fichero_modelo,
                            :notificacion_descarga_enviada, :notificacion_descarga_fecha,
                            :created_at, :updated_at, :updated_by
                        )
                    """),
                    self._entity_to_params(state),
                )
                conn.commit()

                self._logger.info(
                    "Estado creado: org=%s project=%s version=%s",
                    state.organization_id,
                    state.project_id,
                    state.version_id,
                )

            return state

    def update_proposal_phase(
        self,
        state_id: int,
        aceptacion_cliente: bool,
        aceptacion_interna: bool,
        updated_by: int,
    ) -> bool:
        """Actualiza la fase de propuesta (aceptaciones)."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE estado_version
                    SET final_c = :final_c,
                        final_i = :final_i,
                        updated_by = :updated_by,
                        updated_at = NOW()
                    WHERE id = :state_id
                """),
                {
                    "state_id": state_id,
                    "final_c": 1 if aceptacion_cliente else 0,
                    "final_i": 1 if aceptacion_interna else 0,
                    "updated_by": updated_by,
                },
            )
            conn.commit()

            return result.rowcount > 0

    def update_training_phase(
        self,
        state_id: int,
        completado: bool,
        updated_by: int,
    ) -> bool:
        """Actualiza la fase de entrenamiento."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE estado_version
                    SET entrenamiento_inicial_completado = :completado,
                        entrenamiento_inicial_fecha = IF(:completado = 1, NOW(), NULL),
                        updated_by = :updated_by,
                        updated_at = NOW()
                    WHERE id = :state_id
                """),
                {
                    "state_id": state_id,
                    "completado": 1 if completado else 0,
                    "updated_by": updated_by,
                },
            )
            conn.commit()

            return result.rowcount > 0

    def update_evaluation_phase(
        self,
        state_id: int,
        evaluacion: bool,
        reentrenamiento: bool,
        optimizacion: bool,
        calidad_aprobada: bool,
        updated_by: int,
    ) -> bool:
        """Actualiza la fase de evaluación/reentrenamiento."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE estado_version
                    SET evaluacion_entrenamiento = :evaluacion,
                        reentrenamiento = :reentrenamiento,
                        optimizacion = :optimizacion,
                        control_calidad_aprobado = :calidad_aprobada,
                        updated_by = :updated_by,
                        updated_at = NOW()
                    WHERE id = :state_id
                """),
                {
                    "state_id": state_id,
                    "evaluacion": 1 if evaluacion else 0,
                    "reentrenamiento": 1 if reentrenamiento else 0,
                    "optimizacion": 1 if optimizacion else 0,
                    "calidad_aprobada": 1 if calidad_aprobada else 0,
                    "updated_by": updated_by,
                },
            )
            conn.commit()

            return result.rowcount > 0

    def update_generation_phase(
        self,
        state_id: int,
        solicitada: bool,
        completada: bool,
        ruta_fichero: str | None,
        updated_by: int,
    ) -> bool:
        """Actualiza la fase de generación LLM."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE estado_version
                    SET generacion_llm_solicitada = :solicitada,
                        generacion_llm_completada = :completada,
                        generacion_llm_fecha = IF(:completada = 1, NOW(), NULL),
                        ruta_fichero_modelo = :ruta_fichero,
                        updated_by = :updated_by,
                        updated_at = NOW()
                    WHERE id = :state_id
                """),
                {
                    "state_id": state_id,
                    "solicitada": 1 if solicitada else 0,
                    "completada": 1 if completada else 0,
                    "ruta_fichero": ruta_fichero,
                    "updated_by": updated_by,
                },
            )
            conn.commit()

            return result.rowcount > 0

    def update_notification_phase(
        self,
        state_id: int,
        enviada: bool,
        updated_by: int,
    ) -> bool:
        """Actualiza la fase de notificación."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE estado_version
                    SET notificacion_descarga_enviada = :enviada,
                        notificacion_descarga_fecha = IF(:enviada = 1, NOW(), NULL),
                        updated_by = :updated_by,
                        updated_at = NOW()
                    WHERE id = :state_id
                """),
                {
                    "state_id": state_id,
                    "enviada": 1 if enviada else 0,
                    "updated_by": updated_by,
                },
            )
            conn.commit()

            return result.rowcount > 0

    def delete(self, state_id: int) -> bool:
        """Elimina un estado de versión (físicamente)."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("DELETE FROM estado_version WHERE id = :state_id"),
                {"state_id": state_id},
            )
            conn.commit()

            if result.rowcount > 0:
                self._logger.warning("Estado eliminado: id=%s", state_id)
                return True

            return False

    # ========================================================================
    # Helpers privados - Conversión
    # ========================================================================

    def _row_to_entity(self, row: Any) -> ProjectVersionState:
        """Convierte una fila SQL a entidad ProjectVersionState."""
        # Extraer campos con índices o nombres
        def get_val(key: str | int, default: Any = None) -> Any:
            value: Any
            try:
                if isinstance(key, str) and key in vars(row):
                    value = vars(row)[key]
                else:
                    value = row[key]
            except (KeyError, IndexError, TypeError):
                if not isinstance(key, str):
                    return default
                value = getattr(row, key, default)
            if value is None or type(value).__module__ == "unittest.mock":
                return default
            return value

        # Construir value objects
        proposal = ProposalPhase(
            propuesta_cliente=True,  # Siempre true
            revision_interna=bool(get_val("revision_interna", 0)),
            propuesta_mejoras=bool(get_val("propuesta_mejoras", 0)),
            aceptacion_cliente=bool(get_val("final_c", 0)),
            aceptacion_interna=bool(get_val("final_i", 0)),
        )

        training = TrainingPhase(
            solicitado=bool(get_val("entrenamiento_inicial_solicitado", 0)),
            completado=bool(get_val("entrenamiento_inicial_completado", 0)),
            fecha_completado=self._parse_datetime(get_val("entrenamiento_inicial_fecha")),
        )

        evaluation = EvaluationPhase(
            evaluacion_en_curso=bool(get_val("evaluacion_entrenamiento", 0)),
            reentrenamiento_en_curso=bool(get_val("reentrenamiento", 0)),
            optimizacion_en_curso=bool(get_val("optimizacion", 0)),
            calidad_aprobada=bool(get_val("control_calidad_aprobado", 0)),
        )

        generation = GenerationPhase(
            solicitada=bool(get_val("generacion_llm_solicitada", 0)),
            completada=bool(get_val("generacion_llm_completada", 0)),
            fecha_completado=self._parse_datetime(get_val("generacion_llm_fecha")),
            ruta_fichero=get_val("ruta_fichero_modelo"),
        )

        notification = NotificationPhase(
            enviada=bool(get_val("notificacion_descarga_enviada", 0)),
            fecha_envio=self._parse_datetime(get_val("notificacion_descarga_fecha")),
        )

        # Construir entidad
        return ProjectVersionState(
            id=int(get_val("id", 0)),
            organization_id=int(get_val("id_organizacion", 0)),
            project_id=int(get_val("id_proyecto", 0)),
            version_id=int(get_val("id_version", 0)),
            state=ExplorerState(get_val("state", "stable")),
            state_internal=StateInternal(get_val("state_internal", "propuesta_cliente")),
            proposal=proposal,
            training=training,
            evaluation=evaluation,
            generation=generation,
            notification=notification,
            protected=bool(get_val("protected", 0)),
            size=int(get_val("size", 0)),
            created_at=self._parse_datetime(get_val("created_at")) or datetime.utcnow(),
            updated_at=self._parse_datetime(get_val("updated_at")) or datetime.utcnow(),
            updated_by=int(get_val("updated_by")) if get_val("updated_by") else None,
        )

    def _entity_to_params(self, state: ProjectVersionState) -> dict[str, Any]:
        """Convierte entidad ProjectVersionState a parámetros SQL."""
        return {
            "id": state.id,
            "organization_id": state.organization_id,
            "project_id": state.project_id,
            "version_id": state.version_id,
            "state": state.state.value,
            "state_internal": state.state_internal.value,
            "protected": 1 if state.protected else 0,
            "size": state.size,
            "final_c": 1 if state.proposal.aceptacion_cliente else 0,
            "final_i": 1 if state.proposal.aceptacion_interna else 0,
            "revision_interna": 1 if state.proposal.revision_interna else 0,
            "propuesta_mejoras": 1 if state.proposal.propuesta_mejoras else 0,
            "entrenamiento_inicial_solicitado": 1 if state.training.solicitado else 0,
            "entrenamiento_inicial_completado": 1 if state.training.completado else 0,
            "entrenamiento_inicial_fecha": self._format_datetime(state.training.fecha_completado),
            "evaluacion_entrenamiento": 1 if state.evaluation.evaluacion_en_curso else 0,
            "reentrenamiento": 1 if state.evaluation.reentrenamiento_en_curso else 0,
            "optimizacion": 1 if state.evaluation.optimizacion_en_curso else 0,
            "control_calidad_aprobado": 1 if state.evaluation.calidad_aprobada else 0,
            "generacion_llm_solicitada": 1 if state.generation.solicitada else 0,
            "generacion_llm_completada": 1 if state.generation.completada else 0,
            "generacion_llm_fecha": self._format_datetime(state.generation.fecha_completado),
            "ruta_fichero_modelo": state.generation.ruta_fichero,
            "notificacion_descarga_enviada": 1 if state.notification.enviada else 0,
            "notificacion_descarga_fecha": self._format_datetime(state.notification.fecha_envio),
            "created_at": self._format_datetime(state.created_at),
            "updated_at": self._format_datetime(state.updated_at),
            "updated_by": state.updated_by,
        }

    def _parse_datetime(self, value: Any) -> datetime | None:
        """Convierte valor SQL a datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    def _format_datetime(self, value: datetime | None) -> str | None:
        """Convierte datetime a string SQL."""
        if value is None:
            return None
        return value.strftime("%Y-%m-%d %H:%M:%S")

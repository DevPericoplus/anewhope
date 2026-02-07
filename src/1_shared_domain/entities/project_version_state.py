"""Entidades de dominio para gestión de estado de versiones de proyectos.

Este módulo define las entidades y value objects para modelar el ciclo de vida
completo de una versión de proyecto, desde propuesta hasta notificación de descarga.

Arquitectura DDD:
- ProjectVersionState: Entidad raíz (aggregate root)
- Value Objects: StateInternal, ProposalPhase, TrainingPhase, etc.
- Invariantes: Validaciones de negocio en el dominio
- Comportamiento: Métodos de transición de estado
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ============================================================================
# Enumeraciones
# ============================================================================


class StateInternal(str, Enum):
    """Estados internos del flujo de trabajo (backoffice).

    Estos estados son gestionados automáticamente por triggers en base de datos
    y reflejan la fase actual del proyecto en el flujo de misión.
    """

    # Fase 1: Propuesta/Revisión
    PROPUESTA_CLIENTE = "propuesta_cliente"
    REVISION_INTERNA = "revision_interna"
    PROPUESTA_MEJORAS = "propuesta_mejoras"
    ACEPTACION_CLIENTE = "aceptacion_cliente"
    ACEPTACION_INTERNA = "aceptacion_interna"

    # Fase 2: Entrenamiento Inicial
    ENTRENAMIENTO_INICIAL = "entrenamiento_inicial"
    ENTRENAMIENTO_INICIAL_COMPLETADO = "entrenamiento_inicial_completado"

    # Fase 3: Evaluación/Reentrenamiento
    EVALUACION_ENTRENAMIENTO = "evaluacion_entrenamiento"
    REENTRENAMIENTO = "reentrenamiento"
    OPTIMIZACION = "optimizacion"
    APROBACION_CALIDAD = "aprobacion_calidad"

    # Fase 4: Generación LLM
    GENERACION_LLM = "generacion_llm"
    GENERACION_LLM_COMPLETADA = "generacion_llm_completada"

    # Fase 5: Notificación
    NOTIFICACION_DESCARGA = "notificacion_descarga"

    @property
    def phase_number(self) -> int:
        """Retorna el número de fase (1-5) para ordenamiento."""
        phase_map = {
            # Fase 1
            self.PROPUESTA_CLIENTE: 1,
            self.REVISION_INTERNA: 1,
            self.PROPUESTA_MEJORAS: 1,
            self.ACEPTACION_CLIENTE: 1,
            self.ACEPTACION_INTERNA: 1,
            # Fase 2
            self.ENTRENAMIENTO_INICIAL: 2,
            self.ENTRENAMIENTO_INICIAL_COMPLETADO: 2,
            # Fase 3
            self.EVALUACION_ENTRENAMIENTO: 3,
            self.REENTRENAMIENTO: 3,
            self.OPTIMIZACION: 3,
            self.APROBACION_CALIDAD: 3,
            # Fase 4
            self.GENERACION_LLM: 4,
            self.GENERACION_LLM_COMPLETADA: 4,
            # Fase 5
            self.NOTIFICACION_DESCARGA: 5,
        }
        return phase_map.get(self, 0)

    @property
    def display_name(self) -> str:
        """Retorna nombre legible para UI."""
        names = {
            self.PROPUESTA_CLIENTE: "Propuesta del Cliente",
            self.REVISION_INTERNA: "Revisión Interna",
            self.PROPUESTA_MEJORAS: "Propuesta de Mejoras",
            self.ACEPTACION_CLIENTE: "Aceptación del Cliente",
            self.ACEPTACION_INTERNA: "Aceptación Interna",
            self.ENTRENAMIENTO_INICIAL: "Entrenamiento Inicial",
            self.ENTRENAMIENTO_INICIAL_COMPLETADO: "Entrenamiento Completado",
            self.EVALUACION_ENTRENAMIENTO: "Evaluación",
            self.REENTRENAMIENTO: "Reentrenamiento",
            self.OPTIMIZACION: "Optimización",
            self.APROBACION_CALIDAD: "Aprobación de Calidad",
            self.GENERACION_LLM: "Generación del Modelo",
            self.GENERACION_LLM_COMPLETADA: "Modelo Generado",
            self.NOTIFICACION_DESCARGA: "Notificación Enviada",
        }
        return names.get(self, self.value)


class ExplorerState(str, Enum):
    """Estados para el componente explorador (no tocar).

    Estos estados son usados por el explorador y no deben ser modificados
    por el backoffice para mantener estabilidad del componente crítico.
    """

    STABLE = "stable"
    UNSTABLE = "unstable"
    DEPRECATED = "deprecated"


# ============================================================================
# Value Objects - Fase 1: Propuesta/Revisión
# ============================================================================


@dataclass(frozen=True)
class ProposalPhase:
    """Value object para fase de propuesta y revisión (Fase 1).

    Esta fase representa el bucle de propuesta-revisión-mejoras entre
    cliente e interno hasta lograr doble aceptación.

    Attributes:
        propuesta_cliente: Cliente propone/solicita (siempre true al inicio)
        revision_interna: Revisión interna en curso
        propuesta_mejoras: Propuesta de mejoras generada
        aceptacion_cliente: Cliente acepta (final_c)
        aceptacion_interna: Interno acepta (final_i)
    """

    propuesta_cliente: bool = True  # Siempre true
    revision_interna: bool = False
    propuesta_mejoras: bool = False
    aceptacion_cliente: bool = False  # final_c
    aceptacion_interna: bool = False  # final_i

    @property
    def is_approved(self) -> bool:
        """Verifica si la propuesta está aprobada por ambas partes."""
        return self.aceptacion_cliente and self.aceptacion_interna

    @property
    def is_in_review_loop(self) -> bool:
        """Verifica si está en bucle de revisión (sin doble aceptación)."""
        return not self.is_approved

    def approve_by_client(self) -> ProposalPhase:
        """Marca aprobación del cliente."""
        return ProposalPhase(
            propuesta_cliente=self.propuesta_cliente,
            revision_interna=self.revision_interna,
            propuesta_mejoras=self.propuesta_mejoras,
            aceptacion_cliente=True,
            aceptacion_interna=self.aceptacion_interna,
        )

    def approve_by_internal(self) -> ProposalPhase:
        """Marca aprobación interna."""
        return ProposalPhase(
            propuesta_cliente=self.propuesta_cliente,
            revision_interna=self.revision_interna,
            propuesta_mejoras=self.propuesta_mejoras,
            aceptacion_cliente=self.aceptacion_cliente,
            aceptacion_interna=True,
        )

    def revoke_client_approval(self) -> ProposalPhase:
        """Retira aprobación del cliente."""
        return ProposalPhase(
            propuesta_cliente=self.propuesta_cliente,
            revision_interna=self.revision_interna,
            propuesta_mejoras=self.propuesta_mejoras,
            aceptacion_cliente=False,
            aceptacion_interna=self.aceptacion_interna,
        )

    def revoke_internal_approval(self) -> ProposalPhase:
        """Retira aprobación interna."""
        return ProposalPhase(
            propuesta_cliente=self.propuesta_cliente,
            revision_interna=self.revision_interna,
            propuesta_mejoras=self.propuesta_mejoras,
            aceptacion_cliente=self.aceptacion_cliente,
            aceptacion_interna=False,
        )


# ============================================================================
# Value Objects - Fase 2: Entrenamiento Inicial
# ============================================================================


@dataclass(frozen=True)
class TrainingPhase:
    """Value object para fase de entrenamiento inicial (Fase 2).

    Esta fase se activa automáticamente cuando la propuesta es aprobada
    por ambas partes (final_c=1 AND final_i=1).

    Attributes:
        solicitado: Entrenamiento solicitado (automático con doble aprobación)
        completado: Entrenamiento completado
        fecha_completado: Fecha de completado (nullable)
    """

    solicitado: bool = False
    completado: bool = False
    fecha_completado: datetime | None = None

    @property
    def is_in_progress(self) -> bool:
        """Verifica si el entrenamiento está en curso."""
        return self.solicitado and not self.completado

    @property
    def is_completed(self) -> bool:
        """Verifica si el entrenamiento está completado."""
        return self.completado

    def mark_completed(self, completed_at: datetime | None = None) -> TrainingPhase:
        """Marca el entrenamiento como completado."""
        return TrainingPhase(
            solicitado=self.solicitado,
            completado=True,
            fecha_completado=completed_at or datetime.utcnow(),
        )


# ============================================================================
# Value Objects - Fase 3: Evaluación/Reentrenamiento
# ============================================================================


@dataclass(frozen=True)
class EvaluationPhase:
    """Value object para fase de evaluación y reentrenamiento (Fase 3).

    Esta fase representa el bucle de evaluación-reentrenamiento-optimización
    hasta lograr aprobación de control de calidad.

    Attributes:
        evaluacion_en_curso: Evaluación del entrenamiento en curso
        reentrenamiento_en_curso: Reentrenamiento en curso
        optimizacion_en_curso: Optimización en curso
        calidad_aprobada: Control de calidad aprobado (salida del bucle)
    """

    evaluacion_en_curso: bool = False
    reentrenamiento_en_curso: bool = False
    optimizacion_en_curso: bool = False
    calidad_aprobada: bool = False

    @property
    def is_in_loop(self) -> bool:
        """Verifica si está en bucle de evaluación (sin aprobación de calidad)."""
        return not self.calidad_aprobada

    @property
    def is_approved(self) -> bool:
        """Verifica si pasó control de calidad."""
        return self.calidad_aprobada

    def approve_quality(self) -> EvaluationPhase:
        """Marca aprobación de control de calidad (salida del bucle)."""
        return EvaluationPhase(
            evaluacion_en_curso=False,
            reentrenamiento_en_curso=False,
            optimizacion_en_curso=False,
            calidad_aprobada=True,
        )


# ============================================================================
# Value Objects - Fase 4: Generación LLM
# ============================================================================


@dataclass(frozen=True)
class GenerationPhase:
    """Value object para fase de generación del modelo LLM (Fase 4).

    Esta fase se activa después de aprobar el control de calidad y genera
    el fichero del modelo LLM listo para descarga.

    Attributes:
        solicitada: Generación del modelo solicitada
        completada: Generación del modelo completada
        fecha_completado: Fecha de completado (nullable)
        ruta_fichero: Ruta del fichero generado (nullable)
    """

    solicitada: bool = False
    completada: bool = False
    fecha_completado: datetime | None = None
    ruta_fichero: str | None = None

    @property
    def is_in_progress(self) -> bool:
        """Verifica si la generación está en curso."""
        return self.solicitada and not self.completada

    @property
    def is_completed(self) -> bool:
        """Verifica si la generación está completada."""
        return self.completada

    @property
    def has_file(self) -> bool:
        """Verifica si hay fichero generado."""
        return self.ruta_fichero is not None and self.ruta_fichero != ""

    def mark_completed(
        self,
        file_path: str,
        completed_at: datetime | None = None,
    ) -> GenerationPhase:
        """Marca la generación como completada con ruta de fichero."""
        return GenerationPhase(
            solicitada=self.solicitada,
            completada=True,
            fecha_completado=completed_at or datetime.utcnow(),
            ruta_fichero=file_path,
        )


# ============================================================================
# Value Objects - Fase 5: Notificación
# ============================================================================


@dataclass(frozen=True)
class NotificationPhase:
    """Value object para fase de notificación de descarga (Fase 5).

    Esta fase notifica al cliente que el modelo está listo para descarga.

    Attributes:
        enviada: Notificación enviada al cliente
        fecha_envio: Fecha de envío (nullable)
    """

    enviada: bool = False
    fecha_envio: datetime | None = None

    @property
    def is_sent(self) -> bool:
        """Verifica si la notificación fue enviada."""
        return self.enviada

    def mark_sent(self, sent_at: datetime | None = None) -> NotificationPhase:
        """Marca la notificación como enviada."""
        return NotificationPhase(
            enviada=True,
            fecha_envio=sent_at or datetime.utcnow(),
        )


# ============================================================================
# Entidad Principal - ProjectVersionState
# ============================================================================


@dataclass
class ProjectVersionState:
    """Entidad de dominio que representa el estado de una versión de proyecto.

    Esta es la entidad raíz (aggregate root) que encapsula el ciclo de vida
    completo de una versión de proyecto, desde propuesta hasta notificación.

    Responsabilidades:
    - Mantener integridad del estado a través de las 5 fases
    - Validar transiciones de estado según reglas de negocio
    - Exponer comportamiento de dominio (métodos de transición)
    - Garantizar invariantes (ej: no generar LLM sin calidad aprobada)

    Attributes:
        id: ID del registro en estado_version
        organization_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        state: Estado para explorador (no tocar)
        state_internal: Estado interno para backoffice (auto-gestionado)
        proposal: Fase 1 - Propuesta y revisión
        training: Fase 2 - Entrenamiento inicial
        evaluation: Fase 3 - Evaluación y reentrenamiento
        generation: Fase 4 - Generación del modelo LLM
        notification: Fase 5 - Notificación de descarga
        protected: Versión protegida contra eliminación
        size: Tamaño de la versión
        created_at: Fecha de creación
        updated_at: Fecha de última actualización
        updated_by: ID del usuario que hizo el último cambio
    """

    # Identificación
    id: int
    organization_id: int
    project_id: int
    version_id: int

    # Estados
    state: ExplorerState
    state_internal: StateInternal

    # Fases del flujo (Value Objects)
    proposal: ProposalPhase
    training: TrainingPhase
    evaluation: EvaluationPhase
    generation: GenerationPhase
    notification: NotificationPhase

    # Metadatos
    protected: bool = False
    size: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    updated_by: int | None = None

    # ========================================================================
    # Propiedades computadas
    # ========================================================================

    @property
    def current_phase_number(self) -> int:
        """Retorna el número de fase actual (1-5)."""
        return self.state_internal.phase_number

    @property
    def is_ready_for_training(self) -> bool:
        """Verifica si está lista para iniciar entrenamiento."""
        return self.proposal.is_approved

    @property
    def is_ready_for_generation(self) -> bool:
        """Verifica si está lista para generar modelo."""
        return self.evaluation.is_approved

    @property
    def is_ready_for_notification(self) -> bool:
        """Verifica si está lista para notificar descarga."""
        return self.generation.is_completed

    @property
    def is_completed(self) -> bool:
        """Verifica si completó todo el ciclo (notificación enviada)."""
        return self.notification.is_sent

    @property
    def progress_percentage(self) -> float:
        """Calcula el porcentaje de progreso (0-100)."""
        # Cada fase vale 20%
        progress = 0.0

        # Fase 1: Propuesta aprobada
        if self.proposal.is_approved:
            progress += 20.0

        # Fase 2: Entrenamiento completado
        if self.training.is_completed:
            progress += 20.0

        # Fase 3: Calidad aprobada
        if self.evaluation.is_approved:
            progress += 20.0

        # Fase 4: Generación completada
        if self.generation.is_completed:
            progress += 20.0

        # Fase 5: Notificación enviada
        if self.notification.is_sent:
            progress += 20.0

        return progress

    # ========================================================================
    # Métodos de negocio - Transiciones de estado
    # ========================================================================

    def approve_proposal_by_client(self, user_id: int) -> None:
        """Marca aprobación de propuesta por cliente."""
        self.proposal = self.proposal.approve_by_client()
        self.updated_by = user_id
        self.updated_at = datetime.utcnow()

    def approve_proposal_by_internal(self, user_id: int) -> None:
        """Marca aprobación de propuesta por interno."""
        self.proposal = self.proposal.approve_by_internal()
        self.updated_by = user_id
        self.updated_at = datetime.utcnow()

    def revoke_client_approval(self, user_id: int) -> None:
        """Retira aprobación del cliente."""
        self.proposal = self.proposal.revoke_client_approval()
        self.updated_by = user_id
        self.updated_at = datetime.utcnow()

    def revoke_internal_approval(self, user_id: int) -> None:
        """Retira aprobación interna."""
        self.proposal = self.proposal.revoke_internal_approval()
        self.updated_by = user_id
        self.updated_at = datetime.utcnow()

    def complete_training(self, user_id: int, completed_at: datetime | None = None) -> None:
        """Marca entrenamiento como completado."""
        if not self.training.solicitado:
            raise ProjectVersionStateError(
                "No se puede completar entrenamiento sin haberlo solicitado"
            )

        self.training = self.training.mark_completed(completed_at)
        self.updated_by = user_id
        self.updated_at = datetime.utcnow()

    def approve_quality(self, user_id: int) -> None:
        """Marca aprobación de control de calidad."""
        if not self.training.is_completed:
            raise ProjectVersionStateError(
                "No se puede aprobar calidad sin haber completado el entrenamiento"
            )

        self.evaluation = self.evaluation.approve_quality()
        self.updated_by = user_id
        self.updated_at = datetime.utcnow()

    def request_generation(self, user_id: int) -> None:
        """Solicita generación del modelo LLM."""
        if not self.evaluation.is_approved:
            raise ProjectVersionStateError(
                "No se puede solicitar generación sin aprobación de calidad"
            )

        self.generation = GenerationPhase(solicitada=True)
        self.updated_by = user_id
        self.updated_at = datetime.utcnow()

    def complete_generation(
        self,
        user_id: int,
        file_path: str,
        completed_at: datetime | None = None,
    ) -> None:
        """Marca generación como completada."""
        if not self.generation.solicitada:
            raise ProjectVersionStateError(
                "No se puede completar generación sin haberla solicitado"
            )

        if not file_path:
            raise ProjectVersionStateError(
                "Se requiere ruta de fichero para completar generación"
            )

        self.generation = self.generation.mark_completed(file_path, completed_at)
        self.updated_by = user_id
        self.updated_at = datetime.utcnow()

    def send_notification(self, user_id: int, sent_at: datetime | None = None) -> None:
        """Envía notificación de descarga al cliente."""
        if not self.generation.is_completed:
            raise ProjectVersionStateError(
                "No se puede enviar notificación sin haber completado la generación"
            )

        self.notification = self.notification.mark_sent(sent_at)
        self.updated_by = user_id
        self.updated_at = datetime.utcnow()

    # ========================================================================
    # Métodos de consulta
    # ========================================================================

    def can_transition_to_phase(self, phase_number: int) -> bool:
        """Verifica si puede transicionar a una fase específica.

        Args:
            phase_number: Número de fase (1-5)

        Returns:
            True si puede transicionar, False en caso contrario
        """
        if phase_number == 1:
            return True  # Siempre en fase 1 al inicio
        elif phase_number == 2:
            return self.proposal.is_approved
        elif phase_number == 3:
            return self.training.is_completed
        elif phase_number == 4:
            return self.evaluation.is_approved
        elif phase_number == 5:
            return self.generation.is_completed
        else:
            return False

    def get_blocking_reasons(self) -> list[str]:
        """Retorna lista de razones que impiden avanzar a siguiente fase.

        Returns:
            Lista de mensajes describiendo bloqueos
        """
        reasons: list[str] = []

        if not self.proposal.is_approved:
            if not self.proposal.aceptacion_cliente:
                reasons.append("Falta aceptación del cliente")
            if not self.proposal.aceptacion_interna:
                reasons.append("Falta aceptación interna")

        if self.proposal.is_approved and not self.training.is_completed:
            reasons.append("Entrenamiento inicial pendiente")

        if self.training.is_completed and not self.evaluation.is_approved:
            reasons.append("Falta aprobación de control de calidad")

        if self.evaluation.is_approved and not self.generation.is_completed:
            if not self.generation.solicitada:
                reasons.append("Generación LLM no solicitada")
            else:
                reasons.append("Generación LLM en curso")

        if self.generation.is_completed and not self.notification.is_sent:
            reasons.append("Notificación de descarga pendiente")

        return reasons

    # ========================================================================
    # Factory methods
    # ========================================================================

    @classmethod
    def create_initial(
        cls,
        id: int,
        organization_id: int,
        project_id: int,
        version_id: int,
    ) -> ProjectVersionState:
        """Crea una instancia inicial con estado de propuesta del cliente.

        Args:
            id: ID del registro
            organization_id: ID de la organización
            project_id: ID del proyecto
            version_id: ID de la versión

        Returns:
            Nueva instancia en estado inicial
        """
        return cls(
            id=id,
            organization_id=organization_id,
            project_id=project_id,
            version_id=version_id,
            state=ExplorerState.STABLE,
            state_internal=StateInternal.PROPUESTA_CLIENTE,
            proposal=ProposalPhase(),
            training=TrainingPhase(),
            evaluation=EvaluationPhase(),
            generation=GenerationPhase(),
            notification=NotificationPhase(),
        )


# ============================================================================
# Excepciones de dominio
# ============================================================================


class ProjectVersionStateError(Exception):
    """Excepción base para errores de dominio en ProjectVersionState."""

    pass


class InvalidStateTransitionError(ProjectVersionStateError):
    """Error al intentar una transición de estado inválida."""

    pass

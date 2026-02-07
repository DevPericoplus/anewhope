"""Servicio de aplicación para gestión de estados de versiones de proyectos.

Este servicio coordina operaciones entre el dominio (ProjectVersionState)
y la persistencia (ProjectVersionStateRepository).

Responsabilidades:
- Coordinar casos de uso de alto nivel
- Validar permisos según roles y asignaciones
- Delegar lógica de negocio a la entidad de dominio
- Orquestar persistencia a través del repositorio
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


# ============================================================================
# Carga dinámica de módulos DDD (evitar imports circulares)
# ============================================================================


def _load_domain_entities() -> Any:
    """Carga dinámicamente el módulo de entidades de dominio."""
    module_path = (
        Path(__file__).resolve().parents[2]
        / "1_shared_domain/entities/project_version_state.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_project_version_state_entities", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar project_version_state entities")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_project_version_state_entities"] = module
    spec.loader.exec_module(module)
    return module


_entities = _load_domain_entities()
ProjectVersionState = _entities.ProjectVersionState
StateInternal = _entities.StateInternal
ProjectVersionStateError = _entities.ProjectVersionStateError
InvalidStateTransitionError = _entities.InvalidStateTransitionError


# ============================================================================
# Servicio de Aplicación
# ============================================================================


class ProjectVersionStateService:
    """Servicio de aplicación para gestión de estados de versiones.

    Este servicio NO contiene lógica de negocio (esa está en el dominio).
    Se encarga de coordinar operaciones y validar permisos.

    Args:
        repository: Implementación del repositorio de persistencia
        db_engine: SQLAlchemy engine para consultas de permisos (opcional)
    """

    def __init__(self, repository: Any, db_engine: Any | None = None):
        """Inicializa el servicio con un repositorio.

        Args:
            repository: Debe implementar ProjectVersionStateRepository Protocol
            db_engine: SQLAlchemy Engine para consultas de permisos
        """
        self._repository = repository
        self._db_engine = db_engine

    # ========================================================================
    # Consultas - Obtener estados
    # ========================================================================

    def get_state_by_id(
        self,
        state_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState | None:
        """Obtiene un estado por ID con validación de permisos.

        Args:
            state_id: ID del estado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            ProjectVersionState si existe y tiene permisos, None en caso contrario

        Raises:
            PermissionDeniedError: Si no tiene permisos para ver el estado
        """
        state = self._repository.get_by_id(state_id)

        if state is None:
            return None

        # SuperAdmin puede ver todo
        if requesting_user_identity_type == 1:
            return state

        # Otros usuarios: verificar asignación
        if not self._has_read_permission(
            requesting_user_id,
            state.organization_id,
            state.project_id,
        ):
            raise PermissionDeniedError(
                f"Usuario {requesting_user_id} no tiene permisos para ver estado {state_id}"
            )

        return state

    def get_state_by_version(
        self,
        organization_id: int,
        project_id: int,
        version_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState | None:
        """Obtiene estado de una versión con validación de permisos.

        Args:
            organization_id: ID de la organización
            project_id: ID del proyecto
            version_id: ID de la versión
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            ProjectVersionState si existe y tiene permisos, None en caso contrario
        """
        state = self._repository.get_by_version(
            organization_id, project_id, version_id
        )

        if state is None:
            return None

        # SuperAdmin puede ver todo
        if requesting_user_identity_type == 1:
            return state

        # Otros usuarios: verificar asignación
        if not self._has_read_permission(
            requesting_user_id, organization_id, project_id
        ):
            raise PermissionDeniedError(
                f"Usuario {requesting_user_id} no tiene permisos para ver versión"
            )

        return state

    def list_states_by_user(
        self,
        requesting_user_id: int,
        requesting_user_identity_type: int,
        organization_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[ProjectVersionState, ...]:
        """Lista estados según las asignaciones del usuario.

        Args:
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante
            organization_id: Filtrar por organización (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a saltar

        Returns:
            Tupla de estados visibles para el usuario
        """
        # SuperAdmin: puede ver todo de una organización o todas
        if requesting_user_identity_type == 1:
            if organization_id:
                return self._repository.list_by_organization(
                    organization_id, limit, offset
                )
            # Si no se especifica org, usar list_by_user_assignments que devolverá todas
            # (aunque SuperAdmin no tenga asignaciones explícitas, el repo debe manejarlo)
            return self._repository.list_by_user_assignments(
                requesting_user_id, organization_id, limit, offset
            )

        # Otros usuarios: filtrar por asignaciones
        return self._repository.list_by_user_assignments(
            requesting_user_id, organization_id, limit, offset
        )

    # ========================================================================
    # Comandos - Actualizar estados (Fase 1: Propuesta)
    # ========================================================================

    def approve_proposal_by_client(
        self,
        state_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState:
        """Marca aprobación de propuesta por cliente.

        Args:
            state_id: ID del estado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Estado actualizado

        Raises:
            PermissionDeniedError: Si no tiene permisos de escritura
            ProjectVersionStateError: Si hay error de dominio
        """
        state = self._get_state_with_write_permission(
            state_id, requesting_user_id, requesting_user_identity_type
        )

        # Delegar lógica de negocio al dominio
        state.approve_proposal_by_client(requesting_user_id)

        # Persistir cambios
        return self._repository.save(state)

    def approve_proposal_by_internal(
        self,
        state_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState:
        """Marca aprobación de propuesta por interno.

        Args:
            state_id: ID del estado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Estado actualizado
        """
        state = self._get_state_with_write_permission(
            state_id, requesting_user_id, requesting_user_identity_type
        )

        state.approve_proposal_by_internal(requesting_user_id)
        return self._repository.save(state)

    def revoke_client_approval(
        self,
        state_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState:
        """Retira aprobación del cliente.

        Args:
            state_id: ID del estado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Estado actualizado
        """
        state = self._get_state_with_write_permission(
            state_id, requesting_user_id, requesting_user_identity_type
        )

        state.revoke_client_approval(requesting_user_id)
        return self._repository.save(state)

    def revoke_internal_approval(
        self,
        state_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState:
        """Retira aprobación interna.

        Args:
            state_id: ID del estado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Estado actualizado
        """
        state = self._get_state_with_write_permission(
            state_id, requesting_user_id, requesting_user_identity_type
        )

        state.revoke_internal_approval(requesting_user_id)
        return self._repository.save(state)

    # ========================================================================
    # Comandos - Actualizar estados (Fase 2: Entrenamiento)
    # ========================================================================

    def complete_training(
        self,
        state_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState:
        """Marca entrenamiento como completado.

        Args:
            state_id: ID del estado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Estado actualizado
        """
        state = self._get_state_with_write_permission(
            state_id, requesting_user_id, requesting_user_identity_type
        )

        state.complete_training(requesting_user_id)
        return self._repository.save(state)

    # ========================================================================
    # Comandos - Actualizar estados (Fase 3: Evaluación)
    # ========================================================================

    def approve_quality(
        self,
        state_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState:
        """Marca aprobación de control de calidad.

        Args:
            state_id: ID del estado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Estado actualizado
        """
        state = self._get_state_with_write_permission(
            state_id, requesting_user_id, requesting_user_identity_type
        )

        state.approve_quality(requesting_user_id)
        return self._repository.save(state)

    def update_evaluation_flags(
        self,
        state_id: int,
        evaluacion: bool,
        reentrenamiento: bool,
        optimizacion: bool,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState:
        """Actualiza flags del bucle de evaluación.

        Args:
            state_id: ID del estado
            evaluacion: Si está en evaluación
            reentrenamiento: Si está en reentrenamiento
            optimizacion: Si está en optimización
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Estado actualizado
        """
        state = self._get_state_with_write_permission(
            state_id, requesting_user_id, requesting_user_identity_type
        )

        # Usar método directo del repositorio para actualización granular
        success = self._repository.update_evaluation_phase(
            state_id=state_id,
            evaluacion=evaluacion,
            reentrenamiento=reentrenamiento,
            optimizacion=optimizacion,
            calidad_aprobada=state.evaluation.calidad_aprobada,
            updated_by=requesting_user_id,
        )

        if not success:
            raise ProjectVersionStateError("No se pudo actualizar fase de evaluación")

        # Re-cargar estado actualizado
        return self._repository.get_by_id(state_id) or state

    # ========================================================================
    # Comandos - Actualizar estados (Fase 4: Generación)
    # ========================================================================

    def request_generation(
        self,
        state_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState:
        """Solicita generación del modelo LLM.

        Args:
            state_id: ID del estado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Estado actualizado
        """
        state = self._get_state_with_write_permission(
            state_id, requesting_user_id, requesting_user_identity_type
        )

        state.request_generation(requesting_user_id)
        return self._repository.save(state)

    def complete_generation(
        self,
        state_id: int,
        file_path: str,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState:
        """Marca generación como completada.

        Args:
            state_id: ID del estado
            file_path: Ruta del fichero generado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Estado actualizado
        """
        state = self._get_state_with_write_permission(
            state_id, requesting_user_id, requesting_user_identity_type
        )

        state.complete_generation(requesting_user_id, file_path)
        return self._repository.save(state)

    # ========================================================================
    # Comandos - Actualizar estados (Fase 5: Notificación)
    # ========================================================================

    def send_notification(
        self,
        state_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState:
        """Envía notificación de descarga al cliente.

        Args:
            state_id: ID del estado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Estado actualizado
        """
        state = self._get_state_with_write_permission(
            state_id, requesting_user_id, requesting_user_identity_type
        )

        state.send_notification(requesting_user_id)
        return self._repository.save(state)

    # ========================================================================
    # Helpers privados - Permisos
    # ========================================================================

    def _get_state_with_write_permission(
        self,
        state_id: int,
        requesting_user_id: int,
        requesting_user_identity_type: int,
    ) -> ProjectVersionState:
        """Obtiene estado y valida permisos de escritura.

        Args:
            state_id: ID del estado
            requesting_user_id: ID del usuario solicitante
            requesting_user_identity_type: Tipo de identidad del solicitante

        Returns:
            Estado si tiene permisos

        Raises:
            NotFoundError: Si no existe el estado
            PermissionDeniedError: Si no tiene permisos de escritura
        """
        state = self._repository.get_by_id(state_id)

        if state is None:
            raise NotFoundError(f"Estado {state_id} no encontrado")

        # SuperAdmin puede editar todo
        if requesting_user_identity_type == 1:
            return state

        # Verificar permisos de escritura (no Auditor ni Lector)
        if not self._has_write_permission(
            requesting_user_id,
            requesting_user_identity_type,
            state.organization_id,
            state.project_id,
        ):
            raise PermissionDeniedError(
                f"Usuario {requesting_user_id} no tiene permisos de escritura"
            )

        return state

    def _has_read_permission(
        self,
        user_id: int,
        organization_id: int,
        project_id: int,
    ) -> bool:
        """Verifica si el usuario tiene permisos de lectura.

        Permisos de lectura: Cualquier asignación activa a organización o proyecto.

        Args:
            user_id: ID del usuario
            organization_id: ID de la organización
            project_id: ID del proyecto

        Returns:
            True si tiene permisos, False en caso contrario
        """
        # Si no hay engine configurado, permitir acceso (modo desarrollo)
        if self._db_engine is None:
            return True

        from sqlalchemy import text

        try:
            with self._db_engine.connect() as conn:
                # 1. Verificar asignación a nivel de organización
                result_org = conn.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM asignaciones_organizaciones_internas
                        WHERE id_usuario = :user_id
                          AND id_organizacion = :org_id
                          AND active = 1
                    """),
                    {"user_id": user_id, "org_id": organization_id},
                ).fetchone()

                if result_org and result_org.count > 0:
                    return True

                # 2. Verificar asignación a nivel de proyecto
                result_prj = conn.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM proyectos_roles
                        WHERE id_usuario = :user_id
                          AND id_organizacion = :org_id
                          AND id_proyecto = :project_id
                          AND active = 1
                    """),
                    {
                        "user_id": user_id,
                        "org_id": organization_id,
                        "project_id": project_id,
                    },
                ).fetchone()

                if result_prj and result_prj.count > 0:
                    return True

                return False

        except Exception:
            # En caso de error de DB, denegar acceso por seguridad
            return False

    def _has_write_permission(
        self,
        user_id: int,
        identity_type_id: int,
        organization_id: int,
        project_id: int,
    ) -> bool:
        """Verifica si el usuario tiene permisos de escritura.

        Permisos de escritura:
        - Rol Admin (identity_type_id=2) o Editor (3) con asignación activa
        - NO Auditor (identity_type_id=4) ni Lector (identity_type_id=5)

        Args:
            user_id: ID del usuario
            identity_type_id: Tipo de identidad del usuario
            organization_id: ID de la organización
            project_id: ID del proyecto

        Returns:
            True si tiene permisos, False en caso contrario
        """
        # Auditor (4) y Lector (5): solo lectura
        if identity_type_id in (4, 5):
            return False

        # Si no hay engine configurado, permitir acceso (modo desarrollo)
        if self._db_engine is None:
            return True

        from sqlalchemy import text

        try:
            with self._db_engine.connect() as conn:
                # 1. Verificar asignación a organización con rol de escritura
                # Roles de escritura: 1 (SuperAdmin), 2 (Admin), 3 (Editor)
                result_org = conn.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM asignaciones_organizaciones_internas
                        WHERE id_usuario = :user_id
                          AND id_organizacion = :org_id
                          AND active = 1
                          AND id_rol IN (1, 2, 3)
                    """),
                    {"user_id": user_id, "org_id": organization_id},
                ).fetchone()

                if result_org and result_org.count > 0:
                    return True

                # 2. Verificar asignación a proyecto con rol de escritura
                # En proyectos_roles, los roles son del catálogo proyectos_roles_base
                # Necesitamos excluir roles de solo lectura (Auditor y Lector)
                result_prj = conn.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM proyectos_roles pr
                        INNER JOIN proyectos_roles_base prb
                            ON pr.id_rol = prb.id
                        WHERE pr.id_usuario = :user_id
                          AND pr.id_organizacion = :org_id
                          AND pr.id_proyecto = :project_id
                          AND pr.active = 1
                          AND prb.nombre_rol NOT IN ('Auditor', 'Lector')
                    """),
                    {
                        "user_id": user_id,
                        "org_id": organization_id,
                        "project_id": project_id,
                    },
                ).fetchone()

                if result_prj and result_prj.count > 0:
                    return True

                return False

        except Exception:
            # En caso de error de DB, denegar acceso por seguridad
            return False


# ============================================================================
# Excepciones del servicio
# ============================================================================


class ProjectVersionStateServiceError(Exception):
    """Excepción base para errores del servicio."""

    pass


class PermissionDeniedError(ProjectVersionStateServiceError):
    """Error cuando el usuario no tiene permisos."""

    pass


class NotFoundError(ProjectVersionStateServiceError):
    """Error cuando no se encuentra el recurso."""

    pass

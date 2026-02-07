"""Contrato de acceso a estados de versiones de proyectos para la capa de aplicación.

Este protocolo define la interfaz que debe implementar cualquier adaptador
de persistencia para gestionar estados de versiones de proyectos.
"""

from __future__ import annotations

from typing import Protocol


class ProjectVersionStateRepository(Protocol):
    """Contrato para acceder a estados de versiones desde cualquier fuente.

    NOTA: Usa strings para tipos (forward references) para evitar imports
    circulares con módulos numerados (1_shared_domain).

    Implementaciones esperadas:
    - MariaDBProjectVersionStateRepository (SQL)
    - JsonProjectVersionStateRepository (JSON para tests)
    """

    def get_by_id(self, state_id: int) -> "ProjectVersionState | None":
        """Obtiene un estado por su ID.

        Args:
            state_id: ID del registro en estado_version

        Returns:
            ProjectVersionState si existe, None si no se encuentra
        """
        ...

    def get_by_version(
        self,
        organization_id: int,
        project_id: int,
        version_id: int,
    ) -> "ProjectVersionState | None":
        """Obtiene el estado de una versión específica.

        Args:
            organization_id: ID de la organización
            project_id: ID del proyecto
            version_id: ID de la versión

        Returns:
            ProjectVersionState si existe, None si no se encuentra
        """
        ...

    def list_by_organization(
        self,
        organization_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> "tuple[ProjectVersionState, ...]":
        """Retorna estados de versiones de una organización.

        Args:
            organization_id: ID de la organización
            limit: Número máximo de resultados (default: 100)
            offset: Número de resultados a saltar (default: 0)

        Returns:
            Tupla de ProjectVersionState (puede estar vacía)
        """
        ...

    def list_by_project(
        self,
        organization_id: int,
        project_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> "tuple[ProjectVersionState, ...]":
        """Retorna estados de versiones de un proyecto.

        Args:
            organization_id: ID de la organización
            project_id: ID del proyecto
            limit: Número máximo de resultados (default: 100)
            offset: Número de resultados a saltar (default: 0)

        Returns:
            Tupla de ProjectVersionState (puede estar vacía)
        """
        ...

    def list_by_user_assignments(
        self,
        user_id: int,
        organization_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> "tuple[ProjectVersionState, ...]":
        """Retorna estados de versiones a las que el usuario tiene acceso.

        Filtra según asignaciones en:
        - asignaciones_organizaciones_internas (nivel organización)
        - proyectos_roles (nivel proyecto)

        Args:
            user_id: ID del usuario
            organization_id: ID de organización (opcional, para filtrar)
            limit: Número máximo de resultados (default: 100)
            offset: Número de resultados a saltar (default: 0)

        Returns:
            Tupla de ProjectVersionState (puede estar vacía)
        """
        ...

    def save(self, state: "ProjectVersionState") -> "ProjectVersionState":
        """Guarda o actualiza el estado de una versión.

        Args:
            state: Estado a guardar

        Returns:
            Estado guardado (con ID asignado si es nuevo)
        """
        ...

    def update_proposal_phase(
        self,
        state_id: int,
        aceptacion_cliente: bool,
        aceptacion_interna: bool,
        updated_by: int,
    ) -> bool:
        """Actualiza la fase de propuesta (aceptaciones).

        Args:
            state_id: ID del estado
            aceptacion_cliente: Estado de aceptación del cliente (final_c)
            aceptacion_interna: Estado de aceptación interna (final_i)
            updated_by: ID del usuario que hace la actualización

        Returns:
            True si se actualizó, False si no se encontró
        """
        ...

    def update_training_phase(
        self,
        state_id: int,
        completado: bool,
        updated_by: int,
    ) -> bool:
        """Actualiza la fase de entrenamiento.

        Args:
            state_id: ID del estado
            completado: Si el entrenamiento está completado
            updated_by: ID del usuario que hace la actualización

        Returns:
            True si se actualizó, False si no se encontró
        """
        ...

    def update_evaluation_phase(
        self,
        state_id: int,
        evaluacion: bool,
        reentrenamiento: bool,
        optimizacion: bool,
        calidad_aprobada: bool,
        updated_by: int,
    ) -> bool:
        """Actualiza la fase de evaluación/reentrenamiento.

        Args:
            state_id: ID del estado
            evaluacion: Si está en evaluación
            reentrenamiento: Si está en reentrenamiento
            optimizacion: Si está en optimización
            calidad_aprobada: Si pasó control de calidad
            updated_by: ID del usuario que hace la actualización

        Returns:
            True si se actualizó, False si no se encontró
        """
        ...

    def update_generation_phase(
        self,
        state_id: int,
        solicitada: bool,
        completada: bool,
        ruta_fichero: str | None,
        updated_by: int,
    ) -> bool:
        """Actualiza la fase de generación LLM.

        Args:
            state_id: ID del estado
            solicitada: Si la generación fue solicitada
            completada: Si la generación está completada
            ruta_fichero: Ruta del fichero generado (nullable)
            updated_by: ID del usuario que hace la actualización

        Returns:
            True si se actualizó, False si no se encontró
        """
        ...

    def update_notification_phase(
        self,
        state_id: int,
        enviada: bool,
        updated_by: int,
    ) -> bool:
        """Actualiza la fase de notificación.

        Args:
            state_id: ID del estado
            enviada: Si la notificación fue enviada
            updated_by: ID del usuario que hace la actualización

        Returns:
            True si se actualizó, False si no se encontró
        """
        ...

    def delete(self, state_id: int) -> bool:
        """Elimina un estado de versión (físicamente).

        ADVERTENCIA: Esta operación es irreversible.
        Solo usar si también se elimina la versión asociada.

        Args:
            state_id: ID del estado a eliminar

        Returns:
            True si se eliminó, False si no se encontró
        """
        ...

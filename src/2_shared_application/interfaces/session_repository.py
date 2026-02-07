"""Contrato de acceso a sesiones para la capa de aplicación."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class SessionRepository(Protocol):
    """Contrato para acceder a sesiones desde cualquier fuente.

    NOTA: Usa strings para tipos (forward references) para evitar imports
    circulares con módulos numerados (1_shared_domain).
    """

    def get_by_session_id(self, session_id: str) -> "Session | None":
        """Obtiene una sesión por su identificador."""

    def list_by_user_id(self, user_id: int) -> "tuple[Session, ...]":
        """Retorna las sesiones asociadas a un usuario."""

    def save(self, session: "Session") -> "Session":
        """Guarda la sesión y retorna la versión persistida."""

    def update_status(
        self, session_id: str, status: "SessionStatus", updated_at: datetime | None = None
    ) -> bool:
        """Actualiza el estado de una sesión."""

    def update_activity(self, session_id: str, last_activity: datetime) -> bool:
        """Actualiza la última actividad de una sesión."""

"""SessionRepository compuesto: combina un repositorio primario (backoffice,
JSON local) con uno secundario de solo respaldo (sesiones LAIM en MariaDB).

Contexto: las sesiones del backoffice de anewhope (login con OTP) se crean y
viven en JsonSessionRepository. Las sesiones LAIM (login vía backend_core →
laim_auth_service) viven en laim_core_db.laim_sessions (MariaDB), un store
totalmente distinto que middleware no escribe nunca. RouterMiddleware valida
ambos tipos de sesión con el mismo `_validate_tokens`, así que necesita
consultar los dos stores sin romper ninguno de los dos flujos existentes.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any


class CompositeSessionRepository:
    """Consulta `primary` primero y cae a `secondary` si no encuentra nada.

    `save()` siempre delega en `primary`: el secundario (LAIM/MariaDB) sólo
    lo escribe backend_core, middleware nunca crea sesiones LAIM. Los fallos
    del secundario (p.ej. credenciales de solo lectura) se registran y se
    ignoran para no romper la validación de sesiones del backoffice.

    `secondary_read_only=True` evita además intentar escribir en el
    secundario (update_status/update_activity): cuando ya se sabe que las
    credenciales son de solo lectura, intentarlo solo genera un
    UPDATE/denied garantizado en cada request autenticada.
    """

    def __init__(
        self,
        primary: Any,
        secondary: Any,
        secondary_read_only: bool = False,
    ) -> None:
        self._primary = primary
        self._secondary = secondary
        self._secondary_read_only = secondary_read_only
        self._logger = logging.getLogger("CompositeSessionRepository")

    def get_by_session_id(self, session_id: str) -> Any | None:
        session = self._primary.get_by_session_id(session_id)
        if session is not None:
            return session
        try:
            return self._secondary.get_by_session_id(session_id)
        except Exception as exc:
            self._logger.warning(
                "Repositorio secundario de sesiones falló en get_by_session_id "
                "session_id=%s: %s",
                session_id,
                exc,
            )
            return None

    def list_by_user_id(self, user_id: int) -> tuple[Any, ...]:
        primary_sessions = list(self._primary.list_by_user_id(user_id))
        seen_ids = {s.session_id for s in primary_sessions}
        try:
            secondary_sessions = self._secondary.list_by_user_id(user_id)
        except Exception as exc:
            self._logger.warning(
                "Repositorio secundario de sesiones falló en list_by_user_id "
                "user_id=%s: %s",
                user_id,
                exc,
            )
            secondary_sessions = ()
        for session in secondary_sessions:
            if session.session_id not in seen_ids:
                primary_sessions.append(session)
        return tuple(primary_sessions)

    def save(self, session: Any) -> Any:
        return self._primary.save(session)

    def update_status(
        self, session_id: str, status: Any, updated_at: datetime | None = None
    ) -> bool:
        if self._primary.update_status(session_id, status, updated_at):
            return True
        if self._secondary_read_only:
            return False
        try:
            return self._secondary.update_status(session_id, status, updated_at)
        except Exception as exc:
            self._logger.warning(
                "Repositorio secundario de sesiones falló en update_status "
                "session_id=%s: %s",
                session_id,
                exc,
            )
            return False

    def update_activity(self, session_id: str, last_activity: datetime) -> bool:
        if self._primary.update_activity(session_id, last_activity):
            return True
        if self._secondary_read_only:
            return False
        try:
            return self._secondary.update_activity(session_id, last_activity)
        except Exception as exc:
            self._logger.warning(
                "Repositorio secundario de sesiones falló en update_activity "
                "session_id=%s: %s",
                session_id,
                exc,
            )
            return False

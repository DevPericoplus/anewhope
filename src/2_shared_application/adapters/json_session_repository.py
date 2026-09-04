"""Implementación JSON del SessionRepository.

Este adaptador implementa el contrato SessionRepository usando
sessions.json como backend de persistencia.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


_SESSION_ENTITY_ALIASES = (
    "src.shared_domain.entities.session",
    "_session_entities_repo",
    "_session_entities_service",
    "_session_entities_jwt",
    "ddd_session_entities",
    "_laim_session_entities",
)


def _load_session_entities():
    """Carga entities/session.py una sola vez (evita clases Session duplicadas)."""
    for name in _SESSION_ENTITY_ALIASES:
        existing = sys.modules.get(name)
        if existing is not None and hasattr(existing, "Session"):
            for alias in _SESSION_ENTITY_ALIASES:
                sys.modules.setdefault(alias, existing)
            return existing

    module_path = (
        Path(__file__).resolve().parents[2] / "1_shared_domain/entities/session.py"
    )
    spec = importlib.util.spec_from_file_location(
        "src.shared_domain.entities.session", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar session entities")
    module = importlib.util.module_from_spec(spec)
    for alias in _SESSION_ENTITY_ALIASES:
        sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


_session_entities = _load_session_entities()
Session = _session_entities.Session
SessionStatus = _session_entities.SessionStatus
SessionTokenBinding = _session_entities.SessionTokenBinding


class JsonSessionRepository:
    """Implementación JSON del SessionRepository Protocol.

    Responsabilidades:
    - Leer/escribir sessions.json
    - Convertir entre JSON y entidades Session
    - Garantizar atomicidad de operaciones
    """

    def __init__(self, sessions_file_path: Path):
        """Inicializa el repositorio con la ruta al archivo JSON.

        Args:
            sessions_file_path: Ruta absoluta a sessions.json
        """
        self._sessions_file_path = sessions_file_path
        self._logger = logging.getLogger("JsonSessionRepository")

    def get_by_session_id(self, session_id: str) -> Session | None:
        """Obtiene una sesión por su identificador.

        Args:
            session_id: ID de la sesión

        Returns:
            Session si existe, None si no se encuentra
        """
        sessions_data = self._load_sessions_data()

        for record in sessions_data.get("sessions", []):
            if record.get("session_id") == session_id:
                return self._record_to_session(record)

        return None

    def list_by_user_id(self, user_id: int) -> tuple[Session, ...]:
        """Retorna las sesiones asociadas a un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Tupla de sesiones (puede estar vacía)
        """
        sessions_data = self._load_sessions_data()
        sessions = []

        for record in sessions_data.get("sessions", []):
            if record.get("user_id") == user_id:
                try:
                    session = self._record_to_session(record)
                    sessions.append(session)
                except Exception as exc:
                    self._logger.warning(
                        "Error al convertir sesión user_id=%s session_id=%s: %s",
                        user_id,
                        record.get("session_id"),
                        exc,
                    )

        return tuple(sessions)

    def save(self, session: Session) -> Session:
        """Guarda la sesión y retorna la versión persistida.

        Args:
            session: Sesión a guardar

        Returns:
            Sesión guardada (misma instancia)
        """
        sessions_data = self._load_sessions_data()

        # Buscar sesión existente
        existing_index = None
        for i, record in enumerate(sessions_data.get("sessions", [])):
            if record.get("session_id") == session.session_id:
                existing_index = i
                break

        # Convertir sesión a record
        new_record = self._session_to_record(session)

        # Actualizar o agregar
        if existing_index is not None:
            sessions_data["sessions"][existing_index] = new_record
            self._logger.info(
                "Sesión actualizada: session_id=%s user_id=%s",
                session.session_id,
                session.user_id,
            )
        else:
            if "sessions" not in sessions_data:
                sessions_data["sessions"] = []
            sessions_data["sessions"].append(new_record)
            self._logger.info(
                "Sesión creada: session_id=%s user_id=%s",
                session.session_id,
                session.user_id,
            )

        # Guardar atómicamente
        self._store_sessions_data(sessions_data)

        return session

    def update_status(
        self, session_id: str, status: SessionStatus, updated_at: datetime | None = None
    ) -> bool:
        """Actualiza el estado de una sesión.

        Args:
            session_id: ID de la sesión
            status: Nuevo estado
            updated_at: Timestamp de actualización (opcional)

        Returns:
            True si se actualizó, False si no se encontró
        """
        sessions_data = self._load_sessions_data()

        for record in sessions_data.get("sessions", []):
            if record.get("session_id") == session_id:
                record["status"] = status.value

                if updated_at:
                    record["last_activity"] = self._to_iso_utc(updated_at)

                self._store_sessions_data(sessions_data)

                self._logger.info(
                    "Estado de sesión actualizado: session_id=%s status=%s",
                    session_id,
                    status.value,
                )

                return True

        self._logger.warning(
            "Sesión no encontrada para actualizar estado: session_id=%s", session_id
        )
        return False

    def update_activity(self, session_id: str, last_activity: datetime) -> bool:
        """Actualiza la última actividad de una sesión.

        Args:
            session_id: ID de la sesión
            last_activity: Timestamp de última actividad

        Returns:
            True si se actualizó, False si no se encontró
        """
        sessions_data = self._load_sessions_data()

        for record in sessions_data.get("sessions", []):
            if record.get("session_id") == session_id:
                record["last_activity"] = self._to_iso_utc(last_activity)

                self._store_sessions_data(sessions_data)

                return True

        return False

    # ========================================================================
    # Helpers privados
    # ========================================================================

    def _load_sessions_data(self) -> dict[str, Any]:
        """Carga sessions.json desde el filesystem.

        Returns:
            Diccionario con estructura {"sessions": [...]}
        """
        if not self._sessions_file_path.exists():
            self._logger.warning(
                "sessions.json no existe, creando estructura vacía: %s",
                self._sessions_file_path,
            )
            return {"sessions": []}

        try:
            with open(self._sessions_file_path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {"sessions": []}
        except json.JSONDecodeError as exc:
            self._logger.error(
                "Error al decodificar sessions.json: %s. Retornando estructura vacía.",
                exc,
            )
            return {"sessions": []}
        except Exception as exc:
            self._logger.error(
                "Error inesperado al leer sessions.json: %s. Retornando estructura vacía.",
                exc,
            )
            return {"sessions": []}

    def _store_sessions_data(self, sessions_data: dict[str, Any]) -> None:
        """Guarda sessions.json al filesystem de forma atómica.

        Args:
            sessions_data: Diccionario con estructura {"sessions": [...]}
        """
        try:
            # Crear directorio si no existe
            self._sessions_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Escribir atómicamente (write + rename)
            temp_path = self._sessions_file_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(sessions_data, f, ensure_ascii=False, indent=2)

            temp_path.replace(self._sessions_file_path)

        except Exception as exc:
            self._logger.error("Error al guardar sessions.json: %s", exc)
            raise

    def _record_to_session(self, record: dict[str, Any]) -> Session:
        """Convierte un record JSON a entidad Session.

        Args:
            record: Diccionario con datos de sesión

        Returns:
            Entidad Session
        """
        tokens_dict = record.get("tokens", {})

        return Session(
            session_id=str(record.get("session_id", "")),
            user_id=int(record.get("user_id", 0)),
            organization_id=int(record.get("organization_id", 0)),
            identity_type_id=int(record.get("identity_type_id", 0)),
            tokens=SessionTokenBinding(
                access_token_jti=str(tokens_dict.get("access_token_jti", "")),
                session_token_jti=str(tokens_dict.get("session_token_jti", "")),
            ),
            status=SessionStatus(str(record.get("status", "inactive"))),
            created_at=self._parse_iso_utc(str(record.get("created_at", ""))),
            last_activity=self._parse_iso_utc(str(record.get("last_activity", ""))),
            expires_at=self._parse_iso_utc(str(record.get("expires_at", ""))),
            ip_address=str(record.get("ip_address", "")),
            user_agent=str(record.get("user_agent", "")),
        )

    def _session_to_record(self, session: Session) -> dict[str, Any]:
        """Convierte entidad Session a record JSON.

        Args:
            session: Entidad Session

        Returns:
            Diccionario con datos de sesión
        """
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "organization_id": session.organization_id,
            "identity_type_id": session.identity_type_id,
            "tokens": {
                "access_token_jti": session.tokens.access_token_jti,
                "session_token_jti": session.tokens.session_token_jti,
            },
            "status": session.status.value,
            "created_at": self._to_iso_utc(session.created_at),
            "last_activity": self._to_iso_utc(session.last_activity),
            "expires_at": self._to_iso_utc(session.expires_at),
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
        }

    def _parse_iso_utc(self, value: str) -> datetime:
        """Convierte un string ISO 8601 a datetime en UTC.

        Args:
            value: String con formato ISO 8601

        Returns:
            datetime en UTC
        """
        if not value:
            # Retornar epoch si vacío (para compatibilidad)
            from datetime import timezone
            return datetime.fromtimestamp(0, tz=timezone.utc)

        from datetime import timezone
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )

    def _to_iso_utc(self, value: datetime) -> str:
        """Convierte un datetime a ISO 8601 en UTC.

        Args:
            value: datetime a convertir

        Returns:
            String con formato ISO 8601
        """
        from datetime import timezone

        # Asegurar que tiene timezone
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

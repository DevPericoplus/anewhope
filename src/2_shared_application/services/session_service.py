"""Servicio de aplicación para gestión de sesiones.

Este servicio orquesta la lógica de negocio relacionada con sesiones,
coordinando JwtService (tokens) y SessionRepository (persistencia).
"""

from __future__ import annotations

import importlib.util
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

# Imports de tipo (TYPE_CHECKING) para interfaces
if TYPE_CHECKING:
    from ...interfaces.session_repository import SessionRepository


# Cargar módulos dinámicamente
def _load_session_entities():
    """Carga entities/session.py dinámicamente."""
    module_path = (
        Path(__file__).resolve().parents[2] / "1_shared_domain/entities/session.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_session_entities_service", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar session entities")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_session_entities_service"] = module
    spec.loader.exec_module(module)
    return module


def _load_jwt_service():
    """Carga jwt_service.py dinámicamente."""
    module_path = Path(__file__).resolve().parent / "jwt_service.py"
    spec = importlib.util.spec_from_file_location("_jwt_service_for_session", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar jwt_service")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_jwt_service_for_session"] = module
    spec.loader.exec_module(module)
    return module


def _load_session_repository():
    """Carga session_repository.py dinámicamente."""
    module_path = (
        Path(__file__).resolve().parents[1] / "interfaces/session_repository.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_session_repository_interface", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar session_repository")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_session_repository_interface"] = module
    spec.loader.exec_module(module)
    return module


_session_entities = _load_session_entities()
_jwt_service_module = _load_jwt_service()
_session_repository_module = _load_session_repository()

# Extraer clases de los módulos
DomainError = _session_entities.DomainError
Session = _session_entities.Session
SessionStatus = _session_entities.SessionStatus
SessionTokenBinding = _session_entities.SessionTokenBinding
TokenPair = _session_entities.TokenPair
UserSessionContext = _session_entities.UserSessionContext

JwtService = _jwt_service_module.JwtService
TokenExpiredError = _jwt_service_module.TokenExpiredError
TokenValidationError = _jwt_service_module.TokenValidationError

SessionRepository = _session_repository_module.SessionRepository


class SessionServiceError(Exception):
    """Error en operaciones del SessionService."""

    pass


class SessionNotFoundError(SessionServiceError):
    """La sesión no existe."""

    pass


class SessionExpiredError(SessionServiceError):
    """La sesión ha expirado."""

    pass


class InvalidTokenError(SessionServiceError):
    """Token inválido o expirado."""

    pass


@dataclass
class CreateSessionRequest:
    """Request para crear una sesión."""

    user_id: int
    organization_id: int
    identity_type_id: int
    ip_address: str = ""
    user_agent: str = ""


@dataclass
class SessionResponse:
    """Response con datos de sesión y tokens."""

    session: Session
    token_pair: TokenPair


class SessionService:
    """Servicio de aplicación para gestión de sesiones.

    Responsabilidades:
    - Crear sesiones con tokens JWT
    - Renovar access_token usando session_token
    - Invalidar sesiones (logout)
    - Obtener contexto de sesión para validación de permisos

    Este servicio coordina:
    - JwtService: Generación y validación de tokens
    - SessionRepository: Persistencia de sesiones
    """

    def __init__(
        self,
        jwt_service: JwtService,
        session_repository: SessionRepository,
    ):
        """Inicializa el servicio con sus dependencias.

        Args:
            jwt_service: Servicio para operaciones JWT
            session_repository: Repositorio para persistencia de sesiones
        """
        self._jwt_service = jwt_service
        self._session_repository = session_repository

    def create_session(
        self,
        request: CreateSessionRequest,
    ) -> SessionResponse:
        """Crea una nueva sesión con tokens JWT.

        Args:
            request: Datos para crear la sesión

        Returns:
            SessionResponse con sesión y tokens

        Raises:
            SessionServiceError: Si hay error al crear la sesión
        """
        try:
            # Generar session_id único
            session_id = str(uuid.uuid4())

            # Generar par de tokens usando JwtService
            token_pair = self._jwt_service.create_token_pair(
                session_id=session_id,
                user_id=request.user_id,
                organization_id=request.organization_id,
                identity_type_id=request.identity_type_id,
            )

            # Extraer JTIs de los tokens
            access_jti = self._jwt_service.extract_jti_without_validation(
                token_pair.access_token
            )
            session_jti = self._jwt_service.extract_jti_without_validation(
                token_pair.session_token
            )

            # Crear entidad Session
            now = datetime.now(timezone.utc)
            expires_at = datetime.fromtimestamp(
                token_pair.session_expires_at, tz=timezone.utc
            )

            session = Session(
                session_id=session_id,
                user_id=request.user_id,
                organization_id=request.organization_id,
                identity_type_id=request.identity_type_id,
                tokens=SessionTokenBinding(
                    access_token_jti=access_jti,
                    session_token_jti=session_jti,
                ),
                status=SessionStatus.ACTIVE,
                created_at=now,
                last_activity=now,
                expires_at=expires_at,
                ip_address=request.ip_address,
                user_agent=request.user_agent,
            )

            # Persistir sesión
            saved_session = self._session_repository.save(session)

            return SessionResponse(
                session=saved_session,
                token_pair=token_pair,
            )

        except DomainError as exc:
            raise SessionServiceError(
                f"Error de dominio al crear sesión: {exc}"
            ) from exc
        except Exception as exc:
            raise SessionServiceError(
                f"Error inesperado al crear sesión: {exc}"
            ) from exc

    def refresh_access_token(
        self,
        session_token: str,
    ) -> TokenPair:
        """Renueva el access_token usando un session_token válido.

        Args:
            session_token: Token de sesión válido

        Returns:
            Nuevo TokenPair con access_token renovado

        Raises:
            SessionNotFoundError: Si la sesión no existe
            SessionExpiredError: Si la sesión ha expirado
            InvalidTokenError: Si el token es inválido
        """
        try:
            # Validar session_token
            payload = self._jwt_service.validate_session_token(session_token)

            # Obtener sesión de la base de datos
            session = self._session_repository.get_by_session_id(payload.session_id)
            if not session:
                raise SessionNotFoundError(
                    f"Sesión {payload.session_id} no encontrada"
                )

            # Verificar que la sesión esté activa
            if not session.is_active():
                raise SessionExpiredError(
                    f"Sesión {payload.session_id} no está activa "
                    f"(status={session.status.value})"
                )

            # Verificar que el JTI del session_token coincida
            session_jti = self._jwt_service.extract_jti_without_validation(
                session_token
            )
            if session_jti != session.tokens.session_token_jti:
                raise InvalidTokenError(
                    "El JTI del session_token no coincide con el registrado"
                )

            # Generar nuevo par de tokens
            new_token_pair = self._jwt_service.create_token_pair(
                session_id=session.session_id,
                user_id=session.user_id,
                organization_id=session.organization_id,
                identity_type_id=session.identity_type_id,
            )

            # Extraer nuevos JTIs
            new_access_jti = self._jwt_service.extract_jti_without_validation(
                new_token_pair.access_token
            )
            new_session_jti = self._jwt_service.extract_jti_without_validation(
                new_token_pair.session_token
            )

            # Actualizar JTIs en la sesión
            session.update_tokens(new_access_jti, new_session_jti)

            # Actualizar última actividad
            now = datetime.now(timezone.utc)
            self._session_repository.update_activity(session.session_id, now)

            # Persistir cambios de tokens
            self._session_repository.save(session)

            return new_token_pair

        except TokenExpiredError as exc:
            raise SessionExpiredError(f"Token expirado: {exc}") from exc
        except TokenValidationError as exc:
            raise InvalidTokenError(f"Token inválido: {exc}") from exc
        except DomainError as exc:
            raise SessionServiceError(
                f"Error de dominio al renovar tokens: {exc}"
            ) from exc
        except (SessionNotFoundError, SessionExpiredError, InvalidTokenError):
            raise
        except Exception as exc:
            raise SessionServiceError(
                f"Error inesperado al renovar tokens: {exc}"
            ) from exc

    def invalidate_session(
        self,
        session_id: str,
        reason: str = "logout",
    ) -> bool:
        """Invalida una sesión (logout).

        Args:
            session_id: ID de la sesión a invalidar
            reason: Razón de invalidación (logout, expired, revoked)

        Returns:
            True si se invalidó correctamente

        Raises:
            SessionNotFoundError: Si la sesión no existe
        """
        try:
            # Obtener sesión
            session = self._session_repository.get_by_session_id(session_id)
            if not session:
                raise SessionNotFoundError(f"Sesión {session_id} no encontrada")

            # Marcar como inactiva según razón
            now = datetime.now(timezone.utc)
            if reason == "revoked":
                session.mark_revoked(now)
            elif reason == "expired":
                session.mark_expired(now)
            else:  # logout o cualquier otro
                session.mark_inactive(now)

            # Persistir cambios
            status_updated = self._session_repository.update_status(
                session_id=session.session_id,
                status=session.status,
                updated_at=now,
            )

            return status_updated

        except SessionNotFoundError:
            raise
        except Exception as exc:
            raise SessionServiceError(
                f"Error al invalidar sesión {session_id}: {exc}"
            ) from exc

    def get_session_context(
        self,
        access_token: str,
    ) -> UserSessionContext:
        """Obtiene el contexto de sesión para validación de permisos.

        Args:
            access_token: Token de acceso válido

        Returns:
            UserSessionContext con datos mínimos para permisos

        Raises:
            InvalidTokenError: Si el token es inválido
            SessionNotFoundError: Si la sesión no existe
            SessionExpiredError: Si la sesión no está activa
        """
        try:
            # Validar access_token
            payload = self._jwt_service.validate_access_token(access_token)

            # Obtener sesión
            session = self._session_repository.get_by_session_id(payload.session_id)
            if not session:
                raise SessionNotFoundError(
                    f"Sesión {payload.session_id} no encontrada"
                )

            # Verificar que la sesión esté activa
            if not session.is_active():
                raise SessionExpiredError(
                    f"Sesión {payload.session_id} no está activa"
                )

            # Retornar contexto
            return session.to_context()

        except TokenExpiredError as exc:
            raise SessionExpiredError(f"Token expirado: {exc}") from exc
        except TokenValidationError as exc:
            raise InvalidTokenError(f"Token inválido: {exc}") from exc
        except (SessionNotFoundError, SessionExpiredError):
            raise
        except Exception as exc:
            raise SessionServiceError(
                f"Error al obtener contexto de sesión: {exc}"
            ) from exc

    def validate_session(
        self,
        session_id: str,
        access_token_jti: str | None = None,
    ) -> bool:
        """Valida que una sesión exista y esté activa.

        Args:
            session_id: ID de la sesión
            access_token_jti: JTI del access_token (opcional, para validación adicional)

        Returns:
            True si la sesión es válida

        Raises:
            SessionNotFoundError: Si la sesión no existe
            SessionExpiredError: Si la sesión no está activa
        """
        try:
            session = self._session_repository.get_by_session_id(session_id)
            if not session:
                raise SessionNotFoundError(f"Sesión {session_id} no encontrada")

            if not session.is_active():
                raise SessionExpiredError(
                    f"Sesión {session_id} no está activa (status={session.status.value})"
                )

            # Validación adicional de JTI si se proporciona
            if access_token_jti:
                if access_token_jti != session.tokens.access_token_jti:
                    raise InvalidTokenError(
                        "El JTI del access_token no coincide con el registrado"
                    )

            return True

        except (SessionNotFoundError, SessionExpiredError, InvalidTokenError):
            raise
        except Exception as exc:
            raise SessionServiceError(
                f"Error al validar sesión {session_id}: {exc}"
            ) from exc

    def get_active_sessions_for_user(
        self,
        user_id: int,
    ) -> list[Session]:
        """Obtiene todas las sesiones activas de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de sesiones activas
        """
        try:
            all_sessions = self._session_repository.list_by_user_id(user_id)
            return [
                session for session in all_sessions
                if session.is_active()
            ]
        except Exception as exc:
            raise SessionServiceError(
                f"Error al obtener sesiones del usuario {user_id}: {exc}"
            ) from exc

    def invalidate_all_user_sessions(
        self,
        user_id: int,
        reason: str = "logout_all",
    ) -> int:
        """Invalida todas las sesiones de un usuario.

        Útil para logout global o cambio de contraseña.

        Args:
            user_id: ID del usuario
            reason: Razón de invalidación

        Returns:
            Número de sesiones invalidadas
        """
        try:
            sessions = self._session_repository.list_by_user_id(user_id)
            count = 0

            for session in sessions:
                if session.is_active():
                    self.invalidate_session(session.session_id, reason)
                    count += 1

            return count

        except Exception as exc:
            raise SessionServiceError(
                f"Error al invalidar sesiones del usuario {user_id}: {exc}"
            ) from exc

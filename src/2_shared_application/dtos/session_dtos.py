"""DTOs de sesión para intercambio de datos entre capas."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import importlib.util
import sys

from pydantic import BaseModel, ConfigDict, Field


def _load_session_models() -> Any:
    """Carga las entidades de sesión del dominio."""

    module_path = (
        Path(__file__).resolve().parents[2]
        / "1_shared_domain/entities/session.py"
    )
    module_name = "shared_domain_sessions"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar session.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_session_models = _load_session_models()
Session = _session_models.Session
SessionStatus = _session_models.SessionStatus
SessionTokenBinding = _session_models.SessionTokenBinding
UserSessionContext = _session_models.UserSessionContext


class SessionTokenBindingDto(BaseModel):
    """DTO para los JTIs asociados a la sesión."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    access_token_jti: str
    session_token_jti: str

    def to_domain(self) -> SessionTokenBinding:
        """Convierte el DTO a entidad de dominio."""

        return SessionTokenBinding(
            access_token_jti=self.access_token_jti,
            session_token_jti=self.session_token_jti,
        )

    @classmethod
    def from_domain(cls, tokens: SessionTokenBinding) -> SessionTokenBindingDto:
        """Crea un DTO desde la entidad de dominio."""

        return cls(
            access_token_jti=tokens.access_token_jti,
            session_token_jti=tokens.session_token_jti,
        )


class SessionDto(BaseModel):
    """DTO para Session."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    session_id: str
    user_id: int
    organization_id: int
    identity_type_id: int
    status: SessionStatus = Field(default=SessionStatus.INACTIVE)
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    access_token_jti: str
    session_token_jti: str
    ip_address: str = ""
    user_agent: str = ""

    def to_domain(self) -> Session:
        """Convierte el DTO a entidad de dominio."""

        return Session(
            session_id=self.session_id,
            user_id=self.user_id,
            organization_id=self.organization_id,
            identity_type_id=self.identity_type_id,
            tokens=SessionTokenBinding(
                access_token_jti=self.access_token_jti,
                session_token_jti=self.session_token_jti,
            ),
            status=self.status,
            created_at=self.created_at,
            last_activity=self.last_activity,
            expires_at=self.expires_at,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
        )

    @classmethod
    def from_domain(cls, session: Session) -> SessionDto:
        """Crea un DTO desde la entidad de dominio."""

        return cls(
            session_id=session.session_id,
            user_id=session.user_id,
            organization_id=session.organization_id,
            identity_type_id=session.identity_type_id,
            status=session.status,
            created_at=session.created_at,
            last_activity=session.last_activity,
            expires_at=session.expires_at,
            access_token_jti=session.tokens.access_token_jti,
            session_token_jti=session.tokens.session_token_jti,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
        )


class UserSessionContextDto(BaseModel):
    """DTO para el contexto mínimo de sesión."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    session_id: str
    user_id: int
    organization_id: int
    identity_type_id: int

    def to_domain(self) -> UserSessionContext:
        """Convierte el DTO a entidad de dominio."""

        return UserSessionContext(
            session_id=self.session_id,
            user_id=self.user_id,
            organization_id=self.organization_id,
            identity_type_id=self.identity_type_id,
        )

    @classmethod
    def from_domain(
        cls, context: UserSessionContext
    ) -> UserSessionContextDto:
        """Crea un DTO desde la entidad de dominio."""

        return cls(
            session_id=context.session_id,
            user_id=context.user_id,
            organization_id=context.organization_id,
            identity_type_id=context.identity_type_id,
        )

"""Entidades de dominio para sesiones y tokens."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
import importlib.util
import sys


def _load_domain_models() -> Any:
    """Carga domain_models sin import directo."""

    module_path = Path(__file__).resolve().parent / "domain_models.py"
    module_name = "shared_domain_models_session"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar domain_models.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_domain_models = _load_domain_models()
DomainError = _domain_models.DomainError


class SessionStatus(str, Enum):
    """Estados válidos de una sesión."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class SessionTokenBinding:
    """Vincula los JTIs de los tokens a una sesión."""

    access_token_jti: str
    session_token_jti: str

    def __post_init__(self) -> None:
        if not self.access_token_jti or not self.access_token_jti.strip():
            raise DomainError("access_token_jti no puede estar vacío")
        if not self.session_token_jti or not self.session_token_jti.strip():
            raise DomainError("session_token_jti no puede estar vacío")


@dataclass
class UserSessionContext:
    """Contexto mínimo de sesión para validar permisos."""

    session_id: str
    user_id: int
    organization_id: int
    identity_type_id: int


class TokenType(str, Enum):
    """Tipos de tokens JWT."""

    ACCESS = "access"
    SESSION = "session"


class JwtAlgorithm(str, Enum):
    """Algoritmos de firma JWT soportados."""

    HS256 = "HS256"
    HS384 = "HS384"
    HS512 = "HS512"
    RS256 = "RS256"
    RS384 = "RS384"
    RS512 = "RS512"


class Jti:
    """Value Object para JWT ID (JTI).

    Garantiza que el JTI tenga formato UUID válido.
    Inmutable por diseño (Value Object pattern).
    """

    def __init__(self, value: str):
        """Crea un JTI validando formato UUID.

        Args:
            value: String con formato UUID

        Raises:
            DomainError: Si el formato no es UUID válido
        """
        if not value or not value.strip():
            raise DomainError("JTI no puede estar vacío")

        if not self._is_valid_uuid(value.strip()):
            raise DomainError(f"JTI debe ser UUID válido, recibido: {value}")

        self._value = value.strip()

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        """Verifica si el string es un UUID válido."""
        try:
            import uuid
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False

    @property
    def value(self) -> str:
        """Retorna el valor del JTI."""
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"Jti({self._value})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Jti):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)


@dataclass(frozen=True)
class JwtPayload:
    """Value Object que representa los claims de un JWT.

    Inmutable (frozen=True) para garantizar consistencia.
    Contiene todos los claims estándar más los personalizados.
    """

    session_id: str
    user_id: int
    organization_id: int
    identity_type_id: int
    jti: str  # JWT ID único
    iat: int  # Issued At (Unix timestamp)
    exp: int  # Expiration (Unix timestamp)
    token_type: TokenType

    def __post_init__(self) -> None:
        """Valida invariantes del payload."""
        if not self.session_id or not self.session_id.strip():
            raise DomainError("session_id no puede estar vacío")

        if self.user_id <= 0:
            raise DomainError(f"user_id debe ser positivo, recibido: {self.user_id}")

        if self.organization_id <= 0:
            raise DomainError(
                f"organization_id debe ser positivo, recibido: {self.organization_id}"
            )

        if self.identity_type_id <= 0:
            raise DomainError(
                f"identity_type_id debe ser positivo, recibido: {self.identity_type_id}"
            )

        if not self.jti or not self.jti.strip():
            raise DomainError("jti no puede estar vacío")

        if self.iat <= 0:
            raise DomainError(f"iat debe ser positivo, recibido: {self.iat}")

        if self.exp <= 0:
            raise DomainError(f"exp debe ser positivo, recibido: {self.exp}")

        if self.exp <= self.iat:
            raise DomainError(
                f"exp ({self.exp}) debe ser mayor que iat ({self.iat})"
            )

    def is_expired(self, now: int | None = None) -> bool:
        """Verifica si el token está expirado.

        Args:
            now: Timestamp Unix actual (opcional, usa datetime.now si no se proporciona)

        Returns:
            True si el token ya expiró
        """
        if now is None:
            now = int(datetime.now(timezone.utc).timestamp())
        return now >= self.exp

    def seconds_until_expiration(self, now: int | None = None) -> int:
        """Retorna segundos hasta la expiración.

        Args:
            now: Timestamp Unix actual (opcional)

        Returns:
            Segundos restantes (0 si ya expiró)
        """
        if now is None:
            now = int(datetime.now(timezone.utc).timestamp())
        return max(0, self.exp - now)

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para codificar en JWT."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "identity_type_id": self.identity_type_id,
            "jti": self.jti,
            "iat": self.iat,
            "exp": self.exp,
            "type": self.token_type.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JwtPayload:
        """Crea JwtPayload desde diccionario.

        Args:
            data: Diccionario con claims del JWT

        Returns:
            Instancia de JwtPayload

        Raises:
            DomainError: Si faltan campos o tienen valores inválidos
        """
        try:
            return cls(
                session_id=str(data["session_id"]),
                user_id=int(data["user_id"]),
                organization_id=int(data["organization_id"]),
                identity_type_id=int(data["identity_type_id"]),
                jti=str(data["jti"]),
                iat=int(data["iat"]),
                exp=int(data["exp"]),
                token_type=TokenType(data.get("type", "access")),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise DomainError(f"Error al crear JwtPayload desde dict: {exc}") from exc


@dataclass(frozen=True)
class TokenPair:
    """Value Object que representa un par de tokens JWT.

    Contiene access_token y session_token con sus metadatos.
    Inmutable (frozen=True) para garantizar consistencia.
    """

    access_token: str
    session_token: str
    access_expires_at: int  # Unix timestamp
    session_expires_at: int  # Unix timestamp
    session_id: str
    user_id: int
    organization_id: int
    identity_type_id: int

    def __post_init__(self) -> None:
        """Valida invariantes del par de tokens."""
        if not self.access_token or not self.access_token.strip():
            raise DomainError("access_token no puede estar vacío")

        if not self.session_token or not self.session_token.strip():
            raise DomainError("session_token no puede estar vacío")

        if self.access_expires_at <= 0:
            raise DomainError(
                f"access_expires_at debe ser positivo, recibido: {self.access_expires_at}"
            )

        if self.session_expires_at <= 0:
            raise DomainError(
                f"session_expires_at debe ser positivo, recibido: {self.session_expires_at}"
            )

        if self.session_expires_at < self.access_expires_at:
            raise DomainError(
                "session_expires_at debe ser mayor o igual que access_expires_at"
            )

        if not self.session_id or not self.session_id.strip():
            raise DomainError("session_id no puede estar vacío")

        if self.user_id <= 0:
            raise DomainError(f"user_id debe ser positivo, recibido: {self.user_id}")

        if self.organization_id <= 0:
            raise DomainError(
                f"organization_id debe ser positivo, recibido: {self.organization_id}"
            )

    def is_access_expired(self, now: int | None = None) -> bool:
        """Verifica si el access_token está expirado."""
        if now is None:
            now = int(datetime.now(timezone.utc).timestamp())
        return now >= self.access_expires_at

    def is_session_expired(self, now: int | None = None) -> bool:
        """Verifica si el session_token está expirado."""
        if now is None:
            now = int(datetime.now(timezone.utc).timestamp())
        return now >= self.session_expires_at

    def needs_renewal(
        self, threshold_seconds: int = 180, now: int | None = None
    ) -> bool:
        """Verifica si el access_token necesita renovación.

        Args:
            threshold_seconds: Segundos antes de expiración para renovar (default: 3 min)
            now: Timestamp actual (opcional)

        Returns:
            True si el token expira en menos de threshold_seconds
        """
        if now is None:
            now = int(datetime.now(timezone.utc).timestamp())

        seconds_remaining = max(0, self.access_expires_at - now)
        return 0 < seconds_remaining < threshold_seconds

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "access_token": self.access_token,
            "session_token": self.session_token,
            "access_expires_at": self.access_expires_at,
            "session_expires_at": self.session_expires_at,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "identity_type_id": self.identity_type_id,
        }


@dataclass
class Session:
    """Entidad de dominio que representa una sesión de usuario."""

    session_id: str
    user_id: int
    organization_id: int
    identity_type_id: int
    tokens: SessionTokenBinding
    status: SessionStatus
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    ip_address: str = ""
    user_agent: str = ""

    def __post_init__(self) -> None:
        if not self.session_id or not self.session_id.strip():
            raise DomainError("session_id no puede estar vacío")
        if self.user_id <= 0:
            raise DomainError("user_id debe ser positivo")
        if self.organization_id <= 0:
            raise DomainError("organization_id debe ser positivo")
        if self.identity_type_id <= 0:
            raise DomainError("identity_type_id debe ser positivo")
        if not isinstance(self.status, SessionStatus):
            raise DomainError("status debe ser SessionStatus")

        self.created_at = _ensure_timezone(self.created_at)
        self.last_activity = _ensure_timezone(self.last_activity)
        self.expires_at = _ensure_timezone(self.expires_at)

    def is_expired(self, now: datetime | None = None) -> bool:
        """Indica si la sesión está expirada."""

        current = _ensure_timezone(now or datetime.now(timezone.utc))
        return current >= self.expires_at

    def is_active(self, now: datetime | None = None) -> bool:
        """Indica si la sesión está activa y vigente."""

        return self.status == SessionStatus.ACTIVE and not self.is_expired(now)

    def mark_inactive(self, at: datetime | None = None) -> None:
        """Marca la sesión como inactiva."""

        self.status = SessionStatus.INACTIVE
        self.last_activity = _ensure_timezone(at or datetime.now(timezone.utc))

    def mark_revoked(self, at: datetime | None = None) -> None:
        """Marca la sesión como revocada."""

        self.status = SessionStatus.REVOKED
        self.last_activity = _ensure_timezone(at or datetime.now(timezone.utc))

    def mark_expired(self, at: datetime | None = None) -> None:
        """Marca la sesión como expirada."""

        self.status = SessionStatus.EXPIRED
        self.last_activity = _ensure_timezone(at or datetime.now(timezone.utc))

    def update_tokens(self, access_token_jti: str, session_token_jti: str) -> None:
        """Actualiza los JTIs asociados a la sesión."""

        self.tokens = SessionTokenBinding(
            access_token_jti=access_token_jti,
            session_token_jti=session_token_jti,
        )

    def to_context(self) -> UserSessionContext:
        """Construye un contexto mínimo para validar permisos."""

        return UserSessionContext(
            session_id=self.session_id,
            user_id=self.user_id,
            organization_id=self.organization_id,
            identity_type_id=self.identity_type_id,
        )

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> Session:
        """Construye una sesión desde un registro genérico."""

        tokens = record.get("tokens") or {}
        return cls(
            session_id=str(record.get("session_id", "")).strip(),
            user_id=int(record.get("user_id", 0)),
            organization_id=int(record.get("organization_id", 0)),
            identity_type_id=int(record.get("identity_type_id", 0)),
            tokens=SessionTokenBinding(
                access_token_jti=str(tokens.get("access_token_jti", "")).strip(),
                session_token_jti=str(tokens.get("session_token_jti", "")).strip(),
            ),
            status=SessionStatus(str(record.get("status", "inactive"))),
            created_at=_parse_iso_utc(str(record.get("created_at", ""))),
            last_activity=_parse_iso_utc(str(record.get("last_activity", ""))),
            expires_at=_parse_iso_utc(str(record.get("expires_at", ""))),
            ip_address=str(record.get("ip_address", "")).strip(),
            user_agent=str(record.get("user_agent", "")).strip(),
        )

    def to_record(self) -> dict[str, Any]:
        """Convierte la sesión en un diccionario serializable."""

        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "identity_type_id": self.identity_type_id,
            "tokens": {
                "access_token_jti": self.tokens.access_token_jti,
                "session_token_jti": self.tokens.session_token_jti,
            },
            "status": self.status.value,
            "created_at": _to_iso_utc(self.created_at),
            "last_activity": _to_iso_utc(self.last_activity),
            "expires_at": _to_iso_utc(self.expires_at),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }


def _ensure_timezone(value: datetime) -> datetime:
    """Asegura que un datetime tenga zona horaria."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_iso_utc(value: str) -> datetime:
    """Convierte un string ISO 8601 a datetime en UTC."""

    if not value:
        raise DomainError("La fecha ISO no puede estar vacía")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def _to_iso_utc(value: datetime) -> str:
    """Convierte un datetime a ISO 8601 en UTC."""

    return _ensure_timezone(value).isoformat().replace("+00:00", "Z")

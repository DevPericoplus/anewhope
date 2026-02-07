"""Servicio de aplicación para gestión de tokens JWT.

Este servicio centraliza toda la lógica de generación, validación y
manipulación de tokens JWT siguiendo los principios de DDD.
"""

from __future__ import annotations

import importlib.util
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jwt


# Cargar módulo de dominio dinámicamente
def _load_session_entities():
    """Carga entities/session.py dinámicamente."""
    module_path = (
        Path(__file__).resolve().parents[2] / "1_shared_domain/entities/session.py"
    )
    spec = importlib.util.spec_from_file_location("_session_entities_jwt", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar session entities")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_session_entities_jwt"] = module
    spec.loader.exec_module(module)
    return module


_session_entities = _load_session_entities()
DomainError = _session_entities.DomainError
Jti = _session_entities.Jti
JwtAlgorithm = _session_entities.JwtAlgorithm
JwtPayload = _session_entities.JwtPayload
TokenPair = _session_entities.TokenPair
TokenType = _session_entities.TokenType


class JwtServiceError(Exception):
    """Error en operaciones del JwtService."""

    pass


class TokenValidationError(JwtServiceError):
    """Error al validar un token."""

    pass


class TokenExpiredError(TokenValidationError):
    """El token ha expirado."""

    pass


@dataclass
class JwtSettings:
    """Configuración para generación de tokens JWT."""

    # Secretos
    access_secret: str
    session_secret: str

    # TTLs (en segundos)
    access_ttl_seconds: int = 900  # 15 minutos
    session_ttl_seconds: int = 2700  # 45 minutos

    # Algoritmo
    algorithm: JwtAlgorithm = JwtAlgorithm.HS256

    def __post_init__(self) -> None:
        """Valida la configuración."""
        if not self.access_secret or not self.access_secret.strip():
            raise ValueError("access_secret no puede estar vacío")

        if not self.session_secret or not self.session_secret.strip():
            raise ValueError("session_secret no puede estar vacío")

        if self.access_ttl_seconds <= 0:
            raise ValueError("access_ttl_seconds debe ser positivo")

        if self.session_ttl_seconds <= 0:
            raise ValueError("session_ttl_seconds debe ser positivo")

        if self.session_ttl_seconds < self.access_ttl_seconds:
            raise ValueError(
                "session_ttl_seconds debe ser mayor o igual que access_ttl_seconds"
            )


class JwtService:
    """Servicio de aplicación para gestión de tokens JWT.

    Responsabilidades:
    - Generar tokens JWT (access y session)
    - Validar tokens JWT
    - Extraer claims de tokens
    - Verificar expiración

    Este servicio usa Value Objects del dominio (JwtPayload, TokenPair, Jti)
    y aplica las reglas de negocio relacionadas con JWT.
    """

    def __init__(self, settings: JwtSettings):
        """Inicializa el servicio con la configuración.

        Args:
            settings: Configuración de JWT (secretos, TTLs, algoritmo)
        """
        self._settings = settings

    def create_token_pair(
        self,
        session_id: str,
        user_id: int,
        organization_id: int,
        identity_type_id: int,
    ) -> TokenPair:
        """Crea un par completo de tokens (access + session).

        Args:
            session_id: ID único de la sesión
            user_id: ID del usuario
            organization_id: ID de la organización
            identity_type_id: ID del tipo de identidad (rol)

        Returns:
            TokenPair con ambos tokens y sus metadatos

        Raises:
            JwtServiceError: Si hay error al generar los tokens
        """
        try:
            now = int(time.time())
            access_exp = now + self._settings.access_ttl_seconds
            session_exp = now + self._settings.session_ttl_seconds

            # Generar access token
            access_token = self._generate_token(
                session_id=session_id,
                user_id=user_id,
                organization_id=organization_id,
                identity_type_id=identity_type_id,
                iat=now,
                exp=access_exp,
                token_type=TokenType.ACCESS,
                secret=self._settings.access_secret,
            )

            # Generar session token
            session_token = self._generate_token(
                session_id=session_id,
                user_id=user_id,
                organization_id=organization_id,
                identity_type_id=identity_type_id,
                iat=now,
                exp=session_exp,
                token_type=TokenType.SESSION,
                secret=self._settings.session_secret,
            )

            return TokenPair(
                access_token=access_token,
                session_token=session_token,
                access_expires_at=access_exp,
                session_expires_at=session_exp,
                session_id=session_id,
                user_id=user_id,
                organization_id=organization_id,
                identity_type_id=identity_type_id,
            )

        except DomainError as exc:
            raise JwtServiceError(f"Error de dominio al crear TokenPair: {exc}") from exc
        except Exception as exc:
            raise JwtServiceError(f"Error inesperado al crear tokens: {exc}") from exc

    def _generate_token(
        self,
        session_id: str,
        user_id: int,
        organization_id: int,
        identity_type_id: int,
        iat: int,
        exp: int,
        token_type: TokenType,
        secret: str,
    ) -> str:
        """Genera un token JWT individual.

        Args:
            session_id: ID de la sesión
            user_id: ID del usuario
            organization_id: ID de la organización
            identity_type_id: ID del tipo de identidad
            iat: Issued At timestamp
            exp: Expiration timestamp
            token_type: Tipo de token (ACCESS o SESSION)
            secret: Secreto para firma

        Returns:
            Token JWT codificado como string
        """
        # Generar JTI único
        jti = Jti(str(uuid.uuid4()))

        # Crear payload usando Value Object de dominio
        payload = JwtPayload(
            session_id=session_id,
            user_id=user_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
            jti=jti.value,
            iat=iat,
            exp=exp,
            token_type=token_type,
        )

        # Codificar JWT
        token = jwt.encode(
            payload.to_dict(),
            secret,
            algorithm=self._settings.algorithm.value,
        )

        return token

    def validate_access_token(self, token: str) -> JwtPayload:
        """Valida un access token y retorna su payload.

        Args:
            token: Token JWT a validar

        Returns:
            JwtPayload con los claims del token

        Raises:
            TokenExpiredError: Si el token expiró
            TokenValidationError: Si el token es inválido
        """
        return self._validate_token(
            token=token,
            secret=self._settings.access_secret,
            expected_type=TokenType.ACCESS,
        )

    def validate_session_token(self, token: str) -> JwtPayload:
        """Valida un session token y retorna su payload.

        Args:
            token: Token JWT a validar

        Returns:
            JwtPayload con los claims del token

        Raises:
            TokenExpiredError: Si el token expiró
            TokenValidationError: Si el token es inválido
        """
        return self._validate_token(
            token=token,
            secret=self._settings.session_secret,
            expected_type=TokenType.SESSION,
        )

    def _validate_token(
        self, token: str, secret: str, expected_type: TokenType
    ) -> JwtPayload:
        """Valida un token JWT genérico.

        Args:
            token: Token JWT a validar
            secret: Secreto para verificar firma
            expected_type: Tipo de token esperado

        Returns:
            JwtPayload con los claims

        Raises:
            TokenExpiredError: Si el token expiró
            TokenValidationError: Si el token es inválido
        """
        try:
            # Decodificar y verificar firma
            claims = jwt.decode(
                token,
                secret,
                algorithms=[self._settings.algorithm.value],
            )

            # Crear JwtPayload desde claims
            payload = JwtPayload.from_dict(claims)

            # Verificar tipo de token
            if payload.token_type != expected_type:
                raise TokenValidationError(
                    f"Token type mismatch: esperado {expected_type.value}, "
                    f"recibido {payload.token_type.value}"
                )

            # Verificar expiración
            if payload.is_expired():
                raise TokenExpiredError(
                    f"Token {expected_type.value} ha expirado "
                    f"(exp={payload.exp}, now={int(time.time())})"
                )

            return payload

        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError(f"Token {expected_type.value} expirado") from exc

        except jwt.InvalidTokenError as exc:
            raise TokenValidationError(
                f"Token {expected_type.value} inválido: {exc}"
            ) from exc

        except DomainError as exc:
            raise TokenValidationError(
                f"Claims inválidos en token {expected_type.value}: {exc}"
            ) from exc

        except Exception as exc:
            raise TokenValidationError(
                f"Error inesperado al validar token: {exc}"
            ) from exc

    def extract_jti_without_validation(self, token: str) -> str:
        """Extrae el JTI de un token SIN validar la firma.

        Útil cuando necesitas el JTI para buscar en una blacklist
        antes de hacer la validación completa.

        Args:
            token: Token JWT

        Returns:
            JTI como string

        Raises:
            TokenValidationError: Si el token no tiene formato válido
        """
        try:
            # Decodificar sin verificar firma
            claims = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=[self._settings.algorithm.value],
            )

            jti = claims.get("jti")
            if not jti:
                raise TokenValidationError("Token no contiene claim 'jti'")

            return str(jti)

        except Exception as exc:
            raise TokenValidationError(
                f"Error al extraer JTI del token: {exc}"
            ) from exc

    def extract_session_id_without_validation(self, token: str) -> str:
        """Extrae el session_id de un token SIN validar la firma.

        Args:
            token: Token JWT

        Returns:
            session_id como string

        Raises:
            TokenValidationError: Si el token no tiene formato válido
        """
        try:
            claims = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=[self._settings.algorithm.value],
            )

            session_id = claims.get("session_id")
            if not session_id:
                raise TokenValidationError("Token no contiene claim 'session_id'")

            return str(session_id)

        except Exception as exc:
            raise TokenValidationError(
                f"Error al extraer session_id del token: {exc}"
            ) from exc

    def decode_without_validation(self, token: str) -> dict[str, Any]:
        """Decodifica un token sin validar firma ni expiración.

        ADVERTENCIA: Solo para debugging/logging. NO usar para validación.

        Args:
            token: Token JWT

        Returns:
            Diccionario con todos los claims

        Raises:
            TokenValidationError: Si el token no tiene formato válido
        """
        try:
            claims = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
                algorithms=[self._settings.algorithm.value],
            )
            return dict(claims)

        except Exception as exc:
            raise TokenValidationError(
                f"Error al decodificar token: {exc}"
            ) from exc

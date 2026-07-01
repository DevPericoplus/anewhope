"""Servicio de autenticación LAIM (login, registro, sesiones JWT)."""

from __future__ import annotations

import importlib.util
import logging
import os
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


def _load_module(relative_path: str, module_name: str) -> Any:
    """Carga módulo desde ruta relativa al repo."""
    module_path = Path(__file__).resolve().parents[3] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_jwt_mod = _load_module(
    "src/2_shared_application/services/jwt_service.py", "laim_jwt_service"
)
_session_mod = _load_module(
    "src/2_shared_application/services/session_service.py", "laim_session_service"
)
_session_entities = _load_module(
    "src/1_shared_domain/entities/session.py", "laim_session_entities_svc"
)
_storage_adapter = _load_module(
    "src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py",
    "laim_storage_adapter",
)
_env_settings = _load_module(
    "src/2_shared_application/config/env_settings.py", "laim_env_settings_auth"
)

JwtService = _jwt_mod.JwtService
JwtSettings = _jwt_mod.JwtSettings
JwtAlgorithm = _session_entities.JwtAlgorithm
SessionService = _session_mod.SessionService
CreateSessionRequest = _session_mod.CreateSessionRequest
SessionExpiredError = _session_mod.SessionExpiredError
InvalidTokenError = _session_mod.InvalidTokenError
SessionStatus = _session_entities.SessionStatus
load_laim_mariadb_settings = _storage_adapter.load_laim_mariadb_settings

_laim_session_repo_mod = _load_module(
    "src/2_shared_application/adapters/laim_mariadb_session_repository.py",
    "laim_mariadb_session_repository_svc",
)
_laim_user_repo_mod = _load_module(
    "src/2_shared_application/adapters/laim_user_repository.py",
    "laim_user_repository_svc",
)
_laim_crypto_mod = _load_module(
    "src/2_shared_application/security/laim_password_crypto.py",
    "laim_password_crypto_svc",
)

LaimMariaDbSessionRepository = _laim_session_repo_mod.LaimMariaDbSessionRepository
create_laim_session_engine = _laim_session_repo_mod.create_laim_session_engine
LaimUserRepository = _laim_user_repo_mod.LaimUserRepository
decrypt_password = _laim_crypto_mod.decrypt_password
encrypt_password = _laim_crypto_mod.encrypt_password

MSG_INVALID_CREDENTIALS = "Usuario o credenciales inválidas"


class LaimAuthError(Exception):
    """Error de autenticación LAIM."""

    pass


@dataclass(frozen=True)
class LaimTokenResponse:
    """Respuesta de tokens LAIM."""

    success: bool
    user_id: int = 0
    user_name: str = ""
    organization_id: int = 0
    identity_type_id: int = 0
    access_token: str = ""
    session_token: str = ""
    access_expires_at: int = 0
    session_expires_at: int = 0
    session_id: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        payload = {
            "success": self.success,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "organization_id": self.organization_id,
            "identity_type_id": self.identity_type_id,
            "access_token": self.access_token,
            "session_token": self.session_token,
            "access_expires_at": self.access_expires_at,
            "session_expires_at": self.session_expires_at,
            "session_id": self.session_id,
        }
        if not self.success:
            payload["error"] = self.error
        return payload


class LaimAuthService:
    """Orquesta autenticación LAIM contra laim_core_db."""

    DEFAULT_ORG_NAME = "laim"
    DEFAULT_IDENTITY_TYPE_ID = 4
    MAX_FAILED_ATTEMPTS = 3

    def __init__(self) -> None:
        self._logger = logging.getLogger("LaimAuthService")
        settings = load_laim_mariadb_settings()
        engine = create_laim_session_engine(settings)
        self._user_repo = LaimUserRepository(engine)
        self._session_repo = LaimMariaDbSessionRepository(engine)
        self._session_service = SessionService(
            jwt_service=self._build_jwt_service(),
            session_repository=self._session_repo,
        )

    def _build_jwt_service(self) -> JwtService:
        """Construye JwtService con secretos dedicados LAIM."""
        protected = _env_settings.load_protected_settings() or {}
        access_secret = os.environ.get(
            "LAIM_JWT_ACCESS_SECRET",
            protected.get("laim_jwt_access_secret_key")
            or protected.get("jwt_access_secret_key", "laim-access-secret"),
        )
        session_secret = os.environ.get(
            "LAIM_JWT_SESSION_SECRET",
            protected.get("laim_jwt_session_secret_key")
            or protected.get("jwt_session_secret_key", "laim-session-secret"),
        )
        algorithm = os.environ.get(
            "LAIM_JWT_ALGORITHM",
            protected.get("laim_jwt_algorithm")
            or protected.get("jwt_algorithm", "HS256"),
        )
        access_ttl = int(
            os.environ.get(
                "LAIM_JWT_ACCESS_TTL_SECONDS",
                protected.get("laim_jwt_access_expiration_seconds")
                or protected.get("jwt_access_expiration_seconds", 900),
            )
        )
        session_ttl = int(
            os.environ.get(
                "LAIM_JWT_SESSION_TTL_SECONDS",
                protected.get("laim_jwt_session_expiration_seconds")
                or protected.get("jwt_session_expiration_seconds", 2700),
            )
        )
        return JwtService(
            JwtSettings(
                access_secret=str(access_secret),
                session_secret=str(session_secret),
                access_ttl_seconds=access_ttl,
                session_ttl_seconds=session_ttl,
                algorithm=JwtAlgorithm(str(algorithm)),
            )
        )

    def login(
        self,
        user_name: str,
        password: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> LaimTokenResponse:
        """Autentica usuario LAIM (sin OTP)."""
        user = self._user_repo.get_user_by_name(user_name.strip())
        if user is None:
            self._log_failure(user_name, "USER_NOT_FOUND", "Usuario no existe", ip_address, user_agent)
            return LaimTokenResponse(success=False, error=MSG_INVALID_CREDENTIALS)

        if not user.active or user.blocked:
            self._log_failure(user_name, "USER_BLOCKED", "Usuario bloqueado o inactivo", ip_address, user_agent)
            return LaimTokenResponse(success=False, error="El usuario no está habilitado")

        try:
            decrypted = decrypt_password(user.user_password)
        except ValueError:
            self._log_failure(user_name, "DECRYPT_ERROR", "Error al descifrar contraseña", ip_address, user_agent)
            return LaimTokenResponse(success=False, error=MSG_INVALID_CREDENTIALS)

        if decrypted != password:
            self._log_failure(user_name, "INVALID_PASSWORD", "Contraseña inválida", ip_address, user_agent)
            if (
                self._user_repo.count_recent_failed_attempts(user_name)
                >= self.MAX_FAILED_ATTEMPTS
            ):
                self._user_repo.set_user_blocked(user_name, blocked=True)
                self._user_repo.append_auth_log(
                    user_name=user_name,
                    event="login_blocked",
                    status="blocked",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "TOO_MANY_ATTEMPTS"},
                )
            return LaimTokenResponse(success=False, error=MSG_INVALID_CREDENTIALS)

        try:
            response = self._session_service.create_session(
                CreateSessionRequest(
                    user_id=user.user_id,
                    organization_id=user.organization_id,
                    identity_type_id=user.identity_type_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
        except Exception as exc:
            self._logger.error("Error creando sesión LAIM: %s", exc, exc_info=True)
            return LaimTokenResponse(success=False, error="No se pudo iniciar sesión")

        token_pair = response.token_pair
        self._user_repo.append_auth_log(
            user_name=user_name,
            event="login_success",
            status="success",
            ip_address=ip_address,
            session_id=response.session.session_id,
            user_agent=user_agent,
        )
        self._logger.info(
            "[laimweb] Login exitoso user_id=%s org_id=%s",
            user.user_id,
            user.organization_id,
        )
        return LaimTokenResponse(
            success=True,
            user_id=user.user_id,
            user_name=user.user_name,
            organization_id=user.organization_id,
            identity_type_id=user.identity_type_id,
            access_token=token_pair.access_token,
            session_token=token_pair.session_token,
            access_expires_at=token_pair.access_expires_at,
            session_expires_at=token_pair.session_expires_at,
            session_id=token_pair.session_id,
        )

    def refresh(self, session_token: str) -> LaimTokenResponse:
        """Renueva tokens LAIM."""
        try:
            token_pair = self._session_service.refresh_access_token(session_token)
        except SessionExpiredError:
            return LaimTokenResponse(success=False, error="Sesión expirada")
        except InvalidTokenError:
            return LaimTokenResponse(success=False, error="Token inválido")
        except Exception as exc:
            self._logger.error("Error renovando tokens LAIM: %s", exc, exc_info=True)
            return LaimTokenResponse(success=False, error="No se pudo renovar la sesión")

        return LaimTokenResponse(
            success=True,
            user_id=token_pair.user_id,
            organization_id=token_pair.organization_id,
            identity_type_id=token_pair.identity_type_id,
            access_token=token_pair.access_token,
            session_token=token_pair.session_token,
            access_expires_at=token_pair.access_expires_at,
            session_expires_at=token_pair.session_expires_at,
            session_id=token_pair.session_id,
        )

    def logout(self, session_token: str) -> dict[str, Any]:
        """Invalida sesión LAIM."""
        try:
            payload = self._session_service._jwt_service.validate_session_token(
                session_token
            )
            self._session_service.invalidate_session(
                payload.session_id, reason="logout"
            )
            return {"success": True}
        except Exception as exc:
            self._logger.warning("Logout LAIM fallido: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_session_permissions(self, identity_type_id: int) -> dict[str, Any]:
        """Obtiene permisos de bajo nivel para el rol."""
        permissions = self._user_repo.get_low_level_permissions(identity_type_id)
        return {"success": True, "permissions": permissions}

    def register(
        self,
        user_name: str,
        password: str,
        password_confirm: str,
        user_email: str,
        full_name: str,
        user_mobile: str | None = None,
        hcaptcha_token: str = "",
        ip_address: str = "",
        user_agent: str = "",
    ) -> dict[str, Any]:
        """Registro público de usuario LAIM (rol Lector)."""
        if password != password_confirm:
            return {"success": False, "error": "Las contraseñas no coinciden"}

        if len(password) < 8:
            return {"success": False, "error": "La contraseña debe tener al menos 8 caracteres"}

        if not self._verify_hcaptcha(hcaptcha_token, ip_address):
            return {"success": False, "error": "Verificación hCaptcha fallida"}

        org_id = self._user_repo.get_organization_id_by_name(self.DEFAULT_ORG_NAME)
        if org_id is None:
            return {"success": False, "error": "Organización LAIM no configurada"}

        if self._user_repo.user_exists(user_name.strip(), user_email):
            return {"success": False, "error": "Usuario o email ya registrados"}

        first_name, sur_name = self._split_full_name(full_name)
        encrypted_password = encrypt_password(password)
        user_id = self._user_repo.create_user(
            organization_id=org_id,
            identity_type_id=self.DEFAULT_IDENTITY_TYPE_ID,
            user_name=user_name.strip(),
            encrypted_password=encrypted_password,
            user_email=user_email,
            user_mobile=user_mobile,
            first_name=first_name,
            sur_name=sur_name,
        )
        self._user_repo.append_auth_log(
            user_name=user_name,
            event="login_success",
            status="success",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"action": "register", "user_id": user_id},
        )
        return {
            "success": True,
            "user_id": user_id,
            "message": "Registro completado. Ya puede iniciar sesión.",
        }

    def get_status(self) -> dict[str, Any]:
        """Estado básico del subsistema LAIM."""
        org_id = self._user_repo.get_organization_id_by_name(self.DEFAULT_ORG_NAME)
        return {
            "success": True,
            "service": "laim_auth",
            "organization_configured": org_id is not None,
            "organization_id": org_id,
        }

    def _log_failure(
        self,
        user_name: str,
        error_code: str,
        detail: str,
        ip_address: str,
        user_agent: str,
    ) -> None:
        """Registra intento fallido."""
        self._user_repo.append_auth_log(
            user_name=user_name,
            event="login_attempt",
            status="failed",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"error_code": error_code, "detail": detail},
        )

    def _split_full_name(self, full_name: str) -> tuple[str | None, str | None]:
        """Divide nombre completo en nombre y apellidos."""
        parts = full_name.strip().split()
        if not parts:
            return None, None
        if len(parts) == 1:
            return parts[0], None
        return parts[0], " ".join(parts[1:])

    def _verify_hcaptcha(self, token: str, remote_ip: str) -> bool:
        """Valida token hCaptcha (omitido si no hay secret configurado)."""
        protected = _env_settings.load_protected_settings() or {}
        secret = protected.get("laim_hcaptcha_secret") or protected.get("hcaptcha_secret")
        if not secret:
            self._logger.warning("hCaptcha secret no configurado — registro sin verificación")
            return True
        if not token:
            return False
        proxy_url = str(_env_settings.get_env_value("proxy_url", "") or "").strip()
        try:
            client_kwargs: dict[str, Any] = {"timeout": 10.0}
            if proxy_url:
                client_kwargs["proxy"] = proxy_url
            with httpx.Client(**client_kwargs) as client:
                response = client.post(
                    "https://hcaptcha.com/siteverify",
                    data={
                        "secret": secret,
                        "response": token,
                        "remoteip": remote_ip,
                    },
                )
            response.raise_for_status()
            payload = response.json()
            return bool(payload.get("success"))
        except httpx.HTTPError as exc:
            self._logger.error("Error verificando hCaptcha: %s", exc)
            return False

    def resolve_optional_session_context(
        self,
        access_token: str,
        session_token: str,
    ) -> dict[str, Any]:
        """Devuelve contexto de usuario si los tokens LAIM son válidos."""
        if not access_token.strip() or not session_token.strip():
            return {}

        try:
            access_payload = self._session_service._jwt_service.validate_access_token(
                access_token.strip()
            )
            session_payload = self._session_service._jwt_service.validate_session_token(
                session_token.strip()
            )
            if access_payload.session_id != session_payload.session_id:
                return {}

            context = self._session_service.get_session_context(access_token.strip())
            user = self._user_repo.get_user_by_id(context.user_id)
            return {
                "user_id": context.user_id,
                "user_name": user.user_name if user else "",
                "organization_id": context.organization_id,
            }
        except Exception as exc:
            self._logger.debug("Sesión LAIM opcional no válida en contacto: %s", exc)
            return {}

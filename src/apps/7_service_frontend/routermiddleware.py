"""Capa de orquestación con reglas de negocio y validaciones."""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import json
import logging
import os
import secrets
import sys
import time
import unicodedata
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .interfacetobackend import InterfaceToBackend
except ImportError:  # pragma: no cover - soporte para ejecuciones fuera de paquete
    from interfacetobackend import InterfaceToBackend


def _load_dto_module(module_name: str, filename: str) -> Any:
    """Carga un módulo de DTOs desde el paquete compartido."""

    module_path = (
        Path(__file__).resolve().parents[3]
        / "src/2_shared_application/dtos"
        / filename
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise BusinessRuleError(
            "No se pudo cargar el módulo de DTOs compartidos"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_domain_dtos = _load_dto_module("shared_domain_dtos", "domain_dtos.py")
_security_dtos = _load_dto_module("shared_security_dtos", "security_dtos.py")

OrganizationDto = _domain_dtos.OrganizationDto
UserDto = _domain_dtos.UserDto
RoleDto = _security_dtos.RoleDto
BasicPermissionDto = _security_dtos.BasicPermissionDto
ManageRoleByOrgDto = _security_dtos.ManageRoleByOrgDto


@dataclass(frozen=True)
class JwtSettings:
    """Configura los secretos y algoritmos JWT desde variables de entorno."""

    access_secret: str
    session_secret: str
    algorithm: str
    access_ttl_seconds: int
    session_ttl_seconds: int


def get_jwt_settings() -> JwtSettings:
    """Obtiene la configuración JWT desde el entorno."""

    protected = _load_protected_jwt_settings()
    return JwtSettings(
        access_secret=os.environ.get(
            "JWT_ACCESS_SECRET",
            protected.get("jwt_access_secret_key", "access-secret"),
        ),
        session_secret=os.environ.get(
            "JWT_SESSION_SECRET",
            protected.get("jwt_session_secret_key", "session-secret"),
        ),
        algorithm=os.environ.get(
            "JWT_ALGORITHM",
            protected.get("jwt_algorithm", "HS256"),
        ),
        access_ttl_seconds=int(
            os.environ.get(
                "JWT_ACCESS_TTL_SECONDS",
                protected.get("jwt_access_expiration_seconds", 900),
            )
        ),
        session_ttl_seconds=int(
            os.environ.get(
                "JWT_SESSION_TTL_SECONDS",
                protected.get("jwt_session_expiration_seconds", 2700),
            )
        ),
    )


class TokenValidationError(Exception):
    """Error de validación de token JWT."""


class TokenExpiredError(Exception):
    """Error de expiración de token JWT."""


class BusinessRuleError(Exception):
    """Error por incumplimiento de reglas de negocio."""


def _load_protected_jwt_settings() -> dict[str, str]:
    """Carga secretos JWT desde protected_values.py si existe."""

    try:
        from protected_values import (  # type: ignore
            jwt_access_secret_key,
            jwt_session_secret_key,
            jwt_algorithm,
            jwt_access_expiration_seconds,
            jwt_session_expiration_seconds,
        )

        return {
            "jwt_access_secret_key": jwt_access_secret_key,
            "jwt_session_secret_key": jwt_session_secret_key,
            "jwt_algorithm": jwt_algorithm,
            "jwt_access_expiration_seconds": jwt_access_expiration_seconds,
            "jwt_session_expiration_seconds": jwt_session_expiration_seconds,
        }
    except Exception:
        return {}


@dataclass(frozen=True)
class SessionContext:
    """Contexto de sesión validado."""

    user_id: int
    organization_id: int
    identity_type_id: int
    access_payload: dict[str, Any]
    session_payload: dict[str, Any]


@dataclass(frozen=True)
class TokenPair:
    """Par de tokens generados para la sesión."""

    user_id: int
    organization_id: int
    identity_type_id: int
    access_token: str
    session_token: str
    access_expires_at: int
    session_expires_at: int


@dataclass(frozen=True)
class UserCreationResult:
    """Resultado de creación de usuario."""

    user_id: int
    organization_id: int
    identity_type_id: int


def _base64url_decode(value: str) -> bytes:
    """Decodifica un valor base64url con padding automático."""

    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _base64url_encode(value: bytes) -> str:
    """Codifica bytes en base64url sin padding."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def _decode_jwt(token: str, secret: str, algorithm: str) -> dict[str, Any]:
    """Decodifica y valida un JWT con HMAC-SHA256."""

    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise TokenValidationError("Formato de token inválido") from exc

    header = json.loads(_base64url_decode(header_b64))
    payload = json.loads(_base64url_decode(payload_b64))

    if header.get("alg") != algorithm:
        raise TokenValidationError("Algoritmo de token no soportado")

    if algorithm != "HS256":
        raise TokenValidationError("Algoritmo de token no soportado")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).rstrip(b"=")
    if not hmac.compare_digest(expected_signature_b64, signature_b64.encode("utf-8")):
        raise TokenValidationError("Firma de token inválida")

    exp = payload.get("exp")
    if exp is None:
        raise TokenValidationError("El token no incluye expiración")
    if time.time() >= float(exp):
        raise TokenExpiredError("El token ha expirado")

    return payload


def _encode_jwt(payload: dict[str, Any], secret: str, algorithm: str) -> str:
    """Codifica un JWT con HMAC-SHA256."""

    if algorithm != "HS256":
        raise TokenValidationError("Algoritmo de token no soportado")

    header = {"alg": algorithm, "typ": "JWT"}
    header_b64 = _base64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    payload_b64 = _base64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    signature_b64 = _base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def _load_cipher_module(module_path: Path) -> Any:
    """Carga dinámicamente el módulo de cifrado."""

    spec = importlib.util.spec_from_file_location("custom_cipher_lib", module_path)
    if spec is None or spec.loader is None:
        raise BusinessRuleError("No se pudo cargar el módulo de cifrado")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RouterMiddleware:
    """Orquestador de reglas de negocio y validaciones."""

    def __init__(self, interface: InterfaceToBackend, jwt_settings: JwtSettings) -> None:
        self._interface = interface
        self._jwt_settings = jwt_settings
        self._logger = logging.getLogger("middlewarefe.router")

    def _validate_token_ttl(
        self, payload: dict[str, Any], max_ttl_seconds: int, token_label: str
    ) -> None:
        """Valida la caducidad esperada del token."""

        exp = payload.get("exp")
        if exp is None:
            raise TokenValidationError(
                f"El token de {token_label} no incluye expiración"
            )
        issued_at = payload.get("iat")
        now = time.time()
        if issued_at is not None:
            if float(exp) - float(issued_at) > max_ttl_seconds:
                raise TokenValidationError(
                    f"El token de {token_label} excede la caducidad permitida"
                )
        elif float(exp) - now > max_ttl_seconds:
            raise TokenValidationError(
                f"El token de {token_label} excede la caducidad permitida"
            )

    def _validate_tokens(self, access_token: str, session_token: str) -> SessionContext:
        """Valida la presencia y vigencia de los tokens JWT."""

        access_payload = _decode_jwt(
            access_token, self._jwt_settings.access_secret, self._jwt_settings.algorithm
        )
        session_payload = _decode_jwt(
            session_token, self._jwt_settings.session_secret, self._jwt_settings.algorithm
        )
        self._validate_token_ttl(
            access_payload, self._jwt_settings.access_ttl_seconds, "acceso"
        )
        self._validate_token_ttl(
            session_payload, self._jwt_settings.session_ttl_seconds, "sesión"
        )
        for label, payload in (
            ("acceso", access_payload),
            ("sesión", session_payload),
        ):
            if (
                "user_id" not in payload
                or "organization_id" not in payload
                or "identity_type_id" not in payload
            ):
                raise TokenValidationError(
                    f"El token de {label} no incluye user_id, organization_id e identity_type_id"
                )

        try:
            access_user_id = int(access_payload["user_id"])
            access_org_id = int(access_payload["organization_id"])
            access_identity_type_id = int(access_payload["identity_type_id"])
            session_user_id = int(session_payload["user_id"])
            session_org_id = int(session_payload["organization_id"])
            session_identity_type_id = int(session_payload["identity_type_id"])
        except (TypeError, ValueError) as exc:
            raise TokenValidationError(
                "Los identificadores del token no son válidos"
            ) from exc

        if (
            access_user_id != session_user_id
            or access_org_id != session_org_id
            or access_identity_type_id != session_identity_type_id
        ):
            raise TokenValidationError("Los tokens no corresponden a la misma sesión")

        return SessionContext(
            user_id=access_user_id,
            organization_id=access_org_id,
            identity_type_id=access_identity_type_id,
            access_payload=access_payload,
            session_payload=session_payload,
        )

    def validate_session(self, access_token: str, session_token: str) -> SessionContext:
        """Valida la sesión y retorna el contexto."""

        return self._validate_tokens(access_token, session_token)

    def issue_tokens(
        self, user_id: int, organization_id: int, identity_type_id: int
    ) -> TokenPair:
        """Genera los tokens de acceso y sesión."""

        now = int(time.time())
        access_exp = now + self._jwt_settings.access_ttl_seconds
        session_exp = now + self._jwt_settings.session_ttl_seconds
        access_payload = {
            "user_id": user_id,
            "organization_id": organization_id,
            "identity_type_id": identity_type_id,
            "iat": now,
            "exp": access_exp,
        }
        session_payload = {
            "user_id": user_id,
            "organization_id": organization_id,
            "identity_type_id": identity_type_id,
            "iat": now,
            "exp": session_exp,
        }
        access_token = _encode_jwt(
            access_payload, self._jwt_settings.access_secret, self._jwt_settings.algorithm
        )
        session_token = _encode_jwt(
            session_payload,
            self._jwt_settings.session_secret,
            self._jwt_settings.algorithm,
        )
        return TokenPair(
            user_id=user_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
            access_token=access_token,
            session_token=session_token,
            access_expires_at=access_exp,
            session_expires_at=session_exp,
        )

    def _load_users(self, data_path: Path) -> list[UserDto]:
        """Carga los usuarios desde archivo JSON."""

        try:
            with data_path.open("r", encoding="utf-8") as file_handle:
                records = json.load(file_handle)
        except FileNotFoundError as exc:
            raise BusinessRuleError("El archivo de usuarios no existe") from exc
        except json.JSONDecodeError as exc:
            raise BusinessRuleError("El archivo de usuarios no es válido") from exc
        return [UserDto.model_validate(record) for record in records]

    def _store_users(self, data_path: Path, users: list[UserDto]) -> None:
        """Guarda los usuarios en el archivo JSON."""

        with data_path.open("w", encoding="utf-8") as file_handle:
            payload = [user.model_dump() for user in users]
            json.dump(payload, file_handle, ensure_ascii=False, indent=2)

    def _get_users_file_path(self) -> Path:
        """Resuelve la ruta del archivo de usuarios."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "USERS_DATA_PATH",
                root_path / "src/2_shared_application/moks/users.json",
            )
        )

    def _get_security_key_path(self) -> Path:
        """Resuelve la ruta de la clave Fernet."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "FERNET_KEY_PATH",
                root_path / "src/2_shared_application/security/basesecuritypass.json",
            )
        )

    def _decrypt_password(self, encrypted_password: str) -> str:
        """Descifra la contraseña almacenada."""

        cipher_module = _load_cipher_module(
            self._get_security_key_path().parent / "custom_cipher_lib.py"
        )
        fernet_instance = cipher_module.load_fernet_key_from_file(
            self._get_security_key_path()
        )
        decrypted_bytes, _ = cipher_module.decrypt_value(
            fernet_instance, encrypted_password.encode("utf-8")
        )
        if not decrypted_bytes:
            raise BusinessRuleError("No se pudo descifrar la contraseña")
        return decrypted_bytes.decode("utf-8")

    def _rotate_otp(self, user: UserDto) -> str:
        """Genera y actualiza el OTP del usuario."""

        new_otp = f"{secrets.randbelow(10000):04d}"
        user.user_otp = new_otp
        return new_otp

    def authenticate_user(self, user_name: str, password: str, otp: str) -> TokenPair:
        """Valida credenciales, OTP y genera nuevos tokens."""

        users_path = self._get_users_file_path()
        users = self._load_users(users_path)
        user_record = next(
            (entry for entry in users if entry.user_name == user_name), None
        )
        if user_record is None:
            raise BusinessRuleError("Usuario o credenciales inválidas")
        if not user_record.active or user_record.blocked:
            raise BusinessRuleError("El usuario no está habilitado")

        decrypted_password = self._decrypt_password(
            str(user_record.user_password)
        )
        if decrypted_password != password:
            raise BusinessRuleError("Usuario o credenciales inválidas")

        if str(user_record.user_otp) != str(otp):
            raise BusinessRuleError("OTP inválido")

        self._logger.info(
            "Login exitoso user_id=%s org_id=%s",
            user_record.user_id,
            user_record.organization_id,
        )

        self._rotate_otp(user_record)
        self._store_users(users_path, users)

        return self.issue_tokens(
            int(user_record.user_id),
            int(user_record.organization_id),
            int(user_record.identity_type_id),
        )

    def refresh_tokens(self, session_token: str) -> TokenPair:
        """Renueva los tokens de la sesión vigente."""

        session_payload = _decode_jwt(
            session_token, self._jwt_settings.session_secret, self._jwt_settings.algorithm
        )
        self._validate_token_ttl(
            session_payload, self._jwt_settings.session_ttl_seconds, "sesión"
        )
        if (
            "user_id" not in session_payload
            or "organization_id" not in session_payload
            or "identity_type_id" not in session_payload
        ):
            raise TokenValidationError(
                "El token de sesión no incluye user_id, organization_id e identity_type_id"
            )
        try:
            user_id = int(session_payload["user_id"])
            organization_id = int(session_payload["organization_id"])
            identity_type_id = int(session_payload["identity_type_id"])
        except (TypeError, ValueError) as exc:
            raise TokenValidationError(
                "Los identificadores del token no son válidos"
            ) from exc

        self._logger.info(
            "Renovación de tokens user_id=%s org_id=%s", user_id, organization_id
        )
        return self.issue_tokens(user_id, organization_id, identity_type_id)

    def get_permissions(self, session: SessionContext) -> dict[str, Any]:
        """Obtiene los permisos asociados a la sesión."""

        users_path = self._get_users_file_path()
        users = self._load_users(users_path)
        user_record = next(
            (
                entry
                for entry in users
                if entry.user_id == session.user_id
                and entry.organization_id == session.organization_id
            ),
            None,
        )
        if user_record is None:
            raise BusinessRuleError("El usuario no existe en el sistema")

        self._logger.info(
            "Consulta de permisos user_id=%s org_id=%s",
            session.user_id,
            session.organization_id,
        )

        permissions = self._get_permissions_for_role(session.identity_type_id)
        return {
            "user_id": session.user_id,
            "organization_id": session.organization_id,
            "identity_type_id": session.identity_type_id,
            "permissions": permissions,
        }

    def _get_security_log_path(self) -> Path:
        """Resuelve la ruta del log de seguridad del middleware."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "SECURITY_LOG_PATH",
                root_path / "src/apps/7_service_frontend/logs/middleware_secure.log",
            )
        )

    def log_security_action(
        self, action: str, entity_id: int | None, ip: str, user_agent: str
    ) -> bool:
        """Registra una acción de seguridad en el log del middleware."""

        log_path = self._get_security_log_path()
        now = datetime.now().strftime("%Y-%m-%d-%H:%M")
        entity_id_str = str(entity_id) if entity_id is not None else ""
        log_line = f"{now},{ip},{user_agent},{action},{entity_id_str}\n"
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as file_handle:
                file_handle.write(log_line)
            return True
        except OSError as exc:
            self._logger.error(
                "Error al escribir log de seguridad en %s: %s", log_path, exc
            )
            return False

    def _normalize_text(self, text: str) -> str:
        """Normaliza texto eliminando acentos y convirtiendo a minúsculas."""

        normalized = unicodedata.normalize("NFD", text.strip().lower())
        return "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )

    def _get_organizations_file_path(self) -> Path:
        """Resuelve la ruta del archivo de organizaciones."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "ORGANIZATIONS_DATA_PATH",
                root_path / "src/2_shared_application/moks/organizations.json",
            )
        )

    def _load_organizations(self, data_path: Path) -> list[OrganizationDto]:
        """Carga las organizaciones desde archivo JSON."""

        try:
            with data_path.open("r", encoding="utf-8") as file_handle:
                records = json.load(file_handle)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as exc:
            raise BusinessRuleError("El archivo de organizaciones no es válido") from exc
        return [OrganizationDto.model_validate(record) for record in records]

    def _store_organizations(
        self, data_path: Path, organizations: list[OrganizationDto]
    ) -> None:
        """Guarda las organizaciones en el archivo JSON."""

        with data_path.open("w", encoding="utf-8") as file_handle:
            payload = [org.model_dump() for org in organizations]
            json.dump(payload, file_handle, ensure_ascii=False, indent=2)

    def check_organization_name_exists(self, organization_name: str) -> bool:
        """Verifica si existe una organización con el nombre dado."""

        organizations = self._load_organizations(self._get_organizations_file_path())
        if not organizations:
            return False
        normalized_input = self._normalize_text(organization_name)
        for org in organizations:
            org_name = str(org.organization_name)
            if self._normalize_text(org_name) == normalized_input:
                return True
        return False

    def create_organization(self, organization_data: dict[str, Any]) -> int:
        """Crea una organización y retorna el identificador asignado."""

        organization_name = organization_data.get("organization_name", "").strip()
        if self.check_organization_name_exists(organization_name):
            raise BusinessRuleError(
                "Esa organización ya existe en nuestro sistema, por favor contacte con su administrador."
            )

        organizations_path = self._get_organizations_file_path()
        organizations = self._load_organizations(organizations_path)
        existing_ids = [org.organization_id for org in organizations]
        next_id = max(existing_ids, default=0) + 1
        org_record = OrganizationDto(
            organization_id=next_id,
            organization_name=organization_data.get("organization_name", "").strip(),
            organization_email=organization_data.get("organization_email", "").strip(),
            organization_tlf=organization_data.get("organization_tlf", "").strip(),
            organization_address=organization_data.get("organization_address", "").strip(),
            organization_country=organization_data.get("organization_country", "").strip(),
            organization_state=organization_data.get("organization_state", "").strip(),
        )
        organizations.append(org_record)
        self._store_organizations(organizations_path, organizations)
        self._logger.info(
            "Organización creada org_id=%s nombre=%s",
            next_id,
            org_record.organization_name,
        )
        return next_id

    def _get_manage_roles_path(self) -> Path:
        """Resuelve la ruta del archivo de roles por organización."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "MANAGE_ROLES_BY_ORG_PATH",
                root_path / "src/2_shared_application/moks/manage_roles_by_org.json",
            )
        )

    def _get_roles_path(self) -> Path:
        """Resuelve la ruta del archivo de roles."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "ROLES_DATA_PATH",
                root_path / "src/2_shared_application/moks/roles.json",
            )
        )

    def _get_basic_permissions_path(self) -> Path:
        """Resuelve la ruta del archivo de permisos básicos."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "BASIC_PERMISSIONS_PATH",
                root_path / "src/2_shared_application/moks/basic_permissions.json",
            )
        )

    def _load_roles(self, data_path: Path) -> list[RoleDto]:
        """Carga los roles desde archivo JSON."""

        try:
            with data_path.open("r", encoding="utf-8") as file_handle:
                records = json.load(file_handle)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as exc:
            raise BusinessRuleError("El archivo de roles no es válido") from exc
        return [RoleDto.model_validate(record) for record in records]

    def _load_basic_permissions(self, data_path: Path) -> list[BasicPermissionDto]:
        """Carga los permisos básicos desde archivo JSON."""

        try:
            with data_path.open("r", encoding="utf-8") as file_handle:
                records = json.load(file_handle)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as exc:
            raise BusinessRuleError(
                "El archivo de permisos básicos no es válido"
            ) from exc
        return [BasicPermissionDto.model_validate(record) for record in records]

    def _get_permissions_for_role(self, identity_type_id: int) -> list[dict[str, Any]]:
        """Obtiene permisos básicos para un rol."""

        roles = self._load_roles(self._get_roles_path())
        role_entry = next(
            (
                role
                for role in roles
                if role.identity_type_id == identity_type_id
            ),
            None,
        )
        if role_entry is None:
            return []

        permission_ids = role_entry.identity_type_group_permissions
        permissions = self._load_basic_permissions(self._get_basic_permissions_path())
        return [
            permission.model_dump(by_alias=True)
            for permission in permissions
            if permission.id in permission_ids
        ]

    def _load_manage_roles(self, data_path: Path) -> list[ManageRoleByOrgDto]:
        """Carga la asignación de roles por organización."""

        try:
            with data_path.open("r", encoding="utf-8") as file_handle:
                records = json.load(file_handle)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as exc:
            raise BusinessRuleError(
                "El archivo de roles por organización no es válido"
            ) from exc
        return [ManageRoleByOrgDto.model_validate(record) for record in records]

    def _store_manage_roles(
        self, data_path: Path, entries: list[ManageRoleByOrgDto]
    ) -> None:
        """Guarda la asignación de roles por organización."""

        with data_path.open("w", encoding="utf-8") as file_handle:
            payload = [entry.model_dump() for entry in entries]
            json.dump(payload, file_handle, ensure_ascii=False, indent=2)

    def _get_manage_roles_identity_type_id(
        self, organization_id: int, requested_identity_type_id: int | None
    ) -> int:
        """Determina el rol a asignar para un usuario."""

        manage_roles_path = self._get_manage_roles_path()
        entries = self._load_manage_roles(manage_roles_path)
        is_first_user = not any(
            entry.id_organization == organization_id for entry in entries
        )
        if is_first_user:
            return 2
        if requested_identity_type_id is not None:
            return requested_identity_type_id
        return 2

    def _create_manage_role_entry(
        self, user_id: int, organization_id: int, identity_type_id: int
    ) -> None:
        """Crea el registro de rol por organización."""

        manage_roles_path = self._get_manage_roles_path()
        entries = self._load_manage_roles(manage_roles_path)
        now_str = datetime.now().strftime("%d/%m/%y-%H:%M")
        entries.append(
            ManageRoleByOrgDto(
                id_user=user_id,
                id_organization=organization_id,
                identity_type_id=identity_type_id,
                create_date=now_str,
                modification_date="",
                id_modifier_user=1,
                active=True,
            )
        )
        self._store_manage_roles(manage_roles_path, entries)

    def create_user(self, user_data: dict[str, Any]) -> UserCreationResult:
        """Crea un usuario y registra su rol por organización."""

        users_path = self._get_users_file_path()
        users = self._load_users(users_path)
        existing_ids = [user.user_id for user in users]
        next_id = max(existing_ids, default=0) + 1
        organization_id = int(user_data.get("organization_id", 1))
        requested_identity_type_id = user_data.get("identity_type_id")
        identity_type_id = self._get_manage_roles_identity_type_id(
            organization_id, requested_identity_type_id
        )

        user_record = UserDto(
            user_id=next_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
            user_name=str(user_data.get("user_name", "")).strip(),
            user_password=user_data.get("user_password", ""),
            user_email=str(user_data.get("user_email", "")).strip().lower(),
            user_mobile=str(user_data.get("user_mobile", "")).strip(),
            user_otp=user_data.get("user_otp", ""),
            active=bool(user_data.get("active", True)),
            blocked=bool(user_data.get("blocked", False)),
            contact_info=user_data.get("contact_info", {}),
            billing_info=user_data.get("billing_info", {}),
        )
        users.append(user_record)
        self._store_users(users_path, users)
        self._create_manage_role_entry(next_id, organization_id, identity_type_id)
        self._logger.info(
            "Usuario creado user_id=%s org_id=%s role_id=%s",
            next_id,
            organization_id,
            identity_type_id,
        )
        return UserCreationResult(
            user_id=next_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
        )

    async def process_data(
        self, payload: dict[str, Any], session: SessionContext
    ) -> dict[str, Any]:
        """Aplica reglas de negocio y llama al backend."""

        self._logger.info(
            "Inicio de procesamiento de datos user_id=%s org_id=%s",
            session.user_id,
            session.organization_id,
        )

        if not payload:
            raise BusinessRuleError("El payload no puede estar vacío")

        response = await self._interface.process_data(payload)
        self._logger.info(
            "Procesamiento completado user_id=%s org_id=%s",
            session.user_id,
            session.organization_id,
        )
        return response

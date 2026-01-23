"""Capa de orquestación con reglas de negocio y validaciones."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import importlib.util
import json
import logging
import os
import secrets
import uuid
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from .broker_backend_client import (
        BrokerBackendClient,
        BrokerBackendCommunicationError,
    )
    from .interfacetobackend import InterfaceToBackend
except ImportError:  # pragma: no cover - soporte para ejecuciones fuera de paquete
    from broker_backend_client import (
        BrokerBackendClient,
        BrokerBackendCommunicationError,
    )
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
LowLevelPermissionDto = _security_dtos.LowLevelPermissionDto
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


def _load_protected_storage_settings() -> dict[str, str]:
    """Carga la configuración de almacenamiento desde protected_values.py."""

    try:
        from protected_values import (  # type: ignore
            broker_backend_base_url,
            storage_mode,
            active_sync_db_jsons,
        )

        return {
            "broker_backend_base_url": broker_backend_base_url,
            "storage_mode": storage_mode,
            "active_sync_db_jsons": str(active_sync_db_jsons),
        }
    except Exception:
        return {}


class StorageMode(str, Enum):
    """Modos de persistencia de datos."""

    MOCK_ONLY = "mock"
    MOCK_AND_DB = "mock_and_db"
    DB_ONLY = "db_only"


def _parse_storage_mode(raw_value: str | None) -> StorageMode:
    """Normaliza el modo de almacenamiento."""

    normalized = (raw_value or "").strip().lower()
    if normalized == StorageMode.MOCK_AND_DB.value:
        return StorageMode.MOCK_AND_DB
    if normalized == StorageMode.DB_ONLY.value:
        return StorageMode.DB_ONLY
    return StorageMode.MOCK_ONLY


@dataclass(frozen=True)
class _SyncDataset:
    """Define un dataset para sincronización."""

    name: str
    json_path: Path
    key_fields: tuple[str, ...]
    fetch: Any


@dataclass(frozen=True)
class _SyncDiff:
    """Resultado de comparación entre broker y JSON."""

    added: list[tuple[Any, ...]]
    updated: list[tuple[Any, ...]]
    removed: list[tuple[Any, ...]]
    invalid_json: list[dict[str, Any]]

    @property
    def has_changes(self) -> bool:
        """Indica si hay cambios a aplicar."""

        return bool(self.added or self.updated or self.removed or self.invalid_json)


def _build_record_map(
    records: list[dict[str, Any]], key_fields: tuple[str, ...]
) -> tuple[dict[tuple[Any, ...], dict[str, Any]], list[dict[str, Any]]]:
    """Construye un mapa de registros por clave."""

    mapping: dict[tuple[Any, ...], dict[str, Any]] = {}
    invalid: list[dict[str, Any]] = []
    for record in records:
        key = tuple(record.get(field) for field in key_fields)
        if any(value is None for value in key):
            invalid.append(record)
            continue
        mapping[key] = record
    return mapping, invalid


def _record_signature(record: dict[str, Any]) -> str:
    """Genera una firma estable para comparar registros."""

    return json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)


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
    session_id: str | None = None


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


def _utc_now() -> datetime:
    """Obtiene la fecha actual en UTC."""

    return datetime.now(tz=timezone.utc)


def _to_iso_utc(value: datetime) -> str:
    """Convierte un datetime a ISO 8601 en UTC."""

    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso_utc(value: str) -> datetime:
    """Convierte un string ISO 8601 a datetime en UTC."""

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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


def _load_common_security_module(module_path: Path) -> Any:
    """Carga dinámicamente el módulo de seguridad compartida."""

    spec = importlib.util.spec_from_file_location("common_security", module_path)
    if spec is None or spec.loader is None:
        raise BusinessRuleError("No se pudo cargar el módulo de seguridad compartida")
    module = importlib.util.module_from_spec(spec)
    sys.modules["common_security"] = module
    spec.loader.exec_module(module)
    return module


class RouterMiddleware:
    """Orquestador de reglas de negocio y validaciones."""

    def __init__(
        self,
        interface: InterfaceToBackend,
        jwt_settings: JwtSettings,
        broker_client: BrokerBackendClient | None = None,
    ) -> None:
        self._interface = interface
        self._jwt_settings = jwt_settings
        self._logger = logging.getLogger("middlewarefe.router")
        self._sync_logger = self._build_sync_logger()
        self._storage_mode = self._get_storage_mode()
        self._broker_client = broker_client or BrokerBackendClient(
            base_url=self._get_broker_base_url()
        )

    def _get_storage_mode(self) -> StorageMode:
        """Obtiene el modo de almacenamiento configurado."""

        protected = _load_protected_storage_settings()
        raw_mode = os.environ.get("STORAGE_MODE", protected.get("storage_mode", "mock"))
        return _parse_storage_mode(raw_mode)

    def _get_broker_base_url(self) -> str:
        """Obtiene la URL base del broker backend."""

        protected = _load_protected_storage_settings()
        return os.environ.get(
            "BROKER_BACKEND_BASE_URL",
            protected.get("broker_backend_base_url", "http://localhost:8008"),
        )

    def _get_sync_log_path(self) -> Path:
        """Resuelve la ruta del log de sincronización."""

        root_path = Path(__file__).resolve().parents[3]
        return root_path / "src/apps/7_service_frontend/logs/sync_database_and_jsons.log"

    def _build_sync_logger(self) -> logging.Logger:
        """Configura el logger específico de sincronización."""

        logger = logging.getLogger("middlewarefe.sync")
        if any(
            isinstance(handler, logging.FileHandler)
            and Path(handler.baseFilename) == self._get_sync_log_path()
            for handler in logger.handlers
        ):
            return logger
        logger.setLevel(logging.INFO)
        log_path = self._get_sync_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _get_sync_interval_seconds(self) -> int:
        """Obtiene el intervalo de sincronización en segundos."""

        return int(os.environ.get("SYNC_DATABASE_INTERVAL_SECONDS", "300"))

    def _is_sync_enabled(self) -> bool:
        """Indica si la sincronización periódica está habilitada."""

        protected = _load_protected_storage_settings()
        raw_value = os.environ.get(
            "ACTIVE_SYNC_DB_JSONS", protected.get("active_sync_db_jsons", "1")
        )
        normalized = str(raw_value).strip().lower()
        return normalized in {"1", "true", "yes", "on"}

    def _should_use_broker_reads(self) -> bool:
        """Determina si se deben leer datos desde el broker."""

        return self._storage_mode == StorageMode.DB_ONLY

    def _should_replicate(self) -> bool:
        """Determina si se deben replicar datos en el broker."""

        return self._storage_mode == StorageMode.MOCK_AND_DB

    async def run_periodic_sync(self) -> None:
        """Ejecuta la sincronización periódica en segundo plano."""

        if self._storage_mode == StorageMode.MOCK_ONLY:
            self._sync_logger.info(
                "Sincronización deshabilitada (STORAGE_MODE=mock)."
            )
            return
        if not self._is_sync_enabled():
            self._sync_logger.info(
                "Sincronización deshabilitada (ACTIVE_SYNC_DB_JSONS=false)."
            )
            return
        interval = max(self._get_sync_interval_seconds(), 30)
        self._sync_logger.info(
            "Sincronización periódica iniciada intervalo=%s segundos", interval
        )
        try:
            while True:
                await asyncio.to_thread(self.sync_database_and_jsons)
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            self._sync_logger.info("Sincronización periódica detenida.")
            raise

    def sync_database_and_jsons(self) -> None:
        """Sincroniza las tablas del broker con los JSON locales."""

        if self._storage_mode == StorageMode.MOCK_ONLY:
            return
        if not self._is_sync_enabled():
            return
        datasets = [
            _SyncDataset(
                name="users",
                json_path=self._get_users_file_path(),
                key_fields=("user_id",),
                fetch=self._broker_client.fetch_users,
            ),
            _SyncDataset(
                name="organizations",
                json_path=self._get_organizations_file_path(),
                key_fields=("organization_id",),
                fetch=self._broker_client.fetch_organizations,
            ),
            _SyncDataset(
                name="roles",
                json_path=self._get_roles_path(),
                key_fields=("identity_type_id",),
                fetch=self._broker_client.fetch_roles,
            ),
            _SyncDataset(
                name="basic_permissions",
                json_path=self._get_basic_permissions_path(),
                key_fields=("id",),
                fetch=self._broker_client.fetch_basic_permissions,
            ),
            _SyncDataset(
                name="low_level_permissions",
                json_path=self._get_low_level_permissions_path(),
                key_fields=("id_permissions",),
                fetch=self._broker_client.fetch_low_level_permissions,
            ),
            _SyncDataset(
                name="manage_roles_by_org",
                json_path=self._get_manage_roles_path(),
                key_fields=("id_user", "id_organization"),
                fetch=self._broker_client.fetch_manage_roles,
            ),
        ]
        for dataset in datasets:
            self._sync_single_dataset(dataset)

    def _sync_single_dataset(self, dataset: "_SyncDataset") -> None:
        """Sincroniza un dataset específico con el broker."""

        try:
            broker_records = dataset.fetch()
        except BrokerBackendCommunicationError as exc:
            self._sync_logger.error(
                "Sincronización fallida dataset=%s error=%s", dataset.name, exc
            )
            return

        json_records = self._load_json_list(dataset.json_path)
        diff = self._diff_records(
            dataset.name, broker_records, json_records, dataset.key_fields
        )
        if diff.has_changes:
            self._sync_logger.info(
                "Sincronización dataset=%s añadidos=%s actualizados=%s eliminados=%s",
                dataset.name,
                diff.added,
                diff.updated,
                diff.removed,
            )
            if diff.invalid_json:
                self._sync_logger.warning(
                    "Registros JSON inválidos dataset=%s total=%s",
                    dataset.name,
                    len(diff.invalid_json),
                )
            self._sync_json_list(dataset.json_path, broker_records)
        else:
            self._sync_logger.info(
                "Sin cambios dataset=%s total=%s",
                dataset.name,
                len(broker_records),
            )

    def _load_json_list(self, data_path: Path) -> list[dict[str, Any]]:
        """Lee un JSON tipo lista desde disco."""

        if not data_path.exists():
            return []
        try:
            with data_path.open("r", encoding="utf-8") as file_handle:
                payload = json.load(file_handle)
        except json.JSONDecodeError as exc:
            self._sync_logger.error(
                "JSON inválido en %s: %s", data_path.name, exc
            )
            return []
        if not isinstance(payload, list):
            self._sync_logger.error(
                "JSON inesperado en %s, se esperaba lista", data_path.name
            )
            return []
        return [record for record in payload if isinstance(record, dict)]

    def _diff_records(
        self,
        dataset_name: str,
        broker_records: list[dict[str, Any]],
        json_records: list[dict[str, Any]],
        key_fields: tuple[str, ...],
    ) -> "_SyncDiff":
        """Calcula diferencias entre broker y JSON."""

        broker_map, invalid_broker = _build_record_map(broker_records, key_fields)
        json_map, invalid_json = _build_record_map(json_records, key_fields)
        if invalid_broker:
            self._sync_logger.warning(
                "Registros del broker sin clave dataset=%s total=%s",
                dataset_name,
                len(invalid_broker),
            )
        broker_keys = set(broker_map.keys())
        json_keys = set(json_map.keys())
        added = sorted(broker_keys - json_keys)
        removed = sorted(json_keys - broker_keys)
        updated = sorted(
            key
            for key in broker_keys & json_keys
            if _record_signature(broker_map[key])
            != _record_signature(json_map[key])
        )
        return _SyncDiff(
            added=added,
            updated=updated,
            removed=removed,
            invalid_json=invalid_json,
        )

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
                or "jti" not in payload
                or "session_id" not in payload
            ):
                raise TokenValidationError(
                    "El token de "
                    f"{label} no incluye user_id, organization_id, identity_type_id, jti o session_id"
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
        if access_payload["session_id"] != session_payload["session_id"]:
            raise TokenValidationError("Los tokens no corresponden a la misma sesión")

        sessions_path = self._get_sessions_file_path()
        sessions_data = self._load_sessions_data(sessions_path)
        session_record = self._find_session_record(
            sessions_data,
            access_payload["jti"],
            session_payload["jti"],
            access_user_id,
            access_payload["session_id"],
        )
        if session_record is None:
            raise TokenValidationError("La sesión no está registrada")

        status = session_record.get("status", "inactive")
        if status != "active":
            raise TokenValidationError("La sesión no está activa")

        expires_at = session_record.get("expires_at")
        if expires_at:
            if _utc_now() >= _parse_iso_utc(expires_at):
                session_record["status"] = "expired"
                self._store_sessions_data(sessions_path, sessions_data)
                raise TokenExpiredError("La sesión ha expirado")

        session_record["last_activity"] = _to_iso_utc(_utc_now())
        self._store_sessions_data(sessions_path, sessions_data)

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
        self,
        user_id: int,
        organization_id: int,
        identity_type_id: int,
        session_id: str | None = None,
        ip_address: str = "",
        user_agent: str = "",
    ) -> TokenPair:
        """Genera los tokens de acceso y sesión."""

        now = int(time.time())
        access_exp = now + self._jwt_settings.access_ttl_seconds
        session_exp = now + self._jwt_settings.session_ttl_seconds
        access_jti = str(uuid.uuid4())
        session_jti = str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())
        access_payload = {
            "user_id": user_id,
            "organization_id": organization_id,
            "identity_type_id": identity_type_id,
            "iat": now,
            "exp": access_exp,
            "jti": access_jti,
            "session_id": session_id,
        }
        session_payload = {
            "user_id": user_id,
            "organization_id": organization_id,
            "identity_type_id": identity_type_id,
            "iat": now,
            "exp": session_exp,
            "jti": session_jti,
            "session_id": session_id,
        }
        access_token = _encode_jwt(
            access_payload, self._jwt_settings.access_secret, self._jwt_settings.algorithm
        )
        session_token = _encode_jwt(
            session_payload,
            self._jwt_settings.session_secret,
            self._jwt_settings.algorithm,
        )
        sessions_path = self._get_sessions_file_path()
        sessions_data = self._load_sessions_data(sessions_path)
        self._upsert_session_record(
            sessions_data,
            session_id=session_id,
            user_id=user_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
            access_jti=access_jti,
            session_jti=session_jti,
            expires_at=_to_iso_utc(
                datetime.fromtimestamp(session_exp, tz=timezone.utc)
            ),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._store_sessions_data(sessions_path, sessions_data)
        return TokenPair(
            user_id=user_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
            access_token=access_token,
            session_token=session_token,
            access_expires_at=access_exp,
            session_expires_at=session_exp,
            session_id=session_id,
        )

    def _load_users(self, data_path: Path) -> list[UserDto]:
        """Carga los usuarios desde archivo JSON."""

        if self._should_use_broker_reads():
            try:
                records = self._broker_client.fetch_users()
            except BrokerBackendCommunicationError as exc:
                raise BusinessRuleError(
                    "No se pudo cargar usuarios desde el broker"
                ) from exc
            self._sync_users_cache(data_path, records)
            return [UserDto.model_validate(record) for record in records]
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

        payload = [user.model_dump() for user in users]
        if self._should_use_broker_reads() or self._should_replicate():
            try:
                self._broker_client.store_users(payload)
            except BrokerBackendCommunicationError as exc:
                raise BusinessRuleError(
                    "No se pudo guardar usuarios en el broker"
                ) from exc
        self._sync_users_cache(data_path, payload)

    def _sync_users_cache(
        self, data_path: Path, records: list[dict[str, Any]]
    ) -> None:
        """Sincroniza el cache local de usuarios con la fuente preferente."""

        self._sync_json_list(data_path, records)

    def _sync_json_list(
        self, data_path: Path, records: list[dict[str, Any]]
    ) -> None:
        """Sincroniza un JSON tipo lista con la fuente preferente."""

        try:
            data_path.parent.mkdir(parents=True, exist_ok=True)
            with data_path.open("w", encoding="utf-8") as file_handle:
                json.dump(records, file_handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            self._logger.error(
                "No se pudo sincronizar %s: %s", data_path.name, exc
            )

    def _get_users_file_path(self) -> Path:
        """Resuelve la ruta del archivo de usuarios."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "USERS_DATA_PATH",
                root_path / "src/2_shared_application/moks/users.json",
            )
        )

    def _get_sessions_file_path(self) -> Path:
        """Resuelve la ruta del archivo de sesiones."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "SESSIONS_DATA_PATH",
                root_path / "src/2_shared_application/moks/sessions.json",
            )
        )

    def _load_sessions_data(self, data_path: Path) -> dict[str, Any]:
        """Carga la estructura de sesiones y logs."""

        if not data_path.exists():
            return {"sessions": [], "auth_logs": []}
        try:
            with data_path.open("r", encoding="utf-8") as file_handle:
                payload = json.load(file_handle)
        except json.JSONDecodeError as exc:
            raise BusinessRuleError("El archivo de sesiones no es válido") from exc
        if not isinstance(payload, dict):
            raise BusinessRuleError("La estructura de sesiones no es válida")
        payload.setdefault("sessions", [])
        payload.setdefault("auth_logs", [])
        return payload

    def _store_sessions_data(self, data_path: Path, payload: dict[str, Any]) -> None:
        """Guarda la estructura de sesiones y logs."""

        data_path.parent.mkdir(parents=True, exist_ok=True)
        with data_path.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, ensure_ascii=False, indent=2)

    def _find_session_record(
        self,
        payload: dict[str, Any],
        access_jti: str,
        session_jti: str,
        user_id: int,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Busca una sesión por los JTIs y el usuario."""

        sessions = payload.get("sessions", [])
        for session in sessions:
            tokens = session.get("tokens", {})
            if (
                tokens.get("access_token_jti") == access_jti
                and tokens.get("session_token_jti") == session_jti
                and session.get("user_id") == user_id
                and session.get("session_id") == session_id
            ):
                return session
        return None

    def _upsert_session_record(
        self,
        payload: dict[str, Any],
        session_id: str,
        user_id: int,
        organization_id: int,
        identity_type_id: int,
        access_jti: str,
        session_jti: str,
        expires_at: str,
        ip_address: str,
        user_agent: str,
    ) -> None:
        """Crea o actualiza la sesión en memoria."""

        sessions = payload.get("sessions", [])
        now_iso = _to_iso_utc(_utc_now())
        for session in sessions:
            if session.get("session_id") == session_id:
                session["tokens"] = {
                    "access_token_jti": access_jti,
                    "session_token_jti": session_jti,
                }
                session["status"] = "active"
                session["last_activity"] = now_iso
                session["expires_at"] = expires_at
                session["ip_address"] = ip_address
                session["user_agent"] = user_agent
                return

        sessions.append(
            {
                "session_id": session_id,
                "user_id": user_id,
                "organization_id": organization_id,
                "identity_type_id": identity_type_id,
                "tokens": {
                    "access_token_jti": access_jti,
                    "session_token_jti": session_jti,
                },
                "status": "active",
                "created_at": now_iso,
                "last_activity": now_iso,
                "expires_at": expires_at,
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        )

    def _append_auth_log(
        self,
        payload: dict[str, Any],
        user_name: str,
        event: str,
        status: str,
        error_code: str | None = None,
        details: str | None = None,
        session_id: str | None = None,
        ip_address: str = "",
        user_agent: str = "",
    ) -> None:
        """Registra un evento de autenticación."""

        auth_logs = payload.get("auth_logs", [])
        record: dict[str, Any] = {
            "timestamp": _to_iso_utc(_utc_now()),
            "user_name": user_name,
            "event": event,
            "status": status,
            "ip_address": ip_address,
        }
        if error_code:
            record["error_code"] = error_code
        if details:
            record["details"] = details
        if session_id:
            record["session_id"] = session_id
        if user_agent:
            record["user_agent"] = user_agent
        auth_logs.append(record)
        max_records = 500
        if len(auth_logs) > max_records:
            auth_logs = auth_logs[-max_records:]
        payload["auth_logs"] = auth_logs

    def _count_recent_failed_attempts(
        self,
        payload: dict[str, Any],
        user_name: str,
        max_attempts: int = 3,
        window_minutes: int = 10,
        events: tuple[str, ...] = ("login_attempt",),
    ) -> int:
        """Cuenta intentos fallidos consecutivos para el usuario."""

        cutoff = _utc_now() - timedelta(minutes=window_minutes)
        failures = 0
        for record in reversed(payload.get("auth_logs", [])):
            if record.get("user_name") != user_name:
                continue
            timestamp = record.get("timestamp")
            if timestamp:
                try:
                    if _parse_iso_utc(timestamp) < cutoff:
                        break
                except ValueError:
                    break
            if record.get("event") == "login_success":
                break
            if record.get("event") in events and record.get("status") == "failed":
                failures += 1
                if failures >= max_attempts:
                    break
        return failures

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

    def _load_common_security(self) -> Any:
        """Carga el módulo common_security desde el paquete compartido."""

        common_security_path = (
            self._get_security_key_path().parent / "common_security.py"
        )
        return _load_common_security_module(common_security_path)

    def request_login_otp(
        self,
        user_name: str,
        password: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> bool:
        """Valida credenciales y envía el OTP por SMS."""

        users_path = self._get_users_file_path()
        users = self._load_users(users_path)
        sessions_path = self._get_sessions_file_path()
        sessions_data = self._load_sessions_data(sessions_path)
        user_record = next(
            (entry for entry in users if entry.user_name == user_name), None
        )
        if user_record is None:
            self._append_auth_log(
                sessions_data,
                user_name=user_name,
                event="otp_request",
                status="failed",
                error_code="USER_NOT_FOUND",
                details="Usuario no existe",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self._store_sessions_data(sessions_path, sessions_data)
            raise BusinessRuleError("Usuario o credenciales inválidas")
        if not user_record.active or user_record.blocked:
            self._append_auth_log(
                sessions_data,
                user_name=user_name,
                event="otp_request",
                status="failed",
                error_code="USER_BLOCKED",
                details="Usuario bloqueado o inactivo",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self._store_sessions_data(sessions_path, sessions_data)
            raise BusinessRuleError("El usuario no está habilitado")

        decrypted_password = self._decrypt_password(
            str(user_record.user_password)
        )
        if decrypted_password != password:
            self._append_auth_log(
                sessions_data,
                user_name=user_name,
                event="otp_request",
                status="failed",
                error_code="INVALID_PASSWORD",
                details="Contraseña inválida",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if (
                self._count_recent_failed_attempts(
                    sessions_data,
                    user_name,
                    events=("login_attempt", "otp_request"),
                )
                >= 3
            ):
                user_record.blocked = True
                self._append_auth_log(
                    sessions_data,
                    user_name=user_name,
                    event="login_blocked",
                    status="blocked",
                    error_code="TOO_MANY_ATTEMPTS",
                    details="Usuario bloqueado por intentos fallidos",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                self._store_users(users_path, users)
            self._store_sessions_data(sessions_path, sessions_data)
            raise BusinessRuleError("Usuario o credenciales inválidas")

        user_otp = str(user_record.user_otp)
        if len(user_otp) != 4 or not user_otp.isdigit():
            self._append_auth_log(
                sessions_data,
                user_name=user_name,
                event="otp_request",
                status="failed",
                error_code="INVALID_OTP",
                details="OTP inválido",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self._store_sessions_data(sessions_path, sessions_data)
            raise BusinessRuleError("OTP inválido")

        if not user_record.user_mobile:
            self._append_auth_log(
                sessions_data,
                user_name=user_name,
                event="otp_request",
                status="failed",
                error_code="MOBILE_NOT_FOUND",
                details="Número móvil no disponible",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self._store_sessions_data(sessions_path, sessions_data)
            raise BusinessRuleError("No hay teléfono asociado al usuario")

        common_security = self._load_common_security()
        send_sms = getattr(common_security, "send_message_by_sms", None)
        if send_sms is None:
            self._append_auth_log(
                sessions_data,
                user_name=user_name,
                event="otp_request",
                status="failed",
                error_code="SMS_MODULE_MISSING",
                details="Función de envío de SMS no disponible",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self._store_sessions_data(sessions_path, sessions_data)
            raise BusinessRuleError("No se pudo enviar el OTP")

        sms_sent = bool(send_sms(user_otp, str(user_record.user_mobile).strip()))
        self._append_auth_log(
            sessions_data,
            user_name=user_name,
            event="otp_request",
            status="success" if sms_sent else "failed",
            error_code=None if sms_sent else "SMS_FAILED",
            details="OTP enviado por SMS" if sms_sent else "Fallo al enviar SMS",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._store_sessions_data(sessions_path, sessions_data)
        if not sms_sent:
            raise BusinessRuleError("No se pudo enviar el OTP")
        return True

    def authenticate_user(
        self,
        user_name: str,
        password: str,
        otp: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> TokenPair:
        """Valida credenciales, OTP y genera nuevos tokens."""

        users_path = self._get_users_file_path()
        users = self._load_users(users_path)
        sessions_path = self._get_sessions_file_path()
        sessions_data = self._load_sessions_data(sessions_path)
        user_record = next(
            (entry for entry in users if entry.user_name == user_name), None
        )
        if user_record is None:
            self._append_auth_log(
                sessions_data,
                user_name=user_name,
                event="login_attempt",
                status="failed",
                error_code="USER_NOT_FOUND",
                details="Usuario no existe",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self._store_sessions_data(sessions_path, sessions_data)
            raise BusinessRuleError("Usuario o credenciales inválidas")
        if not user_record.active or user_record.blocked:
            self._append_auth_log(
                sessions_data,
                user_name=user_name,
                event="login_attempt",
                status="failed",
                error_code="USER_BLOCKED",
                details="Usuario bloqueado o inactivo",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self._store_sessions_data(sessions_path, sessions_data)
            raise BusinessRuleError("El usuario no está habilitado")

        decrypted_password = self._decrypt_password(
            str(user_record.user_password)
        )
        if decrypted_password != password:
            self._append_auth_log(
                sessions_data,
                user_name=user_name,
                event="login_attempt",
                status="failed",
                error_code="INVALID_PASSWORD",
                details="Contraseña inválida",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if self._count_recent_failed_attempts(sessions_data, user_name) >= 3:
                user_record.blocked = True
                self._append_auth_log(
                    sessions_data,
                    user_name=user_name,
                    event="login_blocked",
                    status="blocked",
                    error_code="TOO_MANY_ATTEMPTS",
                    details="Usuario bloqueado por intentos fallidos",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                self._store_users(users_path, users)
            self._store_sessions_data(sessions_path, sessions_data)
            raise BusinessRuleError("Usuario o credenciales inválidas")

        if str(user_record.user_otp) != str(otp):
            self._append_auth_log(
                sessions_data,
                user_name=user_name,
                event="login_attempt",
                status="failed",
                error_code="INVALID_OTP",
                details="OTP inválido",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if self._count_recent_failed_attempts(sessions_data, user_name) >= 3:
                user_record.blocked = True
                self._append_auth_log(
                    sessions_data,
                    user_name=user_name,
                    event="login_blocked",
                    status="blocked",
                    error_code="TOO_MANY_ATTEMPTS",
                    details="Usuario bloqueado por intentos fallidos",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                self._store_users(users_path, users)
            self._store_sessions_data(sessions_path, sessions_data)
            raise BusinessRuleError("OTP inválido")

        self._logger.info(
            "Login exitoso user_id=%s org_id=%s",
            user_record.user_id,
            user_record.organization_id,
        )

        self._rotate_otp(user_record)
        self._store_users(users_path, users)

        tokens = self.issue_tokens(
            int(user_record.user_id),
            int(user_record.organization_id),
            int(user_record.identity_type_id),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        sessions_data = self._load_sessions_data(sessions_path)
        self._append_auth_log(
            sessions_data,
            user_name=user_name,
            event="login_success",
            status="success",
            session_id=tokens.session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._store_sessions_data(sessions_path, sessions_data)
        return tokens

    def refresh_tokens(
        self, session_token: str, ip_address: str = "", user_agent: str = ""
    ) -> TokenPair:
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

        session_jti = session_payload.get("jti")
        session_id = session_payload.get("session_id")
        if session_jti is None or session_id is None:
            raise TokenValidationError(
                "El token de sesión no incluye jti o session_id"
            )

        sessions_path = self._get_sessions_file_path()
        sessions_data = self._load_sessions_data(sessions_path)
        session_record = None
        for session in sessions_data.get("sessions", []):
            tokens = session.get("tokens", {})
            if (
                tokens.get("session_token_jti") == session_jti
                and session.get("user_id") == user_id
                and session.get("session_id") == session_id
            ):
                session_record = session
                break
        if session_record is None:
            raise TokenValidationError("La sesión no está registrada")
        if session_record.get("status") != "active":
            raise TokenValidationError("La sesión no está activa")

        self._logger.info(
            "Renovación de tokens user_id=%s org_id=%s", user_id, organization_id
        )
        tokens = self.issue_tokens(
            user_id,
            organization_id,
            identity_type_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._store_sessions_data(sessions_path, sessions_data)
        return tokens

    def logout_session(
        self,
        session: SessionContext,
        ip_address: str = "",
        user_agent: str = "",
    ) -> bool:
        """Cierra la sesión activa del usuario."""

        session_id = session.access_payload.get("session_id")
        if not session_id:
            raise BusinessRuleError("No se pudo resolver la sesión")
        sessions_path = self._get_sessions_file_path()
        sessions_data = self._load_sessions_data(sessions_path)
        users = self._load_users(self._get_users_file_path())
        user_name = next(
            (user.user_name for user in users if user.user_id == session.user_id),
            str(session.user_id),
        )
        session_record = None
        for record in sessions_data.get("sessions", []):
            if record.get("session_id") == session_id:
                session_record = record
                break
        if session_record is None:
            raise BusinessRuleError("La sesión no está registrada")
        session_record["status"] = "inactive"
        session_record["last_activity"] = _to_iso_utc(_utc_now())
        self._append_auth_log(
            sessions_data,
            user_name=user_name,
            event="logout",
            status="success",
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._store_sessions_data(sessions_path, sessions_data)
        return True

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
        low_level_permissions = self._get_low_level_permissions_for_role(
            session.identity_type_id
        )
        return {
            "user_id": session.user_id,
            "organization_id": session.organization_id,
            "identity_type_id": session.identity_type_id,
            "permissions": permissions,
            "low_level_permissions": low_level_permissions,
        }

    def has_low_level_permission(
        self, session: SessionContext, permission_key: str
    ) -> bool:
        """Valida un permiso de bajo nivel usando el contexto de sesión."""

        if not permission_key:
            return False
        permissions = self._get_low_level_permissions_for_role(
            session.identity_type_id
        )
        value = permissions.get(permission_key)
        allowed = bool(value)
        self._logger.info(
            "Permiso bajo nivel user_id=%s org_id=%s role_id=%s key=%s allowed=%s",
            session.user_id,
            session.organization_id,
            session.identity_type_id,
            permission_key,
            allowed,
        )
        return allowed

    def can_rename_folder(self, session: SessionContext) -> bool:
        """Valida si puede renombrar carpetas según permisos de bajo nivel."""

        return self.has_low_level_permission(session, "folder_rename")

    def _get_security_log_path(self) -> Path:
        """Resuelve la ruta del log de seguridad del middleware."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "SECURITY_LOG_PATH",
                root_path / "src/apps/7_service_frontend/logs/middleware_secure.log",
            )
        )

    def _get_activity_log_path(self) -> Path:
        """Resuelve la ruta del log de actividad del middleware."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "ACTIVITY_LOG_PATH",
                root_path / "src/apps/7_service_frontend/logs/middleware_activiy.log",
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

    def log_activity_action(
        self, action: str, entity_id: int | None, ip: str, user_agent: str
    ) -> bool:
        """Registra una acción operativa en el log de actividad."""

        log_path = self._get_activity_log_path()
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
                "Error al escribir log de actividad en %s: %s", log_path, exc
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

        if self._should_use_broker_reads():
            try:
                records = self._broker_client.fetch_organizations()
            except BrokerBackendCommunicationError as exc:
                raise BusinessRuleError(
                    "No se pudo cargar organizaciones desde el broker"
                ) from exc
            self._sync_json_list(data_path, records)
            return [OrganizationDto.model_validate(record) for record in records]
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

        payload = [org.model_dump() for org in organizations]
        if self._should_use_broker_reads() or self._should_replicate():
            try:
                self._broker_client.store_organizations(payload)
            except BrokerBackendCommunicationError as exc:
                raise BusinessRuleError(
                    "No se pudo guardar organizaciones en el broker"
                ) from exc
        self._sync_json_list(data_path, payload)

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

    def _get_low_level_permissions_path(self) -> Path:
        """Resuelve la ruta del archivo de permisos de bajo nivel."""

        root_path = Path(__file__).resolve().parents[3]
        return Path(
            os.environ.get(
                "LOW_LEVEL_PERMISSIONS_PATH",
                root_path
                / "src/2_shared_application/moks/low_level_permisions.json",
            )
        )

    def _load_roles(self, data_path: Path) -> list[RoleDto]:
        """Carga los roles desde archivo JSON."""

        if self._should_use_broker_reads():
            try:
                records = self._broker_client.fetch_roles()
            except BrokerBackendCommunicationError as exc:
                raise BusinessRuleError("No se pudo cargar roles desde el broker") from exc
            self._sync_json_list(data_path, records)
            return [RoleDto.model_validate(record) for record in records]
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

        if self._should_use_broker_reads():
            try:
                records = self._broker_client.fetch_basic_permissions()
            except BrokerBackendCommunicationError as exc:
                raise BusinessRuleError(
                    "No se pudo cargar permisos desde el broker"
                ) from exc
            self._sync_json_list(data_path, records)
            return [BasicPermissionDto.model_validate(record) for record in records]
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

    def _load_low_level_permissions(
        self, data_path: Path
    ) -> list[LowLevelPermissionDto]:
        """Carga permisos de bajo nivel desde archivo JSON."""

        if self._should_use_broker_reads():
            try:
                records = self._broker_client.fetch_low_level_permissions()
            except BrokerBackendCommunicationError as exc:
                raise BusinessRuleError(
                    "No se pudo cargar permisos de bajo nivel desde el broker"
                ) from exc
            self._sync_json_list(data_path, records)
            return [LowLevelPermissionDto.model_validate(record) for record in records]
        try:
            with data_path.open("r", encoding="utf-8") as file_handle:
                records = json.load(file_handle)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as exc:
            raise BusinessRuleError(
                "El archivo de permisos de bajo nivel no es válido"
            ) from exc
        return [LowLevelPermissionDto.model_validate(record) for record in records]

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

    def _get_low_level_permissions_for_role(
        self, identity_type_id: int
    ) -> dict[str, Any]:
        """Obtiene permisos de bajo nivel para un rol."""

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
            return {}

        permission_ids = role_entry.identity_type_group_permissions
        if not permission_ids:
            return {}

        permissions = self._load_low_level_permissions(
            self._get_low_level_permissions_path()
        )
        for permission in permissions:
            if permission.id_permissions == permission_ids[0]:
                return permission.model_dump()
        return {}

    def _load_manage_roles(self, data_path: Path) -> list[ManageRoleByOrgDto]:
        """Carga la asignación de roles por organización."""

        if self._should_use_broker_reads():
            try:
                records = self._broker_client.fetch_manage_roles()
            except BrokerBackendCommunicationError as exc:
                raise BusinessRuleError(
                    "No se pudo cargar roles por organización desde el broker"
                ) from exc
            return [ManageRoleByOrgDto.model_validate(record) for record in records]
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

        payload = [entry.model_dump() for entry in entries]
        if self._should_use_broker_reads() or self._should_replicate():
            try:
                self._broker_client.store_manage_roles(payload)
            except BrokerBackendCommunicationError as exc:
                raise BusinessRuleError(
                    "No se pudo guardar roles por organización en el broker"
                ) from exc
        if self._should_use_broker_reads():
            return
        with data_path.open("w", encoding="utf-8") as file_handle:
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

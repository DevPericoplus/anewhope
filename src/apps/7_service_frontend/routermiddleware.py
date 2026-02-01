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


def _load_env_settings_module(module_name: str) -> Any:
    """Carga el módulo de configuración compartida."""

    module_path = (
        Path(__file__).resolve().parents[3]
        / "src/2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise BusinessRuleError("No se pudo cargar el módulo de configuración")
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

    env_settings = _load_env_settings_module("middleware_env_settings")
    return {
        "jwt_access_secret_key": env_settings.get_protected_value(
            "jwt_access_secret_key"
        ),
        "jwt_session_secret_key": env_settings.get_protected_value(
            "jwt_session_secret_key"
        ),
        "jwt_algorithm": env_settings.get_protected_value("jwt_algorithm"),
        "jwt_access_expiration_seconds": env_settings.get_protected_value(
            "jwt_access_expiration_seconds"
        ),
        "jwt_session_expiration_seconds": env_settings.get_protected_value(
            "jwt_session_expiration_seconds"
        ),
    }


def _load_protected_storage_settings() -> dict[str, str]:
    """Carga la configuración de almacenamiento desde protected_values.py."""

    env_settings = _load_env_settings_module("middleware_env_settings")
    return {
        "broker_backend_base_url": env_settings.get_protected_value(
            "broker_backend_base_url", "http://localhost:8008"
        ),
        "storage_mode": env_settings.get_env_value("STORAGE_MODE", "mock"),
        "active_sync_db_jsons": env_settings.get_env_value(
            "ACTIVE_SYNC_DB_JSONS", "1"
        ),
    }


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
    """Contexto de sesión validado.

    Incluye los tokens originales para propagación a servicios downstream.
    Esto permite mantener el contexto de seguridad en todo el flujo
    (Security by Design).
    """

    user_id: int
    organization_id: int
    identity_type_id: int
    access_payload: dict[str, Any]
    session_payload: dict[str, Any]
    access_token: str = ""  # Token JWT original para propagación
    session_token: str = ""  # Token de sesión original para propagación

    @property
    def authorization_header(self) -> str:
        """Retorna el header Authorization formateado."""
        if self.access_token:
            return f"Bearer {self.access_token}"
        return ""


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
        """Obtiene el modo de almacenamiento configurado.
        
        CRÍTICO: En producción (entorno 'pro') solo se permite db_only.
        Si se detecta otro modo, se fuerza a db_only con un warning.
        """
        protected = _load_protected_storage_settings()
        raw_mode = os.environ.get("STORAGE_MODE", protected.get("storage_mode", "mock"))
        mode = _parse_storage_mode(raw_mode)
        
        # Validación de seguridad para producción
        environment = os.environ.get("ENVIRONMENT", "").lower()
        if environment == "pro" and mode != StorageMode.DB_ONLY:
            self._logger.warning(
                "SEGURIDAD: En producción solo se permite storage_mode=db_only. "
                "Forzando cambio de '%s' a 'db_only'",
                mode.value
            )
            return StorageMode.DB_ONLY
        
        return mode

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
        """Ejecuta la sincronización periódica en segundo plano.
        
        CRÍTICO: En producción (entorno 'pro') la sincronización está deshabilitada
        por seguridad para evitar exponer datos en archivos JSON.
        """
        # Verificación de seguridad para producción
        environment = os.environ.get("ENVIRONMENT", "").lower()
        if environment == "pro":
            self._sync_logger.info(
                "SEGURIDAD: Sincronización deshabilitada en producción. "
                "Los datos solo se gestionan en MariaDB."
            )
            return

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
        
        # PROTECCIÓN: No sobrescribir JSON con datos si el broker devuelve vacío
        # Esto evita perder datos locales cuando el backend no tiene la tabla
        if not broker_records and json_records:
            self._sync_logger.warning(
                "Protección activada dataset=%s: broker devuelve vacío pero JSON tiene %s registros. "
                "No se sobrescribe para evitar pérdida de datos.",
                dataset.name,
                len(json_records),
            )
            return
        
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
            access_token=access_token,
            session_token=session_token,
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
        """Guarda los usuarios en el archivo JSON con retry automático.
        
        IMPORTANTE: En modo db_only, NO escribe al cache local porque el
        backend core ya lo hace después de sincronizar con MariaDB.
        Esto evita que el middleware sobrescriba el OTP correcto.
        """

        payload = [user.model_dump() for user in users]
        
        # Log detallado para debugging de OTP
        admin_users = [u for u in payload if u.get("user_name") == "adminone"]
        if admin_users:
            self._logger.info(
                "_store_users() llamado - adminone OTP=%s, storage_mode=%s",
                admin_users[0].get("user_otp"),
                self._storage_mode.value,
            )
        
        use_broker = self._should_use_broker_reads()
        replicate = self._should_replicate()
        self._logger.info(
            "_store_users: use_broker=%s, replicate=%s",
            use_broker, replicate
        )
        
        if use_broker or replicate:
            max_retries = 3
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    self._logger.info(
                        "Llamando broker.store_users() intento %d/%d",
                        attempt + 1, max_retries
                    )
                    self._broker_client.store_users(payload)
                    self._logger.info(
                        "Usuarios sincronizados con broker (intento %d/%d)",
                        attempt + 1, max_retries
                    )
                    break  # Éxito, salir del loop
                except BrokerBackendCommunicationError as exc:
                    last_exception = exc
                    if attempt < max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        sleep_time = 2 ** attempt
                        self._logger.warning(
                            "Fallo al sincronizar usuarios con broker "
                            "(intento %d/%d). Reintentando en %ds: %s",
                            attempt + 1, max_retries, sleep_time, exc
                        )
                        time.sleep(sleep_time)
                    else:
                        # Último intento falló
                        self._logger.error(
                            "Todos los intentos de sincronización con broker fallaron "
                            "tras %d intentos: %s",
                            max_retries, exc
                        )
            
            # Si todos los intentos fallaron, lanzar excepción
            if last_exception:
                raise BusinessRuleError(
                    f"No se pudo guardar usuarios en broker tras {max_retries} intentos. "
                    f"OTP NO sincronizado."
                ) from last_exception
            
            # En modo db_only, NO escribir al cache local
            # El backend core ya sincroniza con MariaDB y escribe al JSON
            if use_broker:
                self._logger.info(
                    "Modo db_only: cache local NO actualizado (delegado a backend core)"
                )
                return
        
        # Solo en modo mock o mock_and_db: escribir al cache local
        self._logger.info("Escribiendo cache local en %s", data_path)
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

        # Devolver datos al frontend para que envíe el SMS directamente
        # El frontend es responsable de enviar el SMS a la API externa (Infobip)
        phone_number = str(user_record.user_mobile).strip()
        
        self._append_auth_log(
            sessions_data,
            user_name=user_name,
            event="otp_request",
            status="success",
            error_code=None,
            details="Datos OTP entregados al frontend para envío de SMS",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._store_sessions_data(sessions_path, sessions_data)
        
        return {
            "success": True,
            "otp": user_otp,
            "phone_number": phone_number,
        }

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
        """
        Obtiene permisos básicos para un rol.
        
        Fuente de datos según storage_mode:
        - db_only: Consulta directamente MariaDB vía broker backend
        - mock: Lee desde JSON local
        - mock_and_db: Lee desde JSON local (sincronizado con MariaDB)
        """
        # En modo db_only, ir directo a MariaDB vía broker
        if self._should_use_broker_reads():
            self._logger.debug(
                "Modo db_only: Consultando permisos básicos desde MariaDB (identity_type_id=%s)",
                identity_type_id
            )
            return self._get_basic_permissions_from_broker_fallback(identity_type_id)

        # Modos mock o mock_and_db: cargar desde JSON local
        roles = self._load_roles(self._get_roles_path())
        
        # Si roles.json está vacío, intentar fallback a MariaDB vía broker
        if not roles:
            self._logger.warning(
                "roles.json está vacío (identity_type_id=%s). "
                "Intentando fallback a MariaDB para permisos básicos...",
                identity_type_id
            )
            return self._get_basic_permissions_from_broker_fallback(identity_type_id)
        
        # Buscar el rol específico
        role_entry = next(
            (
                role
                for role in roles
                if role.identity_type_id == identity_type_id
            ),
            None,
        )
        
        if role_entry is None:
            self._logger.warning(
                "Rol no encontrado en roles.json (identity_type_id=%s). "
                "Intentando fallback a MariaDB para permisos básicos...",
                identity_type_id
            )
            return self._get_basic_permissions_from_broker_fallback(identity_type_id)

        permission_ids = role_entry.identity_type_group_permissions
        permissions = self._load_basic_permissions(self._get_basic_permissions_path())
        
        # Si basic_permissions.json está vacío, intentar fallback
        if not permissions:
            self._logger.warning(
                "basic_permissions.json está vacío (identity_type_id=%s). "
                "Intentando fallback a MariaDB para permisos básicos...",
                identity_type_id
            )
            return self._get_basic_permissions_from_broker_fallback(identity_type_id)
        
        result = [
            permission.model_dump(by_alias=True)
            for permission in permissions
            if permission.id in permission_ids
        ]
        
        if result:
            self._logger.debug(
                "Permisos básicos cargados desde JSON local "
                "(identity_type_id=%s, count=%s, source=JSON)",
                identity_type_id,
                len(result)
            )
        else:
            self._logger.warning(
                "Permisos básicos no encontrados en JSON "
                "(identity_type_id=%s, permission_ids=%s). "
                "Intentando fallback a MariaDB...",
                identity_type_id,
                permission_ids
            )
            return self._get_basic_permissions_from_broker_fallback(identity_type_id)
        
        return result
    
    def _get_basic_permissions_from_broker_fallback(
        self, identity_type_id: int
    ) -> list[dict[str, Any]]:
        """
        Fallback: Consulta permisos básicos desde MariaDB vía broker backend.
        
        Args:
            identity_type_id: ID del tipo de identidad (rol)
        
        Returns:
            Lista de permisos básicos o [] si no se encuentran
        """
        
        try:
            # 1. Obtener roles desde broker → MariaDB
            self._logger.info(
                "Fallback: Consultando roles desde MariaDB para permisos básicos "
                "(identity_type_id=%s)...",
                identity_type_id
            )
            broker_roles = self._broker_client.fetch_roles()
            
            if not broker_roles:
                self._logger.error(
                    "Fallback: Tabla 'roles' en MariaDB está vacía "
                    "(identity_type_id=%s)",
                    identity_type_id
                )
                return []
            
            # 2. Buscar el rol específico
            role_record = next(
                (
                    role for role in broker_roles
                    if role.get("identity_type_id") == identity_type_id
                ),
                None
            )
            
            if role_record is None:
                self._logger.error(
                    "Fallback: Rol no encontrado en MariaDB "
                    "(identity_type_id=%s)",
                    identity_type_id
                )
                return []
            
            permission_ids = role_record.get("identity_type_group_permissions", [])
            
            # 3. Obtener permisos básicos desde broker → MariaDB
            self._logger.info(
                "Fallback: Consultando basic_permissions desde MariaDB "
                "(permission_ids=%s)...",
                permission_ids
            )
            broker_permissions = self._broker_client.fetch_basic_permissions()
            
            if not broker_permissions:
                self._logger.error(
                    "Fallback: Tabla 'basic_permissions' en MariaDB está vacía "
                    "(identity_type_id=%s)",
                    identity_type_id
                )
                return []
            
            # 4. Filtrar permisos
            result = [
                perm for perm in broker_permissions
                if perm.get("id") in permission_ids
            ]
            
            self._logger.info(
                "✅ Fallback exitoso: Permisos básicos cargados desde MariaDB "
                "(identity_type_id=%s, count=%s, source=MariaDB)",
                identity_type_id,
                len(result)
            )
            return result
            
        except BrokerBackendCommunicationError as exc:
            self._logger.error(
                "Fallback: Error al comunicarse con broker backend "
                "(identity_type_id=%s): %s",
                identity_type_id,
                exc,
                exc_info=True
            )
            return []
        except Exception as exc:
            self._logger.error(
                "Fallback: Error inesperado al consultar MariaDB "
                "(identity_type_id=%s): %s",
                identity_type_id,
                exc,
                exc_info=True
            )
            return []

    def _get_low_level_permissions_for_role(
        self, identity_type_id: int
    ) -> dict[str, Any]:
        """
        Obtiene permisos de bajo nivel para un rol.
        
        Fuente de datos según storage_mode:
        - db_only: Consulta directamente MariaDB vía broker backend
        - mock: Lee desde JSON local
        - mock_and_db: Lee desde JSON local (sincronizado con MariaDB)
        """
        # En modo db_only, ir directo a MariaDB vía broker
        if self._should_use_broker_reads():
            self._logger.debug(
                "Modo db_only: Consultando permisos desde MariaDB (identity_type_id=%s)",
                identity_type_id
            )
            return self._get_low_level_permissions_from_broker_fallback(identity_type_id)

        # Modos mock o mock_and_db: cargar desde JSON local
        roles = self._load_roles(self._get_roles_path())
        
        # Si roles.json está vacío, intentar fallback a MariaDB vía broker
        if not roles:
            self._logger.warning(
                "roles.json está vacío (identity_type_id=%s). "
                "Intentando fallback a MariaDB vía broker backend...",
                identity_type_id
            )
            return self._get_low_level_permissions_from_broker_fallback(identity_type_id)
        
        # Buscar el rol específico
        role_entry = next(
            (
                role
                for role in roles
                if role.identity_type_id == identity_type_id
            ),
            None,
        )
        
        if role_entry is None:
            self._logger.warning(
                "Rol no encontrado en roles.json (identity_type_id=%s). "
                "Intentando fallback a MariaDB vía broker backend...",
                identity_type_id
            )
            return self._get_low_level_permissions_from_broker_fallback(identity_type_id)

        permission_ids = role_entry.identity_type_group_permissions
        if not permission_ids:
            self._logger.warning(
                "Rol sin permisos asignados en roles.json (identity_type_id=%s, "
                "role=%s). Intentando fallback a MariaDB vía broker backend...",
                identity_type_id,
                role_entry.identity_type_name
            )
            return self._get_low_level_permissions_from_broker_fallback(identity_type_id)

        # Cargar permisos de bajo nivel desde JSON
        permissions = self._load_low_level_permissions(
            self._get_low_level_permissions_path()
        )
        
        # Si low_level_permisions.json está vacío, intentar fallback
        if not permissions:
            self._logger.warning(
                "low_level_permisions.json está vacío (identity_type_id=%s). "
                "Intentando fallback a MariaDB vía broker backend...",
                identity_type_id
            )
            return self._get_low_level_permissions_from_broker_fallback(identity_type_id)
        
        # Buscar los permisos específicos
        for permission in permissions:
            if permission.id_permissions == permission_ids[0]:
                self._logger.debug(
                    "Permisos cargados desde JSON local (identity_type_id=%s, "
                    "id_permissions=%s, source=JSON)",
                    identity_type_id,
                    permission.id_permissions
                )
                return permission.model_dump()
        
        # No se encontraron los permisos en JSON, intentar fallback
        self._logger.warning(
            "Permisos no encontrados en low_level_permisions.json "
            "(identity_type_id=%s, permission_ids=%s). "
            "Intentando fallback a MariaDB vía broker backend...",
            identity_type_id,
            permission_ids
        )
        return self._get_low_level_permissions_from_broker_fallback(identity_type_id)
    
    def _get_low_level_permissions_from_broker_fallback(
        self, identity_type_id: int
    ) -> dict[str, Any]:
        """
        Fallback: Consulta permisos directamente desde MariaDB vía broker backend.
        
        Este método se llama cuando los archivos JSON están vacíos o incompletos.
        Consulta la tabla 'low_level_permission' en MariaDB a través del broker.
        
        Args:
            identity_type_id: ID del tipo de identidad (rol)
        
        Returns:
            Diccionario con permisos de bajo nivel o {} si no se encuentran
        """
        
        try:
            # 1. Obtener todos los roles desde broker → MariaDB
            self._logger.info(
                "Fallback: Consultando roles desde MariaDB (identity_type_id=%s)...",
                identity_type_id
            )
            broker_roles = self._broker_client.fetch_roles()
            
            if not broker_roles:
                self._logger.error(
                    "Fallback: Tabla 'roles' en MariaDB está vacía. "
                    "No se pueden obtener permisos (identity_type_id=%s)",
                    identity_type_id
                )
                return {}
            
            # 2. Buscar el rol específico
            role_record = next(
                (
                    role for role in broker_roles
                    if role.get("identity_type_id") == identity_type_id
                ),
                None
            )
            
            if role_record is None:
                self._logger.error(
                    "Fallback: Rol no encontrado en MariaDB (identity_type_id=%s). "
                    "Roles disponibles: %s",
                    identity_type_id,
                    [r.get("identity_type_id") for r in broker_roles]
                )
                return {}
            
            permission_ids = role_record.get("identity_type_group_permissions", [])
            if not permission_ids:
                self._logger.error(
                    "Fallback: Rol sin permisos asignados en MariaDB "
                    "(identity_type_id=%s, role=%s)",
                    identity_type_id,
                    role_record.get("identity_type_name")
                )
                return {}
            
            # 3. Obtener permisos de bajo nivel desde broker → MariaDB
            self._logger.info(
                "Fallback: Consultando low_level_permission desde MariaDB "
                "(id_permissions=%s)...",
                permission_ids[0]
            )
            broker_permissions = self._broker_client.fetch_low_level_permissions()
            
            if not broker_permissions:
                self._logger.error(
                    "Fallback: Tabla 'low_level_permission' en MariaDB está vacía. "
                    "No se pueden obtener permisos (identity_type_id=%s)",
                    identity_type_id
                )
                return {}
            
            # 4. Buscar los permisos específicos
            for permission in broker_permissions:
                if permission.get("id_permissions") == permission_ids[0]:
                    self._logger.info(
                        "✅ Fallback exitoso: Permisos cargados desde MariaDB "
                        "(identity_type_id=%s, id_permissions=%s, source=MariaDB, "
                        "training_create=%s, can_access_backoffice=posible)",
                        identity_type_id,
                        permission.get("id_permissions"),
                        permission.get("training_create", False)
                    )
                    return permission
            
            # No se encontraron los permisos
            self._logger.error(
                "Fallback: Permisos no encontrados en MariaDB "
                "(identity_type_id=%s, permission_ids=%s). "
                "Permisos disponibles: %s",
                identity_type_id,
                permission_ids,
                [p.get("id_permissions") for p in broker_permissions]
            )
            return {}
            
        except BrokerBackendCommunicationError as exc:
            self._logger.error(
                "Fallback: Error al comunicarse con broker backend "
                "(identity_type_id=%s): %s. "
                "No se pueden obtener permisos desde MariaDB.",
                identity_type_id,
                exc,
                exc_info=True
            )
            return {}
        except Exception as exc:
            self._logger.error(
                "Fallback: Error inesperado al consultar MariaDB "
                "(identity_type_id=%s): %s",
                identity_type_id,
                exc,
                exc_info=True
            )
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
        """Determina el rol a asignar para un usuario.
        
        Reglas de asignación de roles:
        1. Si se solicita identity_type_id = 5 (auditor/usuario base), SIEMPRE se respeta.
           Este es el rol por defecto para usuarios creados desde el panel de organización.
        2. Si es el primer usuario de la organización y no se especifica rol, se asigna 2 (admin).
        3. Para otros casos, se usa el rol solicitado o 5 (auditor) por defecto.
        
        IMPORTANTE: Solo puede haber UN administrador (identity_type_id=2) por organización.
        Los usuarios adicionales creados desde el panel son auditores (identity_type_id=5)
        y pueden tener otros roles asignados en tablas relacionadas con proyectos.
        """
        # Si se solicita explícitamente identity_type_id = 5 (auditor/usuario base),
        # SIEMPRE se respeta. Este es el rol para usuarios creados desde el panel.
        if requested_identity_type_id == 5:
            return 5
        
        manage_roles_path = self._get_manage_roles_path()
        entries = self._load_manage_roles(manage_roles_path)
        is_first_user = not any(
            entry.id_organization == organization_id for entry in entries
        )
        
        # Solo el primer usuario de la organización puede ser administrador
        if is_first_user and requested_identity_type_id is None:
            return 2
        
        # Si se solicita otro rol específico, usarlo
        if requested_identity_type_id is not None:
            return requested_identity_type_id
        
        # Por defecto, usuarios adicionales son auditores (permisos restringidos)
        return 5

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

    def update_user_active_status(
        self, user_id: int, active: bool, requester_org_id: int
    ) -> dict[str, Any]:
        """
        Actualiza el estado activo/inactivo de un usuario.
        
        FLUJO CORRECTO (según arquitectura):
        Frontend/Backoffice → Middleware (aquí) → Broker → Backend Core → MariaDB
        
        Args:
            user_id: ID del usuario a modificar
            active: True para habilitar, False para deshabilitar
            requester_org_id: ID de la organización del usuario que solicita el cambio
        
        Returns:
            Diccionario con user_id, active y message
        
        Raises:
            BusinessRuleError: Si hay error en el flujo o el usuario no existe
        """
        storage_mode = self._get_storage_mode()
        
        if storage_mode == "mock":
            # Solo JSON, sin pasar por broker/backend core
            return self._update_user_status_mock_only(user_id, active, requester_org_id)
        
        # Modo db_only o mock_and_db: enviar al broker → backend core → MariaDB
        try:
            self._logger.info(
                "Enviando actualización de estado al broker: user_id=%s active=%s org_id=%s",
                user_id,
                active,
                requester_org_id,
            )
            
            # Usar el método del broker client que sigue el flujo correcto
            result = self._broker_client.update_user_status(
                user_id=user_id,
                active=active,
                requester_org_id=requester_org_id,
            )
            
            # Actualizar también el JSON local para mantener consistencia
            if storage_mode == "mock_and_db":
                self._update_user_status_in_json(user_id, active)
            
            return result
            
        except BrokerBackendCommunicationError as e:
            self._logger.error("Error en flujo broker para actualizar usuario: %s", e)
            raise BusinessRuleError(f"Error actualizando usuario: {e}") from e

    def _update_user_status_mock_only(
        self, user_id: int, active: bool, requester_org_id: int
    ) -> dict[str, Any]:
        """Actualiza estado solo en JSON (modo mock)."""
        users_path = self._get_users_file_path()
        all_users = self._load_users(users_path)
        
        target_user = None
        for user in all_users:
            if user.user_id == user_id:
                target_user = user
                break
        
        if target_user is None:
            raise BusinessRuleError(f"Usuario con ID {user_id} no encontrado")
        
        if target_user.organization_id != requester_org_id:
            raise BusinessRuleError(
                "No tiene permisos para modificar usuarios de otra organización"
            )
        
        for user in all_users:
            if user.user_id == user_id:
                user.active = active
                break
        
        self._store_users(users_path, all_users)
        
        action = "habilitado" if active else "deshabilitado"
        self._logger.info(
            "Usuario %s (id=%s) %s por org_id=%s (modo mock)",
            target_user.user_name,
            user_id,
            action,
            requester_org_id,
        )
        
        return {
            "user_id": user_id,
            "active": active,
            "message": f"Usuario {action} correctamente",
        }

    def _update_user_status_in_json(self, user_id: int, active: bool) -> None:
        """Actualiza el estado del usuario en el JSON local."""
        try:
            users_path = self._get_users_file_path()
            all_users = self._load_users(users_path)
            
            for user in all_users:
                if user.user_id == user_id:
                    user.active = active
                    break
            
            self._store_users(users_path, all_users)
            self._logger.info("Usuario id=%s actualizado en JSON: active=%s", user_id, active)
        except Exception as e:
            self._logger.warning("Error actualizando JSON local: %s", e)

    def check_user_exists(self, user_name: str) -> dict[str, Any]:
        """Verifica si existe un usuario por nombre de usuario.
        
        Flujo: Frontend → Middleware (aquí) → Broker → Backend Core → JSON/MariaDB
        
        Args:
            user_name: Nombre de usuario a verificar
        
        Returns:
            Diccionario con exists y user_name
        """
        storage_mode = self._get_storage_mode()
        
        if storage_mode == "mock":
            # Solo JSON local
            users = self._load_users(self._get_users_file_path())
            exists = any(u.user_name.lower() == user_name.lower() for u in users)
            return {"exists": exists, "user_name": user_name}
        
        # Usar broker → backend core
        try:
            return self._broker_client.check_user_exists(user_name)
        except BrokerBackendCommunicationError as e:
            self._logger.error("Error verificando usuario: %s", e)
            raise BusinessRuleError(f"Error verificando usuario: {e}") from e

    def get_user_by_email(self, email: str) -> dict[str, Any]:
        """Obtiene datos de un usuario por email.
        
        Flujo: Frontend → Middleware (aquí) → Broker → Backend Core → JSON/MariaDB
        
        Args:
            email: Email del usuario
        
        Returns:
            Diccionario con datos del usuario o found=False
        """
        storage_mode = self._get_storage_mode()
        
        if storage_mode == "mock":
            # Solo JSON local
            users = self._load_users(self._get_users_file_path())
            email_lower = email.lower().strip()
            for user in users:
                if user.user_email.lower() == email_lower:
                    return {
                        "found": True,
                        "user_id": user.user_id,
                        "user_name": user.user_name,
                        "user_email": user.user_email,
                        "user_mobile": user.user_mobile,
                        "organization_id": user.organization_id,
                    }
            return {"found": False}
        
        # Usar broker → backend core
        try:
            return self._broker_client.get_user_by_email(email)
        except BrokerBackendCommunicationError as e:
            self._logger.error("Error obteniendo usuario por email: %s", e)
            raise BusinessRuleError(f"Error obteniendo usuario: {e}") from e

    def update_user_password(
        self, email: str, new_password: str, new_otp: str
    ) -> dict[str, Any]:
        """Actualiza contraseña y OTP de un usuario.
        
        Flujo: Frontend → Middleware (aquí) → Broker → Backend Core → JSON/MariaDB
        
        Args:
            email: Email del usuario
            new_password: Nueva contraseña (ya cifrada)
            new_otp: Nuevo código OTP
        
        Returns:
            Diccionario con success y message
        """
        storage_mode = self._get_storage_mode()
        
        if storage_mode == "mock":
            # Solo JSON local
            users_path = self._get_users_file_path()
            users = self._load_users(users_path)
            email_lower = email.lower().strip()
            
            user_found = False
            for user in users:
                if user.user_email.lower() == email_lower:
                    user.user_password = new_password
                    user.user_otp = new_otp
                    user_found = True
                    break
            
            if not user_found:
                return {"success": False, "message": "Usuario no encontrado"}
            
            self._store_users(users_path, users)
            return {"success": True, "message": "Contraseña actualizada correctamente"}
        
        # Usar broker → backend core
        try:
            return self._broker_client.update_user_password(email, new_password, new_otp)
        except BrokerBackendCommunicationError as e:
            self._logger.error("Error actualizando contraseña: %s", e)
            raise BusinessRuleError(f"Error actualizando contraseña: {e}") from e

    def get_organization_users(
        self, organization_id: int, identity_type_id: int | None = 5, active_only: bool = True
    ) -> list[dict[str, Any]]:
        """
        Obtiene los usuarios de una organización filtrados por identity_type_id.
        
        Args:
            organization_id: ID de la organización
            identity_type_id: Filtrar por tipo de identidad (default: 5 = auditores)
            active_only: Si True, solo retorna usuarios activos (default: True)
                         El backoffice usa False para ver también usuarios inactivos
        
        Returns:
            Lista de diccionarios con user_id, user_name y active
        """
        users_path = self._get_users_file_path()
        all_users = self._load_users(users_path)
        
        # Filtrar por organización, identity_type_id y opcionalmente por active
        filtered_users = [
            {
                "user_id": user.user_id,
                "user_name": user.user_name,
                "active": user.active,
            }
            for user in all_users
            if user.organization_id == organization_id
            and (identity_type_id is None or user.identity_type_id == identity_type_id)
            and (not active_only or user.active)  # Filtrar inactivos si active_only=True
        ]
        
        self._logger.info(
            "Listado usuarios org_id=%s identity_type_id=%s active_only=%s total=%s",
            organization_id,
            identity_type_id,
            active_only,
            len(filtered_users),
        )
        
        return filtered_users

    def create_user(self, user_data: dict[str, Any]) -> UserCreationResult:
        """Crea un usuario y registra su rol por organización.
        
        Según STORAGE_MODE:
        - mock: Solo guarda en JSON local
        - mock_and_db: Guarda en JSON y envía al broker->core->DB
        - db_only: Solo envía al broker->core->DB
        """
        organization_id = int(user_data.get("organization_id", 1))
        requested_identity_type_id = user_data.get("identity_type_id")
        identity_type_id = self._get_manage_roles_identity_type_id(
            organization_id, requested_identity_type_id
        )
        
        # Preparar datos con identity_type_id resuelto
        user_data_resolved = {
            **user_data,
            "organization_id": organization_id,
            "identity_type_id": identity_type_id,
        }
        
        # Determinar flujo según STORAGE_MODE
        if self._storage_mode == StorageMode.DB_ONLY:
            # Solo usar broker -> core -> DB
            return self._create_user_via_broker(user_data_resolved)
        elif self._storage_mode == StorageMode.MOCK_AND_DB:
            # Guardar en JSON local Y enviar al broker
            result = self._create_user_local(user_data_resolved)
            try:
                self._broker_client.create_user(user_data_resolved)
                self._logger.info(
                    "Usuario replicado en DB vía broker user_id=%s",
                    result.user_id,
                )
            except Exception as exc:
                self._logger.warning(
                    "Error al replicar usuario en DB: %s", exc
                )
            return result
        else:
            # MOCK_ONLY: Solo JSON local
            return self._create_user_local(user_data_resolved)
    
    def _create_user_local(self, user_data: dict[str, Any]) -> UserCreationResult:
        """Crea un usuario en el almacenamiento JSON local."""
        users_path = self._get_users_file_path()
        users = self._load_users(users_path)
        existing_ids = [user.user_id for user in users]
        next_id = max(existing_ids, default=0) + 1
        organization_id = int(user_data.get("organization_id", 1))
        identity_type_id = int(user_data.get("identity_type_id", 5))

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
            "Usuario creado (local) user_id=%s org_id=%s role_id=%s",
            next_id,
            organization_id,
            identity_type_id,
        )
        return UserCreationResult(
            user_id=next_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
        )
    
    def _create_user_via_broker(self, user_data: dict[str, Any]) -> UserCreationResult:
        """Crea un usuario enviando al broker -> backend core -> DB."""
        try:
            response = self._broker_client.create_user(user_data)
            user_id = response.get("user_id", 0)
            organization_id = response.get("organization_id", user_data.get("organization_id", 1))
            identity_type_id = response.get("identity_type_id", user_data.get("identity_type_id", 5))
            
            self._logger.info(
                "Usuario creado (vía broker) user_id=%s org_id=%s role_id=%s",
                user_id,
                organization_id,
                identity_type_id,
            )
            return UserCreationResult(
                user_id=user_id,
                organization_id=organization_id,
                identity_type_id=identity_type_id,
            )
        except Exception as exc:
            self._logger.error("Error al crear usuario vía broker: %s", exc)
            raise BusinessRuleError(f"Error al crear usuario: {exc}") from exc

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

    # === Métodos de Training (Backend IA) ===

    def _configure_broker_security(self, session: SessionContext) -> None:
        """Configura el contexto de seguridad en el broker client.

        Este método propaga los tokens JWT al broker para mantener
        el contexto de sesión en todo el flujo (Security by Design).

        Args:
            session: Contexto de sesión validado con tokens
        """
        if self._broker_client is None:
            return

        self._broker_client.set_security_context(
            authorization=session.authorization_header,
            session_token=session.session_token,
        )
        self._logger.debug(
            "Contexto de seguridad configurado para broker: user_id=%s",
            session.user_id,
        )

    def trainer_health_check(self, session: SessionContext) -> dict[str, Any]:
        """Verifica el estado del servicio trainer.

        Args:
            session: Contexto de sesión del usuario

        Returns:
            Estado del servicio trainer

        Raises:
            BusinessRuleError: Si no se puede contactar al trainer
        """
        self._configure_broker_security(session)
        try:
            return self._broker_client.trainer_health_check()
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                "No se pudo verificar el estado del trainer"
            ) from exc

    def clone_version_for_training(
        self,
        payload: dict[str, Any],
        session: SessionContext,
    ) -> dict[str, Any]:
        """Clona una versión para entrenamiento.

        Args:
            payload: Datos de la versión a clonar
            session: Contexto de sesión del usuario

        Returns:
            Resultado del clonado con path de destino

        Raises:
            BusinessRuleError: Si no tiene permisos o falla el clonado
        """
        # Validar permisos de entrenamiento
        if not self.has_low_level_permission(session, "training_create"):
            raise BusinessRuleError(
                "Sin permisos para clonar versiones para entrenamiento"
            )

        self._configure_broker_security(session)

        # Añadir identity_type_id para validación en backend
        payload_with_auth = {
            **payload,
            "identity_type_id": session.identity_type_id,
        }

        self._logger.info(
            "Clonando versión para entrenamiento: user_id=%s org_id=%s project_id=%s",
            session.user_id,
            payload.get("id_organization"),
            payload.get("id_project"),
        )

        try:
            return self._broker_client.clone_version_for_training(payload_with_auth)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                "No se pudo clonar la versión para entrenamiento"
            ) from exc

    def start_training(
        self,
        payload: dict[str, Any],
        session: SessionContext,
    ) -> dict[str, Any]:
        """Inicia un proceso de entrenamiento.

        Args:
            payload: Configuración del entrenamiento
            session: Contexto de sesión del usuario

        Returns:
            ID del entrenamiento iniciado

        Raises:
            BusinessRuleError: Si no tiene permisos o falla el inicio
        """
        # Validar permisos de entrenamiento
        if not self.has_low_level_permission(session, "training_start"):
            raise BusinessRuleError("Sin permisos para iniciar entrenamiento")

        self._configure_broker_security(session)

        payload_with_auth = {
            **payload,
            "identity_type_id": session.identity_type_id,
        }

        self._logger.info(
            "Iniciando entrenamiento: user_id=%s org_id=%s project_id=%s",
            session.user_id,
            payload.get("id_organization"),
            payload.get("id_project"),
        )

        try:
            return self._broker_client.start_training(payload_with_auth)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError("No se pudo iniciar el entrenamiento") from exc

    def stop_training(
        self,
        payload: dict[str, Any],
        session: SessionContext,
    ) -> dict[str, Any]:
        """Detiene un proceso de entrenamiento.

        Args:
            payload: Datos del entrenamiento a detener
            session: Contexto de sesión del usuario

        Returns:
            Confirmación de detención

        Raises:
            BusinessRuleError: Si no tiene permisos o falla la detención
        """
        # Validar permisos de entrenamiento
        if not self.has_low_level_permission(session, "training_stop"):
            raise BusinessRuleError("Sin permisos para detener entrenamiento")

        self._configure_broker_security(session)

        payload_with_auth = {
            **payload,
            "identity_type_id": session.identity_type_id,
        }

        self._logger.info(
            "Deteniendo entrenamiento: user_id=%s training_id=%s",
            session.user_id,
            payload.get("training_id"),
        )

        try:
            return self._broker_client.stop_training(payload_with_auth)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError("No se pudo detener el entrenamiento") from exc

    def get_training_status(
        self,
        training_id: int,
        session: SessionContext,
    ) -> dict[str, Any]:
        """Obtiene el estado de un entrenamiento.

        Args:
            training_id: ID del entrenamiento
            session: Contexto de sesión del usuario

        Returns:
            Estado del entrenamiento con métricas

        Raises:
            BusinessRuleError: Si no tiene permisos o falla la consulta
        """
        # Validar permisos de lectura de entrenamiento
        if not self.has_low_level_permission(session, "training_read"):
            raise BusinessRuleError("Sin permisos para ver estado de entrenamiento")

        self._configure_broker_security(session)

        try:
            return self._broker_client.get_training_status(
                training_id, session.identity_type_id
            )
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                "No se pudo obtener el estado del entrenamiento"
            ) from exc

    def list_models(
        self,
        session: SessionContext,
        id_organization: int | None = None,
        id_project: int | None = None,
    ) -> dict[str, Any]:
        """Lista modelos entrenados.

        Args:
            session: Contexto de sesión del usuario
            id_organization: Filtro por organización
            id_project: Filtro por proyecto

        Returns:
            Lista de modelos

        Raises:
            BusinessRuleError: Si no tiene permisos o falla la consulta
        """
        # Validar permisos de lectura de entrenamiento
        if not self.has_low_level_permission(session, "training_read"):
            raise BusinessRuleError("Sin permisos para listar modelos")

        self._configure_broker_security(session)

        try:
            return self._broker_client.list_models(
                id_organization, id_project, session.identity_type_id
            )
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError("No se pudo listar los modelos") from exc

    def get_model_metrics(
        self,
        model_id: int,
        session: SessionContext,
    ) -> dict[str, Any]:
        """Obtiene métricas de un modelo.

        Args:
            model_id: ID del modelo
            session: Contexto de sesión del usuario

        Returns:
            Métricas del modelo

        Raises:
            BusinessRuleError: Si no tiene permisos o falla la consulta
        """
        # Validar permisos de lectura de entrenamiento
        if not self.has_low_level_permission(session, "training_read"):
            raise BusinessRuleError("Sin permisos para ver métricas del modelo")

        self._configure_broker_security(session)

        try:
            return self._broker_client.get_model_metrics(
                model_id, session.identity_type_id
            )
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                "No se pudo obtener las métricas del modelo"
            ) from exc

    def get_training_permissions(
        self,
        session: SessionContext,
    ) -> dict[str, Any]:
        """Obtiene permisos de entrenamiento para el usuario actual.

        Args:
            session: Contexto de sesión del usuario

        Returns:
            Diccionario con permisos de entrenamiento
        """
        self._configure_broker_security(session)

        try:
            return self._broker_client.get_training_permissions(
                session.identity_type_id
            )
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                "No se pudo obtener los permisos de entrenamiento"
            ) from exc

    # ========================================================================
    # Gestión de Proyectos
    # ========================================================================

    def get_organization_projects(
        self,
        organization_id: int,
        session: SessionContext,
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """Obtiene los proyectos de una organización.

        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

        Args:
            organization_id: ID de la organización
            session: Contexto de sesión del usuario
            include_deleted: Si True, incluye proyectos con existe=false

        Returns:
            {"projects": [...], "total": int}
        """
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Consultando proyectos org_id=%s user_id=%s include_deleted=%s",
            organization_id,
            session.user_id,
            include_deleted,
        )

        try:
            return self._broker_client.get_organization_projects(
                organization_id, include_deleted=include_deleted
            )
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudieron obtener los proyectos: {exc}"
            ) from exc

    def create_project(
        self,
        payload: dict[str, Any],
        session: SessionContext,
    ) -> dict[str, Any]:
        """Crea un nuevo proyecto.

        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

        El trigger en MariaDB crea automáticamente:
        - Registro en tabla estado (versión 1)
        - Registro en tabla cambios (tipo "Alta proyecto")

        Args:
            payload: {"nombre": str, "descripcion": str, "id_organizacion": int, ...}
            session: Contexto de sesión del usuario

        Returns:
            {"project_id": int, "nombre": str, ...}
        """
        self._configure_broker_security(session)

        nombre = payload.get("nombre", "").strip()
        if not nombre:
            raise BusinessRuleError("El nombre del proyecto es obligatorio")

        self._logger.info(
            "[middleware] Creando proyecto: nombre=%s org_id=%s user_id=%s",
            nombre,
            payload.get("id_organizacion"),
            session.user_id,
        )

        try:
            return self._broker_client.create_project(payload)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudo crear el proyecto: {exc}"
            ) from exc

    def update_project(
        self,
        project_id: int,
        update_data: dict[str, Any],
        session: SessionContext,
    ) -> dict[str, Any]:
        """Actualiza un proyecto existente.

        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

        El trigger en MariaDB registra cambios automáticamente.

        Args:
            project_id: ID del proyecto
            update_data: Campos a actualizar
            session: Contexto de sesión del usuario

        Returns:
            {"success": True, "updated": True, "project_id": int}
        """
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Actualizando proyecto: project_id=%s data=%s user_id=%s",
            project_id,
            update_data,
            session.user_id,
        )

        try:
            return self._broker_client.update_project(project_id, update_data)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudo actualizar el proyecto: {exc}"
            ) from exc

    def delete_project(
        self,
        project_id: int,
        session: SessionContext,
    ) -> dict[str, Any]:
        """Elimina un proyecto.

        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

        El trigger en MariaDB registra el borrado.

        Args:
            project_id: ID del proyecto
            session: Contexto de sesión del usuario

        Returns:
            {"success": True, "deleted": True, "project_id": int}
        """
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Eliminando proyecto: project_id=%s user_id=%s",
            project_id,
            session.user_id,
        )

        try:
            return self._broker_client.delete_project(project_id)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudo eliminar el proyecto: {exc}"
            ) from exc

    def request_project_support(
        self,
        project_id: int,
        tipo_cambio: str,
        descripcion: str,
        session: SessionContext,
    ) -> dict[str, Any]:
        """Registra una solicitud de soporte para un proyecto.

        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

        Args:
            project_id: ID del proyecto
            tipo_cambio: Tipo de cambio a registrar
            descripcion: Descripción de la solicitud
            session: Contexto de sesión del usuario

        Returns:
            {"success": True, "cambio_id": int | None}
        """
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Solicitud de soporte: project_id=%s tipo=%s user_id=%s",
            project_id,
            tipo_cambio,
            session.user_id,
        )

        try:
            return self._broker_client.request_project_support(
                project_id, tipo_cambio, descripcion
            )
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudo registrar la solicitud de soporte: {exc}"
            ) from exc

    # ========================================================================
    # GESTIÓN DE ROLES DE USUARIO EN PROYECTOS
    # ========================================================================

    def get_project_roles_base(self, session: SessionContext) -> dict[str, Any]:
        """Obtiene el catálogo maestro de roles base para proyectos.

        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

        Esta información es reutilizable por todas las aplicaciones
        para selectores de roles y validaciones de seguridad.

        Args:
            session: Contexto de sesión del usuario

        Returns:
            {"roles": [{"id": int, "nombre_rol": str, "descripcion": str}, ...], "total": int}
        """
        self._configure_broker_security(session)

        self._logger.info("[middleware] Consultando catálogo de roles base")

        try:
            return self._broker_client.get_project_roles_base()
        except Exception as e:
            self._logger.error("[middleware] Error obteniendo roles base: %s", e)
            raise BusinessRuleError(f"Error obteniendo roles base: {e}") from e

    def get_user_project_roles(
        self, user_id: int, organization_id: int, session: SessionContext
    ) -> dict[str, Any]:
        """Obtiene los roles de un usuario en proyectos.

        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

        Args:
            user_id: ID del usuario
            organization_id: ID de la organización
            session: Contexto de sesión del usuario

        Returns:
            {"user_id": int, "organization_id": int, "roles": [...], "total": int}
        """
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Consultando roles de usuario %s en org %s",
            user_id,
            organization_id,
        )

        try:
            return self._broker_client.get_user_project_roles(user_id, organization_id)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudieron obtener roles del usuario: {exc}"
            ) from exc

    def assign_user_to_project(
        self, payload: dict[str, Any], session: SessionContext
    ) -> dict[str, Any]:
        """Asigna un usuario a un proyecto.

        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

        Args:
            payload: {"id_usuario": int, "id_proyecto": int, "id_organizacion": int, "id_rol": int}
            session: Contexto de sesión del usuario

        Returns:
            {"success": True, "message": str, ...}
        """
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Asignando usuario %s a proyecto %s con rol %s",
            payload.get("id_usuario"),
            payload.get("id_proyecto"),
            payload.get("id_rol"),
        )

        try:
            return self._broker_client.assign_user_to_project(payload)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudo asignar usuario al proyecto: {exc}"
            ) from exc

    def remove_user_from_project(
        self, payload: dict[str, Any], session: SessionContext
    ) -> dict[str, Any]:
        """Quita un usuario de un proyecto.

        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

        Args:
            payload: {"id_usuario": int, "id_proyecto": int, "id_organizacion": int}
            session: Contexto de sesión del usuario

        Returns:
            {"success": True, "message": str, ...}
        """
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Quitando usuario %s de proyecto %s",
            payload.get("id_usuario"),
            payload.get("id_proyecto"),
        )

        try:
            return self._broker_client.remove_user_from_project(payload)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudo quitar usuario del proyecto: {exc}"
            ) from exc

    # ========================================================================
    # GESTIÓN DE TICKETS DE SOPORTE
    # ========================================================================

    def create_ticket(
        self, payload: dict[str, Any], session: SessionContext
    ) -> dict[str, Any]:
        """Crea un nuevo ticket de soporte.

        Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB

        Args:
            payload: {titulo, consulta, id_proyecto?}
            session: Contexto de sesión del usuario

        Returns:
            {"success": True, "ticket_id": int, "mensaje": str}
        """
        self._configure_broker_security(session)

        # Validar que la sesión tenga user_id válido
        if session.user_id <= 0:
            raise BusinessRuleError(f"Sesión sin user_id válido: {session.user_id}")

        # Añadir datos de la sesión al payload
        payload["id_organizacion"] = session.organization_id
        payload["cliente_id"] = session.user_id

        self._logger.info(
            "[middleware] Creando ticket: titulo=%s cliente_id=%s org_id=%s payload=%s",
            payload.get("titulo"),
            session.user_id,
            session.organization_id,
            payload,
        )

        try:
            return self._broker_client.create_ticket(payload)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(f"No se pudo crear el ticket: {exc}") from exc

    def get_organization_tickets(
        self, organization_id: int, session: SessionContext
    ) -> dict[str, Any]:
        """Obtiene los tickets de una organización.

        Args:
            organization_id: ID de la organización
            session: Contexto de sesión del usuario

        Returns:
            {"tickets": [...], "total": int}
        """
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Consultando tickets org_id=%s user_id=%s",
            organization_id,
            session.user_id,
        )

        try:
            return self._broker_client.get_organization_tickets(organization_id)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudieron obtener los tickets: {exc}"
            ) from exc

    def get_ticket_detail(
        self, ticket_id: int, session: SessionContext
    ) -> dict[str, Any]:
        """Obtiene el detalle de un ticket específico."""
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Consultando ticket_id=%s user_id=%s",
            ticket_id,
            session.user_id,
        )

        try:
            return self._broker_client.get_ticket_detail(ticket_id)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(f"No se pudo obtener el ticket: {exc}") from exc

    def update_ticket(
        self, ticket_id: int, update_data: dict[str, Any], session: SessionContext
    ) -> dict[str, Any]:
        """Actualiza estado/prioridad de un ticket."""
        self._configure_broker_security(session)

        # Añadir user_id para registro de cambios
        update_data["user_id"] = session.user_id

        self._logger.info(
            "[middleware] Actualizando ticket_id=%s data=%s user_id=%s",
            ticket_id,
            update_data,
            session.user_id,
        )

        try:
            return self._broker_client.update_ticket(ticket_id, update_data)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudo actualizar el ticket: {exc}"
            ) from exc

    def add_ticket_response(
        self, ticket_id: int, respuesta: str, session: SessionContext
    ) -> dict[str, Any]:
        """Añade respuesta a un ticket."""
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Añadiendo respuesta a ticket_id=%s user_id=%s",
            ticket_id,
            session.user_id,
        )

        try:
            # Enviar user_id para registrar autor de la respuesta
            return self._broker_client.add_ticket_response(
                ticket_id, respuesta, user_id=session.user_id
            )
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(f"No se pudo añadir la respuesta: {exc}") from exc

    # ========================================================================
    # GESTIÓN DE TECNOLOGÍAS
    # ========================================================================

    def get_tecnologias(self, session: SessionContext) -> dict[str, Any]:
        """Obtiene todas las tecnologías disponibles."""
        self._configure_broker_security(session)

        self._logger.info("[middleware] Consultando tecnologías")

        try:
            return self._broker_client.get_tecnologias()
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(f"No se pudieron obtener tecnologías: {exc}") from exc

    def get_proyecto_tecnologia(
        self, project_id: int, session: SessionContext
    ) -> dict[str, Any]:
        """Obtiene la tecnología asignada a un proyecto."""
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Consultando tecnología de proyecto %s", project_id
        )

        try:
            return self._broker_client.get_proyecto_tecnologia(project_id)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudo obtener tecnología: {exc}"
            ) from exc

    def asignar_tecnologia(
        self, project_id: int, payload: dict[str, Any], session: SessionContext
    ) -> dict[str, Any]:
        """Asigna una tecnología a un proyecto (primera asignación)."""
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Asignando tecnología a proyecto %s user_id=%s",
            project_id,
            session.user_id,
        )

        try:
            return self._broker_client.asignar_tecnologia(project_id, payload)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(f"No se pudo asignar tecnología: {exc}") from exc

    def actualizar_tecnologia(
        self, project_id: int, payload: dict[str, Any], session: SessionContext
    ) -> dict[str, Any]:
        """Actualiza la tecnología de un proyecto (solo Backoffice)."""
        self._configure_broker_security(session)

        self._logger.info(
            "[middleware] Actualizando tecnología de proyecto %s user_id=%s",
            project_id,
            session.user_id,
        )

        try:
            return self._broker_client.actualizar_tecnologia(project_id, payload)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                f"No se pudo actualizar tecnología: {exc}"
            ) from exc

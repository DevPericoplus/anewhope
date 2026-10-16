"""Registro de instalaciones LAIM: verify HMAC + persistencia. Sin master_key."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.engine import Engine

MSG_SERIAL_INVALID = "El número de serie no es válido"
MSG_SERIAL_UNAVAILABLE = (
    "No se puede validar el número de serie ahora mismo. "
    "Inténtelo más tarde o abra un ticket de soporte."
)
MSG_SERIAL_TAKEN = "Este número de serie ya está registrado"
SERIAL_SIGNING_ENV = "LAIM_SERIAL_SIGNING_KEY"
MSG_USER_MISMATCH = "El usuario y el e-mail no corresponden a la misma cuenta"
MSG_USER_UNKNOWN = "No hay ninguna cuenta de laimweb con ese usuario y e-mail"
MSG_NOT_FOUND = "Instalación no encontrada"
MSG_HOSTNAME_OS = "El nombre de máquina y el sistema operativo son obligatorios"
MSG_IMMUTABLE = "El nombre de máquina y el número de serie no se pueden cambiar"
MSG_NOT_PENDING = "Esta instalación no está pendiente de reconocer"
MSG_REGISTER_BLOCKED = (
    "Se han superado los intentos de registro para este correo. "
    "Abra un ticket de soporte para desbloquear la cuenta."
)

VALID_OS = ("windows", "mac", "linux")
VALID_EDITIONS = ("community_edition", "advance")
# La UI pública solo muestra Community Edition. La columna edition y
# VALID_EDITIONS quedan listos para activar Advance (formulario extra:
# vigencia, plugins, cobro) sin otra migración de instalaciones.
ADVANCE_LICENSES_ENABLED = False
MAX_FAILED_REGISTER = 3


class InstallationsError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SigningKeyMissing(Exception):
    """No hay KeySerialSigning en laim_exchange_keys ni en LAIM_SERIAL_SIGNING_KEY."""


def resolve_serial_signing_key(db_value: str | None, env_value: str | None) -> str | None:
    """DB primero (rotación); env de vault si el entorno aún no tiene la fila."""
    for raw in (db_value, env_value):
        text = (raw or "").strip()
        if text:
            return text
    return None


class LaimInstallationsService:
    def __init__(
        self,
        engine: Engine | None = None,
        *,
        verify_serial: Callable[[str], bool] | None = None,
        user_repo: Any | None = None,
        installation_repo: Any | None = None,
        license_repo: Any | None = None,
    ) -> None:
        self._logger = logging.getLogger("LaimInstallationsService")
        if user_repo is not None and installation_repo is not None and verify_serial is not None:
            self._verify = verify_serial
            self._users = user_repo
            self._installs = installation_repo
            self._licenses = license_repo
            return
        self._wire_runtime(engine, verify_serial, user_repo, installation_repo, license_repo)

    def _wire_runtime(
        self,
        engine: Engine | None,
        verify_serial: Callable[[str], bool] | None,
        user_repo: Any | None,
        installation_repo: Any | None,
        license_repo: Any | None,
    ) -> None:
        import importlib.util
        import sys
        from pathlib import Path

        auth_path = Path(__file__).resolve().parent / "laim_auth_service.py"
        spec = importlib.util.spec_from_file_location("laim_auth_service_installations", auth_path)
        assert spec is not None and spec.loader is not None
        auth_mod = importlib.util.module_from_spec(spec)
        sys.modules["laim_auth_service_installations"] = auth_mod
        spec.loader.exec_module(auth_mod)
        users = user_repo or auth_mod.LaimAuthService()._user_repo
        db = engine or getattr(users, "_engine", None)
        if db is None:
            raise RuntimeError("LaimInstallationsService: no hay engine de laim_core_db")
        shared = Path(__file__).resolve().parents[2] / "2_shared_application"

        def _load(name: str, rel: str):
            path = shared / rel
            loaded = importlib.util.spec_from_file_location(name, path)
            assert loaded is not None and loaded.loader is not None
            mod = importlib.util.module_from_spec(loaded)
            sys.modules[name] = mod
            loaded.loader.exec_module(mod)
            return mod

        inst_mod = _load("laim_inst_repo_rt", "adapters/laim_installation_repository.py")
        lic_mod = _load("laim_lic_rt", "../1_shared_domain/entities/product_license.py")
        serial_mod = _load("laim_serial_rt", "security/laim_serial.py")
        keys_mod = _load("laim_exch_rt", "adapters/laim_exchange_key.py")
        self._users = users
        self._installs = installation_repo or inst_mod.LaimInstallationRepository(db)
        self._licenses = license_repo or lic_mod.ProductLicenseRepository(db)
        if verify_serial is not None:
            self._verify = verify_serial
            return
        keys = keys_mod.LaimExchangeKeyRepository(db)

        def _verify(serial: str) -> bool:
            row = keys.get_serial_signing_key()
            db_val = row.key_value if row is not None else None
            key = resolve_serial_signing_key(db_val, os.environ.get(SERIAL_SIGNING_ENV))
            if not key:
                self._logger.error(
                    "KeySerialSigning no está en laim_exchange_keys ni %s",
                    SERIAL_SIGNING_ENV,
                )
                raise SigningKeyMissing
            return serial_mod.verify_serial(serial, key)

        self._verify = _verify
        self._keys = keys

    def _serial_hmac(self, serial: str) -> str | None:
        """None = HMAC ok. Si falta la clave de firma, no se finge un serial inválido."""
        try:
            ok = bool(serial) and self._verify(serial)
        except SigningKeyMissing:
            return MSG_SERIAL_UNAVAILABLE
        if not ok:
            return MSG_SERIAL_INVALID
        return None

    def verify(self, serial_number: str, user_id: int | None = None) -> dict[str, Any]:
        email = self._email_of(user_id) if user_id else ""
        blocked = self._blocked(email)
        if blocked is not None:
            return {"success": True, "valid": False, "error": blocked["error"], "blocked": True}
        serial = (serial_number or "").strip()
        reason = self._serial_hmac(serial)
        if reason:
            # El blur de laimweb no es un intento de registro.
            return {"success": True, "valid": False, "error": reason}
        return {"success": True, "valid": True}

    def list_mine(self, user_id: int) -> dict[str, Any]:
        items = [row.as_public_dict() for row in self._installs.list_for_user(user_id)]
        blob = str(items)
        if "master_key" in blob or "user_password" in blob:
            raise RuntimeError("fuga de secretos en el listado de instalaciones")
        return {"success": True, "items": items}

    def list_pending_notifications(self, user_id: int) -> dict[str, Any]:
        return {"success": True, "items": self._installs.list_pending_notifications(user_id)}

    def ack_notification(self, user_id: int, notification_id: int) -> dict[str, Any]:
        ok = self._installs.ack_notification(notification_id, user_id)
        if not ok:
            return {"success": False, "error": MSG_NOT_FOUND}
        return {"success": True}

    def register_manual(
        self,
        user_id: int,
        serial_number: str,
        hostname: str,
        operating_system: str,
        edition: str = "community_edition",
        display_name: str = "",
    ) -> dict[str, Any]:
        email = self._email_of(user_id)
        blocked = self._blocked(email)
        if blocked is not None:
            return blocked
        serial = (serial_number or "").strip()
        host = (hostname or "").strip()
        os_name = (operating_system or "").strip()
        edition = self._public_edition(edition)
        hmac_error = self._serial_hmac(serial)
        if hmac_error == MSG_SERIAL_UNAVAILABLE:
            return {"success": False, "error": hmac_error}
        if hmac_error:
            return self._fail_attempt(email, hmac_error)
        if not host or os_name not in VALID_OS:
            return {"success": False, "error": MSG_HOSTNAME_OS}
        existing = self._installs.get_by_serial(serial)
        if existing is not None:
            return self._fail_attempt(email, MSG_SERIAL_TAKEN)
        row = self._installs.insert(
            serial_number=serial,
            user_id=user_id,
            hostname=host,
            display_name=display_name,
            operating_system=os_name,
            edition=edition,
            origin="manual",
            status="pending_recognition",
        )
        license_id = self._attach_license(serial, edition, user_id)
        self._installs.set_registered(row.installation_id, license_id, recognized=False)
        self._installs.insert_metric_event(
            installation_id=row.installation_id,
            user_id=user_id,
            operating_system=os_name,
            edition=edition,
            origin="manual",
        )
        self._installs.reset_register_attempts(email)
        item = self._installs.get_by_id(row.installation_id)
        assert item is not None
        public = item.as_public_dict()
        if "master_key" in str(public):
            raise RuntimeError("fuga de master_key")
        return {"success": True, "item": public}

    def propose_from_laim(
        self,
        user_name: str,
        user_email: str,
        serial_number: str,
        hostname: str,
        operating_system: str,
        edition: str = "community_edition",
        display_name: str = "",
    ) -> dict[str, Any]:
        email = (user_email or "").strip().lower()
        blocked = self._blocked(email)
        if blocked is not None:
            return blocked
        serial = (serial_number or "").strip()
        host = (hostname or "").strip()
        os_name = (operating_system or "").strip()
        edition = self._public_edition(edition)
        hmac_error = self._serial_hmac(serial)
        if hmac_error == MSG_SERIAL_UNAVAILABLE:
            return {"success": False, "error": hmac_error}
        if hmac_error:
            return self._fail_attempt(email, hmac_error)
        if not host or os_name not in VALID_OS:
            return {"success": False, "error": MSG_HOSTNAME_OS}
        user = self._match_portal_user(user_name, user_email)
        if isinstance(user, dict):
            return self._fail_attempt(email, str(user.get("error") or MSG_USER_UNKNOWN))
        existing = self._installs.get_by_serial(serial)
        if existing is not None:
            return self._fail_attempt(email, MSG_SERIAL_TAKEN)
        row = self._installs.insert(
            serial_number=serial,
            user_id=user.user_id,
            hostname=host,
            display_name=display_name,
            operating_system=os_name,
            edition=edition,
            origin="laim",
            status="pending_recognition",
        )
        self._installs.insert_notification(user.user_id, row.installation_id)
        self._installs.reset_register_attempts(email)
        return {"success": True, "item": row.as_public_dict()}

    def recognize(self, user_id: int, installation_id: int) -> dict[str, Any]:
        row = self._owned(user_id, installation_id)
        if row.status != "pending_recognition" or row.origin != "laim":
            return {"success": False, "error": MSG_NOT_PENDING}
        license_id = self._attach_license(row.serial_number, row.edition, user_id)
        self._installs.set_registered(row.installation_id, license_id, recognized=True)
        self._installs.insert_metric_event(
            installation_id=row.installation_id,
            user_id=user_id,
            operating_system=row.operating_system,
            edition=row.edition,
            origin=row.origin,
        )
        item = self._installs.get_by_id(row.installation_id)
        assert item is not None
        return {"success": True, "item": item.as_public_dict()}

    def reject(self, user_id: int, installation_id: int) -> dict[str, Any]:
        row = self._owned(user_id, installation_id)
        if row.status != "pending_recognition":
            return {"success": False, "error": MSG_NOT_PENDING}
        self._installs.delete(row.installation_id)
        return {"success": True}

    def update(
        self,
        user_id: int,
        installation_id: int,
        operating_system: str,
        edition: str,
        hostname: str | None = None,
        serial_number: str | None = None,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        row = self._owned(user_id, installation_id)
        if hostname is not None and hostname.strip() and hostname.strip() != row.hostname:
            return {"success": False, "error": MSG_IMMUTABLE}
        if serial_number is not None and serial_number.strip() and serial_number.strip() != row.serial_number:
            return {"success": False, "error": MSG_IMMUTABLE}
        os_name = (operating_system or row.operating_system).strip()
        edition = self._public_edition(edition or row.edition)
        if os_name not in VALID_OS:
            return {"success": False, "error": MSG_HOSTNAME_OS}
        alias = row.display_name if display_name is None else display_name
        self._installs.update_mutable(row.installation_id, os_name, edition, display_name=alias)
        item = self._installs.get_by_id(row.installation_id)
        assert item is not None
        return {"success": True, "item": item.as_public_dict()}

    def list_all(self, limit: int = 200) -> dict[str, Any]:
        items = [row.as_public_dict() for row in self._installs.list_all(limit)]
        blob = str(items)
        if "master_key" in blob or "user_password" in blob:
            raise RuntimeError("fuga de secretos en el listado de instalaciones")
        return {"success": True, "items": items}

    def metrics_dashboard(self) -> dict[str, Any]:
        """Agregados para el dashboard de laim_maintenance (y un futuro backoffice)."""
        events = self._installs.list_metric_events()
        now = datetime.now(timezone.utc)
        this_month = now.strftime("%Y-%m")
        buckets: dict[str, dict[str, int]] = {}
        totals = {"windows": 0, "mac": 0, "linux": 0}
        licenses = 0
        this_month_n = 0
        for ev in events:
            os_name = ev["operating_system"]
            if os_name not in totals:
                continue
            totals[os_name] += 1
            licenses += 1
            occurred = ev["occurred_at"]
            month = occurred.strftime("%Y-%m")
            bucket = buckets.setdefault(month, {"windows": 0, "mac": 0, "linux": 0, "total": 0})
            bucket[os_name] += 1
            bucket["total"] += 1
            if month == this_month:
                this_month_n += 1
        monthly: list[dict[str, Any]] = []
        cumulative = 0
        for month in sorted(buckets):
            row = buckets[month]
            cumulative += row["total"]
            monthly.append(
                {
                    "month": month,
                    "windows": row["windows"],
                    "mac": row["mac"],
                    "linux": row["linux"],
                    "total": row["total"],
                    "cumulative": cumulative,
                }
            )
        payload = {
            "success": True,
            "totals": {
                "registered": licenses,
                "windows": totals["windows"],
                "mac": totals["mac"],
                "linux": totals["linux"],
                "this_month": this_month_n,
                "licenses": licenses,
            },
            "monthly": monthly,
        }
        blob = str(payload)
        if "master_key" in blob or "user_password" in blob:
            raise RuntimeError("fuga de secretos en métricas de instalaciones")
        return payload

    def _owned(self, user_id: int, installation_id: int):
        row = self._installs.get_by_id(installation_id)
        if row is None or row.user_id != user_id:
            raise InstallationsError(MSG_NOT_FOUND)
        return row

    def _match_portal_user(self, user_name: str, user_email: str):
        name = (user_name or "").strip()
        email = (user_email or "").strip()
        by_name = self._users.get_user_by_name(name) if name else None
        by_email = self._users.get_user_by_email(email) if email else None
        if by_name is None or by_email is None:
            return {"success": False, "error": MSG_USER_UNKNOWN}
        if by_name.user_id != by_email.user_id:
            return {"success": False, "error": MSG_USER_MISMATCH}
        return by_name

    def _attach_license(self, serial: str, edition: str, user_id: int) -> int:
        if self._licenses is None:
            return 0
        lic = self._licenses.register(
            serial_number=serial,
            edition=edition,
            owner_type="user",
            owner_id=user_id,
        )
        return int(lic.license_id)

    def _public_edition(self, requested: str) -> str:
        if not ADVANCE_LICENSES_ENABLED:
            return "community_edition"
        edition = (requested or "community_edition").strip() or "community_edition"
        if edition not in VALID_EDITIONS:
            return "community_edition"
        return edition

    def _email_of(self, user_id: int | None) -> str:
        if not user_id:
            return ""
        user = self._users.get_user_by_id(user_id)
        if user is None:
            return ""
        return (user.user_email or "").strip().lower()

    def _blocked(self, email: str) -> dict[str, Any] | None:
        if not email:
            return None
        if self._installs.is_register_blocked(email):
            return {"success": False, "error": MSG_REGISTER_BLOCKED, "blocked": True}
        return None

    def _fail_attempt(self, email: str, reason: str) -> dict[str, Any]:
        if not email:
            return {"success": False, "error": reason}
        count = self._installs.record_failed_attempt(email, reason)
        if count >= MAX_FAILED_REGISTER:
            self._installs.block_register(email)
            return {"success": False, "error": MSG_REGISTER_BLOCKED, "blocked": True}
        return {"success": False, "error": reason}

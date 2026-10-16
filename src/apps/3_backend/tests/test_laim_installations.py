"""Registro de instalaciones contra esquema 030 + VerifySerial real."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, event, text

_BACKEND = Path(__file__).resolve().parents[1]
_SHARED = Path(__file__).resolve().parents[3] / "2_shared_application"
_SERIAL = _SHARED / "security" / "laim_serial.py"
_INST_REPO = _SHARED / "adapters" / "laim_installation_repository.py"
_USER_REPO = _SHARED / "adapters" / "laim_user_repository.py"
_LIC_PATH = Path(__file__).resolve().parents[3] / "1_shared_domain" / "entities" / "product_license.py"
_SVC = _BACKEND / "laim_installations_service.py"
_MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "infrastructure"
    / "database"
    / "migrations"
    / "030_laim_installations.sql"
)
_VERSION_GO = Path("/Users/perico/develop/laim/internal/utils/version.go")
_IDENTITY_GO = Path("/Users/perico/develop/laim/internal/utils/identity_dat.go")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_MIGRATION_031 = (
    Path(__file__).resolve().parents[4]
    / "infrastructure"
    / "database"
    / "migrations"
    / "031_laim_installation_metrics.sql"
)


def test_migration_030_declares_installations_and_serial_key_kind() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    assert "laim_installations" in sql
    assert "`serial_number`" in sql
    assert "`hostname`" in sql
    assert "`operating_system`" in sql
    assert "pending_recognition" in sql
    assert "key_kind" in sql
    assert "serial_signing" in sql
    ident = _IDENTITY_GO.read_text(encoding="utf-8")
    assert "master_key_cipher" in ident
    assert "master_key_cipher" not in sql


def test_migration_031_declares_alias_guards_notifications_and_metrics() -> None:
    sql = _MIGRATION_031.read_text(encoding="utf-8")
    assert "`display_name`" in sql
    assert "laim_installation_register_guards" in sql
    assert "`user_email`" in sql
    assert "laim_installation_notifications" in sql
    assert "laim_installation_metric_events" in sql
    assert "ticket de soporte" in (
        Path(__file__).resolve().parents[1] / "laim_installations_service.py"
    ).read_text(encoding="utf-8")


_SCHEMA = """
CREATE TABLE laim_organizations (
    organization_id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_name TEXT NOT NULL,
    organization_email TEXT NOT NULL DEFAULT 'org@laim.test',
    active INTEGER DEFAULT 1
);
CREATE TABLE laim_identity_types (
    identity_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    identity_type_name TEXT NOT NULL,
    identity_type_rol TEXT NOT NULL
);
CREATE TABLE laim_users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    identity_type_id INTEGER NOT NULL,
    user_name TEXT NOT NULL UNIQUE,
    user_password TEXT NOT NULL,
    user_email TEXT NOT NULL,
    user_mobile TEXT,
    user_otp TEXT,
    active INTEGER DEFAULT 1,
    blocked INTEGER DEFAULT 0
);
CREATE TABLE laim_user_contact_info (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    sur_name TEXT
);
CREATE TABLE laim_product_licenses (
    license_id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_number TEXT NOT NULL UNIQUE,
    edition TEXT NOT NULL,
    status TEXT NOT NULL,
    owner_type TEXT NOT NULL,
    owner_id INTEGER NOT NULL,
    fecha_inicio TEXT,
    fecha_fin TEXT,
    registered_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE laim_product_license_plugins (
    entitlement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL,
    plugin_name TEXT NOT NULL,
    fecha_inicio TEXT,
    fecha_fin TEXT
);
CREATE TABLE laim_installations (
    installation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_number TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    hostname TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    operating_system TEXT NOT NULL,
    edition TEXT NOT NULL DEFAULT 'community_edition',
    origin TEXT NOT NULL,
    status TEXT NOT NULL,
    license_id INTEGER,
    proposed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    registered_at TEXT,
    recognized_at TEXT,
    rejected_at TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE laim_installation_register_guards (
    user_email TEXT PRIMARY KEY,
    fail_count INTEGER NOT NULL DEFAULT 0,
    blocked_at TEXT,
    last_reason TEXT NOT NULL DEFAULT '',
    last_fail_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE laim_installation_notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    installation_id INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    acked_at TEXT,
    FOREIGN KEY (installation_id) REFERENCES laim_installations (installation_id) ON DELETE CASCADE
);
CREATE TABLE laim_installation_metric_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    installation_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    operating_system TEXT NOT NULL,
    edition TEXT NOT NULL,
    origin TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'registered',
    occurred_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE laim_exchange_keys (
    key_id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_version TEXT NOT NULL,
    key_kind TEXT NOT NULL DEFAULT 'exchange',
    key_value_cipher TEXT NOT NULL,
    valid_from TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until TEXT
);
"""


def _engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _connection_record):  # noqa: ANN001
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    with engine.begin() as conn:
        for statement in _SCHEMA.split(";"):
            sql = statement.strip()
            if sql:
                conn.execute(text(sql))
        conn.execute(text("INSERT INTO laim_organizations (organization_name) VALUES ('laim')"))
        conn.execute(
            text(
                "INSERT INTO laim_identity_types "
                "(identity_type_id, identity_type_name, identity_type_rol) "
                "VALUES (4, 'Lector', 'lector')"
            )
        )
    return engine


def _svc():
    engine = _engine()
    serial_mod = _load("laim_serial_inst", _SERIAL)
    users = _load("laim_user_repo_inst", _USER_REPO).LaimUserRepository(engine)
    installs = _load("laim_inst_repo", _INST_REPO).LaimInstallationRepository(engine)
    licenses = _load("laim_lic_inst", _LIC_PATH).ProductLicenseRepository(engine)
    svc_mod = _load("laim_inst_svc", _SVC)
    key = serial_mod.key_serial_signing_from_laim_repo(_VERSION_GO.read_text(encoding="utf-8"))

    def verify(s: str) -> bool:
        return serial_mod.verify_serial(s, key)

    svc = svc_mod.LaimInstallationsService(
        engine,
        verify_serial=verify,
        user_repo=users,
        installation_repo=installs,
        license_repo=licenses,
    )
    return svc_mod, svc, users, serial_mod, key, engine


def _user(users, name="ana", email="ana@laim.example"):
    return users.create_user(
        organization_id=1,
        identity_type_id=4,
        user_name=name,
        encrypted_password="x",
        user_email=email,
        user_mobile=None,
        first_name=name.title(),
        sur_name="Laim",
    )


def test_verify_ok_and_ko_with_real_hmac() -> None:
    _mod, svc, _users, serial_mod, key, _engine = _svc()
    good = serial_mod.generate_serial(key)
    assert svc.verify(good)["valid"] is True
    assert svc.verify("2-AAAA-AAAA-AAAA-AAAAAAA-AAAAAAA")["valid"] is False
    assert svc.verify("2-AAAA-AAAA-AAAA-AAAAAAA-AAAAAAA")["error"]


def test_resolve_serial_signing_key_prefers_db_then_env_then_product() -> None:
    _mod, *_rest = _svc()
    assert _mod.resolve_serial_signing_key(" db ", "env", "prod") == "db"
    assert _mod.resolve_serial_signing_key(None, " env-key ", "prod") == "env-key"
    assert _mod.resolve_serial_signing_key("", "", " product ") == "product"
    assert _mod.resolve_serial_signing_key(None, None, None) is None
    assert _mod.SERIAL_SIGNING_ENV == "LAIM_SERIAL_SIGNING_KEY"
    assert _mod.resolve_exchange_key(" db-ex ", "prod-ex") == "db-ex"
    assert _mod.resolve_exchange_key(None, " prod-ex ") == "prod-ex"
    assert _mod.resolve_exchange_key("", None) is None


def test_load_install_register_keys_falls_back_to_product_and_seeds_signing() -> None:
    """propose no puede exigir fila DB: el verify ya usa constante de producto."""
    _mod, _svc_obj, _users, serial_mod, _key, engine = _svc()
    keys_mod = _load("laim_exch_propose", _SHARED / "adapters" / "laim_exchange_key.py")
    keys = keys_mod.LaimExchangeKeyRepository(engine)
    assert keys.get_current_key("2", key_kind="exchange") is None
    assert keys.get_serial_signing_key() is None
    pair = _mod.load_install_register_keys(
        keys,
        "2",
        env_signing="",
        product_exchange=serial_mod.product_exchange_key(),
        product_signing=serial_mod.product_serial_signing_key(),
    )
    assert pair is not None
    exchange, signing = pair
    assert exchange == serial_mod.product_exchange_key()
    assert signing == serial_mod.product_serial_signing_key()
    seeded = keys.get_serial_signing_key()
    assert seeded is not None
    assert seeded.key_value == signing


def test_load_install_register_keys_prefers_db_over_product() -> None:
    _mod, _svc_obj, _users, serial_mod, _key, engine = _svc()
    keys_mod = _load("laim_exch_propose_db", _SHARED / "adapters" / "laim_exchange_key.py")
    keys = keys_mod.LaimExchangeKeyRepository(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO laim_exchange_keys (major_version, key_kind, key_value_cipher) "
                "VALUES ('2', 'exchange', 'db-exchange='), ('2', 'serial_signing', 'db-signing=')"
            )
        )
    pair = _mod.load_install_register_keys(
        keys,
        "2",
        env_signing="env-signing=",
        product_exchange=serial_mod.product_exchange_key(),
        product_signing=serial_mod.product_serial_signing_key(),
    )
    assert pair == ("db-exchange=", "db-signing=")


def test_live_verify_does_not_count_as_register_attempt() -> None:
    """El blur de laimweb no es un intento de registro: no debe bloquear."""
    _mod, svc, users, serial_mod, key, _e = _svc()
    uid = _user(users)
    bogus = "2-AAAA-AAAA-AAAA-AAAAAAA-AAAAAAA"
    for _ in range(5):
        got = svc.verify(bogus, user_id=uid)
        assert got["valid"] is False
        assert got.get("blocked") is not True
        assert "válido" in got["error"]
    serial = serial_mod.generate_serial(key)
    saved = svc.register_manual(uid, serial, "silicon.local", "windows")
    assert saved["success"] is True
    assert saved["item"]["hostname"] == "silicon.local"


def test_missing_signing_key_is_not_invalid_serial_and_does_not_block() -> None:
    _mod, svc, users, serial_mod, key, _e = _svc()
    uid = _user(users)

    def missing(_serial: str) -> bool:
        raise _mod.SigningKeyMissing

    svc._verify = missing
    serial = serial_mod.generate_serial(key)
    checked = svc.verify(serial, user_id=uid)
    assert checked["valid"] is False
    assert checked["error"] == _mod.MSG_SERIAL_UNAVAILABLE
    assert "no es válido" not in checked["error"]
    denied = svc.register_manual(uid, serial, "silicon.local", "windows")
    assert denied["success"] is False
    assert denied["error"] == _mod.MSG_SERIAL_UNAVAILABLE
    assert denied.get("blocked") is not True
    svc._verify = lambda value: serial_mod.verify_serial(value, key)
    ok = svc.register_manual(uid, serial, "silicon.local", "windows")
    assert ok["success"] is True


def test_manual_register_persists_identity_fields_not_master_key() -> None:
    _mod, svc, users, serial_mod, key, engine = _svc()
    uid = _user(users)
    serial = serial_mod.generate_serial(key)
    saved = svc.register_manual(
        uid, serial, "macbook-ana", "mac", "community_edition"
    )
    assert saved["success"] is True
    item = saved["item"]
    assert item["serial_number"] == serial
    assert item["hostname"] == "macbook-ana"
    assert item["operating_system"] == "mac"
    assert item["status"] == "registered"
    assert item["origin"] == "manual"
    assert item["registered_at"]
    blob = json.dumps(saved)
    assert "master_key" not in blob
    listed = svc.list_mine(uid)
    assert [r["serial_number"] for r in listed["items"]] == [serial]
    with engine.connect() as conn:
        lic = conn.execute(text("SELECT status, owner_id FROM laim_product_licenses")).mappings().fetchone()
    assert lic["status"] == "FREE"
    assert int(lic["owner_id"]) == uid


def test_manual_rejects_invalid_or_taken_serial() -> None:
    _mod, svc, users, serial_mod, key, _e = _svc()
    uid = _user(users)
    assert svc.register_manual(uid, "no-es-un-serial", "h", "mac")["success"] is False
    serial = serial_mod.generate_serial(key)
    assert svc.register_manual(uid, serial, "h1", "linux")["success"] is True
    other = _user(users, "bruno", "bruno@laim.example")
    taken = svc.register_manual(other, serial, "h2", "linux")
    assert taken["success"] is False
    assert "ya está registrado" in taken["error"]


def test_update_cannot_change_hostname_or_serial() -> None:
    _mod, svc, users, serial_mod, key, _e = _svc()
    uid = _user(users)
    serial = serial_mod.generate_serial(key)
    item = svc.register_manual(uid, serial, "host-a", "mac")["item"]
    iid = item["installation_id"]
    blocked = svc.update(uid, iid, "linux", "community_edition", hostname="otro")
    assert blocked["success"] is False
    ok = svc.update(uid, iid, "linux", "community_edition")
    assert ok["success"] is True
    assert ok["item"]["hostname"] == "host-a"
    assert ok["item"]["serial_number"] == serial
    assert ok["item"]["operating_system"] == "linux"


def test_propose_from_laim_requires_matching_user_then_recognize_or_reject() -> None:
    _mod, svc, users, serial_mod, key, engine = _svc()
    uid = _user(users)
    _user(users, "bruno", "bruno@laim.example")
    serial = serial_mod.generate_serial(key)
    mismatch = svc.propose_from_laim("ana", "bruno@laim.example", serial, "box", "linux")
    assert mismatch["success"] is False
    unknown = svc.propose_from_laim("nadie", "nadie@laim.example", serial, "box", "linux")
    assert unknown["success"] is False
    pending = svc.propose_from_laim("ana", "ana@laim.example", serial, "box", "linux")
    assert pending["success"] is True
    assert pending["item"]["status"] == "pending_recognition"
    assert pending["item"]["origin"] == "laim"
    iid = pending["item"]["installation_id"]
    other = users.get_user_by_name("bruno").user_id
    try:
        svc.recognize(other, iid)
        raise AssertionError("no debe reconocer la de otro")
    except Exception as exc:
        assert "no encontrada" in str(exc).lower() or "encontrada" in str(exc).lower()
    ok = svc.recognize(uid, iid)
    assert ok["success"] is True
    assert ok["item"]["status"] == "registered"
    assert ok["item"]["recognized_at"]
    with engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) AS c FROM laim_product_licenses")).mappings().fetchone()
    assert int(n["c"]) == 1
    serial2 = serial_mod.generate_serial(key)
    pend2 = svc.propose_from_laim("ana", "ana@laim.example", serial2, "box2", "mac")
    iid2 = pend2["item"]["installation_id"]
    svc.reject(uid, iid2)
    gone = svc.list_mine(uid)
    assert serial2 not in [r["serial_number"] for r in gone["items"]]


def test_alias_is_mutable_hostname_stays_immutable() -> None:
    _mod, svc, users, serial_mod, key, _e = _svc()
    uid = _user(users)
    serial = serial_mod.generate_serial(key)
    item = svc.register_manual(
        uid, serial, "host-a", "mac", display_name="Portátil de Ana"
    )["item"]
    assert item["display_name"] == "Portátil de Ana"
    assert item["hostname"] == "host-a"
    iid = item["installation_id"]
    blocked = svc.update(uid, iid, "linux", "community_edition", hostname="otro")
    assert blocked["success"] is False
    ok = svc.update(uid, iid, "linux", "community_edition", display_name="Mac de casa")
    assert ok["item"]["display_name"] == "Mac de casa"
    assert ok["item"]["hostname"] == "host-a"


def test_public_register_forces_community_edition_while_advance_flag_off() -> None:
    _mod, svc, users, serial_mod, key, _e = _svc()
    uid = _user(users)
    serial = serial_mod.generate_serial(key)
    item = svc.register_manual(uid, serial, "box", "linux", edition="advance")["item"]
    assert item["edition"] == "community_edition"
    assert _mod.ADVANCE_LICENSES_ENABLED is False
    assert "advance" in _mod.VALID_EDITIONS


def test_three_failed_attempts_per_email_block_and_recommend_ticket() -> None:
    _mod, svc, users, serial_mod, key, _e = _svc()
    uid = _user(users)
    first = svc.register_manual(uid, "no-es-un-serial", "h", "mac")
    assert first["success"] is False
    assert "válido" in first["error"]
    svc.register_manual(uid, "no-es-un-serial", "h", "mac")
    third = svc.register_manual(uid, "no-es-un-serial", "h", "mac")
    assert third["success"] is False
    assert third.get("blocked") is True
    assert "ticket de soporte" in third["error"].lower()
    good = serial_mod.generate_serial(key)
    blocked = svc.register_manual(uid, good, "h", "mac")
    assert blocked.get("blocked") is True
    verify = svc.verify(good, user_id=uid)
    assert verify["valid"] is False
    assert "ticket de soporte" in verify["error"].lower()


def test_successful_register_resets_failed_attempts() -> None:
    _mod, svc, users, serial_mod, key, _e = _svc()
    uid = _user(users)
    svc.register_manual(uid, "no-es-un-serial", "h", "mac")
    svc.register_manual(uid, "no-es-un-serial", "h", "mac")
    serial = serial_mod.generate_serial(key)
    ok = svc.register_manual(uid, serial, "h", "linux")
    assert ok["success"] is True
    other = serial_mod.generate_serial(key)
    again = svc.register_manual(uid, other, "h2", "linux")
    assert again["success"] is True


def test_propose_creates_notification_poll_does_not_ack() -> None:
    _mod, svc, users, serial_mod, key, _e = _svc()
    uid = _user(users)
    serial = serial_mod.generate_serial(key)
    pending = svc.propose_from_laim("ana", "ana@laim.example", serial, "box", "linux")
    iid = pending["item"]["installation_id"]
    notes = svc.list_pending_notifications(uid)
    assert notes["success"] is True
    assert len(notes["items"]) == 1
    assert notes["items"][0]["installation_id"] == iid
    again = svc.list_pending_notifications(uid)
    assert len(again["items"]) == 1
    ack = svc.ack_notification(uid, notes["items"][0]["id"])
    assert ack["success"] is True
    empty = svc.list_pending_notifications(uid)
    assert empty["items"] == []


def test_metrics_snapshot_os_at_register_and_monthly_totals() -> None:
    _mod, svc, users, serial_mod, key, _e = _svc()
    uid = _user(users)
    for os_name in ("windows", "mac", "linux", "mac"):
        serial = serial_mod.generate_serial(key)
        assert svc.register_manual(uid, serial, f"h-{os_name}", os_name)["success"]
    dash = svc.metrics_dashboard()
    assert dash["totals"]["registered"] == 4
    assert dash["totals"]["licenses"] == 4
    assert dash["totals"]["windows"] == 1
    assert dash["totals"]["mac"] == 2
    assert dash["totals"]["linux"] == 1
    assert dash["totals"]["this_month"] == 4
    assert dash["monthly"]
    last = dash["monthly"][-1]
    assert last["total"] == 4
    assert last["cumulative"] == 4
    assert last["mac"] == 2
    blob = json.dumps(dash)
    assert "master_key" not in blob
    assert "user_password" not in blob


def test_ack_from_laim_reports_status() -> None:
    _mod, svc, users, serial_mod, key, _e = _svc()
    uid = _user(users)
    serial = serial_mod.generate_serial(key)
    unknown = svc.ack_from_laim(serial)
    assert unknown["success"] is True
    assert unknown["registered"] is False
    assert unknown["status"] == "unknown"
    pending = svc.propose_from_laim("ana", "ana@laim.example", serial, "box", "linux")
    assert pending["success"] is True
    mid = svc.ack_from_laim(serial)
    assert mid["registered"] is False
    assert mid["status"] == "pending_recognition"
    iid = pending["item"]["installation_id"]
    assert svc.recognize(uid, iid)["success"] is True
    done = svc.ack_from_laim(serial)
    assert done["registered"] is True
    assert done["status"] == "registered"
    blob = str(done)
    assert "master_key" not in blob
    assert "user_email" not in blob

"""Gestión de cuentas laimweb contra el esquema real de 012 y Fernet."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, event, text

_BACKEND = Path(__file__).resolve().parents[1]
_SHARED = Path(__file__).resolve().parents[3] / "2_shared_application"
_REPO_PATH = _SHARED / "adapters" / "laim_user_repository.py"
_CRYPTO_PATH = _SHARED / "security" / "laim_password_crypto.py"
_SVC_PATH = _BACKEND / "laim_users_ops_service.py"
_SCHEMA_012 = (
    Path(__file__).resolve().parents[4]
    / "infrastructure"
    / "database"
    / "migrations"
    / "012_laim_core_db_schema.sql"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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
CREATE TABLE laim_auth_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    user_name TEXT,
    event TEXT NOT NULL,
    status TEXT NOT NULL,
    ip_address TEXT,
    session_id TEXT,
    user_agent TEXT,
    details TEXT
);
"""


def test_schema_012_declares_real_user_columns() -> None:
    sql = _SCHEMA_012.read_text(encoding="utf-8")
    table = sql.split("CREATE TABLE IF NOT EXISTS `laim_users`", 1)[1].split(
        "CREATE TABLE IF NOT EXISTS", 1
    )[0]
    for col in (
        "`user_id`",
        "`user_name`",
        "`user_email`",
        "`user_mobile`",
        "`user_password`",
    ):
        assert col in table
    assert "UNIQUE KEY `user_name`" in table
    contact = sql.split("CREATE TABLE IF NOT EXISTS `laim_user_contact_info`", 1)[1].split(
        "CREATE TABLE IF NOT EXISTS", 1
    )[0]
    assert "`first_name`" in contact
    assert "`sur_name`" in contact


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
    repo_mod = _load("laim_user_repository_users_ops", _REPO_PATH)
    crypto = _load("laim_password_crypto_users_ops", _CRYPTO_PATH)
    svc_mod = _load("laim_users_ops_service_test", _SVC_PATH)
    repo = repo_mod.LaimUserRepository(engine)
    return svc_mod, svc_mod.LaimUsersOpsService(user_repo=repo), repo, crypto


def _create(repo, crypto, name, email, mobile=None, full="Ana Laim"):
    first, _, sur = full.partition(" ")
    return repo.create_user(
        organization_id=1,
        identity_type_id=4,
        user_name=name,
        encrypted_password=crypto.encrypt_password("ClaveValida1"),
        user_email=email,
        user_mobile=mobile,
        first_name=first or None,
        sur_name=sur or None,
    )


def test_list_orders_by_id_filters_name_or_email_and_omits_password() -> None:
    _mod, svc, repo, crypto = _svc()
    _create(repo, crypto, "ana", "ana@laim.example", "+34600111222", "Ana Laim")
    _create(repo, crypto, "bruno", "bruno@laim.example", None, "Bruno Laim")
    listed = svc.list_users("")
    assert listed["success"] is True
    ids = [row["user_id"] for row in listed["items"]]
    assert ids == sorted(ids)
    blob = json.dumps(listed)
    assert "user_password" not in blob
    assert "ClaveValida1" not in blob
    by_name = svc.list_users("bru")
    assert [r["user_name"] for r in by_name["items"]] == ["bruno"]
    by_mail = svc.list_users("ana@laim.example")
    assert [r["user_email"] for r in by_mail["items"]] == ["ana@laim.example"]
    assert by_mail["items"][0]["user_mobile"] == "+34600111222"


def test_get_detail_matches_alta_fields_without_password() -> None:
    _mod, svc, repo, crypto = _svc()
    user_id = _create(repo, crypto, "ana", "ana@laim.example", "+34600111222", "Ana Laim")
    detail = svc.get_user(user_id)
    assert detail["success"] is True
    item = detail["item"]
    assert item["user_id"] == user_id
    assert item["user_name"] == "ana"
    assert item["user_email"] == "ana@laim.example"
    assert item["user_mobile"] == "+34600111222"
    assert item["full_name"] == "Ana Laim"
    assert "user_password" not in item
    assert "password" not in item


def test_update_profile_rejects_duplicate_username_and_email() -> None:
    _mod, svc, repo, crypto = _svc()
    ana = _create(repo, crypto, "ana", "ana@laim.example")
    _create(repo, crypto, "bruno", "bruno@laim.example")
    taken_name = svc.update_profile(
        ana, user_name="bruno", user_email="ana@laim.example", user_mobile="", full_name="Ana Laim"
    )
    assert taken_name["success"] is False
    assert "usuario" in taken_name["error"].lower()
    taken_mail = svc.update_profile(
        ana, user_name="ana", user_email="bruno@laim.example", user_mobile="", full_name="Ana Laim"
    )
    assert taken_mail["success"] is False
    assert "e-mail" in taken_mail["error"].lower() or "email" in taken_mail["error"].lower()
    still = repo.get_user_by_id(ana)
    assert still.user_name == "ana"
    assert still.user_email == "ana@laim.example"


def test_update_profile_allows_retry_with_free_values() -> None:
    _mod, svc, repo, crypto = _svc()
    ana = _create(repo, crypto, "ana", "ana@laim.example", "+34600", "Ana Laim")
    ok = svc.update_profile(
        ana,
        user_name="ana2",
        user_email="ana2@laim.example",
        user_mobile="+34699",
        full_name="Ana Dos",
    )
    assert ok["success"] is True
    item = ok["item"]
    assert item["user_name"] == "ana2"
    assert item["user_email"] == "ana2@laim.example"
    assert item["user_mobile"] == "+34699"
    assert item["full_name"] == "Ana Dos"
    assert "user_password" not in item


def test_update_password_uses_real_fernet_like_register() -> None:
    _mod, svc, repo, crypto = _svc()
    user_id = _create(repo, crypto, "ana", "ana@laim.example")
    short = svc.update_password(user_id, "corta", "corta")
    assert short["success"] is False
    mismatch = svc.update_password(user_id, "NuevaClave9", "OtraClave9")
    assert mismatch["success"] is False
    ok = svc.update_password(user_id, "NuevaClave9", "NuevaClave9")
    assert ok["success"] is True
    assert "éxito" in ok["message"].lower() or "exito" in ok["message"].lower()
    user = repo.get_user_by_id(user_id)
    assert crypto.decrypt_password(user.user_password) == "NuevaClave9"
    assert "NuevaClave9" not in user.user_password
    assert "user_password" not in json.dumps(ok)

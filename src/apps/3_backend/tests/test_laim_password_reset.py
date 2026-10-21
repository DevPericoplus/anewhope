"""Recuperación de contraseña contra el esquema real y Fernet de verdad."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text

_BACKEND = Path(__file__).resolve().parents[1]
_SHARED = Path(__file__).resolve().parents[3] / "2_shared_application"
_REPO_PATH = _SHARED / "adapters" / "laim_user_repository.py"
_SERVICE_PATH = _BACKEND / "laim_auth_service.py"
_CRYPTO_PATH = _SHARED / "security" / "laim_password_crypto.py"


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
CREATE TABLE laim_password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    request_ip TEXT,
    FOREIGN KEY (user_id) REFERENCES laim_users (user_id)
);
"""


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _connection_record):  # noqa: ANN001
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    with engine.begin() as conn:
        for statement in _SCHEMA.split(";"):
            sql = statement.strip()
            if sql:
                conn.execute(text(sql))
        conn.execute(
            text(
                "INSERT INTO laim_organizations (organization_name) VALUES ('laim')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO laim_identity_types "
                "(identity_type_id, identity_type_name, identity_type_rol) "
                "VALUES (4, 'Lector', 'lector')"
            )
        )
    return engine


@pytest.fixture
def repo(engine):
    module = _load("laim_user_repository_reset_test", _REPO_PATH)
    return module, module.LaimUserRepository(engine)


@pytest.fixture
def crypto():
    return _load("laim_password_crypto_reset_test", _CRYPTO_PATH)


@pytest.fixture
def service(repo):
    _repo_mod, user_repo = repo
    svc_mod = _load("laim_auth_service_reset_test", _SERVICE_PATH)
    return svc_mod, svc_mod.LaimAuthService(user_repo=user_repo)


def _create_user(repo_mod, user_repo, crypto, email="ana@laim.example"):
    encrypted = crypto.encrypt_password("ClaveValida1")
    user_id = user_repo.create_user(
        organization_id=1,
        identity_type_id=4,
        user_name="ana",
        encrypted_password=encrypted,
        user_email=email,
        user_mobile=None,
        first_name="Ana",
        sur_name="Laim",
    )
    return user_id


def test_request_unknown_email_does_not_mint_token(service, repo) -> None:
    svc_mod, auth = service
    _repo_mod, user_repo = repo
    result = auth.request_password_reset("nadie@laim.example")
    assert result["accepted"] is True
    assert result["found"] is False
    assert "token" not in result
    with user_repo._engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) AS n FROM laim_password_reset_tokens")
        ).mappings().fetchone()
    assert int(total["n"]) == 0


def test_request_blocked_user_skips_mail_and_logs(service, repo, crypto) -> None:
    _svc_mod, auth = service
    repo_mod, user_repo = repo
    _create_user(repo_mod, user_repo, crypto)
    user_repo.set_user_blocked("ana", True)
    result = auth.request_password_reset("ana@laim.example", ip_address="10.0.0.8")
    assert result["accepted"] is True
    assert result["found"] is False
    assert "token" not in result
    with user_repo._engine.connect() as conn:
        tokens = conn.execute(
            text("SELECT COUNT(*) AS n FROM laim_password_reset_tokens")
        ).mappings().fetchone()
        log = conn.execute(
            text(
                "SELECT event, status, details FROM laim_auth_logs "
                "WHERE user_name = 'ana' ORDER BY id DESC LIMIT 1"
            )
        ).mappings().fetchone()
    assert int(tokens["n"]) == 0
    assert log["event"] == "login_blocked"
    assert log["status"] == "blocked"
    assert "password_reset_skipped" in log["details"]


def test_request_existing_user_returns_raw_once_and_stores_hash(
    service, repo, crypto
) -> None:
    svc_mod, auth = service
    repo_mod, user_repo = repo
    _create_user(repo_mod, user_repo, crypto)
    result = auth.request_password_reset("ana@laim.example", ip_address="127.0.0.1")
    assert result["found"] is True
    assert result["user_name"] == "ana"
    raw = result["token"]
    assert raw and raw != repo_mod.hash_reset_token(raw)
    stored = user_repo.get_reset_token_by_hash(repo_mod.hash_reset_token(raw))
    assert stored is not None
    assert stored.token_hash == repo_mod.hash_reset_token(raw)
    assert stored.token_hash != raw


def test_confirm_updates_fernet_and_audits_without_secrets(
    service, repo, crypto
) -> None:
    _svc_mod, auth = service
    repo_mod, user_repo = repo
    user_id = _create_user(repo_mod, user_repo, crypto)
    minted = auth.request_password_reset("ana@laim.example")
    raw = minted["token"]
    new_password = "NuevaClave9"
    result = auth.confirm_password_reset(raw, new_password, new_password)
    assert result["success"] is True
    user = user_repo.get_user_by_id(user_id)
    assert crypto.decrypt_password(user.user_password) == new_password
    assert new_password not in user.user_password
    with user_repo._engine.connect() as conn:
        log = conn.execute(
            text(
                "SELECT event, details FROM laim_auth_logs "
                "WHERE event = 'password_change' ORDER BY id DESC LIMIT 1"
            )
        ).mappings().fetchone()
    assert log is not None
    details = json.loads(log["details"])
    blob = json.dumps(details) + raw
    assert details["action"] == "password_reset"
    assert details["user_id"] == user_id
    assert new_password not in blob
    assert "ClaveValida1" not in blob
    reused = auth.confirm_password_reset(raw, "OtraClave88", "OtraClave88")
    assert reused["success"] is False
    assert auth.password_reset_status(raw)["reason"] == "used"


def test_confirm_rejects_mismatch_and_expired(service, repo, crypto) -> None:
    _svc_mod, auth = service
    repo_mod, user_repo = repo
    user_id = _create_user(repo_mod, user_repo, crypto)
    minted = auth.request_password_reset("ana@laim.example")
    raw = minted["token"]
    mismatch = auth.confirm_password_reset(raw, "NuevaClave9", "OtraClave9")
    assert mismatch["success"] is False
    user = user_repo.get_user_by_id(user_id)
    assert crypto.decrypt_password(user.user_password) == "ClaveValida1"
    expired_raw = "token-caducado-urlsafe-32bytes-xxxx"
    user_repo.create_password_reset_token(
        user_id=user_id,
        token_hash=repo_mod.hash_reset_token(expired_raw),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    status = auth.password_reset_status(expired_raw)
    assert status["valid"] is False
    assert status["reason"] == "expired"
    expired = auth.confirm_password_reset(expired_raw, "NuevaClave9", "NuevaClave9")
    assert expired["success"] is False

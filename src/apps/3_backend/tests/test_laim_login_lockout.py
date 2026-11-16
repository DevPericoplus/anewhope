"""Login LAIM: cada clave errónea queda en laim_auth_logs y la quinta bloquea.

Regla (usuario, 2026-11-16): 5 fallos de contraseña consecutivos desde el
último reinicio (login correcto, bloqueo/desbloqueo del operador o cambio de
clave) bloquean la cuenta. Sin ventana de tiempo que el atacante pueda esperar.
Esquema real de laim_auth_logs (mismas columnas que 012/000) y Fernet de verdad.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

_BACKEND = Path(__file__).resolve().parents[1]
_SHARED = Path(__file__).resolve().parents[3] / "2_shared_application"
_REPO_PATH = _SHARED / "adapters" / "laim_user_repository.py"
_SERVICE_PATH = _BACKEND / "laim_auth_service.py"
_OPS_PATH = _BACKEND / "laim_users_ops_service.py"
_CRYPTO_PATH = _SHARED / "security" / "laim_password_crypto.py"

GOOD = "ClaveValida1"
BAD = "ClaveMala99"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_SCHEMA = """
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
    event TEXT NOT NULL CHECK (event IN ('login_success','login_failed','logout',
        'password_change','otp_verification','token_refresh','permission_denied',
        'login_attempt','login_blocked','otp_request')),
    status TEXT NOT NULL CHECK (status IN ('success','failure','failed','blocked')),
    ip_address TEXT,
    session_id TEXT,
    user_agent TEXT,
    details TEXT
);
"""


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


@pytest.fixture
def env():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        for statement in _SCHEMA.split(";"):
            if statement.strip():
                conn.execute(text(statement.strip()))
    repo_mod = _load("laim_user_repository_lockout_test", _REPO_PATH)
    crypto = _load("laim_password_crypto_lockout_test", _CRYPTO_PATH)
    svc_mod = _load("laim_auth_service_lockout_test", _SERVICE_PATH)
    repo = repo_mod.LaimUserRepository(engine)
    repo.create_user(
        organization_id=1,
        identity_type_id=4,
        user_name="ana",
        encrypted_password=crypto.encrypt_password(GOOD),
        user_email="ana@laim.example",
        user_mobile=None,
        first_name="Ana",
        sur_name="Laim",
    )
    auth = svc_mod.LaimAuthService(user_repo=repo, auditoria=MagicMock())
    auth._session_service = _fake_session_service()
    ops_mod = _load("laim_users_ops_service_lockout_test", _OPS_PATH)
    ops = ops_mod.LaimUsersOpsService(user_repo=repo)
    return svc_mod, auth, repo, ops, engine


def _fake_session_service() -> MagicMock:
    token_pair = MagicMock()
    token_pair.access_token = "a"
    token_pair.session_token = "s"
    token_pair.access_expires_at = 1
    token_pair.session_expires_at = 2
    token_pair.session_id = "sess-1"
    created = MagicMock()
    created.session.session_id = "sess-1"
    created.token_pair = token_pair
    service = MagicMock()
    service.create_session.return_value = created
    return service


def _logs(engine) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT user_name, event, status, details FROM laim_auth_logs "
                "WHERE user_name = 'ana' ORDER BY id"
            )
        ).mappings().fetchall()
    return [dict(row) for row in rows]


def _blocked(repo) -> bool:
    return repo.get_user_by_name("ana").blocked


def _fail(auth, times: int, user_name: str = "ana") -> list:
    return [auth.login(user_name, BAD, ip_address="10.0.0.8") for _ in range(times)]


def test_max_failed_attempts_is_five(env) -> None:
    svc_mod, *_ = env
    assert svc_mod.LaimAuthService.MAX_FAILED_ATTEMPTS == 5


def test_every_wrong_password_is_recorded_and_four_do_not_block(env) -> None:
    svc_mod, auth, repo, _ops, engine = env
    results = _fail(auth, 4)
    assert [r.error for r in results] == [svc_mod.MSG_INVALID_CREDENTIALS] * 4
    logs = _logs(engine)
    assert [(r["event"], r["status"]) for r in logs] == [("login_attempt", "failed")] * 4
    assert [json.loads(r["details"])["error_code"] for r in logs] == ["INVALID_PASSWORD"] * 4
    assert BAD not in json.dumps(logs)
    assert _blocked(repo) is False


def test_fifth_wrong_password_blocks_and_records_login_blocked(env) -> None:
    svc_mod, auth, repo, _ops, engine = env
    results = _fail(auth, 5)
    assert [r.error for r in results[:4]] == [svc_mod.MSG_INVALID_CREDENTIALS] * 4
    assert results[4].error == svc_mod.MSG_ACCOUNT_LOCKED
    assert _blocked(repo) is True
    last = _logs(engine)[-1]
    assert (last["event"], last["status"]) == ("login_blocked", "blocked")
    assert json.loads(last["details"]) == {"reason": "TOO_MANY_ATTEMPTS", "failed_attempts": 5}


def test_old_failures_count_there_is_no_time_window(env) -> None:
    _svc_mod, auth, repo, _ops, engine = env
    _fail(auth, 4)
    with engine.begin() as conn:
        conn.execute(text("UPDATE laim_auth_logs SET timestamp = '2026-01-01 00:00:00'"))
    _fail(auth, 1)
    assert _blocked(repo) is True


def test_failures_with_padded_user_name_count_for_the_account(env) -> None:
    _svc_mod, auth, repo, _ops, engine = env
    _fail(auth, 5, user_name=" ana ")
    assert _blocked(repo) is True
    assert {r["user_name"] for r in _logs(engine)} == {"ana"}


def test_successful_login_resets_the_count(env) -> None:
    _svc_mod, auth, repo, _ops, _engine = env
    _fail(auth, 4)
    assert auth.login("ana", GOOD).success is True
    _fail(auth, 4)
    assert _blocked(repo) is False
    _fail(auth, 1)
    assert _blocked(repo) is True


def test_blocked_account_gets_locked_message_even_with_good_password(env) -> None:
    svc_mod, auth, repo, _ops, engine = env
    _fail(auth, 5)
    result = auth.login("ana", GOOD)
    assert result.success is False
    assert result.error == svc_mod.MSG_ACCOUNT_LOCKED
    last = _logs(engine)[-1]
    assert (last["event"], last["status"]) == ("login_attempt", "failed")
    assert json.loads(last["details"])["error_code"] == "USER_BLOCKED"


def test_operator_unblock_resets_the_count(env) -> None:
    _svc_mod, auth, repo, ops, _engine = env
    _fail(auth, 5)
    user_id = repo.get_user_by_name("ana").user_id
    assert ops.set_blocked(user_id, False)["success"] is True
    assert _blocked(repo) is False
    _fail(auth, 4)
    assert _blocked(repo) is False
    assert auth.login("ana", GOOD).success is True


def test_operator_unblock_after_manual_block_ignores_older_failures(env) -> None:
    _svc_mod, auth, repo, ops, _engine = env
    _fail(auth, 4)
    user_id = repo.get_user_by_name("ana").user_id
    ops.set_blocked(user_id, True)
    ops.set_blocked(user_id, False)
    _fail(auth, 4)
    assert _blocked(repo) is False


def test_manual_block_keeps_not_enabled_message(env) -> None:
    svc_mod, auth, repo, ops, _engine = env
    ops.set_blocked(repo.get_user_by_name("ana").user_id, True)
    assert auth.login("ana", GOOD).error == svc_mod.MSG_USER_DISABLED
    assert svc_mod.MSG_USER_DISABLED == "El usuario no está habilitado"


def test_unknown_user_and_wrong_password_get_the_same_message(env) -> None:
    _svc_mod, auth, _repo, _ops, _engine = env
    unknown = auth.login("nadie", BAD)
    wrong = auth.login("ana", BAD)
    assert unknown.error == wrong.error
    assert unknown.to_dict() == wrong.to_dict()


def test_unknown_user_failures_never_block_anyone(env) -> None:
    _svc_mod, auth, repo, _ops, _engine = env
    for _ in range(6):
        auth.login("nadie", BAD)
    assert repo.count_failed_password_attempts("nadie") == 0
    assert _blocked(repo) is False


def test_repository_count_ignores_non_password_failures(env) -> None:
    _svc_mod, _auth, repo, _ops, _engine = env
    for code in ("USER_BLOCKED", "DECRYPT_ERROR", "USER_NOT_FOUND"):
        repo.append_auth_log(
            user_name="ana",
            event="login_attempt",
            status="failed",
            details={"error_code": code, "detail": "x"},
        )
    repo.append_auth_log(
        user_name="ana",
        event="login_attempt",
        status="failed",
        details={"error_code": "INVALID_PASSWORD", "detail": "x"},
    )
    assert repo.count_failed_password_attempts("ana") == 1


def test_password_change_resets_the_count(env) -> None:
    _svc_mod, auth, repo, _ops, _engine = env
    _fail(auth, 4)
    repo.append_auth_log(
        user_name="ana",
        event="password_change",
        status="success",
        details={"action": "password_reset"},
    )
    assert repo.count_failed_password_attempts("ana") == 0


def test_reset_request_of_locked_account_keeps_lock_and_message(env) -> None:
    svc_mod, auth, repo, _ops, _engine = env
    _fail(auth, 5)
    assert auth.request_password_reset("ana@laim.example")["found"] is False
    assert repo.last_block_reason("ana") == "TOO_MANY_ATTEMPTS"
    assert auth.login("ana", GOOD).error == svc_mod.MSG_ACCOUNT_LOCKED
    assert repo.count_failed_password_attempts("ana") == 0


def test_last_block_reason_is_empty_after_unblock(env) -> None:
    _svc_mod, auth, repo, ops, _engine = env
    _fail(auth, 5)
    ops.set_blocked(repo.get_user_by_name("ana").user_id, False)
    assert repo.last_block_reason("ana") == ""

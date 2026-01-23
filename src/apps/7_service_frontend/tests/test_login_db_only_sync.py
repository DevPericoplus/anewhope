"""Test de login con storage_mode=db_only y sincronía OTP."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest


MYSQL_PATH = "/usr/local/opt/mariadb@10.6/bin/mysql"
DB_NAME = "myllm_core_db"
DB_USER = "root"
DB_PASSWORD = "RootP@ssw0rd2026"


def _load_module(module_name: str, module_path: Path) -> Any:
    """Carga un módulo desde una ruta absoluta."""

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el módulo {module_name}")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _exec_sql(query: str) -> None:
    cmd = [
        MYSQL_PATH,
        "-u",
        DB_USER,
        f"-p{DB_PASSWORD}",
        "--database",
        DB_NAME,
        "-e",
        query,
    ]
    subprocess.run(cmd, check=True)


def _fetch_rows(query: str) -> list[list[str]]:
    cmd = [
        MYSQL_PATH,
        "-u",
        DB_USER,
        f"-p{DB_PASSWORD}",
        "--database",
        DB_NAME,
        "-N",
        "-B",
        "-e",
        query,
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    rows = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


def _fetch_users() -> list[dict[str, object]]:
    rows = _fetch_rows(
        "SELECT user_id, organization_id, identity_type_id, user_name, user_password, "
        "user_email, user_mobile, user_otp, active, blocked FROM users ORDER BY user_id"
    )
    users = []
    for row in rows:
        users.append(
            {
                "user_id": int(row[0]),
                "organization_id": int(row[1]),
                "identity_type_id": int(row[2]),
                "user_name": row[3],
                "user_password": row[4],
                "user_email": row[5],
                "user_mobile": row[6] or "",
                "user_otp": row[7] or "",
                "active": bool(int(row[8])) if row[8] is not None else False,
                "blocked": bool(int(row[9])) if row[9] is not None else False,
                "contact_info": {},
                "billing_info": {},
            }
        )
    return users


def _update_user_otp(user_id: int, otp: str) -> None:
    _exec_sql(
        f"UPDATE users SET user_otp = '{otp}' WHERE user_id = {user_id}"
    )


def test_login_db_only_syncs_otp(tmp_path: Path, monkeypatch: Any) -> None:
    """Valida login con OTP en DB y sincronía post-rotación."""

    monkeypatch.setenv("STORAGE_MODE", "db_only")
    monkeypatch.setenv("MARIADB_CLI_PATH", MYSQL_PATH)
    users_path = tmp_path / "users.json"
    monkeypatch.setenv("USERS_DATA_PATH", str(users_path))

    admin_row = _fetch_rows(
        "SELECT user_id, user_otp FROM users WHERE user_name = 'adminone' LIMIT 1"
    )
    if not admin_row:
        pytest.skip("Usuario adminone no existe en la base de datos")
    user_id = int(admin_row[0][0])
    _update_user_otp(user_id, "3296")

    class BrokerStub:
        def fetch_users(self) -> list[dict[str, object]]:
            return _fetch_users()

        def store_users(self, users_payload: list[dict[str, object]]) -> None:
            for entry in users_payload:
                _update_user_otp(int(entry["user_id"]), str(entry.get("user_otp", "")))

    middleware_path = (
        Path(__file__).resolve().parents[1] / "routermiddleware.py"
    )
    routermiddleware = _load_module("routermiddleware", middleware_path)

    router = routermiddleware.RouterMiddleware(
        interface=object(),
        jwt_settings=routermiddleware.get_jwt_settings(),
        broker_client=BrokerStub(),
    )

    tokens = router.authenticate_user(
        user_name="adminone",
        password="Password01",
        otp="3296",
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    assert tokens.user_id == user_id

    rotated = _fetch_rows(
        "SELECT user_otp FROM users WHERE user_id = 1 LIMIT 1"
    )[0][0]
    assert rotated != "3296"

    users_payload = json.loads(users_path.read_text(encoding="utf-8"))
    json_otp = next(
        user["user_otp"] for user in users_payload if user["user_id"] == user_id
    )
    assert json_otp == rotated

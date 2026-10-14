"""Tests TDD del repositorio de auditoría del portal."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

_REPO_PATH = Path(__file__).resolve().parents[1] / "adapters" / "laim_auditoria_repository.py"
_DOMAIN_PATH = Path(__file__).resolve().parents[1] / "domain" / "laim_auditoria.py"


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def _load_repo():
    name = "laim_auditoria_repository_test"
    spec = importlib.util.spec_from_file_location(name, _REPO_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_domain():
    name = "laim_auditoria_domain_test"
    spec = importlib.util.spec_from_file_location(name, _DOMAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _schema_sql() -> str:
    return """
    CREATE TABLE auditoria_usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        accion TEXT NOT NULL,
        user_id INTEGER,
        user_name TEXT NOT NULL,
        session_id TEXT,
        occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE auditoria_visitas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        started_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        segundos INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE auditoria_paginas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        seccion TEXT NOT NULL,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        segundos INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE auditoria_instaladores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        accion TEXT NOT NULL,
        edition TEXT NOT NULL,
        platform TEXT NOT NULL,
        version TEXT,
        filename TEXT,
        user_id INTEGER,
        occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE auditoria_foro (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        accion TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        thread_id INTEGER NOT NULL,
        post_id INTEGER,
        subcategory_id TEXT,
        occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """


@pytest.fixture
def repo():
    module = _load_repo()
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        for statement in _schema_sql().split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(text(stmt))
    return module.LaimAuditoriaRepository(engine), engine


def test_record_usuario_allows_failed_login_without_user_id(repo) -> None:
    repository, engine = repo
    row_id = repository.record_usuario("login_fallido", "ghost", user_id=None)
    assert row_id > 0
    with engine.connect() as conn:
        row = conn.execute(text("SELECT user_id, accion FROM auditoria_usuarios")).mappings().fetchone()
    assert row["user_id"] is None
    assert row["accion"] == "login_fallido"


def test_record_instalador_anonymous_has_no_user_id(repo) -> None:
    repository, engine = repo
    repository.record_instalador(
        "descarga",
        "community_edition",
        "linux_deb",
        version="2.0.1",
        filename="laim.deb",
        user_id=None,
    )
    with engine.connect() as conn:
        row = conn.execute(text("SELECT user_id, accion FROM auditoria_instaladores")).mappings().fetchone()
    assert row["user_id"] is None
    assert row["accion"] == "descarga"


def test_heartbeat_does_not_duplicate_visita_rows(repo) -> None:
    repository, engine = repo
    now = datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)
    first = repository.upsert_visita(9, "sess-a", now=now)
    second = repository.upsert_visita(9, "sess-a", now=now + timedelta(seconds=30))
    assert first["id"] == second["id"]
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM auditoria_visitas")).scalar()
    assert count == 1
    assert second["segundos"] == 30


def test_idle_heartbeat_opens_new_visita(repo) -> None:
    repository, _engine = repo
    now = datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)
    first = repository.upsert_visita(9, "sess-a", now=now)
    later = repository.upsert_visita(9, "sess-a", now=now + timedelta(seconds=91))
    assert later["id"] != first["id"]
    assert later.get("opened") is True


def test_section_change_closes_previous_tramo(repo) -> None:
    repository, engine = repo
    now = datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)
    repository.heartbeat_pagina(9, "sess-a", "home", now=now)
    repository.heartbeat_pagina(9, "sess-a", "foro", now=now + timedelta(seconds=40))
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT seccion, ended_at, segundos FROM auditoria_paginas ORDER BY id")
        ).mappings().fetchall()
    assert len(rows) == 2
    assert rows[0]["seccion"] == "home"
    assert rows[0]["ended_at"] is not None
    assert int(rows[0]["segundos"]) == 40
    assert rows[1]["seccion"] == "foro"
    assert rows[1]["ended_at"] is None


def test_should_record_download_only_for_install_script() -> None:
    domain = _load_domain()
    assert domain.should_record_download("install-script") is True
    assert domain.should_record_download("") is False
    assert domain.should_record_download("cache") is False


def test_migration_029_declares_auditoria_tables() -> None:
    sql_path = (
        Path(__file__).resolve().parents[3]
        / "infrastructure"
        / "database"
        / "migrations"
        / "029_auditoria_portal.sql"
    )
    text_sql = sql_path.read_text(encoding="utf-8")
    for table in (
        "auditoria_usuarios",
        "auditoria_visitas",
        "auditoria_paginas",
        "auditoria_instaladores",
        "auditoria_foro",
    ):
        assert f"CREATE TABLE IF NOT EXISTS `{table}`" in text_sql
        assert f"GRANT SELECT ON `laim_core_db`.`{table}`" in text_sql
    assert "ip_address" not in text_sql
    assert "copia_script" in text_sql
    assert "script_http" in text_sql

"""Recuento de respuestas por hilo y estadísticas del foro contra SQL real.

QA de LAIM Web: la lista de hilos decía siempre «0 resp.» porque la consulta
no traía posts_count, y «Actividad por subcategoría» incluía subcategorías
inactivas que el selector público no ofrece, sin marcarlas.
Se ejecuta en SQLite en memoria (como test_laim_password_reset.py); NOW() y
CURDATE() de MariaDB se registran como funciones.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text

_SHARED = Path(__file__).resolve().parents[3] / "2_shared_application"
_REPO_PATH = _SHARED / "adapters" / "laim_forum_repository.py"

_SCHEMA = """
CREATE TABLE laim_forum_categories (
    id TEXT PRIMARY KEY, nombre TEXT, descripcion TEXT, orden INTEGER DEFAULT 0,
    activa INTEGER DEFAULT 1
);
CREATE TABLE laim_forum_subcategories (
    id TEXT PRIMARY KEY, categoria_id TEXT, nombre TEXT, descripcion TEXT,
    orden INTEGER DEFAULT 0, activa INTEGER DEFAULT 1
);
CREATE TABLE laim_forum_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT, subcategory_id TEXT, prefix_id TEXT,
    titulo TEXT, user_id INTEGER, user_name TEXT, cuerpo_md TEXT,
    fijado INTEGER DEFAULT 0, cerrado INTEGER DEFAULT 0, deleted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE laim_forum_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, thread_id INTEGER, user_id INTEGER,
    user_name TEXT, cuerpo_md TEXT, deleted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE laim_forum_thread_ratings (thread_id INTEGER, user_id INTEGER, valoracion INTEGER);
CREATE TABLE laim_forum_post_ratings (post_id INTEGER, user_id INTEGER, valoracion INTEGER);
CREATE TABLE laim_forum_bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT, activo INTEGER, expires_at TIMESTAMP
);
CREATE TABLE laim_forum_infractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TIMESTAMP
);
CREATE TABLE laim_forum_thread_images (thread_id INTEGER, image_id INTEGER, sort_order INTEGER);
CREATE TABLE laim_forum_post_images (post_id INTEGER, image_id INTEGER, sort_order INTEGER);
CREATE TABLE laim_user_forum (
    user_id INTEGER PRIMARY KEY, forum_display_name TEXT, avatar_image_id INTEGER,
    reputation_avg REAL DEFAULT 0, reputation_votes INTEGER DEFAULT 0
);
CREATE TABLE laim_forum_avatar_catalog (image_id INTEGER, label TEXT, active INTEGER);
CREATE TABLE laim_users (user_id INTEGER PRIMARY KEY, user_name TEXT);
"""

_SEED = """
INSERT INTO laim_forum_categories (id, nombre, orden, activa) VALUES
    ('general', 'General', 1, 1), ('archivo', 'Archivo', 2, 0);
INSERT INTO laim_forum_subcategories (id, categoria_id, nombre, orden, activa) VALUES
    ('presentaciones', 'general', 'Presentaciones', 1, 1),
    ('anuncios', 'general', 'Anuncios', 2, 0),
    ('viejo', 'archivo', 'Viejo', 1, 1);
INSERT INTO laim_forum_threads (id, subcategory_id, titulo, user_id, user_name, cuerpo_md, deleted) VALUES
    (1, 'presentaciones', 'Hola', 10, 'ana', 'mensaje inicial', 0),
    (2, 'presentaciones', 'Sin respuestas', 11, 'bob', 'otro inicial', 0),
    (3, 'presentaciones', 'Borrado', 10, 'ana', 'borrado', 1),
    (4, 'anuncios', 'Aviso', 10, 'ana', 'aviso', 0);
INSERT INTO laim_forum_posts (thread_id, user_id, user_name, cuerpo_md, deleted) VALUES
    (1, 11, 'bob', 'r1', 0),
    (1, 12, 'eva', 'r2', 0),
    (1, 11, 'bob', 'r3 borrada', 1),
    (3, 11, 'bob', 'en hilo borrado', 0),
    (4, 11, 'bob', 'r aviso', 0);
"""


def _load_repository_module():
    name = "laim_forum_repository_counts_test"
    spec = importlib.util.spec_from_file_location(name, _REPO_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repository(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("STORAGE_MODE", "mock")
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _mariadb_functions(dbapi_conn, _record) -> None:
        dbapi_conn.create_function("NOW", 0, lambda: datetime.now().isoformat(sep=" "))
        dbapi_conn.create_function("CURDATE", 0, lambda: datetime.now().date().isoformat())

    with engine.begin() as conn:
        for statement in (_SCHEMA + _SEED).split(";"):
            if statement.strip():
                conn.execute(text(statement))
    return _load_repository_module().LaimForumRepository(engine)


def test_thread_list_counts_non_deleted_replies(repository) -> None:
    items = {item["id"]: item for item in repository.list_threads_by_subcategory("presentaciones")}
    # El mensaje inicial no es una respuesta; la respuesta borrada no cuenta.
    assert items[1]["posts_count"] == 2
    assert items[2]["posts_count"] == 0
    assert 3 not in items


def test_reply_count_matches_the_thread_view(repository) -> None:
    for item in repository.list_threads_by_subcategory("presentaciones"):
        assert item["posts_count"] == len(repository.list_posts_by_thread(item["id"]))


def test_user_thread_list_carries_reply_count(repository) -> None:
    items = {item["id"]: item for item in repository.list_threads_by_user(10)}
    assert items[1]["posts_count"] == 2
    assert items[4]["posts_count"] == 1


def test_admin_stats_mark_inactive_subcategories(repository) -> None:
    stats = repository.get_admin_stats()
    rows = {row["subcategory_id"]: row for row in stats["subcategorias_detalle"]}
    assert rows["presentaciones"]["activa"] is True
    assert rows["anuncios"]["activa"] is False  # subcategoría inactiva
    assert rows["viejo"]["activa"] is False  # su categoría está inactiva
    # Las inactivas siguen contando para el admin.
    assert rows["anuncios"]["hilos"] == 1
    assert rows["anuncios"]["respuestas"] == 1


def test_stats_replies_agree_with_thread_list(repository) -> None:
    stats = repository.get_admin_stats()
    rows = {row["subcategory_id"]: row for row in stats["subcategorias_detalle"]}
    listed = repository.list_threads_by_subcategory("presentaciones")
    assert rows["presentaciones"]["respuestas"] == sum(t["posts_count"] for t in listed)
    assert rows["presentaciones"]["hilos"] == len(listed)

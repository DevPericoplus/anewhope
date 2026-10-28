"""Lista de hilos con su nº de respuestas y estadísticas con inactivas marcadas."""

from __future__ import annotations

from pathlib import Path

from laim_web.laim_forum_mixin import (
    FORUM_INACTIVE_SUFFIX,
    forum_stats_inactive_note,
    forum_stats_subcategory_rows,
)

laimweb_root = Path(__file__).resolve().parents[1]


def test_stats_rows_mark_inactive_subcategories() -> None:
    rows = forum_stats_subcategory_rows(
        [
            {"subcategory_name": "Presentaciones", "activa": True, "hilos": 2},
            {"subcategory_name": "Anuncios", "activa": False, "hilos": 1},
            {"subcategory_name": "Sin campo (backend anterior)", "hilos": 0},
            "basura",
        ]
    )
    assert [row["estado_sufijo"] for row in rows] == ["", FORUM_INACTIVE_SUFFIX, ""]
    assert FORUM_INACTIVE_SUFFIX == " (inactiva)"
    assert [row["activa"] for row in rows] == [True, False, True]
    assert rows[1]["hilos"] == 1  # el admin sigue viendo sus cifras
    assert forum_stats_subcategory_rows(None) == []


def test_stats_panel_shows_the_suffix() -> None:
    ui = (laimweb_root / "laim_web" / "components" / "forum_extended_ui.py").read_text(
        encoding="utf-8"
    )
    assert 'row["subcategory_name"],\n' in ui
    assert 'row["estado_sufijo"]' in ui


def test_thread_list_reads_the_reply_count_from_the_api() -> None:
    mixin = (laimweb_root / "laim_web" / "laim_forum_mixin.py").read_text(encoding="utf-8")
    assert 'row.setdefault("respuestas_count", int(row.get("posts_count") or 0))' in mixin
    repo = (
        Path(__file__).resolve().parents[3]
        / "2_shared_application"
        / "adapters"
        / "laim_forum_repository.py"
    ).read_text(encoding="utf-8")
    assert ") AS posts_count" in repo
    assert repo.count("{_THREAD_POSTS_COUNT_SQL}") == 2


def test_subcategory_total_notes_how_many_are_inactive() -> None:
    """QA Silicon 28/10: el total decía 10 y el selector solo ofrecía 8."""
    rows = forum_stats_subcategory_rows(
        [{"activa": True}, {"activa": False}, {"activa": False}, {}]
    )
    assert forum_stats_inactive_note(rows) == "(2 inactivas)"
    assert forum_stats_inactive_note(rows[:2]) == "(1 inactiva)"
    assert forum_stats_inactive_note(rows[:1]) == ""
    ui = (laimweb_root / "laim_web" / "components" / "forum_extended_ui.py").read_text(
        encoding="utf-8"
    )
    assert "LaimWebState.forum_stats_subcategorias_nota" in ui

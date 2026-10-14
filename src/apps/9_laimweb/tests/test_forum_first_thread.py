"""Al entrar o cambiar selectores, el foro abre el primer hilo visible."""

from __future__ import annotations

from pathlib import Path

from laim_web.laim_forum_mixin import first_visible_forum_thread_id

_MIXIN = (
    Path(__file__).resolve().parents[1] / "laim_web" / "laim_forum_mixin.py"
).read_text(encoding="utf-8")


def test_first_visible_forum_thread_id_picks_list_head() -> None:
    assert first_visible_forum_thread_id([]) == 0
    assert first_visible_forum_thread_id([{"titulo": "sin id"}]) == 0
    assert first_visible_forum_thread_id([{"id": 11}, {"id": 22}]) == 11


def test_load_threads_opens_first_when_none_active() -> None:
    load = _MIXIN.split("def forum_load_threads", 1)[1].split(
        "def forum_open_thread", 1
    )[0]
    assert "_forum_open_first_visible_thread" in load
    helper = _MIXIN.split("def _forum_open_first_visible_thread", 1)[1].split(
        "\n    def ", 1
    )[0]
    assert "first_visible_forum_thread_id" in helper
    assert "forum_open_thread" in helper


def test_page_load_and_selectors_reset_then_list() -> None:
    on_load = _MIXIN.split("def forum_on_page_load", 1)[1].split(
        "def forum_poll_notifications", 1
    )[0]
    assert "forum_active_thread_id = 0" in on_load
    assert "forum_load_catalog" in on_load
    catalog = _MIXIN.split("def forum_load_catalog", 1)[1].split(
        "def _forum_apply_category", 1
    )[0]
    assert "forum_load_threads" in catalog
    apply_cat = _MIXIN.split("def _forum_apply_category", 1)[1].split(
        "def forum_select_category", 1
    )[0]
    assert "forum_active_thread_id = 0" in apply_cat
    assert "forum_load_threads" in apply_cat
    apply_sub = _MIXIN.split("def _forum_apply_subcategory", 1)[1].split(
        "def forum_select_subcategory", 1
    )[0]
    assert "forum_active_thread_id = 0" in apply_sub
    assert "forum_load_threads" in apply_sub

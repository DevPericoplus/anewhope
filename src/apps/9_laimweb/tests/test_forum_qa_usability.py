"""Contrato de las mejoras de QA en Configuración y Foro."""

from __future__ import annotations

from pathlib import Path

from laim_web.laim_forum_mixin import forum_log_range_message, prefer_general_category_id

_ROOT = Path(__file__).resolve().parents[1]
_WEB = _ROOT / "laim_web" / "components"


def test_general_category_is_the_default_when_present() -> None:
    categories = [
        {"id": "offtopic", "nombre": "Offtopic"},
        {"id": "general", "nombre": "General"},
    ]
    assert prefer_general_category_id(categories) == "general"
    assert prefer_general_category_id(categories, "offtopic") == "offtopic"
    assert prefer_general_category_id([{"id": "solo", "nombre": "Solo"}]) == "solo"
    assert prefer_general_category_id([]) == ""


def test_log_range_rejects_end_before_start() -> None:
    assert forum_log_range_message("2020-01-01", "2019-01-01") == (
        "La fecha Hasta es anterior a Desde"
    )
    assert forum_log_range_message("2019-01-01", "2020-01-01") == ""
    assert forum_log_range_message("", "2019-01-01") == ""


def test_forum_ui_labels_dialogs_and_uncontrolled_editor() -> None:
    ui = (_WEB / "forum_ui.py").read_text(encoding="utf-8")
    assert "default_value=LaimWebState.forum_edit_post_body" in ui
    assert "default_value=LaimWebState.forum_edit_thread_title" in ui
    assert "default_value=LaimWebState.forum_edit_thread_body" in ui
    assert "\n                    value=LaimWebState.forum_edit_post_body" not in ui
    assert "\n                                value=LaimWebState.forum_edit_thread_title" not in ui
    assert "\n                                value=LaimWebState.forum_edit_thread_body" not in ui
    assert "_forum_dialog(" in ui
    assert "forum_cat_tree_add_sub_open_changed" in ui
    assert "on_click=LaimWebState.forum_cat_tree_close_add_sub" in ui
    mixin = (_ROOT / "laim_web" / "laim_forum_mixin.py").read_text(encoding="utf-8")
    assert "def forum_cat_tree_close_add_sub(self)" in mixin
    assert "def forum_cat_tree_add_sub_open_changed(self, opened: bool)" in mixin
    assert '_field_label("Nombre")' in ui
    assert '_field_label("Descripción")' in ui
    assert "Orden de aparición" in ui
    assert "Duración del ban (segundos)" in ui
    assert "Rotación del log" in ui


def test_service_panel_avatars_and_log_filters() -> None:
    panel = (_WEB / "forum_service_panel.py").read_text(encoding="utf-8")
    assert '_service_action_button("Avatares", "image", "avatars")' in panel
    assert "Quitar filtros" in panel
    assert "forum_log_active_summary" in panel
    assert "La fecha Hasta es anterior a Desde" not in panel
    assert "forum_log_range_error" in panel
    assert "min_value=LaimWebState.forum_log_from" in panel
    assert "max_value=LaimWebState.forum_log_to" in panel


def test_extended_admin_confirms_and_avatar_catalog() -> None:
    extended = (_WEB / "forum_extended_ui.py").read_text(encoding="utf-8")
    assert 'forum_ask_confirm(\n                                                    "prefix"' in extended or 'forum_ask_confirm(' in extended
    assert "¿Eliminar el prefijo" not in extended
    assert "forum_confirm_prompt" in extended
    assert "on_open_change=LaimWebState.forum_confirm_open_changed" in extended
    assert "on_click=LaimWebState.forum_cancel_confirm" in extended
    assert "Quitar del catálogo" in extended
    assert "forum_admin_upload_catalog_avatar" in extended
    assert "forum_catalog_avatar_upload" in extended
    assert "Image ID" not in extended
    assert 'rx.el.label("Palabra"' in extended
    assert 'rx.el.label("Acción"' in extended
    assert 'rx.el.label("Mensaje al usuario"' in extended
    mixin = (_ROOT / "laim_web" / "laim_forum_mixin.py").read_text(encoding="utf-8")
    assert "Prefijo eliminado." in mixin
    assert "prefer_general_category_id" in mixin
    service = (
        _ROOT.parents[0] / "3_backend" / "laim_forum_service.py"
    ).read_text(encoding="utf-8")
    assert "def update_avatar_catalog_item" in service
    assert "def delete_avatar_catalog_item" in service

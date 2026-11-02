"""Defectos de Configuración que la prueba de QA comprobó contra la API."""

from __future__ import annotations

from pathlib import Path

from laim_web.laim_forum_mixin import (
    forum_new_identifier_error,
    forum_orden_value,
    forum_thread_counts,
)

ROOT = Path(__file__).resolve().parents[1]
MIXIN = (ROOT / "laim_web" / "laim_forum_mixin.py").read_text(encoding="utf-8")
UI = (ROOT / "laim_web" / "components" / "forum_ui.py").read_text(encoding="utf-8")
EXTENDED = (ROOT / "laim_web" / "components" / "forum_extended_ui.py").read_text(
    encoding="utf-8"
)
MANUAL = (ROOT / "static_pages" / "config_general.md").read_text(encoding="utf-8")


def test_orden_rejects_text_instead_of_storing_zero() -> None:
    assert forum_orden_value("abc") == (None, "Orden solo admite números.")
    assert forum_orden_value("7") == (7, "")
    assert forum_orden_value("") == (0, "")


def test_new_identifier_rejects_spaces() -> None:
    assert forum_new_identifier_error("qa_ok") == ""
    assert "minúsculas" in forum_new_identifier_error("qa con espacios")


def test_thread_counts_come_from_stats_detail() -> None:
    counts = forum_thread_counts(
        [
            {"subcategory_id": "inicios", "hilos": 1},
            {"subcategory_id": "general", "hilos": 2},
        ]
    )
    assert counts == {"inicios": 1, "general": 2}


def test_rename_sends_the_rest_of_the_subcategory() -> None:
    rename = MIXIN.split("def forum_cat_tree_save_rename", 1)[1].split(
        "def forum_cat_tree_open_delete", 1
    )[0]
    assert '"descripcion"' in rename
    assert '"ban_seconds"' in rename
    assert '"log_rotation"' in rename
    assert '"orden": 0' not in rename


def test_word_rule_form_resets_after_saving() -> None:
    save = MIXIN.split("def forum_admin_save_word_rule", 1)[1].split(
        "def forum_admin_delete_word_rule", 1
    )[0]
    assert "_forum_admin_reset_word_form()" in save


def test_updating_a_domain_says_updated_and_patches_the_row() -> None:
    assert "Dominio actualizado." in MIXIN
    assert "laim_forum_admin_update_allowed_url" in MIXIN
    assert "forum_admin_url_id" in EXTENDED


def test_context_menu_uses_an_opaque_surface() -> None:
    assert 'COLORS["panel_bg_solid"]' in UI
    assert "boxShadow" in UI


def test_manual_uses_the_controls_that_exist() -> None:
    assert "Guardar ajustes" not in MANUAL
    assert "Añadir dominio" not in MANUAL
    assert "Anunciar ban en log" not in MANUAL
    assert "Guardar dominio" in MANUAL
    assert "Restablecer" in MANUAL
    assert "Anunciar ban en el log" in MANUAL
    assert "Modificar" in EXTENDED
    assert "Guardar dominio" in EXTENDED

"""El desplegable acepta el id de categoría aunque no coincidan las mayúsculas."""

from __future__ import annotations

from laim_web.laim_forum_mixin import (
    forum_same_category,
    forum_subcategories_for_category,
)


def test_general_seed_matches_capitalised_category_id() -> None:
    rows = forum_subcategories_for_category(
        [
            {"id": "presentaciones", "categoria_id": "general", "nombre": "Presentaciones"},
            {"id": "debate", "categoria_id": "general", "nombre": "Debate"},
            {"id": "novedades", "categoria_id": "General", "nombre": "Novedades"},
            {"id": "inicios", "categoria_id": "Modo cli", "nombre": "Inicios"},
        ],
        "General",
    )
    assert [row["nombre"] for row in rows] == [
        "Presentaciones",
        "Debate",
        "Novedades",
    ]


def test_empty_active_category_keeps_every_subcategory() -> None:
    rows = forum_subcategories_for_category(
        [{"id": "debate", "categoria_id": "general", "nombre": "Debate"}],
        "",
    )
    assert forum_same_category("general", "")
    assert [row["id"] for row in rows] == ["debate"]

"""Tests del catálogo ilustrado alohe/avatars."""

from __future__ import annotations

from pathlib import Path

from laim_web.dynamic_import import load_module_from_path

_MODULE = load_module_from_path(
    Path(__file__).resolve().parents[3]
    / "2_shared_application"
    / "laim_forum_alohe_avatars.py",
    "test_laim_forum_alohe_avatars",
)

_ASSETS = (
    Path(__file__).resolve().parents[1] / "assets" / "forum_avatars" / "alohe"
)


def test_expected_count_matches_specs() -> None:
    specs = _MODULE.list_alohe_specs()
    assert len(specs) == _MODULE.expected_alohe_count()
    assert len(specs) == 133


def test_static_url_map_includes_laim_and_alohe() -> None:
    mapping = _MODULE.build_static_url_map()
    assert mapping["Terminal"].startswith("/forum_avatars/avatar_01_terminal.png")
    assert mapping["Vibrent 1"] == "/forum_avatars/alohe/vibrent_1.png?v=1"
    assert mapping["3D 5"] == "/forum_avatars/alohe/3d_5.png?v=1"
    assert mapping["Upstream 22"] == "/forum_avatars/alohe/upstream_22.png?v=1"
    assert len(mapping) == 8 + 133


def test_collection_for_label() -> None:
    assert _MODULE.collection_for_label("Cipher") == "laim"
    assert _MODULE.collection_for_label("Memo 12") == "memo"
    assert _MODULE.collection_for_label("3D 1") == "3d"
    assert _MODULE.collection_for_label("desconocido") == ""


def test_filter_catalog_items_by_collection() -> None:
    items = [
        {"label": "Terminal", "collection": "laim"},
        {"label": "Vibrent 1", "collection": "vibrent"},
        {"label": "Vibrent 2", "collection": "vibrent"},
        {"label": "Memo 1", "collection": "memo"},
    ]
    laim = _MODULE.filter_catalog_items(items, "laim")
    assert [row["label"] for row in laim] == ["Terminal"]
    vibrent = _MODULE.filter_catalog_items(items, "vibrent")
    assert [row["label"] for row in vibrent] == ["Vibrent 1", "Vibrent 2"]
    everyone = _MODULE.filter_catalog_items(items, "all")
    assert len(everyone) == 4
    unknown = _MODULE.filter_catalog_items(items, "no-existe")
    assert [row["label"] for row in unknown] == ["Terminal"]


def test_collection_options_start_with_laim_and_end_with_all() -> None:
    options = _MODULE.build_collection_options()
    assert options[0] == {"id": "laim", "label": "LAIM"}
    assert options[-1] == {"id": "all", "label": "Todos"}
    assert {item["id"] for item in options} >= {
        "vibrent",
        "3d",
        "bluey",
        "memo",
        "notion",
        "teams",
        "toon",
        "upstream",
    }


def test_seed_module_resolves_repo_root() -> None:
    seed = load_module_from_path(
        Path(__file__).resolve().parents[3]
        / "2_shared_application"
        / "laim_forum_avatar_catalog_seed.py",
        "test_laim_forum_avatar_catalog_seed",
    )
    assert (seed.REPO_ROOT / "versions.yml").is_file()
    assert seed.ALOHE_ASSETS_DIR.is_dir()
    assert len(seed._ensure_alohe_asset_files()) == 133


def test_vendored_png_assets_exist() -> None:
    missing = [
        spec["filename"]
        for spec in _MODULE.list_alohe_specs()
        if not (_ASSETS / spec["filename"]).is_file()
    ]
    assert missing == []
    licence = _ASSETS / "LICENCE"
    assert licence.is_file()
    assert "MIT License" in licence.read_text(encoding="utf-8")

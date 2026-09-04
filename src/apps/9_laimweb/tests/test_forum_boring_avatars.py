"""Tests del generador de avatares al estilo boring-avatars."""

from __future__ import annotations

from pathlib import Path

from laim_web.dynamic_import import load_module_from_path

_MODULE = load_module_from_path(
    Path(__file__).resolve().parents[3]
    / "2_shared_application"
    / "laim_forum_boring_avatars.py",
    "test_laim_forum_boring_avatars",
)


def test_same_seed_is_deterministic() -> None:
    first = _MODULE.build_avatar_svg("Ada Lovelace", variant="beam", palette_id="crt")
    second = _MODULE.build_avatar_svg("Ada Lovelace", variant="beam", palette_id="crt")
    assert first == second
    assert first.startswith("<svg")
    assert "</svg>" in first


def test_different_names_change_svg() -> None:
    alice = _MODULE.build_avatar_svg("Alice Paul", variant="pixel")
    grace = _MODULE.build_avatar_svg("Grace Hopper", variant="pixel")
    assert alice != grace


def test_all_variants_and_palettes_render() -> None:
    for variant in _MODULE.VARIANTS:
        for palette_id in _MODULE.PALETTES:
            svg = _MODULE.build_avatar_svg(
                "Maria Mitchell",
                variant=variant,
                palette_id=palette_id,
                square=True,
            )
            assert "<svg" in svg
            assert "mask" in svg


def test_preview_tiles_cover_six_variants() -> None:
    tiles = _MODULE.build_variant_preview_tiles("Clara Barton", palette_id="classic")
    assert [tile["variant"] for tile in tiles] == list(_MODULE.VARIANTS)
    assert all(tile["preview_url"].startswith("data:image/svg+xml;base64,") for tile in tiles)
    assert tiles[0]["label"] == "Mármol"


def test_hash_code_matches_javascript_abs32() -> None:
    assert _MODULE.hash_code("") == 0
    assert _MODULE.hash_code("a") == abs(_MODULE._to_int32(97))


def test_unknown_variant_falls_back_to_marble() -> None:
    assert _MODULE.resolve_variant("no-existe") == "marble"
    assert _MODULE.resolve_seed("   ") == "LAIM"

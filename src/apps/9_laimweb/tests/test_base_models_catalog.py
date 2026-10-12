"""Referencia blue/green del catálogo de modelos base."""

from pathlib import Path

from laim_web.base_models_catalog import BASE_MODEL_TIER_ROWS, catalog_table_markdown
from laim_web.static_pages_loader import load_static_page_markdown

laimweb_root = Path(__file__).resolve().parents[1]


def test_catalog_has_all_client_tiers() -> None:
    """Las filas siguen AllTierKeys / TierKeyLabel del cliente."""
    assert [row.tier for row in BASE_MODEL_TIER_ROWS] == [
        "Traductor",
        "Rápido",
        "Medio",
        "Lento",
        "Alternativo",
        "Imágenes",
        "Vídeo",
        "Sonido",
        "TTS EN",
        "TTS ES",
        "Desarrollo",
    ]


def test_catalog_table_has_tier_blue_green_columns() -> None:
    """La tabla del modal es tier / blue / green con modelos de este equipo."""
    table = catalog_table_markdown()
    assert table.startswith("| Tier | Blue | Green |")
    assert "`gemma3:4b`" in table
    assert "`parable/qwen3-fable:4b`" in table
    assert "`qwen3.5:4b`" in table
    assert "`legraphista/Orpheus:latest`" in table
    assert "`sematre/Orpheus:ft-it_es-3b`" in table
    assert "`deepseek-coder:6.7b`" in table
    for row in BASE_MODEL_TIER_ROWS:
        assert row.blue
        assert row.green
        assert f"| {row.tier} |" in table


def test_catalog_matches_silicon_clear_export() -> None:
    """Blue/green (salvo TTS) coinciden con el export de este LAIM."""
    by_tier = {row.tier: row for row in BASE_MODEL_TIER_ROWS}
    assert by_tier["Traductor"].blue == "gemma3:4b"
    assert by_tier["Traductor"].green == "gemma3:4b"
    assert by_tier["Rápido"].blue == "qwen3.5:2b"
    assert by_tier["Medio"].blue == "parable/qwen3-fable:4b"
    assert by_tier["Medio"].green == "gemma3:4b"
    assert by_tier["Lento"].blue == "qwen3:8b"
    assert by_tier["Lento"].green == "qwen3.5:4b"
    assert by_tier["Desarrollo"].blue == "qwen2.5-coder:1.5b-base"
    assert by_tier["Desarrollo"].green == "deepseek-coder:6.7b"


def test_modelos_base_page_points_to_reference_catalog() -> None:
    """La página explica la tabla de referencia y no promete un catálogo vivo."""
    content = load_static_page_markdown("modelos_base")
    assert "Ver catálogo de modelos base" in content
    assert "blue" in content
    assert "green" in content
    assert "probados" in content


def test_catalog_button_opens_mounted_modal() -> None:
    """El botón abre el overlay; no un toast ni un rx.cond que desmonte."""
    state_src = (laimweb_root / "laim_web" / "laim_state.py").read_text(
        encoding="utf-8"
    )
    modal_src = (
        laimweb_root / "laim_web" / "components" / "base_models_modal.py"
    ).read_text(encoding="utf-8")
    index_src = (laimweb_root / "laim_web" / "pages" / "index.py").read_text(
        encoding="utf-8"
    )
    assert 'if action_key == "catalog_base_models"' in state_src
    assert "self.base_models_catalog_open = True" in state_src
    assert "El catálogo de modelos base estará disponible desde el cliente" not in state_src
    assert "base_models_catalog_modal()" in index_src
    assert 'display=rx.cond(LaimWebState.base_models_catalog_open, "flex", "none")' in modal_src
    assert "on_mouse_down=LaimWebState.close_base_models_catalog" in modal_src
    assert "crt-modal-panel--catalog" in modal_src

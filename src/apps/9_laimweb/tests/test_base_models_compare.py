"""Comparativa de requisitos monopuesto vs Share/Connect."""

from pathlib import Path

from laim_web.base_models_compare import (
    MONO_ROWS,
    SHARE_ROWS,
    compare_guide_markdown,
)
from laim_web.static_pages_loader import load_static_page_markdown

laimweb_root = Path(__file__).resolve().parents[1]


def test_compare_tables_have_cores_and_memory() -> None:
    """Las dos tablas estiman cores GPU y memoria mínima."""
    assert [row.profile for row in MONO_ROWS] == [
        "Esencial",
        "Dedicado (día a día)",
        "Holgado",
    ]
    assert MONO_ROWS[1].memory == "12 GB"
    assert "9b" in MONO_ROWS[1].notes
    assert SHARE_ROWS[0].memory == "16–20 GB"
    assert SHARE_ROWS[-1].memory == "48 GB+"
    for row in (*MONO_ROWS, *SHARE_ROWS):
        assert row.gpu_cores
        assert "GB" in row.memory


def test_compare_guide_covers_share_headscale_queues_and_kv() -> None:
    """La guía cubre Share, Headscale, colas y reutilización de memoria."""
    body = compare_guide_markdown()
    assert "Monopuesto" in body
    assert "Share" in body and "Connect" in body
    assert "share_api" in body
    assert "Headscale" in body
    assert "laim remote" in body
    assert "Gestor de colas" in body
    assert "num_ctx" in body
    assert "KV-cache" in body or "KV cache" in body or "KV-cache" in body
    assert "Chat Context Summarized" in body
    assert "warmup" in body.lower() or "Warmup" in body
    assert "OLLAMA_NUM_PARALLEL" in body
    assert "Flash Attention" in body


def test_modelos_base_page_points_to_compare() -> None:
    """La página menciona la comparativa de requisitos."""
    content = load_static_page_markdown("modelos_base")
    assert "Comparativa de requisitos" in content
    assert "Share" in content
    assert "Headscale" in content


def test_compare_button_opens_mounted_modal() -> None:
    """El botón abre overlay montado, no el toast antiguo."""
    state_src = (laimweb_root / "laim_web" / "laim_state.py").read_text(
        encoding="utf-8"
    )
    modal_src = (
        laimweb_root / "laim_web" / "components" / "base_models_modal.py"
    ).read_text(encoding="utf-8")
    index_src = (laimweb_root / "laim_web" / "pages" / "index.py").read_text(
        encoding="utf-8"
    )
    assert 'if action_key == "compare_requirements"' in state_src
    assert "self.compare_requirements_open = True" in state_src
    assert "La comparativa de requisitos se publicará" not in state_src
    assert "compare_requirements_modal()" in index_src
    assert (
        'display=rx.cond(LaimWebState.compare_requirements_open, "flex", "none")'
        in modal_src
    )

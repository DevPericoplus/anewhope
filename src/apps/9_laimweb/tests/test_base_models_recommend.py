"""Mini-guía de recomendación por cores, memoria y warmup."""

from pathlib import Path

from laim_web.base_models_recommend import (
    MEMORY_SIZE_ROWS,
    memory_table_markdown,
    recommend_guide_markdown,
)
from laim_web.static_pages_loader import load_static_page_markdown

laimweb_root = Path(__file__).resolve().parents[1]


def test_memory_table_covers_requested_brackets() -> None:
    """La tabla recorre 6–128 GB y pone 9b como techo de 12 GB."""
    assert [row.memory_gb for row in MEMORY_SIZE_ROWS] == [
        6,
        12,
        20,
        24,
        36,
        48,
        64,
        128,
    ]
    by_gb = {row.memory_gb: row for row in MEMORY_SIZE_ROWS}
    assert by_gb[6].max_params == "2b"
    assert by_gb[12].max_params == "9b"
    assert "9b" in by_gb[12].examples
    assert "2b" in by_gb[6].typical_range
    assert "70b" in by_gb[64].max_params
    assert "70b+" in by_gb[128].max_params
    table = memory_table_markdown()
    assert table.startswith("| Memoria GPU / unificada |")
    assert "| 12 GB | 9b |" in table


def test_recommend_guide_covers_cores_warmup_and_tools() -> None:
    """La guía explica cores, concurrencia, warmup y herramientas del cliente."""
    body = recommend_guide_markdown()
    assert "laim info" in body
    assert "nvidia-smi" in body
    assert "system_profiler" in body
    assert "OLLAMA_NUM_PARALLEL" in body
    assert "warmup" in body.lower() or "Precalentamiento" in body
    assert "Rápido" in body and "Medio" in body
    assert "🧭 Asesor" in body
    assert "laim eval" in body
    assert "laim compare" in body
    assert "Capacidades" in body
    assert memory_table_markdown() in body


def test_modelos_base_page_points_to_recommend_guide() -> None:
    """La página enlaza la mini-guía del botón."""
    content = load_static_page_markdown("modelos_base")
    assert "Modelo recomendado para mi equipo" in content
    assert "6–128 GB" in content
    assert "warmup" in content


def test_recommend_button_opens_mounted_modal() -> None:
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
    assert 'if action_key == "recommended_model"' in state_src
    assert "self.recommended_model_open = True" in state_src
    assert "Use el asistente del cliente LAIM para recomendar un modelo base." not in state_src
    assert "recommended_model_modal()" in index_src
    assert 'display=rx.cond(LaimWebState.recommended_model_open, "flex", "none")' in modal_src
    assert "on_mouse_down=LaimWebState.close_recommended_model" in modal_src

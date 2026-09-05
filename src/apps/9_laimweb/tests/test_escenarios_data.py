"""Tests de la guía gráfica de escenarios LAIM."""

from pathlib import Path

from laim_web.escenarios_data import (
    ESCENARIO_DEFAULT_ID,
    build_escenario_view,
    escenario_step_count,
    get_escenario,
    infer_packet_dir,
    list_escenario_cards,
    list_escenario_ids,
    wire_curve_d,
)


def test_five_escenarios_in_order() -> None:
    """Hay cinco casos y el primero es varios Connect a un Share."""
    ids = list_escenario_ids()
    assert ids == [
        "share_multi",
        "remote_ssh",
        "combo_bastion",
        "mesh_headscale",
        "perimetro",
    ]
    assert ESCENARIO_DEFAULT_ID == "share_multi"


def test_unknown_escenario_falls_back_to_default() -> None:
    """Un id inválido usa el escenario por defecto."""
    assert get_escenario("no-existe")["id"] == ESCENARIO_DEFAULT_ID


def test_each_escenario_has_steps_and_geometry() -> None:
    """Cada escenario tiene nodos, cables y al menos cuatro fases."""
    for escenario_id in list_escenario_ids():
        scenario = get_escenario(escenario_id)
        assert len(scenario["nodes"]) >= 3
        assert len(scenario["edges"]) >= 3
        assert escenario_step_count(escenario_id) >= 4
        node_ids = {node["id"] for node in scenario["nodes"]}
        edge_ids = {edge["id"] for edge in scenario["edges"]}
        for step in scenario["steps"]:
            for edge_id in step["active_edges"]:
                assert edge_id in edge_ids
            for node_id in step["lit_nodes"]:
                assert node_id in node_ids
            if step["packet_edge"]:
                assert step["packet_edge"] in edge_ids


def test_build_view_clamps_step_and_marks_packet() -> None:
    """La vista recorta el índice y coloca el paquete en el cable activo."""
    last = escenario_step_count("share_multi") + 8
    view = build_escenario_view("share_multi", last)
    assert view["id"] == "share_multi"
    assert view["last_step"] is True
    assert view["step_label"].endswith(f"/{escenario_step_count('share_multi')}")

    mid = build_escenario_view("share_multi", 1)
    assert mid["packet_visible"] is True
    assert mid["packet_label"] == "SUBMIT"
    assert mid["packet_dir"] == "fwd"
    assert mid["show_queue"] is True
    assert mid["queue_slots"] == "0/2"
    assert mid["traffic"][0]["primary"] is True
    assert mid["traffic"][0]["edge"] == "c1-share"
    assert any("esc-gpu-" in node["class_name"] for node in mid["nodes"])
    assert mid["lit_csv"].startswith("|") and mid["lit_csv"].endswith("|")
    assert mid["active_csv"].startswith("|") and mid["active_csv"].endswith("|")

    tokens = build_escenario_view("share_multi", 3)
    assert tokens["packet_label"] == "TOKENS"
    assert tokens["packet_dir"] == "rev"
    assert tokens["traffic"][0]["reverse"] is True
    assert tokens["queue_slots"] == "1/2"
    assert tokens["queue_jobs"][0]["status"] == "running"


def test_share_multi_queue_mirrors_laim_share_priorities() -> None:
    """La cola GPU sigue claim no preemptivo: P2 antes que P3, 2 slots."""
    assert escenario_step_count("share_multi") == 7
    idle = build_escenario_view("share_multi", 0)
    assert idle["queue_jobs"] == []
    assert idle["queue_slots"] == "0/2"

    enqueue = build_escenario_view("share_multi", 4)
    assert enqueue["packet_label"] == "ENQUEUE"
    clients = {job["client"]: job for job in enqueue["queue_jobs"]}
    assert clients["A"]["status"] == "running"
    assert clients["B"]["status"] == "queued"
    assert clients["B"]["prio"] == "P2"
    assert clients["C"]["status"] == "queued"
    assert clients["C"]["prio"] == "P3"
    assert clients["C"]["kind"] == "teacher"

    saturated = build_escenario_view("share_multi", 5)
    assert saturated["queue_slots"] == "2/2"
    assert saturated["queue_jobs"][2]["client"] == "C"
    assert saturated["queue_jobs"][2]["status"] == "queued"

    done_a = build_escenario_view("share_multi", 6)
    assert done_a["queue_jobs"][2]["client"] == "A"
    assert done_a["queue_jobs"][2]["status"] == "done"


def test_infer_packet_dir_and_curve() -> None:
    """TOKENS vuelve al cliente; el cable usa curva Bézier tipo monitor."""
    assert infer_packet_dir("TOKENS") == "rev"
    assert infer_packet_dir("SUBMIT") == "fwd"
    assert infer_packet_dir("CLAIM") == "fwd"
    assert infer_packet_dir("ENQUEUE") == "fwd"
    path = wire_curve_d(16, 78, 50, 22)
    assert path.startswith("M16,78 C")
    assert path.endswith("50,22")


def test_escenarios_panel_avoids_dynamic_class_name_from_foreach() -> None:
    """Reflex no acepta class_name desde un item de foreach (causa 502)."""
    source = Path(__file__).resolve().parents[1] / "laim_web" / "components" / "escenarios_panel.py"
    text = source.read_text(encoding="utf-8")
    assert "node[\"class_name\"]" not in text
    assert 'job["class_name"]' not in text
    assert "escenario_nodes_view" not in text
    assert "escenario_wire_classes" not in text
    assert "esc-path-" in text
    assert "ESCENARIO_TRAFFIC_JS" in text
    assert "animateMotion" in text
    assert "_queue_panel" in text
    state = Path(__file__).resolve().parents[1] / "laim_web" / "laim_state.py"
    state_text = state.read_text(encoding="utf-8")
    assert "return self._start_escenario_playback()" in state_text
    assert "escenario_play_generation" in state_text
    assert ":{self.escenario_play_generation}:" in state_text


def test_escenarios_panel_uses_valid_crt_color_keys() -> None:
    """LAIM usa get_crt_colors (sin clave primary de frontend/backoffice)."""
    import re

    from laim_web.components.crt_theme import COLORS

    source = Path(__file__).resolve().parents[1] / "laim_web" / "components" / "escenarios_panel.py"
    keys = set(re.findall(r'COLORS\["(\w+)"\]', source.read_text(encoding="utf-8")))
    assert keys, "el panel debe usar COLORS"
    missing = keys - set(COLORS)
    assert not missing, f"claves COLORS inválidas en escenarios_panel: {missing}"


def test_selector_cards_match_scenarios() -> None:
    """Las tarjetas del selector cubren los cinco casos."""
    cards = list_escenario_cards()
    assert [card["id"] for card in cards] == list_escenario_ids()
    assert cards[0]["heading"].startswith("1.")

"""Tests de la guía gráfica de escenarios LAIM."""

from pathlib import Path

from laim_web.escenarios_data import (
    ESCENARIO_CHARS_PER_SEC,
    ESCENARIO_DEFAULT_ID,
    ESCENARIO_FADE_IN_S,
    ESCENARIO_FADE_OUT_S,
    ESCENARIO_READ_MIN_S,
    build_escenario_view,
    caption_packet_seconds,
    caption_step_seconds,
    escenario_step_count,
    get_escenario,
    infer_packet_dir,
    list_escenario_cards,
    list_escenario_ids,
    wire_curve_d,
)


def test_six_escenarios_in_order() -> None:
    """Hay seis casos; el sexto es el chat HITL que opera un servidor."""
    ids = list_escenario_ids()
    assert ids == [
        "share_multi",
        "remote_ssh",
        "combo_bastion",
        "mesh_headscale",
        "perimetro",
        "hitl_remote",
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
    assert infer_packet_dir("OUT") == "rev"
    assert infer_packet_dir("REPLY") == "rev"
    assert infer_packet_dir("SUBMIT") == "fwd"
    assert infer_packet_dir("CLAIM") == "fwd"
    assert infer_packet_dir("ENQUEUE") == "fwd"
    assert infer_packet_dir("HITL") == "fwd"
    path = wire_curve_d(16, 78, 50, 22)
    assert path.startswith("M16,78 C")
    assert path.endswith("50,22")


def test_escenarios_page_uses_slightly_larger_type() -> None:
    """La página Escenarios aplica un zoom tipográfico suave para leer mejor."""
    css = (
        Path(__file__).resolve().parents[1] / "assets" / "crt" / "crt_base.css"
    ).read_text(encoding="utf-8")
    assert ".crt-escenarios {" in css
    block = css.split(".crt-escenarios {", 1)[1].split("}", 1)[0]
    assert "font-size: 1.14em" in block
    assert ".crt-escenarios .crt-muted" in css
    assert "font-size: 0.96em" in css.split(".crt-escenarios .crt-muted", 1)[1].split("}", 1)[0]
    panel = (
        Path(__file__).resolve().parents[1] / "laim_web" / "components" / "escenarios_panel.py"
    ).read_text(encoding="utf-8")
    assert 'class_name="crt-escenarios crt-readable-zone"' in panel


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
    """Las tarjetas del selector cubren los seis casos."""
    cards = list_escenario_cards()
    assert [card["id"] for card in cards] == list_escenario_ids()
    assert cards[0]["heading"].startswith("1.")
    assert cards[5]["heading"].startswith("6.")
    assert "HITL" in cards[5]["summary"] or "confirma" in cards[5]["summary"].lower()


def test_hitl_remote_tells_grounded_confirm_execute() -> None:
    """El sexto caso muestra pregunta → plan grounded → HITL → comando real."""
    assert escenario_step_count("hitl_remote") >= 6
    idle = build_escenario_view("hitl_remote", 0)
    assert idle["packet_visible"] is False
    assert "autorice" in idle["caption"]

    labels = [
        build_escenario_view("hitl_remote", i)["packet_label"]
        for i in range(escenario_step_count("hitl_remote"))
    ]
    assert "ASK" in labels
    assert "HITL" in labels
    assert "CMD" in labels
    assert "OUT" in labels
    out = next(
        build_escenario_view("hitl_remote", i)
        for i in range(escenario_step_count("hitl_remote"))
        if build_escenario_view("hitl_remote", i)["packet_label"] == "OUT"
    )
    assert out["packet_dir"] == "rev"
    hitl = next(
        build_escenario_view("hitl_remote", i)
        for i in range(escenario_step_count("hitl_remote"))
        if build_escenario_view("hitl_remote", i)["packet_label"] == "HITL"
    )
    assert "hitl" in hitl["lit_csv"]


def test_caption_step_seconds_scales_with_length() -> None:
    """Cada fase dura lo de leer el texto más el fundido suave."""
    short = caption_step_seconds("ok")
    long = caption_step_seconds("x" * 140)
    fades = ESCENARIO_FADE_IN_S + ESCENARIO_FADE_OUT_S
    assert abs(short - (fades + ESCENARIO_READ_MIN_S)) < 1e-9
    assert long > short
    assert abs(long - (fades + (140 / ESCENARIO_CHARS_PER_SEC))) < 1e-9
    assert abs(caption_step_seconds("") - (fades + ESCENARIO_READ_MIN_S)) < 1e-9
    assert fades / long < 0.22
    packet = caption_packet_seconds("x" * 140, primary=True)
    assert 2.4 <= packet < long
    assert caption_packet_seconds("x" * 140, primary=False) < packet


def test_caption_has_larger_type_and_fade() -> None:
    """El pie es nítido; el fundido es solo opacidad, nunca blur."""
    css = (
        Path(__file__).resolve().parents[1] / "assets" / "crt" / "crt_base.css"
    ).read_text(encoding="utf-8")
    caption = css.split(".esc-caption {", 1)[1].split("}", 1)[0]
    assert "font-size: 1.17em" in caption
    assert "@keyframes esc-caption-breathe" not in css
    assert "@keyframes esc-caption-in" in css
    assert "@keyframes esc-caption-out" in css
    live = css.split(".esc-caption-live {", 1)[1].split("}", 1)[0]
    assert "esc-caption-in" in live
    assert "esc-caption-out" in live
    assert "ease-in-out" not in live
    inn = css.split("@keyframes esc-caption-in", 1)[1].split("@keyframes", 1)[0]
    out = css.split("@keyframes esc-caption-out", 1)[1]
    assert "blur" not in inn and "blur" not in out
    selector = css.split(".esc-selector {", 1)[1].split("}", 1)[0]
    assert "overflow-y: auto" in selector
    assert "100dvh" in selector or "100vh" in selector
    panel = (
        Path(__file__).resolve().parents[1] / "laim_web" / "components" / "escenarios_panel.py"
    ).read_text(encoding="utf-8")
    assert "esc-caption-live" in panel
    assert "escenario_caption_dur" in panel
    assert "animationDuration" not in panel
    assert "--esc-fade-in" in panel
    assert "hitl_remote" in panel
    assert "step_s" in panel or "cfg.step_s" in panel


def test_selecting_a_case_plays_and_homes_on_first_step() -> None:
    """Elegir un caso equivale a Reproducir; al terminar vuelve a la fase 1."""
    state = (
        Path(__file__).resolve().parents[1] / "laim_web" / "laim_state.py"
    ).read_text(encoding="utf-8")
    select = state.split("def escenario_select", 1)[1].split("def ", 1)[0]
    assert "return self._start_escenario_playback()" in select
    play = state.split("def escenario_play(", 1)[1].split("def ", 1)[0]
    assert "self.escenario_step = 1" in play
    loop = state.split("def escenario_play_loop", 1)[1].split("def ", 1)[0]
    assert "caption_step_seconds" in loop
    assert "self.escenario_step = 0" in loop
    assert "self.escenario_playing = False" in loop
    panel = (
        Path(__file__).resolve().parents[1] / "laim_web" / "components" / "escenarios_panel.py"
    ).read_text(encoding="utf-8")
    assert "No arranca solo" not in panel

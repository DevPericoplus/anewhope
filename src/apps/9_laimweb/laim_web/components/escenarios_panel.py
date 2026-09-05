"""Guía gráfica de escenarios LAIM (selector + diagrama animado)."""

from __future__ import annotations

import reflex as rx

from laim_web.escenarios_data import wire_curve_d
from laim_web.laim_state import LaimWebState

from laim_web.components.crt_theme import COLORS

ESCENARIO_TRAFFIC_JS = """
(function () {
  if (window.__escTrafficWatch) return;
  window.__escTrafficWatch = true;
  var lastGen = "";
  var SVG_NS = "http://www.w3.org/2000/svg";
  var XLINK_NS = "http://www.w3.org/1999/xlink";

  function colorFor(kind, reverse) {
    if (kind === "ai") return reverse ? "#6ee7b7" : "#a78bfa";
    if (kind === "ssh") return reverse ? "#44ffcc" : "#ffcc44";
    if (kind === "mesh" || kind === "wan") return reverse ? "#9dff9d" : "#7dffd6";
    return reverse ? "#44ffcc" : "#ffcc44";
  }

  function attachMotion(el, pathId, dur, keyPoints, delay) {
    var am = document.createElementNS(SVG_NS, "animateMotion");
    am.setAttribute("dur", dur + "s");
    am.setAttribute("rotate", "auto");
    am.setAttribute("keyPoints", keyPoints);
    am.setAttribute("keyTimes", "0;1");
    am.setAttribute("calcMode", "linear");
    am.setAttribute("fill", "freeze");
    am.setAttribute("begin", delay + "s");
    var mpath = document.createElementNS(SVG_NS, "mpath");
    mpath.setAttributeNS(XLINK_NS, "href", "#esc-path-" + pathId);
    mpath.setAttribute("href", "#esc-path-" + pathId);
    am.appendChild(mpath);
    el.appendChild(am);
  }

  function animateOne(svg, pkt, delay) {
    var pathEl = svg.querySelector("#esc-path-" + pkt.edge);
    if (!pathEl) return;
    var reverse = !!pkt.reverse;
    var keyPoints = reverse ? "1;0" : "0;1";
    var color = colorFor(pkt.kind || "ai", reverse);
    var dur = pkt.primary ? 2.45 : 2.15;
    var g = document.createElementNS(SVG_NS, "g");
    g.setAttribute("class", "traffic-packet");
    if (!pkt.primary) g.setAttribute("opacity", "0.7");

    var tail = document.createElementNS(SVG_NS, "path");
    tail.setAttribute("d", pathEl.getAttribute("d") || "");
    tail.setAttribute("stroke", color);
    tail.setAttribute("stroke-width", pkt.primary ? "1.15" : "0.85");
    tail.setAttribute("stroke-dasharray", "3.4 2");
    tail.setAttribute("fill", "none");
    tail.setAttribute("opacity", "0.58");
    tail.setAttribute("class", "esc-traffic-tail");
    g.appendChild(tail);

    var arrow = document.createElementNS(SVG_NS, "polygon");
    arrow.setAttribute("points", pkt.primary ? "-2.4,-1.4 2.6,0 -2.4,1.4" : "-1.7,-1 1.9,0 -1.7,1");
    arrow.setAttribute("fill", color);
    attachMotion(arrow, pkt.edge, dur, keyPoints, delay);
    g.appendChild(arrow);

    if (pkt.label) {
      var badge = document.createElementNS(SVG_NS, "text");
      badge.setAttribute("font-size", "3.1");
      badge.setAttribute("fill", color);
      badge.setAttribute("text-anchor", "middle");
      badge.setAttribute("dominant-baseline", "middle");
      badge.setAttribute("dy", "-3.4");
      badge.setAttribute("font-family", "Inconsolata, ui-monospace, monospace");
      badge.textContent = pkt.label;
      attachMotion(badge, pkt.edge, dur, keyPoints, delay);
      g.appendChild(badge);
    }

    svg.appendChild(g);
    setTimeout(function () {
      if (g.parentNode) g.parentNode.removeChild(g);
    }, (delay + dur + 0.4) * 1000);
  }

  function play(cfg) {
    var svg = document.querySelector(".esc-stage svg.esc-wires");
    if (!svg || !cfg) return;
    svg.querySelectorAll("g.traffic-packet").forEach(function (node) { node.remove(); });
    (cfg.packets || []).forEach(function (pkt, idx) {
      animateOne(svg, pkt, idx * 0.28);
    });
  }

  function tick() {
    var el = document.getElementById("esc-traffic-payload");
    if (!el) return;
    var raw = (el.textContent || "").trim();
    if (!raw) return;
    try {
      var cfg = JSON.parse(raw);
      var gen = String(cfg.gen || "");
      if (!gen || gen === lastGen) return;
      lastGen = gen;
      play(cfg);
    } catch (err) {}
  }

  setInterval(tick, 180);
})();
"""


def _selector_card(card: dict) -> rx.Component:
    """Tarjeta del selector de escenario."""
    return rx.box(
        rx.text(card["heading"], class_name="esc-card-title"),
        rx.text(card["summary"], class_name="esc-card-summary"),
        on_click=lambda: LaimWebState.escenario_select(card["id"]),
        class_name=rx.cond(
            LaimWebState.escenario_id == card["id"],
            "esc-card esc-card-active",
            "esc-card",
        ),
        width="100%",
        cursor="pointer",
    )


def _is_lit(node_id: str) -> rx.Var:
    """Nodo destacado en la fase actual."""
    return LaimWebState.escenario_lit_csv.contains(f"|{node_id}|")


def _is_active_wire(edge_id: str) -> rx.Var:
    """Cable con tráfico en la fase actual."""
    return LaimWebState.escenario_active_csv.contains(f"|{edge_id}|")


def _plain_node(node_id: str, label: str, role: str, left: str, top: str) -> rx.Component:
    """Nodo sin GPU: clase estática + resalte por fase."""
    base = f"esc-node esc-role-{role}"
    return rx.box(
        rx.text(role.upper(), class_name="esc-node-role"),
        rx.text(label, class_name="esc-node-label"),
        class_name=rx.cond(_is_lit(node_id), f"{base} esc-lit", base),
        style={"left": left, "top": top},
    )


def _gpu_node(node_id: str, label: str, role: str, left: str, top: str) -> rx.Component:
    """Nodo con GPU: color de carga + resalte."""
    base = f"esc-node esc-role-{role}"
    lit = _is_lit(node_id)
    return rx.box(
        rx.text(role.upper(), class_name="esc-node-role"),
        rx.text(label, class_name="esc-node-label"),
        class_name=rx.match(
            LaimWebState.escenario_gpu,
            (
                "infer",
                rx.cond(lit, f"{base} esc-gpu-infer esc-lit", f"{base} esc-gpu-infer"),
            ),
            (
                "queue",
                rx.cond(lit, f"{base} esc-gpu-queue esc-lit", f"{base} esc-gpu-queue"),
            ),
            (
                "hot",
                rx.cond(lit, f"{base} esc-gpu-hot esc-lit", f"{base} esc-gpu-hot"),
            ),
            rx.cond(lit, f"{base} esc-gpu-idle esc-lit", f"{base} esc-gpu-idle"),
        ),
        style={"left": left, "top": top},
    )


def _wire(edge_id: str, x1: int, y1: int, x2: int, y2: int, kind: str) -> rx.Component:
    """Cable curvo (path) con id para animateMotion, como el Network Monitor."""
    base = f"esc-wire esc-wire-{kind}"
    return rx.el.path(
        id=f"esc-path-{edge_id}",
        d=wire_curve_d(x1, y1, x2, y2),
        class_name=rx.cond(_is_active_wire(edge_id), f"{base} esc-wire-active", base),
    )


def _svg_wires(*children: rx.Component) -> rx.Component:
    """Contenedor SVG del escenario (coordenadas 0–100)."""
    return rx.el.svg(
        *children,
        view_box="0 0 100 100",
        preserve_aspect_ratio="none",
        class_name="esc-wires",
    )


def _wires_for_scenario() -> rx.Component:
    """Cables fijos por escenario (SVG no admite bien foreach de Reflex)."""
    return rx.match(
        LaimWebState.escenario_id,
        (
            "share_multi",
            _svg_wires(
                _wire("c1-share", 16, 78, 50, 22, "ai"),
                _wire("c2-share", 50, 84, 50, 22, "ai"),
                _wire("c3-share", 84, 78, 50, 22, "ai"),
            ),
        ),
        (
            "remote_ssh",
            _svg_wires(
                _wire("ssh1", 24, 50, 78, 20, "ssh"),
                _wire("ssh2", 24, 50, 84, 50, "ssh"),
                _wire("ssh3", 24, 50, 78, 80, "ssh"),
            ),
        ),
        (
            "combo_bastion",
            _svg_wires(
                _wire("c1-sa", 20, 82, 32, 18, "ai"),
                _wire("c2-sb", 50, 86, 68, 18, "ai"),
                _wire("sa-ha", 32, 18, 14, 40, "ssh"),
                _wire("sb-hb", 68, 18, 86, 40, "ssh"),
            ),
        ),
        (
            "mesh_headscale",
            _svg_wires(
                _wire("hs-n1", 50, 48, 18, 18, "mesh"),
                _wire("hs-n2", 50, 48, 82, 18, "mesh"),
                _wire("hs-n3", 50, 48, 18, 82, "mesh"),
                _wire("hs-ts", 50, 48, 82, 82, "mesh"),
            ),
        ),
        _svg_wires(
            _wire("wan-bas", 12, 50, 42, 50, "wan"),
            _wire("bas-share", 42, 50, 80, 24, "ai"),
            _wire("bas-files", 42, 50, 82, 52, "ssh"),
            _wire("bas-pc", 42, 50, 80, 80, "ssh"),
        ),
    )


def _nodes_for_scenario() -> rx.Component:
    """Nodos fijos por escenario (Reflex no admite class_name dinámico en foreach)."""
    return rx.match(
        LaimWebState.escenario_id,
        (
            "share_multi",
            rx.fragment(
                _gpu_node("share", "LAIM Share", "share", "50%", "22%"),
                _plain_node("c1", "Connect A", "connect", "16%", "78%"),
                _plain_node("c2", "Connect B", "connect", "50%", "84%"),
                _plain_node("c3", "Connect C", "connect", "84%", "78%"),
            ),
        ),
        (
            "remote_ssh",
            rx.fragment(
                _plain_node("connect", "LAIM Connect", "connect", "24%", "50%"),
                _plain_node("h1", "Host Linux", "host", "78%", "20%"),
                _plain_node("h2", "Host Windows", "host", "84%", "50%"),
                _plain_node("h3", "Host macOS", "host", "78%", "80%"),
            ),
        ),
        (
            "combo_bastion",
            rx.fragment(
                _gpu_node("sa", "Share GPU-A", "share", "32%", "18%"),
                _gpu_node("sb", "Share GPU-B", "share", "68%", "18%"),
                _plain_node("c1", "Connect 1", "connect", "20%", "82%"),
                _plain_node("c2", "Connect 2", "connect", "50%", "86%"),
                _plain_node("ha", "Host A", "host", "14%", "40%"),
                _plain_node("hb", "Host B", "host", "86%", "40%"),
            ),
        ),
        (
            "mesh_headscale",
            rx.fragment(
                _plain_node("hs", "LAIM + Headscale", "mesh", "50%", "48%"),
                _plain_node("n1", "Nodo remoto 1", "remote", "18%", "18%"),
                _plain_node("n2", "Nodo remoto 2", "remote", "82%", "18%"),
                _plain_node("n3", "Nodo remoto 3", "remote", "18%", "82%"),
                _plain_node("ts", "Cliente Tailscale", "connect", "82%", "82%"),
            ),
        ),
        rx.fragment(
            _plain_node("wan", "Equipo en Internet", "connect", "12%", "50%"),
            _plain_node("bastion", "LAIM bastión", "bastion", "42%", "50%"),
            _gpu_node("share", "Share interno", "share", "80%", "24%"),
            _plain_node("files", "Servidor ficheros", "host", "82%", "52%"),
            _plain_node("pc", "PC interno", "host", "80%", "80%"),
        ),
    )


def _stage() -> rx.Component:
    """Escenario: cables, nodos y motor de paquetes SVG."""
    return rx.box(
        _wires_for_scenario(),
        _nodes_for_scenario(),
        rx.text(
            LaimWebState.escenario_traffic_payload,
            id="esc-traffic-payload",
            class_name="esc-traffic-payload",
        ),
        rx.script(ESCENARIO_TRAFFIC_JS),
        class_name="esc-stage",
        width="100%",
    )


def _queue_job_row(job: dict) -> rx.Component:
    """Fila de job: class_name solo con literales (Reflex no admite item[class_name])."""
    return rx.hstack(
        rx.text(job["client"], class_name="esc-q-client"),
        rx.text(job["kind"], class_name="esc-q-kind"),
        rx.match(
            job["prio"],
            ("P1", rx.box(rx.text("P1"), class_name="esc-q-prio esc-q-prio-p1")),
            ("P3", rx.box(rx.text("P3"), class_name="esc-q-prio esc-q-prio-p3")),
            rx.box(rx.text("P2"), class_name="esc-q-prio esc-q-prio-p2"),
        ),
        rx.match(
            job["status"],
            ("running", rx.box(rx.text("RUNNING"), class_name="esc-q-st esc-q-running")),
            ("done", rx.box(rx.text("DONE"), class_name="esc-q-st esc-q-done")),
            rx.box(rx.text("QUEUED"), class_name="esc-q-st esc-q-queued"),
        ),
        rx.text(job["detail"], class_name="esc-q-detail"),
        spacing="2",
        align_items="center",
        width="100%",
        class_name="esc-q-row",
    )


def _queue_panel() -> rx.Component:
    """Gestor de colas GPU del Share (claim, slots, prioridades)."""
    return rx.cond(
        LaimWebState.escenario_show_queue,
        rx.box(
            rx.hstack(
                rx.text("Gestor de colas · GPU", class_name="esc-q-title"),
                rx.text("Ollama", class_name="esc-q-slots-label"),
                rx.text(LaimWebState.escenario_queue_slots, class_name="esc-q-slots"),
                spacing="3",
                align_items="center",
                flex_wrap="wrap",
                width="100%",
            ),
            rx.text(LaimWebState.escenario_queue_note, class_name="esc-q-note"),
            rx.cond(
                LaimWebState.escenario_queue_empty,
                rx.text("Cola vacía · 2 slots libres · nada preemptivo", class_name="esc-q-empty"),
                rx.vstack(
                    rx.foreach(LaimWebState.escenario_queue_jobs, _queue_job_row),
                    spacing="1",
                    width="100%",
                ),
            ),
            class_name="esc-queue",
            width="100%",
        ),
        rx.fragment(),
    )


def _controls() -> rx.Component:
    """Reproducir, pausar, reiniciar y paso a paso."""
    return rx.hstack(
        rx.cond(
            LaimWebState.escenario_playing,
            rx.button(
                "Pausar",
                on_click=LaimWebState.escenario_pause,
                class_name="crt-btn crt-btn-inline",
            ),
            rx.button(
                "Reproducir",
                on_click=LaimWebState.escenario_play,
                class_name="crt-btn crt-btn-inline",
            ),
        ),
        rx.button(
            "Reiniciar",
            on_click=LaimWebState.escenario_restart,
            class_name="crt-btn crt-btn-inline",
        ),
        rx.button(
            "◀",
            on_click=LaimWebState.escenario_prev_step,
            class_name="crt-btn crt-btn-inline",
        ),
        rx.button(
            "▶",
            on_click=LaimWebState.escenario_next_step,
            class_name="crt-btn crt-btn-inline",
        ),
        rx.text(LaimWebState.escenario_step_label, class_name="esc-step-label"),
        spacing="2",
        align_items="center",
        flex_wrap="wrap",
        width="100%",
    )


def _legend() -> rx.Component:
    """Leyenda de roles y calor de GPU."""
    return rx.hstack(
        rx.box(rx.text("SHARE"), class_name="esc-legend-swatch esc-role-share"),
        rx.box(rx.text("CONNECT"), class_name="esc-legend-swatch esc-role-connect"),
        rx.box(rx.text("REMOTE / HOST"), class_name="esc-legend-swatch esc-role-host"),
        rx.box(rx.text("GPU idle"), class_name="esc-legend-swatch esc-gpu-idle"),
        rx.box(rx.text("GPU infer"), class_name="esc-legend-swatch esc-gpu-infer"),
        rx.box(rx.text("GPU cola"), class_name="esc-legend-swatch esc-gpu-queue"),
        rx.box(rx.text("GPU saturada"), class_name="esc-legend-swatch esc-gpu-hot"),
        rx.box(rx.text("Solicitud →"), class_name="esc-legend-swatch esc-legend-req"),
        rx.box(rx.text("← Respuesta"), class_name="esc-legend-swatch esc-legend-res"),
        spacing="2",
        flex_wrap="wrap",
        width="100%",
        class_name="esc-legend",
    )


def escenarios_content_panel() -> rx.Component:
    """Página Escenarios: selector, diagrama y controles."""
    return rx.box(
        rx.vstack(
            rx.heading(
                "Escenarios",
                size="7",
                color=COLORS["title"],
                class_name="crt-title",
            ),
            rx.text(
                "Guía gráfica de cómo se combinan Share, Connect, Remote y malla. "
                "Reproducir recorre el flujo; Reiniciar vuelve a la fase 1 y lo "
                "repite. En los casos con Share se ve el gestor de colas GPU "
                "(queue_submit, claim, slots Ollama, P2/P3). No arranca solo.",
                class_name="crt-muted esc-intro",
            ),
            rx.hstack(
                rx.vstack(
                    rx.text("Casos", class_name="crt-label"),
                    rx.foreach(LaimWebState.escenario_cards, _selector_card),
                    spacing="2",
                    width="100%",
                    min_width="220px",
                    max_width="280px",
                    class_name="esc-selector",
                ),
                rx.vstack(
                    rx.heading(
                        LaimWebState.escenario_title,
                        size="5",
                        color=COLORS["title"],
                    ),
                    rx.text(LaimWebState.escenario_summary, class_name="crt-muted"),
                    _stage(),
                    rx.text(LaimWebState.escenario_caption, class_name="esc-caption"),
                    _queue_panel(),
                    rx.text(LaimWebState.escenario_command, class_name="esc-command"),
                    _controls(),
                    _legend(),
                    spacing="3",
                    width="100%",
                    min_width="0",
                    flex="1",
                ),
                spacing="4",
                align_items="start",
                width="100%",
                flex_wrap="wrap",
            ),
            spacing="3",
            width="100%",
            align_items="stretch",
        ),
        class_name="crt-escenarios crt-readable-zone",
        width="100%",
        padding="1.25em",
    )

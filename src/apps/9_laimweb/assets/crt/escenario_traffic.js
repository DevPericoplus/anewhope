(function () {
  if (window.__escTrafficWatch) return;
  window.__escTrafficWatch = true;
  var lastGen = "";
  var scheduled = false;
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
    var stepS = Number((svg && svg.__escStepS) || 0);
    var usable = stepS > 0 ? Math.max(2.4, stepS - 0.85) : 0;
    var dur = pkt.primary
      ? (usable > 0 ? usable * 0.82 : 2.45)
      : (usable > 0 ? Math.max(2.15, usable * 0.72) : 2.15);
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
      badge.setAttribute("font-size", "3.5");
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
    svg.__escStepS = Number(cfg.step_s || 0);
    svg.querySelectorAll("g.traffic-packet").forEach(function (node) { node.remove(); });
    (cfg.packets || []).forEach(function (pkt, idx) {
      animateOne(svg, pkt, idx * 0.08);
    });
  }

  function pathsReady(svg, packets) {
    var i;
    for (i = 0; i < packets.length; i++) {
      if (!svg.querySelector("#esc-path-" + packets[i].edge)) return false;
    }
    return true;
  }

  function attempt() {
    var el = document.getElementById("esc-traffic-payload");
    if (!el) return;
    var raw = (el.textContent || "").trim();
    if (!raw) return;
    var cfg;
    try {
      cfg = JSON.parse(raw);
    } catch (err) {
      return;
    }
    var gen = String(cfg.gen || "");
    if (!gen || gen === lastGen) return;
    var svg = document.querySelector(".esc-stage svg.esc-wires");
    var packets = cfg.packets || [];
    if (!svg) return;
    var ready = pathsReady(svg, packets);
    if (!ready) return;
    lastGen = gen;
    play(cfg);
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(function () {
      scheduled = false;
      attempt();
    });
  }

  var obs = new MutationObserver(schedule);
  obs.observe(document.documentElement, {
    childList: true,
    subtree: true,
    characterData: true
  });
  schedule();
})();

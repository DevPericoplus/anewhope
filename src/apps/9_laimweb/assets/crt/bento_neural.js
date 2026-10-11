(function () {
  if (window.__LAIM_BENTO_NEURAL__) {
    return;
  }
  window.__LAIM_BENTO_NEURAL__ = true;

  var LAYOUT = [
    { glyph: "core", x: 50, y: 42 },
    { glyph: "shield", x: 20, y: 26 },
    { glyph: "mesh", x: 80, y: 24 },
    { glyph: "soul", x: 18, y: 58 },
    { glyph: "tools", x: 82, y: 58 },
    { glyph: "hardware", x: 36, y: 78 },
    { glyph: "steps", x: 64, y: 76 },
    { glyph: "gerbil", x: 32, y: 46 },
    { glyph: "idea", x: 70, y: 46 }
  ];

  var EDGES = [
    [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8],
    [1, 3], [1, 7], [2, 4], [2, 8], [3, 5], [4, 6], [5, 6], [7, 8]
  ];

  var travelMs = 1400;
  var lastVisited = [];
  var current = 0;
  var raf = 0;
  var started = 0;
  var fromIdx = 0;
  var toIdx = 0;
  var phase = "hold";
  var holdUntil = 0;
  var hoverHold = false;

  function prefersReduced() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function gridEl() {
    return document.querySelector(".crt-bento-grid");
  }

  function stageSvg() {
    return document.getElementById("crt-neural-svg");
  }

  function isPaused() {
    var grid = gridEl();
    return !grid || grid.getAttribute("data-paused") === "true" || hoverHold;
  }

  function tileForGlyph(glyph) {
    return document.querySelector('.crt-bento-tile[data-bento-glyph="' + glyph + '"]');
  }

  function pauseMsFor(idx) {
    var node = LAYOUT[idx];
    var tile = tileForGlyph(node.glyph);
    var raw = tile && tile.getAttribute("data-pause");
    var n = raw ? parseInt(raw, 10) : 1600;
    return isNaN(n) ? 1600 : n;
  }

  function pickNext(from) {
    var avoid = lastVisited.slice(-2);
    var weights = LAYOUT.map(function (_, i) {
      if (i === from || avoid.indexOf(i) !== -1) {
        return 0;
      }
      var tile = tileForGlyph(LAYOUT[i].glyph);
      var span = tile ? tile.getAttribute("data-span") || "1x1" : "1x1";
      return span === "2x1" || span === "1x2" ? 2.4 : 1;
    });
    var sum = weights.reduce(function (a, b) { return a + b; }, 0);
    if (sum <= 0) {
      return (from + 1) % LAYOUT.length;
    }
    var r = Math.random() * sum;
    for (var i = 0; i < weights.length; i++) {
      r -= weights[i];
      if (r <= 0) {
        return i;
      }
    }
    return (from + 1) % LAYOUT.length;
  }

  function curve(a, b) {
    var jitter = (Math.random() - 0.5) * 18;
    var mx = (a.x + b.x) / 2 + jitter;
    var my = (a.y + b.y) / 2 + (Math.random() - 0.5) * 14;
    return "M " + a.x + " " + a.y + " Q " + mx + " " + my + " " + b.x + " " + b.y;
  }

  function pointOnQuad(a, c, b, t) {
    var u = 1 - t;
    return {
      x: u * u * a.x + 2 * u * t * c.x + t * t * b.x,
      y: u * u * a.y + 2 * u * t * c.y + t * t * b.y
    };
  }

  function parseQuad(d) {
    var parts = d.replace(/[MQ]/g, " ").trim().split(/\s+/).map(Number);
    return {
      a: { x: parts[0], y: parts[1] },
      c: { x: parts[2], y: parts[3] },
      b: { x: parts[4], y: parts[5] }
    };
  }

  function setLit(idx) {
    document.querySelectorAll(".crt-bento-tile.crt-bento-lit").forEach(function (el) {
      el.classList.remove("crt-bento-lit");
    });
    document.querySelectorAll(".crt-neural-node.is-lit").forEach(function (el) {
      el.classList.remove("is-lit");
    });
    if (idx < 0) {
      return;
    }
    var node = LAYOUT[idx];
    var tile = tileForGlyph(node.glyph);
    if (tile) {
      tile.classList.add("crt-bento-lit");
    }
    var mini = document.querySelector('.crt-neural-node[data-glyph="' + node.glyph + '"]');
    if (mini) {
      mini.classList.add("is-lit");
    }
  }

  function injectSprite(done) {
    if (document.getElementById("crt-bento-sprite")) {
      done();
      return;
    }
    fetch("/crt/bento_glyphs.svg")
      .then(function (r) { return r.text(); })
      .then(function (txt) {
        var wrap = document.createElement("div");
        wrap.id = "crt-bento-sprite";
        wrap.setAttribute("hidden", "true");
        wrap.innerHTML = txt;
        document.body.appendChild(wrap);
        done();
      })
      .catch(function () { done(); });
  }

  function ensureScene() {
    var svg = stageSvg();
    if (!svg || svg.getAttribute("data-ready") === "1") {
      return svg;
    }
    svg.setAttribute("viewBox", "0 0 100 100");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    var ns = "http://www.w3.org/2000/svg";
    EDGES.forEach(function (pair) {
      var path = document.createElementNS(ns, "path");
      path.setAttribute("class", "crt-neural-edge");
      path.setAttribute("data-from", String(pair[0]));
      path.setAttribute("data-to", String(pair[1]));
      path.setAttribute("d", curve(LAYOUT[pair[0]], LAYOUT[pair[1]]));
      path.setAttribute("fill", "none");
      svg.appendChild(path);
    });
    LAYOUT.forEach(function (node, i) {
      var g = document.createElementNS(ns, "g");
      g.setAttribute("class", "crt-neural-node");
      g.setAttribute("data-glyph", node.glyph);
      g.setAttribute("data-idx", String(i));
      g.setAttribute("transform", "translate(" + node.x + " " + node.y + ")");
      var use = document.createElementNS(ns, "use");
      use.setAttribute("href", "#glyph-" + node.glyph);
      use.setAttribute("x", "-5");
      use.setAttribute("y", "-5");
      use.setAttribute("width", "10");
      use.setAttribute("height", "10");
      g.appendChild(use);
      g.addEventListener("mouseenter", function () {
        hoverHold = true;
        current = i;
        setLit(i);
      });
      g.addEventListener("mouseleave", function () {
        hoverHold = false;
      });
      svg.appendChild(g);
    });
    var pulse = document.createElementNS(ns, "circle");
    pulse.setAttribute("id", "crt-neural-pulse");
    pulse.setAttribute("r", "1.6");
    pulse.setAttribute("class", "crt-neural-pulse");
    svg.appendChild(pulse);
    svg.setAttribute("data-ready", "1");
    return svg;
  }

  function edgePath(from, to) {
    var svg = stageSvg();
    if (!svg) {
      return null;
    }
    return svg.querySelector(
      '.crt-neural-edge[data-from="' + from + '"][data-to="' + to + '"],' +
      '.crt-neural-edge[data-from="' + to + '"][data-to="' + from + '"]'
    );
  }

  function bindTiles() {
    document.querySelectorAll(".crt-bento-tile[data-bento-glyph]").forEach(function (tile) {
      if (tile.getAttribute("data-neural-bound") === "1") {
        return;
      }
      tile.setAttribute("data-neural-bound", "1");
      tile.addEventListener("mouseenter", function () {
        var glyph = tile.getAttribute("data-bento-glyph");
        var idx = LAYOUT.findIndex(function (n) { return n.glyph === glyph; });
        if (idx >= 0) {
          hoverHold = true;
          current = idx;
          setLit(idx);
        }
      });
      tile.addEventListener("mouseleave", function () {
        hoverHold = false;
      });
      tile.addEventListener("focus", function () {
        var glyph = tile.getAttribute("data-bento-glyph");
        var idx = LAYOUT.findIndex(function (n) { return n.glyph === glyph; });
        if (idx >= 0) {
          hoverHold = true;
          current = idx;
          setLit(idx);
        }
      });
      tile.addEventListener("blur", function () {
        hoverHold = false;
      });
    });
  }

  function startTravel() {
    fromIdx = current;
    toIdx = pickNext(fromIdx);
    var path = edgePath(fromIdx, toIdx);
    if (!path) {
      current = toIdx;
      phase = "hold";
      holdUntil = performance.now() + pauseMsFor(current);
      setLit(current);
      return;
    }
    path.setAttribute("data-active", "1");
    started = performance.now();
    phase = "travel";
  }

  function tick(now) {
    raf = requestAnimationFrame(tick);
    var svg = ensureScene();
    if (!svg || prefersReduced()) {
      setLit(-1);
      return;
    }
    bindTiles();
    if (isPaused()) {
      setLit(current);
      return;
    }
    var pulse = document.getElementById("crt-neural-pulse");
    if (phase === "hold") {
      setLit(current);
      if (now >= holdUntil) {
        lastVisited.push(current);
        if (lastVisited.length > 4) {
          lastVisited.shift();
        }
        document.querySelectorAll(".crt-neural-edge[data-active]").forEach(function (el) {
          el.removeAttribute("data-active");
        });
        startTravel();
      }
      if (pulse) {
        pulse.setAttribute("cx", String(LAYOUT[current].x));
        pulse.setAttribute("cy", String(LAYOUT[current].y));
      }
      return;
    }
    var path = edgePath(fromIdx, toIdx);
    var t = Math.min(1, (now - started) / travelMs);
    var eased = t * t * (3 - 2 * t);
    if (path && pulse) {
      var q = parseQuad(path.getAttribute("d"));
      var pt = pointOnQuad(q.a, q.c, q.b, fromIdx < toIdx || path.getAttribute("data-from") === String(fromIdx) ? eased : 1 - eased);
      if (path.getAttribute("data-from") === String(toIdx)) {
        pt = pointOnQuad(q.a, q.c, q.b, 1 - eased);
      }
      pulse.setAttribute("cx", String(pt.x));
      pulse.setAttribute("cy", String(pt.y));
    }
    if (t >= 1) {
      current = toIdx;
      phase = "hold";
      holdUntil = now + pauseMsFor(current);
      setLit(current);
    }
  }

  function boot() {
    if (!gridEl() || !stageSvg()) {
      return;
    }
    injectSprite(function () {
      ensureScene();
      bindTiles();
      current = 0;
      phase = "hold";
      holdUntil = performance.now() + pauseMsFor(0);
      setLit(0);
      if (!prefersReduced() && !raf) {
        raf = requestAnimationFrame(tick);
      }
    });
  }

  function watch() {
    boot();
    var root = document.querySelector(".crt-shell") || document.body;
    var obs = new MutationObserver(function () {
      if (gridEl() && stageSvg() && (!stageSvg().getAttribute("data-ready"))) {
        boot();
      }
    });
    obs.observe(root, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", watch);
  } else {
    watch();
  }
})();

(function () {
  if (window.LAIMBentoNeural && window.LAIMBentoNeural.restart) {
    window.LAIMBentoNeural.restart();
    return;
  }

  var HOLD_MS = 4000;
  var APPROACH_MS = 3200;
  var RETREAT_MS = 2200;
  var ORBIT_MS = 1800;
  var PULSE_COUNT = 5;

  var nodes = [];
  var edges = [];
  var titled = [];
  var pulses = [];
  var focus = 0;
  var phase = "orbit";
  var phaseStart = 0;
  var yaw = 0.55;
  var pitch = 0.28;
  var dist = 4.35;
  var look = { x: 0, y: 0, z: 0 };
  var hoverHold = false;
  var raf = 0;
  var lastTs = 0;
  var ready = false;
  var boundWorld = null;
  var boundCanvas = null;
  var resizeObs = null;
  var watching = false;
  var polling = false;

  function prefersReduced() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function worldEl() {
    return document.querySelector(".crt-neural-world");
  }

  function canvasEl() {
    return document.getElementById("crt-neural-canvas");
  }

  function homeEl() {
    return document.querySelector(".crt-inicio-home");
  }

  function sceneHasSize(size) {
    return !!(size && size.w > 48 && size.h > 48);
  }

  function elementHasSize(el) {
    if (!el || !el.getBoundingClientRect) {
      return false;
    }
    var rect = el.getBoundingClientRect();
    return rect.width > 48 && rect.height > 48;
  }

  function scenePrepared() {
    return !!(worldEl() && canvasEl() &&
      (elementHasSize(worldEl()) || elementHasSize(canvasEl())));
  }

  function homeShowsSpinner() {
    var home = homeEl();
    return !!(home && !home.classList.contains("is-neural-ready"));
  }

  function markSceneReady(on) {
    var home = homeEl();
    var world = worldEl();
    if (home) {
      home.classList.toggle("is-neural-ready", on);
    }
    if (world) {
      world.classList.toggle("is-ready", on);
    }
  }

  function bindResize() {
    var canvas = canvasEl();
    if (!canvas || canvas === boundCanvas) {
      return;
    }
    boundCanvas = canvas;
    if (resizeObs) {
      resizeObs.disconnect();
      resizeObs = null;
    }
    if (!window.ResizeObserver) {
      return;
    }
    resizeObs = new ResizeObserver(function () {
      if (ready) {
        var size = draw(currentCam());
        if (sceneHasSize(size)) {
          markSceneReady(true);
        }
      }
    });
    resizeObs.observe(canvas);
  }

  function isPaused() {
    var world = worldEl();
    return !world || world.getAttribute("data-paused") === "true";
  }

  function cssColor(name, fallback) {
    var style = getComputedStyle(document.documentElement);
    return (style.getPropertyValue(name) || "").trim() || fallback;
  }

  function layerColumn(count, x, spreadY, spreadZ, seed) {
    var out = [];
    var i;
    for (i = 0; i < count; i++) {
      var t = count === 1 ? 0.5 : i / (count - 1);
      var wobble = Math.sin((seed + i) * 1.7) * spreadZ;
      out.push({
        x: x,
        y: (t - 0.5) * spreadY,
        z: wobble
      });
    }
    return out;
  }

  function titleTiles() {
    return Array.prototype.slice.call(
      document.querySelectorAll(".crt-bento-tile[data-bento-glyph]")
    ).sort(function (a, b) {
      return (parseInt(a.getAttribute("data-title-index"), 10) || 0) -
        (parseInt(b.getAttribute("data-title-index"), 10) || 0);
    });
  }

  function buildNetwork() {
    nodes = [];
    edges = [];
    titled = [];
    var tiles = titleTiles();
    var left = layerColumn(6, -1.35, 2.15, 0.55, 1);
    var hidden = layerColumn(7, -0.4, 2.35, 0.7, 4);
    var mid = layerColumn(5, 0.45, 2.05, 0.5, 8);
    var right = layerColumn(4, 1.35, 1.85, 0.45, 12);
    left.forEach(function (p) {
      nodes.push({ x: p.x, y: p.y, z: p.z, titled: false });
    });
    hidden.forEach(function (p) {
      nodes.push({ x: p.x, y: p.y, z: p.z, titled: false });
    });
    var leftCount = 6;
    var hiddenCount = 7;
    tiles.forEach(function (el, i) {
      var pos = i < 5 ? mid[i] : right[i - 5];
      var node = {
        x: pos.x,
        y: pos.y,
        z: pos.z,
        titled: true,
        el: el,
        glyph: el.getAttribute("data-bento-glyph")
      };
      nodes.push(node);
      titled.push(node);
    });
    function connectLayers(a0, aN, b0, bN) {
      var a, b;
      for (a = a0; a < aN; a++) {
        for (b = b0; b < bN; b++) {
          if ((a + b) % 3 === 0) {
            continue;
          }
          edges.push({ a: a, b: b });
        }
      }
    }
    connectLayers(0, leftCount, leftCount, leftCount + hiddenCount);
    connectLayers(leftCount, leftCount + hiddenCount, leftCount + hiddenCount, leftCount + hiddenCount + 5);
    connectLayers(leftCount + hiddenCount, leftCount + hiddenCount + 5, leftCount + hiddenCount + 5, nodes.length);
    return titled.length > 0;
  }

  function rotY(p, a) {
    var c = Math.cos(a);
    var s = Math.sin(a);
    return { x: p.x * c - p.z * s, y: p.y, z: p.x * s + p.z * c };
  }

  function rotX(p, a) {
    var c = Math.cos(a);
    var s = Math.sin(a);
    return { x: p.x, y: p.y * c - p.z * s, z: p.y * s + p.z * c };
  }

  function project(p, cam, w, h) {
    var q = rotY({ x: p.x - cam.look.x, y: p.y - cam.look.y, z: p.z - cam.look.z }, -cam.yaw);
    q = rotX(q, -cam.pitch);
    var zz = q.z + cam.dist;
    if (zz < 0.35) {
      zz = 0.35;
    }
    var scale = (1.65 * Math.min(w, h) * 0.5) / zz;
    return {
      x: w * 0.5 + q.x * scale,
      y: h * 0.52 + q.y * scale,
      z: zz,
      scale: scale
    };
  }

  // Acelera al salir, cruza a la velocidad actual y aterriza más lento.
  function easeApproach(t) {
    if (t <= 0) {
      return 0;
    }
    if (t >= 1) {
      return 1;
    }
    var accelEnd = 0.2;
    var cruiseEnd = 0.52;
    var accelDist = 0.14;
    var cruiseDist = 0.46;
    if (t < accelEnd) {
      var u = t / accelEnd;
      return accelDist * u * u;
    }
    if (t < cruiseEnd) {
      return accelDist + cruiseDist * ((t - accelEnd) / (cruiseEnd - accelEnd));
    }
    var u = (t - cruiseEnd) / (1 - cruiseEnd);
    return accelDist + cruiseDist + (1 - accelDist - cruiseDist) * (1 - Math.pow(1 - u, 3));
  }

  function easeRetreat(t) {
    if (t <= 0) {
      return 0;
    }
    if (t >= 1) {
      return 1;
    }
    var u = t * t;
    return u * (2 - t);
  }

  function focusAmount() {
    var now = performance.now();
    if (phase === "hold") {
      return 1;
    }
    if (phase === "approach") {
      return easeApproach(Math.min(1, (now - phaseStart) / APPROACH_MS));
    }
    if (phase === "retreat") {
      return 1 - easeRetreat(Math.min(1, (now - phaseStart) / RETREAT_MS));
    }
    return 0;
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function angLerp(a, b, t) {
    var d = b - a;
    while (d > Math.PI) {
      d -= Math.PI * 2;
    }
    while (d < -Math.PI) {
      d += Math.PI * 2;
    }
    return a + d * t;
  }

  function cameraForFocus(idx) {
    var node = titled[idx] || titled[0];
    if (!node) {
      return orbitCam();
    }
    return {
      yaw: Math.atan2(node.x, node.z + 0.08),
      pitch: 0.08 + node.y * 0.05,
      dist: 0.86,
      look: { x: node.x * 0.9, y: node.y * 0.92, z: node.z * 0.7 }
    };
  }

  function orbitCam() {
    return {
      yaw: yaw,
      pitch: 0.3,
      dist: 4.35,
      look: { x: 0, y: 0.05, z: 0 }
    };
  }

  function mixCam(a, b, t) {
    return {
      yaw: angLerp(a.yaw, b.yaw, t),
      pitch: lerp(a.pitch, b.pitch, t),
      dist: lerp(a.dist, b.dist, t),
      look: {
        x: lerp(a.look.x, b.look.x, t),
        y: lerp(a.look.y, b.look.y, t),
        z: lerp(a.look.z, b.look.z, t)
      }
    };
  }

  function currentCam() {
    var orbit = orbitCam();
    var close = cameraForFocus(focus);
    var now = performance.now();
    var u = 0;
    if (phase === "orbit") {
      return orbit;
    }
    if (phase === "approach") {
      u = easeApproach(Math.min(1, (now - phaseStart) / APPROACH_MS));
      return mixCam(orbit, close, u);
    }
    if (phase === "hold") {
      return close;
    }
    u = easeRetreat(Math.min(1, (now - phaseStart) / RETREAT_MS));
    return mixCam(close, orbit, u);
  }

  function setLit(idx) {
    titled.forEach(function (node, i) {
      if (!node.el) {
        return;
      }
      node.el.classList.toggle("crt-bento-lit", i === idx);
      node.el.classList.toggle("crt-neural-near", i === idx);
    });
  }

  function spawnPulse(preferFocus) {
    var choices = edges;
    if (preferFocus && titled[focus]) {
      var target = nodes.indexOf(titled[focus]);
      var inward = edges.filter(function (e) { return e.b === target || e.a === target; });
      if (inward.length) {
        choices = inward;
      }
    }
    var edge = choices[Math.floor(Math.random() * choices.length)];
    if (!edge) {
      return;
    }
    pulses.push({
      a: edge.a,
      b: edge.b,
      t: 0,
      speed: 0.32 + Math.random() * 0.28
    });
  }

  function bindHover() {
    titled.forEach(function (node, i) {
      if (!node.el || node.el.getAttribute("data-neural-bound") === "1") {
        return;
      }
      node.el.setAttribute("data-neural-bound", "1");
      node.el.addEventListener("mouseenter", function () {
        hoverHold = true;
        focus = i;
        setLit(i);
      });
      node.el.addEventListener("focus", function () {
        hoverHold = true;
        focus = i;
        setLit(i);
      });
      node.el.addEventListener("mouseleave", function () {
        hoverHold = false;
      });
      node.el.addEventListener("blur", function () {
        hoverHold = false;
      });
    });
  }

  function resizeCanvas(canvas) {
    var rect = canvas.getBoundingClientRect();
    if (rect.width < 48 || rect.height < 48) {
      var world = worldEl();
      if (world) {
        var worldRect = world.getBoundingClientRect();
        if (worldRect.width > 48 && worldRect.height > 48) {
          rect = worldRect;
        }
      }
    }
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = Math.max(1, Math.floor(rect.width * dpr));
    var h = Math.max(1, Math.floor(rect.height * dpr));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    return { w: canvas.width, h: canvas.height, dpr: dpr };
  }

  function draw(cam) {
    var canvas = canvasEl();
    if (!canvas) {
      return null;
    }
    var size = resizeCanvas(canvas);
    var ctx = canvas.getContext("2d");
    var w = size.w;
    var h = size.h;
    ctx.clearRect(0, 0, w, h);
    var accent = cssColor("--crt-accent", "#39ff14");
    var strong = cssColor("--crt-accent-strong", "#9cff57");
    var border = cssColor("--crt-border", "#145214");
    var projected = nodes.map(function (n) { return project(n, cam, w, h); });
    var order = edges.map(function (_, i) { return i; }).sort(function (i, j) {
      return (projected[edges[i].a].z + projected[edges[i].b].z) -
        (projected[edges[j].a].z + projected[edges[j].b].z);
    });
    order.forEach(function (ei) {
      var e = edges[ei];
      var pa = projected[e.a];
      var pb = projected[e.b];
      var depth = (pa.z + pb.z) * 0.5;
      var alpha = Math.max(0.08, Math.min(0.45, 1.8 / depth));
      var active = pulses.some(function (p) { return p.a === e.a && p.b === e.b; });
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.strokeStyle = active ? accent : border;
      ctx.globalAlpha = active ? Math.min(0.9, alpha + 0.4) : alpha;
      ctx.lineWidth = active ? 1.6 * size.dpr : 0.9 * size.dpr;
      ctx.stroke();
    });
    ctx.globalAlpha = 1;
    nodes.forEach(function (node, i) {
      if (node.titled) {
        return;
      }
      var p = projected[i];
      var r = Math.max(1.4, Math.min(4.2, p.scale * 0.028));
      var glow = pulses.some(function (pulse) {
        return (pulse.a === i || pulse.b === i) && pulse.t > 0.15 && pulse.t < 0.95;
      });
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fillStyle = glow ? strong : accent;
      ctx.globalAlpha = glow ? 0.95 : 0.45;
      ctx.fill();
      if (glow) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, r * 2.4, 0, Math.PI * 2);
        ctx.globalAlpha = 0.18;
        ctx.fillStyle = accent;
        ctx.fill();
      }
    });
    pulses.forEach(function (pulse) {
      var a = projected[pulse.a];
      var b = projected[pulse.b];
      var t = pulse.t;
      var x = lerp(a.x, b.x, t);
      var y = lerp(a.y, b.y, t);
      ctx.beginPath();
      ctx.arc(x, y, 3.1 * size.dpr, 0, Math.PI * 2);
      ctx.globalAlpha = 0.95;
      ctx.fillStyle = strong;
      ctx.shadowColor = accent;
      ctx.shadowBlur = 12 * size.dpr;
      ctx.fill();
      ctx.shadowBlur = 0;
    });
    ctx.globalAlpha = 1;
    titled.forEach(function (node, i) {
      var p = project(node, cam, w, h);
      if (!node.el) {
        return;
      }
      var amount = i === focus ? focusAmount() : 0;
      var near = amount > 0.12;
      var scale = Math.max(0.52, Math.min(1.18, 46 / p.z)) + amount * 1.22;
      node.el.style.left = (p.x / size.dpr) + "px";
      node.el.style.top = (p.y / size.dpr) + "px";
      node.el.style.transform = "translate(-50%, -50%) scale(" + scale + ")";
      node.el.style.zIndex = String(Math.round(4000 - p.z * 40));
      node.el.style.opacity = near ? "1" : String(Math.max(0.4, Math.min(0.82, 2.15 / p.z)));
      node.el.style.setProperty("--crt-focus", amount.toFixed(3));
      var label = node.el.querySelector(".crt-bento-label");
      if (label) {
        label.style.fontSize = (0.74 + amount * 0.7) + "rem";
        label.style.fontWeight = String(400 + Math.round(amount * 300));
        label.style.letterSpacing = (0.08 - amount * 0.03).toFixed(3) + "em";
        if (amount > 0.18) {
          label.style.textShadow =
            "0 1px 2px rgba(0,0,0," + (0.2 + amount * 0.22).toFixed(2) + "), " +
            "0 2px 8px rgba(0,0,0," + (0.12 + amount * 0.18).toFixed(2) + ")";
        } else {
          label.style.textShadow = "";
        }
      }
    });
    return size;
  }

  function advancePhase(now) {
    if (!titled.length) {
      phase = "orbit";
      return;
    }
    if (phase === "orbit" && now - phaseStart >= ORBIT_MS) {
      phase = "approach";
      phaseStart = now;
      setLit(focus);
      return;
    }
    if (phase === "approach" && now - phaseStart >= APPROACH_MS) {
      phase = "hold";
      phaseStart = now;
      setLit(focus);
      return;
    }
    if (phase === "hold" && !hoverHold && now - phaseStart >= HOLD_MS) {
      phase = "retreat";
      phaseStart = now;
      return;
    }
    if (phase === "retreat" && now - phaseStart >= RETREAT_MS) {
      focus = (focus + 1) % titled.length;
      phase = "orbit";
      phaseStart = now;
      setLit(-1);
    }
  }

  function sceneStale() {
    var world = worldEl();
    if (!world || world !== boundWorld) {
      return true;
    }
    if (titled.length !== titleTiles().length) {
      return true;
    }
    if (titled.some(function (node) { return !node.el || !node.el.isConnected; })) {
      return true;
    }
    return titleTiles().some(function (el) { return !el.isConnected; });
  }

  function revealIfPrepared() {
    if (!scenePrepared()) {
      return false;
    }
    if (!ready || sceneStale()) {
      ready = false;
      boundWorld = null;
      boundCanvas = null;
      if (!boot()) {
        return false;
      }
    }
    var size = draw(currentCam());
    if (sceneHasSize(size) || scenePrepared()) {
      markSceneReady(true);
      return true;
    }
    return false;
  }

  function pollUntilShown() {
    if (!raf) {
      raf = requestAnimationFrame(tick);
    }
    if (polling) {
      return;
    }
    polling = true;
    function step() {
      if (revealIfPrepared()) {
        polling = false;
        return;
      }
      if (homeShowsSpinner() || worldEl()) {
        requestAnimationFrame(step);
        return;
      }
      polling = false;
    }
    requestAnimationFrame(step);
  }

  function restart() {
    lastTs = 0;
    if (ready && !sceneStale() && scenePrepared()) {
      markSceneReady(true);
      if (!raf) {
        raf = requestAnimationFrame(tick);
      }
      return;
    }
    ready = false;
    boundWorld = null;
    boundCanvas = null;
    markSceneReady(false);
    pollUntilShown();
  }

  function ensure() {
    if (ready && !sceneStale() && scenePrepared()) {
      markSceneReady(true);
      if (!raf) {
        raf = requestAnimationFrame(tick);
      }
      return;
    }
    pollUntilShown();
  }

  function tick(now) {
    raf = requestAnimationFrame(tick);
    if (ready && sceneStale()) {
      ready = false;
      boundWorld = null;
      boundCanvas = null;
      markSceneReady(false);
    }
    if (homeShowsSpinner() || !ready) {
      if (revealIfPrepared()) {
        // La escena ya pinta: el spinner debe desaparecer en este frame.
      } else if (!ready) {
        return;
      }
    }
    if (!ready && !boot()) {
      return;
    }
    bindResize();
    var dt = lastTs ? Math.min(0.05, (now - lastTs) / 1000) : 0.016;
    lastTs = now;
    bindHover();
    var size;
    if (prefersReduced()) {
      yaw = 0.7;
      phase = "orbit";
      size = draw(orbitCam());
      titled.forEach(function (node) {
        if (node.el) {
          node.el.style.opacity = "1";
        }
      });
      if (sceneHasSize(size) || scenePrepared()) {
        markSceneReady(true);
      }
      return;
    }
    if (!isPaused() && !(hoverHold && phase === "hold")) {
      if (phase === "orbit" || phase === "retreat") {
        yaw += dt * 0.22;
      }
      advancePhase(now);
    }
    while (pulses.length < PULSE_COUNT) {
      spawnPulse(phase === "hold" || phase === "approach");
    }
    pulses.forEach(function (p) {
      p.t += p.speed * dt * (phase === "hold" ? 1.15 : 1);
    });
    pulses = pulses.filter(function (p) { return p.t < 1; });
    if (hoverHold) {
      setLit(focus);
    } else if (!isPaused()) {
      setLit(phase === "orbit" ? -1 : focus);
    }
    size = draw(currentCam());
    if (sceneHasSize(size) || scenePrepared()) {
      markSceneReady(true);
    }
  }

  function boot() {
    if (!worldEl() || !canvasEl()) {
      return false;
    }
    if (!buildNetwork()) {
      return false;
    }
    ready = true;
    boundWorld = worldEl();
    focus = 0;
    phase = "orbit";
    phaseStart = performance.now();
    setLit(-1);
    bindResize();
    return true;
  }

  function watch() {
    if (!raf) {
      raf = requestAnimationFrame(tick);
    }
    if (watching) {
      pollUntilShown();
      return;
    }
    watching = true;
    var root = document.documentElement;
    var obs = new MutationObserver(function () {
      if (homeShowsSpinner() || (worldEl() && !document.querySelector(".crt-inicio-home.is-neural-ready"))) {
        pollUntilShown();
      }
    });
    obs.observe(root, { childList: true, subtree: true });
    window.addEventListener("resize", function () {
      revealIfPrepared();
    });
    window.addEventListener("visibilitychange", function () {
      if (!document.hidden) {
        pollUntilShown();
      }
    });
    setInterval(function () {
      if (homeShowsSpinner() || (worldEl() && !document.querySelector(".crt-inicio-home.is-neural-ready"))) {
        pollUntilShown();
      }
    }, 400);
    pollUntilShown();
  }

  window.LAIMBentoNeural = { restart: restart, ensure: ensure };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", watch);
  } else {
    watch();
  }
})();

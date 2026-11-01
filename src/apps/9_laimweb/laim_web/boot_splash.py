"""Pantalla de arranque, en el HTML, antes de que Reflex pinte.

Mismo papel que la página `/boot` de laim (`LAIM se está preparando`):
el navegador tiene contenido en el primer byte, no un fondo negro hasta
que llega el bundle.
"""

from __future__ import annotations

import reflex as rx

from laim_web.visual_assets import ESCENARIO_SCRIPT_SRC, NEURAL_SCRIPT_SRC

BOOT_INLINE = r"""
(function () {
  var css = ''
    + 'html,body{background:#031207;}'
    + '#laim-boot{position:fixed!important;inset:0!important;z-index:100000!important;'
    + 'display:flex!important;flex-direction:column!important;align-items:center!important;'
    + 'justify-content:center!important;background:#031207!important;margin:0!important;'
    + 'padding:0!important;text-align:center!important;}'
    + '#laim-boot .laim-boot-card{display:flex!important;flex-direction:column!important;'
    + 'align-items:center!important;justify-content:center!important;text-align:center!important;'
    + 'max-width:28rem;padding:2rem;}'
    + '#laim-boot h1{display:block!important;position:static!important;width:auto!important;'
    + 'max-width:24rem!important;margin:0 0 8px!important;font:600 1.15rem/1.4 '
    + 'Inconsolata,ui-monospace,monospace!important;color:#d8ffd8!important;}'
    + '#laim-boot p{display:block!important;position:static!important;width:auto!important;'
    + 'margin:0!important;font:16px/1.5 Inconsolata,ui-monospace,monospace!important;'
    + 'color:#7dcc7d!important;}'
    + '#laim-boot{transition:opacity .22s ease;}'
    + '.laim-boot-bar{width:220px;height:4px;margin:0 auto 18px!important;background:#14301c;'
    + 'border-radius:999px;overflow:hidden;}'
    + '.laim-boot-bar-fill{height:100%;width:8%;background:#3dff7a;transition:width .35s ease;}'
    + '@media (prefers-reduced-motion: reduce){'
    + '.laim-boot-bar-fill{transition:none!important;}#laim-boot{transition:none!important;}}';
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);
  var root = document.createElement('div');
  root.id = 'laim-boot';
  root.setAttribute('role', 'status');
  root.setAttribute('aria-live', 'polite');
  root.innerHTML = '<div class="laim-boot-card">'
    + '<div id="laim-boot-bar" class="laim-boot-bar" role="progressbar"'
    + ' aria-valuemin="0" aria-valuemax="100" aria-valuenow="8"'
    + ' aria-label="Carga de la página">'
    + '<div id="laim-boot-fill" class="laim-boot-bar-fill"></div></div>'
    + '<h1>LAIM se está preparando</h1>'
    + '<p id="laim-boot-msg">Preparando la interfaz…</p>'
    + '</div>';
  document.documentElement.appendChild(root);
  function setProgress(n) {
    if (n < 0) n = 0;
    if (n > 100) n = 100;
    var fill = document.getElementById('laim-boot-fill');
    var bar = document.getElementById('laim-boot-bar');
    if (fill) fill.style.width = n + '%';
    if (bar) bar.setAttribute('aria-valuenow', String(Math.round(n)));
  }
  setProgress(8);
  function shellReady() {
    return !!document.querySelector('.crt-shell');
  }
  function dismiss() {
    setProgress(100);
    var el = document.getElementById('laim-boot');
    if (!el || el.getAttribute('data-gone') === '1') return;
    el.setAttribute('data-gone', '1');
    el.style.opacity = '0';
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 220);
  }
  function arm() {
    if (shellReady()) {
      dismiss();
      return;
    }
    var obs = new MutationObserver(function () {
      if (shellReady()) {
        obs.disconnect();
        dismiss();
      }
    });
    obs.observe(document.documentElement, { childList: true, subtree: true });
  }
  function onDocument() {
    setProgress(70);
    var msg = document.getElementById('laim-boot-msg');
    if (msg && msg.textContent === 'Preparando la interfaz…') {
      msg.textContent = 'Abriendo la página…';
    }
    arm();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onDocument);
  } else {
    onDocument();
  }
  setTimeout(function () {
    var msg = document.getElementById('laim-boot-msg');
    if (msg && document.getElementById('laim-boot')) {
      msg.textContent = 'La interfaz está tardando más de lo esperado.';
    }
  }, 30000);
})();
"""


def boot_head_components() -> list[rx.Component]:
    """Splash en el <head> real (no Helmet) y motores en paralelo al bundle.

    rx.script envuelve Helmet y solo corre tras hidratar. rx.el.script es
    la etiqueta del documento, la misma que usa Reflex para el tema.
    """
    return [
        rx.el.link(rel="icon", href="/favicon.ico", custom_attrs={"sizes": "any"}),
        rx.el.link(
            rel="icon",
            href="/favicon-32.png",
            custom_attrs={"type": "image/png", "sizes": "32x32"},
        ),
        rx.el.link(rel="apple-touch-icon", href="/apple-touch-icon.png"),
        rx.el.script(BOOT_INLINE),
        rx.el.link(
            rel="preload",
            href=NEURAL_SCRIPT_SRC,
            custom_attrs={"as": "script"},
        ),
        rx.el.script(src=NEURAL_SCRIPT_SRC, defer=True),
        rx.el.link(
            rel="preload",
            href=ESCENARIO_SCRIPT_SRC,
            custom_attrs={"as": "script"},
        ),
        rx.el.script(src=ESCENARIO_SCRIPT_SRC, defer=True),
    ]

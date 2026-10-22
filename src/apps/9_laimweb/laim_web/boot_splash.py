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
    + '#laim-boot{position:fixed;inset:0;z-index:100000;display:flex;align-items:center;'
    + 'justify-content:center;background:#031207;color:#b6ffb6;'
    + 'font:16px/1.5 Inconsolata,ui-monospace,monospace;text-align:center;'
    + 'transition:opacity .22s ease;}'
    + '#laim-boot h1{margin:0 0 6px;font-size:1.15rem;font-weight:600;color:#d8ffd8;}'
    + '#laim-boot p{margin:0;color:#7dcc7d;}'
    + '.laim-boot-spin{width:28px;height:28px;margin:0 auto 18px;border-radius:50%;'
    + 'border:3px solid #14301c;border-top-color:#3dff7a;animation:laim-boot-spin .8s linear infinite;}'
    + '@keyframes laim-boot-spin{to{transform:rotate(360deg);}}';
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);
  var root = document.createElement('div');
  root.id = 'laim-boot';
  root.setAttribute('role', 'status');
  root.setAttribute('aria-live', 'polite');
  root.innerHTML = '<div class="laim-boot-spin"></div>'
    + '<h1>LAIM se está preparando</h1>'
    + '<p id="laim-boot-msg">Preparando la interfaz…</p>';
  document.documentElement.appendChild(root);
  function shellReady() {
    return !!document.querySelector('.crt-shell');
  }
  function dismiss() {
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
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arm);
  } else {
    arm();
  }
  setTimeout(function () {
    var msg = document.getElementById('laim-boot-msg');
    if (msg && document.getElementById('laim-boot')) {
      msg.textContent = 'La interfaz está tardando más de lo esperado.';
    }
  }, 12000);
})();
"""


def boot_head_components() -> list[rx.Component]:
    """Splash en el <head> real (no Helmet) y motores en paralelo al bundle.

    rx.script envuelve Helmet y solo corre tras hidratar. rx.el.script es
    la etiqueta del documento, la misma que usa Reflex para el tema.
    """
    return [
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

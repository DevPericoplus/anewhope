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
    + '.laim-boot-spin{width:28px;height:28px;margin:0 auto 18px!important;border-radius:50%;'
    + 'border:3px solid #14301c;border-top-color:#3dff7a;animation:laim-boot-spin .8s linear infinite;}'
    + '@keyframes laim-boot-spin{to{transform:rotate(360deg);}}';
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);
  var root = document.createElement('div');
  root.id = 'laim-boot';
  root.setAttribute('role', 'status');
  root.setAttribute('aria-live', 'polite');
  root.innerHTML = '<div class="laim-boot-card">'
    + '<div class="laim-boot-spin"></div>'
    + '<h1>LAIM se está preparando</h1>'
    + '<p id="laim-boot-msg">Preparando la interfaz…</p>'
    + '</div>';
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
  }, 30000);
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

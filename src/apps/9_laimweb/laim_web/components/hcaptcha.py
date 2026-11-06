"""Widget Cap (CAPTCHA proof-of-work) para el formulario de registro LAIM.

Sustituye hCaptcha por Cap (https://github.com/tiagozip/cap),
un CAPTCHA auto-hospedado basado en proof-of-work.

Reglas que hacen fiable el alta:

- React no gestiona el ``<cap-widget>``. El contenedor
  ``#laim-cap-container`` no tiene hijos de React; el script de arranque
  crea el widget dentro una vez por apertura del formulario y lo vuelve a
  crear solo si el contenedor se monta de nuevo o cambia el endpoint.
  Escribir en el formulario no lo repinta.
- Los eventos ``solve`` / ``reset`` / ``error`` se escuchan en
  ``document`` en fase de captura: valen para cualquier widget, también
  uno recreado.
- El token vive en ``window`` y no se sincroniza con el estado de Reflex
  (sincronizarlo repintaba el modal). Se lee al pulsar «Registrarse».
- El endpoint es un var de estado que el proceso lee al servir la
  página, no un literal compilado en el JavaScript.
- El motor (WebAssembly y pako) se sirve desde ``/crt/``, no desde
  cdn.jsdelivr.net.
"""

from __future__ import annotations

import os
from pathlib import Path

import reflex as rx

from laim_web.dynamic_import import load_module_from_path

_env_settings_path = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "2_shared_application"
    / "config"
    / "env_settings.py"
)
_env_settings = load_module_from_path(_env_settings_path, "env_settings_hcaptcha")

CAP_ENDPOINT_ENV_VAR = "LAIM_CAP_API_ENDPOINT"
CAP_CONTAINER_ID = "laim-cap-container"
CAP_STATUS_ID = "laim-cap-status"
CAP_WIDGET_ID = "laim-cap-widget"
CAP_WIDGET_SCRIPT_URL = "/crt/cap-widget-0.1.58.js"
# Mismas versiones que cap-widget 0.1.58 pide a jsdelivr (@cap.js/wasm 0.0.8,
# pako 2.1.0), copiadas de los paquetes npm con su integridad comprobada.
CAP_WASM_URL = "/crt/cap_wasm_bg-0.0.8.wasm"
CAP_HASHWX_URL = "/crt/hashwx-0.0.8.wasm"
CAP_PAKO_URL = "/crt/pako_inflate-2.1.0.min.js"
# Un token sin usar más antiguo que esto se descarta antes de enviarlo.
# Cap lo caduca antes o después según su configuración; el widget avisa
# con «reset» al caducar y también se descarta entonces.
CAP_TOKEN_MAX_AGE_MS = 10 * 60 * 1000

_PLACEHOLDER_MARKERS = ("<CAP_SITE_KEY>", "REPLACE_WITH", "CAP-SITE-KEY", "CHANGE_ME")


def _is_placeholder(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return True
    upper = text.upper()
    return any(marker in upper for marker in _PLACEHOLDER_MARKERS)


def get_cap_api_endpoint() -> str:
    """URL pública del Cap del entorno: ``https://<host>/cap/<site-key>/``.

    ``LAIM_CAP_API_ENDPOINT`` del proceso gana a ``laim_cap_api_endpoint``
    de env.yaml. Un marcador (``<CAP_SITE_KEY>``) cuenta como no
    configurado: nunca se pinta un widget que no puede verificar.
    """
    for value in (
        os.environ.get(CAP_ENDPOINT_ENV_VAR, ""),
        str(_env_settings.get_env_value("laim_cap_api_endpoint", "") or ""),
    ):
        if not _is_placeholder(value):
            endpoint = value.strip()
            return endpoint if endpoint.endswith("/") else endpoint + "/"
    return ""


def is_hcaptcha_configured() -> bool:
    """Indica si el widget Cap está configurado en el entorno.

    Mantiene el nombre ``is_hcaptcha_configured`` por compatibilidad
    con las llamadas existentes en ``laim_state.py``.
    """
    return bool(get_cap_api_endpoint())


class CapWidgetState(rx.State):
    """Endpoint del Cap leído por el proceso en cada petición."""

    @rx.var(cache=False)
    def endpoint(self) -> str:
        return get_cap_api_endpoint()


def _cap_bootstrap_script() -> str:
    """Script de arranque, idempotente: se puede ejecutar muchas veces."""
    return f"""
(function() {{
  window.CAP_CUSTOM_WASM_URL = "{CAP_WASM_URL}";
  window.CAP_CUSTOM_HASHWX_URL = "{CAP_HASHWX_URL}";
  window.CAP_PAKO_URL = "{CAP_PAKO_URL}";

  if (window.__LAIM_CAP__) {{
    window.__LAIM_CAP__.ensure();
    return;
  }}

  var CONTAINER_ID = "{CAP_CONTAINER_ID}";
  var STATUS_ID = "{CAP_STATUS_ID}";
  var WIDGET_ID = "{CAP_WIDGET_ID}";
  var MAX_AGE_MS = {CAP_TOKEN_MAX_AGE_MS};
  var held = {{ token: "", solvedAt: 0, widget: null }};
  var scheduled = false;

  function container() {{ return document.getElementById(CONTAINER_ID); }}

  function status(message, kind) {{
    var el = document.getElementById(STATUS_ID);
    if (!el) return;
    el.textContent = message || "";
    if (kind) el.setAttribute("data-cap-state", kind);
    else el.removeAttribute("data-cap-state");
  }}

  function isOurWidget(target) {{
    return !!(target && target.tagName === "CAP-WIDGET" && target.id === WIDGET_ID);
  }}

  function clearToken() {{
    held.token = "";
    held.solvedAt = 0;
  }}

  function ensure() {{
    var box = container();
    if (!box) {{ held.widget = null; return; }}
    var endpoint = box.getAttribute("data-cap-endpoint") || "";
    if (!endpoint) return;
    if (!window.customElements || !customElements.get("cap-widget")) return;
    var widget = box.querySelector("cap-widget");
    if (widget && widget.getAttribute("data-cap-api-endpoint") === endpoint) {{
      held.widget = widget;
      return;
    }}
    if (widget) widget.remove();
    // Un widget nuevo empieza sin resolver: un token de otro widget no vale.
    clearToken();
    widget = document.createElement("cap-widget");
    widget.id = WIDGET_ID;
    widget.setAttribute("data-cap-api-endpoint", endpoint);
    widget.setAttribute("data-cap-lang", "es");
    box.appendChild(widget);
    held.widget = widget;
  }}

  function scheduleEnsure() {{
    if (scheduled) return;
    scheduled = true;
    window.setTimeout(function() {{ scheduled = false; ensure(); }}, 50);
  }}

  document.addEventListener("solve", function(e) {{
    if (!isOurWidget(e.target)) return;
    held.token = (e.detail && e.detail.token) ? String(e.detail.token) : "";
    held.solvedAt = held.token ? Date.now() : 0;
    status(held.token ? "" : "La verificación no ha devuelto un resultado. Pulsa otra vez el botón.",
           held.token ? "" : "error");
  }}, true);

  document.addEventListener("reset", function(e) {{
    if (!isOurWidget(e.target)) return;
    clearToken();
  }}, true);

  document.addEventListener("error", function(e) {{
    if (!isOurWidget(e.target)) return;
    clearToken();
    status("La verificación no ha podido completarse. Pulsa otra vez el botón.", "error");
  }}, true);

  new MutationObserver(scheduleEnsure).observe(document.documentElement, {{
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["data-cap-endpoint"]
  }});

  if (window.customElements) {{
    customElements.whenDefined("cap-widget").then(function() {{
      var el = document.getElementById(STATUS_ID);
      if (el && el.getAttribute("data-cap-state") === "load") status("");
      ensure();
    }});
  }}

  window.setTimeout(function() {{
    if (container() && (!window.customElements || !customElements.get("cap-widget"))) {{
      status("No se ha podido cargar la verificación. Recarga la página e inténtalo de nuevo.", "load");
    }}
  }}, 8000);

  window.__LAIM_CAP__ = {{
    ensure: ensure,
    token: function() {{
      if (!held.token) return "";
      if (Date.now() - held.solvedAt > MAX_AGE_MS) {{
        window.__LAIM_CAP__.reset();
        return "";
      }}
      return held.token;
    }},
    reset: function(message) {{
      clearToken();
      var widget = held.widget || document.getElementById(WIDGET_ID);
      if (widget && typeof widget.reset === "function") {{
        try {{ widget.reset(); }} catch (err) {{}}
      }}
      status(message || "", message ? "retry" : "");
    }}
  }};

  // Nombres que ya usa laim_state.py.
  window.resetLaimHcaptcha = function(message) {{ window.__LAIM_CAP__.reset(message); }};
  window.renderLaimHcaptchaWidget = ensure;

  ensure();
}})();
"""


def hcaptcha_widget() -> rx.Component:
    """Renderiza el contenedor del widget Cap o el aviso si no está configurado.

    Solo montar este componente con el modal de registro abierto: el
    script de Cap en cada visita dispara el permiso de Chrome
    «acceder a apps y servicios de este dispositivo» (LNA/loopback).

    Mantiene el nombre ``hcaptcha_widget`` por compatibilidad
    con la referencia existente en ``auth_modals.py``.
    """
    return rx.fragment(
        rx.script(_cap_bootstrap_script()),
        rx.script(src=CAP_WIDGET_SCRIPT_URL),
        rx.cond(
            CapWidgetState.endpoint == "",
            rx.text(
                "Verificación anti-bot no configurada en este entorno.",
                font_size="0.8em",
                color="#e8ffe8",
            ),
            # Sin hijos de React: el script crea aquí el <cap-widget>.
            rx.box(
                id=CAP_CONTAINER_ID,
                custom_attrs={"data-cap-endpoint": CapWidgetState.endpoint},
                width="100%",
                min_height="78px",
            ),
        ),
        rx.el.p(id=CAP_STATUS_ID, class_name="crt-cap-status", aria_live="polite"),
    )

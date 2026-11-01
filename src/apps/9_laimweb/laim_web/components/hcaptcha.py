"""Widget Cap (CAPTCHA proof-of-work) para el formulario de registro LAIM.

Sustituye hCaptcha por Cap (https://github.com/tiagozip/cap),
un CAPTCHA auto-hospedado basado en proof-of-work e instrumentación JS.
"""

from __future__ import annotations

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


def get_cap_api_endpoint() -> str:
    """Obtiene la URL del servidor Cap desde env.yaml.

    Formato esperado: ``https://<host>:<port>/<site-key>/``
    """
    return str(_env_settings.get_env_value("laim_cap_api_endpoint", "") or "").strip()


def is_hcaptcha_configured() -> bool:
    """Indica si el widget Cap está configurado en el entorno.

    Mantiene el nombre ``is_hcaptcha_configured`` por compatibilidad
    con las llamadas existentes en ``laim_state.py``.
    """
    return bool(get_cap_api_endpoint())


def hcaptcha_widget() -> rx.Component:
    """Renderiza el widget Cap o aviso si no está configurado.

    Solo montar este componente con el modal de registro abierto: el
    script de Cap en cada visita dispara el permiso de Chrome
    «acceder a apps y servicios de este dispositivo» (LNA/loopback).

    Mantiene el nombre ``hcaptcha_widget`` por compatibilidad
    con la referencia existente en ``auth_modals.py``.
    """
    api_endpoint = get_cap_api_endpoint()
    if not api_endpoint:
        return rx.text(
            "Verificación anti-bot no configurada en este entorno.",
            font_size="0.8em",
            color="#e8ffe8",
        )

    safe_endpoint = api_endpoint.replace("\\", "\\\\").replace('"', '\\"')

    # cap-widget 0.1.58, servido por la propia página. data-cap-lang fuerza
    # el castellano aunque el navegador esté en otro idioma.
    cap_html = (
        f'<cap-widget data-cap-api-endpoint="{safe_endpoint}" '
        f'data-cap-lang="es" id="laim-cap-widget"></cap-widget>'
    )

    return rx.fragment(
        rx.script(src="/crt/cap-widget-0.1.58.js"),
        rx.box(
            rx.html(cap_html),
            id="laim-cap-container",
            width="100%",
            min_height="78px",
        ),
        rx.el.p(id="laim-cap-status", class_name="crt-cap-status", aria_live="polite"),
        rx.script(
            f"""
            (function() {{
              function capStatus(message, failedLoad) {{
                var status = document.getElementById("laim-cap-status");
                if (!status) return;
                status.textContent = message || "";
                if (failedLoad) status.setAttribute("data-cap-load", "1");
                else status.removeAttribute("data-cap-load");
              }}

              if (!window.__LAIM_CAP_BOOTSTRAP__) {{
                window.__LAIM_CAP_BOOTSTRAP__ = true;
                window.__LAIM_CAP_TOKEN__ = "";

                window.__LAIM_SYNC_CAP_TOKEN__ = function(token) {{
                  window.__LAIM_CAP_TOKEN__ = token || "";
                  var input = document.getElementById("laim-hcaptcha-token-input");
                  if (!input) return;
                  var setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, "value"
                  );
                  if (setter && setter.set) {{
                    setter.set.call(input, token || "");
                  }} else {{
                    input.value = token || "";
                  }}
                  input.dispatchEvent(new Event("input", {{ bubbles: true }}));
                }};

                window.resetLaimHcaptcha = function() {{
                  window.__LAIM_SYNC_CAP_TOKEN__("");
                  capStatus("");
                  var widget = document.getElementById("laim-cap-widget");
                  if (widget && typeof widget.reset === "function") {{
                    try {{ widget.reset(); }} catch(e) {{}}
                  }}
                }};

                window.renderLaimHcaptchaWidget = function() {{
                  var widget = document.getElementById("laim-cap-widget");
                  if (!widget) return;
                  if (widget.__capListenerAttached) return;
                  widget.__capListenerAttached = true;
                  widget.addEventListener("solve", function(e) {{
                    var token = e.detail && e.detail.token ? e.detail.token : "";
                    window.__LAIM_SYNC_CAP_TOKEN__(token);
                    capStatus("");
                  }});
                  widget.addEventListener("error", function() {{
                    window.__LAIM_SYNC_CAP_TOKEN__("");
                    capStatus("La verificación no ha podido completarse. Pulsa otra vez el botón.");
                  }});
                }};

                window.__LAIM_CAP_POLL__ = window.setInterval(function() {{
                  var widget = document.getElementById("laim-cap-widget");
                  if (widget && window.customElements && customElements.get("cap-widget")) {{
                    var status = document.getElementById("laim-cap-status");
                    if (status && status.getAttribute("data-cap-load") === "1") capStatus("");
                    window.renderLaimHcaptchaWidget();
                    window.clearInterval(window.__LAIM_CAP_POLL__);
                  }}
                }}, 500);

                window.setTimeout(function() {{
                  if (!window.customElements || !customElements.get("cap-widget")) {{
                    capStatus("No se ha podido cargar la verificación. Recarga la página e inténtalo de nuevo.", true);
                  }}
                }}, 4000);
              }}

              window.renderLaimHcaptchaWidget();
            }})();
            """
        ),
    )

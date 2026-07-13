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

    Mantiene el nombre ``hcaptcha_widget`` por compatibilidad
    con la referencia existente en ``auth_modals.py``.
    """
    api_endpoint = get_cap_api_endpoint()
    if not api_endpoint:
        return rx.text(
            "Verificación anti-bot no configurada en este entorno.",
            font_size="0.8em",
            color="rgba(200, 255, 200, 0.55)",
        )

    safe_endpoint = api_endpoint.replace("\\", "\\\\").replace('"', '\\"')

    cap_html = (
        f'<cap-widget data-cap-api-endpoint="{safe_endpoint}" '
        f'id="laim-cap-widget"></cap-widget>'
    )

    return rx.fragment(
        rx.script(
            src="https://cdn.jsdelivr.net/npm/cap-widget@latest",
        ),
        rx.box(
            rx.html(cap_html),
            id="laim-cap-container",
            width="100%",
            min_height="78px",
        ),
        rx.script(
            f"""
            (function() {{
              var apiEndpoint = "{safe_endpoint}";

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
                  }});
                }};

                window.__LAIM_CAP_POLL__ = window.setInterval(function() {{
                  var widget = document.getElementById("laim-cap-widget");
                  if (widget) {{
                    window.renderLaimHcaptchaWidget();
                    window.clearInterval(window.__LAIM_CAP_POLL__);
                  }}
                }}, 500);
              }}

              window.renderLaimHcaptchaWidget();
            }})();
            """
        ),
    )

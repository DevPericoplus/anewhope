"""Widget hCaptcha para el formulario de registro LAIM."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import reflex as rx

_env_settings_path = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "2_shared_application"
    / "config"
    / "env_settings.py"
)
_spec = importlib.util.spec_from_file_location("env_settings_hcaptcha", _env_settings_path)
_env_settings = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("env_settings_hcaptcha", _env_settings)
_spec.loader.exec_module(_env_settings)


def get_hcaptcha_site_key() -> str:
    """Obtiene la site key pública de hCaptcha desde env.yaml."""
    return str(_env_settings.get_env_value("laim_hcaptcha_site_key", "") or "").strip()


def is_hcaptcha_configured() -> bool:
    """Indica si el widget hCaptcha está configurado en el entorno."""
    return bool(get_hcaptcha_site_key())


HCAPTCHA_SITE_KEY = get_hcaptcha_site_key()


def hcaptcha_widget() -> rx.Component:
    """Renderiza el widget hCaptcha o aviso si no está configurado."""
    if not HCAPTCHA_SITE_KEY:
        return rx.text(
            "Verificación anti-bot no configurada en este entorno.",
            font_size="0.8em",
            color="rgba(200, 255, 200, 0.55)",
        )

    site_key = HCAPTCHA_SITE_KEY.replace("\\", "\\\\").replace('"', '\\"')

    return rx.fragment(
        rx.script(src="https://js.hcaptcha.com/1/api.js", async_=True, defer=True),
        rx.box(id="laim-hcaptcha-container", width="100%", min_height="78px"),
        rx.script(
            f"""
            (function() {{
              const siteKey = "{site_key}";

              window.__LAIM_HCAPTCHA_TOKEN__ = window.__LAIM_HCAPTCHA_TOKEN__ || "";

              window.__LAIM_SYNC_HCAPTCHA_TOKEN__ = function(token) {{
                window.__LAIM_HCAPTCHA_TOKEN__ = token || "";
                const input = document.getElementById("laim-hcaptcha-token-input");
                if (!input) {{
                  return;
                }}
                const setter = Object.getOwnPropertyDescriptor(
                  window.HTMLInputElement.prototype,
                  "value"
                );
                if (setter && setter.set) {{
                  setter.set.call(input, token || "");
                }} else {{
                  input.value = token || "";
                }}
                input.dispatchEvent(new Event("input", {{ bubbles: true }}));
              }};

              window.resetLaimHcaptcha = function() {{
                window.__LAIM_HCAPTCHA_TOKEN__ = "";
                const container = document.getElementById("laim-hcaptcha-container");
                if (!container) {{
                  return;
                }}
                if (window.laimHcaptchaWidgetId !== undefined && window.hcaptcha) {{
                  try {{
                    window.hcaptcha.remove(window.laimHcaptchaWidgetId);
                  }} catch (e) {{}}
                }}
                window.laimHcaptchaWidgetId = undefined;
                container.dataset.rendered = "0";
                container.innerHTML = "";
              }};

              window.renderLaimHcaptchaWidget = function() {{
                const container = document.getElementById("laim-hcaptcha-container");
                if (!container || container.offsetParent === null) {{
                  return;
                }}
                if (container.dataset.rendered === "1") {{
                  return;
                }}
                if (!window.hcaptcha) {{
                  setTimeout(window.renderLaimHcaptchaWidget, 150);
                  return;
                }}
                container.dataset.rendered = "1";
                window.laimHcaptchaWidgetId = window.hcaptcha.render("laim-hcaptcha-container", {{
                  sitekey: siteKey,
                  callback: function(token) {{
                    window.__LAIM_SYNC_HCAPTCHA_TOKEN__(token);
                  }},
                  "expired-callback": function() {{
                    window.__LAIM_SYNC_HCAPTCHA_TOKEN__("");
                  }},
                  "error-callback": function() {{
                    window.__LAIM_SYNC_HCAPTCHA_TOKEN__("");
                  }},
                }});
              }};

              window.renderLaimHcaptchaWidget();
              setInterval(function() {{
                window.renderLaimHcaptchaWidget();
              }}, 500);
            }})();
            """
        ),
    )

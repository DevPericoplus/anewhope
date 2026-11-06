"""El alta con Cap no depende de cómo React repinte el modal (QA 0.12.65).

Defectos que cubre:
- el widget repintado perdía el oyente «solve» y el token no llegaba;
- tras un alta fallida se reenviaba el token ya gastado;
- el motor de Cap se descargaba de cdn.jsdelivr.net;
- el endpoint quedaba compilado en el JavaScript (o era un marcador).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

laimweb_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(laimweb_root))

CRT = laimweb_root / "assets" / "crt"

# sha256 de los ficheros de @cap.js/wasm 0.0.8 y pako 2.1.0 (tarballs npm
# verificados con su integridad sha512 del registro).
PINNED_ASSETS = {
    "cap_wasm_bg-0.0.8.wasm": "e4f3c00246a775193661f9277ca1288cd310a6514de166ecc2176ccd26fb06a9",
    "hashwx-0.0.8.wasm": "b1a0dbb3ef444d3c7069e0a5e0a0273ffa4cf8fef62cbbe43761c02f7cd6aff5",
    "pako_inflate-2.1.0.min.js": "fa226c8e1e3556993260e6a5c1fe94e225da59b3418a06811fdc51d308f8bb43",
}


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def _widget_source() -> str:
    return (laimweb_root / "laim_web" / "components" / "hcaptcha.py").read_text(
        encoding="utf-8"
    )


def _filled_state():
    from laim_web.laim_state import LaimWebState

    state = LaimWebState()
    state.reg_username = "user1"
    state.reg_full_name = "User One"
    state.reg_email = "user1@example.com"
    state.reg_password = "password1"
    state.reg_password_confirm = "password1"
    return state


def test_engine_is_served_from_crt_not_jsdelivr() -> None:
    from laim_web.components import hcaptcha

    script = hcaptcha._cap_bootstrap_script()
    for name, digest in PINNED_ASSETS.items():
        path = CRT / name
        assert path.is_file(), name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
        assert f"/crt/{name}" in script
    assert "window.CAP_CUSTOM_WASM_URL" in script
    assert "window.CAP_CUSTOM_HASHWX_URL" in script
    assert "window.CAP_PAKO_URL" in script
    assert "jsdelivr" not in script
    # El script de arranque va antes que el del widget.
    source = _widget_source()
    assert source.find("_cap_bootstrap_script()),") < source.find(
        "rx.script(src=CAP_WIDGET_SCRIPT_URL)"
    )


def test_widget_is_created_by_script_not_by_react() -> None:
    source = _widget_source()
    assert "rx.html(" not in source
    assert "rx.el.cap_widget" not in source
    assert 'document.createElement("cap-widget")' in source
    # Un solo widget por contenedor; se recrea solo si cambia el endpoint
    # o el contenedor es nuevo.
    assert 'box.querySelector("cap-widget")' in source
    assert "MutationObserver" in source


def test_listeners_are_delegated_in_capture_phase() -> None:
    script = _widget_source()
    for event_name in ("solve", "reset", "error"):
        assert f'document.addEventListener("{event_name}", function(e)' in script
    assert script.count("}, true);") >= 3
    assert "__capListenerAttached" not in script
    # Un «error» de una imagen o un «reset» de un formulario no tocan el token.
    assert 'target.tagName === "CAP-WIDGET"' in script


def test_token_never_goes_through_reflex_state_on_solve() -> None:
    modal = (laimweb_root / "laim_web" / "components" / "auth_modals.py").read_text(
        encoding="utf-8"
    )
    assert "laim-hcaptcha-token-input" not in modal
    assert "set_reg_hcaptcha_token_value" not in modal
    assert 'dispatchEvent(new Event("input"' not in _widget_source()


def test_endpoint_placeholder_is_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from laim_web.components import hcaptcha

    monkeypatch.delenv("LAIM_CAP_API_ENDPOINT", raising=False)
    monkeypatch.setattr(
        hcaptcha._env_settings,
        "get_env_value",
        lambda name, default="": "https://laim.example.com/cap/<CAP_SITE_KEY>/",
    )
    assert hcaptcha.get_cap_api_endpoint() == ""
    assert hcaptcha.is_hcaptcha_configured() is False


def test_endpoint_env_var_wins_and_gets_trailing_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from laim_web.components import hcaptcha

    monkeypatch.setenv("LAIM_CAP_API_ENDPOINT", "https://laim.example.com/cap/abc123")
    monkeypatch.setattr(
        hcaptcha._env_settings,
        "get_env_value",
        lambda name, default="": "https://other.example.com/cap/zzz/",
    )
    assert hcaptcha.get_cap_api_endpoint() == "https://laim.example.com/cap/abc123/"


def test_handle_register_always_reads_a_fresh_token() -> None:
    from laim_web.laim_state import READ_LAIM_HCAPTCHA_TOKEN_SCRIPT

    with patch("laim_web.components.hcaptcha.is_hcaptcha_configured", return_value=True):
        state = _filled_state()
        state.reg_hcaptcha_token = "spent-token-from-previous-try"
        event_spec = state.handle_register()

    assert state.reg_hcaptcha_token == ""
    assert event_spec is not None
    script_arg = event_spec.args[0][1]
    assert script_arg._var_value == READ_LAIM_HCAPTCHA_TOKEN_SCRIPT


def test_read_script_uses_window_token_only() -> None:
    from laim_web.laim_state import READ_LAIM_HCAPTCHA_TOKEN_SCRIPT

    assert "window.__LAIM_CAP__" in READ_LAIM_HCAPTCHA_TOKEN_SCRIPT
    assert "laim-hcaptcha-token-input" not in READ_LAIM_HCAPTCHA_TOKEN_SCRIPT


@pytest.mark.parametrize(
    ("detail", "expected_start"),
    [
        (
            "Error del broker backend: 400 - Error en registro LAIM: Error del backend core: "
            "400 - Usuario o email ya registrados",
            "Error del broker backend",
        ),
        ("Verificación CAPTCHA fallida", "No se ha podido comprobar que eres una persona."),
        ("HTTP 400", "Datos de registro inválidos o usuario ya existente"),
    ],
)
def test_every_failure_asks_to_repeat_the_check(detail: str, expected_start: str) -> None:
    from laim_web.laim_state import MSG_CAPTCHA_REPEAT, register_failure_message

    message = register_failure_message(detail, captcha_on=True)
    assert message.startswith(expected_start)
    assert message.endswith(MSG_CAPTCHA_REPEAT)


def test_failure_without_captcha_keeps_the_backend_text() -> None:
    from laim_web.laim_state import register_failure_message

    assert register_failure_message("Usuario o email ya registrados", captcha_on=False) == (
        "Usuario o email ya registrados"
    )


def test_background_register_spends_token_and_resets_widget() -> None:
    source = (laimweb_root / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    body = source.split("async def complete_register_background", 1)[1].split(
        "def open_login_modal", 1
    )[0]
    # El token se vacía al enviarlo, antes de la llamada al backend.
    assert body.find('self.reg_hcaptcha_token = ""') < body.find("laim_register(")
    assert "reset_captcha = captcha_on" in body
    assert "RETRY_LAIM_HCAPTCHA_SCRIPT" in body

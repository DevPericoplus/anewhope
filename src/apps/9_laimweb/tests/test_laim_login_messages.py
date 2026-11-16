"""Login de laimweb: mensajes honestos y formulario que envía lo que se ve.

Antes todo fallo (campos vacíos → 422, red, 5xx, cuenta bloqueada) salía como
«Credenciales no válidas». Ahora solo lo dice cuando backend_core rechaza la
clave, y el modal envía los valores reales del formulario (autorrelleno).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

laimweb_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(laimweb_root))

UNAVAILABLE = "No se pudo iniciar sesión. Inténtelo más tarde."
LOCKED = (
    "Su cuenta está bloqueada por seguridad tras demasiados intentos fallidos "
    "de inicio de sesión. Puede pedir el desbloqueo desde el menú «Contacto», "
    "con el botón «Contactar»."
)


@pytest.fixture(autouse=True)
def _mock_storage_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "mock")


def _http_error(client_mod, status: int, body: object, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.text = text or str(body)
    if isinstance(body, Exception):
        response.json.side_effect = body
    else:
        response.json.return_value = body
    response.raise_for_status.side_effect = client_mod.httpx.HTTPStatusError(
        str(status), request=MagicMock(), response=response
    )
    return response


def _login_with(response_or_exc, username: str = "ana", password: str = "x"):
    from laim_web.adapters import laim_api_client

    with patch.object(laim_api_client.httpx, "Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        if isinstance(response_or_exc, Exception):
            mock_client.request.side_effect = response_or_exc
        else:
            mock_client.request.return_value = response_or_exc
        mock_client_cls.return_value = mock_client
        result = laim_api_client.laim_login(username, password)
    return result, mock_client


@pytest.mark.parametrize(
    ("username", "password", "expected"),
    [
        ("", "", "Introduzca su usuario y su contraseña."),
        ("   ", "", "Introduzca su usuario y su contraseña."),
        ("", "secreta", "Introduzca su usuario."),
        ("  ", "secreta", "Introduzca su usuario."),
        ("ana", "", "Introduzca su contraseña."),
    ],
)
def test_empty_fields_ask_to_fill_them_without_calling_middleware(
    username: str, password: str, expected: str
) -> None:
    result, client = _login_with(AssertionError("no debe llamar"), username, password)
    assert result == {"success": False, "error": expected}
    client.request.assert_not_called()


def test_real_rejection_is_invalid_credentials() -> None:
    from laim_web.adapters import laim_api_client

    result, _ = _login_with(
        _http_error(laim_api_client, 400, {"detail": "Credenciales no válidas"})
    )
    assert result == {"success": False, "error": "Credenciales no válidas"}


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (502, {"detail": UNAVAILABLE}),
        (500, ValueError("no json")),
        (503, {"detail": "Service Unavailable"}),
        (422, {"detail": [{"type": "string_too_short", "loc": ["body", "password"]}]}),
    ],
)
def test_service_failures_are_not_bad_credentials(status: int, body: object) -> None:
    from laim_web.adapters import laim_api_client

    result, _ = _login_with(_http_error(laim_api_client, status, body, "Internal Server Error"))
    assert result == {"success": False, "error": UNAVAILABLE}


def test_network_failure_is_unavailable() -> None:
    from laim_web.adapters import laim_api_client

    result, _ = _login_with(laim_api_client.httpx.ConnectError("refused"))
    assert result == {"success": False, "error": UNAVAILABLE}


def test_locked_account_explains_how_to_get_unblocked() -> None:
    from laim_web.adapters import laim_api_client

    result, _ = _login_with(
        _http_error(
            laim_api_client,
            403,
            {"detail": "Cuenta bloqueada por seguridad tras demasiados intentos fallidos"},
        )
    )
    assert result == {"success": False, "error": LOCKED}
    assert laim_api_client.MSG_ACCOUNT_LOCKED == LOCKED


def test_locked_message_names_the_real_contact_menu_and_button() -> None:
    index = (laimweb_root / "laim_web" / "pages" / "index.py").read_text(encoding="utf-8")
    contact = (laimweb_root / "laim_web" / "components" / "contact_form.py").read_text(
        encoding="utf-8"
    )
    assert '"contacto": "Contacto",' in index
    assert '"Contactar",\n                on_click=LaimWebState.open_contact_modal,' in contact


def test_login_modal_is_a_form_that_submits_field_values() -> None:
    source = (laimweb_root / "laim_web" / "components" / "auth_modals.py").read_text(
        encoding="utf-8"
    )
    modal = source[source.index("def login_modal()") : source.index("def register_modal()")]
    assert "rx.form(" in modal
    assert "on_submit=LaimWebState.handle_login_submit" in modal
    assert 'name="username"' in modal
    assert 'name="password"' in modal
    assert 'custom_attrs={"autoComplete": "username"}' in modal
    assert 'custom_attrs={"autoComplete": "current-password"}' in modal
    assert 'type="submit"' in modal
    assert "on_click=LaimWebState.handle_login" not in modal

    from laim_web.components.auth_modals import login_modal

    assert login_modal() is not None


def test_submit_uses_form_data_over_stale_state() -> None:
    from laim_web.laim_state import LaimWebState

    state = LaimWebState()
    state.login_username = ""
    state.login_password = ""
    with patch(
        "laim_web.adapters.laim_api_client.laim_login",
        return_value={"success": False, "error": "Credenciales no válidas"},
    ) as mock_login:
        state.handle_login_submit({"username": " ana ", "password": "Autorrelleno1"})

    mock_login.assert_called_once_with("ana", "Autorrelleno1")
    assert state.login_username == "ana"
    assert state.error_message == "Credenciales no válidas"
    assert state.loading is False


def test_submit_with_empty_form_shows_fill_message() -> None:
    from laim_web.laim_state import LaimWebState

    state = LaimWebState()
    with patch("laim_web.adapters.laim_api_client.httpx.Client") as mock_client_cls:
        state.handle_login_submit({"username": "", "password": ""})

    mock_client_cls.assert_not_called()
    assert state.error_message == "Introduzca su usuario y su contraseña."

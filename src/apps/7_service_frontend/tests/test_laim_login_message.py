"""El login de LAIM no disfraza una cuenta bloqueada como clave incorrecta."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def _load_routermiddleware() -> Any:
    module_path = Path(__file__).resolve().parents[1] / "routermiddleware.py"
    spec = importlib.util.spec_from_file_location(
        "routermiddleware_laim_login_message", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar routermiddleware")
    module = importlib.util.module_from_spec(spec)
    sys.modules["routermiddleware_laim_login_message"] = module
    spec.loader.exec_module(module)
    return module


routermiddleware = _load_routermiddleware()


def test_blocked_login_is_not_rewritten_as_bad_credentials() -> None:
    detail = (
        "Error del broker backend: 400 - "
        "El usuario no está habilitado"
    )
    message = routermiddleware._laim_login_user_message(detail)
    assert message == "El usuario no está habilitado. Contacta con soporte."
    assert "400" not in message


def test_unknown_400_stays_invalid_credentials() -> None:
    message = routermiddleware._laim_login_user_message(
        "Error del backend core: 400 - Usuario o credenciales inválidas"
    )
    assert message == routermiddleware.MSG_LAIM_INVALID_CREDENTIALS


BROKER = "Error del broker backend: "


def test_broker_credential_rejection_stays_invalid_credentials() -> None:
    message = routermiddleware._laim_login_user_message(
        BROKER + "400 - Credenciales no válidas"
    )
    assert message == "Credenciales no válidas"


def test_account_lock_passes_through_to_laimweb() -> None:
    message = routermiddleware._laim_login_user_message(
        BROKER + "403 - Cuenta bloqueada por seguridad tras demasiados intentos fallidos"
    )
    assert message == "Cuenta bloqueada por seguridad tras demasiados intentos fallidos"
    assert message == routermiddleware.MSG_LAIM_ACCOUNT_LOCKED


def test_service_failures_are_unavailable_not_bad_credentials() -> None:
    for detail in (
        BROKER + "502 - No se pudo iniciar sesión. Inténtelo más tarde.",
        BROKER + "400 - No se pudo iniciar sesión. Inténtelo más tarde.",
        BROKER + "500 - Internal Server Error",
        BROKER + "422 - [{'type': 'missing'}]",
        "No se pudo contactar con el broker backend",
    ):
        assert (
            routermiddleware._laim_login_user_message(detail)
            == "No se pudo iniciar sesión. Inténtelo más tarde."
        ), detail


def test_http_status_follows_the_kind_of_failure() -> None:
    status = routermiddleware.laim_login_http_status
    assert status("Credenciales no válidas") == 400
    assert status(routermiddleware.MSG_LAIM_ACCOUNT_LOCKED) == 403
    assert status("El usuario no está habilitado. Contacta con soporte.") == 403
    assert status("No se pudo iniciar sesión. Inténtelo más tarde.") == 502


def test_login_endpoint_uses_the_status_helper() -> None:
    api = (Path(__file__).resolve().parents[1] / "apife.py").read_text(encoding="utf-8")
    start = api.index('@app.post("/laim/login")')
    body = api[start : api.index('@app.post("/laim/register")')]
    assert "status_code=laim_login_http_status(detail)" in body

"""El broker no convierte cualquier fallo de login LAIM en «Credenciales no válidas».

Antes bastaba un «400» en el texto: una cuenta bloqueada («no está habilitado»)
o un fallo de sesión del core llegaban al portal como clave incorrecta.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

_BASE = Path(__file__).resolve().parents[1]


def _load(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, _BASE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


routerbroker = _load("routerbroker_laim_login_message_test", "routerbroker.py")
apibe = _load("apibe_laim_login_message_test", "apibe.py")

CORE = "Error del backend core: "


def test_core_credential_rejection_is_invalid_credentials() -> None:
    message = routerbroker._laim_login_user_message(
        CORE + "400 - Usuario o credenciales inválidas"
    )
    assert message == "Credenciales no válidas"


def test_core_lock_passes_through() -> None:
    message = routerbroker._laim_login_user_message(
        CORE + "400 - Cuenta bloqueada por seguridad tras demasiados intentos fallidos"
    )
    assert message == "Cuenta bloqueada por seguridad tras demasiados intentos fallidos"
    assert message == routerbroker.MSG_LAIM_ACCOUNT_LOCKED


def test_core_disabled_user_is_not_rewritten_as_bad_credentials() -> None:
    message = routerbroker._laim_login_user_message(
        CORE + "400 - El usuario no está habilitado"
    )
    assert message == "El usuario no está habilitado"


def test_core_session_failure_and_5xx_are_unavailable() -> None:
    for detail in (
        CORE + "400 - No se pudo iniciar sesión",
        CORE + "500 - Internal Server Error",
        CORE + "422 - [{'type': 'missing'}]",
        "No se pudo contactar con el backend core",
    ):
        assert (
            routerbroker._laim_login_user_message(detail)
            == "No se pudo iniciar sesión. Inténtelo más tarde."
        ), detail


def teardown_function() -> None:
    apibe.app.dependency_overrides.pop(apibe.get_router_broker, None)


def _status_for(message: str) -> tuple[int, str]:
    router = MagicMock()
    router.laim_login.side_effect = apibe.BrokerBusinessError(message)
    apibe.app.dependency_overrides[apibe.get_router_broker] = lambda: router
    response = TestClient(apibe.app).post(
        "/laim/login", json={"username": "ana", "password": "x"}
    )
    return response.status_code, response.json()["detail"]


def test_route_status_codes_follow_the_kind_of_failure() -> None:
    assert _status_for(routerbroker.MSG_LAIM_INVALID_CREDENTIALS) == (
        400,
        "Credenciales no válidas",
    )
    assert _status_for(routerbroker.MSG_LAIM_ACCOUNT_LOCKED) == (
        403,
        routerbroker.MSG_LAIM_ACCOUNT_LOCKED,
    )
    assert _status_for(routerbroker.MSG_LAIM_USER_DISABLED) == (
        403,
        "El usuario no está habilitado",
    )
    assert _status_for(routerbroker.MSG_LAIM_LOGIN_UNAVAILABLE) == (
        502,
        "No se pudo iniciar sesión. Inténtelo más tarde.",
    )

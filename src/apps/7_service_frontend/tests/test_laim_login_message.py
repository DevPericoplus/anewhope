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

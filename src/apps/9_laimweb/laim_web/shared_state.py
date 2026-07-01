"""Carga dinámica de LaimSharedSessionState."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_laim_shared_session_state():
    """Carga LaimSharedSessionState evitando imports de paquetes numéricos."""
    shared_state_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "2_shared_application"
        / "reflex_shared"
        / "laim_shared_session_state.py"
    )
    spec = importlib.util.spec_from_file_location(
        "laim_shared_session_state", shared_state_path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_shared_session_state"] = module
    spec.loader.exec_module(module)
    return module.LaimSharedSessionState


LaimSharedSessionState = load_laim_shared_session_state()

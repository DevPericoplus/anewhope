"""Carga dinámica de LaimSharedSessionState."""

from __future__ import annotations

from pathlib import Path

from laim_web.dynamic_import import load_module_from_path


def load_laim_shared_session_state():
    """Carga LaimSharedSessionState evitando imports de paquetes numéricos."""
    shared_state_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "2_shared_application"
        / "reflex_shared"
        / "laim_shared_session_state.py"
    )
    module = load_module_from_path(shared_state_path, "laim_shared_session_state")
    return module.LaimSharedSessionState


LaimSharedSessionState = load_laim_shared_session_state()

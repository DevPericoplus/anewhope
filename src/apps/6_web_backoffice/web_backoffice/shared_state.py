"""
Módulo para cargar SharedSessionState dinámicamente.

Este módulo maneja la importación de SharedSessionState evitando el SyntaxError
que ocurre al importar desde paquetes con nombres numéricos (2_shared_application).
"""
import sys
import importlib.util
from pathlib import Path


def load_shared_session_state():
    """
    Carga SharedSessionState dinámicamente.
    
    Returns:
        class: La clase SharedSessionState
    """
    # Ruta al archivo shared_session_state.py
    shared_state_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "2_shared_application"
        / "reflex_shared"
        / "shared_session_state.py"
    )
    
    # Cargar el módulo dinámicamente
    spec = importlib.util.spec_from_file_location(
        "shared_session_state", shared_state_path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["shared_session_state"] = module
    spec.loader.exec_module(module)
    
    return module.SharedSessionState


# Instancia única de SharedSessionState
SharedSessionState = load_shared_session_state()

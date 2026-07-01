"""Utilidades para cargar módulos por ruta sin imports de paquetes numéricos."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_module_from_path(path: Path, module_name: str) -> ModuleType:
    """Carga un módulo Python desde una ruta absoluta."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar el módulo desde {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(module_name, module)
    spec.loader.exec_module(module)
    return module

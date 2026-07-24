"""Helper para importar el módulo CRT desde apps con rutas numeradas."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def load_crt_module(module_name: str, from_file: str | Path) -> ModuleType:
    """Carga un submódulo CRT usando importlib (patrón del repo)."""
    crt_dir = Path(from_file).resolve().parents[3] / "2_shared_application" / "reflex_shared" / "crt"
    target = crt_dir / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(f"crt_{module_name}", target)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar módulo CRT: {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

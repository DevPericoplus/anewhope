"""Configuración de pytest para el middleware."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _ensure_path(path: Path) -> None:
    """Asegura que la ruta esté en sys.path."""
    resolved = str(path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


_REPO_ROOT = Path(__file__).resolve().parents[3]
_ensure_path(Path(__file__).parent)
_ensure_path(_REPO_ROOT)

_spec = importlib.util.spec_from_file_location(
    "anewhope_import_aliases",
    _REPO_ROOT / "tests" / "import_aliases.py",
)
if _spec is not None and _spec.loader is not None:
    _aliases = importlib.util.module_from_spec(_spec)
    sys.modules["anewhope_import_aliases"] = _aliases
    _spec.loader.exec_module(_aliases)
    _aliases.bootstrap_test_imports(_REPO_ROOT)

"""Configuración de pytest para la app web frontend."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_path(path: Path) -> None:
    """Asegura que la ruta esté en sys.path."""

    resolved = str(path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


# Permite importar tests.* cuando se ejecuta desde la raíz
_ensure_path(Path(__file__).parent)

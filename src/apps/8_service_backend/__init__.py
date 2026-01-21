"""Inicializa el paquete del broker backend."""

try:
    from .apibe import app
except ImportError:  # pragma: no cover - soporte para ejecuciones fuera de paquete
    from apibe import app

__all__ = ["app"]

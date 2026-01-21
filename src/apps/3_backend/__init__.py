"""Inicializa el paquete del backend core."""

try:
    from .apicore import app
except ImportError:  # pragma: no cover - soporte para ejecuciones fuera de paquete
    from apicore import app

__all__ = ["app"]

"""Inicializa el paquete del backend IA (trainer)."""

try:
    from .apitrainer import app
except ImportError:  # pragma: no cover - soporte para ejecuciones fuera de paquete
    from apitrainer import app

__all__ = ["app"]

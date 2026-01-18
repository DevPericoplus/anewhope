"""Inicializa el paquete del servicio frontend."""

try:
    from .apife import app
except ImportError:  # pragma: no cover - soporte para ejecuciones fuera de paquete
    from apife import app

__all__ = ["app"]

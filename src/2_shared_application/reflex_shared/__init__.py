"""
Componentes Reflex compartidos entre aplicaciones web.

Este paquete contiene estados y componentes que se comparten entre
web_frontend (puerto 8005) y web_backoffice (puerto 8006) mediante Redis.
"""

from .shared_session_state import SharedSessionState
from .activity_logger import (
    ActivityLogger,
    get_frontend_logger,
    get_backoffice_logger,
)

__all__ = [
    "SharedSessionState",
    "ActivityLogger",
    "get_frontend_logger",
    "get_backoffice_logger",
]

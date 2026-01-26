"""
Componentes Reflex compartidos entre aplicaciones web.

Este paquete contiene estados y componentes que se comparten entre
web_frontend (puerto 8005) y web_backoffice (puerto 8006) mediante Redis.
"""

from .shared_session_state import SharedSessionState

__all__ = ["SharedSessionState"]

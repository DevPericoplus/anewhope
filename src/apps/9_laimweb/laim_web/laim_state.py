"""Estado global de la aplicación LAIM Web.

Hereda de SharedSessionState para compartir sesión vía Redis
con el resto de aplicaciones del ecosistema.
"""

from __future__ import annotations

import reflex as rx
from reflex.event import event


class LaimWebState(rx.State):
    """Estado base de LAIM Web.

    Gestiona la sesión del usuario y la comunicación con el middleware.
    """

    # Sesión
    is_logged_in: bool = False
    user_id: int = 0
    user_name: str = ""
    organization_id: int = 0
    identity_type_id: int = 0
    access_token: str = ""
    session_token: str = ""

    # UI / Navegación
    loading: bool = False
    error_message: str = ""
    active_menu: str = "inicio"

    # Login
    login_username: str = ""
    login_password: str = ""

    @event
    def set_login_username(self, value: str) -> None:
        """Setter explícito para login_username."""
        self.login_username = value

    @event
    def set_login_password(self, value: str) -> None:
        """Setter explícito para login_password."""
        self.login_password = value

    def on_page_load(self) -> None:
        """Carga inicial de la página."""
        pass

    @event
    def set_menu(self, item: str) -> None:
        """Cambia la opción activa del menú."""
        self.active_menu = item

    @event
    def handle_login(self) -> None:
        """Procesa el login del usuario a través del middleware."""
        from laim_web.adapters.laim_api_client import laim_login

        self.loading = True
        self.error_message = ""

        result = laim_login(self.login_username, self.login_password)

        if result.get("success"):
            self.is_logged_in = True
            self.user_id = result.get("user_id", 0)
            self.user_name = result.get("user_name", "")
            self.organization_id = result.get("organization_id", 0)
            self.identity_type_id = result.get("identity_type_id", 0)
            self.access_token = result.get("access_token", "")
            self.session_token = result.get("session_token", "")
            self.active_menu = "dashboard"
        else:
            self.error_message = result.get("error", "Error de autenticación")

        self.loading = False

    @event
    def handle_logout(self) -> None:
        """Cierra la sesión del usuario."""
        self.is_logged_in = False
        self.user_id = 0
        self.user_name = ""
        self.access_token = ""
        self.session_token = ""
        self.active_menu = "inicio"
        self.login_username = ""
        self.login_password = ""
        self.error_message = ""

"""Estado de los modales Usuarios y Registro en Configuración → General."""

from __future__ import annotations

from typing import Any

import reflex as rx

from laim_web.config_ops import (
    portal_environment_name,
    support_admin_call,
    users_list_path,
    visible_account,
)
from laim_web.install_dashboard import build_dashboard

CONFIG_EVENT_HANDLER_NAMES: list[str] = []


def config_event(func):
    """Evento síncrono re-registrable en LaimWebState."""
    CONFIG_EVENT_HANDLER_NAMES.append(func.__name__)
    return rx.event(func)


def config_background_event(func):
    """Evento de red re-registrable en LaimWebState."""
    CONFIG_EVENT_HANDLER_NAMES.append(func.__name__)
    return rx.event(background=True)(func)


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "bloqueado"}
    return bool(value)


class LaimConfigMixin(rx.State, mixin=True):
    """Modales de General. La identidad sale del login, no de un argumento del cliente."""

    cfg_users_open: bool = False
    cfg_users_loading: bool = False
    cfg_users_error: str = ""
    cfg_users_notice: str = ""
    cfg_users_query: str = ""
    cfg_users: list[dict[str, Any]] = []
    cfg_user_open: bool = False
    cfg_user_id: int = 0
    cfg_user_name: str = ""
    cfg_user_email: str = ""
    cfg_user_mobile: str = ""
    cfg_user_full_name: str = ""
    cfg_password_open: bool = False
    cfg_password: str = ""
    cfg_password_confirm: str = ""
    cfg_registro_open: bool = False
    cfg_registro_loading: bool = False
    cfg_registro_error: str = ""
    cfg_registro_rows: list[dict[str, Any]] = []
    cfg_dash_open: bool = False
    cfg_dash_title: str = ""
    cfg_dash_subtitle: str = ""
    cfg_dash_highlights: list[dict[str, Any]] = []
    cfg_dash_tiles: list[dict[str, Any]] = []
    cfg_dash_channels: list[dict[str, Any]] = []
    cfg_svg_trend: str = ""
    cfg_svg_monthly: str = ""
    cfg_svg_mix: str = ""
    cfg_svg_scatter: str = ""
    cfg_svg_os: str = ""
    cfg_svg_gauge: str = ""

    @config_event
    def set_cfg_users_query(self, value: str):
        self.cfg_users_query = value

    @config_event
    def set_cfg_user_name(self, value: str):
        self.cfg_user_name = value

    @config_event
    def set_cfg_user_full_name(self, value: str):
        self.cfg_user_full_name = value

    @config_event
    def set_cfg_user_email(self, value: str):
        self.cfg_user_email = value

    @config_event
    def set_cfg_user_mobile(self, value: str):
        self.cfg_user_mobile = value

    @config_event
    def set_cfg_password(self, value: str):
        self.cfg_password = value

    @config_event
    def set_cfg_password_confirm(self, value: str):
        self.cfg_password_confirm = value

    def _apply_user_form(self, item: dict[str, Any]) -> None:
        account = visible_account(item)
        self.cfg_user_id = int(account["user_id"])
        self.cfg_user_name = account["user_name"]
        self.cfg_user_email = account["user_email"]
        self.cfg_user_mobile = account["user_mobile"]
        self.cfg_user_full_name = account["full_name"]

    @config_event
    def close_cfg_users(self):
        self.cfg_users_open = False
        self.cfg_user_open = False
        self.cfg_password_open = False

    @config_event
    def close_cfg_user(self):
        self.cfg_user_open = False
        self.cfg_password_open = False
        self.cfg_password = ""
        self.cfg_password_confirm = ""

    @config_event
    def open_cfg_password(self):
        self.cfg_password = ""
        self.cfg_password_confirm = ""
        self.cfg_users_error = ""
        self.cfg_password_open = True

    @config_event
    def close_cfg_password(self):
        self.cfg_password_open = False
        self.cfg_password = ""
        self.cfg_password_confirm = ""

    @config_event
    def close_cfg_registro(self):
        self.cfg_registro_open = False
        self.cfg_dash_open = False

    @config_event
    def close_cfg_dash(self):
        self.cfg_dash_open = False

    async def _load_cfg_users_body(self):
        async with self:
            self.cfg_users_loading = True
            self.cfg_users_error = ""
            identity = int(self.identity_type_id or 0)
            query = self.cfg_users_query
        result = support_admin_call(identity, "GET", users_list_path(query))
        async with self:
            self.cfg_users_loading = False
            if not result.get("success"):
                self.cfg_users_error = str(result.get("error") or "No se pudieron listar los usuarios")
                return
            self.cfg_users = [visible_account(item) for item in result.get("items") or []]

    @config_background_event
    async def open_cfg_users(self):
        async with self:
            self.cfg_users_open = True
            self.cfg_users_error = ""
            self.cfg_users_notice = ""
        await self._load_cfg_users_body()

    @config_background_event
    async def load_cfg_users(self):
        await self._load_cfg_users_body()

    @config_background_event
    async def open_cfg_user(self, user_id: int):
        async with self:
            self.cfg_users_loading = True
            self.cfg_users_error = ""
            self.cfg_users_notice = ""
            identity = int(self.identity_type_id or 0)
            target = int(user_id)
        result = support_admin_call(identity, "GET", f"/laim/support/users/{target}")
        async with self:
            self.cfg_users_loading = False
            if not result.get("success") or not result.get("item"):
                self.cfg_users_error = str(result.get("error") or "No se pudo abrir el usuario")
                return
            self._apply_user_form(result["item"])
            self.cfg_password = ""
            self.cfg_password_confirm = ""
            self.cfg_user_open = True

    @config_background_event
    async def save_cfg_user(self):
        async with self:
            self.cfg_users_loading = True
            self.cfg_users_error = ""
            self.cfg_users_notice = ""
            identity = int(self.identity_type_id or 0)
            user_id = int(self.cfg_user_id)
            payload = {
                "user_name": self.cfg_user_name.strip(),
                "user_email": self.cfg_user_email.strip(),
                "user_mobile": self.cfg_user_mobile.strip(),
                "full_name": self.cfg_user_full_name.strip(),
            }
        result = support_admin_call(identity, "PATCH", f"/laim/support/users/{user_id}", payload)
        async with self:
            self.cfg_users_loading = False
            if not result.get("success") or not result.get("item"):
                self.cfg_users_error = str(result.get("error") or "No se pudo guardar")
                return
            self._apply_user_form(result["item"])
            self.cfg_users_notice = "Cambios guardados."
            identity = int(self.identity_type_id or 0)
            query = self.cfg_users_query
        listing = support_admin_call(identity, "GET", users_list_path(query))
        async with self:
            if listing.get("success"):
                self.cfg_users = [visible_account(item) for item in listing.get("items") or []]

    @config_background_event
    async def submit_cfg_password(self):
        async with self:
            password = self.cfg_password
            confirm = self.cfg_password_confirm
            if len(password) < 8 or password != confirm:
                self.cfg_users_error = (
                    "La contraseña debe tener al menos 8 caracteres y coincidir."
                )
                return
            self.cfg_users_loading = True
            self.cfg_users_error = ""
            self.cfg_users_notice = ""
            identity = int(self.identity_type_id or 0)
            user_id = int(self.cfg_user_id)
        result = support_admin_call(
            identity,
            "POST",
            f"/laim/support/users/{user_id}/password",
            {"password": password, "password_confirm": confirm},
        )
        async with self:
            self.cfg_users_loading = False
            if not result.get("success"):
                self.cfg_users_error = str(result.get("error") or "No se pudo actualizar la contraseña")
                return
            self.cfg_password_open = False
            self.cfg_password = ""
            self.cfg_password_confirm = ""
            self.cfg_users_notice = str(
                result.get("message") or "La contraseña se ha actualizado con éxito"
            )
            identity = int(self.identity_type_id or 0)
            query = self.cfg_users_query
        listing = support_admin_call(identity, "GET", users_list_path(query))
        async with self:
            if listing.get("success"):
                self.cfg_users = [visible_account(item) for item in listing.get("items") or []]

    @config_background_event
    async def toggle_cfg_user_status(self, user_id: int, blocked: bool):
        """Envía el estado contrario. Si el remoto falla, la fila se queda igual."""
        async with self:
            self.cfg_users_loading = True
            self.cfg_users_error = ""
            self.cfg_users_notice = ""
            identity = int(self.identity_type_id or 0)
            target = int(user_id)
            desired = not _as_bool(blocked)
            previous = list(self.cfg_users)
        result = support_admin_call(
            identity,
            "POST",
            f"/laim/support/users/{target}/status",
            {"blocked": desired},
        )
        async with self:
            self.cfg_users_loading = False
            if not result.get("success"):
                self.cfg_users = previous
                self.cfg_users_error = str(result.get("error") or "No se pudo cambiar el estado")
                return
            item = result.get("item") or {}
            if not item:
                self.cfg_users = previous
                self.cfg_users_error = "El servidor no devolvió la cuenta."
                return
            account = visible_account(item)
            self.cfg_users = [
                account if int(row.get("user_id") or 0) == target else row for row in previous
            ]
            self.cfg_users_notice = str(
                result.get("message")
                or ("La cuenta queda bloqueada." if desired else "La cuenta queda activa.")
            )

    async def _load_cfg_registro_body(self):
        async with self:
            self.cfg_registro_loading = True
            self.cfg_registro_error = ""
            identity = int(self.identity_type_id or 0)
        metrics = support_admin_call(identity, "GET", "/laim/support/installations/metrics")
        listing = support_admin_call(identity, "GET", "/laim/support/installations")
        async with self:
            self.cfg_registro_loading = False
            if not metrics.get("success"):
                self.cfg_registro_error = str(metrics.get("error") or "No se pudieron leer las métricas")
                return
            if not listing.get("success"):
                self.cfg_registro_error = str(listing.get("error") or "No se pudo leer el inventario")
                return
            dashboard = build_dashboard(
                portal_environment_name(),
                metrics,
                listing.get("items") or [],
            )
            self._apply_dashboard(dashboard)

    def _apply_dashboard(self, dashboard: dict[str, Any]) -> None:
        self.cfg_dash_title = str(dashboard.get("title") or "")
        self.cfg_dash_subtitle = str(dashboard.get("subtitle") or "")
        self.cfg_dash_highlights = list(dashboard.get("highlights") or [])
        self.cfg_dash_tiles = list(dashboard.get("tiles") or [])
        self.cfg_dash_channels = list(dashboard.get("channels") or [])
        self.cfg_svg_trend = str(dashboard.get("svg_trend") or "")
        self.cfg_svg_monthly = str(dashboard.get("svg_monthly") or "")
        self.cfg_svg_mix = str(dashboard.get("svg_mix") or "")
        self.cfg_svg_scatter = str(dashboard.get("svg_scatter") or "")
        self.cfg_svg_os = str(dashboard.get("svg_os") or "")
        self.cfg_svg_gauge = str(dashboard.get("svg_gauge") or "")
        self.cfg_registro_rows = list(dashboard.get("items") or [])

    @config_background_event
    async def open_cfg_registro(self):
        async with self:
            self.cfg_registro_open = True
            self.cfg_registro_error = ""
            self.cfg_dash_open = False
        await self._load_cfg_registro_body()

    @config_background_event
    async def load_cfg_registro(self):
        await self._load_cfg_registro_body()

    @config_background_event
    async def open_cfg_dash(self):
        async with self:
            if not self.cfg_registro_rows and not self.cfg_dash_subtitle:
                self.cfg_registro_error = "Todavía no hay datos de registro."
                return
            self.cfg_dash_open = True

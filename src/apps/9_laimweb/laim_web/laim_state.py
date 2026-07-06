"""Estado global de la aplicación LAIM Web.

Hereda de LaimSharedSessionState para sincronizar sesión vía Redis
con prefijo ``laim:``.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import reflex as rx
from reflex.event import event

from laim_web.laim_forum_mixin import LaimForumMixin
from laim_web.shared_state import LaimSharedSessionState

EventHandlerReturn = Any

RESET_LAIM_HCAPTCHA_SCRIPT = (
    "if (typeof window.resetLaimHcaptcha === 'function') { window.resetLaimHcaptcha(); }"
)

SCHEDULE_LAIM_HCAPTCHA_RENDER_SCRIPT = """
(function() {
  var attempts = 0;
  function tryRender() {
    if (typeof window.renderLaimHcaptchaWidget === 'function') {
      window.renderLaimHcaptchaWidget();
    }
    if (++attempts < 20) {
      setTimeout(tryRender, 200);
    }
  }
  tryRender();
})();
"""

READ_LAIM_HCAPTCHA_TOKEN_SCRIPT = """
(function() {
  var input = document.getElementById('laim-hcaptcha-token-input');
  var token = window.__LAIM_HCAPTCHA_TOKEN__ || (input && input.value) || '';
  return String(token).trim();
})();
"""


class LaimWebState(LaimSharedSessionState, LaimForumMixin):
    """Estado de LAIM Web con autenticación y UI."""

    @rx.var
    def is_laim_admin(self) -> bool:
        """True si el usuario tiene rol administrador (SuperAdmin o Admin org)."""
        if not self.is_logged_in or self.identity_type_id <= 0:
            return False
        from laim_web.static_pages_loader import LAIM_ADMIN_IDENTITY_TYPE_IDS

        return self.identity_type_id in LAIM_ADMIN_IDENTITY_TYPE_IDS

    # UI / Navegación
    loading: bool = False
    error_message: str = ""
    login_error: str = ""
    active_menu: str = "inicio"
    static_page_content: str = ""

    # Login / modales de autenticación
    login_username: str = ""
    login_password: str = ""
    login_modal_open: bool = False
    register_modal_open: bool = False
    register_message: str = ""

    # Registro
    reg_username: str = ""
    reg_password: str = ""
    reg_password_confirm: str = ""
    reg_email: str = ""
    reg_full_name: str = ""
    reg_mobile: str = ""
    reg_hcaptcha_token: str = ""

    # Formulario de contacto
    contact_usage_mode: str = "local"
    contact_affected_user: str = ""
    contact_message_body: str = ""
    contact_reply_email: str = ""
    contact_form_error: str = ""
    contact_form_success: bool = False
    contact_submitting: bool = False
    _pending_contact_screenshot: dict[str, str] | None = None

    _token_renewal_running: bool = False

    @event
    def set_reg_username(self, value: str) -> None:
        self.reg_username = value

    @event
    def set_reg_password(self, value: str) -> None:
        self.reg_password = value

    @event
    def set_reg_password_confirm(self, value: str) -> None:
        self.reg_password_confirm = value

    @event
    def set_reg_email(self, value: str) -> None:
        self.reg_email = value

    @event
    def set_reg_full_name(self, value: str) -> None:
        self.reg_full_name = value

    @event
    def set_reg_mobile(self, value: str) -> None:
        self.reg_mobile = value

    @event
    def set_reg_hcaptcha_token_value(self, value: str) -> None:
        """Sincroniza el token hCaptcha desde el widget (input oculto)."""
        self.reg_hcaptcha_token = value

    @event
    def handle_register(self) -> EventHandlerReturn:
        """Inicia registro; usa hCaptcha solo si está configurado en el entorno."""
        from laim_web.components.hcaptcha import is_hcaptcha_configured

        validation_error = self._validate_register_form()
        if validation_error:
            self.error_message = validation_error
            return None

        self.error_message = ""

        if not is_hcaptcha_configured():
            return LaimWebState.complete_register_background

        if self.reg_hcaptcha_token.strip():
            return LaimWebState.complete_register_background

        return rx.call_script(
            READ_LAIM_HCAPTCHA_TOKEN_SCRIPT,
            callback=LaimWebState.set_reg_hcaptcha_token,
        )

    def _validate_register_form(self) -> str:
        """Valida campos obligatorios del formulario de registro."""
        if not self.reg_username.strip():
            return "El usuario es obligatorio."
        if not self.reg_full_name.strip():
            return "El nombre completo es obligatorio."
        if not self.reg_email.strip():
            return "El email es obligatorio."
        if not self.reg_password:
            return "La contraseña es obligatoria."
        if self.reg_password != self.reg_password_confirm:
            return "Las contraseñas no coinciden."
        if len(self.reg_password) < 8:
            return "La contraseña debe tener al menos 8 caracteres."
        return ""

    @event
    def set_reg_hcaptcha_token(self, token: str | None) -> EventHandlerReturn:
        """Recibe token hCaptcha desde JavaScript y continúa el registro."""
        from laim_web.components.hcaptcha import is_hcaptcha_configured

        resolved_token = (token or "").strip()
        if is_hcaptcha_configured() and not resolved_token:
            self.error_message = (
                "Debe completar la verificación anti-bot (hCaptcha) antes de registrarse."
            )
            return None

        self.reg_hcaptcha_token = resolved_token
        return LaimWebState.complete_register_background

    @rx.event(background=True)
    async def complete_register_background(self) -> None:
        """Ejecuta el registro en segundo plano para no bloquear la UI."""
        from laim_web.adapters.laim_api_client import laim_register
        from laim_web.components.hcaptcha import is_hcaptcha_configured

        async with self:
            validation_error = self._validate_register_form()
            if validation_error:
                self.error_message = validation_error
                return

            if is_hcaptcha_configured() and not self.reg_hcaptcha_token.strip():
                self.error_message = (
                    "Debe completar la verificación anti-bot (hCaptcha) antes de registrarse."
                )
                return

            self.loading = True
            self.error_message = ""
            self.register_message = ""

            username = self.reg_username
            password = self.reg_password
            password_confirm = self.reg_password_confirm
            email = self.reg_email
            full_name = self.reg_full_name
            mobile = self.reg_mobile.strip() or None
            hcaptcha_token = self.reg_hcaptcha_token

        try:
            result = laim_register(
                username=username,
                password=password,
                password_confirm=password_confirm,
                email=email,
                full_name=full_name,
                mobile=mobile,
                hcaptcha_token=hcaptcha_token,
            )
        except Exception as exc:
            result = {"success": False, "error": f"Error inesperado: {exc}"}

        async with self:
            try:
                if result.get("success"):
                    self.register_message = result.get(
                        "message", "Registro completado. Ya puede iniciar sesión."
                    )
                    self.register_modal_open = False
                    self.login_modal_open = True
                    self.login_username = username
                    self.reg_username = ""
                    self.reg_password = ""
                    self.reg_password_confirm = ""
                    self.reg_email = ""
                    self.reg_full_name = ""
                    self.reg_mobile = ""
                    self.reg_hcaptcha_token = ""
                else:
                    detail = result.get("error", "Error en registro")
                    if "HTTP 400" in str(detail):
                        detail = "Datos de registro inválidos o usuario ya existente"
                    self.error_message = str(detail)
            finally:
                self.loading = False

    @event
    def open_login_modal(self) -> None:
        """Abre el modal de inicio de sesión."""
        self.login_modal_open = True
        self.register_modal_open = False
        self.error_message = ""

    @event
    def close_login_modal(self) -> None:
        """Cierra el modal de inicio de sesión."""
        self.login_modal_open = False
        self.error_message = ""

    @event
    def open_register_modal(self) -> EventHandlerReturn:
        """Abre el modal de registro."""
        self.register_modal_open = True
        self.login_modal_open = False
        self.error_message = ""
        self.register_message = ""
        self.reg_hcaptcha_token = ""
        return rx.call_script(SCHEDULE_LAIM_HCAPTCHA_RENDER_SCRIPT)

    @event
    def close_register_modal(self) -> EventHandlerReturn:
        """Cierra el modal de registro."""
        self.register_modal_open = False
        self.error_message = ""
        self.loading = False
        return rx.call_script(RESET_LAIM_HCAPTCHA_SCRIPT)

    @event
    def switch_to_register_modal(self) -> EventHandlerReturn:
        """Cierra login y abre registro."""
        self.login_modal_open = False
        self.register_modal_open = True
        self.error_message = ""
        self.register_message = ""
        self.reg_hcaptcha_token = ""
        return rx.call_script(SCHEDULE_LAIM_HCAPTCHA_RENDER_SCRIPT)

    @event
    def switch_to_login_modal(self) -> None:
        """Cierra registro y abre login."""
        self.register_modal_open = False
        self.login_modal_open = True
        self.error_message = ""

    @event
    def set_login_username(self, value: str) -> None:
        self.login_username = value

    @event
    def set_login_password(self, value: str) -> None:
        self.login_password = value

    def _sync_menu_for_session(self) -> None:
        """Alinea menú y contenido con el estado de sesión actual."""
        from laim_web.static_pages_loader import (
            AUTHENTICATED_PAGE_MENUS,
            PUBLIC_MENU_FILES,
            can_access_admin_config_menu,
            is_admin_config_menu,
        )

        if self.is_logged_in:
            if is_admin_config_menu(self.active_menu):
                if not can_access_admin_config_menu(
                    self.active_menu, self.identity_type_id
                ):
                    self.active_menu = "instaladores"
            elif self.active_menu not in AUTHENTICATED_PAGE_MENUS:
                if self.active_menu not in PUBLIC_MENU_FILES:
                    self.active_menu = "instaladores"
        elif self.active_menu not in PUBLIC_MENU_FILES:
            self.active_menu = "inicio"

        self._load_static_page(self.active_menu)

    @rx.event
    def on_page_load(self) -> EventHandlerReturn:
        """Carga inicial de la página."""
        self._sync_menu_for_session()
        if self.is_logged_in and self.session_token and not self._token_renewal_running:
            self._token_renewal_running = True
            return LaimWebState.auto_renew_tokens_loop

    def _load_static_page(self, menu: str) -> None:
        """Carga markdown de static_pages/ para menús públicos."""
        from laim_web.static_pages_loader import STATIC_PAGE_MENUS, load_static_page_markdown

        if menu in STATIC_PAGE_MENUS:
            self.static_page_content = load_static_page_markdown(menu)

    @event
    def set_menu(self, item: str) -> None:
        from laim_web.static_pages_loader import can_access_admin_config_menu

        if not can_access_admin_config_menu(item, self.identity_type_id):
            return

        self.active_menu = item
        self._load_static_page(item)
        if item == "contacto":
            self._prepare_contact_form()

    def _prepare_contact_form(self) -> None:
        """Pre-rellena el formulario de contacto al abrir la página."""
        if self.is_logged_in and self.user_email.strip() and not self.contact_reply_email.strip():
            self.contact_reply_email = self.user_email.strip()
        self.contact_form_error = ""
        self.contact_form_success = False

    @event
    def set_contact_usage_mode(self, value: str) -> None:
        self.contact_usage_mode = value

    @event
    def set_contact_affected_user(self, value: str) -> None:
        self.contact_affected_user = value

    @event
    def set_contact_message_body(self, value: str) -> None:
        self.contact_message_body = value

    @event
    def set_contact_reply_email(self, value: str) -> None:
        self.contact_reply_email = value

    def _validate_contact_form(self) -> str:
        """Valida campos del formulario de contacto."""
        if self.contact_usage_mode not in {
            "local",
            "share",
            "connect",
            "remote",
            "other",
        }:
            return "Seleccione un modo de uso válido."
        if not self.contact_reply_email.strip():
            return "Indique un e-mail de respuesta."
        if "@" not in self.contact_reply_email or "." not in self.contact_reply_email:
            return "El e-mail de respuesta no es válido."
        if len(self.contact_message_body.strip()) < 10:
            return "La descripción debe tener al menos 10 caracteres."
        return ""

    _CONTACT_SCREENSHOT_SCRIPT = """
(() => {
  const input = document.getElementById('laim_contact_screenshot');
  if (!input || !input.files || input.files.length === 0) {
    return { screenshot: null };
  }
  const file = input.files[0];
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result || '';
      const base64 = typeof result === 'string' && result.includes(',')
        ? result.split(',')[1]
        : '';
      resolve({
        screenshot: {
          file_name: file.name,
          mime_type: file.type || 'application/octet-stream',
          data_base64: base64,
        },
      });
    };
    reader.onerror = () => resolve({ screenshot: null });
    reader.readAsDataURL(file);
  });
})()
"""

    @event
    def submit_contact_form(self) -> EventHandlerReturn:
        """Inicia envío del formulario (lee captura en el cliente)."""
        validation_error = self._validate_contact_form()
        if validation_error:
            self.contact_form_error = validation_error
            self.contact_form_success = False
            return None

        self.contact_form_error = ""
        self.contact_form_success = False
        return rx.call_script(
            self._CONTACT_SCREENSHOT_SCRIPT,
            callback=LaimWebState.contact_submit_with_screenshot,
        )

    @event
    def contact_submit_with_screenshot(
        self, payload: dict[str, object] | None
    ) -> EventHandlerReturn:
        """Recibe captura opcional y lanza envío en background."""
        validation_error = self._validate_contact_form()
        if validation_error:
            self.contact_form_error = validation_error
            return None

        screenshot_data: dict[str, str] | None = None
        if isinstance(payload, dict):
            raw_screenshot = payload.get("screenshot")
            if isinstance(raw_screenshot, dict):
                file_name = str(raw_screenshot.get("file_name", "")).strip()
                mime_type = str(raw_screenshot.get("mime_type", "")).strip()
                data_base64 = str(raw_screenshot.get("data_base64", "")).strip()
                if file_name and mime_type and data_base64:
                    screenshot_data = {
                        "file_name": file_name,
                        "mime_type": mime_type,
                        "data_base64": data_base64,
                    }

        self._pending_contact_screenshot = screenshot_data
        return LaimWebState.submit_contact_form_background

    @rx.event(background=True)
    async def submit_contact_form_background(self) -> None:
        """Envía el mensaje de contacto al middleware."""
        from laim_web.adapters.laim_api_client import laim_submit_contact_message

        async with self:
            validation_error = self._validate_contact_form()
            if validation_error:
                self.contact_form_error = validation_error
                return

            self.contact_submitting = True
            self.contact_form_error = ""
            self.contact_form_success = False
            screenshot = self._pending_contact_screenshot
            self._pending_contact_screenshot = None

            payload: dict[str, object] = {
                "usage_mode": self.contact_usage_mode,
                "affected_user_info": self.contact_affected_user.strip(),
                "message_body": self.contact_message_body.strip(),
                "reply_email": self.contact_reply_email.strip(),
            }
            if screenshot:
                payload["screenshot"] = screenshot

            access_token = self.access_token if self.is_logged_in else ""
            session_token = self.session_token if self.is_logged_in else ""

        result = laim_submit_contact_message(
            payload=payload,
            access_token=access_token,
            session_token=session_token,
        )

        async with self:
            self.contact_submitting = False
            if result.get("success"):
                self.contact_form_success = True
                self.contact_affected_user = ""
                self.contact_message_body = ""
                if not self.is_logged_in:
                    self.contact_reply_email = ""
                return

            self.contact_form_error = result.get(
                "error", "No se pudo enviar el mensaje. Inténtelo más tarde."
            )

    @event
    def handle_page_action(self, action_key: str) -> EventHandlerReturn:
        """Ejecuta acciones de botones bajo el contenido markdown."""
        navigate_to_menu = {
            "faq_to_support": "soporte",
            "faq_privacy": "faq",
            "faq_security": "manuales",
            "support_ticket": "soporte",
            "manual_quickstart": "manuales",
            "manual_user": "manuales",
            "manual_security": "manuales",
            "manual_cli": "manuales",
            "custom_howto": "modelos_personalizados",
        }
        if action_key in navigate_to_menu:
            target = navigate_to_menu[action_key]
            self.active_menu = target
            self._load_static_page(target)
            return None

        pending_messages = {
            "download_windows": (
                "La descarga para Windows se habilitará en esta sección en breve."
            ),
            "download_macos": (
                "La descarga para macOS se habilitará en esta sección en breve."
            ),
            "download_linux_deb": (
                "La descarga Linux (.deb) se habilitará en esta sección en breve."
            ),
            "download_linux_rpm": (
                "La descarga Linux (.rpm) se habilitará en esta sección en breve."
            ),
            "view_requirements": (
                "Consulte Manuales → Configuración segura para requisitos detallados."
            ),
            "catalog_base_models": (
                "El catálogo de modelos base estará disponible desde el cliente LAIM."
            ),
            "recommended_model": (
                "Use el asistente del cliente LAIM para recomendar un modelo base."
            ),
            "compare_requirements": (
                "La comparativa de requisitos se publicará junto al catálogo de modelos."
            ),
            "catalog_specialized": (
                "Los modelos especializados se listarán aquí cuando estén asignados a su cuenta."
            ),
            "skills_library": (
                "La biblioteca de skills se integrará con las próximas versiones del cliente."
            ),
            "skills_sample": (
                "El skill de ejemplo se instalará desde el cliente LAIM."
            ),
            "skills_create": (
                "La creación de skills personalizados estará documentada en Manuales."
            ),
            "addons_catalog": (
                "El catálogo de complementos se ampliará en próximas versiones."
            ),
            "addons_integrations": (
                "Las integraciones recomendadas se anunciarán en las notas de versión."
            ),
            "addons_changelog": (
                "Las notas de versión se publicarán en esta misma sección."
            ),
            "support_status": (
                "Todos los servicios del portal están operativos en condiciones normales."
            ),
        }
        message = pending_messages.get(
            action_key,
            "Funcionalidad en preparación. Consulte Soporte si lo necesita con urgencia.",
        )
        return rx.toast.info(message)

    def _load_permissions_after_login(
        self, identity_type_id: int, access_token: str, session_token: str
    ) -> dict[str, Any]:
        """Obtiene permisos de bajo nivel desde el middleware."""
        from laim_web.adapters.laim_api_client import laim_get_session_permissions

        response = laim_get_session_permissions(
            identity_type_id=identity_type_id,
            access_token=access_token,
            session_token=session_token,
        )
        if response.get("success"):
            return response.get("permissions", {})
        return {}

    @event
    def handle_login(self) -> EventHandlerReturn:
        """Procesa login contra middleware LAIM."""
        from laim_web.adapters.laim_api_client import laim_login

        self.loading = True
        self.error_message = ""
        self.login_error = ""

        result = laim_login(self.login_username, self.login_password)

        if result.get("success"):
            permissions = self._load_permissions_after_login(
                identity_type_id=int(result.get("identity_type_id", 0)),
                access_token=result.get("access_token", ""),
                session_token=result.get("session_token", ""),
            )
            self.load_user_data(
                user_id=int(result.get("user_id", 0)),
                organization_id=int(result.get("organization_id", 0)),
                identity_type_id=int(result.get("identity_type_id", 0)),
                user_name=result.get("user_name", ""),
                user_email=result.get("user_email", ""),
                user_mobile=result.get("user_mobile", ""),
                access_token=result.get("access_token", ""),
                session_token=result.get("session_token", ""),
                permissions=permissions,
                access_expires_at=int(result.get("access_expires_at", 0)),
                session_expires_at=int(result.get("session_expires_at", 0)),
                session_id=result.get("session_id", ""),
            )
            self.login_modal_open = False
            self.register_modal_open = False
            self.register_message = ""
            self.loading = False
            self.active_menu = "instaladores"
            self._load_static_page("instaladores")
            self._token_renewal_running = True
            return LaimWebState.auto_renew_tokens_loop

        self.error_message = result.get("error", "Error de autenticación")
        self.loading = False

    @event
    def handle_logout(self) -> EventHandlerReturn:
        """Cierra sesión LAIM y vuelve al área pública."""
        from laim_web.adapters.laim_api_client import laim_logout

        access_token = self.access_token
        session_token = self.session_token

        self._token_renewal_running = False

        if access_token and session_token:
            laim_logout(access_token, session_token)

        self.clear_session()
        self.is_logged_in = False
        self.active_menu = "inicio"
        self._load_static_page("inicio")
        self.login_username = ""
        self.login_password = ""
        self.error_message = ""
        self.login_error = ""
        self.login_modal_open = False
        self.register_modal_open = False
        self.register_message = ""

        return rx.redirect("/")

    def check_token_expiration(self) -> dict[str, Any]:
        """Evalúa expiración de tokens JWT."""
        now = int(time.time())
        seconds_until_access = self.access_token_expires_at - now
        seconds_until_session = self.session_token_expires_at - now
        session_expired = seconds_until_session <= 0
        needs_renewal = seconds_until_access < 120
        return {
            "needs_renewal": needs_renewal,
            "session_expired": session_expired,
            "seconds_until_access_expires": seconds_until_access,
            "seconds_until_session_expires": seconds_until_session,
        }

    def ensure_tokens_valid(self) -> bool:
        """Renueva tokens si el access token está próximo a expirar."""
        from laim_web.adapters.laim_api_client import ensure_valid_tokens

        if not self.access_token or not self.session_token:
            return False

        result = ensure_valid_tokens(
            access_token=self.access_token,
            session_token=self.session_token,
            access_expires_at=self.access_token_expires_at,
            session_expires_at=self.session_token_expires_at,
        )

        if result.get("error"):
            self.login_error = result["error"]
            self.error_message = result["error"]
            self.clear_session()
            self.is_logged_in = False
            self.active_menu = "inicio"
            self._load_static_page("inicio")
            self._token_renewal_running = False
            return False

        if result.get("renewed"):
            self.update_tokens(
                access_token=result["access_token"],
                session_token=result["session_token"],
                access_expires_at=result["access_expires_at"],
                session_expires_at=result["session_expires_at"],
            )

        return True

    def _handle_renewal_session_expired(self) -> None:
        """Limpia la sesión cuando expira durante el loop de renovación."""

        self.login_error = (
            "Su sesión ha expirado. Por favor, inicie sesión nuevamente."
        )
        self.error_message = self.login_error
        self.clear_session()
        self.is_logged_in = False
        self.active_menu = "inicio"
        self._load_static_page("inicio")
        self.login_modal_open = True
        self._token_renewal_running = False

    def _run_token_renewal_iteration(self) -> bool:
        """Ejecuta una iteración del loop de renovación.

        Returns:
            False si el loop debe detenerse.
        """
        if (
            not self.is_logged_in
            or not self.access_token
            or not self.session_token
        ):
            self._token_renewal_running = False
            return False

        self._load_tokens_from_redis()
        check_result = self.check_token_expiration()

        if check_result["session_expired"]:
            self._handle_renewal_session_expired()
            return False

        if not check_result["needs_renewal"]:
            return True

        success = self.ensure_tokens_valid()
        if success or not self.login_error:
            return True

        if "expirado" in self.login_error.lower():
            self._token_renewal_running = False
            return False

        self.login_error = ""
        return True

    @rx.event(background=True)
    async def auto_renew_tokens_loop(self) -> None:
        """Renueva tokens en background cada 2 minutos."""
        while True:
            async with self:
                if not self._run_token_renewal_iteration():
                    break

            await asyncio.sleep(120)

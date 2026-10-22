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

from laim_web.laim_config_mixin import LaimConfigMixin
from laim_web.laim_forum_mixin import LaimForumMixin
from laim_web.shared_state import LaimSharedSessionState

EventHandlerReturn = Any

PUBLIC_TICKET_OPERATOR = "Soporte LAIM"


def public_ticket_actor(name: str) -> str:
    """Nombre visible del hilo. laim_maintenance no sale al usuario."""
    raw = str(name or "").strip()
    if raw.lower() == "laim_maintenance":
        return PUBLIC_TICKET_OPERATOR
    return raw

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
  var token = window.__LAIM_CAP_TOKEN__ || (input && input.value) || '';
  return String(token).trim();
})();
"""


class LaimWebState(LaimSharedSessionState, LaimForumMixin, LaimConfigMixin):
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
    sidebar_menu_open: bool = False
    sidebar_forum_open: bool = False
    _auditoria_heartbeat_running: bool = False
    static_page_content: str = ""
    inicio_page_title: str = ""
    inicio_sections: list[dict[str, str]] = []
    inicio_open_titles: list[str] = []
    inicio_view: str = "graphic"
    inicio_modal_open: bool = False
    inicio_modal_title: str = ""
    inicio_modal_body: str = ""
    inicio_modal_glyph: str = ""
    inicio_modal_ctas: list[dict[str, str]] = []

    # Instaladores: modalidad (community_edition/advance) + plataforma elegidas
    installers_edition: str = "community_edition"
    installers_platform: str = ""
    installers_latest: str = ""  # "<version>/<filename>" tal y como lo devuelve el backend
    installers_error: str = ""
    installers_loading: bool = False
    show_advance_construction_modal: bool = False
    base_models_catalog_open: bool = False
    recommended_model_open: bool = False
    compare_requirements_open: bool = False

    # Tickets de soporte (usuario autenticado)
    ticket_create_open: bool = False
    ticket_status_open: bool = False
    ticket_subject: str = ""
    ticket_body: str = ""
    ticket_form_error: str = ""
    ticket_form_success: str = ""
    ticket_submitting: bool = False
    ticket_items: list[dict[str, str | int | bool]] = []
    ticket_list_error: str = ""
    ticket_detail_id: int = 0
    ticket_detail_subject: str = ""
    ticket_detail_estado: str = ""
    ticket_detail_edition: str = ""
    ticket_detail_readonly: bool = False
    ticket_messages: list[dict[str, str]] = []
    ticket_reply_body: str = ""
    ticket_replying: bool = False
    ticket_notif_open: bool = False
    ticket_notif_id: int = 0

    # Registro de instalaciones LAIM
    install_items: list[dict[str, str]] = []
    install_list_error: str = ""
    install_form_open: bool = False
    install_editing: bool = False
    install_edit_id: str = ""
    install_serial: str = ""
    install_serial_valid: bool = False
    install_serial_error: str = ""
    install_hostname: str = ""
    install_display_name: str = ""
    install_os: str = "mac"
    install_edition: str = "community_edition"
    install_notif_open: bool = False
    install_notif_id: int = 0
    install_notif_label: str = ""
    install_form_error: str = ""
    install_form_success: str = ""
    install_saving: bool = False
    install_instructions_open: bool = False
    ticket_notif_ticket_id: int = 0
    ticket_notif_subject: str = ""
    ticket_notif_tipo: str = ""

    # Guía gráfica de escenarios (página pública)
    escenario_id: str = "share_multi"
    escenario_step: int = 0
    escenario_playing: bool = False
    escenario_play_generation: int = 0

    @rx.var
    def escenario_cards(self) -> list[dict[str, Any]]:
        """Tarjetas del selector de escenarios."""
        from laim_web.escenarios_data import list_escenario_cards

        return list_escenario_cards()

    @rx.var
    def escenario_title(self) -> str:
        """Título del escenario activo."""
        from laim_web.escenarios_data import get_escenario

        return str(get_escenario(self.escenario_id)["title"])

    @rx.var
    def escenario_summary(self) -> str:
        """Resumen del escenario activo."""
        from laim_web.escenarios_data import get_escenario

        return str(get_escenario(self.escenario_id)["summary"])

    @rx.var
    def escenario_command(self) -> str:
        """Comandos asociados al escenario activo."""
        from laim_web.escenarios_data import get_escenario

        return str(get_escenario(self.escenario_id)["command"])

    @rx.var
    def escenario_step_label(self) -> str:
        """Indicador de fase actual."""
        from laim_web.escenarios_data import build_escenario_view

        return str(build_escenario_view(self.escenario_id, self.escenario_step)["step_label"])

    @rx.var
    def escenario_caption(self) -> str:
        """Texto de la fase en reproducción."""
        from laim_web.escenarios_data import build_escenario_view

        return str(build_escenario_view(self.escenario_id, self.escenario_step)["caption"])

    @rx.var
    def escenario_gpu(self) -> str:
        """Nivel de carga GPU de la fase (idle/infer/queue/hot)."""
        from laim_web.escenarios_data import build_escenario_view

        return str(build_escenario_view(self.escenario_id, self.escenario_step)["gpu"])

    @rx.var
    def escenario_lit_csv(self) -> str:
        """Nodos iluminados en la fase, delimitados por |."""
        from laim_web.escenarios_data import build_escenario_view

        return str(build_escenario_view(self.escenario_id, self.escenario_step)["lit_csv"])

    @rx.var
    def escenario_active_csv(self) -> str:
        """Cables activos en la fase, delimitados por |."""
        from laim_web.escenarios_data import build_escenario_view

        return str(build_escenario_view(self.escenario_id, self.escenario_step)["active_csv"])

    @rx.var
    def escenario_packet_visible(self) -> bool:
        """Si hay paquete de tráfico en esta fase."""
        from laim_web.escenarios_data import build_escenario_view

        return bool(build_escenario_view(self.escenario_id, self.escenario_step)["packet_visible"])

    @rx.var
    def escenario_packet_x(self) -> str:
        """Posición horizontal del paquete."""
        from laim_web.escenarios_data import build_escenario_view

        return str(build_escenario_view(self.escenario_id, self.escenario_step)["packet_x"])

    @rx.var
    def escenario_packet_y(self) -> str:
        """Posición vertical del paquete."""
        from laim_web.escenarios_data import build_escenario_view

        return str(build_escenario_view(self.escenario_id, self.escenario_step)["packet_y"])

    @rx.var
    def escenario_packet_label(self) -> str:
        """Etiqueta del paquete (SUBMIT, CLAIM, TOKENS, SSH…)."""
        from laim_web.escenarios_data import build_escenario_view

        return str(build_escenario_view(self.escenario_id, self.escenario_step)["packet_label"])

    @rx.var
    def escenario_traffic_payload(self) -> str:
        """JSON de paquetes para el motor SVG (mismo patrón que el Network Monitor)."""
        import json

        from laim_web.escenarios_data import build_escenario_view, caption_step_seconds

        view = build_escenario_view(self.escenario_id, self.escenario_step)
        return json.dumps(
            {
                "gen": (
                    f"{view['id']}:{self.escenario_step}:{self.escenario_play_generation}:"
                    f"{view['packet_edge']}:{view['packet_label']}"
                ),
                "step_s": round(caption_step_seconds(str(view["caption"])), 2),
                "packets": view["traffic"],
            },
            separators=(",", ":"),
        )

    @rx.var
    def escenario_caption_dur(self) -> str:
        """Duración CSS del fundido del pie de fase."""
        from laim_web.escenarios_data import build_escenario_view, caption_step_seconds

        caption = str(build_escenario_view(self.escenario_id, self.escenario_step)["caption"])
        return f"{caption_step_seconds(caption):.2f}s"

    @rx.var
    def escenario_caption_live(self) -> bool:
        """True mientras la reproducción automática está activa."""
        return bool(self.escenario_playing)

    @rx.var
    def escenario_caption_tick(self) -> bool:
        """Alterna la clase CSS para reiniciar el fundido en cada fase."""
        return ((self.escenario_step + self.escenario_play_generation) % 2) == 0

    @rx.var
    def escenario_show_queue(self) -> bool:
        """Si el escenario usa el gestor de colas GPU del Share."""
        from laim_web.escenarios_data import build_escenario_view

        return bool(build_escenario_view(self.escenario_id, self.escenario_step)["show_queue"])

    @rx.var
    def escenario_queue_slots(self) -> str:
        """Slots Ollama ocupados / totales en esta fase."""
        from laim_web.escenarios_data import build_escenario_view

        return str(build_escenario_view(self.escenario_id, self.escenario_step)["queue_slots"])

    @rx.var
    def escenario_queue_note(self) -> str:
        """Nota del claim / prioridad de la fase."""
        from laim_web.escenarios_data import build_escenario_view

        return str(build_escenario_view(self.escenario_id, self.escenario_step)["queue_note"])

    @rx.var
    def escenario_queue_jobs(self) -> list[dict[str, str]]:
        """Jobs de la cola GPU visibles en el panel."""
        from laim_web.escenarios_data import build_escenario_view

        jobs = build_escenario_view(self.escenario_id, self.escenario_step)["queue_jobs"]
        return [dict(job) for job in jobs] if isinstance(jobs, list) else []

    @rx.var
    def escenario_queue_empty(self) -> bool:
        """Si la cola GPU de esta fase no tiene jobs."""
        from laim_web.escenarios_data import build_escenario_view

        jobs = build_escenario_view(self.escenario_id, self.escenario_step)["queue_jobs"]
        return not isinstance(jobs, list) or len(jobs) == 0

    @rx.var
    def presentacion_hero_url(self) -> str:
        """URL del asset hero de Presentación (backend con fallback local)."""
        from laim_web.adapters.laim_api_client import get_laim_site_asset_url

        return get_laim_site_asset_url("presentacion-hero")

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

    # Recuperación de contraseña
    forgot_modal_open: bool = False
    forgot_email: str = ""
    forgot_message: str = ""
    forgot_submitting: bool = False
    forgot_public_origin: str = ""
    reset_page_status: str = "loading"
    reset_token: str = ""
    reset_password: str = ""
    reset_password_confirm: str = ""
    reset_error: str = ""
    reset_submitting: bool = False

    # Formulario de contacto
    contact_usage_mode: str = "local"
    contact_affected_user: str = ""
    contact_message_body: str = ""
    contact_reply_email: str = ""
    contact_form_error: str = ""
    contact_form_success: bool = False
    contact_success_message: str = ""
    contact_case_number: int = 0
    contact_submitting: bool = False
    contact_screenshot_preview_url: str = ""
    contact_screenshot_name: str = ""
    contact_preview_open: bool = False
    contact_modal_open: bool = False
    contact_thanks_open: bool = False
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
                "Debe completar la verificación anti-bot antes de registrarse."
            )
            return None

        self.reg_hcaptcha_token = resolved_token
        return LaimWebState.complete_register_background

    @rx.event(background=True)
    async def complete_register_background(self) -> EventHandlerReturn:
        """Ejecuta el registro en segundo plano para no bloquear la UI."""
        from laim_web.adapters.laim_api_client import laim_login, laim_register
        from laim_web.components.hcaptcha import is_hcaptcha_configured

        async with self:
            validation_error = self._validate_register_form()
            if validation_error:
                self.error_message = validation_error
                return

            if is_hcaptcha_configured() and not self.reg_hcaptcha_token.strip():
                self.error_message = (
                    "Debe completar la verificación anti-bot antes de registrarse."
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

        auto_login_started = False
        async with self:
            try:
                if result.get("success"):
                    login_result = laim_login(username, password)
                    if self._apply_laim_login_success(
                        login_result,
                        user_email_fallback=email,
                    ):
                        self.reg_username = ""
                        self.reg_password = ""
                        self.reg_password_confirm = ""
                        self.reg_email = ""
                        self.reg_full_name = ""
                        self.reg_mobile = ""
                        self.reg_hcaptcha_token = ""
                        auto_login_started = True
                    else:
                        self.register_message = result.get(
                            "message",
                            "Registro completado. Ya puede iniciar sesión.",
                        )
                        self.register_modal_open = False
                        self.login_modal_open = True
                        self.login_username = username
                        self.login_password = password
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

        if auto_login_started:
            yield LaimWebState.auto_renew_tokens_loop

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
    def open_forgot_modal(self) -> None:
        """Abre el modal de recuperación."""
        self.forgot_modal_open = True
        self.login_modal_open = False
        self.register_modal_open = False
        self.error_message = ""
        self.forgot_message = ""

    @event
    def close_forgot_modal(self) -> None:
        """Cierra el modal de recuperación."""
        self.forgot_modal_open = False
        self.error_message = ""
        self.forgot_submitting = False

    @event
    def switch_to_forgot_modal(self) -> None:
        """Cierra login y abre recuperación."""
        self.login_modal_open = False
        self.register_modal_open = False
        self.forgot_modal_open = True
        self.error_message = ""
        self.forgot_message = ""

    @event
    def set_forgot_email(self, value: str) -> None:
        self.forgot_email = value

    @event
    def handle_forgot_password(self) -> EventHandlerReturn:
        """Lee el origen público y envía la solicitud."""
        if not self.forgot_email.strip() or "@" not in self.forgot_email:
            self.error_message = "El email es obligatorio."
            return None
        self.error_message = ""
        return rx.call_script(
            "window.location.origin",
            callback=LaimWebState.forgot_with_origin,
        )

    @event
    def forgot_with_origin(self, origin: str | None) -> EventHandlerReturn:
        """Continúa el envío con la URL absoluta del entorno."""
        self.forgot_public_origin = (origin or "").strip().rstrip("/")
        return LaimWebState.complete_forgot_background

    def apply_forgot_prepare_and_send(
        self,
        prepare: dict[str, Any],
        public_origin: str,
        *,
        send_mail,
        build_email,
        build_url,
    ) -> None:
        """Anti-enumeración: mensaje genérico; el correo solo si hay token."""
        from laim_web.password_reset_mail import RESET_ACCEPTED_MSG

        self.forgot_message = RESET_ACCEPTED_MSG
        self.error_message = ""
        if not prepare.get("found") or not prepare.get("token"):
            return
        reset_url = build_url(public_origin, str(prepare["token"]))
        subject, body = build_email(str(prepare.get("user_name") or ""), reset_url)
        try:
            send_mail(self.forgot_email.strip(), subject, body)
        except Exception:
            return

    @rx.event(background=True)
    async def complete_forgot_background(self) -> None:
        """Solicita token y, si existe usuario, envía el correo Workspace."""
        from laim_web.adapters.laim_api_client import (
            laim_mail_send,
            laim_password_reset_request,
        )
        from laim_web.password_reset_mail import (
            RESET_ACCEPTED_MSG,
            build_reset_email,
            build_reset_url,
        )

        async with self:
            email = self.forgot_email.strip()
            origin = self.forgot_public_origin
            self.forgot_submitting = True
            self.error_message = ""
            self.forgot_message = ""

        try:
            prepare = laim_password_reset_request(email, origin)
        except Exception:
            prepare = {"accepted": True, "found": False}

        async with self:
            self.forgot_email = email
            self.apply_forgot_prepare_and_send(
                prepare,
                origin,
                send_mail=laim_mail_send,
                build_email=build_reset_email,
                build_url=build_reset_url,
            )
            if not self.forgot_message:
                self.forgot_message = RESET_ACCEPTED_MSG
            self.forgot_submitting = False

    @event
    def set_reset_password(self, value: str) -> None:
        self.reset_password = value

    @event
    def set_reset_password_confirm(self, value: str) -> None:
        self.reset_password_confirm = value

    def apply_reset_status(self, token: str, status: dict[str, Any]) -> None:
        """Página muerta si falta, caducó o ya se usó el token."""
        self.reset_token = (token or "").strip()
        self.reset_password = ""
        self.reset_password_confirm = ""
        self.reset_error = ""
        if self.reset_token and status.get("valid"):
            self.reset_page_status = "form"
            return
        self.reset_page_status = "dead"

    @event
    def load_password_reset_page(self) -> None:
        """GET del token: formulario o página muerta (410 semántico)."""
        from laim_web.adapters.laim_api_client import laim_password_reset_status

        token = ""
        try:
            token = str(self.router.page.params.get("token") or "").strip()
        except Exception:
            token = ""
        if not token:
            self.apply_reset_status("", {"valid": False, "reason": "missing"})
            return
        self.apply_reset_status(token, laim_password_reset_status(token))

    @event
    def handle_reset_confirm(self) -> EventHandlerReturn:
        """Valida las dos claves y actualiza."""
        if not self.reset_password or self.reset_password != self.reset_password_confirm:
            self.reset_error = "Las contraseñas no coinciden."
            return None
        if len(self.reset_password) < 8:
            self.reset_error = "La contraseña debe tener al menos 8 caracteres."
            return None
        self.reset_error = ""
        return LaimWebState.complete_reset_confirm_background

    @rx.event(background=True)
    async def complete_reset_confirm_background(self) -> None:
        """Confirma en core y deja el token inválido."""
        from laim_web.adapters.laim_api_client import laim_password_reset_confirm
        from laim_web.password_reset_mail import RESET_DEAD_MSG

        async with self:
            token = self.reset_token
            password = self.reset_password
            confirm = self.reset_password_confirm
            self.reset_submitting = True
            self.reset_error = ""

        try:
            result = laim_password_reset_confirm(token, password, confirm)
        except Exception as exc:
            result = {"success": False, "error": str(exc)}

        async with self:
            if result.get("success"):
                self.reset_page_status = "done"
                self.reset_error = ""
                self.reset_password = ""
                self.reset_password_confirm = ""
            else:
                detail = str(result.get("error") or RESET_DEAD_MSG)
                if "caduc" in detail.lower() or "válido" in detail.lower():
                    self.reset_page_status = "dead"
                else:
                    self.reset_error = detail
            self.reset_submitting = False

    @event
    def set_login_username(self, value: str) -> None:
        self.login_username = value

    @event
    def set_login_password(self, value: str) -> None:
        self.login_password = value

    def _sync_menu_for_session(self) -> None:
        """Alinea menú y contenido con el estado de sesión actual."""
        from laim_web.help_manuals import HELP_MANUAL_PAGE_MENUS
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
            elif (
                self.active_menu not in AUTHENTICATED_PAGE_MENUS
                and self.active_menu not in HELP_MANUAL_PAGE_MENUS
            ):
                if self.active_menu not in PUBLIC_MENU_FILES:
                    self.active_menu = "instaladores"
        elif self.active_menu not in PUBLIC_MENU_FILES:
            self.active_menu = "inicio"

        self._load_static_page(self.active_menu)

    @rx.event
    def on_page_load(self) -> EventHandlerReturn:
        """Carga inicial de la página."""
        self._sync_menu_for_session()
        events: list[Any] = []
        if self.is_logged_in:
            self._record_auditoria_seccion(self.active_menu)
        if self.is_logged_in and self.session_token and not self._token_renewal_running:
            self._token_renewal_running = True
            events.append(LaimWebState.auto_renew_tokens_loop)
        if self.is_logged_in and not self._auditoria_heartbeat_running:
            self._auditoria_heartbeat_running = True
            events.append(LaimWebState.auditoria_heartbeat_loop)
        if not events:
            return None
        if len(events) == 1:
            return events[0]
        return events

    def _hydrate_inicio_sections(self) -> None:
        """Parte Inicio en secciones ## contraídas por defecto."""
        from laim_web.static_pages_loader import split_markdown_h2_sections

        page_title, _preamble, sections = split_markdown_h2_sections(
            self.static_page_content
        )
        self.inicio_page_title = page_title
        self.inicio_sections = sections
        self.inicio_open_titles = []

    @rx.var
    def inicio_bento_tiles(self) -> list[dict[str, str]]:
        """Secciones de Inicio con span, glifo y clase Bento."""
        from laim_web.components.bento.catalog import decorate_sections

        return decorate_sections(self.inicio_sections)

    @rx.var
    def inicio_grid_paused(self) -> str:
        """Pausa el pulso neuronal mientras el modal está abierto."""
        return "true" if self.inicio_modal_open else "false"

    @event
    def set_inicio_view(self, view: str) -> None:
        """Cambia gráfico/clásico solo durante la sesión."""
        if view not in {"graphic", "classic"}:
            return
        self.inicio_view = view
        if view == "classic":
            self.inicio_modal_open = False

    @event
    def open_inicio_section_modal(self, title: str) -> None:
        """Abre el markdown de una sección en overlay."""
        from laim_web.components.bento.catalog import glyph_for, modal_cta_items

        for section in self.inicio_sections:
            if section.get("title") == title:
                self.inicio_modal_title = title
                self.inicio_modal_body = section.get("body", "")
                self.inicio_modal_glyph = glyph_for(title)
                self.inicio_modal_ctas = modal_cta_items(self.inicio_modal_body)
                self.inicio_modal_open = True
                return

    @event
    def close_inicio_section_modal(self) -> None:
        """Cierra el modal y reanuda el pulso neuronal."""
        self.inicio_modal_open = False

    @event
    def inicio_modal_go_menu(self, item: str) -> None:
        """Desde el modal, salta a otra página del portal."""
        self.inicio_modal_open = False
        self.set_menu(item)

    def _load_static_page(self, menu: str) -> None:
        """Carga markdown de static_pages/ para menús públicos."""
        from laim_web.help_manuals import HELP_MANUAL_PAGE_MENUS
        from laim_web.static_pages_loader import STATIC_PAGE_MENUS, load_static_page_markdown

        if menu in HELP_MANUAL_PAGE_MENUS:
            # El visor lee el fichero al montar; no meter 300 KB en Redis.
            self.static_page_content = ""
            return
        if menu in STATIC_PAGE_MENUS:
            self.static_page_content = load_static_page_markdown(menu)
            if menu == "inicio":
                self._hydrate_inicio_sections()

    @event
    def toggle_inicio_section(self, title: str) -> None:
        """Abre o cierra una sección de Inicio."""
        if title in self.inicio_open_titles:
            self.inicio_open_titles = [
                item for item in self.inicio_open_titles if item != title
            ]
            return
        self.inicio_open_titles = [*self.inicio_open_titles, title]

    @event
    def expand_inicio_sections(self) -> None:
        """Abre todas las secciones de Inicio."""
        self.inicio_open_titles = [section["title"] for section in self.inicio_sections]

    @event
    def collapse_inicio_sections(self) -> None:
        """Cierra todas las secciones de Inicio."""
        self.inicio_open_titles = []

    @rx.var
    def sidebar_active_menu(self) -> str:
        """Los documentos de Ayuda resaltan la entrada Manuales del menú."""
        from laim_web.help_manuals import is_help_manual_menu

        if is_help_manual_menu(self.active_menu):
            return "manuales"
        return self.active_menu

    @event
    def toggle_sidebar_menu(self) -> None:
        """Expande o contrae el bloque Menú del sidebar."""
        self.sidebar_menu_open = not self.sidebar_menu_open

    @event
    def toggle_sidebar_forum(self) -> None:
        """Expande o contrae el bloque Foro del sidebar."""
        self.sidebar_forum_open = not self.sidebar_forum_open

    @event
    def set_menu(self, item: str) -> EventHandlerReturn:
        from laim_web.static_pages_loader import can_access_admin_config_menu

        if not can_access_admin_config_menu(item, self.identity_type_id):
            return

        self.active_menu = item
        self._load_static_page(item)
        self._record_auditoria_seccion(item)
        if item == "contacto":
            self._prepare_contact_form()
        else:
            self.contact_modal_open = False
            self.contact_preview_open = False
            self.contact_thanks_open = False
        if item == "escenarios":
            self.escenario_playing = False
        if item == "registro":
            return LaimWebState.load_installations

    def _auditoria_seccion_name(self, item: str) -> str:
        from laim_web.dynamic_import import load_module_from_path
        from pathlib import Path

        domain = load_module_from_path(
            Path(__file__).resolve().parents[3]
            / "2_shared_application"
            / "domain"
            / "laim_auditoria.py",
            "laim_auditoria_domain_web",
        )
        return domain.seccion_from_menu(item)

    def _record_auditoria_seccion(self, item: str) -> None:
        if not self.is_logged_in or not self.access_token or not self.session_token:
            return
        try:
            from laim_web.adapters.laim_api_client import laim_auditoria_seccion

            laim_auditoria_seccion(
                self._auditoria_seccion_name(item),
                self.access_token,
                self.session_token,
            )
        except Exception:
            pass

    @event
    def auditoria_heartbeat_tick(self) -> EventHandlerReturn:
        if not self.is_logged_in:
            return None
        return rx.call_script(
            "document.visibilityState || 'visible'",
            callback=LaimWebState.auditoria_heartbeat_visible,
        )

    @event
    def auditoria_heartbeat_visible(self, state: str) -> None:
        if str(state) != "visible" or not self.is_logged_in:
            return
        try:
            from laim_web.adapters.laim_api_client import laim_auditoria_heartbeat

            laim_auditoria_heartbeat(
                self.access_token,
                self.session_token,
                self._auditoria_seccion_name(self.active_menu),
            )
        except Exception:
            pass

    @rx.event(background=True)
    async def auditoria_heartbeat_loop(self) -> EventHandlerReturn:
        while True:
            await asyncio.sleep(30)
            async with self:
                if not self.is_logged_in:
                    self._auditoria_heartbeat_running = False
                    return
            yield LaimWebState.auditoria_heartbeat_tick

    def _escenario_clamp_step(self) -> None:
        """Mantiene el índice de fase dentro del escenario activo."""
        from laim_web.escenarios_data import escenario_step_count

        last_index = escenario_step_count(self.escenario_id) - 1
        if self.escenario_step < 0:
            self.escenario_step = 0
        elif self.escenario_step > last_index:
            self.escenario_step = last_index

    @event
    def escenario_select(self, escenario_id: str) -> EventHandlerReturn:
        """Elegir un caso reproduce el flujo entero y se detiene en la fase 1."""
        self.escenario_id = escenario_id
        self.escenario_step = 0
        return self._start_escenario_playback()

    @event
    def escenario_pause(self) -> None:
        """Detiene la reproducción automática."""
        self.escenario_playing = False
        self.escenario_play_generation += 1

    def _start_escenario_playback(self) -> EventHandlerReturn:
        """Arranca (o reinicia) el bucle de fases."""
        self.escenario_playing = True
        self.escenario_play_generation += 1
        return LaimWebState.escenario_play_loop

    @event
    def escenario_restart(self) -> EventHandlerReturn:
        """Vuelve a la fase 1 y vuelve a reproducir el flujo entero."""
        self.escenario_step = 0
        return self._start_escenario_playback()

    @event
    def escenario_prev_step(self) -> None:
        """Retrocede una fase (modo manual)."""
        self.escenario_playing = False
        self.escenario_play_generation += 1
        self.escenario_step -= 1
        self._escenario_clamp_step()

    @event
    def escenario_next_step(self) -> None:
        """Avanza una fase (modo manual)."""
        self.escenario_playing = False
        self.escenario_play_generation += 1
        self.escenario_step += 1
        self._escenario_clamp_step()

    @event
    def escenario_play(self) -> EventHandlerReturn:
        """Continúa desde la siguiente fase y recorre el ciclo hasta la fase 1."""
        from laim_web.escenarios_data import escenario_step_count

        last_index = escenario_step_count(self.escenario_id) - 1
        if last_index <= 0:
            return self._start_escenario_playback()
        if self.escenario_step == 0:
            self.escenario_step = 1
        elif self.escenario_step >= last_index:
            self.escenario_step = 0
        return self._start_escenario_playback()

    @rx.event(background=True)
    async def escenario_play_loop(self) -> None:
        """Avanza fases con tiempo de lectura; al terminar vuelve a la fase 1."""
        from laim_web.escenarios_data import (
            build_escenario_view,
            caption_step_seconds,
            escenario_step_count,
        )

        async with self:
            generation = self.escenario_play_generation
            escenario_id = self.escenario_id

        while True:
            async with self:
                caption = str(
                    build_escenario_view(self.escenario_id, self.escenario_step)["caption"]
                )
                delay = caption_step_seconds(caption)
            await asyncio.sleep(delay)
            stop = False
            async with self:
                if not self.escenario_playing or self.escenario_play_generation != generation:
                    return
                if self.escenario_id != escenario_id:
                    return
                last_index = escenario_step_count(self.escenario_id) - 1
                if self.escenario_step >= last_index:
                    self.escenario_step = 0
                    self.escenario_playing = False
                    stop = True
                else:
                    self.escenario_step += 1
            yield
            if stop:
                return

    def _prepare_contact_form(self) -> None:
        """Pre-rellena el formulario de contacto al abrir la página."""
        if self.is_logged_in and self.user_email.strip() and not self.contact_reply_email.strip():
            self.contact_reply_email = self.user_email.strip()
        if self.is_logged_in and self.user_name.strip() and not self.contact_affected_user.strip():
            self.contact_affected_user = self.user_name.strip()
        self.contact_form_error = ""
        self.contact_form_success = False
        self.contact_success_message = ""
        self.contact_case_number = 0
        self.contact_preview_open = False
        self.contact_thanks_open = False

    @event
    def open_contact_modal(self) -> None:
        """Abre el modal de contacto con el formulario pre-rellenado."""
        self._prepare_contact_form()
        self.contact_thanks_open = False
        self.contact_modal_open = True

    @event
    def close_contact_modal(self) -> None:
        """Cierra el modal de contacto y el visor de captura."""
        self.contact_modal_open = False
        self.contact_preview_open = False

    @event
    def contact_thanks_back(self) -> None:
        """Cierra el aviso de envío y deja visible la página de Contacto."""
        self.contact_thanks_open = False
        self.contact_modal_open = False
        self.contact_preview_open = False
        self.contact_form_success = False
        self.contact_success_message = ""
        self.active_menu = "contacto"
        self._load_static_page("contacto")

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

    _CONTACT_PREVIEW_SCRIPT = """
(() => {
  const input = document.getElementById('laim_contact_screenshot');
  if (!input || !input.files || input.files.length === 0) {
    return { data_url: '', file_name: '', mime_type: '' };
  }
  const file = input.files[0];
  const mime = (file.type || '').toLowerCase();
  const name = file.name || '';
  const ok = mime === 'image/jpeg' || mime === 'image/jpg' || mime === 'image/png'
    || /\\.(jpe?g|png)$/i.test(name);
  if (!ok) {
    return { data_url: '', file_name: '', mime_type: '', error: 'Solo PNG o JPG.' };
  }
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      resolve({
        data_url: typeof reader.result === 'string' ? reader.result : '',
        file_name: name,
        mime_type: mime || (name.toLowerCase().endsWith('.png') ? 'image/png' : 'image/jpeg'),
      });
    };
    reader.onerror = () => resolve({ data_url: '', file_name: '', mime_type: '' });
    reader.readAsDataURL(file);
  });
})()
"""

    @event
    def contact_read_screenshot_preview(self, _value: str = "") -> EventHandlerReturn:
        """Lee la captura elegida y alimenta el visor JPG/PNG."""
        return rx.call_script(
            self._CONTACT_PREVIEW_SCRIPT,
            callback=LaimWebState.contact_set_screenshot_preview,
        )

    @event
    def contact_set_screenshot_preview(self, payload: dict[str, object] | None) -> None:
        """Guarda la data URL del visor o lo vacía si no hay imagen válida."""
        if not isinstance(payload, dict):
            self.contact_screenshot_preview_url = ""
            self.contact_screenshot_name = ""
            self.contact_preview_open = False
            return
        error = str(payload.get("error") or "").strip()
        data_url = str(payload.get("data_url") or "").strip()
        if error:
            self.contact_form_error = error
        if not data_url.startswith("data:image/"):
            self.contact_screenshot_preview_url = ""
            self.contact_screenshot_name = ""
            self.contact_preview_open = False
            return
        self.contact_screenshot_preview_url = data_url
        self.contact_screenshot_name = str(payload.get("file_name") or "").strip()
        if self.contact_form_error == "Solo PNG o JPG.":
            self.contact_form_error = ""

    @event
    def contact_open_preview(self) -> None:
        if self.contact_screenshot_preview_url:
            self.contact_preview_open = True

    @event
    def contact_close_preview(self) -> None:
        self.contact_preview_open = False

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
        self.contact_success_message = ""
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
                numero_caso = int(result.get("numero_caso") or result.get("message_id") or 0)
                self.contact_form_success = True
                self.contact_case_number = numero_caso
                self.contact_success_message = ""
                self.contact_modal_open = False
                self.contact_thanks_open = True
                self.contact_affected_user = (
                    self.user_name.strip() if self.is_logged_in else ""
                )
                self.contact_message_body = ""
                self.contact_screenshot_preview_url = ""
                self.contact_screenshot_name = ""
                self.contact_preview_open = False
                if not self.is_logged_in:
                    self.contact_reply_email = ""
                return

            self.contact_form_error = result.get(
                "error", "No se pudo enviar el mensaje. Inténtelo más tarde."
            )


    @rx.var
    def ticket_edition_label(self) -> str:
        """Edición mostrada en el alta (snapshot community_edition en v1)."""
        return "community edition"

    @event
    def set_ticket_subject(self, value: str) -> None:
        self.ticket_subject = value

    @event
    def set_ticket_body(self, value: str) -> None:
        self.ticket_body = value

    @event
    def set_ticket_reply_body(self, value: str) -> None:
        self.ticket_reply_body = value

    @event
    def close_ticket_create(self) -> None:
        self.ticket_create_open = False

    @event
    def close_ticket_status(self) -> None:
        self.ticket_status_open = False

    @event
    def open_ticket_create(self) -> None:
        self.ticket_create_open = True
        self.ticket_form_error = ""
        self.ticket_form_success = ""
        self.ticket_subject = ""
        self.ticket_body = ""

    @rx.event(background=True)
    async def open_ticket_status(self) -> None:
        from laim_web.adapters.laim_api_client import laim_list_my_tickets

        async with self:
            self.ticket_status_open = True
            self.ticket_list_error = ""
            self.ticket_detail_id = 0
            access_token = self.access_token
            session_token = self.session_token
        result = laim_list_my_tickets(access_token=access_token, session_token=session_token)
        async with self:
            if not result.get("success"):
                self.ticket_list_error = result.get("error", "No se pudieron cargar los tickets.")
                self.ticket_items = []
                return
            items = []
            for raw in result.get("items") or []:
                items.append(
                    {
                        "id": int(raw.get("id") or 0),
                        "subject": str(raw.get("subject") or ""),
                        "estado_nombre": str(raw.get("estado_nombre") or raw.get("estado_clave") or ""),
                        "opened_at": str(raw.get("opened_at") or ""),
                    }
                )
            self.ticket_items = items

    @rx.event(background=True)
    async def submit_ticket(self) -> None:
        from laim_web.adapters.laim_api_client import laim_create_ticket

        async with self:
            subject = self.ticket_subject.strip()
            body = self.ticket_body.strip()
            if len(subject) < 5 or len(body) < 10:
                self.ticket_form_error = "Escriba un asunto (5+) y una descripción (10+)."
                return
            self.ticket_submitting = True
            self.ticket_form_error = ""
            access_token = self.access_token
            session_token = self.session_token
        result = laim_create_ticket(
            {"subject": subject, "body": body},
            access_token=access_token,
            session_token=session_token,
        )
        async with self:
            self.ticket_submitting = False
            if result.get("success"):
                ticket = result.get("ticket") or {}
                numero = int(ticket.get("id") or 0)
                self.ticket_form_success = f"Ticket #{numero} creado." if numero else "Ticket creado."
                self.ticket_subject = ""
                self.ticket_body = ""
                return
            self.ticket_form_error = result.get("error", "No se pudo crear el ticket.")

    @rx.event(background=True)
    async def open_ticket_detail(self, ticket_id: int) -> None:
        from laim_web.adapters.laim_api_client import laim_get_my_ticket

        async with self:
            access_token = self.access_token
            session_token = self.session_token
        result = laim_get_my_ticket(int(ticket_id), access_token=access_token, session_token=session_token)
        async with self:
            if not result.get("success"):
                self.ticket_list_error = result.get("error", "No se pudo abrir el ticket.")
                return
            ticket = result.get("ticket") or {}
            self.ticket_detail_id = int(ticket.get("id") or 0)
            self.ticket_detail_subject = str(ticket.get("subject") or "")
            self.ticket_detail_estado = str(ticket.get("estado_nombre") or ticket.get("estado_clave") or "")
            self.ticket_detail_edition = str(ticket.get("edition") or "community_edition")
            self.ticket_detail_readonly = bool(ticket.get("readonly"))
            self.ticket_reply_body = ""
            if self.ticket_notif_ticket_id == int(ticket.get("id") or 0):
                self.ticket_notif_open = False
                self.ticket_notif_id = 0
            messages = []
            for raw in result.get("messages") or []:
                messages.append(
                    {
                        "actor_name": public_ticket_actor(
                            str(raw.get("actor_name") or raw.get("autor") or "")
                        ),
                        "created_at": str(raw.get("created_at") or ""),
                        "cuerpo": str(raw.get("cuerpo") or ""),
                    }
                )
            self.ticket_messages = messages

    @rx.event(background=True)
    async def submit_ticket_reply(self) -> None:
        from laim_web.adapters.laim_api_client import laim_reply_my_ticket

        async with self:
            ticket_id = self.ticket_detail_id
            body = self.ticket_reply_body.strip()
            if ticket_id <= 0 or not body:
                return
            self.ticket_replying = True
            access_token = self.access_token
            session_token = self.session_token
        result = laim_reply_my_ticket(
            ticket_id, body, access_token=access_token, session_token=session_token
        )
        async with self:
            self.ticket_replying = False
            if not result.get("success"):
                self.ticket_list_error = result.get("error", "No se pudo responder.")
                return
            self.ticket_reply_body = ""
        yield LaimWebState.open_ticket_detail(ticket_id)

    @rx.event(background=True)
    async def poll_ticket_notifications(self) -> None:
        """Carga pendientes. No hace ack: el poll no marca leída."""
        from laim_web.adapters.laim_api_client import laim_ticket_notifications_pending

        async with self:
            if not self.is_logged_in or self.ticket_notif_open:
                return
            access_token = self.access_token
            session_token = self.session_token
        result = laim_ticket_notifications_pending(
            access_token=access_token, session_token=session_token
        )
        async with self:
            if not result.get("success"):
                return
            items = result.get("items") or []
            if not items:
                return
            first = items[0]
            self.ticket_notif_id = int(first.get("id") or 0)
            self.ticket_notif_ticket_id = int(first.get("ticket_id") or 0)
            self.ticket_notif_subject = str(first.get("subject") or "")
            self.ticket_notif_tipo = str(first.get("tipo") or "")
            self.ticket_notif_open = True

    @rx.event(background=True)
    async def ack_ticket_notification(self, open_ticket: bool = False) -> None:
        """Ack explícito al cerrar o al abrir el ticket avisado."""
        from laim_web.adapters.laim_api_client import laim_ack_ticket_notification

        async with self:
            notif_id = self.ticket_notif_id
            ticket_id = self.ticket_notif_ticket_id
            access_token = self.access_token
            session_token = self.session_token
            self.ticket_notif_open = False
            self.ticket_notif_id = 0
        if notif_id > 0:
            laim_ack_ticket_notification(
                notif_id, access_token=access_token, session_token=session_token
            )
        if open_ticket and ticket_id > 0:
            async with self:
                self.active_menu = "soporte"
                self._load_static_page("soporte")
                self.ticket_status_open = True
            yield LaimWebState.open_ticket_detail(ticket_id)

    @rx.event(background=True)
    async def poll_install_notifications(self) -> None:
        """Carga propuestas pendientes. El poll no hace ack."""
        from laim_web.adapters.laim_api_client import laim_install_notifications_pending

        async with self:
            if not self.is_logged_in or self.install_notif_open:
                return
            access_token = self.access_token
            session_token = self.session_token
        result = laim_install_notifications_pending(
            access_token=access_token, session_token=session_token
        )
        async with self:
            if not result.get("success"):
                return
            items = result.get("items") or []
            if not items:
                return
            first = items[0]
            alias = str(first.get("display_name") or "").strip()
            host = str(first.get("hostname") or "")
            self.install_notif_id = int(first.get("id") or 0)
            self.install_notif_label = alias or host
            self.install_notif_open = True

    @rx.event(background=True)
    async def ack_install_notification(self, open_registro: bool = False) -> None:
        """Ack explícito al cerrar o al ir a Registro."""
        from laim_web.adapters.laim_api_client import laim_ack_install_notification

        async with self:
            notif_id = self.install_notif_id
            access_token = self.access_token
            session_token = self.session_token
            self.install_notif_open = False
            self.install_notif_id = 0
            self.install_notif_label = ""
        if notif_id > 0:
            laim_ack_install_notification(
                notif_id, access_token=access_token, session_token=session_token
            )
        if open_registro:
            async with self:
                self.active_menu = "registro"
                self._load_static_page("registro")
            yield LaimWebState.load_installations


    @event
    def handle_page_action(self, action_key: str) -> EventHandlerReturn:
        """Ejecuta acciones de botones bajo el contenido markdown."""
        if action_key == "support_ticket":
            return LaimWebState.open_ticket_create
        if action_key == "support_status":
            return LaimWebState.open_ticket_status
        if action_key == "support_email":
            self.active_menu = "contacto"
            self._load_static_page("contacto")
            return None
        if action_key == "go_installers":
            if self.is_logged_in:
                self.active_menu = "instaladores"
                self._load_static_page("instaladores")
                return None
            self.login_modal_open = True
            return None

        from laim_web.help_manuals import BACK_TO_MANUALES_ACTION, menu_for_action

        if action_key == BACK_TO_MANUALES_ACTION:
            self.active_menu = "manuales"
            self._load_static_page("manuales")
            return None

        help_menu = menu_for_action(action_key)
        if help_menu is not None:
            self.active_menu = help_menu
            self._load_static_page(help_menu)
            return None

        navigate_to_menu = {
            "faq_to_support": "soporte",
            "faq_privacy": "faq",
            "faq_security": "manuales",
            "go_documentacion": "documentacion",
            "manual_user": "manuales",
            "custom_howto": "modelos_personalizados",
        }
        if action_key in navigate_to_menu:
            target = navigate_to_menu[action_key]
            self.active_menu = target
            self._load_static_page(target)
            return None

        if action_key == "catalog_base_models":
            self.base_models_catalog_open = True
            return None

        if action_key == "recommended_model":
            self.recommended_model_open = True
            return None

        if action_key == "compare_requirements":
            self.compare_requirements_open = True
            return None

        pending_messages = {
            "view_requirements": (
                "Consulte Manuales → Configuración segura para requisitos detallados."
            ),
            "catalog_specialized": (
                "Los modelos especializados se listarán aquí cuando estén asignados a su cuenta."
            ),
            "agents_catalog": (
                "En el cliente: Config › Agentes o el comando laim agents. "
                "Skills y tools se asignan ahí; usted confirma lo delicado."
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
        }
        message = pending_messages.get(
            action_key,
            "Funcionalidad en preparación. Consulte Soporte si lo necesita con urgencia.",
        )
        return rx.toast.info(message)

    # ------------------------------------------------------------------
    # Instaladores
    # ------------------------------------------------------------------

    @event
    def select_installers_edition(self, edition: str) -> None:
        """Elige community_edition o advance. Advance solo muestra el modal
        "En construcción / Under construction" — de pago, sin flujo real todavía."""
        if edition == "advance":
            self.show_advance_construction_modal = True
            return
        self.installers_edition = edition
        self.installers_platform = ""
        self.installers_latest = ""
        self.installers_error = ""

    @event
    def close_advance_construction_modal(self) -> None:
        self.show_advance_construction_modal = False

    @event
    def close_base_models_catalog(self) -> None:
        """Cierra el modal de referencia blue/green."""
        self.base_models_catalog_open = False

    @event
    def close_recommended_model(self) -> None:
        """Cierra la mini-guía de recomendación por hardware."""
        self.recommended_model_open = False

    @event
    def close_compare_requirements(self) -> None:
        """Cierra la comparativa monopuesto / Share."""
        self.compare_requirements_open = False

    @rx.event(background=True)
    async def select_installers_platform(self, platform: str) -> None:
        """Consulta el último instalador publicado para edition/platform.
        Los parches no se listan aquí: los detecta el cliente LAIM."""
        async with self:
            self.installers_platform = platform
            self.installers_loading = True
            self.installers_error = ""
            self.installers_latest = ""
            edition = self.installers_edition
            access_token = self.access_token
            session_token = self.session_token

        from laim_web.adapters.laim_api_client import get_laim_product_list

        data = get_laim_product_list(edition, "installer", platform, access_token, session_token)
        async with self:
            if data.get("success") is False:
                self.installers_error = data.get("error") or "Error obteniendo versiones disponibles."
            else:
                latest = data.get("latest") or ""
                if not latest:
                    self.installers_error = "Todavía no hay ninguna versión publicada para esta plataforma."
                self.installers_latest = latest

            self.installers_loading = False

    @rx.var
    def installers_download_url(self) -> str:
        if not self.installers_latest or not self.installers_platform:
            return ""
        version, _, filename = self.installers_latest.partition("/")
        if not filename:
            return ""
        from laim_web.adapters.laim_api_client import get_laim_product_download_url

        return get_laim_product_download_url(
            self.installers_edition, "installer", self.installers_platform, version, filename
        )

    @rx.var
    def installers_version(self) -> str:
        version, _, _ = self.installers_latest.partition("/")
        return version

    @rx.var
    def installers_filename(self) -> str:
        _, _, filename = self.installers_latest.partition("/")
        return filename

    @rx.var
    def installers_script_command(self) -> str:
        """Comando de terminal: curl|bash (mac/linux) o curl.exe -o (Windows)."""
        if self.installers_platform in ("mac_intel", "mac_silicon", "linux_deb", "linux_rpm"):
            from laim_web.adapters.laim_api_client import get_laim_product_script_url

            url = get_laim_product_script_url(self.installers_edition, self.installers_platform)
            return f"curl -fsSL {url} | bash"
        if self.installers_platform == "windows":
            url = self.installers_download_url
            filename = self.installers_filename
            if not url or not filename:
                return ""
            return f'curl.exe -fsSL "{url}" -o "{filename}"'
        return ""

    @event
    def copy_installers_script(self) -> EventHandlerReturn:
        """Copia el comando y registra el uso (sesión opcional)."""
        command = self.installers_script_command
        if not command:
            return None
        try:
            from laim_web.adapters.laim_api_client import laim_auditoria_instalador

            laim_auditoria_instalador(
                "copia_script",
                self.installers_edition,
                self.installers_platform,
                version=self.installers_version,
                filename=self.installers_filename,
                access_token=self.access_token,
                session_token=self.session_token,
            )
        except Exception:
            pass
        return rx.set_clipboard(command)

    @event
    def record_installers_download(self) -> None:
        """Clic en Descargar del navegador."""
        if not self.installers_platform:
            return
        try:
            from laim_web.adapters.laim_api_client import laim_auditoria_instalador

            laim_auditoria_instalador(
                "descarga",
                self.installers_edition,
                self.installers_platform,
                version=self.installers_version,
                filename=self.installers_filename,
                access_token=self.access_token,
                session_token=self.session_token,
            )
        except Exception:
            pass

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

    def _apply_laim_login_success(
        self,
        result: dict[str, Any],
        *,
        user_email_fallback: str = "",
    ) -> bool:
        """Aplica tokens y permisos tras un login API exitoso."""
        if not result.get("success"):
            self.error_message = result.get("error", "Error de autenticación")
            return False

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
            user_email=str(result.get("user_email", "") or user_email_fallback),
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
        self.login_password = ""
        self.error_message = ""
        self.login_error = ""
        self.active_menu = "instaladores"
        self._load_static_page("instaladores")
        self._token_renewal_running = True
        return True

    @event
    def handle_login(self) -> EventHandlerReturn:
        """Procesa login contra middleware LAIM."""
        from laim_web.adapters.laim_api_client import laim_login

        self.loading = True
        self.error_message = ""
        self.login_error = ""

        result = laim_login(self.login_username, self.login_password)

        if self._apply_laim_login_success(result):
            self.loading = False
            events: list[Any] = [LaimWebState.auto_renew_tokens_loop]
            self._record_auditoria_seccion(self.active_menu)
            if not self._auditoria_heartbeat_running:
                self._auditoria_heartbeat_running = True
                events.append(LaimWebState.auditoria_heartbeat_loop)
            return events

        self.loading = False

    @event
    def handle_logout(self) -> EventHandlerReturn:
        """Cierra sesión LAIM y vuelve al área pública."""
        from laim_web.adapters.laim_api_client import laim_logout

        access_token = self.access_token
        session_token = self.session_token

        self._token_renewal_running = False
        self._auditoria_heartbeat_running = False

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
        """Renueva tokens y hace polling del foro cuando corresponde."""
        from laim_web.adapters.laim_api_client import laim_forum_get_poll_interval_seconds

        while True:
            should_poll_tickets = False
            async with self:
                if not self._run_token_renewal_iteration():
                    break
                if getattr(self, "forum_poll_enabled", False):
                    self.forum_poll_tick()
                should_poll_tickets = bool(self.is_logged_in)
            if should_poll_tickets:
                yield LaimWebState.poll_ticket_notifications()
                yield LaimWebState.poll_install_notifications()

            if getattr(self, "forum_poll_enabled", False):
                await asyncio.sleep(laim_forum_get_poll_interval_seconds())
            else:
                await asyncio.sleep(120)


    def _mask_serial(self, serial: str) -> str:
        parts = [p for p in str(serial or "").split("-") if p]
        if len(parts) < 2:
            return "••••"
        hidden = [parts[0]] + ["••••"] * (len(parts) - 2) + [parts[-1]]
        return "-".join(hidden)

    def _public_install_row(self, row: dict[str, Any]) -> dict[str, str]:
        serial = str(row.get("serial_number") or "")
        return {
            "installation_id": str(row.get("installation_id") or ""),
            "serial_number": serial,
            "serial_masked": self._mask_serial(serial),
            "hostname": str(row.get("hostname") or ""),
            "display_name": str(row.get("display_name") or ""),
            "operating_system": str(row.get("operating_system") or ""),
            "edition": str(row.get("edition") or "community_edition"),
            "origin": str(row.get("origin") or ""),
            "status": str(row.get("status") or ""),
            "proposed_at": str(row.get("proposed_at") or ""),
            "registered_at": str(row.get("registered_at") or ""),
        }

    def set_install_serial(self, value: str) -> None:
        self.install_serial = value
        self.install_serial_valid = False
        self.install_serial_error = ""

    def set_install_hostname(self, value: str) -> None:
        self.install_hostname = value

    def set_install_display_name(self, value: str) -> None:
        self.install_display_name = value

    def set_install_os(self, value: str) -> None:
        self.install_os = value

    def set_install_edition(self, value: str) -> None:
        self.install_edition = value


    def open_install_instructions(self) -> None:
        self.install_instructions_open = True

    def close_install_instructions(self) -> None:
        self.install_instructions_open = False

    def open_manual_register(self) -> None:
        self.install_form_open = True
        self.install_editing = False
        self.install_edit_id = ""
        self.install_serial = ""
        self.install_serial_valid = False
        self.install_serial_error = ""
        self.install_hostname = ""
        self.install_display_name = ""
        self.install_os = "mac"
        self.install_edition = "community_edition"
        self.install_form_error = ""
        self.install_form_success = ""

    def close_install_form(self) -> None:
        self.install_form_open = False
        self.install_editing = False
        self.install_edit_id = ""
        self.install_form_error = ""
        self.install_form_success = ""

    def open_installation(self, installation_id: str) -> None:
        iid = str(installation_id)
        row = next((r for r in self.install_items if r.get("installation_id") == iid), None)
        if row is None:
            return
        self.install_form_open = True
        self.install_editing = True
        self.install_edit_id = iid
        self.install_serial = row.get("serial_number") or ""
        self.install_serial_valid = True
        self.install_serial_error = ""
        self.install_hostname = row.get("hostname") or ""
        self.install_display_name = row.get("display_name") or ""
        self.install_os = row.get("operating_system") or "mac"
        self.install_edition = "community_edition"
        self.install_form_error = ""
        self.install_form_success = ""

    @event
    def load_installations(self) -> None:
        from laim_web.adapters.laim_api_client import laim_list_installations

        result = laim_list_installations(self.access_token, self.session_token)
        if not result.get("success"):
            self.install_list_error = str(result.get("error") or "No se pudieron cargar las instalaciones")
            self.install_items = []
            return
        self.install_list_error = ""
        self.install_items = [self._public_install_row(r) for r in result.get("items") or []]
        blob = str(self.install_items)
        if "master_key" in blob:
            self.install_items = []
            self.install_list_error = "Respuesta inválida"

    @event
    def verify_install_serial(self) -> None:
        from laim_web.adapters.laim_api_client import laim_verify_serial

        serial = (self.install_serial or "").strip()
        if self.install_editing:
            return
        if not serial:
            self.install_serial_valid = False
            self.install_serial_error = ""
            return
        result = laim_verify_serial(serial, self.access_token, self.session_token)
        if result.get("valid"):
            self.install_serial_valid = True
            self.install_serial_error = ""
            return
        self.install_serial_valid = False
        self.install_serial_error = str(
            result.get("error") or "El número de serie no es válido"
        )

    @event
    def save_installation(self) -> None:
        from laim_web.adapters.laim_api_client import (
            laim_register_installation,
            laim_update_installation,
        )

        self.install_saving = True
        self.install_form_error = ""
        self.install_form_success = ""
        try:
            if self.install_editing:
                result = laim_update_installation(
                    int(self.install_edit_id),
                    {
                        "operating_system": self.install_os,
                        "edition": "community_edition",
                        "display_name": self.install_display_name.strip(),
                    },
                    self.access_token,
                    self.session_token,
                )
            else:
                if not self.install_serial_valid:
                    self.install_form_error = "Valide el número de serie antes de guardar"
                    return
                result = laim_register_installation(
                    {
                        "serial_number": self.install_serial.strip(),
                        "hostname": self.install_hostname.strip(),
                        "operating_system": self.install_os,
                        "edition": "community_edition",
                        "display_name": self.install_display_name.strip(),
                    },
                    self.access_token,
                    self.session_token,
                )
            if not result.get("success"):
                self.install_form_error = str(result.get("error") or "No se pudo guardar")
                return
            self.install_form_success = "Instalación guardada"
            self.load_installations()
            if not self.install_editing:
                self.install_form_open = False
        finally:
            self.install_saving = False

    @event
    def recognize_installation(self, installation_id: str) -> None:
        from laim_web.adapters.laim_api_client import laim_recognize_installation

        result = laim_recognize_installation(
            int(installation_id), self.access_token, self.session_token
        )
        if not result.get("success"):
            self.install_list_error = str(result.get("error") or "No se pudo reconocer")
            return
        self.load_installations()

    @event
    def reject_installation(self, installation_id: str) -> None:
        from laim_web.adapters.laim_api_client import laim_reject_installation

        result = laim_reject_installation(
            int(installation_id), self.access_token, self.session_token
        )
        if not result.get("success"):
            self.install_list_error = str(result.get("error") or "No se pudo rechazar")
            return
        self.load_installations()


def _register_laim_forum_event_handlers() -> None:
    """Registra handlers del foro si Reflex no los enlazó desde el mixin."""
    from reflex.event import EventHandler

    from laim_web.laim_forum_mixin import FORUM_EVENT_HANDLER_NAMES, LaimForumMixin

    for name in FORUM_EVENT_HANDLER_NAMES:
        if isinstance(getattr(LaimWebState, name, None), EventHandler):
            continue
        handler_fn = getattr(LaimForumMixin, name, None)
        if handler_fn is None:
            continue
        LaimWebState._add_event_handler(name, handler_fn)


_register_laim_forum_event_handlers()


def _register_laim_config_event_handlers() -> None:
    """Registra los modales de General si Reflex no los enlazó desde el mixin."""
    from reflex.event import EventHandler

    from laim_web.laim_config_mixin import CONFIG_EVENT_HANDLER_NAMES, LaimConfigMixin

    for name in CONFIG_EVENT_HANDLER_NAMES:
        if isinstance(getattr(LaimWebState, name, None), EventHandler):
            continue
        handler_fn = getattr(LaimConfigMixin, name, None)
        if handler_fn is None:
            continue
        LaimWebState._add_event_handler(name, handler_fn)


_register_laim_config_event_handlers()

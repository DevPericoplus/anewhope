"""Mixin de estado Reflex para el foro LAIM Web."""

from __future__ import annotations

from typing import Any

import reflex as rx
from reflex.event import event

EventHandlerReturn = Any

# Reflex 0.8+ solo registra @event en métodos del State, no en mixins.
FORUM_EVENT_HANDLER_NAMES: list[str] = []


def forum_event(func):
    """Decorador de eventos del foro que permite re-registro en LaimWebState."""
    FORUM_EVENT_HANDLER_NAMES.append(func.__name__)
    return event(func)


def forum_background_event(func):
    """Decorador para eventos background del foro (polling)."""
    FORUM_EVENT_HANDLER_NAMES.append(func.__name__)
    return rx.event(background=True)(func)


class LaimForumMixin:
    """Variables y handlers del foro (mezclar con LaimWebState)."""

    # Estado general del foro
    forum_loading: bool = False
    forum_error: str = ""
    forum_service_active: bool = True
    forum_notifications_count: int = 0

    # Catálogo
    forum_categories: list[dict[str, Any]] = []
    forum_subcategories: list[dict[str, Any]] = []
    forum_prefixes: list[dict[str, Any]] = []
    forum_selected_category_id: str = ""
    forum_selected_subcategory_id: str = ""

    # Hilos
    forum_threads: list[dict[str, Any]] = []
    forum_active_thread_id: int = 0
    forum_thread_title: str = ""
    forum_thread_body: str = ""
    forum_thread_closed: bool = False
    forum_thread_pinned: bool = False
    forum_thread_author: str = ""
    forum_thread_author_id: int = 0

    # Respuestas
    forum_posts: list[dict[str, Any]] = []
    forum_reply_body: str = ""

    # Nuevo hilo
    forum_new_thread_open: bool = False
    forum_new_title: str = ""
    forum_new_body: str = ""
    forum_new_prefix_id: str = ""

    # Mis hilos / respuestas
    forum_my_threads: list[dict[str, Any]] = []
    forum_my_posts: list[dict[str, Any]] = []

    # Admin
    forum_admin_settings_json: str = ""
    forum_admin_category_id: str = ""
    forum_admin_category_name: str = ""
    forum_admin_category_desc: str = ""
    forum_admin_subcategory_id: str = ""
    forum_admin_subcategory_name: str = ""
    forum_admin_subcategory_desc: str = ""
    forum_admin_message: str = ""

    # Adjuntos pendientes
    forum_new_thread_image_ids: list[int] = []
    forum_reply_image_ids: list[int] = []
    forum_thread_image_ids: list[int] = []

    # Perfil de foro
    forum_profile_display_name: str = ""
    forum_profile_signature: str = ""
    forum_profile_avatar_id: int = 0
    forum_profile_notify_mentions: bool = True
    forum_profile_notify_replies: bool = True
    forum_profile_message: str = ""
    forum_avatar_catalog: list[dict[str, Any]] = []

    # Admin extendido
    forum_admin_tab: str = "categories"
    forum_admin_settings_announce_ban: bool = True
    forum_admin_settings_ban_template: str = ""
    forum_admin_settings_delete_template: str = ""
    forum_admin_prefix_id: str = ""
    forum_admin_prefix_text: str = ""
    forum_admin_prefix_color: str = "green"
    forum_admin_word_palabra: str = ""
    forum_admin_word_accion: str = "warn"
    forum_admin_word_mensaje: str = ""
    forum_admin_url_dominio: str = ""
    forum_admin_url_descripcion: str = ""
    forum_admin_mod_user_id: int = 0
    forum_admin_mod_user_name: str = ""
    forum_admin_mod_subcategory_id: str = ""
    forum_admin_avatar_label: str = ""
    forum_admin_avatar_image_id: int = 0
    forum_word_rules: list[dict[str, Any]] = []
    forum_allowed_urls: list[dict[str, Any]] = []
    forum_moderators: list[dict[str, Any]] = []

    # Moderación
    forum_mod_logs: list[dict[str, Any]] = []
    forum_mod_bans: list[dict[str, Any]] = []
    forum_ban_user_id: int = 0
    forum_ban_motivo: str = ""
    forum_ban_expires_at: str = ""
    forum_mod_message: str = ""

    # Polling
    _forum_poll_running: bool = False
    forum_poll_enabled: bool = False

    # Vista previa de imagen
    forum_preview_image_url: str = ""

    def _forum_auth_tokens(self) -> tuple[str, str]:
        """Tokens de sesión para peticiones al foro."""
        return self.access_token, self.session_token

    def _forum_set_error(self, message: str) -> None:
        """Registra error visible en UI del foro."""
        self.forum_error = message

    @rx.var
    def forum_has_selection(self) -> bool:
        """True si hay subcategoría seleccionada."""
        return bool(self.forum_selected_subcategory_id)

    @rx.var
    def forum_has_thread(self) -> bool:
        """True si hay un hilo abierto."""
        return self.forum_active_thread_id > 0

    @rx.var
    def forum_prefix_options(self) -> list[str]:
        """Opciones de prefijo para selectores (id)."""
        return [str(p.get("id", "")) for p in self.forum_prefixes]

    @rx.var
    def forum_prefix_labels(self) -> list[str]:
        """Etiquetas legibles de prefijos."""
        return [str(p.get("texto", p.get("id", ""))) for p in self.forum_prefixes]

    @rx.var
    def forum_new_attachment_count(self) -> int:
        """Número de adjuntos pendientes para nuevo hilo."""
        return len(self.forum_new_thread_image_ids)

    @rx.var
    def forum_reply_attachment_count(self) -> int:
        """Número de adjuntos pendientes para respuesta."""
        return len(self.forum_reply_image_ids)

    @rx.var
    def forum_show_moderation(self) -> bool:
        """True si el usuario puede ver acciones de moderación (admin LAIM)."""
        return bool(getattr(self, "is_laim_admin", False))

    @rx.var
    def forum_ban_user_id_text(self) -> str:
        """Texto del campo ID de usuario para baneo."""
        return str(self.forum_ban_user_id) if self.forum_ban_user_id > 0 else ""

    @rx.var
    def forum_admin_mod_user_id_text(self) -> str:
        """Texto del campo ID de moderador."""
        return str(self.forum_admin_mod_user_id) if self.forum_admin_mod_user_id > 0 else ""

    @rx.var
    def forum_admin_avatar_image_id_text(self) -> str:
        """Texto del campo image ID para catálogo de avatares."""
        return (
            str(self.forum_admin_avatar_image_id)
            if self.forum_admin_avatar_image_id > 0
            else ""
        )

    @rx.var
    def forum_has_prefixes(self) -> bool:
        """True si hay prefijos disponibles para nuevos hilos."""
        return len(self.forum_prefixes) > 0

    @rx.var
    def forum_thread_has_attachments(self) -> bool:
        """True si el hilo activo tiene adjuntos."""
        return len(self.forum_thread_image_ids) > 0

    _FORUM_THREAD_ATTACHMENT_SCRIPT = """
(() => {
  const input = document.getElementById('forum_thread_file_input');
  if (!input || !input.files || input.files.length === 0) {
    return { attachment: null };
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
        attachment: {
          file_name: file.name,
          mime_type: file.type || 'application/octet-stream',
          data_base64: base64,
          target: 'thread',
        },
      });
    };
    reader.onerror = () => resolve({ attachment: null });
    reader.readAsDataURL(file);
  });
})()
"""

    _FORUM_REPLY_ATTACHMENT_SCRIPT = """
(() => {
  const input = document.getElementById('forum_reply_file_input');
  if (!input || !input.files || input.files.length === 0) {
    return { attachment: null };
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
        attachment: {
          file_name: file.name,
          mime_type: file.type || 'application/octet-stream',
          data_base64: base64,
          target: 'reply',
        },
      });
    };
    reader.onerror = () => resolve({ attachment: null });
    reader.readAsDataURL(file);
  });
})()
"""

    _FORUM_AVATAR_SCRIPT = """
(() => {
  const input = document.getElementById('forum_avatar_file_input');
  if (!input || !input.files || input.files.length === 0) {
    return { avatar: null };
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
        avatar: {
          file_name: file.name,
          mime_type: file.type || 'application/octet-stream',
          data_base64: base64,
        },
      });
    };
    reader.onerror = () => resolve({ avatar: null });
    reader.readAsDataURL(file);
  });
})()
"""
    @forum_event
    def forum_guard_auth(self) -> EventHandlerReturn:
        """Redirige al inicio si no hay sesión."""
        if not self.is_logged_in:
            return rx.redirect("/")
        return None

    @forum_event
    def forum_on_page_load(self) -> EventHandlerReturn:
        """Carga inicial del foro principal."""
        if not self.is_logged_in:
            return rx.redirect("/")
        self.forum_error = ""
        self.forum_poll_enabled = True
        self.forum_load_catalog()
        self.forum_poll_notifications()
        if self.forum_active_thread_id > 0:
            self.forum_open_thread(self.forum_active_thread_id)
        from laim_web.laim_state import LaimWebState

        if self.is_logged_in and self.session_token and not self._token_renewal_running:
            self._token_renewal_running = True
            return LaimWebState.auto_renew_tokens_loop
        if self.is_logged_in and not self._forum_poll_running:
            self._forum_poll_running = True
            return LaimWebState.forum_poll_loop
        return None

    @forum_event
    def forum_my_threads_on_load(self) -> EventHandlerReturn:
        """Carga página mis hilos."""
        if not self.is_logged_in:
            return rx.redirect("/")
        self.forum_load_my_threads()
        return None

    @forum_event
    def forum_my_posts_on_load(self) -> EventHandlerReturn:
        """Carga página mis respuestas."""
        if not self.is_logged_in:
            return rx.redirect("/")
        self.forum_load_my_posts()
        return None

    @forum_event
    def forum_admin_on_load(self) -> EventHandlerReturn:
        """Carga panel admin del foro."""
        if not self.is_logged_in:
            return rx.redirect("/")
        if not self.is_laim_admin:
            return rx.redirect("/foro")
        self.forum_load_admin_panel()
        self.forum_load_admin_extended()
        return None

    def forum_poll_notifications(self) -> None:
        """Consulta notificaciones pendientes del foro."""
        from laim_web.adapters.laim_api_client import (
            laim_forum_ack_notifications,
            laim_forum_pending_notifications,
        )

        if not self.is_logged_in:
            return

        access, session = self._forum_auth_tokens()
        result = laim_forum_pending_notifications(access, session)
        if not result.get("success"):
            return

        items = result.get("items", [])
        self.forum_notifications_count = len(items)
        if items:
            ids = [int(i["id"]) for i in items if i.get("id")]
            if ids:
                laim_forum_ack_notifications(ids, access, session)

    def forum_poll_tick(self) -> None:
        """Actualiza notificaciones y hilo activo (llamado desde polling)."""
        self.forum_poll_notifications()
        if self.forum_active_thread_id > 0:
            from laim_web.adapters.laim_api_client import laim_forum_list_posts

            access, session = self._forum_auth_tokens()
            posts_result = laim_forum_list_posts(
                self.forum_active_thread_id, access, session
            )
            if posts_result.get("success"):
                self.forum_posts = posts_result.get("items", [])

    def forum_load_catalog(self) -> None:
        """Carga categorías, subcategorías y prefijos."""
        from laim_web.adapters.laim_api_client import (
            laim_forum_health,
            laim_forum_list_categories,
            laim_forum_list_prefixes,
            laim_forum_list_subcategories,
        )

        self.forum_loading = True
        self.forum_error = ""

        health = laim_forum_health()
        self.forum_service_active = bool(health.get("activo", health.get("success")))

        access, session = self._forum_auth_tokens()
        cat_result = laim_forum_list_categories(access, session)
        if not cat_result.get("success"):
            self._forum_set_error(cat_result.get("error", "No se pudieron cargar categorías"))
            self.forum_loading = False
            return

        self.forum_categories = cat_result.get("items", [])
        prefix_result = laim_forum_list_prefixes(access, session)
        if prefix_result.get("success"):
            self.forum_prefixes = prefix_result.get("items", [])

        if self.forum_categories and not self.forum_selected_category_id:
            self.forum_selected_category_id = str(self.forum_categories[0].get("id", ""))

        if self.forum_selected_category_id:
            sub_result = laim_forum_list_subcategories(
                access, session, self.forum_selected_category_id
            )
            if sub_result.get("success"):
                self.forum_subcategories = sub_result.get("items", [])
                if self.forum_subcategories and not self.forum_selected_subcategory_id:
                    self.forum_selected_subcategory_id = str(
                        self.forum_subcategories[0].get("id", "")
                    )
                    self.forum_load_threads()

        self.forum_loading = False

    @forum_event
    def forum_select_category(self, category_id: str) -> None:
        """Selecciona categoría y recarga subcategorías."""
        from laim_web.adapters.laim_api_client import laim_forum_list_subcategories

        self.forum_selected_category_id = category_id
        self.forum_selected_subcategory_id = ""
        self.forum_active_thread_id = 0
        self.forum_threads = []
        self.forum_posts = []

        access, session = self._forum_auth_tokens()
        result = laim_forum_list_subcategories(access, session, category_id)
        if result.get("success"):
            self.forum_subcategories = result.get("items", [])
            if self.forum_subcategories:
                first_id = str(self.forum_subcategories[0].get("id", ""))
                self.forum_selected_subcategory_id = first_id
                self.forum_load_threads()
        else:
            self._forum_set_error(result.get("error", "Error al cargar subcategorías"))

    @forum_event
    def forum_select_subcategory(self, subcategory_id: str) -> None:
        """Selecciona subcategoría y lista hilos."""
        self.forum_selected_subcategory_id = subcategory_id
        self.forum_active_thread_id = 0
        self.forum_posts = []
        self.forum_load_threads()

    def forum_load_threads(self) -> None:
        """Carga hilos de la subcategoría activa."""
        from laim_web.adapters.laim_api_client import laim_forum_list_threads

        if not self.forum_selected_subcategory_id:
            self.forum_threads = []
            return

        access, session = self._forum_auth_tokens()
        result = laim_forum_list_threads(
            self.forum_selected_subcategory_id, access, session
        )
        if result.get("success"):
            self.forum_threads = result.get("items", [])
        else:
            self._forum_set_error(result.get("error", "Error al cargar hilos"))

    @forum_event
    def forum_open_thread(self, thread_id: int) -> None:
        """Abre un hilo y carga sus respuestas."""
        from laim_web.adapters.laim_api_client import (
            laim_forum_get_thread,
            laim_forum_list_posts,
        )

        access, session = self._forum_auth_tokens()
        thread_result = laim_forum_get_thread(thread_id, access, session)
        if not thread_result.get("success"):
            self._forum_set_error(thread_result.get("error", "Hilo no encontrado"))
            return

        thread = thread_result.get("thread", {})
        self.forum_active_thread_id = int(thread.get("id", thread_id))
        self.forum_thread_title = str(thread.get("titulo", ""))
        self.forum_thread_body = str(thread.get("cuerpo_md", ""))
        self.forum_thread_closed = bool(thread.get("cerrado"))
        self.forum_thread_pinned = bool(thread.get("fijado"))
        self.forum_thread_author = str(thread.get("user_name", ""))
        self.forum_thread_author_id = int(thread.get("user_id", 0))
        raw_images = thread.get("image_ids", [])
        self.forum_thread_image_ids = [
            int(i) for i in raw_images if i is not None
        ] if isinstance(raw_images, list) else []

        posts_result = laim_forum_list_posts(thread_id, access, session)
        if posts_result.get("success"):
            self.forum_posts = posts_result.get("items", [])
        else:
            self.forum_posts = []
            self._forum_set_error(posts_result.get("error", "Error al cargar respuestas"))

    @forum_event
    def forum_close_thread(self) -> None:
        """Cierra vista de hilo."""
        self.forum_active_thread_id = 0
        self.forum_thread_title = ""
        self.forum_thread_body = ""
        self.forum_posts = []
        self.forum_reply_body = ""
        self.forum_reply_image_ids = []

    @forum_event
    def forum_refresh(self) -> None:
        """Refresca hilos o hilo activo."""
        if self.forum_active_thread_id > 0:
            self.forum_open_thread(self.forum_active_thread_id)
        else:
            self.forum_load_threads()

    @forum_event
    def forum_toggle_new_thread(self) -> None:
        """Abre/cierra formulario de nuevo hilo."""
        self.forum_new_thread_open = not self.forum_new_thread_open
        if not self.forum_new_thread_open:
            self.forum_new_title = ""
            self.forum_new_body = ""
            self.forum_new_prefix_id = ""
            self.forum_new_thread_image_ids = []

    @forum_event
    def forum_set_new_title(self, value: str) -> None:
        self.forum_new_title = value

    @forum_event
    def forum_set_new_body(self, value: str) -> None:
        self.forum_new_body = value

    @forum_event
    def forum_set_new_prefix(self, value: str) -> None:
        self.forum_new_prefix_id = value

    @forum_event
    def forum_set_reply_body(self, value: str) -> None:
        self.forum_reply_body = value

    @forum_event
    def forum_create_thread(self) -> EventHandlerReturn:
        """Crea un hilo en la subcategoría activa."""
        from laim_web.adapters.laim_api_client import laim_forum_create_thread

        if not self.forum_selected_subcategory_id:
            self._forum_set_error("Seleccione una subcategoría.")
            return None
        if not self.forum_new_title.strip():
            self._forum_set_error("El título es obligatorio.")
            return None
        if not self.forum_new_body.strip():
            self._forum_set_error("El contenido es obligatorio.")
            return None

        payload: dict[str, Any] = {
            "subcategory_id": self.forum_selected_subcategory_id,
            "titulo": self.forum_new_title.strip(),
            "cuerpo_md": self.forum_new_body.strip(),
            "image_ids": list(self.forum_new_thread_image_ids),
        }
        if self.forum_new_prefix_id.strip():
            payload["prefix_id"] = self.forum_new_prefix_id.strip()

        access, session = self._forum_auth_tokens()
        result = laim_forum_create_thread(payload, access, session)
        if not result.get("success"):
            self._forum_set_error(result.get("error", "No se pudo crear el hilo"))
            return None

        thread_id = int(result.get("thread_id", 0))
        self.forum_new_thread_open = False
        self.forum_new_title = ""
        self.forum_new_body = ""
        self.forum_new_prefix_id = ""
        self.forum_new_thread_image_ids = []
        self.forum_error = ""
        self.forum_load_threads()
        if thread_id > 0:
            self.forum_open_thread(thread_id)
        return None

    @forum_event
    def forum_submit_reply(self) -> EventHandlerReturn:
        """Publica respuesta en el hilo activo."""
        from laim_web.adapters.laim_api_client import laim_forum_create_post

        if self.forum_active_thread_id <= 0:
            return None
        if self.forum_thread_closed:
            self._forum_set_error("El hilo está cerrado.")
            return None
        if not self.forum_reply_body.strip():
            self._forum_set_error("Escriba una respuesta.")
            return None

        access, session = self._forum_auth_tokens()
        result = laim_forum_create_post(
            self.forum_active_thread_id,
            {"cuerpo_md": self.forum_reply_body.strip(), "image_ids": list(self.forum_reply_image_ids)},
            access,
            session,
        )
        if not result.get("success"):
            self._forum_set_error(result.get("error", "No se pudo publicar la respuesta"))
            return None

        self.forum_reply_body = ""
        self.forum_reply_image_ids = []
        self.forum_error = ""
        self.forum_open_thread(self.forum_active_thread_id)
        return None

    @forum_event
    def forum_rate_post(self, post_id: int, rating: int) -> None:
        """Valora una respuesta."""
        from laim_web.adapters.laim_api_client import laim_forum_rate_post

        access, session = self._forum_auth_tokens()
        result = laim_forum_rate_post(post_id, rating, access, session)
        if not result.get("success"):
            self._forum_set_error(result.get("error", "No se pudo valorar"))
        else:
            self.forum_error = ""

    def forum_load_my_threads(self) -> None:
        """Carga hilos del usuario."""
        from laim_web.adapters.laim_api_client import laim_forum_my_threads

        access, session = self._forum_auth_tokens()
        result = laim_forum_my_threads(access, session)
        if result.get("success"):
            self.forum_my_threads = result.get("items", [])
        else:
            self._forum_set_error(result.get("error", "Error al cargar mis hilos"))

    def forum_load_my_posts(self) -> None:
        """Carga respuestas del usuario."""
        from laim_web.adapters.laim_api_client import laim_forum_my_posts

        access, session = self._forum_auth_tokens()
        result = laim_forum_my_posts(access, session)
        if result.get("success"):
            self.forum_my_posts = result.get("items", [])
        else:
            self._forum_set_error(result.get("error", "Error al cargar mis respuestas"))

    @forum_event
    def forum_go_to_thread(self, thread_id: int) -> EventHandlerReturn:
        """Navega al foro y abre un hilo."""
        self.forum_active_thread_id = thread_id
        return rx.redirect("/foro")

    def forum_load_admin_panel(self) -> None:
        """Carga datos del panel admin."""
        from laim_web.adapters.laim_api_client import (
            laim_forum_admin_settings,
            laim_forum_list_categories,
            laim_forum_list_subcategories,
        )

        access, session = self._forum_auth_tokens()
        settings = laim_forum_admin_settings(access, session)
        if settings.get("success"):
            import json

            self.forum_admin_settings_json = json.dumps(
                settings.get("settings", settings.get("items", settings)),
                ensure_ascii=False,
                indent=2,
            )

        cat_result = laim_forum_list_categories(access, session)
        if cat_result.get("success"):
            self.forum_categories = cat_result.get("items", [])
            if self.forum_categories and not self.forum_selected_category_id:
                self.forum_selected_category_id = str(
                    self.forum_categories[0].get("id", "")
                )

        if self.forum_selected_category_id:
            sub_result = laim_forum_list_subcategories(
                access, session, self.forum_selected_category_id
            )
            if sub_result.get("success"):
                self.forum_subcategories = sub_result.get("items", [])

    @forum_event
    def forum_admin_set_category_id(self, value: str) -> None:
        self.forum_admin_category_id = value

    @forum_event
    def forum_admin_set_category_name(self, value: str) -> None:
        self.forum_admin_category_name = value

    @forum_event
    def forum_admin_set_category_desc(self, value: str) -> None:
        self.forum_admin_category_desc = value

    @forum_event
    def forum_admin_set_subcategory_id(self, value: str) -> None:
        self.forum_admin_subcategory_id = value

    @forum_event
    def forum_admin_set_subcategory_name(self, value: str) -> None:
        self.forum_admin_subcategory_name = value

    @forum_event
    def forum_admin_set_subcategory_desc(self, value: str) -> None:
        self.forum_admin_subcategory_desc = value

    @forum_event
    def forum_admin_save_category(self) -> None:
        """Guarda categoría (admin)."""
        from laim_web.adapters.laim_api_client import laim_forum_upsert_category

        if not self.forum_admin_category_id.strip() or not self.forum_admin_category_name.strip():
            self.forum_admin_message = "ID y nombre de categoría son obligatorios."
            return

        access, session = self._forum_auth_tokens()
        result = laim_forum_upsert_category(
            {
                "id": self.forum_admin_category_id.strip(),
                "nombre": self.forum_admin_category_name.strip(),
                "descripcion": self.forum_admin_category_desc.strip(),
                "orden": 0,
                "activa": True,
            },
            access,
            session,
        )
        if result.get("success"):
            self.forum_admin_message = "Categoría guardada."
            self.forum_load_admin_panel()
        else:
            self.forum_admin_message = result.get("error", "Error al guardar categoría")

    @forum_event
    def forum_admin_save_subcategory(self) -> None:
        """Guarda subcategoría (admin)."""
        from laim_web.adapters.laim_api_client import laim_forum_upsert_subcategory

        if not self.forum_selected_category_id:
            self.forum_admin_message = "Seleccione una categoría padre en el foro."
            return
        if not self.forum_admin_subcategory_id.strip() or not self.forum_admin_subcategory_name.strip():
            self.forum_admin_message = "ID y nombre de subcategoría son obligatorios."
            return

        access, session = self._forum_auth_tokens()
        result = laim_forum_upsert_subcategory(
            {
                "id": self.forum_admin_subcategory_id.strip(),
                "categoria_id": self.forum_selected_category_id,
                "nombre": self.forum_admin_subcategory_name.strip(),
                "descripcion": self.forum_admin_subcategory_desc.strip(),
                "orden": 0,
                "activa": True,
            },
            access,
            session,
        )
        if result.get("success"):
            self.forum_admin_message = "Subcategoría guardada."
            self.forum_load_admin_panel()
        else:
            self.forum_admin_message = result.get("error", "Error al guardar subcategoría")

    @forum_event
    def forum_preview_image(self, image_id: int) -> None:
        """Carga imagen adjunta como data URL."""
        from laim_web.adapters.laim_api_client import laim_forum_get_image_data_url

        access, session = self._forum_auth_tokens()
        self.forum_preview_image_url = laim_forum_get_image_data_url(
            image_id, access, session
        )

    @forum_event
    def forum_admin_set_prefix_id(self, value: str) -> None:
        self.forum_admin_prefix_id = value

    @forum_event
    def forum_admin_set_prefix_text(self, value: str) -> None:
        self.forum_admin_prefix_text = value

    @forum_event
    def forum_admin_set_prefix_color(self, value: str) -> None:
        self.forum_admin_prefix_color = value

    @forum_event
    def forum_admin_set_announce_ban(self, value: bool) -> None:
        self.forum_admin_settings_announce_ban = value

    @forum_event
    def forum_admin_set_ban_template(self, value: str) -> None:
        self.forum_admin_settings_ban_template = value

    @forum_event
    def forum_admin_set_delete_template(self, value: str) -> None:
        self.forum_admin_settings_delete_template = value

    @forum_event
    def forum_admin_set_word_palabra(self, value: str) -> None:
        self.forum_admin_word_palabra = value

    @forum_event
    def forum_admin_set_word_accion(self, value: str) -> None:
        self.forum_admin_word_accion = value

    @forum_event
    def forum_admin_set_word_mensaje(self, value: str) -> None:
        self.forum_admin_word_mensaje = value

    @forum_event
    def forum_admin_set_url_dominio(self, value: str) -> None:
        self.forum_admin_url_dominio = value

    @forum_event
    def forum_admin_set_url_descripcion(self, value: str) -> None:
        self.forum_admin_url_descripcion = value

    @forum_event
    def forum_admin_set_mod_user_id(self, value: str) -> None:
        try:
            self.forum_admin_mod_user_id = int(value.strip())
        except ValueError:
            self.forum_admin_mod_user_id = 0

    @forum_event
    def forum_admin_set_mod_user_name(self, value: str) -> None:
        self.forum_admin_mod_user_name = value

    @forum_event
    def forum_admin_set_mod_subcategory_id(self, value: str) -> None:
        self.forum_admin_mod_subcategory_id = value

    @forum_event
    def forum_admin_set_avatar_image_id(self, value: str) -> None:
        try:
            self.forum_admin_avatar_image_id = int(value.strip())
        except ValueError:
            self.forum_admin_avatar_image_id = 0

    @forum_event
    def forum_admin_set_avatar_label(self, value: str) -> None:
        self.forum_admin_avatar_label = value

    @forum_event
    def forum_close_image_preview(self) -> None:
        self.forum_preview_image_url = ""

    @forum_background_event
    async def forum_poll_loop(self) -> None:
        """Polling periódico de notificaciones y respuestas del hilo activo."""
        import asyncio

        from laim_web.adapters.laim_api_client import laim_forum_get_poll_interval_seconds

        interval = laim_forum_get_poll_interval_seconds()
        while True:
            async with self:
                if not self.is_logged_in:
                    self._forum_poll_running = False
                    break
                self.forum_poll_tick()
            await asyncio.sleep(interval)

    @forum_event
    def forum_request_thread_attachment(self) -> EventHandlerReturn:
        """Lee adjunto del formulario de nuevo hilo."""
        from laim_web.laim_state import LaimWebState

        return rx.call_script(
            self._FORUM_THREAD_ATTACHMENT_SCRIPT,
            callback=LaimWebState.forum_process_attachment_upload,
        )

    @forum_event
    def forum_request_reply_attachment(self) -> EventHandlerReturn:
        """Lee adjunto del formulario de respuesta."""
        from laim_web.laim_state import LaimWebState

        return rx.call_script(
            self._FORUM_REPLY_ATTACHMENT_SCRIPT,
            callback=LaimWebState.forum_process_attachment_upload,
        )

    @forum_event
    def forum_process_attachment_upload(
        self, payload: dict[str, object] | None
    ) -> None:
        """Sube adjunto y lo añade a la lista pendiente."""
        from laim_web.adapters.laim_api_client import laim_forum_upload_image

        if not isinstance(payload, dict):
            return
        raw = payload.get("attachment")
        if not isinstance(raw, dict):
            self._forum_set_error("No se seleccionó ningún archivo.")
            return

        file_name = str(raw.get("file_name", "")).strip()
        mime_type = str(raw.get("mime_type", "")).strip()
        data_base64 = str(raw.get("data_base64", "")).strip()
        target = str(raw.get("target", "thread"))
        if not file_name or not mime_type or not data_base64:
            self._forum_set_error("Archivo adjunto no válido.")
            return

        access, session = self._forum_auth_tokens()
        result = laim_forum_upload_image(
            {
                "file_name": file_name,
                "mime_type": mime_type,
                "data_base64": data_base64,
                "image_kind": "post_attachment",
            },
            access,
            session,
        )
        if not result.get("success"):
            self._forum_set_error(result.get("error", "No se pudo subir el adjunto."))
            return

        image = result.get("image", {})
        image_id = int(image.get("id", 0))
        if image_id <= 0:
            self._forum_set_error("Respuesta de imagen inválida.")
            return

        if target == "reply":
            if image_id not in self.forum_reply_image_ids:
                self.forum_reply_image_ids = [*self.forum_reply_image_ids, image_id]
        else:
            if image_id not in self.forum_new_thread_image_ids:
                self.forum_new_thread_image_ids = [
                    *self.forum_new_thread_image_ids,
                    image_id,
                ]
        self.forum_error = ""

    @forum_event
    def forum_moderate_pin(self) -> None:
        """Fija o desfija el hilo activo."""
        from laim_web.adapters.laim_api_client import laim_forum_update_thread

        if self.forum_active_thread_id <= 0:
            return
        access, session = self._forum_auth_tokens()
        result = laim_forum_update_thread(
            self.forum_active_thread_id,
            {"fijado": not self.forum_thread_pinned},
            access,
            session,
        )
        if result.get("success"):
            self.forum_open_thread(self.forum_active_thread_id)
        else:
            self._forum_set_error(result.get("error", "No se pudo fijar el hilo."))

    @forum_event
    def forum_moderate_close(self) -> None:
        """Cierra o abre el hilo activo."""
        from laim_web.adapters.laim_api_client import laim_forum_update_thread

        if self.forum_active_thread_id <= 0:
            return
        access, session = self._forum_auth_tokens()
        result = laim_forum_update_thread(
            self.forum_active_thread_id,
            {"cerrado": not self.forum_thread_closed},
            access,
            session,
        )
        if result.get("success"):
            self.forum_open_thread(self.forum_active_thread_id)
        else:
            self._forum_set_error(result.get("error", "No se pudo cambiar el estado."))

    @forum_event
    def forum_moderate_delete_thread(self) -> None:
        """Elimina el hilo activo."""
        from laim_web.adapters.laim_api_client import laim_forum_delete_thread

        if self.forum_active_thread_id <= 0:
            return
        thread_id = self.forum_active_thread_id
        access, session = self._forum_auth_tokens()
        result = laim_forum_delete_thread(thread_id, access, session)
        if result.get("success"):
            self.forum_close_thread()
            self.forum_load_threads()
            self.forum_error = ""
        else:
            self._forum_set_error(result.get("error", "No se pudo eliminar el hilo."))

    @forum_event
    def forum_profile_on_load(self) -> EventHandlerReturn:
        """Carga página de perfil de foro."""
        if not self.is_logged_in:
            return rx.redirect("/")
        self.forum_load_profile()
        return None

    def forum_load_profile(self) -> None:
        """Carga perfil y catálogo de avatares."""
        from laim_web.adapters.laim_api_client import (
            laim_forum_get_profile,
            laim_forum_list_avatar_catalog,
        )

        access, session = self._forum_auth_tokens()
        profile_result = laim_forum_get_profile(access, session)
        if profile_result.get("success"):
            profile = profile_result.get("profile", {})
            self.forum_profile_display_name = str(
                profile.get("forum_display_name") or profile.get("user_name") or ""
            )
            self.forum_profile_signature = str(profile.get("signature_md") or "")
            self.forum_profile_avatar_id = int(profile.get("avatar_image_id") or 0)
            self.forum_profile_notify_mentions = bool(
                profile.get("notify_mentions", True)
            )
            self.forum_profile_notify_replies = bool(
                profile.get("notify_replies", True)
            )
        else:
            self._forum_set_error(profile_result.get("error", "Error al cargar perfil"))

        catalog = laim_forum_list_avatar_catalog(access, session)
        if catalog.get("success"):
            self.forum_avatar_catalog = catalog.get("items", [])

    @forum_event
    def forum_set_profile_display_name(self, value: str) -> None:
        self.forum_profile_display_name = value

    @forum_event
    def forum_set_profile_signature(self, value: str) -> None:
        self.forum_profile_signature = value

    @forum_event
    def forum_set_profile_notify_mentions(self, value: bool) -> None:
        self.forum_profile_notify_mentions = value

    @forum_event
    def forum_set_profile_notify_replies(self, value: bool) -> None:
        self.forum_profile_notify_replies = value

    @forum_event
    def forum_select_catalog_avatar(self, image_id: int) -> None:
        self.forum_profile_avatar_id = image_id

    @forum_event
    def forum_save_profile(self) -> None:
        """Guarda perfil de foro."""
        from laim_web.adapters.laim_api_client import laim_forum_update_profile

        access, session = self._forum_auth_tokens()
        payload: dict[str, Any] = {
            "forum_display_name": self.forum_profile_display_name.strip() or None,
            "signature_md": self.forum_profile_signature.strip() or None,
            "notify_mentions": self.forum_profile_notify_mentions,
            "notify_replies": self.forum_profile_notify_replies,
        }
        if self.forum_profile_avatar_id > 0:
            payload["avatar_image_id"] = self.forum_profile_avatar_id

        result = laim_forum_update_profile(payload, access, session)
        if result.get("success"):
            self.forum_profile_message = "Perfil guardado."
            self.forum_error = ""
        else:
            self.forum_profile_message = ""
            self._forum_set_error(result.get("error", "No se pudo guardar el perfil."))

    @forum_event
    def forum_request_avatar_upload(self) -> EventHandlerReturn:
        """Sube avatar personal."""
        from laim_web.laim_state import LaimWebState

        return rx.call_script(
            self._FORUM_AVATAR_SCRIPT,
            callback=LaimWebState.forum_process_avatar_upload,
        )

    @forum_event
    def forum_process_avatar_upload(self, payload: dict[str, object] | None) -> None:
        """Procesa subida de avatar personal."""
        from laim_web.adapters.laim_api_client import (
            laim_forum_update_profile,
            laim_forum_upload_image,
        )

        if not isinstance(payload, dict):
            return
        raw = payload.get("avatar")
        if not isinstance(raw, dict):
            self._forum_set_error("No se seleccionó imagen de avatar.")
            return

        access, session = self._forum_auth_tokens()
        upload = laim_forum_upload_image(
            {
                "file_name": str(raw.get("file_name", "")),
                "mime_type": str(raw.get("mime_type", "")),
                "data_base64": str(raw.get("data_base64", "")),
                "image_kind": "avatar_user",
            },
            access,
            session,
        )
        if not upload.get("success"):
            self._forum_set_error(upload.get("error", "No se pudo subir el avatar."))
            return

        image_id = int(upload.get("image", {}).get("id", 0))
        if image_id <= 0:
            return

        self.forum_profile_avatar_id = image_id
        update = laim_forum_update_profile(
            {"avatar_image_id": image_id}, access, session
        )
        if update.get("success"):
            self.forum_profile_message = "Avatar actualizado."
            self.forum_error = ""
        else:
            self._forum_set_error(update.get("error", "No se pudo asignar el avatar."))

    @forum_event
    def forum_mod_on_load(self) -> EventHandlerReturn:
        """Carga panel de moderación."""
        if not self.is_logged_in:
            return rx.redirect("/")
        if not self.forum_show_moderation:
            return rx.redirect("/foro")
        if not self.forum_selected_subcategory_id:
            self.forum_load_catalog()
        self.forum_load_moderation_data()
        return None

    def forum_load_moderation_data(self) -> None:
        """Carga logs de la subcategoría activa."""
        from laim_web.adapters.laim_api_client import laim_forum_moderation_logs

        if not self.forum_selected_subcategory_id:
            self.forum_mod_logs = []
            return
        access, session = self._forum_auth_tokens()
        result = laim_forum_moderation_logs(
            self.forum_selected_subcategory_id, access, session
        )
        if result.get("success"):
            self.forum_mod_logs = result.get("items", [])
        else:
            self._forum_set_error(result.get("error", "No se pudieron cargar logs."))

    @forum_event
    def forum_refresh_moderation(self) -> None:
        """Recarga datos del panel de moderación."""
        self.forum_load_moderation_data()

    @forum_event
    def forum_set_ban_user_id(self, value: str) -> None:
        try:
            self.forum_ban_user_id = int(value.strip())
        except ValueError:
            self.forum_ban_user_id = 0

    @forum_event
    def forum_set_ban_motivo(self, value: str) -> None:
        self.forum_ban_motivo = value

    @forum_event
    def forum_set_ban_expires(self, value: str) -> None:
        self.forum_ban_expires_at = value

    @forum_event
    def forum_submit_ban(self) -> None:
        """Banea usuario en subcategoría activa."""
        from laim_web.adapters.laim_api_client import laim_forum_create_ban

        if not self.forum_selected_subcategory_id:
            self.forum_mod_message = "Seleccione subcategoría en el foro."
            return
        if self.forum_ban_user_id <= 0 or not self.forum_ban_motivo.strip():
            self.forum_mod_message = "Indique usuario y motivo."
            return

        access, session = self._forum_auth_tokens()
        payload: dict[str, Any] = {
            "user_id": self.forum_ban_user_id,
            "subcategory_id": self.forum_selected_subcategory_id,
            "motivo": self.forum_ban_motivo.strip(),
        }
        if self.forum_ban_expires_at.strip():
            payload["expires_at"] = self.forum_ban_expires_at.strip()

        result = laim_forum_create_ban(payload, access, session)
        if result.get("success"):
            self.forum_mod_message = "Usuario baneado."
            self.forum_ban_motivo = ""
            self.forum_load_moderation_data()
        else:
            self.forum_mod_message = result.get("error", "No se pudo banear.")

    @forum_event
    def forum_revoke_ban(self, ban_id: int) -> None:
        """Revoca un baneo."""
        from laim_web.adapters.laim_api_client import laim_forum_revoke_ban

        access, session = self._forum_auth_tokens()
        result = laim_forum_revoke_ban(ban_id, access, session)
        if result.get("success"):
            self.forum_mod_message = "Baneo revocado."
            self.forum_load_moderation_data()
        else:
            self.forum_mod_message = result.get("error", "No se pudo revocar.")

    @forum_event
    def forum_admin_set_tab(self, tab: str) -> None:
        self.forum_admin_tab = tab
        if tab in ("word-rules", "allowed-urls", "moderators", "settings"):
            self.forum_load_admin_extended()

    def forum_load_admin_extended(self) -> None:
        """Carga datos de pestañas admin extendidas."""
        from laim_web.adapters.laim_api_client import (
            laim_forum_admin_allowed_urls,
            laim_forum_admin_moderators,
            laim_forum_admin_settings,
            laim_forum_admin_word_rules,
            laim_forum_list_avatar_catalog,
        )

        access, session = self._forum_auth_tokens()
        settings = laim_forum_admin_settings(access, session)
        if settings.get("success"):
            import json

            cfg = settings.get("settings", settings)
            self.forum_admin_settings_json = json.dumps(
                cfg, ensure_ascii=False, indent=2
            )
            if isinstance(cfg, dict):
                self.forum_admin_settings_announce_ban = bool(
                    cfg.get("anunciar_ban_en_log", True)
                )
                self.forum_admin_settings_ban_template = str(
                    cfg.get("plantilla_ban") or ""
                )
                self.forum_admin_settings_delete_template = str(
                    cfg.get("plantilla_eliminacion") or ""
                )

        words = laim_forum_admin_word_rules(access, session)
        if words.get("success"):
            self.forum_word_rules = words.get("items", [])

        urls = laim_forum_admin_allowed_urls(access, session)
        if urls.get("success"):
            self.forum_allowed_urls = urls.get("items", [])

        mods = laim_forum_admin_moderators(
            access, session, self.forum_selected_subcategory_id or None
        )
        if mods.get("success"):
            self.forum_moderators = mods.get("items", [])

        avatars = laim_forum_list_avatar_catalog(access, session)
        if avatars.get("success"):
            self.forum_avatar_catalog = avatars.get("items", [])

    @forum_event
    def forum_admin_save_settings(self) -> None:
        """Guarda ajustes de moderación."""
        from laim_web.adapters.laim_api_client import laim_forum_admin_update_settings

        access, session = self._forum_auth_tokens()
        result = laim_forum_admin_update_settings(
            {
                "anunciar_ban_en_log": self.forum_admin_settings_announce_ban,
                "plantilla_ban": self.forum_admin_settings_ban_template,
                "plantilla_eliminacion": self.forum_admin_settings_delete_template,
            },
            access,
            session,
        )
        self.forum_admin_message = (
            "Ajustes guardados." if result.get("success") else result.get("error", "Error")
        )

    @forum_event
    def forum_admin_save_prefix(self) -> None:
        """Guarda prefijo de hilo."""
        from laim_web.adapters.laim_api_client import laim_forum_upsert_prefix

        if not self.forum_admin_prefix_id.strip() or not self.forum_admin_prefix_text.strip():
            self.forum_admin_message = "ID y texto del prefijo son obligatorios."
            return
        access, session = self._forum_auth_tokens()
        result = laim_forum_upsert_prefix(
            {
                "id": self.forum_admin_prefix_id.strip(),
                "texto": self.forum_admin_prefix_text.strip(),
                "color_scheme": self.forum_admin_prefix_color.strip() or "green",
                "activo": True,
            },
            access,
            session,
        )
        self.forum_admin_message = (
            "Prefijo guardado." if result.get("success") else result.get("error", "Error")
        )
        if result.get("success"):
            self.forum_load_catalog()

    @forum_event
    def forum_admin_save_word_rule(self) -> None:
        """Crea regla de palabra."""
        from laim_web.adapters.laim_api_client import laim_forum_admin_create_word_rule

        if not self.forum_admin_word_palabra.strip():
            self.forum_admin_message = "Indique la palabra."
            return
        access, session = self._forum_auth_tokens()
        result = laim_forum_admin_create_word_rule(
            {
                "palabra": self.forum_admin_word_palabra.strip(),
                "accion": self.forum_admin_word_accion.strip() or "warn",
                "mensaje": self.forum_admin_word_mensaje.strip(),
                "activo": True,
            },
            access,
            session,
        )
        self.forum_admin_message = (
            "Regla creada." if result.get("success") else result.get("error", "Error")
        )
        if result.get("success"):
            self.forum_load_admin_extended()

    @forum_event
    def forum_admin_delete_word_rule(self, rule_id: int) -> None:
        from laim_web.adapters.laim_api_client import laim_forum_admin_delete_word_rule

        access, session = self._forum_auth_tokens()
        laim_forum_admin_delete_word_rule(rule_id, access, session)
        self.forum_load_admin_extended()

    @forum_event
    def forum_admin_save_allowed_url(self) -> None:
        from laim_web.adapters.laim_api_client import laim_forum_admin_create_allowed_url

        if not self.forum_admin_url_dominio.strip():
            self.forum_admin_message = "Indique el dominio."
            return
        access, session = self._forum_auth_tokens()
        result = laim_forum_admin_create_allowed_url(
            {
                "dominio": self.forum_admin_url_dominio.strip(),
                "descripcion": self.forum_admin_url_descripcion.strip(),
                "activo": True,
            },
            access,
            session,
        )
        self.forum_admin_message = (
            "Dominio añadido." if result.get("success") else result.get("error", "Error")
        )
        if result.get("success"):
            self.forum_load_admin_extended()

    @forum_event
    def forum_admin_delete_allowed_url(self, url_id: int) -> None:
        from laim_web.adapters.laim_api_client import laim_forum_admin_delete_allowed_url

        access, session = self._forum_auth_tokens()
        laim_forum_admin_delete_allowed_url(url_id, access, session)
        self.forum_load_admin_extended()

    @forum_event
    def forum_admin_assign_moderator(self) -> None:
        from laim_web.adapters.laim_api_client import laim_forum_admin_assign_moderator

        if self.forum_admin_mod_user_id <= 0 or not self.forum_admin_mod_subcategory_id.strip():
            self.forum_admin_message = "Usuario y subcategoría obligatorios."
            return
        access, session = self._forum_auth_tokens()
        result = laim_forum_admin_assign_moderator(
            {
                "user_id": self.forum_admin_mod_user_id,
                "user_name": self.forum_admin_mod_user_name.strip() or f"user_{self.forum_admin_mod_user_id}",
                "subcategory_id": self.forum_admin_mod_subcategory_id.strip(),
            },
            access,
            session,
        )
        self.forum_admin_message = (
            "Moderador asignado." if result.get("success") else result.get("error", "Error")
        )
        if result.get("success"):
            self.forum_load_admin_extended()

    @forum_event
    def forum_admin_deactivate_moderator(self, moderator_id: int) -> None:
        from laim_web.adapters.laim_api_client import laim_forum_admin_deactivate_moderator

        access, session = self._forum_auth_tokens()
        laim_forum_admin_deactivate_moderator(moderator_id, access, session)
        self.forum_load_admin_extended()

    @forum_event
    def forum_admin_add_catalog_avatar(self) -> None:
        """Registra imagen de catálogo ya subida."""
        from laim_web.adapters.laim_api_client import laim_forum_add_avatar_catalog

        if self.forum_admin_avatar_image_id <= 0 or not self.forum_admin_avatar_label.strip():
            self.forum_admin_message = "Image ID y etiqueta obligatorios."
            return
        access, session = self._forum_auth_tokens()
        result = laim_forum_add_avatar_catalog(
            {
                "image_id": self.forum_admin_avatar_image_id,
                "label": self.forum_admin_avatar_label.strip(),
                "is_default": False,
                "sort_order": 0,
            },
            access,
            session,
        )
        self.forum_admin_message = (
            "Avatar de catálogo añadido."
            if result.get("success")
            else result.get("error", "Error")
        )
        if result.get("success"):
            self.forum_load_admin_extended()

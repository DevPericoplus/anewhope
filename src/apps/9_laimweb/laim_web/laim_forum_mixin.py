"""Mixin de estado Reflex para el foro LAIM Web."""

from __future__ import annotations

from typing import Any

import reflex as rx
from reflex.event import event

EventHandlerReturn = Any


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

    _FORUM_ATTACHMENT_SCRIPT = """
(() => {
  const inputId = window.__forum_attachment_input_id || 'forum_thread_file_input';
  const input = document.getElementById(inputId);
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
          target: inputId.indexOf('reply') >= 0 ? 'reply' : 'thread',
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
    @event
    def forum_guard_auth(self) -> EventHandlerReturn:
        """Redirige al inicio si no hay sesión."""
        if not self.is_logged_in:
            return rx.redirect("/")
        return None

    @event
    def forum_on_page_load(self) -> EventHandlerReturn:
        """Carga inicial del foro principal."""
        if not self.is_logged_in:
            return rx.redirect("/")
        self.forum_error = ""
        self.forum_load_catalog()
        self.forum_poll_notifications()
        if self.forum_active_thread_id > 0:
            self.forum_open_thread(self.forum_active_thread_id)
        from laim_web.laim_state import LaimWebState

        handlers: list[Any] = []
        if self.is_logged_in and self.session_token and not self._token_renewal_running:
            self._token_renewal_running = True
            handlers.append(LaimWebState.auto_renew_tokens_loop)
        if not self._forum_poll_running:
            self._forum_poll_running = True
            handlers.append(LaimWebState.forum_poll_loop)
        if len(handlers) == 1:
            return handlers[0]
        if len(handlers) == 2:
            return handlers[0]
        return None

    @event
    def forum_my_threads_on_load(self) -> EventHandlerReturn:
        """Carga página mis hilos."""
        if not self.is_logged_in:
            return rx.redirect("/")
        self.forum_load_my_threads()
        return None

    @event
    def forum_my_posts_on_load(self) -> EventHandlerReturn:
        """Carga página mis respuestas."""
        if not self.is_logged_in:
            return rx.redirect("/")
        self.forum_load_my_posts()
        return None

    @event
    def forum_admin_on_load(self) -> EventHandlerReturn:
        """Carga panel admin del foro."""
        if not self.is_logged_in:
            return rx.redirect("/")
        if not self.is_laim_admin:
            return rx.redirect("/foro")
        self.forum_load_admin_panel()
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

    @event
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

    @event
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

    @event
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

    @event
    def forum_close_thread(self) -> None:
        """Cierra vista de hilo."""
        self.forum_active_thread_id = 0
        self.forum_thread_title = ""
        self.forum_thread_body = ""
        self.forum_posts = []
        self.forum_reply_body = ""
        self.forum_reply_image_ids = []

    @event
    def forum_refresh(self) -> None:
        """Refresca hilos o hilo activo."""
        if self.forum_active_thread_id > 0:
            self.forum_open_thread(self.forum_active_thread_id)
        else:
            self.forum_load_threads()

    @event
    def forum_toggle_new_thread(self) -> None:
        """Abre/cierra formulario de nuevo hilo."""
        self.forum_new_thread_open = not self.forum_new_thread_open
        if not self.forum_new_thread_open:
            self.forum_new_title = ""
            self.forum_new_body = ""
            self.forum_new_prefix_id = ""
            self.forum_new_thread_image_ids = []

    @event
    def forum_set_new_title(self, value: str) -> None:
        self.forum_new_title = value

    @event
    def forum_set_new_body(self, value: str) -> None:
        self.forum_new_body = value

    @event
    def forum_set_new_prefix(self, value: str) -> None:
        self.forum_new_prefix_id = value

    @event
    def forum_set_reply_body(self, value: str) -> None:
        self.forum_reply_body = value

    @event
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

    @event
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

    @event
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

    @event
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

    @event
    def forum_admin_set_category_id(self, value: str) -> None:
        self.forum_admin_category_id = value

    @event
    def forum_admin_set_category_name(self, value: str) -> None:
        self.forum_admin_category_name = value

    @event
    def forum_admin_set_category_desc(self, value: str) -> None:
        self.forum_admin_category_desc = value

    @event
    def forum_admin_set_subcategory_id(self, value: str) -> None:
        self.forum_admin_subcategory_id = value

    @event
    def forum_admin_set_subcategory_name(self, value: str) -> None:
        self.forum_admin_subcategory_name = value

    @event
    def forum_admin_set_subcategory_desc(self, value: str) -> None:
        self.forum_admin_subcategory_desc = value

    @event
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

    @event
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

    @event
    def forum_preview_image(self, image_id: int) -> None:
        """Carga imagen adjunta como data URL."""
        from laim_web.adapters.laim_api_client import laim_forum_get_image_data_url

        access, session = self._forum_auth_tokens()
        self.forum_preview_image_url = laim_forum_get_image_data_url(
            image_id, access, session
        )

    @event
    def forum_close_image_preview(self) -> None:
        self.forum_preview_image_url = ""

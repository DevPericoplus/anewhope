"""Mixin de estado Reflex para el foro LAIM Web."""

from __future__ import annotations

from typing import Any

import reflex as rx
from reflex.event import event

EventHandlerReturn = Any

# Reflex 0.8+ solo registra @event en métodos del State, no en mixins.
FORUM_EVENT_HANDLER_NAMES: list[str] = []

# Previews del catálogo: assets estáticos empaquetados con laimweb (iconos con dibujo).
# El image_id sigue viniendo del backend para guardar la selección del usuario.
_CATALOG_AVATAR_STATIC_URLS: dict[str, str] = {
    "Terminal": "/forum_avatars/avatar_01_terminal.png?v=2",
    "Cipher": "/forum_avatars/avatar_02_cipher.png?v=2",
    "Node": "/forum_avatars/avatar_03_node.png?v=2",
    "Pulse": "/forum_avatars/avatar_04_pulse.png?v=2",
    "Signal": "/forum_avatars/avatar_05_signal.png?v=2",
    "Vector": "/forum_avatars/avatar_06_vector.png?v=2",
    "Matrix": "/forum_avatars/avatar_07_matrix.png?v=2",
    "Proxy": "/forum_avatars/avatar_08_proxy.png?v=2",
}


def forum_event(func):
    """Decorador de eventos del foro que permite re-registro en LaimWebState."""
    FORUM_EVENT_HANDLER_NAMES.append(func.__name__)
    return event(func)


def forum_background_event(func):
    """Decorador para eventos background del foro (polling)."""
    FORUM_EVENT_HANDLER_NAMES.append(func.__name__)
    return rx.event(background=True)(func)


class LaimForumMixin(rx.State, mixin=True):
    """Variables y handlers del foro (mezclar con LaimWebState).

    Debe heredar de ``rx.State`` con ``mixin=True`` para que Reflex registre
    ``@rx.var`` y eventos del mixin en ``LaimWebState``.
    """

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
    forum_thread_body_display: str = ""
    forum_thread_closed: bool = False
    forum_thread_pinned: bool = False
    forum_thread_author: str = ""
    forum_thread_author_id: int = 0
    forum_thread_rating_avg: float = 0.0
    forum_thread_rating_count: int = 0
    forum_my_thread_rating: int = 0

    # Respuestas
    forum_posts: list[dict[str, Any]] = []
    forum_reply_body: str = ""

    # Edición de hilo / respuesta
    forum_edit_thread_open: bool = False
    forum_edit_thread_body: str = ""
    forum_edit_post_id: int = 0
    forum_edit_post_body: str = ""

    # Nuevo hilo
    forum_new_thread_open: bool = False
    forum_new_title: str = ""
    forum_new_body: str = ""
    forum_new_prefix_id: str = ""

    # Mis hilos / respuestas
    forum_my_threads: list[dict[str, Any]] = []
    forum_my_posts: list[dict[str, Any]] = []

    # Admin
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
    forum_thread_attachments: list[dict[str, Any]] = []

    # Perfil de foro
    forum_profile_display_name: str = ""
    forum_profile_signature: str = ""
    forum_profile_avatar_id: int = 0
    forum_profile_avatar_preview_url: str = ""
    forum_my_avatar_preview_url: str = ""
    forum_thread_author_avatar_url: str = ""
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
    forum_admin_word_accion: str = "Amonestaciones"
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

    # Estadísticas admin
    forum_stats_dialog_open: bool = False
    forum_stats_loading: bool = False
    forum_stats_message: str = ""
    forum_stats_categorias: int = 0
    forum_stats_subcategorias: int = 0
    forum_stats_hilos: int = 0
    forum_stats_respuestas: int = 0
    forum_stats_valoraciones: int = 0
    forum_stats_valoracion_promedio: float = 0.0
    forum_stats_usuarios_activos: int = 0
    forum_stats_baneos_activos: int = 0
    forum_stats_infracciones_hoy: int = 0
    forum_stats_adjuntos: int = 0
    forum_stats_subcategory_rows: list[dict[str, Any]] = []
    forum_stats_top_users: list[dict[str, Any]] = []

    # Moderación
    forum_mod_logs: list[dict[str, Any]] = []
    forum_mod_bans: list[dict[str, Any]] = []
    forum_ban_user_id: int = 0
    forum_ban_motivo: str = ""
    forum_ban_expires_at: str = ""
    forum_mod_message: str = ""

    # Hub del servicio de foro (admin)
    forum_admin_view: str = "hub"
    forum_service_detail: str = "Comprobando estado del servicio..."
    forum_admin_subcategory_ban_seconds: str = "86400"
    forum_admin_subcategory_log_rotation: str = "weekly"
    forum_admin_logs_subcategory_id: str = ""
    forum_admin_logs_lines: list[dict[str, Any]] = []

    # Árbol de categorías/subcategorías
    forum_cat_tree_expanded: list[str] = []
    forum_cat_tree_nodes: list[dict[str, Any]] = []
    forum_cat_tree_rename_open: bool = False
    forum_cat_tree_rename_id: str = ""
    forum_cat_tree_rename_name: str = ""
    forum_cat_tree_rename_cat_id: str = ""
    forum_cat_tree_delete_open: bool = False
    forum_cat_tree_delete_id: str = ""
    forum_cat_tree_delete_name: str = ""
    forum_cat_tree_delete_is_cat: bool = False
    forum_cat_tree_add_sub_open: bool = False
    forum_cat_tree_add_sub_cat_id: str = ""
    forum_cat_tree_add_sub_id: str = ""
    forum_cat_tree_add_sub_name: str = ""
    forum_cat_tree_add_sub_desc: str = ""

    forum_rule_action_options: list[str] = [
        "Agradecimientos",
        "Amonestaciones",
        "Sugerencias",
        "Ban",
        "Kick",
    ]

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
    def forum_can_vote_thread(self) -> bool:
        """True si el usuario puede valorar el hilo abierto."""
        if not self.is_logged_in or self.forum_active_thread_id <= 0:
            return False
        if self.forum_thread_author_id <= 0:
            return False
        return self.user_id != self.forum_thread_author_id

    @rx.var
    def forum_is_thread_author(self) -> bool:
        """True si el usuario logueado es el autor del hilo abierto."""
        if not self.is_logged_in or self.forum_active_thread_id <= 0:
            return False
        if self.forum_thread_author_id <= 0:
            return False
        return self.user_id == self.forum_thread_author_id

    @rx.var
    def forum_thread_rating_summary(self) -> str:
        """Texto resumen de valoraciones del hilo."""
        avg = self.forum_thread_rating_avg
        count = self.forum_thread_rating_count
        avg_text = f"{avg:.1f}".replace(".", ",")
        if count == 1:
            return f"{avg_text} · 1 valoración"
        return f"{avg_text} · {count} valoraciones"

    @rx.var
    def forum_my_thread_rating_label(self) -> str:
        """Etiqueta de la valoración propia en el hilo."""
        if self.forum_my_thread_rating <= 0:
            return ""
        return f"Tu valoración: {self.forum_my_thread_rating}/5"

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
    def forum_has_avatar_catalog(self) -> bool:
        """True si hay avatares disponibles en el catálogo."""
        return len(self.forum_avatar_catalog) > 0

    @rx.var
    def forum_has_thread_author_avatar(self) -> bool:
        """True si hay URL de avatar para el autor del hilo activo."""
        return self.forum_thread_author_avatar_url != ""

    @rx.var
    def forum_has_profile_avatar(self) -> bool:
        """True si el perfil tiene avatar asignado con vista previa."""
        return self.forum_profile_avatar_preview_url != ""

    @rx.var
    def forum_has_prefixes(self) -> bool:
        """True si hay prefijos disponibles para nuevos hilos."""
        return len(self.forum_prefixes) > 0

    @rx.var
    def forum_category_ids(self) -> list[str]:
        """IDs de categorías para selectores del foro."""
        return [str(c.get("id", "")) for c in self.forum_categories if c.get("id")]

    @rx.var
    def forum_subcategory_ids(self) -> list[str]:
        """IDs de subcategorías visibles para la categoría activa."""
        active = self.forum_selected_category_id
        items: list[str] = []
        for sub in self.forum_subcategories:
            sub_id = str(sub.get("id", ""))
            if not sub_id:
                continue
            parent = str(sub.get("categoria_id", sub.get("category_id", "")))
            if not active or parent == active:
                items.append(sub_id)
        return items

    @rx.var
    def forum_category_select_labels(self) -> list[str]:
        """Etiquetas legibles para el desplegable de categorías."""
        return [
            str(c.get("nombre") or c.get("id", ""))
            for c in self.forum_categories
            if c.get("id")
        ]

    @rx.var
    def forum_subcategory_select_labels(self) -> list[str]:
        """Etiquetas legibles para el desplegable de subcategorías."""
        active = self.forum_selected_category_id
        labels: list[str] = []
        for sub in self.forum_subcategories:
            sub_id = str(sub.get("id", ""))
            if not sub_id:
                continue
            parent = str(sub.get("categoria_id", sub.get("category_id", "")))
            if not active or parent == active:
                labels.append(str(sub.get("nombre") or sub_id))
        return labels

    @rx.var
    def forum_selected_category_label(self) -> str:
        """Nombre visible de la categoría seleccionada."""
        for category in self.forum_categories:
            if str(category.get("id", "")) == self.forum_selected_category_id:
                return str(category.get("nombre") or category.get("id", ""))
        return ""

    @rx.var
    def forum_selected_subcategory_label(self) -> str:
        """Nombre visible de la subcategoría seleccionada."""
        for subcategory in self.forum_subcategories:
            if str(subcategory.get("id", "")) == self.forum_selected_subcategory_id:
                return str(subcategory.get("nombre") or subcategory.get("id", ""))
        return ""

    @rx.var
    def forum_thread_has_attachments(self) -> bool:
        """True si el hilo activo tiene adjuntos."""
        return len(self.forum_thread_attachments) > 0

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
        self._forum_sync_my_avatar_preview()
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
        self.forum_admin_view = "hub"
        self.forum_service_refresh_health()
        self.forum_load_admin_panel()
        self.forum_load_admin_extended()
        return None

    def forum_service_refresh_health(self) -> None:
        """Actualiza badge y detalle del servicio de foro."""
        from laim_web.adapters.laim_api_client import laim_forum_health

        health = laim_forum_health()
        threads = int(health.get("threads", health.get("hilos", 0)) or 0)
        activo = bool(
            health.get("activo", health.get("ok", health.get("success", False)))
        )
        self.forum_service_active = activo
        if activo:
            self.forum_service_detail = (
                f"API operativa · {threads} hilo(s) registrados"
            )
        else:
            detail = str(health.get("error", "")).strip()
            self.forum_service_detail = (
                detail if detail else "Servicio detenido o no disponible"
            )

    @forum_event
    def forum_admin_go_hub(self) -> None:
        """Vuelve al hub del servicio de foro."""
        self.forum_admin_view = "hub"
        self.forum_admin_message = ""
        self.forum_service_refresh_health()

    @forum_event
    def forum_admin_open_view(self, view: str) -> None:
        """Abre una vista del panel admin del foro."""
        self.forum_admin_view = view
        self.forum_admin_message = ""

        tab_map = {
            "prefixes": "prefixes",
            "moderators": "moderators",
            "permissions": "settings",
            "word-rules": "word-rules",
            "allowed-urls": "allowed-urls",
            "avatars": "avatars",
        }
        if view in tab_map:
            self.forum_admin_tab = tab_map[view]
            self.forum_load_admin_extended()
        elif view in ("categories", "subcategories"):
            self.forum_load_admin_panel()
        elif view == "bans":
            self.forum_load_admin_bans()
        elif view == "logs":
            self.forum_load_admin_logs()
        elif view == "config_general":
            self.forum_service_refresh_health()
        elif view == "stats":
            self.forum_open_stats_dialog()
            self.forum_admin_view = "hub"

    @forum_event
    def forum_service_reload_config(self) -> None:
        """Recarga estado del servicio (equivalente a Radikal reload_config)."""
        from laim_web.adapters.laim_api_client import laim_forum_admin_reload_config

        access, session = self._forum_auth_tokens()
        result = laim_forum_admin_reload_config(access, session)
        if result.get("success"):
            self.forum_service_refresh_health()
            self.forum_admin_message = "Estado del servicio actualizado."
        else:
            self.forum_service_refresh_health()
            self.forum_admin_message = result.get(
                "error", "No se pudo actualizar el estado."
            )

    def forum_load_admin_bans(self) -> None:
        """Carga baneos activos para el panel admin."""
        from laim_web.adapters.laim_api_client import laim_forum_admin_list_bans

        access, session = self._forum_auth_tokens()
        result = laim_forum_admin_list_bans(access, session)
        if result.get("success"):
            self.forum_mod_bans = result.get("items", [])
        else:
            self.forum_mod_bans = []
            self.forum_admin_message = result.get(
                "error", "No se pudieron cargar baneos activos."
            )

    @forum_event
    def forum_admin_set_logs_subcategory_id(self, value: str) -> None:
        self.forum_admin_logs_subcategory_id = value

    def forum_load_admin_logs(self) -> None:
        """Carga logs globales de moderación."""
        from laim_web.adapters.laim_api_client import laim_forum_admin_logs

        access, session = self._forum_auth_tokens()
        sub_id = self.forum_admin_logs_subcategory_id.strip() or None
        result = laim_forum_admin_logs(
            access, session, subcategory_id=sub_id, limit=200
        )
        if not result.get("success"):
            self.forum_admin_logs_lines = []
            self.forum_admin_message = result.get("error", "No se pudieron cargar logs.")
            return

        lines: list[dict[str, Any]] = []
        for item in result.get("items", []):
            if not isinstance(item, dict):
                continue
            created = str(item.get("created_at", ""))[:19]
            sub = str(item.get("subcategory_id", ""))
            event = str(item.get("event_type", ""))
            message = str(item.get("message", ""))
            lines.append(
                {
                    "line": f"[{created}] [{sub}] {event}: {message}",
                }
            )
        self.forum_admin_logs_lines = lines

    @forum_event
    def forum_admin_set_subcategory_ban_seconds(self, value: str) -> None:
        self.forum_admin_subcategory_ban_seconds = value

    @forum_event
    def forum_admin_set_subcategory_log_rotation(self, value: str) -> None:
        self.forum_admin_subcategory_log_rotation = value

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
                self.forum_posts = self._forum_process_posts(
                    posts_result.get("items", []),
                    access,
                    session,
                )

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

    def _forum_apply_category(self, category_id: str) -> None:
        """Aplica selección de categoría y recarga subcategorías."""
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
    def forum_select_category(self, category_id: str) -> None:
        """Selecciona categoría y recarga subcategorías."""
        self._forum_apply_category(category_id)

    @forum_event
    def forum_select_category_by_label(self, label: str) -> None:
        """Selecciona categoría desde el desplegable (etiqueta visible)."""
        for category in self.forum_categories:
            nombre = str(category.get("nombre") or category.get("id", ""))
            category_id = str(category.get("id", ""))
            if label in (nombre, category_id):
                self._forum_apply_category(category_id)
                return

    def _forum_apply_subcategory(self, subcategory_id: str) -> None:
        """Aplica selección de subcategoría y carga hilos."""
        self.forum_selected_subcategory_id = subcategory_id
        self.forum_active_thread_id = 0
        self.forum_posts = []
        self.forum_load_threads()

    @forum_event
    def forum_select_subcategory(self, subcategory_id: str) -> None:
        """Selecciona subcategoría y lista hilos."""
        self._forum_apply_subcategory(subcategory_id)

    @forum_event
    def forum_select_subcategory_by_label(self, label: str) -> None:
        """Selecciona subcategoría desde el desplegable (etiqueta visible)."""
        active = self.forum_selected_category_id
        for subcategory in self.forum_subcategories:
            nombre = str(subcategory.get("nombre") or subcategory.get("id", ""))
            subcategory_id = str(subcategory.get("id", ""))
            if label not in (nombre, subcategory_id):
                continue
            parent = str(
                subcategory.get("categoria_id", subcategory.get("category_id", ""))
            )
            if active and parent != active:
                continue
            self._forum_apply_subcategory(subcategory_id)
            return

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
            items = result.get("items", [])
            normalized: list[dict[str, Any]] = []
            for item in items:
                row = dict(item)
                row.setdefault("respuestas_count", row.get("posts_count", 0))
                row.setdefault("actualizado", row.get("updated_at", row.get("creado", "")))
                normalized.append(row)
            self.forum_threads = normalized
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
        raw_body = str(thread.get("cuerpo_md", ""))
        self.forum_thread_body = raw_body
        from laim_web.components.forum_message_viewer import enrich_forum_message_markdown

        self.forum_thread_body_display = enrich_forum_message_markdown(raw_body)
        self.forum_thread_closed = bool(thread.get("cerrado"))
        self.forum_thread_pinned = bool(thread.get("fijado"))
        self.forum_thread_author = str(thread.get("user_name", ""))
        self.forum_thread_author_id = int(thread.get("user_id", 0))
        self.forum_thread_rating_avg = float(thread.get("rating_avg") or 0)
        self.forum_thread_rating_count = int(thread.get("rating_count") or 0)
        my_rating = thread.get("my_rating")
        self.forum_my_thread_rating = int(my_rating) if my_rating is not None else 0
        self._forum_load_thread_author_avatar(thread, access, session)
        raw_images = thread.get("image_ids", [])
        self.forum_thread_image_ids = [
            int(i) for i in raw_images if i is not None
        ] if isinstance(raw_images, list) else []
        self.forum_thread_attachments = self._forum_build_attachments_with_thumbs(
            self.forum_thread_image_ids, access, session,
        )

        posts_result = laim_forum_list_posts(thread_id, access, session)
        if posts_result.get("success"):
            raw_posts = posts_result.get("items", [])
            self.forum_posts = self._forum_process_posts(raw_posts, access, session)
        else:
            self.forum_posts = []
            self._forum_set_error(posts_result.get("error", "Error al cargar respuestas"))

    @forum_event
    def forum_close_thread(self) -> None:
        """Cierra vista de hilo."""
        self.forum_active_thread_id = 0
        self.forum_thread_title = ""
        self.forum_thread_body = ""
        self.forum_thread_body_display = ""
        self.forum_thread_author_avatar_url = ""
        self.forum_thread_rating_avg = 0.0
        self.forum_thread_rating_count = 0
        self.forum_my_thread_rating = 0
        self.forum_posts = []
        self.forum_reply_body = ""
        self.forum_reply_image_ids = []
        self.forum_thread_image_ids = []
        self.forum_thread_attachments = []
        self.forum_edit_thread_open = False
        self.forum_edit_thread_body = ""
        self.forum_edit_post_id = 0
        self.forum_edit_post_body = ""

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
    def forum_open_new_thread(self) -> None:
        """Abre el diálogo de nuevo hilo."""
        self.forum_new_thread_open = True

    @forum_event
    def forum_on_new_thread_dialog_change(self, open: bool) -> None:
        """Sincroniza cierre del diálogo de nuevo hilo."""
        self.forum_new_thread_open = open
        if not open:
            self.forum_new_title = ""
            self.forum_new_body = ""
            self.forum_new_prefix_id = ""
            self.forum_new_thread_image_ids = []

    @forum_event
    def forum_close_new_thread(self) -> None:
        """Cierra el diálogo de nuevo hilo."""
        self.forum_new_thread_open = False
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

    # --- Edición de hilo ---

    @forum_event
    def forum_start_edit_thread(self) -> None:
        """Abre el formulario de edición del cuerpo del hilo."""
        self.forum_edit_thread_body = self.forum_thread_body
        self.forum_edit_thread_open = True

    @forum_event
    def forum_cancel_edit_thread(self) -> None:
        """Cancela la edición del hilo."""
        self.forum_edit_thread_open = False
        self.forum_edit_thread_body = ""

    @forum_event
    def forum_set_edit_thread_body(self, value: str) -> None:
        self.forum_edit_thread_body = value

    @forum_event
    def forum_save_edit_thread(self) -> None:
        """Guarda la edición del cuerpo del hilo."""
        from laim_web.adapters.laim_api_client import laim_forum_update_thread

        new_body = self.forum_edit_thread_body.strip()
        if not new_body:
            self._forum_set_error("El contenido no puede estar vacío.")
            return

        access, session = self._forum_auth_tokens()
        result = laim_forum_update_thread(
            self.forum_active_thread_id,
            {"cuerpo_md": new_body},
            access,
            session,
        )
        if result.get("success") or (isinstance(result, dict) and "error" not in result):
            self.forum_edit_thread_open = False
            self.forum_edit_thread_body = ""
            self.forum_error = ""
            self.forum_open_thread(self.forum_active_thread_id)
        else:
            self._forum_set_error(result.get("error", "No se pudo guardar la edición"))

    # --- Edición de respuesta (post) ---

    @forum_event
    def forum_start_edit_post(self, post_id: int, current_body: str) -> None:
        """Abre la edición inline de una respuesta."""
        self.forum_edit_post_id = post_id
        self.forum_edit_post_body = current_body

    @forum_event
    def forum_cancel_edit_post(self) -> None:
        """Cancela la edición de la respuesta."""
        self.forum_edit_post_id = 0
        self.forum_edit_post_body = ""

    @forum_event
    def forum_set_edit_post_body(self, value: str) -> None:
        self.forum_edit_post_body = value

    @forum_event
    def forum_save_edit_post(self) -> None:
        """Guarda la edición de una respuesta."""
        from laim_web.adapters.laim_api_client import laim_forum_update_post

        new_body = self.forum_edit_post_body.strip()
        if not new_body:
            self._forum_set_error("El contenido no puede estar vacío.")
            return

        access, session = self._forum_auth_tokens()
        result = laim_forum_update_post(
            self.forum_edit_post_id,
            {"cuerpo_md": new_body},
            access,
            session,
        )
        if result.get("success") or (isinstance(result, dict) and "error" not in result):
            self.forum_edit_post_id = 0
            self.forum_edit_post_body = ""
            self.forum_error = ""
            self.forum_open_thread(self.forum_active_thread_id)
        else:
            self._forum_set_error(result.get("error", "No se pudo guardar la edición"))

    @forum_event
    def forum_rate_thread(self, rating: int) -> None:
        """Valora el hilo abierto (1-5, una valoración por usuario)."""
        if self.forum_active_thread_id <= 0:
            return
        from laim_web.adapters.laim_api_client import laim_forum_rate_thread

        access, session = self._forum_auth_tokens()
        result = laim_forum_rate_thread(
            self.forum_active_thread_id, rating, access, session
        )
        if not result.get("success"):
            self._forum_set_error(result.get("error", "No se pudo valorar el hilo"))
            return

        thread = result.get("thread") or {}
        self.forum_thread_rating_avg = float(thread.get("rating_avg") or 0)
        self.forum_thread_rating_count = int(thread.get("rating_count") or 0)
        my_rating = result.get("my_rating", thread.get("my_rating"))
        self.forum_my_thread_rating = int(my_rating) if my_rating is not None else rating
        self.forum_error = ""

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
            from laim_web.components.forum_message_viewer import enrich_forum_message_row

            self.forum_my_threads = [
                enrich_forum_message_row(item) for item in result.get("items", [])
            ]
        else:
            self._forum_set_error(result.get("error", "Error al cargar mis hilos"))

    def forum_load_my_posts(self) -> None:
        """Carga respuestas del usuario."""
        from laim_web.adapters.laim_api_client import laim_forum_my_posts

        access, session = self._forum_auth_tokens()
        result = laim_forum_my_posts(access, session)
        if result.get("success"):
            from laim_web.components.forum_message_viewer import enrich_forum_message_row

            self.forum_my_posts = [
                enrich_forum_message_row(item) for item in result.get("items", [])
            ]
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
            laim_forum_list_categories,
            laim_forum_list_subcategories,
        )

        access, session = self._forum_auth_tokens()
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

        self._forum_rebuild_cat_tree()

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
        try:
            ban_seconds = max(60, int(self.forum_admin_subcategory_ban_seconds.strip()))
        except ValueError:
            ban_seconds = 86400
        log_rotation = self.forum_admin_subcategory_log_rotation.strip() or "weekly"
        if log_rotation not in ("weekly", "daily", "none"):
            log_rotation = "weekly"

        result = laim_forum_upsert_subcategory(
            {
                "id": self.forum_admin_subcategory_id.strip(),
                "categoria_id": self.forum_selected_category_id,
                "nombre": self.forum_admin_subcategory_name.strip(),
                "descripcion": self.forum_admin_subcategory_desc.strip(),
                "orden": 0,
                "activa": True,
                "ban_seconds": ban_seconds,
                "log_rotation": log_rotation,
            },
            access,
            session,
        )
        if result.get("success"):
            self.forum_admin_message = "Subcategoría guardada."
            self.forum_load_admin_panel()
            self._forum_rebuild_cat_tree()
        else:
            self.forum_admin_message = result.get("error", "Error al guardar subcategoría")

    # ── Árbol de categorías / subcategorías ──────────────────────────

    def _forum_rebuild_cat_tree(self) -> None:
        """Reconstruye nodos del árbol a partir de categorías y subcategorías cargadas."""
        from laim_web.adapters.laim_api_client import laim_forum_list_subcategories

        access, session = self._forum_auth_tokens()
        nodes: list[dict[str, Any]] = []

        for cat in self.forum_categories:
            cat_id = str(cat.get("id", ""))
            cat_name = str(cat.get("nombre") or cat_id)
            is_expanded = cat_id in self.forum_cat_tree_expanded

            sub_result = laim_forum_list_subcategories(access, session, cat_id)
            subs = sub_result.get("items", []) if sub_result.get("success") else []
            total_threads = 0

            children: list[dict[str, Any]] = []
            for sub in subs:
                sub_id = str(sub.get("id", ""))
                sub_name = str(sub.get("nombre") or sub_id)
                t_count = int(sub.get("hilos", 0) or sub.get("threads_count", 0) or 0)
                total_threads += t_count
                children.append({
                    "id": sub_id,
                    "name": sub_name,
                    "thread_count": t_count,
                    "cat_id": cat_id,
                    "is_category": False,
                })

            nodes.append({
                "id": cat_id,
                "name": cat_name,
                "thread_count": total_threads,
                "is_expanded": is_expanded,
                "has_children": len(children) > 0,
                "is_category": True,
                "children": children,
            })

        self.forum_cat_tree_nodes = nodes

    @forum_event
    def forum_cat_tree_toggle(self, cat_id: str) -> None:
        """Expande o contrae una categoría en el árbol."""
        expanded = list(self.forum_cat_tree_expanded)
        if cat_id in expanded:
            expanded.remove(cat_id)
        else:
            expanded.append(cat_id)
        self.forum_cat_tree_expanded = expanded
        self._forum_rebuild_cat_tree()

    @forum_event
    def forum_cat_tree_open_add_sub(self, cat_id: str) -> None:
        """Abre diálogo para crear subcategoría en una categoría."""
        self.forum_cat_tree_add_sub_open = True
        self.forum_cat_tree_add_sub_cat_id = cat_id
        self.forum_cat_tree_add_sub_id = ""
        self.forum_cat_tree_add_sub_name = ""
        self.forum_cat_tree_add_sub_desc = ""

    @forum_event
    def forum_cat_tree_close_add_sub(self) -> None:
        self.forum_cat_tree_add_sub_open = False

    @forum_event
    def forum_cat_tree_set_add_sub_id(self, value: str) -> None:
        self.forum_cat_tree_add_sub_id = value

    @forum_event
    def forum_cat_tree_set_add_sub_name(self, value: str) -> None:
        self.forum_cat_tree_add_sub_name = value

    @forum_event
    def forum_cat_tree_set_add_sub_desc(self, value: str) -> None:
        self.forum_cat_tree_add_sub_desc = value

    @forum_event
    def forum_cat_tree_save_new_sub(self) -> None:
        """Guarda nueva subcategoría desde el diálogo del árbol."""
        from laim_web.adapters.laim_api_client import laim_forum_upsert_subcategory

        sub_id = self.forum_cat_tree_add_sub_id.strip()
        sub_name = self.forum_cat_tree_add_sub_name.strip()
        if not sub_id or not sub_name:
            self.forum_admin_message = "ID y nombre son obligatorios."
            return

        access, session = self._forum_auth_tokens()
        result = laim_forum_upsert_subcategory(
            {
                "id": sub_id,
                "categoria_id": self.forum_cat_tree_add_sub_cat_id,
                "nombre": sub_name,
                "descripcion": self.forum_cat_tree_add_sub_desc.strip(),
                "orden": 0,
                "activa": True,
                "ban_seconds": 86400,
                "log_rotation": "weekly",
            },
            access,
            session,
        )
        if result.get("success") or (isinstance(result, dict) and "error" not in result):
            self.forum_admin_message = f"Subcategoría «{sub_name}» creada."
            self.forum_cat_tree_add_sub_open = False
            self.forum_load_admin_panel()
            if self.forum_cat_tree_add_sub_cat_id not in self.forum_cat_tree_expanded:
                self.forum_cat_tree_expanded = [
                    *self.forum_cat_tree_expanded,
                    self.forum_cat_tree_add_sub_cat_id,
                ]
            self._forum_rebuild_cat_tree()
        else:
            self.forum_admin_message = result.get("error", "Error al crear subcategoría")
            self.forum_cat_tree_add_sub_open = False

    @forum_event
    def forum_cat_tree_open_rename(self, sub_id: str, current_name: str, cat_id: str) -> None:
        """Abre diálogo para renombrar subcategoría."""
        self.forum_cat_tree_rename_open = True
        self.forum_cat_tree_rename_id = sub_id
        self.forum_cat_tree_rename_name = current_name
        self.forum_cat_tree_rename_cat_id = cat_id

    @forum_event
    def forum_cat_tree_close_rename(self) -> None:
        self.forum_cat_tree_rename_open = False

    @forum_event
    def forum_cat_tree_set_rename_name(self, value: str) -> None:
        self.forum_cat_tree_rename_name = value

    @forum_event
    def forum_cat_tree_save_rename(self) -> None:
        """Guarda el nuevo nombre de la subcategoría."""
        from laim_web.adapters.laim_api_client import laim_forum_upsert_subcategory

        new_name = self.forum_cat_tree_rename_name.strip()
        if not new_name:
            self.forum_admin_message = "El nombre no puede estar vacío."
            return

        access, session = self._forum_auth_tokens()
        result = laim_forum_upsert_subcategory(
            {
                "id": self.forum_cat_tree_rename_id,
                "categoria_id": self.forum_cat_tree_rename_cat_id,
                "nombre": new_name,
                "orden": 0,
                "activa": True,
            },
            access,
            session,
        )
        if result.get("success") or (isinstance(result, dict) and "error" not in result):
            self.forum_admin_message = f"Subcategoría renombrada a «{new_name}»."
            self.forum_cat_tree_rename_open = False
            self.forum_load_admin_panel()
            self._forum_rebuild_cat_tree()
        else:
            self.forum_admin_message = result.get("error", "Error al renombrar")
            self.forum_cat_tree_rename_open = False

    @forum_event
    def forum_cat_tree_open_delete(self, item_id: str, item_name: str, is_cat: bool) -> None:
        """Abre diálogo de confirmación para eliminar categoría o subcategoría."""
        self.forum_cat_tree_delete_open = True
        self.forum_cat_tree_delete_id = item_id
        self.forum_cat_tree_delete_name = item_name
        self.forum_cat_tree_delete_is_cat = is_cat

    @forum_event
    def forum_cat_tree_close_delete(self) -> None:
        self.forum_cat_tree_delete_open = False

    @forum_event
    def forum_cat_tree_confirm_delete(self) -> None:
        """Ejecuta la eliminación confirmada."""
        from laim_web.adapters.laim_api_client import (
            laim_forum_delete_category,
            laim_forum_delete_subcategory,
        )

        access, session = self._forum_auth_tokens()
        if self.forum_cat_tree_delete_is_cat:
            result = laim_forum_delete_category(
                self.forum_cat_tree_delete_id, access, session
            )
        else:
            result = laim_forum_delete_subcategory(
                self.forum_cat_tree_delete_id, access, session
            )

        if result.get("success") or (isinstance(result, dict) and "error" not in result):
            label = "Categoría" if self.forum_cat_tree_delete_is_cat else "Subcategoría"
            self.forum_admin_message = f"{label} «{self.forum_cat_tree_delete_name}» eliminada."
            self.forum_cat_tree_delete_open = False
            self.forum_load_admin_panel()
            self._forum_rebuild_cat_tree()
        else:
            self.forum_admin_message = result.get("error", "Error al eliminar")
            self.forum_cat_tree_delete_open = False

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

    def _forum_static_url_for_catalog_label(self, label: str) -> str:
        """URL estática empaquetada para un label del catálogo."""
        clean = label.strip()
        if not clean:
            return ""
        return _CATALOG_AVATAR_STATIC_URLS.get(clean, "")

    def _forum_load_thread_author_avatar(
        self,
        thread: dict[str, Any],
        access_token: str,
        session_token: str,
    ) -> None:
        """Resuelve y asigna la vista previa del avatar del autor del hilo."""
        author_id = int(thread.get("user_id") or 0)
        avatar_id = int(thread.get("author_avatar_image_id") or 0)
        catalog_label = str(thread.get("author_avatar_catalog_label") or "")

        if author_id == self.user_id:
            from laim_web.adapters.laim_api_client import laim_forum_get_profile

            profile_result = laim_forum_get_profile(access_token, session_token)
            if profile_result.get("success"):
                profile = profile_result.get("profile", {})
                profile_avatar_id = int(profile.get("avatar_image_id") or 0)
                if profile_avatar_id > 0:
                    avatar_id = profile_avatar_id
                catalog_map = self._forum_build_catalog_preview_map(
                    access_token, session_token
                )
                preview = self._forum_resolve_avatar_preview_url(
                    avatar_id,
                    access_token,
                    session_token,
                    catalog_map=catalog_map,
                    catalog_label=catalog_label,
                )
                if preview:
                    self.forum_thread_author_avatar_url = preview
                    self.forum_my_avatar_preview_url = preview
                    return

        static_url = self._forum_static_url_for_catalog_label(catalog_label)
        if static_url:
            self.forum_thread_author_avatar_url = static_url
            return

        if avatar_id > 0:
            catalog_map = self._forum_build_catalog_preview_map(
                access_token, session_token
            )
            self.forum_thread_author_avatar_url = self._forum_resolve_avatar_preview_url(
                avatar_id,
                access_token,
                session_token,
                catalog_map=catalog_map,
            )
            return

        self.forum_thread_author_avatar_url = ""

    def _forum_catalog_static_url_by_image_id(self) -> dict[int, str]:
        """Mapa image_id → URL estática del catálogo empaquetado."""
        mapping: dict[int, str] = {}
        for item in self.forum_avatar_catalog:
            image_id = int(item.get("image_id") or 0)
            if image_id <= 0:
                continue
            label = str(item.get("label") or "")
            static_url = _CATALOG_AVATAR_STATIC_URLS.get(label, "")
            if static_url:
                mapping[image_id] = static_url
        return mapping

    def _forum_build_catalog_preview_map(
        self,
        access_token: str,
        session_token: str,
    ) -> dict[int, str]:
        """Construye mapa image_id → preview para avatares del catálogo."""
        from laim_web.adapters.laim_api_client import laim_forum_list_avatar_catalog

        mapping: dict[int, str] = {}
        catalog = laim_forum_list_avatar_catalog(access_token, session_token)
        if not catalog.get("success"):
            return mapping
        for item in catalog.get("items", []):
            image_id = int(item.get("image_id") or 0)
            if image_id <= 0:
                continue
            label = str(item.get("label") or "")
            static_url = _CATALOG_AVATAR_STATIC_URLS.get(label, "")
            if static_url:
                mapping[image_id] = static_url
        return mapping

    def _forum_resolve_avatar_preview_url(
        self,
        image_id: int,
        access_token: str,
        session_token: str,
        catalog_map: dict[int, str] | None = None,
        catalog_label: str = "",
    ) -> str:
        """Resuelve URL de vista previa para un avatar (catálogo o personalizado)."""
        if image_id <= 0:
            return ""

        static_from_label = self._forum_static_url_for_catalog_label(catalog_label)
        if static_from_label:
            return static_from_label

        static_from_catalog = self._forum_catalog_static_url_by_image_id().get(image_id)
        if static_from_catalog:
            return static_from_catalog

        if catalog_map and image_id in catalog_map:
            return catalog_map[image_id]

        for item in self.forum_avatar_catalog:
            if int(item.get("image_id") or 0) != image_id:
                continue
            preview = str(item.get("preview_url") or "")
            if preview:
                return preview

        from laim_web.adapters.laim_api_client import laim_forum_get_image_data_url

        return laim_forum_get_image_data_url(image_id, access_token, session_token)

    def _forum_apply_profile_from_api(
        self,
        profile: dict[str, Any],
        access_token: str,
        session_token: str,
    ) -> None:
        """Aplica datos de perfil devueltos por la API y refresca vista previa."""
        self.forum_profile_display_name = str(
            profile.get("forum_display_name") or profile.get("user_name") or ""
        )
        self.forum_profile_signature = str(profile.get("signature_md") or "")
        avatar_id = int(profile.get("avatar_image_id") or 0)
        self.forum_profile_avatar_id = avatar_id
        self.forum_profile_notify_mentions = bool(profile.get("notify_mentions", True))
        self.forum_profile_notify_replies = bool(profile.get("notify_replies", True))
        preview = self._forum_resolve_avatar_preview_url(
            avatar_id, access_token, session_token
        )
        self.forum_profile_avatar_preview_url = preview
        self.forum_my_avatar_preview_url = preview

    def _forum_process_posts(
        self,
        posts: list[dict[str, Any]],
        access_token: str,
        session_token: str,
    ) -> list[dict[str, Any]]:
        """Enriquece respuestas con avatar, miniaturas y markdown legible."""
        with_avatars = self._forum_enrich_posts_author_avatars(
            posts, access_token, session_token
        )
        with_thumbs = self._forum_enrich_posts_attachment_thumbs(
            with_avatars, access_token, session_token
        )
        return self._forum_enrich_posts_display(with_thumbs)

    def _forum_enrich_posts_attachment_thumbs(
        self,
        posts: list[dict[str, Any]],
        access_token: str,
        session_token: str,
    ) -> list[dict[str, Any]]:
        """Reemplaza image_ids por attachments con miniaturas pre-cargadas."""
        enriched: list[dict[str, Any]] = []
        for post in posts:
            row = dict(post)
            raw_ids = row.get("image_ids", [])
            ids = [int(i) for i in raw_ids if i is not None] if isinstance(raw_ids, list) else []
            row["attachments"] = self._forum_build_attachments_with_thumbs(
                ids, access_token, session_token,
            )
            enriched.append(row)
        return enriched

    @staticmethod
    def _forum_enrich_posts_display(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Prepara display_md y display_preview para mensajes del foro."""
        from laim_web.components.forum_message_viewer import enrich_forum_message_row

        return [enrich_forum_message_row(post) for post in posts]

    @staticmethod
    def _forum_build_attachments_with_thumbs(
        image_ids: list[int],
        access_token: str,
        session_token: str,
    ) -> list[dict[str, Any]]:
        """Convierte lista de image_ids en lista de dicts con miniatura pre-cargada."""
        from laim_web.adapters.laim_api_client import laim_forum_get_image_data_url

        attachments: list[dict[str, Any]] = []
        for img_id in image_ids:
            thumb_url = laim_forum_get_image_data_url(img_id, access_token, session_token)
            attachments.append({"id": img_id, "thumb_url": thumb_url})
        return attachments

    def _forum_enrich_posts_author_avatars(
        self,
        posts: list[dict[str, Any]],
        access_token: str,
        session_token: str,
    ) -> list[dict[str, Any]]:
        """Añade author_avatar_preview_url a cada respuesta del hilo."""
        catalog_map = self._forum_build_catalog_preview_map(access_token, session_token)
        preview_cache: dict[int, str] = dict(catalog_map)
        enriched: list[dict[str, Any]] = []

        for post in posts:
            row = dict(post)
            user_id = int(row.get("user_id") or 0)
            if user_id == self.user_id and self.forum_my_avatar_preview_url:
                row["author_avatar_preview_url"] = self.forum_my_avatar_preview_url
                enriched.append(row)
                continue

            avatar_id = int(row.get("author_avatar_image_id") or 0)
            catalog_label = str(row.get("author_avatar_catalog_label") or "")
            static_url = self._forum_static_url_for_catalog_label(catalog_label)
            if static_url:
                row["author_avatar_preview_url"] = static_url
                enriched.append(row)
                continue

            if avatar_id > 0 and avatar_id not in preview_cache:
                preview_cache[avatar_id] = self._forum_resolve_avatar_preview_url(
                    avatar_id,
                    access_token,
                    session_token,
                    catalog_map=catalog_map,
                )
            row["author_avatar_preview_url"] = preview_cache.get(avatar_id, "")
            enriched.append(row)
        return enriched

    def _forum_persist_avatar_selection(self, image_id: int) -> bool:
        """Persiste avatar seleccionado y actualiza estado local."""
        from laim_web.adapters.laim_api_client import laim_forum_update_profile

        if image_id <= 0:
            self._forum_set_error("Avatar no válido.")
            return False

        access, session = self._forum_auth_tokens()
        result = laim_forum_update_profile(
            {"avatar_image_id": image_id}, access, session
        )
        if not result.get("success"):
            self.forum_profile_message = ""
            self._forum_set_error(result.get("error", "No se pudo asignar el avatar."))
            return False

        profile = result.get("profile", {})
        if profile:
            self._forum_apply_profile_from_api(profile, access, session)
        else:
            self.forum_profile_avatar_id = image_id
            preview = self._forum_resolve_avatar_preview_url(image_id, access, session)
            self.forum_profile_avatar_preview_url = preview
            self.forum_my_avatar_preview_url = preview

        self.forum_profile_message = "Avatar actualizado."
        self.forum_error = ""
        return True

    def _forum_sync_my_avatar_preview(self) -> None:
        """Carga vista previa del avatar del usuario para mostrarla en el foro."""
        from laim_web.adapters.laim_api_client import laim_forum_get_profile

        access, session = self._forum_auth_tokens()
        if not access:
            return
        result = laim_forum_get_profile(access, session)
        if not result.get("success"):
            return
        profile = result.get("profile", {})
        avatar_id = int(profile.get("avatar_image_id") or 0)
        if avatar_id <= 0:
            self.forum_my_avatar_preview_url = ""
            return
        self.forum_my_avatar_preview_url = self._forum_resolve_avatar_preview_url(
            avatar_id, access, session
        )

    def _forum_enrich_avatar_catalog(
        self,
        items: list[dict[str, Any]],
        access_token: str,
        session_token: str,
    ) -> list[dict[str, Any]]:
        """Añade preview_url a cada entrada del catálogo."""
        from laim_web.adapters.laim_api_client import laim_forum_get_image_data_url

        enriched: list[dict[str, Any]] = []
        for item in items:
            row = dict(item)
            label = str(row.get("label") or "")
            static_url = _CATALOG_AVATAR_STATIC_URLS.get(label, "")
            if static_url:
                row["preview_url"] = static_url
            else:
                image_id = int(row.get("image_id") or 0)
                if image_id > 0:
                    row["preview_url"] = laim_forum_get_image_data_url(
                        image_id, access_token, session_token
                    )
                else:
                    row["preview_url"] = ""
            enriched.append(row)
        return enriched

    def forum_load_profile(self) -> None:
        """Carga perfil y catálogo de avatares."""
        from laim_web.adapters.laim_api_client import (
            laim_forum_get_profile,
            laim_forum_list_avatar_catalog,
        )

        access, session = self._forum_auth_tokens()
        catalog = laim_forum_list_avatar_catalog(access, session)
        if catalog.get("success"):
            self.forum_avatar_catalog = self._forum_enrich_avatar_catalog(
                catalog.get("items", []), access, session
            )

        profile_result = laim_forum_get_profile(access, session)
        if profile_result.get("success"):
            self._forum_apply_profile_from_api(
                profile_result.get("profile", {}), access, session
            )
        else:
            self._forum_set_error(profile_result.get("error", "Error al cargar perfil"))

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
        """Selecciona avatar del catálogo, persiste y refresca vista previa."""
        self.forum_profile_avatar_id = image_id
        self._forum_persist_avatar_selection(image_id)

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
            profile = result.get("profile", {})
            if profile:
                self._forum_apply_profile_from_api(profile, access, session)
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
            profile = update.get("profile", {})
            if profile:
                self._forum_apply_profile_from_api(profile, access, session)
            else:
                preview = self._forum_resolve_avatar_preview_url(
                    image_id, access, session
                )
                self.forum_profile_avatar_preview_url = preview
                self.forum_my_avatar_preview_url = preview
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
            if self.forum_admin_view == "bans":
                self.forum_load_admin_bans()
        else:
            self.forum_mod_message = result.get("error", "No se pudo revocar.")

    @rx.var
    def forum_stats_valoracion_promedio_text(self) -> str:
        """Promedio de valoraciones formateado para UI."""
        return f"{self.forum_stats_valoracion_promedio:.2f}"

    @forum_event
    def forum_on_stats_dialog_change(self, open: bool) -> None:
        """Abre/cierra el diálogo de estadísticas."""
        self.forum_stats_dialog_open = open
        if open:
            self.forum_load_stats()

    @forum_event
    def forum_open_stats_dialog(self) -> None:
        """Muestra estadísticas del foro."""
        self.forum_stats_dialog_open = True
        self.forum_load_stats()

    def forum_load_stats(self) -> None:
        """Carga estadísticas agregadas del foro (admin)."""
        from laim_web.adapters.laim_api_client import laim_forum_admin_stats

        self.forum_stats_loading = True
        self.forum_stats_message = ""
        access, session = self._forum_auth_tokens()
        result = laim_forum_admin_stats(access, session)
        self.forum_stats_loading = False
        if not result.get("success"):
            self.forum_stats_message = result.get("error", "No se pudieron cargar estadísticas.")
            return

        stats = result.get("stats", {})
        if not isinstance(stats, dict):
            self.forum_stats_message = "Respuesta de estadísticas inválida."
            return

        self.forum_stats_categorias = int(stats.get("categorias", 0) or 0)
        self.forum_stats_subcategorias = int(stats.get("subcategorias", 0) or 0)
        self.forum_stats_hilos = int(stats.get("hilos", 0) or 0)
        self.forum_stats_respuestas = int(stats.get("respuestas", 0) or 0)
        self.forum_stats_valoraciones = int(stats.get("valoraciones", 0) or 0)
        self.forum_stats_valoracion_promedio = float(stats.get("valoracion_promedio", 0) or 0)
        self.forum_stats_usuarios_activos = int(stats.get("usuarios_activos", 0) or 0)
        self.forum_stats_baneos_activos = int(stats.get("baneos_activos", 0) or 0)
        self.forum_stats_infracciones_hoy = int(stats.get("infracciones_hoy", 0) or 0)
        self.forum_stats_adjuntos = int(stats.get("adjuntos", 0) or 0)
        self.forum_stats_subcategory_rows = stats.get("subcategorias_detalle", [])
        self.forum_stats_top_users = stats.get("top_reputacion", [])

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
            cfg = settings.get("settings", settings)
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
            self.forum_avatar_catalog = self._forum_enrich_avatar_catalog(
                avatars.get("items", []), access, session
            )

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
                "accion": self.forum_admin_word_accion.strip() or "Amonestaciones",
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

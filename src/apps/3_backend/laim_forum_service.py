"""Servicio de foro LAIM Web (Backend Core).

Los datos del foro se leen y escriben unicamente via ``LaimForumRepository``
(MariaDB ``laim_core_db``). No se usa ``STORAGE_MODE`` ni ficheros JSON para
persistencia de datos del foro.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger("LaimForumService")


def _load_module(relative_path: str, module_name: str) -> Any:
    """Carga m?dulo desde ruta relativa al repo."""
    module_path = Path(__file__).resolve().parents[3] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_dtos = _load_module(
    "src/2_shared_application/dtos/laim_forum_dtos.py",
    "laim_forum_dtos_svc",
)
_repo_mod = _load_module(
    "src/2_shared_application/adapters/laim_forum_repository.py",
    "laim_forum_repository_svc",
)
_image_mod = _load_module(
    "src/2_shared_application/adapters/laim_forum_image_storage.py",
    "laim_forum_image_storage_svc",
)
_session_repo_mod = _load_module(
    "src/2_shared_application/adapters/laim_mariadb_session_repository.py",
    "laim_session_repo_forum",
)
_storage = _load_module(
    "src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py",
    "laim_storage_forum",
)
_env_settings = _load_module(
    "src/2_shared_application/config/env_settings.py",
    "laim_env_settings_forum",
)
_content_rules = _load_module(
    "src/1_shared_domain/laim_forum_content_rules.py",
    "laim_forum_content_rules_svc",
)

LaimForumRepository = _repo_mod.LaimForumRepository
LaimForumImageStorage = _image_mod.LaimForumImageStorage
create_laim_session_engine = _session_repo_mod.create_laim_session_engine
load_laim_mariadb_settings = _storage.load_laim_mariadb_settings
get_env_value = _env_settings.get_env_value
find_matching_rule = _content_rules.find_matching_rule
evaluate_rule_match = _content_rules.evaluate_rule_match
POSITIVE_ACTIONS = _content_rules.POSITIVE_ACTIONS
find_unauthorized_urls = _content_rules.find_unauthorized_urls

LaimForumThreadCreateDto = _dtos.LaimForumThreadCreateDto
LaimForumThreadUpdateDto = _dtos.LaimForumThreadUpdateDto
LaimForumPostCreateDto = _dtos.LaimForumPostCreateDto
LaimForumPostUpdateDto = _dtos.LaimForumPostUpdateDto
LaimForumPostRatingDto = _dtos.LaimForumPostRatingDto
LaimForumThreadRatingDto = _dtos.LaimForumThreadRatingDto
LaimForumUserProfileUpdateDto = _dtos.LaimForumUserProfileUpdateDto
LaimForumImageUploadDto = _dtos.LaimForumImageUploadDto
LaimForumCategoryUpsertDto = _dtos.LaimForumCategoryUpsertDto
LaimForumSubcategoryUpsertDto = _dtos.LaimForumSubcategoryUpsertDto
LaimForumPrefixUpsertDto = _dtos.LaimForumPrefixUpsertDto
LaimForumAvatarCatalogCreateDto = _dtos.LaimForumAvatarCatalogCreateDto
LaimForumSettingsDto = _dtos.LaimForumSettingsDto
LaimForumWordRuleUpsertDto = _dtos.LaimForumWordRuleUpsertDto
LaimForumAllowedUrlUpsertDto = _dtos.LaimForumAllowedUrlUpsertDto
LaimForumModeratorAssignDto = _dtos.LaimForumModeratorAssignDto


class LaimForumService:
    """Orquesta l?gica de negocio del foro LAIM."""

    FORUM_ADMIN_IDENTITY_TYPES = frozenset({1, 2})

    def __init__(
        self,
        repository: LaimForumRepository | None = None,
        image_storage: LaimForumImageStorage | None = None,
    ) -> None:
        if repository is None:
            settings = load_laim_mariadb_settings()
            engine = create_laim_session_engine(settings)
            repository = LaimForumRepository(engine)
        self._repository = repository
        self._image_storage = image_storage or LaimForumImageStorage()
        self._image_storage.ensure_base_directory()
        self._auth_service: Any | None = None

    def _get_auth_service(self) -> Any:
        """Carga perezosa del servicio de auth LAIM."""
        if self._auth_service is None:
            auth_path = Path(__file__).resolve().parent / "laim_auth_service.py"
            spec = importlib.util.spec_from_file_location(
                "laim_auth_service_forum", auth_path
            )
            if spec is None or spec.loader is None:
                raise RuntimeError("No se pudo cargar laim_auth_service")
            module = importlib.util.module_from_spec(spec)
            sys.modules["laim_auth_service_forum"] = module
            spec.loader.exec_module(module)
            self._auth_service = module.LaimAuthService()
        return self._auth_service

    @staticmethod
    def is_forum_active() -> bool:
        """Indica si el foro est? habilitado en el entorno."""
        raw = str(get_env_value("laim_forum_active", "true")).strip().lower()
        return raw in {"1", "true", "yes", "on"}

    @staticmethod
    def max_attachments_per_message() -> int:
        """M?ximo de adjuntos por mensaje."""
        return int(get_env_value("laim_forum_max_attachments_per_message", "3"))

    @staticmethod
    def max_url_strikes() -> int:
        """Strikes antes de ban autom?tico por URL."""
        return int(get_env_value("laim_forum_max_strikes_url", "3"))

    def _forum_disabled_error(self) -> dict[str, Any]:
        return {"success": False, "error": "El foro no est? activo en este entorno."}

    def resolve_required_session(
        self,
        authorization: str | None,
        session_token: str | None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Valida sesi?n LAIM obligatoria para operaciones del foro."""
        if not session_token or not authorization or not authorization.startswith("Bearer "):
            return None, "Sesi?n requerida. Inicie sesi?n para acceder al foro."
        access_token = authorization.removeprefix("Bearer ").strip()
        if not access_token:
            return None, "Token de acceso no v?lido."

        auth = self._get_auth_service()
        context = auth.resolve_optional_session_context(access_token, session_token)
        if not context.get("user_id"):
            return None, "Sesi?n inv?lida o expirada."

        user_id = int(context["user_id"])
        user = auth._user_repo.get_user_by_id(user_id)
        if user is None or not user.active:
            return None, "Usuario no autorizado."

        return {
            "user_id": user_id,
            "user_name": user.user_name,
            "organization_id": int(context.get("organization_id") or user.organization_id),
            "identity_type_id": int(user.identity_type_id),
        }, None

    def is_forum_admin(self, identity_type_id: int) -> bool:
        """SuperAdmin o Admin Org."""
        return identity_type_id in self.FORUM_ADMIN_IDENTITY_TYPES

    def can_moderate(
        self, user_id: int, identity_type_id: int, subcategory_id: str
    ) -> bool:
        """Admin global o moderador de la subcategor?a."""
        if self.is_forum_admin(identity_type_id):
            return True
        return self._repository.is_moderator(user_id, subcategory_id)

    def _log_moderation_event(
        self,
        *,
        subcategory_id: str,
        event_type: str,
        message: str,
        user_id: int | None = None,
        user_name: str | None = None,
        thread_id: int | None = None,
        post_id: int | None = None,
        moderator_user_id: int | None = None,
        moderator_user_name: str | None = None,
    ) -> None:
        """Registra evento en log de moderación (BD)."""
        self._repository.insert_moderation_log(
            subcategory_id=subcategory_id,
            event_type=event_type,
            message=message,
            user_id=user_id,
            user_name=user_name,
            thread_id=thread_id,
            post_id=post_id,
            moderator_user_id=moderator_user_id,
            moderator_user_name=moderator_user_name,
        )

    def _apply_automatic_ban(
        self,
        *,
        user_id: int,
        subcategory_id: str,
        motivo: str,
        ban_seconds: int,
    ) -> None:
        """Aplica baneo automático por moderación."""
        expires = datetime.now(timezone.utc) + timedelta(seconds=max(1, ban_seconds))
        self._repository.create_ban(
            user_id=user_id,
            subcategory_id=subcategory_id,
            motivo=motivo,
            moderador_user_id=None,
            moderador_user_name="Moderación automática",
            expires_at=expires,
            automatico=True,
        )
        self._log_moderation_event(
            subcategory_id=subcategory_id,
            event_type="ban",
            message=f"Ban automático: user_id={user_id} — {motivo}",
            user_id=user_id,
            moderator_user_name="Moderación automática",
        )

    def _validate_urls(
        self,
        text: str,
        *,
        user_id: int,
        user_name: str,
        sub: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Valida URLs contra dominios permitidos (strikes diarios)."""
        allowed_domains = [
            str(item.get("dominio", "")).strip()
            for item in self._repository.list_allowed_urls(active_only=True)
        ]
        unauthorized = find_unauthorized_urls(text, allowed_domains)
        if not unauthorized:
            return None

        subcategory_id = str(sub["id"])
        url = unauthorized[0]
        strikes = self._repository.increment_daily_infraction(
            user_id=user_id,
            subcategory_id=subcategory_id,
            tipo="url",
        )
        max_strikes = self.max_url_strikes()
        ban_seconds = int(sub.get("ban_seconds") or 86400)
        self._log_moderation_event(
            subcategory_id=subcategory_id,
            event_type="url_rechazada",
            message=f"{user_name}: URL no autorizada {url} ({strikes}/{max_strikes})",
            user_id=user_id,
            user_name=user_name,
        )
        warning = (
            f"Enlace no autorizado detectado ({url}). "
            f"Infracción {strikes}/{max_strikes}."
        )
        self._repository.create_notification(
            user_id=user_id,
            tipo="url_rechazada",
            titulo="Enlace no permitido",
            mensaje=warning,
            subcategory_id=subcategory_id,
        )
        if strikes >= max_strikes:
            self._apply_automatic_ban(
                user_id=user_id,
                subcategory_id=subcategory_id,
                motivo=f"Ban automático tras {strikes} infracciones de URL",
                ban_seconds=ban_seconds,
            )
            warning += " Se ha aplicado un ban automático."
        return {"success": False, "error": warning, "strikes": strikes}

    def _validate_content_rules(
        self,
        text: str,
        *,
        user_id: int,
        user_name: str,
        sub: dict[str, Any],
        thread_id: int = 0,
        thread_title: str = "",
    ) -> dict[str, Any] | None:
        """Valida reglas de palabras con escalado diario (Radikal)."""
        matched = find_matching_rule(
            text, self._repository.list_word_rules(active_only=True)
        )
        if matched is None:
            return None

        subcategory_id = str(sub["id"])
        accion = str(matched.get("accion", "Amonestaciones"))

        if accion in POSITIVE_ACTIONS:
            mensaje = str(matched.get("mensaje", "")).strip()
            if mensaje:
                self._log_moderation_event(
                    subcategory_id=subcategory_id,
                    event_type="regla_positiva",
                    message=(
                        f"{user_name}: regla positiva "
                        f"'{matched.get('palabra')}' — {mensaje}"
                    ),
                    user_id=user_id,
                    user_name=user_name,
                    thread_id=thread_id or None,
                )
            return None

        strike_level = self._repository.increment_daily_infraction(
            user_id=user_id,
            subcategory_id=subcategory_id,
            tipo="palabra",
        )
        outcome = evaluate_rule_match(matched, strike_level=strike_level)
        self._log_moderation_event(
            subcategory_id=subcategory_id,
            event_type="palabra_prohibida",
            message=(
                f"{user_name}: palabra '{matched.get('palabra')}' "
                f"(nivel {strike_level})"
            ),
            user_id=user_id,
            user_name=user_name,
            thread_id=thread_id or None,
        )
        if outcome.notify_user:
            self._repository.create_notification(
                user_id=user_id,
                tipo="regla_automatica",
                titulo="Aviso de moderación",
                mensaje=outcome.notify_user,
                subcategory_id=subcategory_id,
                thread_id=thread_id or None,
            )
        if outcome.escalation in ("ban", "kick"):
            ban_seconds = int(sub.get("ban_seconds") or 86400)
            self._apply_automatic_ban(
                user_id=user_id,
                subcategory_id=subcategory_id,
                motivo=outcome.notify_user or "Ban automático por palabra prohibida",
                ban_seconds=ban_seconds,
            )
        if outcome.block_message:
            return {
                "success": False,
                "error": (
                    outcome.notify_user
                    or "Mensaje no permitido por moderación automática."
                ),
            }
        return None

    def _validate_user_content(
        self,
        text: str,
        *,
        user_id: int,
        user_name: str,
        subcategory_id: str,
        thread_id: int = 0,
        thread_title: str = "",
    ) -> dict[str, Any] | None:
        """Valida URLs y reglas de contenido para un mensaje."""
        sub = self._repository.get_subcategory(subcategory_id)
        if sub is None:
            return {"success": False, "error": "Subcategoría no encontrada."}
        if not sub.get("activa"):
            return {"success": False, "error": "Subcategoría inactiva."}

        url_error = self._validate_urls(
            text, user_id=user_id, user_name=user_name, sub=sub
        )
        if url_error:
            return url_error
        return self._validate_content_rules(
            text,
            user_id=user_id,
            user_name=user_name,
            sub=sub,
            thread_id=thread_id,
            thread_title=thread_title,
        )

    def _validate_attachment_ids(
        self,
        image_ids: list[int] | None,
        user_id: int,
        identity_type_id: int,
        *,
        allowed_kinds: frozenset[str],
    ) -> str | None:
        """Valida adjuntos del usuario."""
        if not image_ids:
            return None
        max_count = self.max_attachments_per_message()
        if len(image_ids) > max_count:
            return f"M?ximo {max_count} im?genes por mensaje."
        seen: set[int] = set()
        for image_id in image_ids:
            if image_id in seen:
                return "Imagen duplicada en adjuntos."
            seen.add(image_id)
            meta = self._repository.get_image_by_id(image_id)
            if meta is None:
                return f"Imagen {image_id} no encontrada."
            if str(meta.get("image_kind")) not in allowed_kinds:
                return "Tipo de imagen no v?lido para esta operaci?n."
            uploader = meta.get("uploaded_by_user_id")
            if uploader is not None and int(uploader) != user_id:
                if not self.is_forum_admin(identity_type_id):
                    return "No puede usar im?genes subidas por otro usuario."
        return None

    def _check_ban(self, user_id: int, subcategory_id: str) -> str | None:
        """Comprueba baneo activo."""
        if self._repository.is_user_banned(user_id, subcategory_id):
            return "Est? baneado en esta subcategor?a."
        return None

    # ------------------------------------------------------------------ health
    def get_health(self) -> dict[str, Any]:
        """Estado del subsistema foro."""
        stats = self._repository.get_health_stats()
        return {
            "success": True,
            "ok": True,
            "status": "ok",
            "activo": self.is_forum_active(),
            "threads": stats.get("hilos", 0),
            **stats,
        }

    def get_admin_stats(self, session: dict[str, Any]) -> dict[str, Any]:
        """Estadísticas agregadas del foro (solo administradores)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
        stats = self._repository.get_admin_stats()
        return {"success": True, "stats": stats}

    # ------------------------------------------------------------------ im?genes
    def upload_image(
        self,
        payload: dict[str, Any],
        session: dict[str, Any],
    ) -> dict[str, Any]:
        """Sube imagen al filesystem y registra metadatos."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        try:
            dto = LaimForumImageUploadDto.model_validate(payload)
        except Exception as exc:
            return {"success": False, "error": f"Datos inv?lidos: {exc}"}

        if dto.image_kind == "avatar_catalog" and not self.is_forum_admin(
            session["identity_type_id"]
        ):
            return {"success": False, "error": "Sin permisos para cat?logo de avatares."}

        stored, error = self._image_storage.save_image(
            image_kind=dto.image_kind,
            file_name=dto.file_name,
            mime_type=dto.mime_type,
            data_base64=dto.data_base64,
            uploaded_by_user_id=session["user_id"],
        )
        if error or stored is None:
            return {"success": False, "error": error or "No se pudo guardar la imagen."}

        image_id = self._repository.insert_image(
            image_kind=dto.image_kind,
            storage_key=stored.storage_key,
            file_name=stored.file_name,
            mime_type=stored.mime_type,
            file_size=stored.file_size,
            uploaded_by_user_id=session["user_id"],
            checksum_sha256=stored.checksum_sha256,
        )
        return {
            "success": True,
            "image": {
                "id": image_id,
                "image_kind": dto.image_kind,
                "file_name": stored.file_name,
                "mime_type": stored.mime_type,
                "file_size": stored.file_size,
                "url_path": f"/laim/forum/images/{image_id}",
            },
        }

    def get_image_content(self, image_id: int) -> tuple[bytes | None, str | None]:
        """Lee bytes e MIME de una imagen."""
        meta = self._repository.get_image_by_id(image_id)
        if meta is None:
            return None, None
        content = self._image_storage.read_image_bytes(str(meta["storage_key"]))
        if content is None:
            return None, None
        return content, str(meta.get("mime_type") or "application/octet-stream")

    # ------------------------------------------------------------------ perfil
    def get_profile(self, session: dict[str, Any]) -> dict[str, Any]:
        """Perfil de foro del usuario."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        profile = self._repository.ensure_user_forum(session["user_id"])
        return {"success": True, "profile": profile}

    def update_profile(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza perfil de foro."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        try:
            dto = LaimForumUserProfileUpdateDto.model_validate(payload)
        except Exception as exc:
            return {"success": False, "error": f"Datos inv?lidos: {exc}"}

        if dto.avatar_image_id is not None and dto.avatar_image_id > 0:
            meta = self._repository.get_image_by_id(dto.avatar_image_id)
            if meta is None:
                return {"success": False, "error": "Avatar no encontrado."}
            kind = str(meta.get("image_kind"))
            if kind not in {"avatar_catalog", "avatar_user"}:
                return {"success": False, "error": "Imagen no v?lida como avatar."}
            if kind == "avatar_user":
                uploader = meta.get("uploaded_by_user_id")
                if uploader is not None and int(uploader) != session["user_id"]:
                    return {"success": False, "error": "Avatar no pertenece al usuario."}

        profile = self._repository.update_user_forum(
            session["user_id"],
            forum_display_name=dto.forum_display_name,
            signature_md=dto.signature_md,
            avatar_image_id=dto.avatar_image_id,
            notify_mentions=dto.notify_mentions,
            notify_replies=dto.notify_replies,
        )
        return {"success": True, "profile": profile}

    # ----------------------------------------------------------- cat?logo lectura
    def list_categories(self) -> dict[str, Any]:
        """Lista categor?as activas."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        return {"success": True, "items": self._repository.list_categories()}

    def list_subcategories(self, category_id: str | None = None) -> dict[str, Any]:
        """Lista subcategor?as."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        items = self._repository.list_subcategories(category_id=category_id or None)
        return {"success": True, "items": items}

    def list_prefixes(self) -> dict[str, Any]:
        """Lista prefijos activos."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        return {"success": True, "items": self._repository.list_prefixes()}

    def list_avatar_catalog(self) -> dict[str, Any]:
        """Cat?logo de avatares."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        return {"success": True, "items": self._repository.list_avatar_catalog()}

    # ----------------------------------------------------------- cat?logo admin
    def upsert_category(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Crea o actualiza categor?a (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        dto = LaimForumCategoryUpsertDto.model_validate(payload)
        self._repository.upsert_category(
            category_id=dto.id,
            nombre=dto.nombre,
            descripcion=dto.descripcion,
            orden=dto.orden,
            activa=dto.activa,
        )
        return {"success": True}

    def delete_category(self, category_id: str, session: dict[str, Any]) -> dict[str, Any]:
        """Elimina categor?a (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        deleted = self._repository.delete_category(category_id)
        return {"success": deleted}

    def upsert_subcategory(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Crea o actualiza subcategor?a (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        dto = LaimForumSubcategoryUpsertDto.model_validate(payload)
        self._repository.upsert_subcategory(
            subcategory_id=dto.id,
            categoria_id=dto.categoria_id,
            nombre=dto.nombre,
            descripcion=dto.descripcion,
            orden=dto.orden,
            activa=dto.activa,
            ban_seconds=dto.ban_seconds,
            log_rotation=dto.log_rotation,
        )
        return {"success": True}

    def delete_subcategory(
        self, subcategory_id: str, session: dict[str, Any]
    ) -> dict[str, Any]:
        """Elimina subcategor?a (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        return {"success": self._repository.delete_subcategory(subcategory_id)}

    def upsert_prefix(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Crea o actualiza prefijo (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        dto = LaimForumPrefixUpsertDto.model_validate(payload)
        self._repository.upsert_prefix(
            prefix_id=dto.id,
            texto=dto.texto,
            color_scheme=dto.color_scheme,
            activo=dto.activo,
        )
        return {"success": True}

    def delete_prefix(self, prefix_id: str, session: dict[str, Any]) -> dict[str, Any]:
        """Elimina prefijo (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        return {"success": self._repository.delete_prefix(prefix_id)}

    def add_avatar_catalog_item(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """A?ade avatar al cat?logo (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        dto = LaimForumAvatarCatalogCreateDto.model_validate(payload)
        meta = self._repository.get_image_by_id(dto.image_id)
        if meta is None or str(meta.get("image_kind")) != "avatar_catalog":
            return {"success": False, "error": "Imagen de cat?logo no v?lida."}
        item_id = self._repository.insert_avatar_catalog_item(
            image_id=dto.image_id,
            label=dto.label,
            is_default=dto.is_default,
            sort_order=dto.sort_order,
        )
        return {"success": True, "id": item_id}

    # ------------------------------------------------------------------ hilos
    def list_threads(self, subcategory_id: str) -> dict[str, Any]:
        """Lista hilos de una subcategor?a."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        return {
            "success": True,
            "items": self._repository.list_threads_by_subcategory(subcategory_id),
        }

    def get_thread(
        self, thread_id: int, session: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Detalle de hilo."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        thread = self._repository.get_thread(thread_id)
        if thread is None:
            return {"success": False, "error": "Hilo no encontrado."}
        if session is not None:
            my_rating = self._repository.get_user_thread_rating(
                thread_id, session["user_id"]
            )
            thread["my_rating"] = my_rating
        return {"success": True, "thread": thread}

    def create_thread(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Crea hilo."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        try:
            dto = LaimForumThreadCreateDto.model_validate(payload)
        except Exception as exc:
            return {"success": False, "error": f"Datos inv?lidos: {exc}"}

        ban_error = self._check_ban(session["user_id"], dto.subcategory_id)
        if ban_error:
            return {"success": False, "error": ban_error}

        content_error = self._validate_user_content(
            dto.cuerpo_md,
            user_id=session["user_id"],
            user_name=session["user_name"],
            subcategory_id=dto.subcategory_id,
            thread_title=dto.titulo.strip(),
        )
        if content_error:
            return content_error

        attach_error = self._validate_attachment_ids(
            dto.image_ids,
            session["user_id"],
            session["identity_type_id"],
            allowed_kinds=frozenset({"post_attachment"}),
        )
        if attach_error:
            return {"success": False, "error": attach_error}

        thread_id = self._repository.create_thread(
            subcategory_id=dto.subcategory_id,
            prefix_id=dto.prefix_id,
            titulo=dto.titulo.strip(),
            user_id=session["user_id"],
            user_name=session["user_name"],
            cuerpo_md=dto.cuerpo_md.strip(),
            image_ids=dto.image_ids,
        )
        return {"success": True, "thread_id": thread_id}

    def update_thread(
        self, thread_id: int, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza hilo (autor o moderador)."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        thread = self._repository.get_thread(thread_id)
        if thread is None:
            return {"success": False, "error": "Hilo no encontrado."}

        subcategory_id = str(thread["subcategory_id"])
        is_owner = int(thread["user_id"]) == session["user_id"]
        is_mod = self.can_moderate(
            session["user_id"], session["identity_type_id"], subcategory_id
        )
        if not is_owner and not is_mod:
            return {"success": False, "error": "Sin permisos para editar el hilo."}

        try:
            dto = LaimForumThreadUpdateDto.model_validate(payload)
        except Exception as exc:
            return {"success": False, "error": f"Datos inv?lidos: {exc}"}

        if dto.cuerpo_md is not None:
            content_error = self._validate_user_content(
                dto.cuerpo_md,
                user_id=session["user_id"],
                user_name=session["user_name"],
                subcategory_id=subcategory_id,
                thread_id=thread_id,
                thread_title=str(thread.get("titulo") or ""),
            )
            if content_error:
                return content_error

        if dto.fijado is not None or dto.cerrado is not None:
            if not is_mod:
                return {"success": False, "error": "Solo moderadores pueden fijar/cerrar."}

        if dto.image_ids is not None:
            attach_error = self._validate_attachment_ids(
                dto.image_ids,
                session["user_id"],
                session["identity_type_id"],
                allowed_kinds=frozenset({"post_attachment"}),
            )
            if attach_error:
                return {"success": False, "error": attach_error}

        self._repository.update_thread(
            thread_id,
            titulo=dto.titulo,
            cuerpo_md=dto.cuerpo_md,
            prefix_id=dto.prefix_id,
            fijado=dto.fijado,
            cerrado=dto.cerrado,
            image_ids=dto.image_ids,
        )
        return {"success": True, "thread": self._repository.get_thread(thread_id)}

    def delete_thread(self, thread_id: int, session: dict[str, Any]) -> dict[str, Any]:
        """Elimina hilo (soft delete)."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        thread = self._repository.get_thread(thread_id)
        if thread is None:
            return {"success": False, "error": "Hilo no encontrado."}
        subcategory_id = str(thread["subcategory_id"])
        is_owner = int(thread["user_id"]) == session["user_id"]
        is_mod = self.can_moderate(
            session["user_id"], session["identity_type_id"], subcategory_id
        )
        if not is_owner and not is_mod:
            return {"success": False, "error": "Sin permisos para eliminar el hilo."}
        ok = self._repository.soft_delete_thread(thread_id)
        if is_mod:
            self._repository.insert_moderation_log(
                subcategory_id=subcategory_id,
                event_type="delete_thread",
                message=f"Hilo {thread_id} eliminado",
                user_id=int(thread["user_id"]),
                user_name=str(thread.get("user_name") or ""),
                moderator_user_id=session["user_id"],
                moderator_user_name=session["user_name"],
                thread_id=thread_id,
            )
        return {"success": ok}

    def list_my_threads(self, session: dict[str, Any]) -> dict[str, Any]:
        """Hilos del usuario autenticado."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        return {
            "success": True,
            "items": self._repository.list_threads_by_user(session["user_id"]),
        }

    # ----------------------------------------------------------------- respuestas
    def list_posts(self, thread_id: int) -> dict[str, Any]:
        """Lista respuestas de un hilo."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        thread = self._repository.get_thread(thread_id)
        if thread is None:
            return {"success": False, "error": "Hilo no encontrado."}
        return {
            "success": True,
            "items": self._repository.list_posts_by_thread(thread_id),
        }

    def create_post(
        self, thread_id: int, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Crea respuesta."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        thread = self._repository.get_thread(thread_id)
        if thread is None:
            return {"success": False, "error": "Hilo no encontrado."}
        if thread.get("cerrado"):
            return {"success": False, "error": "El hilo est? cerrado."}

        subcategory_id = str(thread["subcategory_id"])
        ban_error = self._check_ban(session["user_id"], subcategory_id)
        if ban_error:
            return {"success": False, "error": ban_error}

        try:
            dto = LaimForumPostCreateDto.model_validate(payload)
        except Exception as exc:
            return {"success": False, "error": f"Datos inv?lidos: {exc}"}

        content_error = self._validate_user_content(
            dto.cuerpo_md,
            user_id=session["user_id"],
            user_name=session["user_name"],
            subcategory_id=subcategory_id,
            thread_id=thread_id,
            thread_title=str(thread.get("titulo") or ""),
        )
        if content_error:
            return content_error

        attach_error = self._validate_attachment_ids(
            dto.image_ids,
            session["user_id"],
            session["identity_type_id"],
            allowed_kinds=frozenset({"post_attachment"}),
        )
        if attach_error:
            return {"success": False, "error": attach_error}

        post_id = self._repository.create_post(
            thread_id=thread_id,
            user_id=session["user_id"],
            user_name=session["user_name"],
            cuerpo_md=dto.cuerpo_md.strip(),
            image_ids=dto.image_ids,
        )

        author_id = int(thread["user_id"])
        if author_id != session["user_id"]:
            profile = self._repository.get_user_forum(author_id)
            if profile is None or profile.get("notify_replies", True):
                self._repository.create_notification(
                    user_id=author_id,
                    tipo="reply",
                    titulo="Nueva respuesta en tu hilo",
                    mensaje=f"{session['user_name']} respondi? en ?{thread['titulo']}?",
                    subcategory_id=subcategory_id,
                    thread_id=thread_id,
                    post_id=post_id,
                )

        return {"success": True, "post_id": post_id}

    def update_post(
        self, post_id: int, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza respuesta."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        post = self._repository.get_post(post_id)
        if post is None:
            return {"success": False, "error": "Respuesta no encontrada."}
        thread = self._repository.get_thread(int(post["thread_id"]))
        if thread is None:
            return {"success": False, "error": "Hilo no encontrado."}

        subcategory_id = str(thread["subcategory_id"])
        is_owner = int(post["user_id"]) == session["user_id"]
        is_mod = self.can_moderate(
            session["user_id"], session["identity_type_id"], subcategory_id
        )
        if not is_owner and not is_mod:
            return {"success": False, "error": "Sin permisos para editar la respuesta."}

        dto = LaimForumPostUpdateDto.model_validate(payload)
        if dto.cuerpo_md is not None:
            content_error = self._validate_user_content(
                dto.cuerpo_md,
                user_id=session["user_id"],
                user_name=session["user_name"],
                subcategory_id=subcategory_id,
                thread_id=int(thread["id"]),
                thread_title=str(thread.get("titulo") or ""),
            )
            if content_error:
                return content_error
        if dto.image_ids is not None:
            attach_error = self._validate_attachment_ids(
                dto.image_ids,
                session["user_id"],
                session["identity_type_id"],
                allowed_kinds=frozenset({"post_attachment"}),
            )
            if attach_error:
                return {"success": False, "error": attach_error}

        self._repository.update_post(
            post_id, cuerpo_md=dto.cuerpo_md.strip(), image_ids=dto.image_ids
        )
        return {"success": True, "post": self._repository.get_post(post_id)}

    def delete_post(self, post_id: int, session: dict[str, Any]) -> dict[str, Any]:
        """Elimina respuesta (soft delete)."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        post = self._repository.get_post(post_id)
        if post is None:
            return {"success": False, "error": "Respuesta no encontrada."}
        thread = self._repository.get_thread(int(post["thread_id"]))
        if thread is None:
            return {"success": False, "error": "Hilo no encontrado."}
        subcategory_id = str(thread["subcategory_id"])
        is_owner = int(post["user_id"]) == session["user_id"]
        is_mod = self.can_moderate(
            session["user_id"], session["identity_type_id"], subcategory_id
        )
        if not is_owner and not is_mod:
            return {"success": False, "error": "Sin permisos para eliminar la respuesta."}
        ok = self._repository.soft_delete_post(post_id)
        return {"success": ok}

    def list_my_posts(self, session: dict[str, Any]) -> dict[str, Any]:
        """Respuestas del usuario."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        return {
            "success": True,
            "items": self._repository.list_posts_by_user(session["user_id"]),
        }

    def rate_thread(
        self, thread_id: int, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Valoración 1-5 de un hilo (una por usuario)."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        thread = self._repository.get_thread(thread_id)
        if thread is None:
            return {"success": False, "error": "Hilo no encontrado."}
        if int(thread["user_id"]) == session["user_id"]:
            return {"success": False, "error": "No puede valorar su propio hilo."}
        dto = LaimForumThreadRatingDto.model_validate(payload)
        self._repository.upsert_thread_rating(
            thread_id=thread_id,
            user_id=session["user_id"],
            valoracion=dto.valoracion,
        )
        updated = self._repository.get_thread(thread_id)
        return {
            "success": True,
            "thread": updated,
            "my_rating": dto.valoracion,
        }

    def rate_post(
        self, post_id: int, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Valoraci?n 1-5 de una respuesta."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        post = self._repository.get_post(post_id)
        if post is None:
            return {"success": False, "error": "Respuesta no encontrada."}
        target_user_id = int(post["user_id"])
        if target_user_id == session["user_id"]:
            return {"success": False, "error": "No puede valorar su propia respuesta."}
        dto = LaimForumPostRatingDto.model_validate(payload)
        self._repository.upsert_post_rating(
            post_id=post_id,
            user_id=session["user_id"],
            target_user_id=target_user_id,
            valoracion=dto.valoracion,
        )
        return {"success": True}

    # ------------------------------------------------------------- notificaciones
    def list_pending_notifications(self, session: dict[str, Any]) -> dict[str, Any]:
        """Notificaciones pendientes del usuario."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        items = self._repository.list_pending_notifications(session["user_id"])
        return {"success": True, "items": items}

    def acknowledge_notifications(
        self, notification_ids: list[int], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Marca notificaciones como entregadas."""
        count = self._repository.mark_notifications_delivered(
            session["user_id"], notification_ids
        )
        return {"success": True, "updated": count}

    # ----------------------------------------------------------- admin moderaci?n
    def get_admin_settings(self, session: dict[str, Any]) -> dict[str, Any]:
        """Configuraci?n de moderaci?n."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        return {"success": True, "settings": self._repository.get_settings()}

    def update_admin_settings(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza configuraci?n de moderaci?n."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        dto = LaimForumSettingsDto.model_validate(payload)
        settings = self._repository.update_settings(
            anunciar_ban_en_log=dto.anunciar_ban_en_log,
            plantilla_ban=dto.plantilla_ban,
            plantilla_eliminacion=dto.plantilla_eliminacion,
        )
        return {"success": True, "settings": settings}

    def list_word_rules_admin(self, session: dict[str, Any]) -> dict[str, Any]:
        """Lista reglas de palabras (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        return {
            "success": True,
            "items": self._repository.list_word_rules(active_only=False),
        }

    def upsert_word_rule(
        self, payload: dict[str, Any], session: dict[str, Any], rule_id: int | None = None
    ) -> dict[str, Any]:
        """Crea o actualiza regla de palabra."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        dto = LaimForumWordRuleUpsertDto.model_validate(payload)
        new_id = self._repository.upsert_word_rule(
            rule_id=rule_id,
            palabra=dto.palabra,
            accion=dto.accion,
            mensaje=dto.mensaje,
            activo=dto.activo,
        )
        return {"success": True, "id": new_id}

    def delete_word_rule(self, rule_id: int, session: dict[str, Any]) -> dict[str, Any]:
        """Elimina regla de palabra."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        return {"success": self._repository.delete_word_rule(rule_id)}

    def list_allowed_urls_admin(self, session: dict[str, Any]) -> dict[str, Any]:
        """Lista dominios permitidos."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        return {
            "success": True,
            "items": self._repository.list_allowed_urls(active_only=False),
        }

    def upsert_allowed_url(
        self, payload: dict[str, Any], session: dict[str, Any], url_id: int | None = None
    ) -> dict[str, Any]:
        """Crea o actualiza dominio permitido."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        dto = LaimForumAllowedUrlUpsertDto.model_validate(payload)
        new_id = self._repository.upsert_allowed_url(
            url_id=url_id,
            dominio=dto.dominio.strip().lower(),
            descripcion=dto.descripcion,
            activo=dto.activo,
        )
        return {"success": True, "id": new_id}

    def delete_allowed_url(self, url_id: int, session: dict[str, Any]) -> dict[str, Any]:
        """Elimina dominio permitido."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        return {"success": self._repository.delete_allowed_url(url_id)}

    def list_moderators_admin(
        self, session: dict[str, Any], subcategory_id: str | None = None
    ) -> dict[str, Any]:
        """Lista moderadores."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        return {
            "success": True,
            "items": self._repository.list_moderators(
                subcategory_id=subcategory_id, active_only=False
            ),
        }

    def assign_moderator(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Asigna moderador a subcategor?a."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        dto = LaimForumModeratorAssignDto.model_validate(payload)
        mod_id = self._repository.assign_moderator(
            user_id=dto.user_id,
            user_name=dto.user_name,
            subcategory_id=dto.subcategory_id,
        )
        return {"success": True, "id": mod_id}

    def deactivate_moderator(
        self, moderator_id: int, session: dict[str, Any]
    ) -> dict[str, Any]:
        """Desactiva moderador."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        return {"success": self._repository.deactivate_moderator(moderator_id)}

    def create_ban(
        self,
        payload: dict[str, Any],
        session: dict[str, Any],
    ) -> dict[str, Any]:
        """Banea usuario en subcategor?a (moderador/admin)."""
        subcategory_id = str(payload.get("subcategory_id", "")).strip()
        user_id = int(payload.get("user_id") or 0)
        motivo = str(payload.get("motivo", "")).strip()
        if not subcategory_id or user_id <= 0 or not motivo:
            return {"success": False, "error": "Datos de baneo incompletos."}
        if not self.can_moderate(
            session["user_id"], session["identity_type_id"], subcategory_id
        ):
            return {"success": False, "error": "Sin permisos de moderaci?n."}

        expires_raw = payload.get("expires_at")
        expires_at: datetime | None = None
        if expires_raw:
            try:
                expires_at = datetime.fromisoformat(str(expires_raw))
            except ValueError:
                return {"success": False, "error": "Fecha de expiraci?n no v?lida."}

        ban_id = self._repository.create_ban(
            user_id=user_id,
            subcategory_id=subcategory_id,
            motivo=motivo,
            moderador_user_id=session["user_id"],
            moderador_user_name=session["user_name"],
            expires_at=expires_at,
            automatico=False,
        )
        settings = self._repository.get_settings()
        if settings.get("anunciar_ban_en_log"):
            template = str(settings.get("plantilla_ban") or "")
            message = (
                template.replace("@usuario", str(user_id))
                .replace("@subcategoria", subcategory_id)
                .replace("@motivo", motivo)
            )
            self._repository.insert_moderation_log(
                subcategory_id=subcategory_id,
                event_type="ban",
                message=message,
                user_id=user_id,
                moderator_user_id=session["user_id"],
                moderator_user_name=session["user_name"],
            )
        return {"success": True, "ban_id": ban_id}

    def revoke_ban(self, ban_id: int, session: dict[str, Any]) -> dict[str, Any]:
        """Revoca baneo."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administraci?n."}
        ok = self._repository.revoke_ban(ban_id, session["user_id"])
        return {"success": ok}

    def list_moderation_logs(
        self, subcategory_id: str, session: dict[str, Any]
    ) -> dict[str, Any]:
        """Logs de moderaci?n de una subcategor?a."""
        if not self.can_moderate(
            session["user_id"], session["identity_type_id"], subcategory_id
        ):
            return {"success": False, "error": "Sin permisos de moderaci?n."}
        return {
            "success": True,
            "items": self._repository.list_moderation_logs(subcategory_id),
        }

    def list_active_bans_admin(self, session: dict[str, Any]) -> dict[str, Any]:
        """Lista baneos activos (solo administradores)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
        return {"success": True, "items": self._repository.list_active_bans()}

    def list_admin_logs(
        self,
        session: dict[str, Any],
        *,
        subcategory_id: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Visor de logs de moderación (admin global)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
        return {
            "success": True,
            "items": self._repository.list_moderation_logs_admin(
                subcategory_id=subcategory_id,
                limit=limit,
            ),
        }

    def reload_admin_config(self, session: dict[str, Any]) -> dict[str, Any]:
        """Refresca estado del servicio (equivalente a reload_config en Radikal)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
        health = self.get_health()
        return {
            "success": True,
            "ok": True,
            "activo": health.get("activo"),
            "threads": health.get("hilos", health.get("threads", 0)),
            "stats": health,
        }

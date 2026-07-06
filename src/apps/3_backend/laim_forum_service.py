"""Servicio de foro LAIM Web (Backend Core)."""

from __future__ import annotations

import importlib.util
import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_logger = logging.getLogger("LaimForumService")

_URL_PATTERN = re.compile(r"https?://[^\s)\]>]+", re.IGNORECASE)


def _load_module(relative_path: str, module_name: str) -> Any:
    """Carga módulo desde ruta relativa al repo."""
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

LaimForumRepository = _repo_mod.LaimForumRepository
LaimForumImageStorage = _image_mod.LaimForumImageStorage
create_laim_session_engine = _session_repo_mod.create_laim_session_engine
load_laim_mariadb_settings = _storage.load_laim_mariadb_settings
get_env_value = _env_settings.get_env_value

LaimForumThreadCreateDto = _dtos.LaimForumThreadCreateDto
LaimForumThreadUpdateDto = _dtos.LaimForumThreadUpdateDto
LaimForumPostCreateDto = _dtos.LaimForumPostCreateDto
LaimForumPostUpdateDto = _dtos.LaimForumPostUpdateDto
LaimForumPostRatingDto = _dtos.LaimForumPostRatingDto
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
    """Orquesta lógica de negocio del foro LAIM."""

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
        """Indica si el foro está habilitado en el entorno."""
        raw = str(get_env_value("laim_forum_active", "true")).strip().lower()
        return raw in {"1", "true", "yes", "on"}

    @staticmethod
    def max_attachments_per_message() -> int:
        """Máximo de adjuntos por mensaje."""
        return int(get_env_value("laim_forum_max_attachments_per_message", "3"))

    @staticmethod
    def max_url_strikes() -> int:
        """Strikes antes de ban automático por URL."""
        return int(get_env_value("laim_forum_max_strikes_url", "3"))

    def _forum_disabled_error(self) -> dict[str, Any]:
        return {"success": False, "error": "El foro no está activo en este entorno."}

    def resolve_required_session(
        self,
        authorization: str | None,
        session_token: str | None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Valida sesión LAIM obligatoria para operaciones del foro."""
        if not session_token or not authorization or not authorization.startswith("Bearer "):
            return None, "Sesión requerida. Inicie sesión para acceder al foro."
        access_token = authorization.removeprefix("Bearer ").strip()
        if not access_token:
            return None, "Token de acceso no válido."

        auth = self._get_auth_service()
        context = auth.resolve_optional_session_context(access_token, session_token)
        if not context.get("user_id"):
            return None, "Sesión inválida o expirada."

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
        """Admin global o moderador de la subcategoría."""
        if self.is_forum_admin(identity_type_id):
            return True
        return self._repository.is_moderator(user_id, subcategory_id)

    def _validate_markdown_content(self, content: str) -> str | None:
        """Aplica reglas de palabras y URLs permitidas."""
        lowered = content.lower()
        for rule in self._repository.list_word_rules(active_only=True):
            word = str(rule.get("palabra", "")).strip().lower()
            if word and word in lowered:
                return str(rule.get("mensaje") or f"Contenido no permitido: {word}")
        allowed = {
            str(item.get("dominio", "")).strip().lower()
            for item in self._repository.list_allowed_urls(active_only=True)
        }
        if not allowed:
            return None
        for match in _URL_PATTERN.findall(content):
            parsed = urlparse(match.rstrip(".,;"))
            host = (parsed.hostname or "").lower()
            if not host:
                continue
            if not any(host == domain or host.endswith(f".{domain}") for domain in allowed):
                return f"Dominio no permitido en enlaces: {host}"
        return None

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
            return f"Máximo {max_count} imágenes por mensaje."
        seen: set[int] = set()
        for image_id in image_ids:
            if image_id in seen:
                return "Imagen duplicada en adjuntos."
            seen.add(image_id)
            meta = self._repository.get_image_by_id(image_id)
            if meta is None:
                return f"Imagen {image_id} no encontrada."
            if str(meta.get("image_kind")) not in allowed_kinds:
                return "Tipo de imagen no válido para esta operación."
            uploader = meta.get("uploaded_by_user_id")
            if uploader is not None and int(uploader) != user_id:
                if not self.is_forum_admin(identity_type_id):
                    return "No puede usar imágenes subidas por otro usuario."
        return None

    def _check_ban(self, user_id: int, subcategory_id: str) -> str | None:
        """Comprueba baneo activo."""
        if self._repository.is_user_banned(user_id, subcategory_id):
            return "Está baneado en esta subcategoría."
        return None

    def _register_url_infraction(
        self, user_id: int, subcategory_id: str, reason: str
    ) -> None:
        """Registra strike por URL y banea si supera umbral."""
        self._repository.add_infraction(
            user_id=user_id,
            subcategory_id=subcategory_id,
            tipo="url_no_permitida",
            strikes=1,
        )
        total = self._repository.count_strikes(user_id, subcategory_id)
        if total >= self.max_url_strikes():
            subcats = self._repository.list_subcategories(active_only=False)
            ban_seconds = 86400
            for sub in subcats:
                if sub.get("id") == subcategory_id:
                    ban_seconds = int(sub.get("ban_seconds") or 86400)
                    break
            expires = datetime.now(timezone.utc) + timedelta(seconds=ban_seconds)
            self._repository.create_ban(
                user_id=user_id,
                subcategory_id=subcategory_id,
                motivo=reason,
                expires_at=expires,
                automatico=True,
            )

    # ------------------------------------------------------------------ health
    def get_health(self) -> dict[str, Any]:
        """Estado del subsistema foro."""
        stats = self._repository.get_health_stats()
        return {
            "success": True,
            "ok": True,
            "activo": self.is_forum_active(),
            **stats,
        }

    # ------------------------------------------------------------------ imágenes
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
            return {"success": False, "error": f"Datos inválidos: {exc}"}

        if dto.image_kind == "avatar_catalog" and not self.is_forum_admin(
            session["identity_type_id"]
        ):
            return {"success": False, "error": "Sin permisos para catálogo de avatares."}

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
            return {"success": False, "error": f"Datos inválidos: {exc}"}

        if dto.avatar_image_id is not None and dto.avatar_image_id > 0:
            meta = self._repository.get_image_by_id(dto.avatar_image_id)
            if meta is None:
                return {"success": False, "error": "Avatar no encontrado."}
            kind = str(meta.get("image_kind"))
            if kind not in {"avatar_catalog", "avatar_user"}:
                return {"success": False, "error": "Imagen no válida como avatar."}
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

    # ----------------------------------------------------------- catálogo lectura
    def list_categories(self) -> dict[str, Any]:
        """Lista categorías activas."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        return {"success": True, "items": self._repository.list_categories()}

    def list_subcategories(self, category_id: str | None = None) -> dict[str, Any]:
        """Lista subcategorías."""
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
        """Catálogo de avatares."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        return {"success": True, "items": self._repository.list_avatar_catalog()}

    # ----------------------------------------------------------- catálogo admin
    def upsert_category(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Crea o actualiza categoría (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
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
        """Elimina categoría (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
        deleted = self._repository.delete_category(category_id)
        return {"success": deleted}

    def upsert_subcategory(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Crea o actualiza subcategoría (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
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
        """Elimina subcategoría (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
        return {"success": self._repository.delete_subcategory(subcategory_id)}

    def upsert_prefix(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Crea o actualiza prefijo (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
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
            return {"success": False, "error": "Sin permisos de administración."}
        return {"success": self._repository.delete_prefix(prefix_id)}

    def add_avatar_catalog_item(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Añade avatar al catálogo (admin)."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
        dto = LaimForumAvatarCatalogCreateDto.model_validate(payload)
        meta = self._repository.get_image_by_id(dto.image_id)
        if meta is None or str(meta.get("image_kind")) != "avatar_catalog":
            return {"success": False, "error": "Imagen de catálogo no válida."}
        item_id = self._repository.insert_avatar_catalog_item(
            image_id=dto.image_id,
            label=dto.label,
            is_default=dto.is_default,
            sort_order=dto.sort_order,
        )
        return {"success": True, "id": item_id}

    # ------------------------------------------------------------------ hilos
    def list_threads(self, subcategory_id: str) -> dict[str, Any]:
        """Lista hilos de una subcategoría."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        return {
            "success": True,
            "items": self._repository.list_threads_by_subcategory(subcategory_id),
        }

    def get_thread(self, thread_id: int) -> dict[str, Any]:
        """Detalle de hilo."""
        if not self.is_forum_active():
            return self._forum_disabled_error()
        thread = self._repository.get_thread(thread_id)
        if thread is None:
            return {"success": False, "error": "Hilo no encontrado."}
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
            return {"success": False, "error": f"Datos inválidos: {exc}"}

        ban_error = self._check_ban(session["user_id"], dto.subcategory_id)
        if ban_error:
            return {"success": False, "error": ban_error}

        content_error = self._validate_markdown_content(dto.cuerpo_md)
        if content_error:
            self._register_url_infraction(
                session["user_id"], dto.subcategory_id, content_error
            )
            return {"success": False, "error": content_error}

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
            return {"success": False, "error": f"Datos inválidos: {exc}"}

        if dto.cuerpo_md is not None:
            content_error = self._validate_markdown_content(dto.cuerpo_md)
            if content_error:
                return {"success": False, "error": content_error}

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
            return {"success": False, "error": "El hilo está cerrado."}

        subcategory_id = str(thread["subcategory_id"])
        ban_error = self._check_ban(session["user_id"], subcategory_id)
        if ban_error:
            return {"success": False, "error": ban_error}

        try:
            dto = LaimForumPostCreateDto.model_validate(payload)
        except Exception as exc:
            return {"success": False, "error": f"Datos inválidos: {exc}"}

        content_error = self._validate_markdown_content(dto.cuerpo_md)
        if content_error:
            self._register_url_infraction(
                session["user_id"], subcategory_id, content_error
            )
            return {"success": False, "error": content_error}

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
                    mensaje=f"{session['user_name']} respondió en «{thread['titulo']}»",
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
        content_error = self._validate_markdown_content(dto.cuerpo_md)
        if content_error:
            return {"success": False, "error": content_error}
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

    def rate_post(
        self, post_id: int, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Valoración 1-5 de una respuesta."""
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

    # ----------------------------------------------------------- admin moderación
    def get_admin_settings(self, session: dict[str, Any]) -> dict[str, Any]:
        """Configuración de moderación."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
        return {"success": True, "settings": self._repository.get_settings()}

    def update_admin_settings(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Actualiza configuración de moderación."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
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
            return {"success": False, "error": "Sin permisos de administración."}
        return {
            "success": True,
            "items": self._repository.list_word_rules(active_only=False),
        }

    def upsert_word_rule(
        self, payload: dict[str, Any], session: dict[str, Any], rule_id: int | None = None
    ) -> dict[str, Any]:
        """Crea o actualiza regla de palabra."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
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
            return {"success": False, "error": "Sin permisos de administración."}
        return {"success": self._repository.delete_word_rule(rule_id)}

    def list_allowed_urls_admin(self, session: dict[str, Any]) -> dict[str, Any]:
        """Lista dominios permitidos."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
        return {
            "success": True,
            "items": self._repository.list_allowed_urls(active_only=False),
        }

    def upsert_allowed_url(
        self, payload: dict[str, Any], session: dict[str, Any], url_id: int | None = None
    ) -> dict[str, Any]:
        """Crea o actualiza dominio permitido."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
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
            return {"success": False, "error": "Sin permisos de administración."}
        return {"success": self._repository.delete_allowed_url(url_id)}

    def list_moderators_admin(
        self, session: dict[str, Any], subcategory_id: str | None = None
    ) -> dict[str, Any]:
        """Lista moderadores."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
        return {
            "success": True,
            "items": self._repository.list_moderators(
                subcategory_id=subcategory_id, active_only=False
            ),
        }

    def assign_moderator(
        self, payload: dict[str, Any], session: dict[str, Any]
    ) -> dict[str, Any]:
        """Asigna moderador a subcategoría."""
        if not self.is_forum_admin(session["identity_type_id"]):
            return {"success": False, "error": "Sin permisos de administración."}
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
            return {"success": False, "error": "Sin permisos de administración."}
        return {"success": self._repository.deactivate_moderator(moderator_id)}

    def create_ban(
        self,
        payload: dict[str, Any],
        session: dict[str, Any],
    ) -> dict[str, Any]:
        """Banea usuario en subcategoría (moderador/admin)."""
        subcategory_id = str(payload.get("subcategory_id", "")).strip()
        user_id = int(payload.get("user_id") or 0)
        motivo = str(payload.get("motivo", "")).strip()
        if not subcategory_id or user_id <= 0 or not motivo:
            return {"success": False, "error": "Datos de baneo incompletos."}
        if not self.can_moderate(
            session["user_id"], session["identity_type_id"], subcategory_id
        ):
            return {"success": False, "error": "Sin permisos de moderación."}

        expires_raw = payload.get("expires_at")
        expires_at: datetime | None = None
        if expires_raw:
            try:
                expires_at = datetime.fromisoformat(str(expires_raw))
            except ValueError:
                return {"success": False, "error": "Fecha de expiración no válida."}

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
            return {"success": False, "error": "Sin permisos de administración."}
        ok = self._repository.revoke_ban(ban_id, session["user_id"])
        return {"success": ok}

    def list_moderation_logs(
        self, subcategory_id: str, session: dict[str, Any]
    ) -> dict[str, Any]:
        """Logs de moderación de una subcategoría."""
        if not self.can_moderate(
            session["user_id"], session["identity_type_id"], subcategory_id
        ):
            return {"success": False, "error": "Sin permisos de moderación."}
        return {
            "success": True,
            "items": self._repository.list_moderation_logs(subcategory_id),
        }

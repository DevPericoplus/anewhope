"""Endpoints FastAPI del foro LAIM en Backend Core."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laim/forum", tags=["laim-forum"])

_laim_forum_path = Path(__file__).resolve().parent / "laim_forum_service.py"
_spec = importlib.util.spec_from_file_location("laim_forum_service_router", _laim_forum_path)
if _spec is None or _spec.loader is None:
    raise ImportError("No se pudo cargar laim_forum_service")
_laim_forum_module = importlib.util.module_from_spec(_spec)
sys.modules["laim_forum_service_router"] = _laim_forum_module
_spec.loader.exec_module(_laim_forum_module)

LaimForumService = _laim_forum_module.LaimForumService

_forum_service: LaimForumService | None = None


def get_laim_forum_service() -> LaimForumService:
    """Singleton del servicio de foro LAIM."""
    global _forum_service
    if _forum_service is None:
        _forum_service = LaimForumService()
    return _forum_service


class LaimForumImageUploadRequest(BaseModel):
    """Subida de imagen en base64."""

    file_name: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=3, max_length=100)
    data_base64: str = Field(..., min_length=1)
    image_kind: str = Field(default="post_attachment", max_length=30)


class LaimForumNotificationAckRequest(BaseModel):
    """Confirmación de notificaciones entregadas."""

    notification_ids: list[int] = Field(default_factory=list)


class LaimForumBanRequest(BaseModel):
    """Solicitud de baneo."""

    user_id: int = Field(..., gt=0)
    subcategory_id: str = Field(..., min_length=1, max_length=64)
    motivo: str = Field(..., min_length=1, max_length=500)
    expires_at: str | None = None


def _require_session(
    authorization: str | None,
    session_token: str | None,
) -> dict[str, Any]:
    """Valida sesión LAIM obligatoria."""
    service = get_laim_forum_service()
    session, error = service.resolve_required_session(authorization, session_token)
    if error or session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error or "Sesión requerida",
        )
    return session


def _raise_if_failed(result: dict[str, Any], *, default_status: int = 400) -> dict[str, Any]:
    """Convierte respuesta fallida del servicio en HTTPException."""
    if not result.get("success"):
        raise HTTPException(
            status_code=default_status,
            detail=result.get("error", "Operación no permitida"),
        )
    return result


@router.get("/health")
def laim_forum_health() -> dict[str, Any]:
    """Estado del subsistema foro (público)."""
    return get_laim_forum_service().get_health()


@router.get("/images/{image_id}")
def laim_forum_get_image(
    image_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> Response:
    """Sirve imagen del foro (requiere sesión)."""
    _require_session(authorization, session_token)
    service = get_laim_forum_service()
    content, mime_type = service.get_image_content(image_id)
    if content is None or mime_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imagen no encontrada")
    return Response(content=content, media_type=mime_type)


@router.post("/images/upload")
def laim_forum_upload_image(
    payload: LaimForumImageUploadRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Sube imagen (avatar o adjunto)."""
    session = _require_session(authorization, session_token)
    result = get_laim_forum_service().upload_image(payload.model_dump(), session)
    return _raise_if_failed(result)


@router.get("/profile")
def laim_forum_get_profile(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Perfil de foro del usuario."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().get_profile(session))


@router.patch("/profile")
def laim_forum_update_profile(
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Actualiza perfil de foro."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().update_profile(payload, session))


@router.get("/categories")
def laim_forum_list_categories(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Lista categorías."""
    _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().list_categories())


@router.get("/subcategories")
def laim_forum_list_subcategories(
    category_id: str | None = None,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Lista subcategorías."""
    _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().list_subcategories(category_id))


@router.get("/prefixes")
def laim_forum_list_prefixes(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Lista prefijos."""
    _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().list_prefixes())


@router.get("/avatars/catalog")
def laim_forum_list_avatar_catalog(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Catálogo de avatares."""
    _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().list_avatar_catalog())


@router.put("/categories")
def laim_forum_upsert_category(
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Crea o actualiza categoría (admin)."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().upsert_category(payload, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.delete("/categories/{category_id}")
def laim_forum_delete_category(
    category_id: str,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Elimina categoría (admin)."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().delete_category(category_id, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.put("/subcategories")
def laim_forum_upsert_subcategory(
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Crea o actualiza subcategoría (admin)."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().upsert_subcategory(payload, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.delete("/subcategories/{subcategory_id}")
def laim_forum_delete_subcategory(
    subcategory_id: str,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Elimina subcategoría (admin)."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().delete_subcategory(subcategory_id, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.put("/prefixes")
def laim_forum_upsert_prefix(
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Crea o actualiza prefijo (admin)."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().upsert_prefix(payload, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.delete("/prefixes/{prefix_id}")
def laim_forum_delete_prefix(
    prefix_id: str,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Elimina prefijo (admin)."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().delete_prefix(prefix_id, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.post("/avatars/catalog")
def laim_forum_add_avatar_catalog(
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Añade avatar al catálogo (admin)."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().add_avatar_catalog_item(payload, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.get("/subcategories/{subcategory_id}/threads")
def laim_forum_list_threads(
    subcategory_id: str,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Lista hilos de una subcategoría."""
    _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().list_threads(subcategory_id))


@router.get("/threads/{thread_id}")
def laim_forum_get_thread(
    thread_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Detalle de hilo."""
    _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().get_thread(thread_id))


@router.post("/threads")
def laim_forum_create_thread(
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Crea hilo."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().create_thread(payload, session))


@router.patch("/threads/{thread_id}")
def laim_forum_update_thread(
    thread_id: int,
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Actualiza hilo."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().update_thread(thread_id, payload, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.delete("/threads/{thread_id}")
def laim_forum_delete_thread(
    thread_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Elimina hilo."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().delete_thread(thread_id, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.get("/me/threads")
def laim_forum_my_threads(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Mis hilos."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().list_my_threads(session))


@router.get("/threads/{thread_id}/posts")
def laim_forum_list_posts(
    thread_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Lista respuestas de un hilo."""
    _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().list_posts(thread_id))


@router.post("/threads/{thread_id}/posts")
def laim_forum_create_post(
    thread_id: int,
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Crea respuesta."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().create_post(thread_id, payload, session))


@router.patch("/posts/{post_id}")
def laim_forum_update_post(
    post_id: int,
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Actualiza respuesta."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().update_post(post_id, payload, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.delete("/posts/{post_id}")
def laim_forum_delete_post(
    post_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Elimina respuesta."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().delete_post(post_id, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.get("/me/posts")
def laim_forum_my_posts(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Mis respuestas."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().list_my_posts(session))


@router.post("/posts/{post_id}/rating")
def laim_forum_rate_post(
    post_id: int,
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Valoración de respuesta."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().rate_post(post_id, payload, session))


@router.get("/notifications/pending")
def laim_forum_pending_notifications(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Notificaciones pendientes."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(get_laim_forum_service().list_pending_notifications(session))


@router.post("/notifications/ack")
def laim_forum_ack_notifications(
    payload: LaimForumNotificationAckRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Marca notificaciones como entregadas."""
    session = _require_session(authorization, session_token)
    return get_laim_forum_service().acknowledge_notifications(
        payload.notification_ids, session
    )


@router.get("/admin/settings")
def laim_forum_admin_settings(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Configuración de moderación."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().get_admin_settings(session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.patch("/admin/settings")
def laim_forum_admin_update_settings(
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Actualiza configuración de moderación."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().update_admin_settings(payload, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.get("/admin/word-rules")
def laim_forum_admin_word_rules(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Reglas de palabras."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().list_word_rules_admin(session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.post("/admin/word-rules")
def laim_forum_admin_create_word_rule(
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Crea regla de palabra."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().upsert_word_rule(payload, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.patch("/admin/word-rules/{rule_id}")
def laim_forum_admin_update_word_rule(
    rule_id: int,
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Actualiza regla de palabra."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().upsert_word_rule(payload, session, rule_id=rule_id),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.delete("/admin/word-rules/{rule_id}")
def laim_forum_admin_delete_word_rule(
    rule_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Elimina regla de palabra."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().delete_word_rule(rule_id, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.get("/admin/allowed-urls")
def laim_forum_admin_allowed_urls(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Dominios permitidos."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().list_allowed_urls_admin(session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.post("/admin/allowed-urls")
def laim_forum_admin_create_allowed_url(
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Crea dominio permitido."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().upsert_allowed_url(payload, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.patch("/admin/allowed-urls/{url_id}")
def laim_forum_admin_update_allowed_url(
    url_id: int,
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Actualiza dominio permitido."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().upsert_allowed_url(payload, session, url_id=url_id),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.delete("/admin/allowed-urls/{url_id}")
def laim_forum_admin_delete_allowed_url(
    url_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Elimina dominio permitido."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().delete_allowed_url(url_id, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.get("/admin/moderators")
def laim_forum_admin_moderators(
    subcategory_id: str | None = None,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Lista moderadores."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().list_moderators_admin(session, subcategory_id),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.post("/admin/moderators")
def laim_forum_admin_assign_moderator(
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Asigna moderador."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().assign_moderator(payload, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.delete("/admin/moderators/{moderator_id}")
def laim_forum_admin_deactivate_moderator(
    moderator_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Desactiva moderador."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().deactivate_moderator(moderator_id, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.post("/moderation/bans")
def laim_forum_create_ban(
    payload: LaimForumBanRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Banea usuario en subcategoría."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().create_ban(payload.model_dump(), session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.post("/moderation/bans/{ban_id}/revoke")
def laim_forum_revoke_ban(
    ban_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Revoca baneo."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().revoke_ban(ban_id, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )


@router.get("/moderation/logs/{subcategory_id}")
def laim_forum_moderation_logs(
    subcategory_id: str,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Logs de moderación."""
    session = _require_session(authorization, session_token)
    return _raise_if_failed(
        get_laim_forum_service().list_moderation_logs(subcategory_id, session),
        default_status=status.HTTP_403_FORBIDDEN,
    )

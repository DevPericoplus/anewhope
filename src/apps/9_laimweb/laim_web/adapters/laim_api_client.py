"""Cliente HTTP para LAIM Web → Middleware.

Todas las peticiones se envían al middleware (puerto 8007) siguiendo
el flujo arquitectónico obligatorio:

  LAIM Web (8009) → Middleware (8007) → Broker (8008) → Backend Core (8003)
                                                       → fmanagement (1666)

El único atajo permitido es fmanagement para operaciones de ficheros,
gestionado internamente por el backend core.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any

import httpx

from laim_web.dynamic_import import load_module_from_path

RENEWAL_THRESHOLD_SECONDS = 120

# Cargar env_settings para obtener URL del middleware
_env_settings_path = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "2_shared_application"
    / "config"
    / "env_settings.py"
)
_env_settings = load_module_from_path(_env_settings_path, "env_settings_laim_api")


def _get_middleware_base_url() -> str:
    """Obtiene la URL base del middleware desde env.yaml."""
    return _env_settings.get_env_value("middleware_base_url", "http://localhost:8007")


def get_laim_site_asset_url(asset_key: str) -> str:
    """Construye URL pública de un asset del sitio.

    En producción usa ``laimweb_api_url`` (HTTPS, mismo dominio) con proxy nginx
    hacia middleware. En desarrollo local usa middleware directo o fallback estático.
    """
    normalized = asset_key.strip().lower()
    fallback = "/presentacion_hero.png" if normalized == "presentacion-hero" else ""

    public_base = _env_settings.get_env_value("laimweb_api_url", "").strip().rstrip("/")
    if public_base.startswith("https://"):
        return f"{public_base}/laim/site/assets/{normalized}"

    base_url = _get_middleware_base_url().strip().rstrip("/")
    if base_url:
        return f"{base_url}/laim/site/assets/{normalized}"
    return fallback


def _request_middleware(
    method: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
    access_token: str = "",
    session_token: str = "",
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Ejecuta una petición HTTP al middleware.

    Propaga headers de autenticación y trazabilidad.
    """
    base_url = _get_middleware_base_url()
    url = f"{base_url}{endpoint}"

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Client-App": "laimweb",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method=method,
                url=url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        try:
            body = exc.response.json()
            if isinstance(body, dict):
                detail = body.get("detail", body.get("error", detail))
        except ValueError:
            pass
        return {
            "success": False,
            "error": str(detail),
        }
    except httpx.RequestError as exc:
        return {"success": False, "error": f"Error de conexión: {exc}"}


def _forum_headers(access_token: str, session_token: str) -> dict[str, str]:
    """Headers comunes para peticiones al foro LAIM."""
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Client-App": "laimweb",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token
    return headers


def _request_forum(
    method: str,
    endpoint: str,
    *,
    access_token: str = "",
    session_token: str = "",
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Petición HTTP REST al subsistema foro vía middleware (sin ficheros locales)."""
    base_url = _get_middleware_base_url()
    url = f"{base_url}{endpoint}"
    headers = _forum_headers(access_token, session_token)

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method=method,
                url=url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            if not response.content:
                return {"success": True}
            data = response.json()
            if isinstance(data, dict):
                return data
            return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        try:
            body = exc.response.json()
            if isinstance(body, dict):
                detail = body.get("detail", body.get("error", detail))
        except ValueError:
            pass
        return {"success": False, "error": str(detail)}
    except httpx.RequestError as exc:
        return {"success": False, "error": f"Error de conexión: {exc}"}


def laim_forum_get_image_data_url(
    image_id: int,
    access_token: str,
    session_token: str,
) -> str:
    """Obtiene imagen del foro como data URL (para mostrar en UI autenticada)."""
    base_url = _get_middleware_base_url()
    url = f"{base_url}/laim/forum/images/{image_id}"
    headers = _forum_headers(access_token, session_token)
    headers.pop("Content-Type", None)

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            mime = response.headers.get("content-type", "image/png")
            encoded = base64.b64encode(response.content).decode("ascii")
            return f"data:{mime};base64,{encoded}"
    except (httpx.HTTPError, ValueError):
        return ""


def laim_forum_health() -> dict[str, Any]:
    """Estado público del subsistema foro."""
    return _request_forum("GET", "/laim/forum/health")


def laim_forum_list_categories(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Lista categorías del foro."""
    return _request_forum(
        "GET",
        "/laim/forum/categories",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_list_subcategories(
    access_token: str,
    session_token: str,
    category_id: str | None = None,
) -> dict[str, Any]:
    """Lista subcategorías, opcionalmente filtradas por categoría."""
    endpoint = "/laim/forum/subcategories"
    if category_id:
        endpoint = f"{endpoint}?category_id={category_id}"
    return _request_forum(
        "GET",
        endpoint,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_list_prefixes(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Lista prefijos de hilo."""
    return _request_forum(
        "GET",
        "/laim/forum/prefixes",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_list_threads(
    subcategory_id: str,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Lista hilos de una subcategoría."""
    return _request_forum(
        "GET",
        f"/laim/forum/subcategories/{subcategory_id}/threads",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_get_thread(
    thread_id: int,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Detalle de un hilo."""
    return _request_forum(
        "GET",
        f"/laim/forum/threads/{thread_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_create_thread(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Crea un hilo."""
    return _request_forum(
        "POST",
        "/laim/forum/threads",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_update_thread(
    thread_id: int,
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Actualiza un hilo."""
    return _request_forum(
        "PATCH",
        f"/laim/forum/threads/{thread_id}",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_delete_thread(
    thread_id: int,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Elimina un hilo."""
    return _request_forum(
        "DELETE",
        f"/laim/forum/threads/{thread_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_list_posts(
    thread_id: int,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Lista respuestas de un hilo."""
    return _request_forum(
        "GET",
        f"/laim/forum/threads/{thread_id}/posts",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_create_post(
    thread_id: int,
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Crea respuesta en un hilo."""
    return _request_forum(
        "POST",
        f"/laim/forum/threads/{thread_id}/posts",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_rate_post(
    post_id: int,
    valoracion: int,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Valora una respuesta (1-5)."""
    return _request_forum(
        "POST",
        f"/laim/forum/posts/{post_id}/rating",
        payload={"valoracion": valoracion},
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_my_threads(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Hilos del usuario autenticado."""
    return _request_forum(
        "GET",
        "/laim/forum/me/threads",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_my_posts(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Respuestas del usuario autenticado."""
    return _request_forum(
        "GET",
        "/laim/forum/me/posts",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_upload_image(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Sube imagen (adjunto o avatar)."""
    return _request_forum(
        "POST",
        "/laim/forum/images/upload",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
        timeout=90.0,
    )


def laim_forum_pending_notifications(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Notificaciones pendientes del foro."""
    return _request_forum(
        "GET",
        "/laim/forum/notifications/pending",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_ack_notifications(
    notification_ids: list[int],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Confirma entrega de notificaciones."""
    return _request_forum(
        "POST",
        "/laim/forum/notifications/ack",
        payload={"notification_ids": notification_ids},
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_settings(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Configuración de moderación (admin)."""
    return _request_forum(
        "GET",
        "/laim/forum/admin/settings",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_update_settings(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Actualiza configuración de moderación (admin)."""
    return _request_forum(
        "PATCH",
        "/laim/forum/admin/settings",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_upsert_category(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Crea o actualiza categoría (admin)."""
    return _request_forum(
        "PUT",
        "/laim/forum/categories",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_delete_category(
    category_id: str,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Elimina categoría (admin)."""
    return _request_forum(
        "DELETE",
        f"/laim/forum/categories/{category_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_upsert_subcategory(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Crea o actualiza subcategoría (admin)."""
    return _request_forum(
        "PUT",
        "/laim/forum/subcategories",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_delete_subcategory(
    subcategory_id: str,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Elimina subcategoría (admin)."""
    return _request_forum(
        "DELETE",
        f"/laim/forum/subcategories/{subcategory_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_get_profile(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Obtiene perfil de foro del usuario."""
    return _request_forum(
        "GET",
        "/laim/forum/profile",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_update_profile(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Actualiza perfil de foro."""
    return _request_forum(
        "PATCH",
        "/laim/forum/profile",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_list_avatar_catalog(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Lista avatares del catálogo."""
    return _request_forum(
        "GET",
        "/laim/forum/avatars/catalog",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_add_avatar_catalog(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Añade avatar al catálogo (admin)."""
    return _request_forum(
        "POST",
        "/laim/forum/avatars/catalog",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_update_thread(
    thread_id: int,
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Actualiza hilo (fijar, cerrar, editar)."""
    return _request_forum(
        "PATCH",
        f"/laim/forum/threads/{thread_id}",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_delete_thread(
    thread_id: int,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Elimina hilo."""
    return _request_forum(
        "DELETE",
        f"/laim/forum/threads/{thread_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_upsert_prefix(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Crea o actualiza prefijo (admin)."""
    return _request_forum(
        "PUT",
        "/laim/forum/prefixes",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_delete_prefix(
    prefix_id: str,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Elimina prefijo (admin)."""
    return _request_forum(
        "DELETE",
        f"/laim/forum/prefixes/{prefix_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_word_rules(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Lista reglas de palabras (admin)."""
    return _request_forum(
        "GET",
        "/laim/forum/admin/word-rules",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_create_word_rule(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Crea regla de palabra (admin)."""
    return _request_forum(
        "POST",
        "/laim/forum/admin/word-rules",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_update_word_rule(
    rule_id: int,
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Actualiza regla de palabra (admin)."""
    return _request_forum(
        "PATCH",
        f"/laim/forum/admin/word-rules/{rule_id}",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_delete_word_rule(
    rule_id: int,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Elimina regla de palabra (admin)."""
    return _request_forum(
        "DELETE",
        f"/laim/forum/admin/word-rules/{rule_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_allowed_urls(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Lista dominios permitidos (admin)."""
    return _request_forum(
        "GET",
        "/laim/forum/admin/allowed-urls",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_create_allowed_url(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Crea dominio permitido (admin)."""
    return _request_forum(
        "POST",
        "/laim/forum/admin/allowed-urls",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_delete_allowed_url(
    url_id: int,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Elimina dominio permitido (admin)."""
    return _request_forum(
        "DELETE",
        f"/laim/forum/admin/allowed-urls/{url_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_moderators(
    access_token: str,
    session_token: str,
    subcategory_id: str | None = None,
) -> dict[str, Any]:
    """Lista moderadores (admin)."""
    endpoint = "/laim/forum/admin/moderators"
    if subcategory_id:
        endpoint = f"{endpoint}?subcategory_id={subcategory_id}"
    return _request_forum(
        "GET",
        endpoint,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_assign_moderator(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Asigna moderador (admin)."""
    return _request_forum(
        "POST",
        "/laim/forum/admin/moderators",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_admin_deactivate_moderator(
    moderator_id: int,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Desactiva moderador (admin)."""
    return _request_forum(
        "DELETE",
        f"/laim/forum/admin/moderators/{moderator_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_create_ban(
    payload: dict[str, Any],
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Banea usuario en subcategoría."""
    return _request_forum(
        "POST",
        "/laim/forum/moderation/bans",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_revoke_ban(
    ban_id: int,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Revoca baneo."""
    return _request_forum(
        "POST",
        f"/laim/forum/moderation/bans/{ban_id}/revoke",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_moderation_logs(
    subcategory_id: str,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Logs de moderación de una subcategoría."""
    return _request_forum(
        "GET",
        f"/laim/forum/moderation/logs/{subcategory_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_forum_get_poll_interval_seconds() -> int:
    """Intervalo de polling del foro desde env.yaml."""
    raw = _env_settings.get_env_value("laim_forum_poll_interval_seconds", "30")
    try:
        return max(3, int(str(raw).strip()))
    except ValueError:
        return 30


def laim_login(username: str, password: str) -> dict[str, Any]:
    """Autentica un usuario a través del middleware.

    Flujo: LAIM Web → Middleware /laim/login → Broker → Backend Core
    """
    return _request_middleware(
        "POST",
        "/laim/login",
        payload={"username": username, "password": password},
    )


def laim_register(
    username: str,
    password: str,
    password_confirm: str,
    email: str,
    full_name: str,
    mobile: str | None = None,
    hcaptcha_token: str = "",
) -> dict[str, Any]:
    """Registro público de usuario LAIM."""
    payload: dict[str, Any] = {
        "username": username,
        "password": password,
        "password_confirm": password_confirm,
        "email": email,
        "full_name": full_name,
        "hcaptcha_token": hcaptcha_token,
    }
    if mobile:
        payload["mobile"] = mobile
    return _request_middleware("POST", "/laim/register", payload=payload)


def laim_logout(access_token: str, session_token: str) -> dict[str, Any]:
    """Cierra sesión LAIM."""
    return _request_middleware(
        "POST",
        "/laim/logout",
        access_token=access_token,
        session_token=session_token,
    )


def laim_refresh_token(session_token: str) -> dict[str, Any]:
    """Renueva tokens LAIM."""
    return _request_middleware(
        "POST",
        "/laim/refresh-token",
        session_token=session_token,
    )


def _should_renew_token(expires_at: int) -> bool:
    """Indica si un token debe renovarse antes de expirar."""
    if expires_at <= 0:
        return False
    return time.time() > (expires_at - RENEWAL_THRESHOLD_SECONDS)


def ensure_valid_tokens(
    access_token: str,
    session_token: str,
    access_expires_at: int,
    session_expires_at: int,
) -> dict[str, Any]:
    """Garantiza tokens válidos renovándolos si es necesario."""
    result: dict[str, Any] = {
        "renewed": False,
        "access_token": access_token,
        "session_token": session_token,
        "access_expires_at": access_expires_at,
        "session_expires_at": session_expires_at,
        "error": "",
    }

    if not _should_renew_token(access_expires_at):
        return result

    if _should_renew_token(session_expires_at):
        result["error"] = "La sesión ha expirado, por favor inicie sesión nuevamente"
        return result

    response = laim_refresh_token(session_token)
    if response.get("success") and response.get("access_token"):
        result["renewed"] = True
        result["access_token"] = response["access_token"]
        result["session_token"] = response.get("session_token", session_token)
        result["access_expires_at"] = int(response.get("access_expires_at", 0))
        result["session_expires_at"] = int(response.get("session_expires_at", 0))
        return result

    result["error"] = response.get("error", "No se pudieron renovar los tokens")
    return result


def laim_get_session_permissions(
    identity_type_id: int,
    access_token: str,
    session_token: str,
) -> dict[str, Any]:
    """Obtiene permisos de bajo nivel para el rol."""
    return _request_middleware(
        "GET",
        f"/laim/session/permissions?identity_type_id={identity_type_id}",
        access_token=access_token,
        session_token=session_token,
    )


def laim_get_status(
    access_token: str, session_token: str
) -> dict[str, Any]:
    """Obtiene el estado del sistema LAIM.

    Flujo: LAIM Web → Middleware /laim/status → Broker → Backend Core
    """
    return _request_middleware(
        "GET",
        "/laim/status",
        access_token=access_token,
        session_token=session_token,
    )


def laim_submit_contact_message(
    payload: dict[str, Any],
    access_token: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Envía un mensaje del formulario de contacto.

    Flujo: LAIM Web → Middleware /laim/contact/messages → Broker → Backend Core
    """
    return _request_middleware(
        "POST",
        "/laim/contact/messages",
        payload=payload,
        access_token=access_token,
        session_token=session_token,
        timeout=90.0,
    )

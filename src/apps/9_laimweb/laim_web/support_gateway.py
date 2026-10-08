"""Puerta interna /api/support/*: valida JWT, descifra, reenvía a middleware."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from laim_web.adapters.laim_api_client import laim_support_forward

_AUTH_PATH = (
    Path(__file__).resolve().parents[3]
    / "2_shared_application"
    / "security"
    / "laim_support_auth.py"
)
_spec = importlib.util.spec_from_file_location("laim_support_auth_web", _AUTH_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError("No se pudo cargar laim_support_auth")
_auth = importlib.util.module_from_spec(_spec)
sys.modules["laim_support_auth_web"] = _auth
_spec.loader.exec_module(_auth)

SupportAuthError = _auth.SupportAuthError
require_support_caller = _auth.require_support_caller
support_secret = _auth.support_secret
encrypt_support_payload = _auth.encrypt_support_payload
decrypt_support_payload = _auth.decrypt_support_payload


def _json_error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse({"success": False, "error": message}, status_code=status_code)


async def _handle_support(request: Request, downstream_path: str) -> Response:
    secret = support_secret()
    if not secret:
        return _json_error(503, "LAIM_SUPPORT_SECRET no configurado")
    try:
        require_support_caller(
            request.headers.get("authorization"),
            request.headers.get("x-laim-caller"),
            request.headers.get("x-client-app"),
            secret=secret,
        )
    except SupportAuthError as exc:
        return _json_error(401, str(exc))

    payload: dict[str, Any] | None = None
    if request.method in {"PATCH", "PUT", "POST"}:
        try:
            raw = await request.json()
        except Exception:
            return _json_error(400, "cuerpo JSON inválido")
        if not isinstance(raw, dict):
            return _json_error(400, "cuerpo JSON inválido")
        if "iv" in raw and "ct" in raw:
            try:
                payload = decrypt_support_payload(raw, secret)
            except SupportAuthError as exc:
                return _json_error(401, str(exc))
        else:
            return _json_error(400, "el cuerpo debe ir cifrado")

    authorization = request.headers.get("authorization") or ""
    result = laim_support_forward(
        request.method,
        downstream_path,
        authorization=authorization,
        payload=payload,
    )
    status_code = 200
    if not result.get("success", True) and "http_status" in result:
        status_code = int(result["http_status"])
    try:
        envelope = encrypt_support_payload(result, secret)
    except Exception:
        return JSONResponse(result, status_code=status_code)
    return JSONResponse({"enc": envelope}, status_code=status_code)


async def support_list_messages(request: Request) -> Response:
    params = {}
    for key in (
        "estado_clave",
        "query",
        "usage_mode",
        "has_image",
        "has_user",
        "cursor_created_at",
        "cursor_id",
        "limit",
    ):
        value = request.query_params.get(key)
        if value is not None:
            params[key] = value
    path = "/laim/support/messages"
    if params:
        path = f"{path}?{urlencode(params)}"
    return await _handle_support(request, path)


async def support_get_message(request: Request) -> Response:
    message_id = request.path_params.get("message_id")
    return await _handle_support(request, f"/laim/support/messages/{message_id}")


async def support_update_estado(request: Request) -> Response:
    message_id = request.path_params.get("message_id")
    return await _handle_support(request, f"/laim/support/messages/{message_id}")


async def support_replace_keywords(request: Request) -> Response:
    message_id = request.path_params.get("message_id")
    return await _handle_support(
        request, f"/laim/support/messages/{message_id}/keywords"
    )

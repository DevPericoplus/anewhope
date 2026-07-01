"""Endpoints FastAPI de contacto LAIM en Backend Core."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laim/contact", tags=["laim-contact"])

_laim_contact_path = Path(__file__).resolve().parent / "laim_contact_service.py"
_spec = importlib.util.spec_from_file_location("laim_contact_service_router", _laim_contact_path)
if _spec is None or _spec.loader is None:
    raise ImportError("No se pudo cargar laim_contact_service")
_laim_contact_module = importlib.util.module_from_spec(_spec)
sys.modules["laim_contact_service_router"] = _laim_contact_module
_spec.loader.exec_module(_laim_contact_module)

LaimContactService = _laim_contact_module.LaimContactService

_contact_service: LaimContactService | None = None


def get_laim_contact_service() -> LaimContactService:
    """Singleton del servicio de contacto LAIM."""
    global _contact_service
    if _contact_service is None:
        _contact_service = LaimContactService()
    return _contact_service


class LaimContactScreenshotRequest(BaseModel):
    """Captura adjunta en base64."""

    file_name: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=3, max_length=100)
    data_base64: str = Field(..., min_length=1)


class LaimContactMessageRequest(BaseModel):
    """Payload de formulario de contacto."""

    usage_mode: str = Field(..., min_length=1, max_length=50)
    affected_user_info: str = Field(default="", max_length=500)
    message_body: str = Field(..., min_length=10, max_length=10000)
    reply_email: str = Field(..., min_length=5, max_length=255)
    screenshot: LaimContactScreenshotRequest | None = None


def _request_metadata(request: Request) -> tuple[str, str]:
    """Extrae IP y user-agent."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip_address = forwarded.split(",")[0].strip() if forwarded else ""
    if not ip_address and request.client:
        ip_address = request.client.host
    user_agent = request.headers.get("User-Agent", "")
    return ip_address, user_agent


def _optional_user_context(
    authorization: str | None,
    session_token: str | None,
) -> dict[str, Any]:
    """Extrae contexto de usuario si hay sesión LAIM activa (opcional)."""
    if not session_token:
        return {}
    if not authorization or not authorization.startswith("Bearer "):
        return {}

    access_token = authorization.removeprefix("Bearer ").strip()
    if not access_token:
        return {}

    _auth_path = Path(__file__).resolve().parent / "laim_auth_service.py"
    _auth_spec = importlib.util.spec_from_file_location(
        "laim_auth_service_contact", _auth_path
    )
    if _auth_spec is None or _auth_spec.loader is None:
        return {}
    _auth_mod = importlib.util.module_from_spec(_auth_spec)
    sys.modules["laim_auth_service_contact"] = _auth_mod
    _auth_spec.loader.exec_module(_auth_mod)
    auth_service = _auth_mod.LaimAuthService()
    return auth_service.resolve_optional_session_context(access_token, session_token)


@router.post("/messages")
def laim_create_contact_message(
    request: Request,
    payload: LaimContactMessageRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Registra un mensaje del formulario de contacto (público, sesión opcional)."""
    ip_address, user_agent = _request_metadata(request)
    user_context = _optional_user_context(authorization, session_token)
    service = get_laim_contact_service()
    result = service.create_contact_message(
        payload.model_dump(),
        user_context=user_context,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "No se pudo registrar el mensaje"),
        )
    return result

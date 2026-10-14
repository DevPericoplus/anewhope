"""Endpoints de captura de auditoría del portal laimweb."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laim/auditoria", tags=["laim-auditoria"])

_svc_path = Path(__file__).resolve().parent / "laim_auditoria_service.py"
_spec = importlib.util.spec_from_file_location("laim_auditoria_service_router", _svc_path)
_svc_mod = importlib.util.module_from_spec(_spec)
sys.modules["laim_auditoria_service_router"] = _svc_mod
_spec.loader.exec_module(_svc_mod)
LaimAuditoriaService = _svc_mod.LaimAuditoriaService

_auditoria_service: LaimAuditoriaService | None = None


def get_laim_auditoria_service() -> LaimAuditoriaService:
    global _auditoria_service
    if _auditoria_service is None:
        _auditoria_service = LaimAuditoriaService()
    return _auditoria_service


class HeartbeatRequest(BaseModel):
    seccion: str | None = None


class SeccionRequest(BaseModel):
    seccion: str = Field(..., min_length=1, max_length=32)


class InstaladorRequest(BaseModel):
    accion: str = Field(..., min_length=1, max_length=32)
    edition: str = Field(..., min_length=1, max_length=32)
    platform: str = Field(..., min_length=1, max_length=32)
    version: str = ""
    filename: str = ""


def _optional_user_context(
    authorization: str | None,
    session_token: str | None,
) -> dict[str, Any]:
    if not session_token or not authorization or not authorization.startswith("Bearer "):
        return {}
    access_token = authorization.removeprefix("Bearer ").strip()
    if not access_token:
        return {}
    auth_path = Path(__file__).resolve().parent / "laim_auth_service.py"
    auth_spec = importlib.util.spec_from_file_location("laim_auth_service_auditoria", auth_path)
    auth_mod = importlib.util.module_from_spec(auth_spec)
    sys.modules["laim_auth_service_auditoria"] = auth_mod
    auth_spec.loader.exec_module(auth_mod)
    return auth_mod.LaimAuthService().resolve_optional_session_context(access_token, session_token)


def _required_user_context(
    authorization: str | None,
    session_token: str | None,
) -> dict[str, Any]:
    ctx = _optional_user_context(authorization, session_token)
    if not int(ctx.get("user_id") or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere sesión")
    return ctx


@router.post("/heartbeat")
def heartbeat(
    payload: HeartbeatRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    result = get_laim_auditoria_service().heartbeat(
        int(ctx["user_id"]),
        str(ctx.get("session_id") or session_token or ""),
        seccion=payload.seccion,
    )
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error"))
    return result


@router.post("/seccion")
def change_seccion(
    payload: SeccionRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    result = get_laim_auditoria_service().change_seccion(
        int(ctx["user_id"]),
        str(ctx.get("session_id") or session_token or ""),
        payload.seccion,
    )
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error"))
    return result


@router.post("/instaladores")
def record_instalador(
    payload: InstaladorRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _optional_user_context(authorization, session_token)
    user_id = int(ctx.get("user_id") or 0) or None
    result = get_laim_auditoria_service().record_instalador(
        payload.accion,
        payload.edition,
        payload.platform,
        version=payload.version,
        filename=payload.filename,
        user_id=user_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error"))
    return result

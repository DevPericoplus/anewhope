"""Endpoints FastAPI de autenticación LAIM en Backend Core."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laim", tags=["laim-auth"])

_laim_auth_path = Path(__file__).resolve().parent / "laim_auth_service.py"
_spec = importlib.util.spec_from_file_location("laim_auth_service_router", _laim_auth_path)
if _spec is None or _spec.loader is None:
    raise ImportError("No se pudo cargar laim_auth_service")
_laim_auth_module = importlib.util.module_from_spec(_spec)
sys.modules["laim_auth_service_router"] = _laim_auth_module
_spec.loader.exec_module(_laim_auth_module)

LaimAuthService = _laim_auth_module.LaimAuthService

_auth_service: LaimAuthService | None = None


def get_laim_auth_service() -> LaimAuthService:
    """Singleton del servicio de auth LAIM."""
    global _auth_service
    if _auth_service is None:
        _auth_service = LaimAuthService()
    return _auth_service


class LaimLoginRequest(BaseModel):
    """Payload de login LAIM."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LaimRegisterRequest(BaseModel):
    """Payload de registro público LAIM."""

    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    password_confirm: str = Field(..., min_length=8)
    email: str = Field(..., min_length=5)
    full_name: str = Field(..., min_length=2)
    mobile: str | None = None
    hcaptcha_token: str = ""


def _request_metadata(request: Request) -> tuple[str, str]:
    """Extrae IP y user-agent."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip_address = forwarded.split(",")[0].strip() if forwarded else ""
    if not ip_address and request.client:
        ip_address = request.client.host
    user_agent = request.headers.get("User-Agent", "")
    return ip_address, user_agent


@router.post("/login")
def laim_login(request: Request, payload: LaimLoginRequest) -> dict[str, Any]:
    """Autentica usuario LAIM."""
    ip_address, user_agent = _request_metadata(request)
    service = get_laim_auth_service()
    result = service.login(
        user_name=payload.username,
        password=payload.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error,
        )
    return result.to_dict()


@router.post("/register")
def laim_register(request: Request, payload: LaimRegisterRequest) -> dict[str, Any]:
    """Registro público de usuario LAIM."""
    ip_address, user_agent = _request_metadata(request)
    service = get_laim_auth_service()
    result = service.register(
        user_name=payload.username,
        password=payload.password,
        password_confirm=payload.password_confirm,
        user_email=payload.email,
        full_name=payload.full_name,
        user_mobile=payload.mobile,
        hcaptcha_token=payload.hcaptcha_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Error en registro"),
        )
    return result


@router.post("/logout")
def laim_logout(
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Cierra sesión LAIM."""
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de sesión no proporcionado",
        )
    service = get_laim_auth_service()
    return service.logout(session_token)


@router.post("/refresh-token")
def laim_refresh_token(
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Renueva tokens LAIM."""
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de sesión no proporcionado",
        )
    service = get_laim_auth_service()
    result = service.refresh(session_token)
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error,
        )
    return result.to_dict()


@router.get("/session/permissions")
def laim_session_permissions(
    identity_type_id: int,
) -> dict[str, Any]:
    """Obtiene permisos de bajo nivel para un rol LAIM."""
    service = get_laim_auth_service()
    return service.get_session_permissions(identity_type_id)


@router.get("/status")
def laim_status() -> dict[str, Any]:
    """Estado del subsistema LAIM."""
    service = get_laim_auth_service()
    return service.get_status()

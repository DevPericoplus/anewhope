"""Endpoints de usuario autenticado para tickets de soporte LAIM."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laim/tickets", tags=["laim-tickets"])

_svc_path = Path(__file__).resolve().parent / "laim_tickets_service.py"
_spec = importlib.util.spec_from_file_location("laim_tickets_service_router", _svc_path)
_svc_mod = importlib.util.module_from_spec(_spec)
sys.modules["laim_tickets_service_router"] = _svc_mod
_spec.loader.exec_module(_svc_mod)
LaimTicketsService = _svc_mod.LaimTicketsService

_tickets_service: LaimTicketsService | None = None


def get_laim_tickets_service() -> LaimTicketsService:
    global _tickets_service
    if _tickets_service is None:
        _tickets_service = LaimTicketsService()
    return _tickets_service


class TicketCreateRequest(BaseModel):
    subject: str = Field(..., min_length=5, max_length=200)
    body: str = Field(..., min_length=10, max_length=10000)


class TicketReplyRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)


def _required_user_context(
    authorization: str | None,
    session_token: str | None,
) -> dict[str, Any]:
    if not session_token or not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere sesión")
    access_token = authorization.removeprefix("Bearer ").strip()
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere sesión")

    _auth_path = Path(__file__).resolve().parent / "laim_auth_service.py"
    _auth_spec = importlib.util.spec_from_file_location("laim_auth_service_tickets", _auth_path)
    _auth_mod = importlib.util.module_from_spec(_auth_spec)
    sys.modules["laim_auth_service_tickets"] = _auth_mod
    _auth_spec.loader.exec_module(_auth_mod)
    ctx = _auth_mod.LaimAuthService().resolve_optional_session_context(access_token, session_token)
    if not int(ctx.get("user_id") or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere sesión")

    user = _auth_mod.LaimAuthService()._user_repo.get_user_by_id(int(ctx["user_id"]))
    if user is not None:
        ctx["user_email"] = getattr(user, "user_email", "") or ""
        if not ctx.get("user_name"):
            ctx["user_name"] = getattr(user, "user_name", "") or ""
    if not ctx.get("user_email"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere sesión")
    return ctx


@router.post("")
def create_ticket(
    payload: TicketCreateRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    result = get_laim_tickets_service().create_ticket(payload.model_dump(), ctx)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error"))
    return result


@router.get("")
def list_my_tickets(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    return get_laim_tickets_service().list_my_tickets(int(ctx["user_id"]))


@router.get("/notifications/pending")
def list_my_notifications(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    return get_laim_tickets_service().list_my_notifications(int(ctx["user_id"]))


@router.post("/notifications/{notif_id}/ack")
def ack_my_notification(
    notif_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    result = get_laim_tickets_service().ack_my_notification(notif_id, int(ctx["user_id"]))
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("error"))
    return result


@router.get("/{ticket_id}")
def get_my_ticket(
    ticket_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    result = get_laim_tickets_service().get_my_ticket(ticket_id, int(ctx["user_id"]))
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("error"))
    return result


@router.post("/{ticket_id}/messages")
def reply_my_ticket(
    ticket_id: int,
    payload: TicketReplyRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    result = get_laim_tickets_service().reply_as_user(
        ticket_id, int(ctx["user_id"]), str(ctx.get("user_name") or ""), payload.body
    )
    if not result.get("success"):
        code = (
            status.HTTP_404_NOT_FOUND
            if "no encontrado" in str(result.get("error", "")).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=result.get("error"))
    return result

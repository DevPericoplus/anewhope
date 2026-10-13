"""Endpoints internos de tickets para laim_maintenance (support_ops)."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laim/support/tickets", tags=["laim-support-tickets"])

_auth_path = (
    Path(__file__).resolve().parents[2]
    / "2_shared_application"
    / "security"
    / "laim_support_auth.py"
)
_auth_spec = importlib.util.spec_from_file_location("laim_support_auth_tickets_ops", _auth_path)
_auth = importlib.util.module_from_spec(_auth_spec)
sys.modules["laim_support_auth_tickets_ops"] = _auth
_auth_spec.loader.exec_module(_auth)
require_support_caller = _auth.require_support_caller
SupportAuthError = _auth.SupportAuthError

_svc_path = Path(__file__).resolve().parent / "laim_tickets_service.py"
_spec = importlib.util.spec_from_file_location("laim_tickets_service_ops", _svc_path)
_svc_mod = importlib.util.module_from_spec(_spec)
sys.modules["laim_tickets_service_ops"] = _svc_mod
_spec.loader.exec_module(_svc_mod)
LaimTicketsService = _svc_mod.LaimTicketsService

_tickets_service: LaimTicketsService | None = None


def get_laim_tickets_service() -> LaimTicketsService:
    global _tickets_service
    if _tickets_service is None:
        _tickets_service = LaimTicketsService()
    return _tickets_service


class TicketEstadoRequest(BaseModel):
    estado_clave: str = Field(..., min_length=1, max_length=50)
    actor: str = Field(default="laim_maintenance", max_length=128)
    reabrir: bool = False


class TicketReplyRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)
    actor: str = Field(default="laim_maintenance", max_length=128)


def _guard(authorization: str | None, caller_header: str | None, client_app: str | None) -> None:
    try:
        require_support_caller(authorization, caller_header, client_app)
    except SupportAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/dashboard")
def tickets_dashboard(
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    return get_laim_tickets_service().dashboard()


@router.get("")
def list_tickets(
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
    estado_clave: Annotated[str | None, Query()] = None,
    query: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    return get_laim_tickets_service().list_operator_tickets(
        estado_clave=estado_clave, query=query, limit=limit
    )


@router.get("/notifications")
def list_operator_notifications(
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    return get_laim_tickets_service().list_operator_notifications()


@router.post("/notifications/{notif_id}/ack")
def ack_operator_notification(
    notif_id: int,
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    result = get_laim_tickets_service().ack_operator_notification(notif_id)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("error"))
    return result


@router.get("/{ticket_id}")
def get_ticket(
    ticket_id: int,
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    result = get_laim_tickets_service().get_operator_ticket(ticket_id)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("error"))
    return result


@router.post("/{ticket_id}/messages")
def reply_ticket(
    ticket_id: int,
    payload: TicketReplyRequest,
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    result = get_laim_tickets_service().reply_as_operator(
        ticket_id, payload.actor, payload.body
    )
    if not result.get("success"):
        code = (
            status.HTTP_404_NOT_FOUND
            if "no encontrado" in str(result.get("error", "")).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=result.get("error"))
    return result


@router.patch("/{ticket_id}")
def patch_ticket(
    ticket_id: int,
    payload: TicketEstadoRequest,
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    service = get_laim_tickets_service()
    if payload.reabrir:
        result = service.reopen(ticket_id, payload.actor)
    else:
        result = service.change_status(ticket_id, payload.estado_clave, payload.actor)
    if not result.get("success"):
        code = (
            status.HTTP_404_NOT_FOUND
            if "no encontrado" in str(result.get("error", "")).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=result.get("error"))
    return result

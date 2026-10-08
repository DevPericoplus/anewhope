"""Endpoints internos de soporte LAIM en Backend Core.

Solo aceptan el JWT de herramienta (operation=support_ops) emitido por
laim_maintenance. El formulario público de Contacto sigue en
router_laim_contact.py y no pasa por aquí.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laim/support", tags=["laim-support"])

_auth_path = (
    Path(__file__).resolve().parents[2]
    / "2_shared_application"
    / "security"
    / "laim_support_auth.py"
)
_auth_spec = importlib.util.spec_from_file_location("laim_support_auth_router", _auth_path)
if _auth_spec is None or _auth_spec.loader is None:
    raise ImportError("No se pudo cargar laim_support_auth")
_auth = importlib.util.module_from_spec(_auth_spec)
sys.modules["laim_support_auth_router"] = _auth
_auth_spec.loader.exec_module(_auth)

SupportAuthError = _auth.SupportAuthError
require_support_caller = _auth.require_support_caller

_contact_path = Path(__file__).resolve().parent / "laim_contact_service.py"
_contact_spec = importlib.util.spec_from_file_location(
    "laim_contact_service_support", _contact_path
)
if _contact_spec is None or _contact_spec.loader is None:
    raise ImportError("No se pudo cargar laim_contact_service")
_contact_mod = importlib.util.module_from_spec(_contact_spec)
sys.modules["laim_contact_service_support"] = _contact_mod
_contact_spec.loader.exec_module(_contact_mod)

LaimContactService = _contact_mod.LaimContactService
_contact_service: LaimContactService | None = None


def get_laim_contact_service() -> LaimContactService:
    """Reutiliza el servicio de casos (misma tabla)."""
    global _contact_service
    if _contact_service is None:
        _contact_service = LaimContactService()
    return _contact_service


class SupportEstadoRequest(BaseModel):
    estado_clave: str = Field(..., min_length=1, max_length=50)
    actor: str = Field(default="laim_maintenance", max_length=128)


class SupportKeywordsRequest(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    fuente: str = Field(default="ia", max_length=16)


def _guard(
    authorization: str | None,
    caller_header: str | None,
    client_app: str | None,
) -> None:
    try:
        require_support_caller(authorization, caller_header, client_app)
    except SupportAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.get("/messages")
def list_support_messages(
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
    estado_clave: Annotated[str | None, Query()] = None,
    query: Annotated[str | None, Query()] = None,
    usage_mode: Annotated[str | None, Query()] = None,
    has_image: Annotated[bool | None, Query()] = None,
    has_user: Annotated[bool | None, Query()] = None,
    cursor_created_at: Annotated[str | None, Query()] = None,
    cursor_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, Any]:
    """Lista casos de contacto para laim_maintenance."""
    _guard(authorization, caller_header, client_app)
    return get_laim_contact_service().list_support_messages(
        estado_clave=estado_clave,
        query=query,
        usage_mode=usage_mode,
        has_image=has_image,
        has_user=has_user,
        cursor_created_at=cursor_created_at,
        cursor_id=cursor_id,
        limit=limit,
    )


@router.get("/messages/{message_id}")
def get_support_message(
    message_id: int,
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    """Detalle de un caso, con captura."""
    _guard(authorization, caller_header, client_app)
    result = get_laim_contact_service().get_support_message(message_id)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("error"))
    return result


@router.patch("/messages/{message_id}")
def update_support_estado(
    message_id: int,
    payload: SupportEstadoRequest,
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    """Cambia el estado de un caso."""
    _guard(authorization, caller_header, client_app)
    result = get_laim_contact_service().update_support_estado(
        message_id, payload.estado_clave, actor=payload.actor
    )
    if not result.get("success"):
        code = (
            status.HTTP_404_NOT_FOUND
            if "no encontrado" in str(result.get("error", "")).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=result.get("error"))
    return result


@router.put("/messages/{message_id}/keywords")
def replace_support_keywords(
    message_id: int,
    payload: SupportKeywordsRequest,
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    """Sustituye las keywords IA/manual de un caso."""
    _guard(authorization, caller_header, client_app)
    result = get_laim_contact_service().replace_support_keywords(
        message_id, payload.keywords, fuente=payload.fuente
    )
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("error"))
    return result

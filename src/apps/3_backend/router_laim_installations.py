"""Registro de instalaciones: sesión del portal + propuesta cifrada desde laim."""

from __future__ import annotations

import importlib.util
import logging
import sys
import time
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laim/installations", tags=["laim-installations"])

_svc_path = Path(__file__).resolve().parent / "laim_installations_service.py"
_spec = importlib.util.spec_from_file_location("laim_installations_service_router", _svc_path)
_svc_mod = importlib.util.module_from_spec(_spec)
sys.modules["laim_installations_service_router"] = _svc_mod
_spec.loader.exec_module(_svc_mod)
LaimInstallationsService = _svc_mod.LaimInstallationsService
InstallationsError = _svc_mod.InstallationsError

_tickets_path = Path(__file__).resolve().parent / "router_laim_tickets.py"
_t_spec = importlib.util.spec_from_file_location("router_laim_tickets_installations", _tickets_path)
_t_mod = importlib.util.module_from_spec(_t_spec)
sys.modules["router_laim_tickets_installations"] = _t_mod
_t_spec.loader.exec_module(_t_mod)
_required_user_context = _t_mod._required_user_context

_install_svc: LaimInstallationsService | None = None
_PROPOSE_HITS: dict[str, list[float]] = {}


def get_installations_service() -> LaimInstallationsService:
    global _install_svc
    if _install_svc is None:
        _install_svc = LaimInstallationsService()
    return _install_svc


class SerialRequest(BaseModel):
    serial_number: str = Field(..., min_length=8, max_length=64)


class ManualRegisterRequest(BaseModel):
    serial_number: str = Field(..., min_length=8, max_length=64)
    hostname: str = Field(..., min_length=1, max_length=255)
    operating_system: str = Field(..., min_length=3, max_length=16)
    edition: str = Field(default="community_edition", max_length=32)
    display_name: str = Field(default="", max_length=80)


class UpdateInstallRequest(BaseModel):
    operating_system: str = Field(..., min_length=3, max_length=16)
    edition: str = Field(default="community_edition", max_length=32)
    hostname: str | None = None
    serial_number: str | None = None
    display_name: str | None = None


class ProposeEnvelope(BaseModel):
    v: str
    iv: str
    ct: str


def _fail(result: dict[str, Any]) -> dict[str, Any]:
    """El hop 7→8→3 trata un 4xx del core como 502. Los errores de negocio
    viajan en 200 con success=false; apife/apibe los convierten a 400."""
    return result


def _as_result(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, InstallationsError):
        return {"success": False, "error": exc.message}
    raise exc


def _rate_ok(ip: str, now: float, limit: int = 20, window: float = 60.0) -> bool:
    hits = [t for t in _PROPOSE_HITS.get(ip, []) if now - t < window]
    if len(hits) >= limit:
        _PROPOSE_HITS[ip] = hits
        return False
    hits.append(now)
    _PROPOSE_HITS[ip] = hits
    return True


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.get("")
def list_mine(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    return get_installations_service().list_mine(int(ctx["user_id"]))


@router.get("/notifications/pending")
def list_pending_notifications(
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    return get_installations_service().list_pending_notifications(int(ctx["user_id"]))


@router.post("/notifications/{notif_id}/ack")
def ack_notification(
    notif_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    return get_installations_service().ack_notification(int(ctx["user_id"]), notif_id)


@router.post("/verify")
def verify_serial(
    payload: SerialRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    return get_installations_service().verify(payload.serial_number, user_id=int(ctx["user_id"]))


@router.post("/propose")
def propose_from_laim(
    payload: ProposeEnvelope,
    request: Request,
    major_version: str = Query(default="2", max_length=8),
) -> dict[str, Any]:
    ip = _client_ip(request)
    if not _rate_ok(ip, time.time()):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Demasiadas propuestas")
    return _propose_encrypted(payload.model_dump(), major_version)


def _propose_encrypted(envelope: dict[str, Any], major_version: str) -> dict[str, Any]:
    shared = Path(__file__).resolve().parents[2] / "2_shared_application"
    crypto_path = shared / "security" / "laim_install_register.py"
    keys_path = shared / "adapters" / "laim_exchange_key.py"
    c_spec = importlib.util.spec_from_file_location("laim_install_register_router", crypto_path)
    c_mod = importlib.util.module_from_spec(c_spec)
    sys.modules["laim_install_register_router"] = c_mod
    c_spec.loader.exec_module(c_mod)
    k_spec = importlib.util.spec_from_file_location("laim_exch_install_router", keys_path)
    k_mod = importlib.util.module_from_spec(k_spec)
    sys.modules["laim_exch_install_router"] = k_mod
    k_spec.loader.exec_module(k_mod)
    svc = get_installations_service()
    engine = getattr(svc._users, "_engine", None)
    if engine is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Registro no disponible")
    keys = k_mod.LaimExchangeKeyRepository(engine)
    exchange = keys.get_current_key(major_version, key_kind="exchange")
    signing = keys.get_serial_signing_key()
    if exchange is None or signing is None:
        return {"success": False, "error": "Claves de registro no configuradas"}
    try:
        plain = c_mod.decrypt_install_payload(envelope, exchange.key_value, signing.key_value)
    except c_mod.InstallRegisterError as exc:
        return {"success": False, "error": str(exc)}
    result = svc.propose_from_laim(
        str(plain.get("user_name") or ""),
        str(plain.get("user_email") or ""),
        str(plain.get("serial_number") or ""),
        str(plain.get("hostname") or ""),
        str(plain.get("operating_system") or ""),
        str(plain.get("edition") or "community_edition"),
        display_name=str(plain.get("display_name") or ""),
    )
    return _fail(result)


@router.post("")
def register_manual(
    payload: ManualRegisterRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    result = get_installations_service().register_manual(
        int(ctx["user_id"]),
        payload.serial_number,
        payload.hostname,
        payload.operating_system,
        payload.edition,
        display_name=payload.display_name,
    )
    return _fail(result)


@router.patch("/{installation_id}")
def update_install(
    installation_id: int,
    payload: UpdateInstallRequest,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    try:
        result = get_installations_service().update(
            int(ctx["user_id"]),
            installation_id,
            payload.operating_system,
            payload.edition,
            hostname=payload.hostname,
            serial_number=payload.serial_number,
            display_name=payload.display_name,
        )
    except Exception as exc:
        return _as_result(exc)
    return _fail(result)


@router.post("/{installation_id}/recognize")
def recognize(
    installation_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    try:
        result = get_installations_service().recognize(int(ctx["user_id"]), installation_id)
    except Exception as exc:
        return _as_result(exc)
    return _fail(result)


@router.post("/{installation_id}/reject")
def reject(
    installation_id: int,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    ctx = _required_user_context(authorization, session_token)
    try:
        result = get_installations_service().reject(int(ctx["user_id"]), installation_id)
    except Exception as exc:
        return _as_result(exc)
    return _fail(result)

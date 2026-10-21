"""Endpoints internos de cuentas laimweb para laim_maintenance (support_ops)."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laim/support/users", tags=["laim-support-users"])

_auth_path = (
    Path(__file__).resolve().parents[2]
    / "2_shared_application"
    / "security"
    / "laim_support_auth.py"
)
_auth_spec = importlib.util.spec_from_file_location("laim_support_auth_users_ops", _auth_path)
_auth = importlib.util.module_from_spec(_auth_spec)
sys.modules["laim_support_auth_users_ops"] = _auth
_auth_spec.loader.exec_module(_auth)
require_support_caller = _auth.require_support_caller
SupportAuthError = _auth.SupportAuthError

_svc_path = Path(__file__).resolve().parent / "laim_users_ops_service.py"
_spec = importlib.util.spec_from_file_location("laim_users_ops_service_router", _svc_path)
_svc_mod = importlib.util.module_from_spec(_spec)
sys.modules["laim_users_ops_service_router"] = _svc_mod
_spec.loader.exec_module(_svc_mod)
LaimUsersOpsService = _svc_mod.LaimUsersOpsService

_users_service: LaimUsersOpsService | None = None


def get_users_ops_service() -> LaimUsersOpsService:
    global _users_service
    if _users_service is None:
        _users_service = LaimUsersOpsService()
    return _users_service


class UserProfileRequest(BaseModel):
    user_name: str = Field(..., min_length=3, max_length=255)
    user_email: str = Field(..., min_length=5, max_length=255)
    user_mobile: str | None = Field(default=None, max_length=20)
    full_name: str = Field(default="", max_length=200)


class UserPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8)
    password_confirm: str = Field(..., min_length=8)


class UserStatusRequest(BaseModel):
    blocked: bool


def _guard(authorization: str | None, caller_header: str | None, client_app: str | None) -> None:
    try:
        require_support_caller(authorization, caller_header, client_app)
    except SupportAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def _fail(result: dict[str, Any]) -> None:
    if result.get("success"):
        return
    detail = result.get("error", "error")
    code = (
        status.HTTP_404_NOT_FOUND
        if "no encontrado" in str(detail).lower()
        else status.HTTP_400_BAD_REQUEST
    )
    raise HTTPException(status_code=code, detail=detail)


@router.get("")
def list_users(
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
    query: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    return get_users_ops_service().list_users(query or "")


@router.get("/{user_id}")
def get_user(
    user_id: int,
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    result = get_users_ops_service().get_user(user_id)
    _fail(result)
    return result


@router.patch("/{user_id}")
def patch_user(
    user_id: int,
    payload: UserProfileRequest,
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    result = get_users_ops_service().update_profile(
        user_id,
        user_name=payload.user_name,
        user_email=payload.user_email,
        user_mobile=payload.user_mobile,
        full_name=payload.full_name,
    )
    _fail(result)
    return result


@router.post("/{user_id}/password")
def post_user_password(
    user_id: int,
    payload: UserPasswordRequest,
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    result = get_users_ops_service().update_password(
        user_id, payload.password, payload.password_confirm
    )
    _fail(result)
    return result


@router.post("/{user_id}/status")
def post_user_status(
    user_id: int,
    payload: UserStatusRequest,
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    result = get_users_ops_service().set_blocked(user_id, payload.blocked)
    _fail(result)
    return result

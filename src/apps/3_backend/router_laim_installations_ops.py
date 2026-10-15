"""Métricas e inventario de instalaciones para laim_maintenance (support_ops)."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laim/support/installations", tags=["laim-support-installations"])

_auth_path = (
    Path(__file__).resolve().parents[2]
    / "2_shared_application"
    / "security"
    / "laim_support_auth.py"
)
_auth_spec = importlib.util.spec_from_file_location("laim_support_auth_inst_ops", _auth_path)
_auth = importlib.util.module_from_spec(_auth_spec)
sys.modules["laim_support_auth_inst_ops"] = _auth
_auth_spec.loader.exec_module(_auth)
require_support_caller = _auth.require_support_caller
SupportAuthError = _auth.SupportAuthError

_svc_path = Path(__file__).resolve().parent / "laim_installations_service.py"
_spec = importlib.util.spec_from_file_location("laim_installations_service_ops", _svc_path)
_svc_mod = importlib.util.module_from_spec(_spec)
sys.modules["laim_installations_service_ops"] = _svc_mod
_spec.loader.exec_module(_svc_mod)
LaimInstallationsService = _svc_mod.LaimInstallationsService

_install_svc: LaimInstallationsService | None = None


def get_installations_ops_service() -> LaimInstallationsService:
    global _install_svc
    if _install_svc is None:
        _install_svc = LaimInstallationsService()
    return _install_svc


def _guard(authorization: str | None, caller_header: str | None, client_app: str | None) -> None:
    try:
        require_support_caller(authorization, caller_header, client_app)
    except SupportAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/metrics")
def installations_metrics(
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    return get_installations_ops_service().metrics_dashboard()


@router.get("")
def list_installations(
    authorization: Annotated[str | None, Header()] = None,
    caller_header: Annotated[str | None, Header(alias="X-Laim-Caller")] = None,
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> dict[str, Any]:
    _guard(authorization, caller_header, client_app)
    return get_installations_ops_service().list_all()

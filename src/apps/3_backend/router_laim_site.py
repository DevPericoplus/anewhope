"""Endpoints públicos de assets del sitio LAIM en Backend Core."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laim/site", tags=["laim-site"])

_storage_path = (
    Path(__file__).resolve().parents[2]
    / "2_shared_application"
    / "adapters"
    / "laim_site_asset_storage.py"
)
_spec = importlib.util.spec_from_file_location("laim_site_asset_storage_router", _storage_path)
if _spec is None or _spec.loader is None:
    raise ImportError("No se pudo cargar laim_site_asset_storage")
_storage_module = importlib.util.module_from_spec(_spec)
sys.modules["laim_site_asset_storage_router"] = _storage_module
_spec.loader.exec_module(_storage_module)

LaimSiteAssetStorage = _storage_module.LaimSiteAssetStorage

_storage: LaimSiteAssetStorage | None = None


def get_laim_site_asset_storage() -> LaimSiteAssetStorage:
    """Singleton del almacenamiento de assets del sitio."""
    global _storage
    if _storage is None:
        _storage = LaimSiteAssetStorage()
    return _storage


@router.get("/health")
def laim_site_health() -> dict[str, Any]:
    """Estado del subsistema de assets públicos (público)."""
    storage = get_laim_site_asset_storage()
    return {
        "status": "ok",
        "storage_path": str(storage.base_path),
        "registered_assets": list(_storage_module.REGISTERED_ASSETS.keys()),
    }


@router.get("/assets/{asset_key}")
def laim_site_get_asset(asset_key: str) -> Response:
    """Sirve un asset público del sitio (sin autenticación)."""
    storage = get_laim_site_asset_storage()
    result = storage.read_asset(asset_key)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset no encontrado",
        )

    content, mime_type = result
    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-LAIM-Asset-Key": asset_key.strip().lower(),
        },
    )

"""Tests del almacenamiento de assets públicos del sitio LAIM."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_storage_module():
    module_path = (
        Path(__file__).resolve().parents[3]
        / "2_shared_application"
        / "adapters"
        / "laim_site_asset_storage.py"
    )
    spec = importlib.util.spec_from_file_location("laim_site_asset_storage_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_site_asset_storage_test"] = module
    spec.loader.exec_module(module)
    return module


def test_read_and_write_presentacion_hero(tmp_path: Path) -> None:
    """Guarda y recupera el asset presentacion-hero."""
    module = _load_storage_module()
    storage = module.LaimSiteAssetStorage(base_path=tmp_path)
    payload = b"\x89PNG\r\n\x1a\nfake-image-bytes"

    target = storage.write_asset("presentacion-hero", payload)
    assert target is not None
    assert target.is_file()

    result = storage.read_asset("presentacion-hero")
    assert result is not None
    content, mime_type = result
    assert content == payload
    assert mime_type == "image/png"


def test_rejects_unknown_asset_key(tmp_path: Path) -> None:
    """Las claves no registradas no se resuelven."""
    module = _load_storage_module()
    storage = module.LaimSiteAssetStorage(base_path=tmp_path)

    assert storage.read_asset("no-existe") is None
    assert storage.write_asset("no-existe", b"data") is None

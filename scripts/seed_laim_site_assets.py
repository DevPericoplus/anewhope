#!/usr/bin/env python3
"""Copia assets públicos del sitio LAIM al almacenamiento del backend."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_storage_class():
    """Carga LaimSiteAssetStorage desde la capa compartida."""
    module_path = (
        ROOT_DIR / "src" / "2_shared_application" / "adapters" / "laim_site_asset_storage.py"
    )
    spec = importlib.util.spec_from_file_location("laim_site_asset_storage_seed", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar laim_site_asset_storage")
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_site_asset_storage_seed"] = module
    spec.loader.exec_module(module)
    return module.LaimSiteAssetStorage


SOURCE_ASSETS: dict[str, Path] = {
    "presentacion-hero": ROOT_DIR
    / "src"
    / "apps"
    / "9_laimweb"
    / "assets"
    / "presentacion_hero.png",
}


def main() -> int:
    """Escribe assets registrados en la ruta configurada por entorno."""
    storage_class = _load_storage_class()
    storage = storage_class()
    storage.ensure_base_directory()
    print(f"Destino: {storage.base_path}")

    for asset_key, source_path in SOURCE_ASSETS.items():
        if not source_path.is_file():
            print(f"ERROR: no existe origen para {asset_key}: {source_path}")
            return 1

        content = source_path.read_bytes()
        target = storage.write_asset(asset_key, content)
        if target is None:
            print(f"ERROR: no se pudo escribir asset {asset_key}")
            return 1
        print(f"OK {asset_key} -> {target} ({len(content)} bytes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

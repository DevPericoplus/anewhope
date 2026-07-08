"""Almacenamiento en filesystem de assets públicos del sitio LAIM."""

from __future__ import annotations

import importlib.util
import logging
import re
import sys
from pathlib import Path

_logger = logging.getLogger(__name__)

_ASSET_KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

MIME_BY_EXTENSION: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}

REGISTERED_ASSETS: dict[str, str] = {
    "presentacion-hero": "presentacion-hero.png",
}


def _load_env_settings():
    """Carga env_settings sin import circular."""
    module_path = Path(__file__).resolve().parents[1] / "config" / "env_settings.py"
    spec = importlib.util.spec_from_file_location("laim_site_env_settings", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar env_settings")
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_site_env_settings"] = module
    spec.loader.exec_module(module)
    return module


class LaimSiteAssetStorage:
    """Gestiona lectura/escritura de assets públicos del portal LAIM."""

    def __init__(self, base_path: str | Path | None = None) -> None:
        env_settings = _load_env_settings()
        raw_path = base_path or env_settings.get_env_value(
            "laim_site_storage_path",
            "~/data/anewhope/files/backend_server/laim/site",
        )
        self._base_path = Path(str(raw_path)).expanduser().resolve()

    @property
    def base_path(self) -> Path:
        """Ruta base de almacenamiento."""
        return self._base_path

    def ensure_base_directory(self) -> None:
        """Crea el directorio base si no existe."""
        self._base_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_valid_asset_key(asset_key: str) -> bool:
        """Valida formato seguro de clave de asset."""
        normalized = asset_key.strip().lower()
        return bool(normalized and _ASSET_KEY_PATTERN.fullmatch(normalized))

    def resolve_asset_path(self, asset_key: str) -> Path | None:
        """Resuelve ruta absoluta del asset registrado."""
        normalized = asset_key.strip().lower()
        if not self.is_valid_asset_key(normalized):
            return None

        file_name = REGISTERED_ASSETS.get(normalized)
        if file_name is None:
            return None

        candidate = (self._base_path / file_name).resolve()
        if not str(candidate).startswith(str(self._base_path)):
            return None
        return candidate

    def read_asset(self, asset_key: str) -> tuple[bytes, str] | None:
        """Lee bytes y MIME type de un asset registrado."""
        path = self.resolve_asset_path(asset_key)
        if path is None or not path.is_file():
            return None

        extension = path.suffix.lower()
        mime_type = MIME_BY_EXTENSION.get(extension, "application/octet-stream")
        content = path.read_bytes()
        if not content:
            return None
        return content, mime_type

    def write_asset(self, asset_key: str, content: bytes) -> Path | None:
        """Escribe o sobrescribe un asset registrado en disco."""
        path = self.resolve_asset_path(asset_key)
        if path is None:
            return None

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        _logger.info(
            "Asset LAIM guardado key=%s path=%s size=%s",
            asset_key,
            path,
            len(content),
        )
        return path

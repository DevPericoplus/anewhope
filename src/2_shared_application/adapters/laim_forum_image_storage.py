"""Almacenamiento en filesystem de imágenes del foro LAIM."""

from __future__ import annotations

import base64
import binascii
import hashlib
import importlib.util
import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

_logger = logging.getLogger(__name__)

ImageKind = Literal["avatar_catalog", "avatar_user", "post_attachment"]

ALLOWED_IMAGE_MIME_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
)

MIME_TO_EXTENSION: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _load_env_settings():
    """Carga env_settings sin import circular."""
    module_path = (
        Path(__file__).resolve().parents[1] / "config" / "env_settings.py"
    )
    spec = importlib.util.spec_from_file_location(
        "laim_forum_env_settings", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar env_settings")
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_forum_env_settings"] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True, slots=True)
class LaimForumStoredImage:
    """Resultado de persistir una imagen en disco."""

    storage_key: str
    file_name: str
    mime_type: str
    file_size: int
    checksum_sha256: str
    absolute_path: Path


class LaimForumImageStorage:
    """Gestiona lectura/escritura de imágenes del foro en el backend."""

    def __init__(self, base_path: str | Path | None = None) -> None:
        env_settings = _load_env_settings()
        raw_path = base_path or env_settings.get_env_value(
            "laim_forum_storage_path",
            "~/data/anewhope/files/backend_server/laim/forum",
        )
        self._base_path = Path(str(raw_path)).expanduser().resolve()
        self._max_bytes = int(
            env_settings.get_env_value("laim_forum_max_image_bytes", "5242880")
        )

    @property
    def base_path(self) -> Path:
        """Ruta base de almacenamiento."""
        return self._base_path

    def ensure_base_directory(self) -> None:
        """Crea el directorio base si no existe."""
        self._base_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def decode_base64_payload(data_base64: str) -> bytes:
        """Decodifica payload base64, tolerando prefijo data URI."""
        raw_b64 = data_base64.strip()
        if "," in raw_b64 and raw_b64.startswith("data:"):
            raw_b64 = raw_b64.split(",", 1)[1]
        return base64.b64decode(raw_b64, validate=True)

    def validate_upload(
        self,
        *,
        file_name: str,
        mime_type: str,
        data_base64: str,
    ) -> tuple[bytes | None, str | None]:
        """Valida y decodifica una subida de imagen."""
        normalized_mime = mime_type.strip().lower()
        if normalized_mime not in ALLOWED_IMAGE_MIME_TYPES:
            return None, "Formato de imagen no permitido. Use PNG, JPG, WEBP o GIF."

        safe_name = Path(file_name.strip() or "upload.bin").name
        if not safe_name:
            safe_name = "upload.bin"

        try:
            image_bytes = self.decode_base64_payload(data_base64)
        except (binascii.Error, ValueError):
            return None, "La imagen no es válida."

        if len(image_bytes) == 0:
            return None, "La imagen está vacía."

        if len(image_bytes) > self._max_bytes:
            max_mb = self._max_bytes // (1024 * 1024)
            return None, f"La imagen supera el tamaño máximo permitido ({max_mb} MB)."

        return image_bytes, None

    def build_storage_key(
        self,
        image_kind: ImageKind,
        *,
        user_id: int | None,
        extension: str,
    ) -> str:
        """Genera clave relativa única para el fichero."""
        token = uuid.uuid4().hex
        ext = extension if extension.startswith(".") else f".{extension}"

        if image_kind == "avatar_catalog":
            return f"avatars/catalog/{token}{ext}"
        if image_kind == "avatar_user":
            uid = user_id if user_id and user_id > 0 else 0
            return f"avatars/users/{uid}/{token}{ext}"

        now = datetime.now(timezone.utc)
        return f"attachments/{now:%Y/%m}/{token}{ext}"

    def save_image(
        self,
        *,
        image_kind: ImageKind,
        file_name: str,
        mime_type: str,
        data_base64: str,
        uploaded_by_user_id: int | None = None,
    ) -> tuple[LaimForumStoredImage | None, str | None]:
        """Valida, escribe en disco y retorna metadatos para BD."""
        image_bytes, error = self.validate_upload(
            file_name=file_name,
            mime_type=mime_type,
            data_base64=data_base64,
        )
        if error or image_bytes is None:
            return None, error

        normalized_mime = mime_type.strip().lower()
        extension = MIME_TO_EXTENSION.get(normalized_mime, ".bin")
        storage_key = self.build_storage_key(
            image_kind,
            user_id=uploaded_by_user_id,
            extension=extension,
        )
        target_path = self._base_path / storage_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(image_bytes)

        checksum = hashlib.sha256(image_bytes).hexdigest()
        stored = LaimForumStoredImage(
            storage_key=storage_key.replace("\\", "/"),
            file_name=Path(file_name.strip() or "upload.bin").name[:255],
            mime_type=normalized_mime,
            file_size=len(image_bytes),
            checksum_sha256=checksum,
            absolute_path=target_path,
        )
        _logger.info(
            "Imagen foro guardada kind=%s key=%s size=%s",
            image_kind,
            stored.storage_key,
            stored.file_size,
        )
        return stored, None

    def resolve_absolute_path(self, storage_key: str) -> Path:
        """Resuelve ruta absoluta desde storage_key (protección path traversal)."""
        normalized = storage_key.strip().replace("\\", "/").lstrip("/")
        candidate = (self._base_path / normalized).resolve()
        if not str(candidate).startswith(str(self._base_path)):
            raise ValueError("Ruta de imagen no permitida.")
        return candidate

    def read_image_bytes(self, storage_key: str) -> bytes | None:
        """Lee bytes de imagen desde disco."""
        try:
            path = self.resolve_absolute_path(storage_key)
        except ValueError:
            _logger.warning("Intento de lectura con storage_key inválida: %s", storage_key)
            return None
        if not path.is_file():
            return None
        return path.read_bytes()

    def delete_image_file(self, storage_key: str) -> bool:
        """Elimina fichero físico si existe."""
        try:
            path = self.resolve_absolute_path(storage_key)
        except ValueError:
            return False
        if not path.is_file():
            return False
        path.unlink()
        return True

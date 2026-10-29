"""Caché de imágenes del foro con endpoint proxy HTTP.

Elimina la necesidad de almacenar data URLs base64 en el estado de Reflex,
reduciendo drásticamente el tamaño del estado y mejorando la velocidad
de la interfaz. Las imágenes se sirven directamente al navegador vía
HTTP con cabeceras de caché apropiadas.

Flujo:
  1. Al abrir un hilo, ``prewarm_images()`` descarga imágenes al caché
     usando los tokens de sesión del usuario (servidor → daemon foro).
  2. El navegador solicita ``/api/forum-img/{id}`` (sin auth).
  3. El proxy responde desde el caché.

El caché vive en disco, no solo en la memoria del proceso. ``reflex run
--env prod`` arranca varios workers de Granian y el daemon exige sesión:
si la precarga cae en un worker y el GET del navegador en otro, la
memoria de ese otro está vacía y la descarga sin token responde 401.
En silicon (1.0.47) eso se vio como ``/api/forum-img/{id}`` 404.
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from pathlib import Path

import httpx

from laim_web.dynamic_import import load_module_from_path

_env_settings_path = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "2_shared_application"
    / "config"
    / "env_settings.py"
)
_env_settings = load_module_from_path(_env_settings_path, "env_settings_img_cache")

_MAX_CACHED_IMAGES = 200
_CACHE_TTL_SECONDS = 3600


def default_cache_dir() -> Path:
    """Directorio compartido por todos los workers del mismo contenedor."""
    return Path(
        os.environ.get("LAIM_FORUM_IMAGE_CACHE_DIR", "/tmp/laim_forum_image_cache")
    )


class _CachedImage:
    __slots__ = ("content", "mime_type", "fetched_at")

    def __init__(self, content: bytes, mime_type: str) -> None:
        self.content = content
        self.mime_type = mime_type
        self.fetched_at = time.monotonic()


class ForumImageCache:
    """Caché LRU de imágenes del foro, en memoria y en disco.

    La memoria evita releer el fichero en el mismo worker. El disco es
    lo que ven los demás workers del mismo contenedor.
    """

    def __init__(
        self,
        max_items: int = _MAX_CACHED_IMAGES,
        cache_dir: Path | None = None,
    ) -> None:
        self._max_items = max_items
        self._dir = cache_dir if cache_dir is not None else default_cache_dir()
        self._cache: OrderedDict[int, _CachedImage] = OrderedDict()
        self._lock = threading.Lock()

    def _paths(self, image_id: int) -> tuple[Path, Path]:
        base = self._dir / str(int(image_id))
        return Path(str(base) + ".bin"), Path(str(base) + ".mime")

    def _remember(self, image_id: int, entry: _CachedImage) -> _CachedImage:
        self._cache[image_id] = entry
        self._cache.move_to_end(image_id)
        while len(self._cache) > self._max_items:
            self._cache.popitem(last=False)
        return entry

    def _read_disk(self, image_id: int) -> _CachedImage | None:
        bin_path, mime_path = self._paths(image_id)
        if not bin_path.is_file() or not mime_path.is_file():
            return None
        age = time.time() - bin_path.stat().st_mtime
        if age > _CACHE_TTL_SECONDS:
            bin_path.unlink(missing_ok=True)
            mime_path.unlink(missing_ok=True)
            return None
        content = bin_path.read_bytes()
        if not content:
            return None
        mime = mime_path.read_text(encoding="utf-8").strip() or "application/octet-stream"
        return _CachedImage(content, mime)

    def _write_disk(self, image_id: int, content: bytes, mime_type: str) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        bin_path, mime_path = self._paths(image_id)
        tmp_bin = Path(str(bin_path) + ".tmp")
        tmp_mime = Path(str(mime_path) + ".tmp")
        tmp_mime.write_text(mime_type, encoding="utf-8")
        tmp_bin.write_bytes(content)
        os.replace(tmp_mime, mime_path)
        os.replace(tmp_bin, bin_path)
        self._prune_disk()

    def _prune_disk(self) -> None:
        files = sorted(
            self._dir.glob("*.bin"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for stale in files[self._max_items :]:
            stale.unlink(missing_ok=True)
            Path(str(stale).removesuffix(".bin") + ".mime").unlink(missing_ok=True)

    def get(self, image_id: int) -> _CachedImage | None:
        with self._lock:
            entry = self._cache.get(image_id)
            if entry is not None:
                age = time.monotonic() - entry.fetched_at
                if age > _CACHE_TTL_SECONDS:
                    self._cache.pop(image_id, None)
                    entry = None
                else:
                    self._cache.move_to_end(image_id)
                    return entry
            entry = self._read_disk(image_id)
            if entry is None:
                return None
            return self._remember(image_id, entry)

    def put(self, image_id: int, content: bytes, mime_type: str) -> None:
        if not content:
            return
        with self._lock:
            self._remember(image_id, _CachedImage(content, mime_type))
            self._write_disk(image_id, content, mime_type)

    def has(self, image_id: int) -> bool:
        return self.get(image_id) is not None


_global_cache = ForumImageCache()


def _get_forum_base_url() -> str:
    explicit = _env_settings.get_env_value("laim_forum_api_base_url", "").strip()
    if explicit:
        return explicit.rstrip("/")
    host = _env_settings.get_env_value("laim_forum_api_host", "127.0.0.1")
    port = _env_settings.get_env_value("laim_forum_api_port", "8766")
    return f"http://{host}:{port}"


def _fetch_from_daemon(
    image_id: int,
    access_token: str = "",
    session_token: str = "",
) -> tuple[bytes, str]:
    """Descarga imagen del daemon del foro con auth opcional."""
    base_url = _get_forum_base_url()
    url = f"{base_url}/laim/forum/images/{image_id}"

    headers: dict[str, str] = {"X-Client-App": "laimweb"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if session_token:
        headers["X-Session-Token"] = session_token

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            mime = response.headers.get("content-type", "image/png")
            return response.content, mime
    except (httpx.HTTPError, ValueError):
        return b"", ""


def prewarm_images(
    image_ids: list[int],
    access_token: str,
    session_token: str,
) -> None:
    """Pre-carga imágenes en la caché servidor usando tokens de sesión.

    Se llama al abrir un hilo para que el proxy pueda servir las imágenes
    sin necesidad de auth del navegador.
    """
    for img_id in image_ids:
        if _global_cache.has(img_id):
            continue
        content, mime = _fetch_from_daemon(img_id, access_token, session_token)
        if content:
            _global_cache.put(img_id, content, mime)


def fetch_forum_image(image_id: int) -> tuple[bytes, str]:
    """Obtiene imagen desde la caché (para el endpoint proxy HTTP).

    Returns:
        Tupla (contenido_bytes, mime_type). Vacía si no está en caché.
    """
    cached = _global_cache.get(image_id)
    if cached is not None:
        return cached.content, cached.mime_type

    content, mime = _fetch_from_daemon(image_id)
    if content:
        _global_cache.put(image_id, content, mime)
        return content, mime

    return b"", ""


def get_image_proxy_url(image_id: int) -> str:
    """URL del proxy local para una imagen del foro."""
    return f"/api/forum-img/{image_id}"

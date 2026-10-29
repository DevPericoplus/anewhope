"""La caché de imágenes del foro la ven todos los workers del contenedor."""

from __future__ import annotations

import os
import time
from pathlib import Path

from laim_web.forum_image_cache import ForumImageCache, _CACHE_TTL_SECONDS


def test_another_cache_reads_what_the_first_wrote(tmp_path: Path) -> None:
    writer = ForumImageCache(cache_dir=tmp_path)
    reader = ForumImageCache(cache_dir=tmp_path)
    payload = b"\x89PNG-forum-image"
    writer.put(18, payload, "image/png")
    reader._cache.clear()

    found = reader.get(18)
    assert found is not None
    assert found.content == payload
    assert found.mime_type == "image/png"


def test_expired_disk_entry_is_a_miss(tmp_path: Path) -> None:
    cache = ForumImageCache(cache_dir=tmp_path)
    cache.put(11, b"png", "image/png")
    bin_path = tmp_path / "11.bin"
    expired = time.time() - _CACHE_TTL_SECONDS - 5
    os.utime(bin_path, (expired, expired))
    cache._cache.clear()

    assert cache.get(11) is None
    assert not bin_path.exists()


def test_empty_content_is_not_stored(tmp_path: Path) -> None:
    cache = ForumImageCache(cache_dir=tmp_path)
    cache.put(1, b"", "image/png")
    assert cache.get(1) is None

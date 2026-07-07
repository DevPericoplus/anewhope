#!/usr/bin/env python3
"""Semilla del catálogo de avatares del foro LAIM.

Copia avatares PNG al storage del foro y registra entradas en
``laim_forum_images`` + ``laim_forum_avatar_catalog``. Idempotente: si ya hay
entradas activas en el catálogo, no hace nada.

Uso (desde la raíz del repo, con entorno backend activo):

    PYTHONPATH=. .venv_backend313/bin/python scripts/seed_laim_forum_avatar_catalog.py
"""

from __future__ import annotations

import base64
import importlib.util
import logging
import struct
import sys
import zlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / "src" / "apps" / "9_laimweb" / "assets" / "forum_avatars"

DEFAULT_AVATARS: list[tuple[str, tuple[int, int, int], bool]] = [
    ("Terminal", (125, 255, 125), True),
    ("Cipher", (100, 220, 180), False),
    ("Node", (80, 200, 140), False),
    ("Pulse", (140, 255, 160), False),
    ("Signal", (90, 230, 120), False),
    ("Vector", (110, 240, 150), False),
    ("Matrix", (70, 190, 110), False),
    ("Proxy", (130, 255, 170), False),
]

_logger = logging.getLogger("seed_laim_forum_avatars")


def _load_module(relative_path: str, module_name: str):
    """Carga un módulo Python desde ruta relativa al repo."""
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _build_avatar_png(accent: tuple[int, int, int], size: int = 64) -> bytes:
    """Genera PNG cuadrado estilo CRT (fondo oscuro + disco verde)."""
    bg = (8, 12, 8)
    cx, cy, radius = size // 2, size // 2, size // 2 - 6
    pixels = bytearray()
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist_sq = dx * dx + dy * dy
            if dist_sq <= radius * radius:
                row.extend(accent)
            elif dist_sq <= (radius + 2) * (radius + 2):
                row.extend((40, 90, 40))
            else:
                row.extend(bg)
        pixels.extend(row)
    compressed = zlib.compress(bytes(pixels), 9)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def _ensure_asset_files() -> list[tuple[Path, str, bool]]:
    """Crea PNGs en assets si no existen y devuelve (path, label, is_default)."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    items: list[tuple[Path, str, bool]] = []
    for index, (label, accent, is_default) in enumerate(DEFAULT_AVATARS, start=1):
        slug = label.lower().replace(" ", "-")
        path = ASSETS_DIR / f"avatar_{index:02d}_{slug}.png"
        if not path.is_file():
            path.write_bytes(_build_avatar_png(accent))
            _logger.info("Generado asset %s", path.name)
        items.append((path, label, is_default))
    return items


def _seed_catalog() -> int:
    """Inserta avatares en BD y filesystem. Retorna número de entradas creadas."""
    import os

    # En servidores backend, MariaDB escucha en localhost (como systemd del core).
    os.environ.setdefault("MARIADB_HOST", "localhost")

    repo_mod = _load_module(
        "src/2_shared_application/adapters/laim_forum_repository.py",
        "seed_laim_forum_repository",
    )
    image_mod = _load_module(
        "src/2_shared_application/adapters/laim_forum_image_storage.py",
        "seed_laim_forum_image_storage",
    )
    session_mod = _load_module(
        "src/2_shared_application/adapters/laim_mariadb_session_repository.py",
        "seed_laim_session_repo",
    )
    storage_mod = _load_module(
        "src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py",
        "seed_laim_storage",
    )

    settings = storage_mod.load_laim_mariadb_settings()
    engine = session_mod.create_laim_session_engine(settings)
    repository = repo_mod.LaimForumRepository(engine)
    storage = image_mod.LaimForumImageStorage()
    storage.ensure_base_directory()

    existing = repository.list_avatar_catalog(active_only=False)
    if existing:
        _logger.info(
            "Catálogo ya tiene %s entradas; omitiendo seed.", len(existing)
        )
        return 0

    created = 0
    for path, label, is_default in _ensure_asset_files():
        raw = path.read_bytes()
        data_b64 = base64.b64encode(raw).decode("ascii")
        stored, error = storage.save_image(
            image_kind="avatar_catalog",
            file_name=path.name,
            mime_type="image/png",
            data_base64=data_b64,
            uploaded_by_user_id=None,
        )
        if error or stored is None:
            raise RuntimeError(f"No se pudo guardar {path.name}: {error}")

        image_id = repository.insert_image(
            image_kind="avatar_catalog",
            storage_key=stored.storage_key,
            file_name=stored.file_name,
            mime_type=stored.mime_type,
            file_size=stored.file_size,
            uploaded_by_user_id=None,
            checksum_sha256=stored.checksum_sha256,
        )
        repository.insert_avatar_catalog_item(
            image_id=image_id,
            label=label,
            is_default=is_default,
            sort_order=created,
        )
        created += 1
        _logger.info("Catálogo: %s (image_id=%s, default=%s)", label, image_id, is_default)

    return created


def main() -> None:
    """Punto de entrada del script."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    count = _seed_catalog()
    if count:
        print(f"OK: {count} avatares añadidos al catálogo.")
    else:
        print("OK: catálogo sin cambios (ya poblado).")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Semilla del catálogo de avatares del foro LAIM.

Copia avatares PNG al storage del foro y registra entradas en
``laim_forum_images`` + ``laim_forum_avatar_catalog``. Idempotente: solo
inserta etiquetas que aún no existan (retratos LAIM + colección alohe/avatars).
Con ``--refresh-images`` sobrescribe los ficheros de entradas ya conocidas.

Uso (desde la raíz del repo, con entorno backend activo):

    PYTHONPATH=. .venv_backend313/bin/python scripts/seed_laim_forum_avatar_catalog.py
    PYTHONPATH=. .venv_backend313/bin/python scripts/seed_laim_forum_avatar_catalog.py --host mariadb
"""

from __future__ import annotations

import argparse
import base64
import importlib.util
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = REPO_ROOT / "src" / "apps" / "9_laimweb" / "assets" / "forum_avatars"
ALOHE_ASSETS_DIR = ASSETS_DIR / "alohe"
DEFAULT_MARIADB_HOST = "localhost"

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


def _load_avatar_art():
    """Carga el generador de avatares con iconos."""
    return _load_module(
        "src/2_shared_application/laim_forum_avatar_art.py",
        "seed_laim_forum_avatar_art",
    )


def _load_alohe_catalog():
    """Carga el catálogo ilustrado alohe/avatars."""
    return _load_module(
        "src/2_shared_application/laim_forum_alohe_avatars.py",
        "seed_laim_forum_alohe_avatars",
    )


def _ensure_laim_asset_files(*, force: bool = False) -> list[tuple[Path, str, bool, int]]:
    """Crea PNGs LAIM en assets y devuelve (path, label, is_default, sort_order)."""
    avatar_art = _load_avatar_art()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    items: list[tuple[Path, str, bool, int]] = []
    for index, (label, accent, is_default) in enumerate(
        avatar_art.DEFAULT_AVATAR_SPECS, start=1
    ):
        slug = label.lower().replace(" ", "-")
        path = ASSETS_DIR / f"avatar_{index:02d}_{slug}.png"
        if force or not path.is_file():
            path.write_bytes(avatar_art.build_avatar_png(label, accent))
            _logger.info("Generado asset %s", path.name)
        items.append((path, label, is_default, index - 1))
    return items


def _ensure_alohe_asset_files() -> list[tuple[Path, str, bool, int]]:
    """Valida PNGs vendorizados de alohe y devuelve (path, label, default, sort)."""
    alohe = _load_alohe_catalog()
    if not ALOHE_ASSETS_DIR.is_dir():
        raise RuntimeError(f"No existe el directorio de assets alohe: {ALOHE_ASSETS_DIR}")
    items: list[tuple[Path, str, bool, int]] = []
    missing: list[str] = []
    for spec in alohe.list_alohe_specs():
        path = ALOHE_ASSETS_DIR / str(spec["filename"])
        if not path.is_file() or path.stat().st_size < 100:
            missing.append(str(spec["filename"]))
            continue
        items.append(
            (
                path,
                str(spec["label"]),
                bool(spec["is_default"]),
                int(spec["sort_order"]),
            )
        )
    if missing:
        preview = ", ".join(missing[:8])
        raise RuntimeError(
            f"Faltan {len(missing)} PNG alohe en {ALOHE_ASSETS_DIR}: {preview}"
        )
    return items


def _ensure_asset_files(*, force: bool = False) -> list[tuple[Path, str, bool, int]]:
    """Crea/valida PNGs del catálogo completo (LAIM + alohe)."""
    return _ensure_laim_asset_files(force=force) + _ensure_alohe_asset_files()


def _png_bytes_for_label(label: str) -> bytes | None:
    """Obtiene bytes PNG de un label conocido (LAIM generado o alohe vendorizado)."""
    avatar_art = _load_avatar_art()
    specs_by_label = {
        spec_label: accent
        for spec_label, accent, _is_default in avatar_art.DEFAULT_AVATAR_SPECS
    }
    accent = specs_by_label.get(label)
    if accent is not None:
        return avatar_art.build_avatar_png(label, accent)
    alohe = _load_alohe_catalog()
    for spec in alohe.list_alohe_specs():
        if str(spec["label"]) != label:
            continue
        path = ALOHE_ASSETS_DIR / str(spec["filename"])
        if path.is_file():
            return path.read_bytes()
        return None
    return None


def _refresh_catalog_images(repository, storage) -> int:
    """Sobrescribe PNGs del catálogo existente con assets actualizados."""
    updated = 0
    for entry in repository.list_avatar_catalog(active_only=False):
        label = str(entry.get("label") or "")
        png_bytes = _png_bytes_for_label(label)
        if png_bytes is None:
            continue
        image_id = int(entry.get("image_id") or 0)
        if image_id <= 0:
            continue
        image = repository.get_image_by_id(image_id)
        if image is None:
            continue
        storage_key = str(image["storage_key"])
        storage.overwrite_image_file(storage_key, png_bytes)
        repository.update_image_file_meta(
            image_id=image_id,
            file_size=len(png_bytes),
            checksum_sha256=storage.compute_checksum(png_bytes),
        )
        updated += 1
        _logger.info("Actualizado avatar %s (image_id=%s)", label, image_id)
    return updated


def _seed_catalog(*, refresh_images: bool = False, mariadb_host: str = DEFAULT_MARIADB_HOST) -> int:
    """Inserta avatares en BD y filesystem. Retorna número de entradas creadas."""
    db_host = mariadb_host.strip() or DEFAULT_MARIADB_HOST
    os.environ["MARIADB_HOST"] = db_host

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
    settings = dict(settings)
    settings["host"] = db_host
    settings["admin_dsn"] = ""
    settings["writer_dsn"] = ""
    engine = session_mod.create_laim_session_engine(settings, role="admin")
    repository = repo_mod.LaimForumRepository(engine)
    storage = image_mod.LaimForumImageStorage()
    storage.ensure_base_directory()

    existing = repository.list_avatar_catalog(active_only=False)
    if refresh_images and existing:
        refreshed = _refresh_catalog_images(repository, storage)
        _logger.info("Imágenes del catálogo actualizadas: %s", refreshed)

    existing_labels = {str(entry.get("label") or "") for entry in existing}
    created = 0
    for path, label, is_default, sort_order in _ensure_asset_files(force=True):
        if label in existing_labels:
            continue
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
            sort_order=sort_order,
        )
        created += 1
        existing_labels.add(label)
        _logger.info("Catálogo: %s (image_id=%s, default=%s)", label, image_id, is_default)

    return created


def main() -> None:
    """Punto de entrada del script."""
    parser = argparse.ArgumentParser(description="Semilla del catálogo de avatares LAIM")
    parser.add_argument(
        "--refresh-images",
        action="store_true",
        help="Regenera PNGs con iconos y actualiza ficheros del catálogo existente",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_MARIADB_HOST,
        help="Host MariaDB (localhost en nativo; mariadb dentro de compose)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    _ensure_asset_files(force=args.refresh_images)
    count = _seed_catalog(refresh_images=args.refresh_images, mariadb_host=args.host)
    if count:
        print(f"OK: {count} avatares añadidos al catálogo.")
    elif args.refresh_images:
        print("OK: catálogo sin entradas nuevas; imágenes existentes refrescadas.")
    else:
        print("OK: catálogo sin cambios (ya poblado).")


if __name__ == "__main__":
    main()

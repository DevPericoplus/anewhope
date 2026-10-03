"""Instancia compartida de la caché de instaladores/parches de laim y sus
plugins — ver anewhope/AGENTS.md § 37.3. Extraído de laim_web.py para que
tanto las rutas HTTP (laim_web.py, para el navegador) como el estado Reflex
(laim_state.py, para la UI de "Notas del parche") usen el MISMO repositorio
de checksums y la misma caché en disco, sin import circular (laim_web.py ya
importa laim_state.py).

LAIM_READER_DSN: mismas credenciales laim_reader de solo lectura ya
desplegadas para middleware (ver routermiddleware.py.
_wrap_with_laim_session_repository) — si no está configurada, la caché sigue
sirviendo (product_cache.py degrada a "siempre re-fetch"), nunca sirve una
copia sin poder verificarla.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path

from laim_web.product_cache import ProductFileCache

logger = logging.getLogger(__name__)

PRODUCT_CACHE_DIR = Path(
    os.environ.get(
        "LAIM_PRODUCT_CACHE_DIR",
        str(Path(__file__).resolve().parent.parent / "product_cache"),
    )
)

_checksum_repo_for_cache = None
_checksum_repo_init_attempted = False


def get_product_checksum_repo():
    """Repositorio de checksums de solo lectura, construido una sola vez.
    None si LAIM_READER_DSN no está configurada o la conexión falla —
    product_cache.py trata None como "no puedo verificar", nunca como luz
    verde implícita."""
    global _checksum_repo_for_cache, _checksum_repo_init_attempted
    if _checksum_repo_init_attempted:
        return _checksum_repo_for_cache
    _checksum_repo_init_attempted = True

    reader_dsn = os.environ.get("LAIM_READER_DSN", "").strip()
    if not reader_dsn:
        logger.warning(
            "LAIM_READER_DSN no configurada — la caché de product_cache no podrá "
            "verificar copias existentes, siempre volverá a pedirlas a middleware."
        )
        return None
    try:
        checksum_mod_path = (
            Path(__file__).resolve().parents[3]
            / "2_shared_application" / "adapters" / "product_file_checksum.py"
        )
        checksum_spec = importlib.util.spec_from_file_location(
            "product_file_checksum_laimweb", checksum_mod_path
        )
        checksum_mod = importlib.util.module_from_spec(checksum_spec)
        sys.modules["product_file_checksum_laimweb"] = checksum_mod
        checksum_spec.loader.exec_module(checksum_mod)

        session_repo_mod_path = (
            Path(__file__).resolve().parents[3]
            / "2_shared_application" / "adapters" / "laim_mariadb_session_repository.py"
        )
        session_repo_spec = importlib.util.spec_from_file_location(
            "laim_mariadb_session_repository_laimweb", session_repo_mod_path
        )
        session_repo_mod = importlib.util.module_from_spec(session_repo_spec)
        sys.modules["laim_mariadb_session_repository_laimweb"] = session_repo_mod
        session_repo_spec.loader.exec_module(session_repo_mod)

        engine = session_repo_mod.create_laim_session_engine(
            {"reader_dsn": reader_dsn}, role="reader"
        )
        _checksum_repo_for_cache = checksum_mod.ProductFileChecksumRepository(engine)
        logger.info("[DDD] Repositorio de checksums de product_cache inicializado (solo lectura)")
    except Exception as exc:  # noqa: BLE001 - degradar, nunca romper el arranque de laimweb
        logger.warning("No se pudo inicializar el repositorio de checksums de product_cache: %s", exc)
        _checksum_repo_for_cache = None
    return _checksum_repo_for_cache


PRODUCT_FILE_CACHE = ProductFileCache(PRODUCT_CACHE_DIR, checksum_repo=None)


def refresh_checksum_repo() -> None:
    """Reasigna el repositorio de checksums (ya inicializado o None) a la
    instancia compartida de la caché — llamar antes de cada get_or_fetch* en
    caso de que la primera conexión fallara y queramos que un fallo
    transitorio de laim_core_db no quede "pegado" para siempre."""
    PRODUCT_FILE_CACHE._checksum_repo = get_product_checksum_repo()  # type: ignore[attr-defined]


def get_patch_notes_text(edition: str, version: str) -> str:
    """Devuelve el contenido (markdown, UTF-8) de las "Notas del parche"
    para edition/version — usa la MISMA caché verificada por checksum que
    `/api/product-cache/notes/download` (laim_web.py), llamada en proceso
    en vez de un salto HTTP a sí misma. Pensado para la UI de la Reflex
    State (laim_state.py), no para el navegador."""
    from laim_web.adapters.laim_api_client import fetch_laim_product_notes
    from laim_web.product_cache import FetchedArtifact

    refresh_checksum_repo()

    def fetch_fn() -> FetchedArtifact:
        content, sha256 = fetch_laim_product_notes(edition, version)
        return FetchedArtifact(content=content, sha256=sha256)

    cached_path = PRODUCT_FILE_CACHE.get_or_fetch_notes(edition, version, fetch_fn)
    return cached_path.read_text(encoding="utf-8")

"""Tests de "Notas del parche" en la caché de laimweb (product_cache.py).

Mismo mecanismo fail-closed que get_or_fetch/relative_artifact_path para
instaladores/parches binarios, pero sin dimensión de plataforma/tipo de
artefacto/plugin — ver apicore.py::download_laim_product_notes y AGENTS.md
§ "Página Parches y Notas del parche".
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from laim_web.product_cache import (
    FetchedArtifact,
    ProductCacheError,
    ProductFileCache,
    relative_notes_path,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _FakeChecksumRepo:
    """Doble de ProductFileChecksumRepository — verify_file configurable por test."""

    def __init__(self, verify_result: bool = True, raise_exc: Exception | None = None) -> None:
        self.verify_result = verify_result
        self.raise_exc = raise_exc
        self.calls: list[tuple[str, Path]] = []

    def verify_file(self, relative_path: str, path: Path) -> bool:
        self.calls.append((relative_path, path))
        if self.raise_exc:
            raise self.raise_exc
        return self.verify_result


def test_relative_notes_path_matches_backend_core_convention() -> None:
    assert relative_notes_path("community_edition", "2.0.1") == "community_edition/patches/notes/2.0.1.md"


def test_get_or_fetch_notes_cache_hit_returns_cached_without_fetching(tmp_path: Path) -> None:
    rel = relative_notes_path("community_edition", "2.0.1")
    cached = tmp_path / rel
    cached.parent.mkdir(parents=True)
    cached.write_text("## Notas cacheadas\n", encoding="utf-8")

    repo = _FakeChecksumRepo(verify_result=True)
    cache = ProductFileCache(tmp_path, checksum_repo=repo)

    def _fetch_fn() -> FetchedArtifact:
        raise AssertionError("no debería golpear middleware en un HIT")

    result = cache.get_or_fetch_notes("community_edition", "2.0.1", _fetch_fn)

    assert result == cached
    assert repo.calls == [(rel, cached)]


def test_get_or_fetch_notes_checksum_mismatch_refetches(tmp_path: Path) -> None:
    rel = relative_notes_path("community_edition", "2.0.1")
    cached = tmp_path / rel
    cached.parent.mkdir(parents=True)
    cached.write_text("## Notas viejas/sospechosas\n", encoding="utf-8")

    repo = _FakeChecksumRepo(verify_result=False)  # fail-closed: no coincide
    cache = ProductFileCache(tmp_path, checksum_repo=repo)

    fresh_content = b"## Notas frescas\n"
    fetch_calls = []

    def _fetch_fn() -> FetchedArtifact:
        fetch_calls.append(1)
        return FetchedArtifact(content=fresh_content, sha256=_sha256(fresh_content))

    result = cache.get_or_fetch_notes("community_edition", "2.0.1", _fetch_fn)

    assert len(fetch_calls) == 1
    assert result.read_bytes() == fresh_content


def test_get_or_fetch_notes_no_checksum_repo_always_refetches(tmp_path: Path) -> None:
    rel = relative_notes_path("community_edition", "2.0.1")
    cached = tmp_path / rel
    cached.parent.mkdir(parents=True)
    cached.write_text("## Notas sin poder verificar\n", encoding="utf-8")

    cache = ProductFileCache(tmp_path, checksum_repo=None)

    fresh_content = b"## Notas frescas\n"
    fetch_calls = []

    def _fetch_fn() -> FetchedArtifact:
        fetch_calls.append(1)
        return FetchedArtifact(content=fresh_content, sha256=None)

    result = cache.get_or_fetch_notes("community_edition", "2.0.1", _fetch_fn)

    assert len(fetch_calls) == 1
    assert result.read_bytes() == fresh_content


def test_get_or_fetch_notes_cache_miss_fetches_and_persists(tmp_path: Path) -> None:
    repo = _FakeChecksumRepo(verify_result=True)
    cache = ProductFileCache(tmp_path, checksum_repo=repo)

    content = b"## Notas 2.1.0\n\nPrimera entrada.\n"

    def _fetch_fn() -> FetchedArtifact:
        return FetchedArtifact(content=content, sha256=_sha256(content))

    result = cache.get_or_fetch_notes("community_edition", "2.1.0", _fetch_fn)

    assert result.is_file()
    assert result.read_bytes() == content
    assert result == tmp_path / relative_notes_path("community_edition", "2.1.0")


def test_get_or_fetch_notes_rejects_tampered_content_from_backend(tmp_path: Path) -> None:
    """Si el backend afirma un sha256 que no coincide con lo que de verdad
    escribimos en disco, es una señal de corrupción/sustitución en tránsito
    — nunca debe quedar servible en caché (ver AGENTS.md § seguridad de
    binarios cacheados)."""
    cache = ProductFileCache(tmp_path, checksum_repo=None)

    content = b"## Notas supuestamente de 2.1.0\n"

    def _fetch_fn() -> FetchedArtifact:
        return FetchedArtifact(content=content, sha256="0" * 64)  # sha256 falso/no coincide

    with pytest.raises(ProductCacheError):
        cache.get_or_fetch_notes("community_edition", "2.1.0", _fetch_fn)

    rel = relative_notes_path("community_edition", "2.1.0")
    assert not (tmp_path / rel).exists()

"""Caché en disco de laimweb para instaladores/parches de laim y sus plugins,
con verificación de integridad — ver anewhope/AGENTS.md § 37.3.

Sustituye el patrón anterior (el navegador iba directo a middleware,
saltándose laimweb por completo — ver get_laim_product_download_url en
laim_api_client.py). Ahora laimweb sirve desde una caché local en disco,
pidiendo el fichero a middleware (fuente de verdad) solo cuando no lo tiene
cacheado o cuando su copia no supera la verificación de checksum.

Fail-closed, igual que ProductFileChecksumRepository.verify_file(): sin
poder verificar, nunca se sirve una copia cacheada existente — se vuelve a
pedir fresca a middleware. Un fallo de conexión a laim_core_db no bloquea el
servicio (laimweb sigue funcionando, solo deja de poder confiar en su caché
y re-descarga más de lo estrictamente necesario), pero nunca se traduce en
"sirve la copia cacheada porque sí".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_PLATFORM_SEGMENTS = {
    "linux_deb": ("linux", "deb"),
    "linux_rpm": ("linux", "rpm"),
    "mac_intel": ("mac", "intel"),
    "mac_silicon": ("mac", "silicon"),
    "windows": ("windows",),
}


class ProductCacheError(Exception):
    """Error de negocio al servir/cachear un artefacto de producto."""


@dataclass(frozen=True, slots=True)
class FetchedArtifact:
    """Lo que la función de descarga remota (inyectada, ver fetch_fn) debe devolver."""

    content: bytes
    sha256: Optional[str]


def relative_artifact_path(
    edition: str,
    artifact_type: str,
    platform: str,
    version: str,
    filename: str,
    plugin_name: str = "",
) -> str:
    """Misma convención de ruta que backend_core (apicore.py
    _laim_product_leaf_dir) — para que el relative_path calzado aquí
    coincida exactamente con el que backend_core usó al persistir el
    checksum de referencia."""
    if platform not in _PLATFORM_SEGMENTS:
        raise ProductCacheError(f"Plataforma inválida: {platform!r}")
    parts = [edition]
    if plugin_name:
        parts += ["plugins", plugin_name]
    parts.append("patches" if artifact_type == "patch" else "installers")
    parts += list(_PLATFORM_SEGMENTS[platform])
    parts += [version, filename]
    return "/".join(parts)


class ProductFileCache:
    """cache_dir: raíz de la caché en disco (un volumen persistente del
    contenedor de laimweb). checksum_repo: opcional — si no hay conexión a
    laim_core_db disponible, se degrada a "siempre re-fetch" en vez de
    servir una copia sin poder verificarla."""

    def __init__(self, cache_dir: Path, checksum_repo: object | None = None) -> None:
        self._cache_dir = cache_dir
        self._checksum_repo = checksum_repo

    def get_or_fetch(
        self,
        edition: str,
        artifact_type: str,
        platform: str,
        version: str,
        filename: str,
        fetch_fn: Callable[[], FetchedArtifact],
        plugin_name: str = "",
    ) -> Path:
        """Devuelve la ruta a un fichero verificado y listo para servir —
        de la caché si es válida, recién descargado si no."""
        rel_path = relative_artifact_path(edition, artifact_type, platform, version, filename, plugin_name)
        cached_path = self._cache_dir / rel_path

        if cached_path.is_file() and self._verify(rel_path, cached_path):
            logger.info("product_cache HIT %s", rel_path)
            return cached_path

        logger.info("product_cache MISS %s — pidiendo a middleware", rel_path)
        artifact = fetch_fn()
        cached_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cached_path.with_suffix(cached_path.suffix + ".tmp")
        tmp_path.write_bytes(artifact.content)
        tmp_path.replace(cached_path)  # escritura atómica — nunca una copia a medio escribir

        if artifact.sha256:
            actual = _sha256_of(cached_path)
            if actual != artifact.sha256:
                # El propio backend nos dio un sha256 y no coincide con lo que
                # acabamos de escribir en disco — corrupción de transporte.
                # No servir esto nunca.
                cached_path.unlink(missing_ok=True)
                raise ProductCacheError(
                    f"Integridad fallida tras la descarga de {rel_path}: "
                    f"esperado {artifact.sha256}, obtenido {actual}"
                )
        return cached_path

    def _verify(self, rel_path: str, cached_path: Path) -> bool:
        if self._checksum_repo is None:
            logger.warning(
                "product_cache: sin conexión a laim_core_db, no se puede verificar %s — se trata como MISS",
                rel_path,
            )
            return False
        try:
            return bool(self._checksum_repo.verify_file(rel_path, cached_path))  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001 - fail-closed, nunca propaga como "sí es válido"
            logger.warning("product_cache: fallo verificando %s: %s — se trata como MISS", rel_path, exc)
            return False


def _sha256_of(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

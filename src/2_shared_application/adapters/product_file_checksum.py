"""SHA-256 de referencia de ficheros de producto/parche/plugin laim.

Persistencia real (laim_product_file_checksums, migración 025) — ver
anewhope/AGENTS.md § 37.3. Diseño de dos pasos:

1. backend_core (que ya monta LAIM_PRODUCT_STORAGE directamente) llama a
   `ensure_checksum()` la primera vez que sirve un fichero — lo calcula y
   lo persiste si no existía, lo reutiliza si ya estaba. No hace falta
   tocar el pipeline de publicación de laim_maintenance ni fmanagement
   (que no tiene conexión a MariaDB) para esto.
2. laimweb, antes de servir su copia cacheada en disco de ese mismo
   fichero, llama a `verify_file()` contra ese mismo valor — si no
   coincide, la copia se descarta (nunca se sirve) y laimweb vuelve a
   pedir el fichero fresco al backend, la fuente de verdad. La propia
   caché en disco de laimweb (sustituyendo el patrón en memoria de
   ForumImageCache) es la pieza que queda por construir — este módulo es
   la base de verificación que esa caché debe llamar, no la caché en sí.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

_HASH_CHUNK_SIZE = 1024 * 1024  # 1 MiB — no cargar ficheros grandes enteros en memoria


class ProductFileChecksumError(Exception):
    """Error de negocio al calcular/verificar un checksum."""


@dataclass(frozen=True, slots=True)
class StoredChecksum:
    relative_path: str
    sha256: str
    file_size_bytes: int


def compute_sha256(file_path: Path) -> tuple[str, int]:
    """Calcula el SHA-256 real de un fichero en disco, en streaming."""
    if not file_path.is_file():
        raise ProductFileChecksumError(f"No es un fichero regular: {file_path}")
    h = hashlib.sha256()
    size = 0
    with open(file_path, "rb") as f:
        while chunk := f.read(_HASH_CHUNK_SIZE):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


class ProductFileChecksumRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self, relative_path: str) -> Optional[StoredChecksum]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT relative_path, sha256, file_size_bytes "
                    "FROM laim_product_file_checksums WHERE relative_path = :p"
                ),
                {"p": relative_path},
            ).mappings().fetchone()
        if row is None:
            return None
        return StoredChecksum(
            relative_path=str(row["relative_path"]),
            sha256=str(row["sha256"]),
            file_size_bytes=int(row["file_size_bytes"]),
        )

    def store(self, relative_path: str, sha256: str, file_size_bytes: int) -> StoredChecksum:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_product_file_checksums
                        (relative_path, sha256, file_size_bytes)
                    VALUES (:p, :h, :s)
                    ON DUPLICATE KEY UPDATE
                        sha256 = VALUES(sha256),
                        file_size_bytes = VALUES(file_size_bytes),
                        computed_at = CURRENT_TIMESTAMP
                    """
                ),
                {"p": relative_path, "h": sha256, "s": file_size_bytes},
            )
        return StoredChecksum(relative_path=relative_path, sha256=sha256, file_size_bytes=file_size_bytes)

    def ensure_checksum(self, relative_path: str, backend_file_path: Path) -> StoredChecksum:
        """Devuelve el checksum de referencia, calculándolo y persistiéndolo
        si es la primera vez que se pide para esta ruta. Llamado por
        backend_core al servir un fichero de LAIM_PRODUCT_STORAGE."""
        existing = self.get(relative_path)
        if existing is not None:
            return existing
        sha256, size = compute_sha256(backend_file_path)
        return self.store(relative_path, sha256, size)

    def verify_file(self, relative_path: str, local_file_path: Path) -> bool:
        """True si local_file_path coincide con el checksum de referencia
        registrado para relative_path. False tanto si no coincide como si
        no hay ningún checksum de referencia registrado todavía (fail
        closed: sin referencia, no se puede afirmar que la copia sea
        buena) — el llamador (la caché de laimweb) debe tratar False como
        "no sirvas esta copia cacheada, pide el fichero fresco"."""
        reference = self.get(relative_path)
        if reference is None:
            return False
        if not local_file_path.is_file():
            return False
        actual_sha256, actual_size = compute_sha256(local_file_path)
        return actual_sha256 == reference.sha256 and actual_size == reference.file_size_bytes

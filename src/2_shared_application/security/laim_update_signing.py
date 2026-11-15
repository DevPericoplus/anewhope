"""Firma de las respuestas de /check_last_version (AGENTS.md § 37.2).

LAIM 3.2.10 (pkg139) solo da por buena una actualización cuya carga firmada
es exactamente

    edition|platform|patch|<latest_version>|<filename>|sha256=<hex>

con el SHA-256 del fichero que se sirve, firmada con HMAC-SHA256 y la clave
`exchange` del major. La huella (`exchange_key_fingerprint`) permite comparar
la clave de laimweb con la que lleva compilada LAIM sin revelar ninguna de
las dos: es el HMAC de una etiqueta pública fija, recortado a 16 hex. LAIM
debe calcular la misma función con `KeyExchageLaimApp`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import threading
from pathlib import Path

FINGERPRINT_LABEL = "laim-exchange-key-fingerprint/v1"
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_CHUNK = 1024 * 1024


def decode_exchange_key(key_b64: str) -> bytes:
    """Base64 URL-safe, con o sin relleno (igual que LAIM)."""
    text = (key_b64 or "").strip()
    raw = base64.b64decode(text + "=" * (-len(text) % 4), altchars=b"-_", validate=True)
    if not raw:
        raise ValueError("clave de intercambio vacía")
    return raw


def sign_update_payload(key_b64: str, payload: str) -> str:
    return hmac.new(decode_exchange_key(key_b64), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def exchange_key_fingerprint(key_b64: str) -> str:
    """Huella pública de la clave: HMAC-SHA256(clave, etiqueta fija)[:16]."""
    return sign_update_payload(key_b64, FINGERPRINT_LABEL)[:16]


def signed_update_payload(edition: str, platform: str, latest_version: str, filename: str, sha256_hex: str) -> str:
    if not isinstance(sha256_hex, str) or not _SHA256_HEX.match(sha256_hex):
        raise ValueError("SHA-256 del parche inválido: 64 hex en minúsculas")
    return "|".join([edition, platform, "patch", latest_version, filename, "sha256=" + sha256_hex])


def _sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


class FileSha256Cache:
    """SHA-256 de los parches publicados, recalculado solo si el fichero cambia
    (ruta real, tamaño y mtime). Un fichero que no existe no tiene SHA."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._known: dict[str, tuple[int, int, str]] = {}

    def sha256(self, path: Path) -> str | None:
        try:
            real = path.resolve(strict=True)
            stat = real.stat()
        except OSError:
            return None
        if not real.is_file():
            return None
        key = str(real)
        with self._lock:
            known = self._known.get(key)
        if known is not None and known[:2] == (stat.st_size, stat.st_mtime_ns):
            return known[2]
        try:
            value = _sha256_of_file(real)
        except OSError:
            return None
        with self._lock:
            self._known[key] = (stat.st_size, stat.st_mtime_ns, value)
        return value

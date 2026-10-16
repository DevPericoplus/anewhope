"""Verificación server-side del número de serie de `laim init`.

Espejo exacto de `laim/internal/utils/serial.go` (`VerifySerial`,
`serialScheme` 2, 10 bytes de payload, HMAC-SHA256 truncado a 4 bytes,
base32 sin padding). Cualquier diferencia rechazaría seriales genuinos.

La clave es `KeySerialSigning` (dirección inversa a `KeyExchageLaimApp`):
el cliente firma, el servidor verifica. Vive en `laim_exchange_keys`
(`key_kind=serial_signing`) y, si el deploy aún no ha sembrado la fila,
`product_serial_signing_key()` (el mismo valor que `laim init` embebe).
El AES del propose usa `product_exchange_key()` igual, si no hay fila
`exchange`. Un Update no rellena SQL; sin este fallback el Registro queda ciego.
"""

from __future__ import annotations

import base64
import hmac
import hashlib
import re

SERIAL_SCHEME = "2"
SERIAL_PAYLOAD_BYTES = 10
SERIAL_CHECK_BYTES = 4
# Misma constante que KeySerialSigning en laim/internal/utils/version.go.
# No es un secreto de servidor: viaja en cada binario laim. El test
# test_product_key_matches_version_go falla si divergen.
_PRODUCT_SERIAL_SIGNING_KEY = "d8nKoxuTtrbLytUew0zybWAoukxyn7flmgiLjLn5oHQ="
# KeyExchageLaimApp: AES del propose y HMAC de /check_last_version.
_PRODUCT_EXCHANGE_KEY = "K8aoQdKlbOzk-Qd82pqqlQGTtfnAa3DLUtbrrHv_cgM="


def decode_exchange_key(key: str) -> bytes:
    """Mismo pad + URL-safe base64 que `decodeExchangeKey` en update_check.go."""
    padded = key + ("=" * ((4 - len(key) % 4) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _b32decode_nopad(value: str) -> bytes:
    """encoding/base32.StdEncoding.WithPadding(NoPadding) equivalent."""
    raw = value.upper().encode("ascii")
    pad = b"=" * ((8 - len(raw) % 8) % 8)
    return base64.b32decode(raw + pad)


def parse_serial(serial: str) -> tuple[str, bytes, bytes] | None:
    parts = (serial or "").strip().split("-")
    if len(parts) < 3:
        return None
    scheme = parts[0]
    check_str = parts[-1]
    body_str = "".join(parts[1:-1])
    try:
        payload = _b32decode_nopad(body_str)
        check = _b32decode_nopad(check_str)
    except Exception:
        return None
    return scheme, payload, check


def serial_check(payload: bytes, key_b64: str) -> bytes:
    key_bytes = decode_exchange_key(key_b64)
    digest = hmac.new(key_bytes, payload, hashlib.sha256).digest()
    return digest[:SERIAL_CHECK_BYTES]


def format_serial(payload: bytes, check: bytes) -> str:
    body = base64.b32encode(payload).decode("ascii").rstrip("=")
    chk = base64.b32encode(check).decode("ascii").rstrip("=")
    groups = [SERIAL_SCHEME]
    for i in range(0, len(body), 4):
        groups.append(body[i : i + 4])
    groups.append(chk)
    return "-".join(groups)


def generate_serial(key_b64: str) -> str:
    """Solo tests / interop. El producto usa GenerateLaimSerial en Go."""
    import os

    payload = os.urandom(SERIAL_PAYLOAD_BYTES)
    return format_serial(payload, serial_check(payload, key_b64))


def verify_serial(serial: str, key_b64: str) -> bool:
    parsed = parse_serial(serial)
    if parsed is None:
        return False
    scheme, payload, check = parsed
    if scheme != SERIAL_SCHEME:
        return False
    if len(payload) != SERIAL_PAYLOAD_BYTES:
        return False
    try:
        want = serial_check(payload, key_b64)
    except Exception:
        return False
    return hmac.compare_digest(check, want)


_KEY_RE = re.compile(r'KeySerialSigning\s*=\s*"([^"]+)"')
_EXCHANGE_KEY_RE = re.compile(r'KeyExchageLaimApp\s*=\s*"([^"]+)"')


def key_serial_signing_from_laim_repo(version_go: str) -> str:
    """Lee la constante real de laim/internal/utils/version.go (tests)."""
    match = _KEY_RE.search(version_go)
    if not match:
        raise ValueError("KeySerialSigning no está en version.go")
    return match.group(1)


def key_exchange_from_laim_repo(version_go: str) -> str:
    """Lee KeyExchageLaimApp real de version.go (tests)."""
    match = _EXCHANGE_KEY_RE.search(version_go)
    if not match:
        raise ValueError("KeyExchageLaimApp no está en version.go")
    return match.group(1)


def product_serial_signing_key() -> str:
    """KeySerialSigning de producto: la que firman los instaladores de laim."""
    return _PRODUCT_SERIAL_SIGNING_KEY


def product_exchange_key() -> str:
    """KeyExchageLaimApp de producto: AES del propose / HMAC de updates."""
    return _PRODUCT_EXCHANGE_KEY

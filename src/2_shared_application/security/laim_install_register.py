"""Sobre AES-256-GCM del registro automático laim → laimweb.

HKDF-SHA256 info ``laim-install-register-aes-v1`` a partir de
KeyExchageLaimApp (misma clave HMAC de /check_last_version). El MAC del
JSON canónico usa KeySerialSigning — un serial copiado de una captura no
basta para proponer un registro. El descifrado y el MAC viven solo en
backend_core; middleware y broker reenvían el sobre opaco.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HKDF_INFO = b"laim-install-register-aes-v1"
ENVELOPE_VERSION = "1"
MAX_AGE_SECONDS = 300
FORBIDDEN_PLAIN_KEYS = frozenset({"master_key", "master_key_cipher", "user_password", "user_otp"})


class InstallRegisterError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def hkdf_sha256(ikm: bytes, info: bytes, length: int = 32, salt: bytes = b"") -> bytes:
    hash_len = 32
    salt_bytes = salt if salt else bytes(hash_len)
    prk = hmac.new(salt_bytes, ikm, hashlib.sha256).digest()
    okm = b""
    previous = b""
    counter = 1
    while len(okm) < length:
        previous = hmac.new(prk, previous + info + bytes([counter]), hashlib.sha256).digest()
        okm += previous
        counter += 1
    return okm[:length]


def _decode_key(key_b64: str) -> bytes:
    padded = key_b64 + ("=" * ((4 - len(key_b64) % 4) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def derive_install_aes_key(exchange_key_b64: str) -> bytes:
    return hkdf_sha256(_decode_key(exchange_key_b64), HKDF_INFO, length=32)


def canonical_payload(plain: dict[str, Any]) -> str:
    body = {k: v for k, v in plain.items() if k != "mac"}
    return json.dumps(body, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def payload_mac(plain: dict[str, Any], serial_signing_key_b64: str) -> str:
    digest = hmac.new(
        _decode_key(serial_signing_key_b64),
        canonical_payload(plain).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def encrypt_install_payload(
    plain: dict[str, Any],
    exchange_key_b64: str,
    serial_signing_key_b64: str,
    *,
    nonce: bytes | None = None,
) -> dict[str, str]:
    for banned in FORBIDDEN_PLAIN_KEYS:
        if banned in plain:
            raise InstallRegisterError("el sobre no puede llevar secretos de identity.dat")
    signed = dict(plain)
    signed.pop("mac", None)
    signed["mac"] = payload_mac(signed, serial_signing_key_b64)
    raw = json.dumps(signed, separators=(",", ":"), sort_keys=True, ensure_ascii=True).encode("utf-8")
    key = derive_install_aes_key(exchange_key_b64)
    iv = nonce if nonce is not None else os.urandom(12)
    if len(iv) != 12:
        raise InstallRegisterError("nonce AES-GCM inválido")
    ct = AESGCM(key).encrypt(iv, raw, None)
    return {
        "v": ENVELOPE_VERSION,
        "iv": base64.b64encode(iv).decode("ascii"),
        "ct": base64.b64encode(ct).decode("ascii"),
    }


def decrypt_install_payload(
    envelope: dict[str, Any],
    exchange_key_b64: str,
    serial_signing_key_b64: str,
    *,
    now: int | None = None,
) -> dict[str, Any]:
    if str(envelope.get("v") or "") != ENVELOPE_VERSION:
        raise InstallRegisterError("el cuerpo debe ir cifrado")
    try:
        iv = base64.b64decode(str(envelope["iv"]))
        ct = base64.b64decode(str(envelope["ct"]))
    except Exception as exc:
        raise InstallRegisterError("el cuerpo debe ir cifrado") from exc
    try:
        raw = AESGCM(derive_install_aes_key(exchange_key_b64)).decrypt(iv, ct, None)
        plain = json.loads(raw)
    except Exception as exc:
        raise InstallRegisterError("no se pudo descifrar el registro") from exc
    if not isinstance(plain, dict):
        raise InstallRegisterError("no se pudo descifrar el registro")
    blob = json.dumps(plain)
    for banned in FORBIDDEN_PLAIN_KEYS:
        if banned in plain or banned in blob:
            raise InstallRegisterError("el sobre no puede llevar secretos de identity.dat")
    mac = str(plain.get("mac") or "")
    expected = payload_mac(plain, serial_signing_key_b64)
    if not mac or not hmac.compare_digest(mac, expected):
        raise InstallRegisterError("la propuesta de registro no es auténtica")
    current = int(now if now is not None else time.time())
    try:
        ts = int(plain.get("ts") or 0)
    except (TypeError, ValueError) as exc:
        raise InstallRegisterError("la propuesta de registro ha caducado") from exc
    if ts <= 0 or abs(current - ts) > MAX_AGE_SECONDS:
        raise InstallRegisterError("la propuesta de registro ha caducado")
    return plain

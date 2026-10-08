"""Auth y cifrado del canal interno laim_maintenance → laimweb (soporte).

JWT HS256 con operation=support_ops y caller=laim_maintenance, más
AES-256-GCM del cuerpo. La clave AES se deriva con HKDF-SHA256 del
secreto de soporte del entorno (LAIM_SUPPORT_SECRET), distinto del JWT
de sesión de usuario y del de fmanagement.
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

SUPPORT_OPERATION = "support_ops"
SUPPORT_CALLER = "laim_maintenance"
SUPPORT_CALLER_HEADER = "X-Laim-Caller"
HKDF_INFO = b"laim-support-aes-v1"
TOKEN_TTL_SECONDS = 300


class SupportAuthError(Exception):
    """Token o marca de caller inválidos."""


def support_secret() -> str:
    """Secreto del canal de soporte (nunca el JWT de sesión)."""
    return (os.environ.get("LAIM_SUPPORT_SECRET") or "").strip()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hkdf_sha256(ikm: bytes, info: bytes, length: int = 32, salt: bytes = b"") -> bytes:
    """HKDF-SHA256 (RFC 5869) con stdlib + HMAC."""
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


def derive_support_aes_key(secret: str) -> bytes:
    """Deriva la clave AES-256 del secreto de soporte."""
    return hkdf_sha256(secret.encode("utf-8"), HKDF_INFO, length=32)


def mint_support_token(secret: str, now: int | None = None) -> str:
    """Emite un JWT HS256 de 5 minutos. Misma forma que mintProductToken de Go."""
    if not secret:
        raise SupportAuthError("LAIM_SUPPORT_SECRET no configurado")
    issued = int(now if now is not None else time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    claims = {
        "operation": SUPPORT_OPERATION,
        "caller": SUPPORT_CALLER,
        "iat": issued,
        "exp": issued + TOKEN_TTL_SECONDS,
    }
    signing_input = (
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + _b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    )
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return signing_input + "." + _b64url_encode(signature)


def verify_support_token(token: str, secret: str, now: int | None = None) -> dict[str, Any]:
    """Valida firma, operation, caller y expiración."""
    if not secret:
        raise SupportAuthError("LAIM_SUPPORT_SECRET no configurado")
    parts = token.split(".")
    if len(parts) != 3:
        raise SupportAuthError("token mal formado")
    signing_input = f"{parts[0]}.{parts[1]}"
    expected = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    try:
        actual = _b64url_decode(parts[2])
    except Exception as exc:
        raise SupportAuthError("firma ilegible") from exc
    if not hmac.compare_digest(expected, actual):
        raise SupportAuthError("firma inválida")
    try:
        claims = json.loads(_b64url_decode(parts[1]))
    except Exception as exc:
        raise SupportAuthError("claims ilegibles") from exc
    if claims.get("operation") != SUPPORT_OPERATION:
        raise SupportAuthError("operation no permitida")
    if claims.get("caller") != SUPPORT_CALLER:
        raise SupportAuthError("caller no permitido")
    current = int(now if now is not None else time.time())
    if int(claims.get("exp", 0)) < current:
        raise SupportAuthError("token caducado")
    return claims


def encrypt_support_payload(plain: dict[str, Any], secret: str) -> dict[str, str]:
    """Cifra un JSON como sobre AES-256-GCM."""
    key = derive_support_aes_key(secret)
    nonce = os.urandom(12)
    aes = AESGCM(key)
    raw = json.dumps(plain, separators=(",", ":")).encode("utf-8")
    ciphertext = aes.encrypt(nonce, raw, None)
    return {
        "v": "1",
        "iv": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_support_payload(envelope: dict[str, Any], secret: str) -> dict[str, Any]:
    """Descifra un sobre AES-256-GCM a dict."""
    try:
        nonce = base64.b64decode(str(envelope["iv"]))
        ciphertext = base64.b64decode(str(envelope["ct"]))
    except Exception as exc:
        raise SupportAuthError("sobre cifrado ilegible") from exc
    key = derive_support_aes_key(secret)
    aes = AESGCM(key)
    try:
        raw = aes.decrypt(nonce, ciphertext, None)
        return json.loads(raw)
    except Exception as exc:
        raise SupportAuthError("no se pudo descifrar el cuerpo") from exc


def extract_bearer(authorization: str | None) -> str:
    """Extrae el JWT de Authorization: Bearer ..."""
    if not authorization:
        raise SupportAuthError("falta Authorization")
    value = authorization.strip()
    if not value.startswith("Bearer "):
        raise SupportAuthError("Authorization debe ser Bearer")
    token = value[7:].strip()
    if not token:
        raise SupportAuthError("token vacío")
    return token


def require_support_caller(
    authorization: str | None,
    caller_header: str | None,
    client_app: str | None,
    secret: str | None = None,
) -> dict[str, Any]:
    """Puerta única: JWT + X-Laim-Caller + X-Client-App = laim_maintenance."""
    resolved_secret = secret if secret is not None else support_secret()
    if (caller_header or "").strip() != SUPPORT_CALLER:
        raise SupportAuthError("X-Laim-Caller no permitido")
    if (client_app or "").strip().lower() != SUPPORT_CALLER:
        raise SupportAuthError("X-Client-App no permitido")
    token = extract_bearer(authorization)
    return verify_support_token(token, resolved_secret)

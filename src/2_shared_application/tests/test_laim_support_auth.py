"""Tests del JWT y cifrado del canal interno de soporte."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_AUTH_PATH = (
    Path(__file__).resolve().parents[1] / "security" / "laim_support_auth.py"
)


def _load_auth():
    name = "laim_support_auth_test"
    spec = importlib.util.spec_from_file_location(name, _AUTH_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_token_roundtrip_and_rejects_wrong_operation() -> None:
    auth = _load_auth()
    secret = "support-secret-test"
    token = auth.mint_support_token(secret, now=1_700_000_000)
    claims = auth.verify_support_token(token, secret, now=1_700_000_010)
    assert claims["operation"] == "support_ops"
    assert claims["caller"] == "laim_maintenance"

    with pytest.raises(auth.SupportAuthError):
        auth.verify_support_token(token, "otra-clave", now=1_700_000_010)

    with pytest.raises(auth.SupportAuthError):
        auth.verify_support_token(token, secret, now=1_700_000_000 + 400)


def test_encrypt_decrypt_roundtrip() -> None:
    auth = _load_auth()
    secret = "support-secret-test"
    envelope = auth.encrypt_support_payload({"id": 7, "email": "a@b.com"}, secret)
    assert "iv" in envelope and "ct" in envelope
    plain = auth.decrypt_support_payload(envelope, secret)
    assert plain == {"id": 7, "email": "a@b.com"}


def test_require_support_caller_rejects_wrong_headers() -> None:
    auth = _load_auth()
    secret = "support-secret-test"
    token = auth.mint_support_token(secret)
    claims = auth.require_support_caller(
        f"Bearer {token}",
        "laim_maintenance",
        "laim_maintenance",
        secret=secret,
    )
    assert claims["operation"] == "support_ops"

    with pytest.raises(auth.SupportAuthError):
        auth.require_support_caller(
            f"Bearer {token}", "otro", "laim_maintenance", secret=secret
        )
    with pytest.raises(auth.SupportAuthError):
        auth.require_support_caller(
            f"Bearer {token}", "laim_maintenance", "laimweb", secret=secret
        )
    with pytest.raises(auth.SupportAuthError):
        auth.require_support_caller(
            f"Bearer {token}", "laim_maintenance", "unknown", secret=secret
        )

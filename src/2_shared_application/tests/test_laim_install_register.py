"""Sobre AES del registro automático: roundtrip, MAC y rechazo de secretos."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SERIAL = (
    Path(__file__).resolve().parents[1] / "security" / "laim_serial.py"
)
_REG = (
    Path(__file__).resolve().parents[1] / "security" / "laim_install_register.py"
)
_VERSION_GO = Path("/Users/perico/develop/laim/internal/utils/version.go")
_GO_CLIENT = Path("/Users/perico/develop/laim/internal/utils/install_register.go")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _keys():
    serial = _load("laim_serial_reg", _SERIAL)
    src = _VERSION_GO.read_text(encoding="utf-8")
    signing = serial.key_serial_signing_from_laim_repo(src)
    import re

    match = re.search(r'KeyExchageLaimApp\s*=\s*"([^"]+)"', src)
    assert match is not None
    return match.group(1), signing


def test_go_client_uses_same_hkdf_info_and_omits_master_key() -> None:
    src = _GO_CLIENT.read_text(encoding="utf-8")
    py = _REG.read_text(encoding="utf-8")
    assert "laim-install-register-aes-v1" in src
    assert "laim-install-register-aes-v1" in py
    assert "MasterKeyCipher" not in src
    assert 'json:"master_key' not in src
    assert "/laim/installations/propose" in src


def test_roundtrip_and_reject_tamper_stale_and_secrets() -> None:
    reg = _load("laim_install_register_test", _REG)
    exchange, signing = _keys()
    plain = {
        "user_name": "ana",
        "user_email": "ana@laim.example",
        "serial_number": "2-AAAA",
        "hostname": "box",
        "operating_system": "mac",
        "edition": "community_edition",
        "ts": 1_700_000_000,
    }
    env = reg.encrypt_install_payload(exchange_key_b64=exchange, serial_signing_key_b64=signing, plain=plain)
    out = reg.decrypt_install_payload(env, exchange, signing, now=1_700_000_010)
    assert out["user_name"] == "ana"
    assert out["hostname"] == "box"
    assert "master_key" not in json.dumps(out)

    tampered = dict(env)
    tampered["ct"] = tampered["ct"][:-2] + ("A" if tampered["ct"][-1] != "A" else "B")
    try:
        reg.decrypt_install_payload(tampered, exchange, signing, now=1_700_000_010)
        raise AssertionError("tamper debe fallar")
    except Exception as exc:
        assert "descifrar" in str(exc).lower() or "cifrado" in str(exc).lower()

    try:
        reg.decrypt_install_payload(env, exchange, signing, now=1_700_000_000 + 400)
        raise AssertionError("stale debe fallar")
    except Exception as exc:
        assert "caducado" in str(exc).lower()

    try:
        reg.encrypt_install_payload(
            {**plain, "master_key_cipher": "no"},
            exchange,
            signing,
        )
        raise AssertionError("secretos no deben cifrar")
    except Exception as exc:
        assert "secretos" in str(exc).lower()

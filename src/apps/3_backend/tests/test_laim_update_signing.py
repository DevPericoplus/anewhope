"""Firma de /check_last_version para LAIM 3.2.10 (AW1 + AW2, 2026-11-15).

- AW1: producción respondía sin firma porque `laim_exchange_keys` no tenía la
  clave `exchange` del major 3 y nada la sembraba. Ahora se siembra como
  `serial_signing` (fila → `LAIM_EXCHANGE_KEY` → constante de producto) y un
  parche que no se puede firmar no se ofrece.
- AW2: LAIM pkg139 solo acepta la carga
  `edition|platform|patch|<versión>|<fichero>|sha256=<hex>` con el SHA-256 del
  fichero exacto que se sirve. Sin SHA no hay oferta.
- Huella pública de la clave (HMAC de una etiqueta fija) para comparar la
  clave de laimweb con la que lleva LAIM sin revelar ninguna.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

_SHARED = Path(__file__).resolve().parents[3] / "2_shared_application"
_SIGNING = _SHARED / "security" / "laim_update_signing.py"
_KEYS = _SHARED / "adapters" / "laim_exchange_key.py"
_SERIAL = _SHARED / "security" / "laim_serial.py"

# Claves falsas de prueba (nunca las de producto).
_KEY_A = base64.urlsafe_b64encode(b"A" * 32).decode().rstrip("=")
_KEY_B = base64.urlsafe_b64encode(b"B" * 32).decode()


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _hmac_hex(raw_key: bytes, message: str) -> str:
    return hmac.new(raw_key, message.encode("utf-8"), hashlib.sha256).hexdigest()


# --------------------------------------------------------------------- módulo


def test_signed_payload_carries_the_patch_sha() -> None:
    signing = _load("laim_update_signing_t1", _SIGNING)
    sha = "ab" * 32
    assert (
        signing.signed_update_payload("community_edition", "windows", "3.2.11", "laim_3.2.11.tar", sha)
        == f"community_edition|windows|patch|3.2.11|laim_3.2.11.tar|sha256={sha}"
    )


@pytest.mark.parametrize("bad", ["", "AB" * 32, "ab" * 31, "zz" * 32, None])
def test_signed_payload_refuses_a_bad_sha(bad: Any) -> None:
    signing = _load("laim_update_signing_t2", _SIGNING)
    with pytest.raises(ValueError):
        signing.signed_update_payload("community_edition", "windows", "3.2.11", "f.tar", bad)


def test_signature_is_hmac_sha256_of_the_payload_with_the_decoded_key() -> None:
    signing = _load("laim_update_signing_t3", _SIGNING)
    assert signing.sign_update_payload(_KEY_A, "x|y") == _hmac_hex(b"A" * 32, "x|y")


def test_fingerprint_is_a_public_hmac_of_a_fixed_label() -> None:
    signing = _load("laim_update_signing_t4", _SIGNING)
    assert signing.FINGERPRINT_LABEL == "laim-exchange-key-fingerprint/v1"
    expected = _hmac_hex(b"A" * 32, "laim-exchange-key-fingerprint/v1")[:16]
    assert signing.exchange_key_fingerprint(_KEY_A) == expected
    assert signing.exchange_key_fingerprint(_KEY_A + "=") == expected  # con o sin relleno
    assert signing.exchange_key_fingerprint(_KEY_B) != expected


def test_file_sha_is_cached_until_the_file_changes(tmp_path: Path, monkeypatch) -> None:
    signing = _load("laim_update_signing_t5", _SIGNING)
    patch = tmp_path / "p.tar"
    patch.write_bytes(b"uno")
    cache = signing.FileSha256Cache()
    reads: list[Path] = []
    real = signing._sha256_of_file

    def counting(path: Path) -> str:
        reads.append(path)
        return real(path)

    monkeypatch.setattr(signing, "_sha256_of_file", counting)
    assert cache.sha256(patch) == hashlib.sha256(b"uno").hexdigest()
    assert cache.sha256(patch) == hashlib.sha256(b"uno").hexdigest()
    assert len(reads) == 1
    patch.write_bytes(b"dos-mas-largo")
    os.utime(patch, ns=(patch.stat().st_atime_ns, patch.stat().st_mtime_ns + 5_000_000_000))
    assert cache.sha256(patch) == hashlib.sha256(b"dos-mas-largo").hexdigest()
    assert len(reads) == 2


def test_file_sha_of_a_missing_file_is_none(tmp_path: Path) -> None:
    signing = _load("laim_update_signing_t6", _SIGNING)
    assert signing.FileSha256Cache().sha256(tmp_path / "no.tar") is None


# ---------------------------------------------------------------- repositorio


def _keys_engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE laim_exchange_keys (
                    key_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    major_version TEXT NOT NULL,
                    key_kind TEXT NOT NULL DEFAULT 'exchange',
                    key_value_cipher TEXT NOT NULL,
                    valid_from TEXT NOT NULL DEFAULT '2000-01-01 00:00:00',
                    valid_until TEXT
                )
                """
            )
        )
    return engine


def test_ensure_exchange_key_seeds_once_per_major() -> None:
    keys = _load("laim_exchange_key_t1", _KEYS).LaimExchangeKeyRepository(_keys_engine())
    assert keys.get_current_key("3") is None
    first = keys.ensure_exchange_key("3", _KEY_A)
    again = keys.ensure_exchange_key("3", _KEY_B)
    assert (first.major_version, first.key_value) == ("3", _KEY_A)
    assert (again.key_id, again.key_value) == (first.key_id, _KEY_A)
    assert keys.get_current_key("4") is None
    assert keys.get_serial_signing_key() is None


def test_ensure_exchange_key_never_replaces_an_existing_row() -> None:
    engine = _keys_engine()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO laim_exchange_keys (major_version, key_kind, key_value_cipher) VALUES ('3', 'exchange', :v)"),
            {"v": _KEY_B},
        )
    keys = _load("laim_exchange_key_t2", _KEYS).LaimExchangeKeyRepository(engine)
    assert keys.ensure_exchange_key("3", _KEY_A).key_value == _KEY_B


def test_ensure_exchange_key_refuses_an_empty_value() -> None:
    keys = _load("laim_exchange_key_t3", _KEYS).LaimExchangeKeyRepository(_keys_engine())
    with pytest.raises(ValueError):
        keys.ensure_exchange_key("3", "  ")


# ------------------------------------------------------------------- endpoint


class _FakeKeys:
    def __init__(self, rows: dict[str, str] | None = None) -> None:
        self.rows = dict(rows or {})
        self.seeded: list[tuple[str, str]] = []

    def get_current_key(self, major_version: str, key_kind: str = "exchange") -> Any:
        assert key_kind == "exchange"
        value = self.rows.get(major_version)
        if value is None:
            return None
        return type("K", (), {"key_id": 7, "major_version": major_version, "key_value": value})()

    def ensure_exchange_key(self, major_version: str, key_value: str) -> Any:
        self.seeded.append((major_version, key_value))
        self.rows[major_version] = key_value
        return self.get_current_key(major_version)


def _publish(tmp_path: Path, content: bytes = b"patch-bytes") -> str:
    leaf = tmp_path / "community_edition" / "patches" / "windows"
    (leaf / "3.2.11").mkdir(parents=True)
    (leaf / "3.2.11" / "laim_3.2.11.tar").write_bytes(content)
    (leaf / "latest").symlink_to("3.2.11/laim_3.2.11.tar")
    return hashlib.sha256(content).hexdigest()


def _client(tmp_path: Path, monkeypatch, keys: _FakeKeys, name: str) -> tuple[Any, TestClient]:
    monkeypatch.setenv("LAIM_PRODUCT_STORAGE", str(tmp_path))
    monkeypatch.delenv("LAIM_EXCHANGE_KEY", raising=False)
    apicore = _load(name, Path(__file__).resolve().parents[1] / "apicore.py")
    monkeypatch.setattr(apicore, "_exchange_key_repo", keys)
    return apicore, TestClient(apicore.app)


def _check(client: TestClient, current: str = "3.2.10") -> dict[str, Any]:
    response = client.get(
        "/check_last_version",
        params={"edition": "community_edition", "platform": "windows", "current_version": current},
    )
    assert response.status_code == 200
    return response.json()


def test_an_update_is_signed_with_the_patch_sha(tmp_path: Path, monkeypatch) -> None:
    sha = _publish(tmp_path)
    _, client = _client(tmp_path, monkeypatch, _FakeKeys({"3": _KEY_A}), "apicore_sign_t1")
    body = _check(client)
    payload = f"community_edition|windows|patch|3.2.11|laim_3.2.11.tar|sha256={sha}"
    assert body == {
        "has_update": True,
        "latest_version": "3.2.11",
        "artifact_type": "patch",
        "filename": "laim_3.2.11.tar",
        "download_url": (
            "/laim/product/download?edition=community_edition&artifact_type=patch"
            "&platform=windows&version=3.2.11&filename=laim_3.2.11.tar"
        ),
        "signed_payload": payload,
        "signature": _hmac_hex(b"A" * 32, payload),
        "key_id": 7,
        "key_fingerprint": _hmac_hex(b"A" * 32, "laim-exchange-key-fingerprint/v1")[:16],
    }


def test_without_a_row_the_product_key_is_seeded_for_its_major(tmp_path: Path, monkeypatch) -> None:
    _publish(tmp_path)
    keys = _FakeKeys()
    apicore, client = _client(tmp_path, monkeypatch, keys, "apicore_sign_t2")
    product = _load("laim_serial_sign_t2", _SERIAL)
    body = _check(client)
    assert keys.seeded == [(product.PRODUCT_EXCHANGE_MAJOR, product.product_exchange_key())]
    assert product.PRODUCT_EXCHANGE_MAJOR == "3"
    assert body["has_update"] is True and body["signature"]


def test_the_env_key_overrides_the_product_key(tmp_path: Path, monkeypatch) -> None:
    _publish(tmp_path)
    keys = _FakeKeys()
    _, client = _client(tmp_path, monkeypatch, keys, "apicore_sign_t3")
    monkeypatch.setenv("LAIM_EXCHANGE_KEY", _KEY_B)
    body = _check(client)
    assert keys.seeded == [("3", _KEY_B)]
    assert body["signature"] == _hmac_hex(b"B" * 32, body["signed_payload"])


_NO_OFFER = {"has_update": False, "latest_version": None, "artifact_type": "patch", "filename": None}


def test_no_key_for_that_major_means_no_offer(tmp_path: Path, monkeypatch, caplog) -> None:
    _publish(tmp_path)
    keys = _FakeKeys()
    _, client = _client(tmp_path, monkeypatch, keys, "apicore_sign_t4")
    with caplog.at_level("WARNING"):
        body = _check(client, current="2.9.0")  # 3.2.11 es más nueva; el major 2 no tiene clave
    assert body == _NO_OFFER
    assert keys.seeded == []
    assert "major_version=2" in caplog.text


def test_a_malformed_key_means_no_offer(tmp_path: Path, monkeypatch) -> None:
    _publish(tmp_path)
    _, client = _client(tmp_path, monkeypatch, _FakeKeys({"3": "%%%no-es-base64%%%"}), "apicore_sign_t5")
    assert _check(client) == _NO_OFFER


def test_an_unknown_sha_means_no_offer(tmp_path: Path, monkeypatch, caplog) -> None:
    _publish(tmp_path)
    (tmp_path / "community_edition" / "patches" / "windows" / "3.2.11" / "laim_3.2.11.tar").unlink()
    _, client = _client(tmp_path, monkeypatch, _FakeKeys({"3": _KEY_A}), "apicore_sign_t6")
    with caplog.at_level("WARNING"):
        assert _check(client) == _NO_OFFER
    assert "sin SHA-256" in caplog.text


def test_no_newer_version_is_answered_as_before(tmp_path: Path, monkeypatch) -> None:
    _publish(tmp_path)
    keys = _FakeKeys({"3": _KEY_A})
    _, client = _client(tmp_path, monkeypatch, keys, "apicore_sign_t7")
    assert _check(client, current="3.2.11") == {
        "has_update": False,
        "latest_version": "3.2.11",
        "artifact_type": "patch",
        "filename": None,
    }
    assert keys.seeded == []


def test_the_product_key_fingerprint_matches_laims_compiled_key() -> None:
    """Paridad sin revelar ninguna clave: solo se comparan huellas."""
    version_go = Path("/Users/perico/develop/laim/internal/utils/version.go")
    if not version_go.is_file():
        pytest.skip("sin repositorio de LAIM")
    signing = _load("laim_update_signing_t8", _SIGNING)
    serial = _load("laim_serial_sign_t8", _SERIAL)
    # Solo huellas en variables: pytest nunca muestra una clave si falla.
    laim_fp = signing.exchange_key_fingerprint(
        serial.key_exchange_from_laim_repo(version_go.read_text(encoding="utf-8"))
    )
    laimweb_fp = signing.exchange_key_fingerprint(serial.product_exchange_key())
    assert laim_fp == laimweb_fp


def test_a_latest_link_out_of_the_leaf_is_not_offered(tmp_path: Path, monkeypatch) -> None:
    leaf = tmp_path / "community_edition" / "patches" / "windows"
    (leaf / "9.9.9").mkdir(parents=True)
    (tmp_path / "community_edition" / "patches" / "secret.tar").write_bytes(b"x")
    # Versión «más nueva», pero el fichero sale de leaf/9.9.9/.
    (leaf / "latest").symlink_to("9.9.9/../../secret.tar")
    _, client = _client(tmp_path, monkeypatch, _FakeKeys({"3": _KEY_A}), "apicore_sign_t9")
    body = _check(client, current="0.0.1")
    assert body["has_update"] is False
    assert "signature" not in body and "download_url" not in body


def test_the_fingerprint_script_prints_only_fingerprints(tmp_path: Path, capsys) -> None:
    script = _load("laim_fp_script", Path(__file__).resolve().parents[4] / "scripts" / "laim_exchange_key_fingerprint.py")
    signing = _load("laim_update_signing_t10", _SIGNING)
    repo = tmp_path / "laim"
    (repo / "internal" / "utils").mkdir(parents=True)
    (repo / "internal" / "utils" / "version.go").write_text(f'const KeyExchageLaimApp = "{_KEY_A}"\n', encoding="utf-8")
    assert script.main(["--laim-repo", str(repo)]) == 1  # clave falsa: no coincide con la de producto
    out = capsys.readouterr().out.splitlines()
    assert out[1] == f"laim {repo} (version.go): " + signing.exchange_key_fingerprint(_KEY_A)
    assert out[0].startswith("laimweb producto (major 3): ")
    assert all(_KEY_A not in line for line in out)
    assert len(out[0].rsplit(": ", 1)[1]) == 16


def test_an_unreadable_patch_has_no_sha(tmp_path: Path) -> None:
    signing = _load("laim_update_signing_t11", _SIGNING)
    patch = tmp_path / "p.tar"
    patch.write_bytes(b"x")
    patch.chmod(0)
    try:
        assert signing.FileSha256Cache().sha256(patch) is None
    finally:
        patch.chmod(0o600)


def test_the_served_path_never_leaves_its_version_folder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LAIM_PRODUCT_STORAGE", str(tmp_path))
    apicore = _load("apicore_sign_t12", Path(__file__).resolve().parents[1] / "apicore.py")
    leaf = tmp_path / "leaf"
    (leaf / "3.2.11").mkdir(parents=True)
    (tmp_path / "secret.tar").write_bytes(b"x")
    assert apicore._served_patch_path(leaf, "..", "secret.tar") is None
    assert apicore._served_patch_path(leaf, "3.2.11", "..") is None
    assert apicore._served_patch_path(leaf, "3.2.11", "p.tar") == (leaf / "3.2.11" / "p.tar").resolve()

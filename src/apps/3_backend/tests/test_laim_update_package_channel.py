"""Canal de paquetes Linux de /check_last_version (AW3, 2026-11-15).

LAIM pkg148: una instalación deb/rpm (en /opt/laim, de root) se actualiza con
su paquete firmado, no con un parche. Pide `artifact=package` y solo acepta la
carga `edition|platform|package|<versión>|<fichero .deb|.rpm>|sha256=<hex>`
firmada con la clave `exchange` del major, igual que AW2. El paquete se sirve
desde `<storage>/<edición>/packages/linux/{deb,rpm}/<versión>/<fichero>`, con
un enlace `latest` como `patches/`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

_KEY_A = base64.urlsafe_b64encode(b"A" * 32).decode().rstrip("=")


def _hmac_hex(raw: bytes, message: str) -> str:
    return hmac.new(raw, message.encode("utf-8"), hashlib.sha256).hexdigest()


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _Keys:
    def __init__(self) -> None:
        self.rows = {"3": _KEY_A}

    def get_current_key(self, major_version: str, key_kind: str = "exchange") -> Any:
        value = self.rows.get(major_version)
        if value is None:
            return None
        return type("K", (), {"key_id": 7, "major_version": major_version, "key_value": value})()

    def ensure_exchange_key(self, major_version: str, key_value: str) -> Any:
        raise AssertionError("no debe sembrar: ya hay fila")


def _publish(tmp_path: Path, kind: str, fmt: str, version: str, filename: str, content: bytes = b"pkg") -> str:
    leaf = tmp_path / "community_edition" / kind / "linux" / fmt
    (leaf / version).mkdir(parents=True, exist_ok=True)
    (leaf / version / filename).write_bytes(content)
    latest = leaf / "latest"
    if latest.is_symlink():
        latest.unlink()
    latest.symlink_to(f"{version}/{filename}")
    return hashlib.sha256(content).hexdigest()


def _client(tmp_path: Path, monkeypatch, name: str) -> TestClient:
    monkeypatch.setenv("LAIM_PRODUCT_STORAGE", str(tmp_path))
    monkeypatch.delenv("LAIM_EXCHANGE_KEY", raising=False)
    apicore = _load(name, Path(__file__).resolve().parents[1] / "apicore.py")
    monkeypatch.setattr(apicore, "_exchange_key_repo", _Keys())
    return TestClient(apicore.app)


def _check(client: TestClient, platform: str, artifact: str | None = "package", current: str = "3.2.10", **extra: str):
    params = {"edition": "community_edition", "platform": platform, "current_version": current, **extra}
    if artifact is not None:
        params["artifact"] = artifact
    return client.get("/check_last_version", params=params)


@pytest.mark.parametrize(
    ("platform", "fmt", "filename"),
    [("linux_deb", "deb", "laim_3.2.11_amd64.deb"), ("linux_rpm", "rpm", "laim-3.2.11-1.x86_64.rpm")],
)
def test_a_package_update_is_signed_with_the_package_sha(tmp_path: Path, monkeypatch, platform, fmt, filename) -> None:
    sha = _publish(tmp_path, "packages", fmt, "3.2.11", filename, b"package-bytes")
    client = _client(tmp_path, monkeypatch, f"apicore_pkg_{fmt}")
    response = _check(client, platform)
    assert response.status_code == 200
    payload = f"community_edition|{platform}|package|3.2.11|{filename}|sha256={sha}"
    assert response.json() == {
        "has_update": True,
        "latest_version": "3.2.11",
        "artifact_type": "package",
        "filename": filename,
        "download_url": (
            "/laim/product/download?edition=community_edition&artifact_type=package"
            f"&platform={platform}&version=3.2.11&filename={filename}"
        ),
        "signed_payload": payload,
        "signature": _hmac_hex(b"A" * 32, payload),
        "key_id": 7,
        "key_fingerprint": _hmac_hex(b"A" * 32, "laim-exchange-key-fingerprint/v1")[:16],
    }


_NO_PACKAGE = {"has_update": False, "latest_version": None, "artifact_type": "package", "filename": None}


def test_a_package_of_the_other_format_is_not_offered(tmp_path: Path, monkeypatch, caplog) -> None:
    _publish(tmp_path, "packages", "deb", "3.2.11", "laim-3.2.11-1.x86_64.rpm")
    client = _client(tmp_path, monkeypatch, "apicore_pkg_wrongext")
    with caplog.at_level("WARNING"):
        assert _check(client, "linux_deb").json() == _NO_PACKAGE
    assert "no es un paquete .deb" in caplog.text


def test_a_missing_package_file_is_not_offered(tmp_path: Path, monkeypatch, caplog) -> None:
    _publish(tmp_path, "packages", "deb", "3.2.11", "laim_3.2.11_amd64.deb")
    (tmp_path / "community_edition" / "packages" / "linux" / "deb" / "3.2.11" / "laim_3.2.11_amd64.deb").unlink()
    client = _client(tmp_path, monkeypatch, "apicore_pkg_missing")
    with caplog.at_level("WARNING"):
        assert _check(client, "linux_deb").json() == _NO_PACKAGE
    assert "sin SHA-256" in caplog.text


def test_no_published_package_means_no_update(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch, "apicore_pkg_none")
    assert _check(client, "linux_rpm").json() == _NO_PACKAGE


def test_a_package_not_newer_is_answered_without_signature(tmp_path: Path, monkeypatch) -> None:
    _publish(tmp_path, "packages", "deb", "3.2.11", "laim_3.2.11_amd64.deb")
    client = _client(tmp_path, monkeypatch, "apicore_pkg_notnewer")
    assert _check(client, "linux_deb", current="3.2.11").json() == {
        "has_update": False,
        "latest_version": "3.2.11",
        "artifact_type": "package",
        "filename": None,
    }


def test_without_artifact_the_patch_channel_is_unchanged(tmp_path: Path, monkeypatch) -> None:
    sha = _publish(tmp_path, "patches", "deb", "3.2.11", "laim_patch_3.2.11.tar", b"patch")
    _publish(tmp_path, "packages", "deb", "3.2.12", "laim_3.2.12_amd64.deb", b"pkg")
    client = _client(tmp_path, monkeypatch, "apicore_pkg_patch")
    body = _check(client, "linux_deb", artifact=None).json()
    assert body["artifact_type"] == "patch"
    assert body["filename"] == "laim_patch_3.2.11.tar"
    assert body["signed_payload"] == f"community_edition|linux_deb|patch|3.2.11|laim_patch_3.2.11.tar|sha256={sha}"
    assert _check(client, "linux_deb", artifact="patch").json() == body


@pytest.mark.parametrize(
    ("platform", "artifact", "extra"),
    [
        ("windows", "package", {}),
        ("mac_silicon", "package", {}),
        ("linux_deb", "package", {"plugin_name": "demo"}),
        ("linux_deb", "installer", {}),
        ("linux_deb", "zip", {}),
    ],
)
def test_a_package_request_outside_linux_core_is_refused(tmp_path: Path, monkeypatch, platform, artifact, extra) -> None:
    client = _client(tmp_path, monkeypatch, f"apicore_pkg_bad_{platform}_{artifact}")
    assert _check(client, platform, artifact=artifact, **extra).status_code == 400


def test_the_package_is_downloadable_with_the_offered_url(tmp_path: Path, monkeypatch) -> None:
    _publish(tmp_path, "packages", "rpm", "3.2.11", "laim-3.2.11-1.x86_64.rpm", b"rpm-bytes")
    client = _client(tmp_path, monkeypatch, "apicore_pkg_download")
    url = _check(client, "linux_rpm").json()["download_url"].removeprefix("/laim")
    response = client.get(url)
    assert response.status_code == 200
    assert response.content == b"rpm-bytes"


def test_the_package_download_never_leaves_its_version_folder(tmp_path: Path, monkeypatch) -> None:
    _publish(tmp_path, "packages", "deb", "3.2.11", "laim_3.2.11_amd64.deb")
    (tmp_path / "community_edition" / "secret.deb").write_bytes(b"x")
    client = _client(tmp_path, monkeypatch, "apicore_pkg_guard")
    base = {"edition": "community_edition", "artifact_type": "package", "platform": "linux_deb"}
    assert client.get("/product/download", params={**base, "version": "..", "filename": "secret.deb"}).status_code in (400, 403, 404)
    assert client.get("/product/download", params={**base, "version": "3.2.11", "filename": "../../../../secret.deb"}).status_code == 400
    assert client.get("/product/download", params={**base, "platform": "windows", "version": "3.2.11", "filename": "x.deb"}).status_code == 400

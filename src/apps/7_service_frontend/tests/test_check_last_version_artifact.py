"""AW3: el middleware pasa `artifact` (LAIM pkg148, «package») al broker y,
sin él, la llamada es la misma de siempre (canal de parches)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_BASE = Path(__file__).resolve().parents[1]


def _load(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, _BASE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


client_mod = _load("broker_backend_client_check_artifact_test", "broker_backend_client.py")


def _paths(**kwargs: str) -> list[str]:
    client = object.__new__(client_mod.BrokerBackendClient)
    paths: list[str] = []
    client._request = lambda method, path, **kw: paths.append(path) or {}
    client_mod.BrokerBackendClient.check_last_version(client, "community_edition", "linux_deb", "3.2.10", **kwargs)
    return paths


def test_the_broker_client_adds_artifact_only_when_given() -> None:
    assert _paths(artifact="package") == [
        "/check_last_version?edition=community_edition&platform=linux_deb&current_version=3.2.10&artifact=package"
    ]
    assert _paths() == ["/check_last_version?edition=community_edition&platform=linux_deb&current_version=3.2.10"]


def test_the_middleware_router_forwards_artifact() -> None:
    source = (_BASE / "routermiddleware.py").read_text(encoding="utf-8")
    assert "self._broker_client.check_last_version(edition, platform, current_version, plugin_name, artifact)" in source
    api = (_BASE / "apife.py").read_text(encoding="utf-8")
    assert "router.check_last_version(session, edition, platform, current_version, plugin_name, artifact)" in api

"""AW3: el broker pasa `artifact` (LAIM pkg148, «package») a backend_core y,
sin él, la llamada es la misma de siempre (canal de parches)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

_BASE = Path(__file__).resolve().parents[1]


def _load(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, _BASE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


apibe = _load("apibe_check_artifact_test", "apibe.py")
core = _load("interfacetocore_check_artifact_test", "interfacetocore.py")


def teardown_function() -> None:
    apibe.app.dependency_overrides.pop(apibe.get_router_broker, None)


def _route(params: dict[str, str]) -> MagicMock:
    router = MagicMock()
    router.check_last_version.return_value = {"has_update": False}
    apibe.app.dependency_overrides[apibe.get_router_broker] = lambda: router
    assert TestClient(apibe.app).get("/check_last_version", params=params).status_code == 200
    return router


def test_the_route_passes_the_package_artifact() -> None:
    router = _route({"edition": "community_edition", "platform": "linux_deb", "current_version": "3.2.10", "artifact": "package"})
    router.check_last_version.assert_called_once_with("community_edition", "linux_deb", "3.2.10", "", "package")


def test_without_artifact_the_route_asks_for_the_patch() -> None:
    router = _route({"edition": "community_edition", "platform": "windows", "current_version": "3.2.10"})
    router.check_last_version.assert_called_once_with("community_edition", "windows", "3.2.10", "", "")


def _core_paths(**kwargs: str) -> list[str]:
    client = object.__new__(core.CoreBackendClient)
    paths: list[str] = []
    client._request = lambda method, path, **kw: paths.append(path) or {}
    core.CoreBackendClient.check_last_version(client, "community_edition", "linux_rpm", "3.2.10", **kwargs)
    return paths


def test_the_core_client_adds_artifact_only_when_given() -> None:
    assert _core_paths(artifact="package") == [
        "/check_last_version?edition=community_edition&platform=linux_rpm&current_version=3.2.10&artifact=package"
    ]
    assert _core_paths() == ["/check_last_version?edition=community_edition&platform=linux_rpm&current_version=3.2.10"]

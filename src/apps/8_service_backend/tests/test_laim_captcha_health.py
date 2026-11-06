"""GET /laim/captcha/health en el broker: pasa a backend_core y nunca 5xx."""

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


apibe = _load("apibe_captcha_health_test", "apibe.py")


def teardown_function() -> None:
    apibe.app.dependency_overrides.pop(apibe.get_router_broker, None)


def _client_with(router: object) -> TestClient:
    apibe.app.dependency_overrides[apibe.get_router_broker] = lambda: router
    return TestClient(apibe.app)


def test_route_passes_core_status() -> None:
    router = MagicMock()
    router.laim_captcha_health.return_value = {"status": "ok"}
    response = _client_with(router).get("/laim/captcha/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_route_never_answers_5xx() -> None:
    router = MagicMock()
    router.laim_captcha_health.side_effect = RuntimeError("core caído")
    response = _client_with(router).get("/laim/captcha/health")
    assert response.status_code == 200
    assert response.json() == {"status": "unknown"}


def test_router_maps_core_errors_and_odd_values_to_unknown() -> None:
    router_module = sys.modules.get("routerbroker") or _load("routerbroker", "routerbroker.py")
    router = router_module.BrokerBackendRouter.__new__(router_module.BrokerBackendRouter)
    router._logger = MagicMock()
    router._core_client = MagicMock()
    router._core_client.laim_captcha_health.side_effect = router_module.CoreBackendCommunicationError("x")
    assert router.laim_captcha_health() == {"status": "unknown"}
    router._core_client.laim_captcha_health.side_effect = None
    router._core_client.laim_captcha_health.return_value = {"status": "weird"}
    assert router.laim_captcha_health() == {"status": "unknown"}
    router._core_client.laim_captcha_health.return_value = {"status": "down"}
    assert router.laim_captcha_health() == {"status": "down"}


def test_core_client_calls_the_core_route() -> None:
    core_module = sys.modules.get("interfacetocore") or _load("interfacetocore", "interfacetocore.py")
    client = core_module.CoreBackendClient.__new__(core_module.CoreBackendClient)
    client._request = MagicMock(return_value={"status": "ok"})
    assert client.laim_captcha_health() == {"status": "ok"}
    client._request.assert_called_once_with("GET", "/laim/captcha/health")

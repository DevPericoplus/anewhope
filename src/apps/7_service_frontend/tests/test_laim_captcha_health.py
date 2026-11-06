"""GET /laim/captcha/health en middleware: público y sin 5xx."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from apife import app, get_router_middleware
from broker_backend_client import BrokerBackendCommunicationError
from routermiddleware import RouterMiddleware


def _client_with(router: object) -> TestClient:
    app.dependency_overrides[get_router_middleware] = lambda: router
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.pop(get_router_middleware, None)


def test_route_is_public_and_returns_status() -> None:
    router = MagicMock()
    router.laim_captcha_health.return_value = {"status": "down"}
    response = _client_with(router).get("/laim/captcha/health")
    assert response.status_code == 200
    assert response.json() == {"status": "down"}


def test_route_never_answers_5xx() -> None:
    router = MagicMock()
    router.laim_captcha_health.side_effect = RuntimeError("broker caído")
    response = _client_with(router).get("/laim/captcha/health")
    assert response.status_code == 200
    assert response.json() == {"status": "unknown"}


def test_router_maps_broker_errors_and_odd_values_to_unknown() -> None:
    router = RouterMiddleware.__new__(RouterMiddleware)
    router._broker_client = MagicMock()
    router._broker_client.laim_captcha_health.side_effect = BrokerBackendCommunicationError("x")
    assert router.laim_captcha_health() == {"status": "unknown"}
    router._broker_client.laim_captcha_health.side_effect = None
    router._broker_client.laim_captcha_health.return_value = {"status": "weird", "host": "x"}
    assert router.laim_captcha_health() == {"status": "unknown"}
    router._broker_client.laim_captcha_health.return_value = {"status": "ok"}
    assert router.laim_captcha_health() == {"status": "ok"}

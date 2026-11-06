"""siteverify de Cap: ruta interna sin proxy, reintento solo sin conexión,
secret de marcador rechaza, y el registro dice el motivo sin secretos.

QA laimweb 0.12.65 (2026-11-06): en silicon y dev el backend no validaba
el certificado de la CA local (``CERTIFICATE_VERIFY_FAILED``) y en pre se
reenviaba un token ya gastado.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

import httpx
import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "4_infrastructure" / "captcha" / "cap_siteverify.py"
)
_spec = importlib.util.spec_from_file_location("cap_siteverify_test", _MODULE_PATH)
cap = importlib.util.module_from_spec(_spec)
sys.modules["cap_siteverify_test"] = cap
_spec.loader.exec_module(cap)

SECRET = "s3cr3t-value-never-logged"
TOKEN = "tok-123"
PUBLIC = "https://laim.example.loc/cap/abc123/"
INTERNAL = "http://frontend.example.loc:3300/abc123/"


class _Recorder:
    """Fábrica de clientes con transporte simulado; anota cada llamada."""

    def __init__(self, handler) -> None:
        self.handler = handler
        self.calls: list[tuple[str, bool, dict]] = []

    def __call__(self, url: str, config, internal: bool) -> httpx.Client:
        def respond(request: httpx.Request) -> httpx.Response:
            self.calls.append((str(request.url), internal, {}))
            return self.handler(request, internal)

        return httpx.Client(transport=httpx.MockTransport(respond))


def _config(**overrides) -> object:
    values = {
        "public_endpoint": PUBLIC,
        "verify_endpoint": INTERNAL,
        "secret": SECRET,
        "proxy_url": "http://squid.example.loc:3128",
        "no_proxy": "localhost,.example.loc,10.0.0.0/8",
    }
    values.update(overrides)
    return cap.CapConfig(**values)


def test_internal_endpoint_is_used_first() -> None:
    rec = _Recorder(lambda req, internal: httpx.Response(200, json={"success": True}))
    result = cap.verify_token(TOKEN, _config(), logging.getLogger("t"), rec)
    assert result.ok is True
    assert rec.calls == [("http://frontend.example.loc:3300/abc123/siteverify", True, {})]


def test_connection_error_falls_back_to_public_endpoint() -> None:
    def handler(req: httpx.Request, internal: bool) -> httpx.Response:
        if internal:
            raise httpx.ConnectError("refused", request=req)
        return httpx.Response(200, json={"success": True})

    rec = _Recorder(handler)
    result = cap.verify_token(TOKEN, _config(), logging.getLogger("t"), rec)
    assert result.ok is True
    assert [internal for _, internal, _ in rec.calls] == [True, False]


def test_a_response_from_cap_is_never_retried() -> None:
    """Cap pudo gastar el token: un 404 o success=false no se repite."""
    rec = _Recorder(lambda req, internal: httpx.Response(404, json={"error": "Token not found"}))
    result = cap.verify_token(TOKEN, _config(), logging.getLogger("t"), rec)
    assert result.ok is False
    assert len(rec.calls) == 1
    assert "404" in result.reason and "Token not found" in result.reason


def test_read_timeout_is_not_retried() -> None:
    def handler(req: httpx.Request, internal: bool) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=req)

    rec = _Recorder(handler)
    result = cap.verify_token(TOKEN, _config(), logging.getLogger("t"), rec)
    assert result.ok is False
    assert len(rec.calls) == 1
    assert "ReadTimeout" in result.reason


def test_success_false_is_rejected_with_reason() -> None:
    rec = _Recorder(
        lambda req, internal: httpx.Response(200, json={"success": False, "error": "expired"})
    )
    result = cap.verify_token(TOKEN, _config(), logging.getLogger("t"), rec)
    assert result.ok is False
    assert "success=false" in result.reason and "expired" in result.reason


@pytest.mark.parametrize("secret", ["", "REPLACE_WITH_DEV_CAP_SECRET_KEY", "<CAP_SECRET>CHANGE_ME"])
def test_placeholder_secret_fails_closed(secret: str) -> None:
    rec = _Recorder(lambda req, internal: httpx.Response(200, json={"success": True}))
    result = cap.verify_token(TOKEN, _config(secret=secret), logging.getLogger("t"), rec)
    assert result.ok is False
    assert rec.calls == []


def test_without_endpoints_cap_is_off() -> None:
    rec = _Recorder(lambda req, internal: httpx.Response(500))
    config = _config(public_endpoint="", verify_endpoint="https://x/cap/<CAP_SITE_KEY>/")
    result = cap.verify_token("", config, logging.getLogger("t"), rec)
    assert result.ok is True
    assert rec.calls == []


def test_empty_token_is_rejected_without_calling_cap() -> None:
    rec = _Recorder(lambda req, internal: httpx.Response(200, json={"success": True}))
    result = cap.verify_token("  ", _config(), logging.getLogger("t"), rec)
    assert result.ok is False
    assert rec.calls == []


def test_logs_never_contain_secret_or_token(caplog: pytest.LogCaptureFixture) -> None:
    rec = _Recorder(lambda req, internal: httpx.Response(403, json={"error": "bad secret"}))
    with caplog.at_level(logging.DEBUG):
        cap.verify_token(TOKEN, _config(), logging.getLogger("t"), rec)
    text = caplog.text
    assert "Error verificando Cap CAPTCHA" in text
    assert SECRET not in text
    assert TOKEN not in text


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("laim.example.loc", True),
        ("example.loc", True),
        ("www.laim.app", False),
        ("10.0.2.180", True),
        ("192.168.64.11", False),
        ("localhost", True),
    ],
)
def test_no_proxy_matching(host: str, expected: bool) -> None:
    assert cap.host_bypasses_proxy(host, "localhost,.example.loc,10.0.0.0/8") is expected


def test_public_route_uses_proxy_only_outside_no_proxy() -> None:
    config = _config()
    with cap._client_for("https://laim.example.loc/cap/x/siteverify", config, False) as client:
        assert not client._mounts or all(
            transport is None for transport in client._mounts.values()
        )
    with cap._client_for("https://www.laim.app/cap/x/siteverify", config, False) as client:
        assert any(transport is not None for transport in client._mounts.values())
    with cap._client_for(INTERNAL + "siteverify", config, True) as client:
        assert not client._mounts or all(
            transport is None for transport in client._mounts.values()
        )


def test_env_yaml_of_every_deployed_env_has_internal_verify_endpoint() -> None:
    repo = Path(__file__).resolve().parents[4]
    for env in ("silicon", "dev", "pre"):
        text = (repo / "infrastructure" / "environments" / env / "env.yaml").read_text(
            encoding="utf-8"
        )
        public = [
            line.split(":", 1)[1].strip().strip('"')
            for line in text.splitlines()
            if line.startswith("laim_cap_api_endpoint:")
        ]
        internal = [
            line.split(":", 1)[1].strip().strip('"')
            for line in text.splitlines()
            if line.startswith("laim_cap_verify_endpoint:")
        ]
        assert len(public) == 1 and not cap.is_placeholder(public[0]), env
        assert len(internal) == 1, env
        site_key = public[0].rstrip("/").rsplit("/", 1)[1]
        routes = cap.CapConfig(verify_endpoint=internal[0]).internal_endpoints
        # 3301 (nginx interno) primero; 3300 (Cap directo) solo de transición.
        assert [r.split("://", 1)[1].split("/", 1)[0].rsplit(":", 1)[1] for r in routes] == [
            "3301",
            "3300",
        ], env
        for route in routes:
            assert route.startswith("http://"), env
            # Misma site key en la ruta pública y en cada interna.
            assert route.rstrip("/").rsplit("/", 1)[1] == site_key, env


INTERNAL_LIST = "http://frontend.example.loc:3301/abc123/,http://frontend.example.loc:3300/abc123/"


def test_internal_list_tries_next_route_on_connection_error() -> None:
    def handler(req: httpx.Request, internal: bool) -> httpx.Response:
        if req.url.port == 3301:
            raise httpx.ConnectError("refused", request=req)
        return httpx.Response(200, json={"success": True})

    rec = _Recorder(handler)
    result = cap.verify_token(TOKEN, _config(verify_endpoint=INTERNAL_LIST), logging.getLogger("t"), rec)
    assert result.ok is True
    assert [url for url, _, _ in rec.calls] == [
        "http://frontend.example.loc:3301/abc123/siteverify",
        "http://frontend.example.loc:3300/abc123/siteverify",
    ]


def test_internal_list_never_retries_after_cap_answered() -> None:
    rec = _Recorder(lambda req, internal: httpx.Response(404, json={"error": "Token not found"}))
    result = cap.verify_token(TOKEN, _config(verify_endpoint=INTERNAL_LIST), logging.getLogger("t"), rec)
    assert result.ok is False
    assert len(rec.calls) == 1


def _health(handler, **overrides):
    rec = _Recorder(handler)
    config = _config(verify_endpoint=INTERNAL_LIST, **overrides)
    return cap.check_health(config, logging.getLogger("t"), rec), rec


def test_health_ok_on_200() -> None:
    result, rec = _health(lambda req, internal: httpx.Response(200, json={"status": "ok"}))
    assert result.status == "ok"
    assert rec.calls[0][0] == "http://frontend.example.loc:3301/health"


def test_health_down_on_503() -> None:
    result, _ = _health(lambda req, internal: httpx.Response(503, json={"status": "unavailable"}))
    assert result.status == "down"


def test_health_old_cap_without_health_uses_challenge() -> None:
    def handler(req: httpx.Request, internal: bool) -> httpx.Response:
        if req.url.path == "/health":
            return httpx.Response(404, json={"error": "NOT_FOUND"})
        assert req.method == "POST" and req.url.path == "/abc123/challenge"
        return httpx.Response(200, json={"challenge": {"c": 1, "s": 1, "d": 1}})

    result, _ = _health(handler)
    assert result.status == "ok"


def test_health_skips_refused_route_and_uses_next() -> None:
    def handler(req: httpx.Request, internal: bool) -> httpx.Response:
        if req.url.port == 3301:
            raise httpx.ConnectError("refused", request=req)
        return httpx.Response(200, json={"status": "ok"})

    result, rec = _health(handler)
    assert result.status == "ok"
    assert [url for url, _, _ in rec.calls] == [
        "http://frontend.example.loc:3301/health",
        "http://frontend.example.loc:3300/health",
    ]


def test_health_down_when_no_route_connects() -> None:
    def handler(req: httpx.Request, internal: bool) -> httpx.Response:
        raise httpx.ConnectError("refused", request=req)

    result, _ = _health(handler)
    assert result.status == "down"


def test_health_unknown_on_unexpected_answer() -> None:
    result, _ = _health(lambda req, internal: httpx.Response(500, text="boom"))
    assert result.status == "unknown"


def test_health_off_without_cap() -> None:
    config = cap.CapConfig(public_endpoint="", verify_endpoint="")
    result = cap.check_health(config, logging.getLogger("t"))
    assert result.status == "off"

"""Tests TDD del endurecimiento de APIs (INCIBE-CERT / OWASP API Security Top 10)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_MODULE_PATH = _ROOT / "src/2_shared_application/security/api_hardening.py"


def _load_hardening():
    """Carga el módulo sin importar el paquete numerado."""
    name = "api_hardening_under_test"
    spec = importlib.util.spec_from_file_location(name, _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hardening():
    """Módulo de endurecimiento API."""
    return _load_hardening()


def test_ssrf_rejects_loopback_and_metadata(hardening) -> None:
    """API7 INCIBE: no se puede apuntar a red interna ni a metadatos cloud."""
    assert hardening.is_ssrf_safe_url("https://api.example.com/v1") is True
    assert hardening.is_ssrf_safe_url("http://localhost/admin") is False
    assert hardening.is_ssrf_safe_url("http://127.0.0.1:8003/users") is False
    assert hardening.is_ssrf_safe_url("http://169.254.169.254/latest/meta-data") is False
    assert hardening.is_ssrf_safe_url("http://10.0.0.8/secret") is False
    assert hardening.is_ssrf_safe_url("http://192.168.1.10/admin") is False
    assert hardening.is_ssrf_safe_url("file:///etc/passwd") is False
    assert hardening.is_ssrf_safe_url("not-a-url") is False


def test_ssrf_resolver_blocks_hostname_to_private_ip(hardening) -> None:
    """API7: un hostname público que resuelve a IP privada se rechaza."""
    assert (
        hardening.is_ssrf_safe_url(
            "https://evil.example",
            resolver=lambda _host: ["127.0.0.1"],
        )
        is False
    )
    assert (
        hardening.is_ssrf_safe_url(
            "https://cdn.example",
            resolver=lambda _host: ["93.184.216.34"],
        )
        is True
    )


def test_sanitize_error_hides_internals_outside_dev(hardening) -> None:
    """API8 INCIBE: en pro/pre/silicon no se filtran detalles de excepción."""
    exc = RuntimeError("tabla users no existe en myllm_core_db")
    assert "users" not in hardening.sanitize_error_detail(exc, "pro")
    assert "users" not in hardening.sanitize_error_detail(exc, "silicon")
    assert hardening.sanitize_error_detail(exc, "macbook") == str(exc)


def test_docs_disabled_only_in_pro(hardening) -> None:
    """API9 INCIBE: inventario/docs de API no se publican en producción."""
    pro = hardening.fastapi_docs_kwargs("pro")
    assert pro["docs_url"] is None
    assert pro["redoc_url"] is None
    assert pro["openapi_url"] is None
    silicon = hardening.fastapi_docs_kwargs("silicon")
    assert silicon.get("docs_url") in ("/docs", None) or "docs_url" not in silicon
    if "docs_url" in silicon:
        assert silicon["docs_url"] == "/docs"


def test_rate_limiter_blocks_after_limit(hardening) -> None:
    """API4/API6 INCIBE: consumo de recursos y abuso de flujos con techo."""
    clock = {"now": 1000.0}

    def now() -> float:
        return clock["now"]

    limiter = hardening.SlidingWindowRateLimiter(limit=3, window_seconds=60.0, clock=now)
    assert limiter.check("ip-a").allowed is True
    assert limiter.check("ip-a").allowed is True
    assert limiter.check("ip-a").allowed is True
    denied = limiter.check("ip-a")
    assert denied.allowed is False
    assert denied.retry_after >= 1
    assert limiter.check("ip-b").allowed is True


def test_rate_limiter_window_expires(hardening) -> None:
    """Tras la ventana, el cliente puede volver a llamar."""
    clock = {"now": 0.0}
    limiter = hardening.SlidingWindowRateLimiter(
        limit=1, window_seconds=10.0, clock=lambda: clock["now"]
    )
    assert limiter.check("k").allowed is True
    assert limiter.check("k").allowed is False
    clock["now"] = 10.1
    assert limiter.check("k").allowed is True


def test_auth_paths_use_stricter_bucket(hardening) -> None:
    """Login y refresh se agrupan como bucket de autenticación."""
    settings = hardening.ApiHardeningSettings(service_name="middleware", environment="silicon")
    assert settings.is_auth_path("/login") is True
    assert settings.is_auth_path("/login/request-otp") is True
    assert settings.is_auth_path("/laim/login") is True
    assert settings.is_auth_path("/users") is False
    assert settings.limit_for("/login") < settings.limit_for("/users")


def test_exempt_paths_skip_rate_limit(hardening) -> None:
    """Health y entorno activo no consumen cuota."""
    settings = hardening.ApiHardeningSettings(service_name="middleware", environment="silicon")
    assert settings.is_exempt("/config/environment") is True
    assert settings.is_exempt("/health") is True
    assert settings.is_exempt("/login") is False


def test_security_headers_include_hardening_set(hardening) -> None:
    """API8: cabeceras anti-sniffing, clickjacking y caché de datos."""
    headers = hardening.security_response_headers("req-123")
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Request-ID"] == "req-123"
    assert "Permissions-Policy" in headers


def test_max_body_bytes_larger_for_uploads(hardening) -> None:
    """Subidas de ficheros tienen techo mayor que el JSON de negocio."""
    settings = hardening.ApiHardeningSettings(service_name="middleware", environment="silicon")
    assert settings.max_body_bytes_for("/login") < settings.max_body_bytes_for("/fmo/upload")
    assert settings.max_body_bytes_for("/login") <= 2 * 1024 * 1024


def test_rate_limit_disabled_in_mock_storage(hardening, monkeypatch) -> None:
    """Los unitarios (STORAGE_MODE=mock) no se ahogan con el rate limit."""
    monkeypatch.setenv("STORAGE_MODE", "mock")
    settings = hardening.ApiHardeningSettings.from_env(
        service_name="middleware", environment="silicon"
    )
    assert settings.rate_limit_enabled is False


def test_rate_limit_enabled_for_edge_when_not_mock(hardening, monkeypatch) -> None:
    """El middleware de borde aplica rate limit fuera de mock."""
    monkeypatch.setenv("STORAGE_MODE", "db_only")
    monkeypatch.delenv("API_HARDENING_RATE_LIMIT", raising=False)
    settings = hardening.ApiHardeningSettings.from_env(
        service_name="middleware", environment="silicon"
    )
    assert settings.rate_limit_enabled is True
    internal = hardening.ApiHardeningSettings.from_env(
        service_name="backend_core", environment="silicon"
    )
    assert internal.rate_limit_enabled is False


def test_client_app_allowlist(hardening) -> None:
    """X-Client-App se restringe al inventario conocido (API9)."""
    assert hardening.is_allowed_client_app("frontend") is True
    assert hardening.is_allowed_client_app("laimweb") is True
    assert hardening.is_allowed_client_app("not-a-portal") is False
    assert hardening.is_allowed_client_app("") is False


def test_fastapi_apps_wire_hardening() -> None:
    """Las APIs de runtime aplican el helper compartido."""
    repo = Path(__file__).resolve().parents[3]
    targets = (
        repo / "src/apps/7_service_frontend/apife.py",
        repo / "src/apps/8_service_backend/apibe.py",
        repo / "src/apps/3_backend/apicore.py",
        repo / "src/apps/4_trainer/apitrainer.py",
        repo / "src/apps/9_laimweb/laim_forum_daemon/main.py",
    )
    for path in targets:
        text = path.read_text(encoding="utf-8")
        assert "harden_fastapi_app" in text, path.name
        assert "fastapi_docs_kwargs" in text, path.name


def test_cors_origins_never_wildcard_with_credentials(hardening) -> None:
    """API8: CORS abierto + credentials es una mala configuración."""
    origins = hardening.cors_allow_origins("silicon")
    assert origins
    assert "*" not in origins
    assert any("laim.anewhope.silicon.loc" in origin for origin in origins)

"""Endurecimiento compartido de APIs FastAPI (INCIBE-CERT / OWASP API Top 10).

Referencia: https://www.incibe.es/incibe-cert/blog/seguridad-de-las-api
(actualizado 20/11/2025). Cubre controles prácticos de API4, API6, API7, API8 y API9
sin sustituir la autorización por objeto/función (API1/API5) ni JWT (API2).
"""

from __future__ import annotations

import ipaddress
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

MSG_GENERIC_SERVER_ERROR = "Error interno del servidor"
MSG_RATE_LIMITED = "Demasiadas peticiones. Inténtelo de nuevo más tarde."
MSG_BODY_TOO_LARGE = "Cuerpo de petición demasiado grande"

ALLOWED_CLIENT_APPS = frozenset(
    {
        "frontend",
        "backoffice",
        "laimweb",
        "middleware",
        "broker",
        "trainer",
        "unknown",
    }
)

AUTH_PATH_PREFIXES = (
    "/login",
    "/laim/login",
    "/refresh",
    "/laim/refresh",
    "/register",
    "/laim/register",
)

EXEMPT_PATHS = frozenset(
    {
        "/health",
        "/config/environment",
        "/trainer/chroma/health",
        "/trainer/ollama/health",
        "/training/health",
    }
)

UPLOAD_PATH_MARKERS = ("/fmo/", "/upload", "/files", "/attachment", "/avatar")

EDGE_SERVICES = frozenset({"middleware", "laim_forum"})

SANITIZE_ENVIRONMENTS = frozenset({"pro", "pre", "silicon"})

DEFAULT_JSON_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_UPLOAD_MAX_BYTES = 50 * 1024 * 1024
DEFAULT_WINDOW_SECONDS = 60.0
DEFAULT_EDGE_LIMIT = 180
DEFAULT_AUTH_LIMIT = 20

CORS_ORIGINS_BY_ENV: dict[str, tuple[str, ...]] = {
    "silicon": (
        "https://laim.anewhope.silicon.loc",
        "https://frontend.anewhope.silicon.loc",
    ),
    "macbook": (
        "https://laim.tfmmyllm.ai",
        "https://frontend.tfmmyllm.ai",
        "https://tfmmyllm.ai",
    ),
    "dev": (
        "https://laim.house.loc",
        "https://frontend.house.loc",
    ),
    "pre": (
        "https://www.getmylllm.com",
        "https://laim.anewhope.aws",
        "https://frontend.anewhope.aws",
    ),
    "pro": (
        "https://www.getmylllm.com",
        "https://getmylllm.com",
    ),
}


Resolver = Callable[[str], list[str]]


@dataclass(frozen=True)
class RateLimitDecision:
    """Resultado de comprobar la cuota de un cliente."""

    allowed: bool
    retry_after: int = 0
    remaining: int = 0


class SlidingWindowRateLimiter:
    """Limitador en memoria por clave (IP + bucket), ventana deslizante."""

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if limit < 1:
            raise ValueError("limit debe ser >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds debe ser > 0")
        self._limit = limit
        self._window = window_seconds
        self._clock = clock or time.monotonic
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int | None = None) -> RateLimitDecision:
        """Registra un intento y decide si cabe en la ventana."""
        cap = limit if limit is not None else self._limit
        now = self._clock()
        bucket = self._hits[key]
        cutoff = now - self._window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= cap:
            retry = max(1, int(self._window - (now - bucket[0])) + 1)
            return RateLimitDecision(allowed=False, retry_after=retry, remaining=0)
        bucket.append(now)
        return RateLimitDecision(
            allowed=True,
            remaining=max(0, cap - len(bucket)),
        )


@dataclass
class ApiHardeningSettings:
    """Parámetros de endurecimiento por servicio y entorno."""

    service_name: str
    environment: str
    rate_limit_enabled: bool = False
    window_seconds: float = DEFAULT_WINDOW_SECONDS
    edge_limit: int = DEFAULT_EDGE_LIMIT
    auth_limit: int = DEFAULT_AUTH_LIMIT
    json_max_bytes: int = DEFAULT_JSON_MAX_BYTES
    upload_max_bytes: int = DEFAULT_UPLOAD_MAX_BYTES
    trust_proxy: bool = True

    @classmethod
    def from_env(
        cls,
        *,
        service_name: str,
        environment: str | None = None,
    ) -> ApiHardeningSettings:
        """Construye settings desde variables de entorno."""
        env_name = (environment or os.environ.get("ENVIRONMENT") or "macbook").strip()
        storage_mode = os.environ.get("STORAGE_MODE", "").strip().lower()
        explicit = os.environ.get("API_HARDENING_RATE_LIMIT", "").strip()
        is_edge = service_name in EDGE_SERVICES
        if explicit == "0":
            enabled = False
        elif explicit == "1":
            enabled = True
        else:
            enabled = is_edge and storage_mode != "mock"
        return cls(
            service_name=service_name,
            environment=env_name,
            rate_limit_enabled=enabled,
        )

    def is_auth_path(self, path: str) -> bool:
        """True si la ruta es de autenticación (cuota más estricta)."""
        return any(path == prefix or path.startswith(f"{prefix}/") for prefix in AUTH_PATH_PREFIXES)

    def is_exempt(self, path: str) -> bool:
        """Rutas de salud / inventario de entorno que no gastan cuota."""
        return path in EXEMPT_PATHS

    def limit_for(self, path: str) -> int:
        """Cuota de la ventana para la ruta."""
        if self.is_auth_path(path):
            return self.auth_limit
        return self.edge_limit

    def max_body_bytes_for(self, path: str) -> int:
        """Techo de cuerpo según si la ruta es de subida."""
        lowered = path.lower()
        if any(marker in lowered for marker in UPLOAD_PATH_MARKERS):
            return self.upload_max_bytes
        return self.json_max_bytes


def is_allowed_client_app(client_app: str) -> bool:
    """Valida X-Client-App contra el inventario de portales/servicios."""
    return client_app.strip().lower() in ALLOWED_CLIENT_APPS


def cors_allow_origins(environment: str) -> list[str]:
    """Orígenes CORS explícitos (nunca '*' con credentials)."""
    return list(CORS_ORIGINS_BY_ENV.get(environment, CORS_ORIGINS_BY_ENV["silicon"]))


def fastapi_docs_kwargs(environment: str) -> dict[str, Any]:
    """Oculta Swagger/ReDoc/OpenAPI en producción (API9 inventario)."""
    if environment == "pro":
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}


def sanitize_error_detail(exc: BaseException, environment: str) -> str:
    """Evita filtrar internals en entornos no locales (API8)."""
    if environment in SANITIZE_ENVIRONMENTS:
        return MSG_GENERIC_SERVER_ERROR
    return str(exc) or MSG_GENERIC_SERVER_ERROR


def security_response_headers(request_id: str) -> dict[str, str]:
    """Cabeceras de endurecimiento para respuestas de API."""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "X-Request-ID": request_id,
    }


def _is_private_ip(value: str) -> bool:
    """True si el literal es loopback, link-local o red privada."""
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return False
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def is_ssrf_safe_url(url: str, resolver: Resolver | None = None) -> bool:
    """Valida que una URL no apunte a destinos internos (API7 SSRF)."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False
    if host in {"localhost", "metadata.google.internal"}:
        return False
    if host.endswith(".internal") or host.endswith(".local"):
        return False
    if _is_private_ip(host):
        return False
    if resolver is not None:
        try:
            resolved = resolver(host)
        except (OSError, ValueError):
            return False
        if any(_is_private_ip(item) for item in resolved):
            return False
    return True


def _header_map(scope: Mapping[str, Any]) -> dict[str, str]:
    """Convierte headers ASGI a dict minúsculas."""
    result: dict[str, str] = {}
    for raw_name, raw_value in scope.get("headers") or ():
        name = raw_name.decode("latin-1").lower()
        result[name] = raw_value.decode("latin-1")
    return result


def _client_ip(scope: Mapping[str, Any], headers: Mapping[str, str], trust_proxy: bool) -> str:
    """IP del cliente; usa X-Forwarded-For solo si hay proxy de confianza."""
    if trust_proxy:
        forwarded = headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip() or "unknown"
    client = scope.get("client")
    if client and client[0]:
        return str(client[0])
    return "unknown"


async def _send_json(
    send: Callable,
    status_code: int,
    payload: dict[str, str],
    *,
    request_id: str,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> None:
    """Respuesta JSON corta desde el middleware ASGI."""
    import json

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = [
        (b"content-type", b"application/json; charset=utf-8"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    for name, value in security_response_headers(request_id).items():
        headers.append((name.lower().encode("latin-1"), value.encode("latin-1")))
    if extra_headers:
        headers.extend(extra_headers)
    await send({"type": "http.response.start", "status": status_code, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class ApiHardeningMiddleware:
    """Middleware ASGI: tamaño, rate limit y cabeceras de seguridad."""

    def __init__(
        self,
        app: Callable,
        settings: ApiHardeningSettings,
        limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        self.app = app
        self.settings = settings
        self.limiter = limiter or SlidingWindowRateLimiter(
            limit=settings.edge_limit,
            window_seconds=settings.window_seconds,
        )

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        headers = _header_map(scope)
        request_id = headers.get("x-request-id") or str(uuid.uuid4())

        content_length = headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
            except ValueError:
                size = 0
            if size > self.settings.max_body_bytes_for(path):
                await _send_json(
                    send,
                    413,
                    {"detail": MSG_BODY_TOO_LARGE},
                    request_id=request_id,
                )
                return

        if self.settings.rate_limit_enabled and not self.settings.is_exempt(path):
            ip = _client_ip(scope, headers, self.settings.trust_proxy)
            bucket = "auth" if self.settings.is_auth_path(path) else "api"
            decision = self.limiter.check(
                f"{ip}:{bucket}",
                limit=self.settings.limit_for(path),
            )
            if not decision.allowed:
                logger.warning(
                    "[API-HARDENING] 429 service=%s ip=%s path=%s",
                    self.settings.service_name,
                    ip,
                    path,
                )
                await _send_json(
                    send,
                    429,
                    {"detail": MSG_RATE_LIMITED},
                    request_id=request_id,
                    extra_headers=[
                        (b"retry-after", str(decision.retry_after).encode("ascii")),
                    ],
                )
                return

        async def send_with_headers(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                raw_headers = list(message.get("headers") or [])
                existing = {name for name, _value in raw_headers}
                for name, value in security_response_headers(request_id).items():
                    encoded = name.lower().encode("latin-1")
                    if encoded not in existing:
                        raw_headers.append((encoded, value.encode("latin-1")))
                message = {**message, "headers": raw_headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


def harden_fastapi_app(
    app: Any,
    *,
    service_name: str,
    environment: str | None = None,
) -> ApiHardeningSettings:
    """Aplica middleware y handler de 500 sanitizado a una app FastAPI."""
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    settings = ApiHardeningSettings.from_env(
        service_name=service_name,
        environment=environment,
    )
    app.add_middleware(ApiHardeningMiddleware, settings=settings)

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, (HTTPException, StarletteHTTPException)):
            raise exc
        logger.exception(
            "[API-HARDENING] 500 service=%s path=%s",
            settings.service_name,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": sanitize_error_detail(exc, settings.environment)},
            headers=security_response_headers(str(uuid.uuid4())),
        )

    logger.info(
        "[API-HARDENING] activo service=%s env=%s rate_limit=%s",
        settings.service_name,
        settings.environment,
        settings.rate_limit_enabled,
    )
    return settings

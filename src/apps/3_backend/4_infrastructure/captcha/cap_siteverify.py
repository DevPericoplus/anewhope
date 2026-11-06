"""Verificación de tokens Cap (siteverify) para el alta pública de LAIM.

Por qué así (QA laimweb 0.12.65, 2026-11-06):

- silicon y dev: ``https://laim.<dominio interno>/cap/...`` lleva el
  certificado de la CA local de anewhope, que el backend no tiene en su
  almacén → ``CERTIFICATE_VERIFY_FAILED`` y ninguna alta pasaba.
- ``httpx.Client(proxy=...)`` ignora ``NO_PROXY``: siteverify salía por
  Squid también hacia hosts internos.

Reglas:

1. Si el entorno define ``laim_cap_verify_endpoint`` (Cap por la red
   interna, p. ej. ``http://frontend.<dominio>:3301/<site-key>/``), se
   verifica ahí, sin proxy y sin heredar variables de proxy del proceso.
   Puede ser una lista separada por comas: se prueban en orden mientras
   la conexión no llegue a abrirse (3301 = server interno de nginx, 3300 =
   puerto directo del Cap anterior, mientras dure la transición).
2. Si no, o si la conexión interna no llega a abrirse, se usa el
   endpoint público ``laim_cap_api_endpoint``. El proxy solo se aplica
   si el host no está en ``proxy_no_proxy``. ``laim_cap_ca_bundle``
   (ruta a un PEM) permite validar una CA propia.
3. Solo se reintenta cuando la petición no llegó a salir (error de
   conexión): un token de Cap se gasta en la primera verificación.
4. Con Cap configurado, un secret vacío o de marcador rechaza el alta:
   nunca se deja pasar sin verificar.
5. El registro dice el motivo (HTTP, timeout, ``success=false`` y el
   error de Cap) sin el secret ni el token.
"""

from __future__ import annotations

import ipaddress
import logging
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

PLACEHOLDER_MARKERS = ("<CAP_SITE_KEY>", "REPLACE_WITH", "CAP-SITE-KEY", "CHANGE_ME")
VERIFY_TIMEOUT_S = 10.0


def is_placeholder(value: str | None) -> bool:
    """True si el valor está vacío o es un marcador sin rellenar."""
    text = (value or "").strip()
    if not text:
        return True
    upper = text.upper()
    return any(marker in upper for marker in PLACEHOLDER_MARKERS)


@dataclass(frozen=True)
class CapConfig:
    """Valores del entorno para verificar un token."""

    public_endpoint: str = ""
    verify_endpoint: str = ""
    secret: str = ""
    proxy_url: str = ""
    no_proxy: str = ""
    ca_bundle: str = ""

    @property
    def enabled(self) -> bool:
        """Cap está activo si hay un endpoint (el widget se pinta con él)."""
        return not is_placeholder(self.public_endpoint) or bool(self.internal_endpoints)

    @property
    def internal_endpoints(self) -> list[str]:
        """Rutas internas en orden (``verify_endpoint`` admite comas)."""
        return [
            part.strip()
            for part in (self.verify_endpoint or "").split(",")
            if not is_placeholder(part)
        ]


@dataclass(frozen=True)
class CapHealthResult:
    """Estado de Cap visto por backend_core: ok, down, unknown u off."""

    status: str
    reason: str


@dataclass(frozen=True)
class CapVerifyResult:
    """Resultado de siteverify: ``ok`` y el motivo para el registro."""

    ok: bool
    reason: str


def host_bypasses_proxy(host: str, no_proxy: str) -> bool:
    """Aplica ``no_proxy`` (dominios, ``.sufijos``, IPs y CIDR) a ``host``."""
    host = (host or "").strip().lower().strip("[]")
    if not host:
        return False
    try:
        host_ip = ipaddress.ip_address(host)
    except ValueError:
        host_ip = None
    for raw in (no_proxy or "").split(","):
        entry = raw.strip().lower()
        if not entry:
            continue
        if entry == "*":
            return True
        if host_ip is not None:
            try:
                if host_ip in ipaddress.ip_network(entry, strict=False):
                    return True
            except ValueError:
                pass
            continue
        bare = entry.lstrip(".")
        if host == bare or host.endswith("." + bare):
            return True
    return False


def _siteverify_url(endpoint: str) -> str:
    return endpoint.strip().rstrip("/") + "/siteverify"


def _client_for(url: str, config: CapConfig, internal: bool) -> httpx.Client:
    kwargs: dict[str, object] = {"timeout": VERIFY_TIMEOUT_S, "trust_env": False}
    if config.ca_bundle and url.startswith("https://"):
        kwargs["verify"] = config.ca_bundle
    host = urlsplit(url).hostname or ""
    if not internal and config.proxy_url and not host_bypasses_proxy(host, config.no_proxy):
        kwargs["proxy"] = config.proxy_url
    return httpx.Client(**kwargs)


def _describe_failure(response: httpx.Response) -> str:
    detail = ""
    try:
        payload = response.json()
        if isinstance(payload, dict):
            detail = str(payload.get("error") or payload.get("message") or "")
    except ValueError:
        detail = ""
    return f"HTTP {response.status_code}" + (f" ({detail[:120]})" if detail else "")


def verify_token(
    token: str,
    config: CapConfig,
    logger: logging.Logger,
    client_factory: Callable[[str, CapConfig, bool], httpx.Client] = _client_for,
) -> CapVerifyResult:
    """Verifica ``token`` contra Cap. Nunca lanza excepción."""
    if not config.enabled:
        return CapVerifyResult(True, "cap no configurado en este entorno")
    if is_placeholder(config.secret):
        logger.error(
            "Cap CAPTCHA mal configurado: laim_cap_secret vacío o de marcador; "
            "el alta se rechaza hasta poner el secret de la site key del entorno"
        )
        return CapVerifyResult(False, "secret no configurado")
    if not (token or "").strip():
        return CapVerifyResult(False, "sin token")

    targets: list[tuple[str, bool]] = [
        (_siteverify_url(endpoint), True) for endpoint in config.internal_endpoints
    ]
    if not is_placeholder(config.public_endpoint):
        targets.append((_siteverify_url(config.public_endpoint), False))

    body = {"secret": config.secret, "response": token.strip()}
    last_reason = "sin endpoint"
    for index, (url, internal) in enumerate(targets):
        route = "interno" if internal else "público"
        host = urlsplit(url).netloc
        try:
            with client_factory(url, config, internal) as client:
                response = client.post(url, json=body)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            # La petición no salió: el token sigue sin gastar y se puede
            # probar la ruta siguiente.
            last_reason = f"sin conexión con Cap {route} {host}: {exc}"
            logger.warning("Cap siteverify: %s", last_reason)
            if index + 1 < len(targets):
                continue
            logger.error("Error verificando Cap CAPTCHA: %s", last_reason)
            return CapVerifyResult(False, last_reason)
        except httpx.HTTPError as exc:
            # Pudo llegar a Cap: no se repite con el mismo token.
            reason = f"{type(exc).__name__} con Cap {route} {host}: {exc}"
            logger.error("Error verificando Cap CAPTCHA: %s", reason)
            return CapVerifyResult(False, reason)

        if response.status_code != 200:
            reason = f"Cap {route} {host} respondió {_describe_failure(response)}"
            logger.error("Error verificando Cap CAPTCHA: %s", reason)
            return CapVerifyResult(False, reason)
        try:
            payload = response.json()
        except ValueError:
            reason = f"Cap {route} {host} devolvió un cuerpo que no es JSON"
            logger.error("Error verificando Cap CAPTCHA: %s", reason)
            return CapVerifyResult(False, reason)
        if isinstance(payload, dict) and payload.get("success") is True:
            return CapVerifyResult(True, f"verificado por Cap {route} {host}")
        detail = ""
        if isinstance(payload, dict):
            detail = str(payload.get("error") or "")[:120]
        reason = f"Cap {route} {host}: success=false" + (f" ({detail})" if detail else "")
        logger.warning("Cap CAPTCHA rechazado: %s", reason)
        return CapVerifyResult(False, reason)
    return CapVerifyResult(False, last_reason)


HEALTH_TIMEOUT_S = 3.0


def _health_client(url: str, config: CapConfig, internal: bool) -> httpx.Client:
    return httpx.Client(timeout=HEALTH_TIMEOUT_S, trust_env=False)


def _origin(endpoint: str) -> str:
    parts = urlsplit(endpoint.strip())
    return f"{parts.scheme}://{parts.netloc}"


def check_health(
    config: CapConfig,
    logger: logging.Logger,
    client_factory: Callable[[str, CapConfig, bool], httpx.Client] = _health_client,
) -> CapHealthResult:
    """Estado de Cap por las rutas internas. Nunca lanza excepción.

    - ``ok``: ``/health`` 200, o (Cap < 3.1.13 sin ``/health``) un
      ``POST <endpoint>challenge`` 200, que solo firma un reto sin estado.
    - ``down``: ``/health`` 503 (Valkey no contesta) o ninguna ruta interna
      abre conexión.
    - ``unknown``: cualquier otra respuesta (se registra el motivo).
    - ``off``: Cap no está configurado en este entorno.
    """
    if not config.enabled:
        return CapHealthResult("off", "cap no configurado")
    endpoints = config.internal_endpoints
    if not endpoints:
        return CapHealthResult("unknown", "sin ruta interna (laim_cap_verify_endpoint)")
    reasons: list[str] = []
    for endpoint in endpoints:
        host = urlsplit(endpoint).netloc
        try:
            with client_factory(endpoint, config, True) as client:
                response = client.get(_origin(endpoint) + "/health")
                if response.status_code == 200:
                    return CapHealthResult("ok", f"/health 200 en {host}")
                if response.status_code == 503:
                    reason = f"Cap {host}: /health 503 (Valkey no responde)"
                    logger.error("Cap no disponible para el alta: %s", reason)
                    return CapHealthResult("down", reason)
                if response.status_code == 404:
                    probe = client.post(endpoint.rstrip("/") + "/challenge", json={})
                    if probe.status_code == 200:
                        return CapHealthResult("ok", f"challenge 200 en {host} (sin /health)")
                    reason = f"Cap {host}: challenge respondió HTTP {probe.status_code}"
                    logger.warning("Estado de Cap desconocido: %s", reason)
                    return CapHealthResult("unknown", reason)
                reason = f"Cap {host}: /health respondió HTTP {response.status_code}"
                logger.warning("Estado de Cap desconocido: %s", reason)
                return CapHealthResult("unknown", reason)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            reasons.append(f"sin conexión con {host}: {exc}")
            continue
        except httpx.HTTPError as exc:
            reason = f"{type(exc).__name__} con Cap {host}: {exc}"
            logger.warning("Estado de Cap desconocido: %s", reason)
            return CapHealthResult("unknown", reason)
    reason = "; ".join(reasons) or "sin rutas internas"
    logger.error("Cap no disponible para el alta: %s", reason)
    return CapHealthResult("down", reason)

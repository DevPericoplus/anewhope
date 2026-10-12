"""Envío Gmail API (HTTPS) — Mail Gateway. Solo messages.send."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import GMAIL_SEND_URL, MailGatewayConfig, persist_token
from .rfc822 import build_rfc822, extract_mailbox

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

logger = logging.getLogger("mail_gateway")


class MailGatewayError(Exception):
    """Fallo de envío o de configuración."""


class MailGatewayNotReady(MailGatewayError):
    """Faltan credenciales o token OAuth."""


@dataclass(frozen=True)
class SendResult:
    """Respuesta mínima de Gmail messages.send."""

    id: str
    thread_id: str


HttpDo = Callable[[Request], tuple[int, bytes]]


def _default_http(req: Request) -> tuple[int, bytes]:
    """HTTPS a Gmail. No registra Authorization ni el raw."""
    try:
        with urlopen(req, timeout=30) as resp:  # nosec B310 — URL fija GMAIL_SEND_URL
            return resp.status, resp.read()
    except HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        return exc.code, raw
    except URLError as exc:
        raise MailGatewayError(f"gmail unreachable: {exc.reason}") from exc


def _access_token(cfg: MailGatewayConfig) -> str:
    """Lee access_token del fichero 0600. No lo registra."""
    try:
        data = json.loads(Path(cfg.token_file).read_text(encoding="utf-8"))
    except OSError as exc:
        raise MailGatewayNotReady("token OAuth ilegible") from exc
    token = str(data.get("access_token") or "").strip()
    if not token:
        raise MailGatewayNotReady("token OAuth vacío")
    return token


def _oauth_client(cfg: MailGatewayConfig) -> dict[str, Any]:
    """Lee client_id/secret del JSON de Google (web o installed)."""
    try:
        data = json.loads(Path(cfg.credentials_file).read_text(encoding="utf-8"))
    except OSError as exc:
        raise MailGatewayNotReady("credentials OAuth ilegibles") from exc
    client = data.get("web") or data.get("installed") or data
    return client if isinstance(client, dict) else {}


def refresh_access_token(cfg: MailGatewayConfig, http_do: HttpDo | None = None) -> str:
    """Renueva access_token y reescribe el fichero 0600. No registra secretos."""
    token_data = json.loads(Path(cfg.token_file).read_text(encoding="utf-8"))
    refresh = str(token_data.get("refresh_token") or "").strip()
    client = _oauth_client(cfg)
    client_id = str(client.get("client_id") or "").strip()
    client_secret = str(client.get("client_secret") or "").strip()
    if not refresh or not client_id:
        raise MailGatewayNotReady("no hay refresh_token OAuth")
    body = urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    req = Request(
        GOOGLE_TOKEN_URL,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    doer = http_do or _default_http
    status, raw_body = doer(req)
    if status < 200 or status >= 300:
        raise MailGatewayNotReady("Gmail rechazó el refresh OAuth")
    payload: dict[str, Any] = json.loads(raw_body.decode("utf-8") or "{}")
    access = str(payload.get("access_token") or "").strip()
    if not access:
        raise MailGatewayNotReady("refresh OAuth sin access_token")
    token_data["access_token"] = access
    if payload.get("refresh_token"):
        token_data["refresh_token"] = payload["refresh_token"]
    persist_token(cfg.token_file, token_data)
    return access


def send_message(
    cfg: MailGatewayConfig,
    to: str,
    subject: str,
    body: str,
    html: str = "",
    cc: str = "",
    http_do: HttpDo | None = None,
) -> SendResult:
    """Construye RFC822 y POST /messages/send. TLS del urlopen HTTPS."""
    if not cfg.ready():
        raise MailGatewayNotReady("Mail Gateway sin credentials_file")
    if not cfg.has_token():
        raise MailGatewayNotReady("Mail Gateway sin token OAuth")
    to = to.strip()
    if not to or "@" not in to:
        raise MailGatewayError("destinatario inválido")
    raw = build_rfc822(
        from_addr=cfg.from_header(),
        to=to,
        subject=subject,
        body=body,
        html=html,
        cc=cc,
    )
    payload = json.dumps({"raw": raw}).encode("utf-8")
    token = _access_token(cfg)
    doer = http_do or _default_http

    def _send(access: str) -> tuple[int, bytes]:
        req = Request(
            GMAIL_SEND_URL,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {access}",
                "Content-Type": "application/json",
            },
        )
        return doer(req)

    status, raw_body = _send(token)
    if status in (401, 403):
        token = refresh_access_token(cfg, http_do=doer)
        status, raw_body = _send(token)
    if status in (401, 403):
        raise MailGatewayNotReady("Gmail rechazó el token OAuth")
    if status < 200 or status >= 300:
        raise MailGatewayError(f"gmail {status}")
    sent: dict[str, Any] = json.loads(raw_body.decode("utf-8") or "{}")
    logger.info(
        "Mail Gateway enviado mailbox=%s to_domain=%s",
        extract_mailbox(cfg.from_header()),
        to.rsplit("@", 1)[-1],
    )
    return SendResult(id=str(sent.get("id") or ""), thread_id=str(sent.get("threadId") or ""))

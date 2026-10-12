"""Orquestación de envío usada por el Router del middleware."""

from __future__ import annotations

from .config import MailGatewayConfig, load_config_from_env
from .gmail_client import HttpDo, SendResult, send_message


def send_support_mail(
    to: str,
    subject: str,
    body: str,
    *,
    cfg: MailGatewayConfig | None = None,
    http_do: HttpDo | None = None,
) -> SendResult:
    """Envía desde soporte@laim.app. No registra cuerpo ni token."""
    return send_message(
        cfg or load_config_from_env(),
        to=to,
        subject=subject,
        body=body,
        http_do=http_do,
    )

"""Mail Gateway: envío Gmail desde soporte@laim.app (capa aplicación)."""

from .config import MailGatewayConfig, load_config_from_env
from .gmail_client import MailGatewayError, MailGatewayNotReady, SendResult, send_message
from .rfc822 import build_rfc822, decode_raw
from .service import send_support_mail

__all__ = [
    "MailGatewayConfig",
    "MailGatewayError",
    "MailGatewayNotReady",
    "SendResult",
    "build_rfc822",
    "decode_raw",
    "load_config_from_env",
    "send_message",
    "send_support_mail",
]

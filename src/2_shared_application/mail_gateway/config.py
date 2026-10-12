"""Configuración de Mail Gateway (buzón Workspace, ficheros 0600)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAILBOX = "soporte@laim.app"
DEFAULT_DISPLAY_NAME = "Departamento de soporte de LAIM"
DEFAULT_CREDENTIALS_FILE = "/run/mail-gateway/credentials.json"
DEFAULT_TOKEN_FILE = "/run/mail-gateway/token.json"
MAIL_SCOPE = "https://mail.google.com/"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


@dataclass(frozen=True)
class MailGatewayConfig:
    """Rutas y buzón inyectados por vault → .env del middleware."""

    mailbox: str
    display_name: str
    credentials_file: str
    token_file: str

    def from_header(self) -> str:
        """From visible: `Nombre <buzón>`."""
        mailbox = self.mailbox.strip()
        name = self.display_name.strip()
        if name:
            return f"{name} <{mailbox}>"
        return mailbox

    def ready(self) -> bool:
        """Hay buzón y existe el JSON del cliente OAuth."""
        if not self.mailbox.strip():
            return False
        path = Path(self.credentials_file)
        return path.is_file() and path.stat().st_size > 2

    def has_token(self) -> bool:
        path = Path(self.token_file)
        return path.is_file() and path.stat().st_size > 2


def load_config_from_env() -> MailGatewayConfig:
    """Lee LAIM_MAIL_* del entorno del contenedor middleware."""
    return MailGatewayConfig(
        mailbox=os.environ.get("LAIM_MAIL_MAILBOX", DEFAULT_MAILBOX).strip()
        or DEFAULT_MAILBOX,
        display_name=os.environ.get("LAIM_MAIL_DISPLAY_NAME", DEFAULT_DISPLAY_NAME).strip()
        or DEFAULT_DISPLAY_NAME,
        credentials_file=os.environ.get(
            "LAIM_MAIL_CREDENTIALS_FILE", DEFAULT_CREDENTIALS_FILE
        ).strip()
        or DEFAULT_CREDENTIALS_FILE,
        token_file=os.environ.get("LAIM_MAIL_TOKEN_FILE", DEFAULT_TOKEN_FILE).strip()
        or DEFAULT_TOKEN_FILE,
    )


def persist_token(token_file: str, token: dict) -> None:
    """Escribe el token OAuth con 0600 (mismo criterio que laim_maintenance)."""
    path = Path(token_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(token), encoding="utf-8")
    path.chmod(0o600)

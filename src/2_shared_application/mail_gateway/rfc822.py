"""RFC822 para Mail Gateway — mismo contrato que gmailworkspace.buildRFC822."""

from __future__ import annotations

import base64
import quopri
import re
from datetime import datetime, timezone
from email.utils import format_datetime


def extract_mailbox(from_addr: str) -> str:
    """Saca el buzón de `Nombre <buzon>` o el propio from."""
    from_addr = from_addr.strip()
    match = re.search(r"<([^>]+)>", from_addr)
    if match:
        return match.group(1).strip()
    return from_addr


def encode_subject(subject: str) -> str:
    """Codifica asunto no-ASCII como UTF-8 Base64 (RFC 2047)."""
    if any(ord(ch) > 127 for ch in subject):
        token = base64.b64encode(subject.encode("utf-8")).decode("ascii")
        return f"=?UTF-8?B?{token}?="
    return subject


def encode_quoted_printable(body: str) -> str:
    """QP compatible con el writer de Go (líneas CRLF)."""
    encoded = quopri.encodestring(body.encode("utf-8"), quotetabs=False)
    return encoded.decode("ascii")


def write_common_headers(from_addr: str, to: str, subject: str, cc: str = "") -> str:
    """Date, Reply-To, Content-Language: es. Sin Message-ID ni List-Unsubscribe."""
    mailbox = extract_mailbox(from_addr)
    now = datetime.now(timezone.utc).astimezone()
    lines = [
        f"From: {from_addr}",
        f"To: {to}",
    ]
    if cc.strip():
        lines.append(f"Cc: {cc.strip()}")
    if mailbox:
        lines.append(f"Reply-To: {mailbox}")
    lines.extend(
        [
            f"Date: {format_datetime(now)}",
            f"Subject: {encode_subject(subject)}",
            "MIME-Version: 1.0",
            "Content-Language: es",
        ]
    )
    return "\r\n".join(lines) + "\r\n"


def write_text_part(content_type: str, body: str) -> str:
    """Parte text/plain o text/html en quoted-printable."""
    qp = encode_quoted_printable(body)
    block = (
        f"Content-Type: {content_type}; charset=UTF-8\r\n"
        "Content-Transfer-Encoding: quoted-printable\r\n"
        "\r\n"
        f"{qp}"
    )
    if not body.endswith("\n"):
        block += "\r\n"
    return block


def build_rfc822(
    from_addr: str,
    to: str,
    subject: str,
    body: str,
    html: str = "",
    cc: str = "",
) -> str:
    """Devuelve el raw base64url que espera Gmail messages.send.

    v1 no embebe CID: HTML sin imágenes → multipart/alternative;
    solo texto → text/plain. Nunca multipart/related.
    """
    headers = write_common_headers(from_addr, to, subject, cc=cc)
    if not html.strip():
        raw = headers + write_text_part("text/plain", body)
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")
    alt = "laim-alt-1"
    raw = (
        headers
        + f'Content-Type: multipart/alternative; boundary="{alt}"\r\n'
        + "\r\n"
        + f"--{alt}\r\n"
        + write_text_part("text/plain", body)
        + f"--{alt}\r\n"
        + write_text_part("text/html", html)
        + f"--{alt}--\r\n"
    )
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_raw(raw: str) -> str:
    """Decodifica el raw Gmail a texto RFC822."""
    padded = raw + "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")

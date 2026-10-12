"""Contrato RFC822 de Mail Gateway — mismos asserts que gmail_test.go."""

from __future__ import annotations

import sys
from pathlib import Path

shared = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(shared))

from mail_gateway.rfc822 import build_rfc822, decode_raw  # noqa: E402


def test_build_rfc822_encodes_raw_like_gmail_workspace() -> None:
    raw = build_rfc822(
        from_addr="Soporte <soporte@laim.app>",
        to="a@b.c",
        subject="Hola",
        body="cuerpo",
    )
    decoded = decode_raw(raw)
    for part in (
        "From: Soporte <soporte@laim.app>",
        "To: a@b.c",
        "Subject: Hola",
        "cuerpo",
        "Date:",
        "Reply-To: soporte@laim.app",
        "Content-Language: es",
        "quoted-printable",
    ):
        assert part in decoded, f"falta {part!r} en {decoded}"
    for bad in ("List-Unsubscribe:", "Message-ID:", "multipart/related"):
        assert bad not in decoded, f"no debe llevar {bad!r}"


def test_build_rfc822_html_without_images_is_alternative() -> None:
    raw = build_rfc822(
        from_addr="Soporte <soporte@laim.app>",
        to="a@b.c",
        subject="Re: x",
        body="cuerpo plano",
        html="<p>cuerpo plano</p>",
    )
    decoded = decode_raw(raw)
    assert "multipart/alternative" in decoded
    assert "multipart/related" not in decoded


def test_build_rfc822_plain_has_no_cid() -> None:
    raw = build_rfc822(
        from_addr="Departamento de soporte de LAIM <soporte@laim.app>",
        to="usuario@example.com",
        subject="Restablecer contraseña",
        body="Hola pedro,\n\nUsa /r/abc\n",
    )
    decoded = decode_raw(raw)
    assert "Content-ID:" not in decoded
    assert "cid:" not in decoded.lower()
    assert "Reply-To: soporte@laim.app" in decoded

"""Envío Gmail: el transporte se mockea; el raw RFC822 es real."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.request import Request

import pytest

shared = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(shared))

from mail_gateway.config import MailGatewayConfig, persist_token  # noqa: E402
from mail_gateway.gmail_client import (  # noqa: E402
    MailGatewayNotReady,
    send_message,
)
from mail_gateway.rfc822 import decode_raw  # noqa: E402


@pytest.fixture
def gateway_files(tmp_path: Path) -> MailGatewayConfig:
    creds = tmp_path / "credentials.json"
    creds.write_text(
        '{"web":{"client_id":"x","client_secret":"s"}}', encoding="utf-8"
    )
    token = tmp_path / "token.json"
    persist_token(str(token), {"access_token": "ya29.test-token", "refresh_token": "1//r"})
    assert token.stat().st_mode & 0o777 == 0o600
    return MailGatewayConfig(
        mailbox="soporte@laim.app",
        display_name="Soporte",
        credentials_file=str(creds),
        token_file=str(token),
    )


def test_send_posts_raw_rfc822_over_https(gateway_files: MailGatewayConfig) -> None:
    captured: dict[str, object] = {}

    def fake_http(req: Request) -> tuple[int, bytes]:
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["auth"] = req.get_header("Authorization")
        captured["body"] = req.data
        return 200, json.dumps({"id": "msg-1", "threadId": "th-1"}).encode("utf-8")

    result = send_message(
        gateway_files,
        to="usuario@laim.example",
        subject="Restablecer contraseña",
        body="Hola ana,\n\nEnlace /r/tok\n",
        http_do=fake_http,
    )
    assert result.id == "msg-1"
    assert captured["url"] == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    assert captured["method"] == "POST"
    assert captured["auth"] == "Bearer ya29.test-token"
    payload = json.loads(captured["body"])
    decoded = decode_raw(payload["raw"])
    assert "From: Soporte <soporte@laim.app>" in decoded
    assert "To: usuario@laim.example" in decoded
    assert "Reply-To: soporte@laim.app" in decoded
    assert "Hola ana" in decoded
    assert "List-Unsubscribe:" not in decoded
    assert "Message-ID:" not in decoded


def test_send_refreshes_oauth_and_rewrites_token_0600(
    gateway_files: MailGatewayConfig,
) -> None:
    calls: list[str] = []

    def fake_http(req: Request) -> tuple[int, bytes]:
        calls.append(req.full_url)
        if "oauth2.googleapis.com" in req.full_url:
            return 200, json.dumps({"access_token": "ya29.refreshed"}).encode("utf-8")
        auth = req.get_header("Authorization")
        if auth == "Bearer ya29.test-token":
            return 401, b'{"error":"invalid_token"}'
        assert auth == "Bearer ya29.refreshed"
        return 200, json.dumps({"id": "msg-2", "threadId": "th-2"}).encode("utf-8")

    result = send_message(
        gateway_files,
        to="usuario@laim.example",
        subject="x",
        body="y",
        http_do=fake_http,
    )
    assert result.id == "msg-2"
    assert any("oauth2.googleapis.com" in url for url in calls)
    stored = json.loads(Path(gateway_files.token_file).read_text(encoding="utf-8"))
    assert stored["access_token"] == "ya29.refreshed"
    assert Path(gateway_files.token_file).stat().st_mode & 0o777 == 0o600


def test_send_without_token_fails(tmp_path: Path) -> None:
    creds = tmp_path / "credentials.json"
    creds.write_text("{}", encoding="utf-8")
    cfg = MailGatewayConfig(
        mailbox="soporte@laim.app",
        display_name="Soporte",
        credentials_file=str(creds),
        token_file=str(tmp_path / "missing.json"),
    )
    with pytest.raises(MailGatewayNotReady):
        send_message(cfg, to="a@b.c", subject="x", body="y")

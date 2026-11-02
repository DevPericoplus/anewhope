"""La imagen de un mensaje sale en el mismo envío, no en un clic aparte."""

from __future__ import annotations

import base64

from laim_web.laim_forum_mixin import forum_attachment_payload


def test_attachment_payload_is_a_post_image() -> None:
    raw = b"\x89PNG\r\n"
    payload = forum_attachment_payload(" captura.PNG ", " image/png ", raw)
    assert payload["file_name"] == "captura.PNG"
    assert payload["mime_type"] == "image/png"
    assert payload["image_kind"] == "post_attachment"
    assert base64.b64decode(payload["data_base64"]) == raw


def test_attachment_payload_fills_missing_name_and_type() -> None:
    payload = forum_attachment_payload("  ", "", b"abc")
    assert payload["file_name"] == "imagen"
    assert payload["mime_type"] == "application/octet-stream"

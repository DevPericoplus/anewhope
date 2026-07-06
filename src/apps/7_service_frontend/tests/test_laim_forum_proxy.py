"""Tests del proxy transparente del foro LAIM en middleware."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from apife import _laim_forum_proxy_response


def test_forum_proxy_response_json_success() -> None:
    """Respuesta JSON exitosa se devuelve tal cual."""
    result = _laim_forum_proxy_response(
        {"status_code": 200, "is_binary": False, "body": {"success": True, "hilos": []}}
    )
    assert result == {"success": True, "hilos": []}


def test_forum_proxy_response_binary_image() -> None:
    """Respuesta binaria se convierte en Response con media type."""
    response = _laim_forum_proxy_response(
        {
            "status_code": 200,
            "is_binary": True,
            "content_type": "image/png",
            "body": b"\x89PNG",
        }
    )
    assert response.status_code == 200
    assert response.body == b"\x89PNG"
    assert response.media_type == "image/png"


def test_forum_proxy_response_error_raises_http_exception() -> None:
    """Errores del core se propagan como HTTPException."""
    with pytest.raises(HTTPException) as exc_info:
        _laim_forum_proxy_response(
            {
                "status_code": 401,
                "is_binary": False,
                "body": {"detail": "Sesión requerida"},
            }
        )
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Sesión requerida"


def test_broker_client_forum_request_parses_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """BrokerBackendClient.laim_forum_request detecta imágenes."""
    monkeypatch.setenv("STORAGE_MODE", "mock")

    import httpx
    from broker_backend_client import BrokerBackendClient

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "image/jpeg"}
    mock_response.content = b"fake-image"

    client = BrokerBackendClient("http://broker.test")
    client._client = MagicMock()
    client._client.request.return_value = mock_response

    result = client.laim_forum_request("GET", "/laim/forum/images/1")

    assert result["is_binary"] is True
    assert result["body"] == b"fake-image"

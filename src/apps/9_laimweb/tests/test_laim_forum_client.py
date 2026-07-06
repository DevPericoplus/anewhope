"""Tests del cliente API del foro LAIM Web."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from laim_web.adapters import laim_api_client as client


@pytest.fixture(autouse=True)
def _mock_middleware_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client, "_get_middleware_base_url", lambda: "http://middleware.test:8007")


def test_forum_list_categories_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lista categorías cuando el middleware responde OK."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"success": True, "items": [{"id": "general", "nombre": "General"}]}

    mock_client = MagicMock()
    mock_client.request.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr(client.httpx, "Client", lambda **_: mock_client)

    result = client.laim_forum_list_categories("access", "session")

    assert result["success"] is True
    assert result["items"][0]["id"] == "general"
    mock_client.request.assert_called_once()
    call_kwargs = mock_client.request.call_args.kwargs
    assert call_kwargs["headers"]["X-Client-App"] == "laimweb"
    assert call_kwargs["headers"]["Authorization"] == "Bearer access"


def test_forum_create_thread_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Crea hilo con payload JSON correcto."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"success": True, "thread_id": 42}

    mock_client = MagicMock()
    mock_client.request.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr(client.httpx, "Client", lambda **_: mock_client)

    payload = {
        "subcategory_id": "anuncios",
        "titulo": "Hola",
        "cuerpo_md": "Contenido",
        "image_ids": [],
    }
    result = client.laim_forum_create_thread(payload, "tok", "sess")

    assert result["thread_id"] == 42
    assert mock_client.request.call_args.kwargs["json"] == payload


def test_forum_get_image_data_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Convierte imagen binaria a data URL."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.content = b"\x89PNG"
    mock_response.headers = {"content-type": "image/png"}

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr(client.httpx, "Client", lambda **_: mock_client)

    data_url = client.laim_forum_get_image_data_url(7, "tok", "sess")

    assert data_url.startswith("data:image/png;base64,")

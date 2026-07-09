"""Tests del cliente API del foro LAIM Web."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from laim_web.adapters import laim_api_client as client


@pytest.fixture(autouse=True)
def _mock_service_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client, "_get_middleware_base_url", lambda: "http://middleware.test:8007")
    monkeypatch.setattr(client, "_get_forum_base_url", lambda: "http://forum.test:8766")


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
    """Crea hilo con payload REST correcto en el cuerpo de la petición."""
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
    assert mock_client.get.call_args.args[0] == "http://forum.test:8766/laim/forum/images/7"


def test_forum_admin_list_bans_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lista baneos activos contra el daemon del foro."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"success": True, "items": [{"id": 1}]}

    mock_client = MagicMock()
    mock_client.request.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr(client.httpx, "Client", lambda **_: mock_client)

    result = client.laim_forum_admin_list_bans("tok", "sess")

    assert result["items"][0]["id"] == 1
    assert mock_client.request.call_args.kwargs["url"].endswith("/laim/forum/admin/bans")


def test_forum_admin_reload_config_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Recarga configuración del servicio de foro."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.content = b""
    mock_response.json.side_effect = ValueError()

    mock_client = MagicMock()
    mock_client.request.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr(client.httpx, "Client", lambda **_: mock_client)

    result = client.laim_forum_admin_reload_config("tok", "sess")

    assert result["success"] is True
    assert mock_client.request.call_args.kwargs["url"].endswith("/laim/forum/admin/reload-config")


def test_forum_get_poll_interval_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lee intervalo de polling desde env.yaml."""
    monkeypatch.setattr(
        client._env_settings,
        "get_env_value",
        lambda key, default=None: "5" if key == "laim_forum_poll_interval_seconds" else default,
    )
    assert client.laim_forum_get_poll_interval_seconds() == 5


def test_forum_get_profile_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Consulta perfil de foro."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "profile": {"forum_display_name": "Usuario"},
    }

    mock_client = MagicMock()
    mock_client.request.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr(client.httpx, "Client", lambda **_: mock_client)

    result = client.laim_forum_get_profile("tok", "sess")

    assert result["profile"]["forum_display_name"] == "Usuario"
    assert "/laim/forum/profile" in mock_client.request.call_args.kwargs["url"]


def test_forum_create_ban_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Crea baneo con payload correcto."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"success": True, "ban_id": 9}

    mock_client = MagicMock()
    mock_client.request.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr(client.httpx, "Client", lambda **_: mock_client)

    payload = {
        "user_id": 42,
        "subcategory_id": "general",
        "motivo": "Spam",
    }
    result = client.laim_forum_create_ban(payload, "tok", "sess")

    assert result["ban_id"] == 9
    assert mock_client.request.call_args.kwargs["json"] == payload


def test_forum_admin_stats_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Consulta estadísticas admin con ruta correcta."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "stats": {"hilos": 3, "respuestas": 7},
    }

    mock_client = MagicMock()
    mock_client.request.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr(client.httpx, "Client", lambda **_: mock_client)

    result = client.laim_forum_admin_stats("tok", "sess")

    assert result["stats"]["hilos"] == 3
    assert "/laim/forum/admin/stats" in mock_client.request.call_args.kwargs["url"]

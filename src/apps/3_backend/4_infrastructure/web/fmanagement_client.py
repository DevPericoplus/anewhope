"""Cliente HTTP para delegar operaciones al servicio fmanagement."""

from __future__ import annotations

import json
import mimetypes
import uuid
from typing import Any
from urllib import parse, request


class FmanagementClientError(Exception):
    """Error al comunicarse con el servicio fmanagement."""


class FmanagementClient:
    """Cliente HTTP síncrono para fmanagement."""

    def __init__(self, base_url: str, timeout_seconds: int = 10) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def request_json(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
        file_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una petición HTTP y retorna JSON."""

        url = f"{self._base_url}{path}"
        if params:
            url = f"{url}?{parse.urlencode(params)}"

        data = None
        request_headers = dict(headers or {})

        if file_payload is not None:
            body, content_type = _encode_multipart(form or {}, file_payload)
            data = body
            request_headers["Content-Type"] = content_type
        elif form:
            data = parse.urlencode(form).encode("utf-8")
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = request.Request(url, data=data, headers=request_headers, method=method)
        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - errores de red
            raise FmanagementClientError(
                "No se pudo contactar con fmanagement"
            ) from exc

        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise FmanagementClientError(
                "Respuesta de fmanagement no es JSON válido"
            ) from exc


def _encode_multipart(
    fields: dict[str, str], file_payload: dict[str, Any]
) -> tuple[bytes, str]:
    """Codifica un cuerpo multipart/form-data."""

    boundary = uuid.uuid4().hex
    lines: list[bytes] = []

    for key, value in fields.items():
        lines.append(f"--{boundary}".encode("utf-8"))
        lines.append(
            f'Content-Disposition: form-data; name="{key}"'.encode("utf-8")
        )
        lines.append(b"")
        lines.append(str(value).encode("utf-8"))

    filename = file_payload.get("filename") or "upload.bin"
    content = file_payload.get("content") or b""
    content_type = file_payload.get("content_type") or _guess_content_type(filename)

    lines.append(f"--{boundary}".encode("utf-8"))
    lines.append(
        (
            "Content-Disposition: form-data; "
            f'name="file"; filename="{filename}"'
        ).encode("utf-8")
    )
    lines.append(f"Content-Type: {content_type}".encode("utf-8"))
    lines.append(b"")
    lines.append(content)
    lines.append(f"--{boundary}--".encode("utf-8"))

    body = b"\r\n".join(lines) + b"\r\n"
    return body, f"multipart/form-data; boundary={boundary}"


def _guess_content_type(filename: str) -> str:
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or "application/octet-stream"

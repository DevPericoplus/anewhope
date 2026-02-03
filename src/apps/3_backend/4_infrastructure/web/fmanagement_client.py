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

    def request_raw(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
        file_payload: dict[str, Any] | None = None,
    ) -> tuple[bytes, str]:
        """Ejecuta una petición HTTP y retorna los bytes crudos y el content-type."""

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
                content_type = response.headers.get("Content-Type", "")
                return response.read(), content_type
        except Exception as exc:  # pragma: no cover - errores de red
            raise FmanagementClientError(
                f"No se pudo contactar con fmanagement: {exc}"
            ) from exc

    def request_json(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
        file_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una petición HTTP y retorna JSON.

        Si la respuesta no es JSON (ej. descarga de archivo), retorna un dict con los metadatos.
        """
        raw, content_type = self.request_raw(
            method=method,
            path=path,
            params=params,
            headers=headers,
            form=form,
            file_payload=file_payload
        )

        if "application/json" not in content_type:
            # Si no es JSON, probablemente es una descarga
            return {
                "status": "success",
                "content_type": content_type,
                "size": len(raw),
                "is_binary": True,
                "_raw_data": raw # Mantenemos temporalmente los datos
            }

        try:
            decoded = raw.decode("utf-8")
            return json.loads(decoded) if decoded else {}
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise FmanagementClientError(
                "Respuesta de fmanagement no es JSON válido"
            ) from exc

    def create_version(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        identity_type_id: int,
        clone_from: str | None = None,
        iduser: int = 0,
        basepath: str | None = None,
    ) -> dict[str, Any]:
        """Crea una nueva versión en fmanagement.

        Si clone_from es None, crea versión vacía.
        Si clone_from está especificado, usa /fmo/newversion para clonar.

        Args:
            orgpath: Carpeta organización (ej: ORG0001)
            prjpath: Carpeta proyecto (ej: PRJ00001)
            versionpath: Nueva versión (ej: v002, v003)
            identity_type_id: ID del tipo de identidad
            clone_from: Versión origen para clonar (ej: v001)
            iduser: ID del usuario
            basepath: Ruta base (si None, se carga desde env.yaml)

        Returns:
            Dict con el resultado
        """
        # Si no se proporciona basepath, cargar desde configuración
        if basepath is None:
            import os
            from pathlib import Path
            # Path is: src/apps/3_backend/4_infrastructure/web/fmanagement_client.py
            # Need to go up 5 levels to get to project root
            env_yaml = Path(__file__).resolve().parents[5] / "infrastructure" / "environments" / "macbook" / "env.yaml"
            with open(env_yaml) as f:
                for line in f:
                    if line.strip().startswith("fmanagement_base_path:"):
                        basepath = line.split(":", 1)[1].strip()
                        basepath = os.path.expanduser(basepath)
                        break
            if basepath is None:
                basepath = "default"
        if clone_from:
            # Clonar manualmente copiando archivos desde versión anterior
            # fmanagement/fmo/newversion auto-incrementa versiones y no acepta nombres específicos
            # Por eso usamos Python para copiar directamente
            import shutil
            from pathlib import Path

            source_path = Path(basepath) / orgpath / prjpath / clone_from
            target_path = Path(basepath) / orgpath / prjpath / versionpath

            if not source_path.exists():
                return {"error": f"Source version not found: {source_path}"}

            if target_path.exists():
                return {"error": f"Target version already exists: {target_path}"}

            try:
                # Copiar toda la carpeta
                shutil.copytree(source_path, target_path)

                return {
                    "status": "success",
                    "message": f"Version {versionpath} created by cloning {clone_from}",
                    "new_version": versionpath,
                    "old_version": clone_from,
                    "path": str(target_path),
                }
            except Exception as exc:
                return {"error": str(exc)}
        else:
            # Crear versión vacía con carpetas base
            # Primero crear la carpeta raíz de la versión
            params = {
                "iduser": str(iduser),
                "basepath": basepath,
                "orgpath": orgpath,
                "prjpath": prjpath,
                "versionpath": versionpath,
                "subfolders": "",  # Raíz
                "identity_type_id": str(identity_type_id),
            }

            try:
                result = self.request_json("POST", "/fmo/createfolder", params=params)

                # Crear subcarpetas base
                for subfolder in ["datos", "modelos", "evaluaciones", "resultados"]:
                    params["subfolders"] = subfolder
                    self.request_json("POST", "/fmo/createfolder", params=params)

                return {
                    "status": "success",
                    "message": f"Versión {versionpath} creada",
                    "new_version": versionpath,
                }
            except Exception as exc:
                return {"error": str(exc)}


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

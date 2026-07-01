"""Servicio de mensajes de contacto LAIM (portal web)."""

from __future__ import annotations

import base64
import binascii
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

ALLOWED_USAGE_MODES = frozenset({"local", "share", "connect", "remote", "other"})
ALLOWED_IMAGE_MIME_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
)
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _load_module(relative_path: str, module_name: str) -> Any:
    """Carga módulo desde ruta relativa al repo."""
    module_path = Path(__file__).resolve().parents[3] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_dtos = _load_module(
    "src/2_shared_application/dtos/laim_contact_dtos.py",
    "laim_contact_dtos_svc",
)
_repo_mod = _load_module(
    "src/2_shared_application/adapters/laim_contact_repository.py",
    "laim_contact_repository_svc",
)
_session_repo_mod = _load_module(
    "src/2_shared_application/adapters/laim_mariadb_session_repository.py",
    "laim_session_repo_contact",
)
_storage = _load_module(
    "src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py",
    "laim_storage_contact",
)

LaimContactMessageCreateDto = _dtos.LaimContactMessageCreateDto
LaimContactRepository = _repo_mod.LaimContactRepository
LaimContactImageRecord = _repo_mod.LaimContactImageRecord
create_laim_session_engine = _session_repo_mod.create_laim_session_engine
load_laim_mariadb_settings = _storage.load_laim_mariadb_settings


class LaimContactService:
    """Orquesta validación y persistencia de mensajes de contacto."""

    def __init__(self, repository: LaimContactRepository | None = None) -> None:
        resolved_repository = repository
        if resolved_repository is None:
            settings = load_laim_mariadb_settings()
            engine = create_laim_session_engine(settings)
            resolved_repository = LaimContactRepository(engine)
        self._repository = resolved_repository

    @staticmethod
    def _normalize_positive_id(value: Any) -> int | None:
        """Convierte un ID opcional; valores no positivos se tratan como ausentes."""
        if value is None:
            return None
        parsed = int(value)
        return parsed if parsed > 0 else None

    def _validate_contact_input(
        self, payload: dict[str, Any]
    ) -> tuple[LaimContactMessageCreateDto | None, str | None, str | None]:
        """Valida el payload de contacto.

        Returns:
            Tupla (dto, usage_mode, error). Si hay error, dto y usage_mode son None.
        """
        try:
            dto = LaimContactMessageCreateDto.model_validate(payload)
        except Exception as exc:
            return None, None, f"Datos inválidos: {exc}"

        reply_email = str(dto.reply_email)
        if "@" not in reply_email or "." not in reply_email:
            return None, None, "El e-mail de respuesta no es válido."

        usage_mode = dto.usage_mode.strip().lower()
        if usage_mode not in ALLOWED_USAGE_MODES:
            return (
                None,
                None,
                "Modo de uso no válido. Use: local, share, connect o remote.",
            )

        return dto, usage_mode, None

    @staticmethod
    def _extract_user_context_fields(
        user_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Normaliza campos de usuario opcionales del contexto de sesión."""
        ctx = user_context or {}
        user_name = str(ctx.get("user_name") or "").strip() or None
        return {
            "user_id": LaimContactService._normalize_positive_id(ctx.get("user_id")),
            "organization_id": LaimContactService._normalize_positive_id(
                ctx.get("organization_id")
            ),
            "user_name": user_name,
        }

    def create_contact_message(
        self,
        payload: dict[str, Any],
        user_context: dict[str, Any] | None = None,
        ip_address: str = "",
        user_agent: str = "",
    ) -> dict[str, Any]:
        """Crea un mensaje de contacto con captura opcional."""
        dto, usage_mode, validation_error = self._validate_contact_input(payload)
        if validation_error or dto is None or usage_mode is None:
            return {
                "success": False,
                "error": validation_error or "Datos inválidos.",
            }

        image_record: LaimContactImageRecord | None = None
        if dto.screenshot is not None:
            image_record, image_error = self._parse_screenshot(
                dto.screenshot.model_dump()
            )
            if image_error:
                return {"success": False, "error": image_error}

        user_fields = self._extract_user_context_fields(user_context)

        try:
            message_id, image_id = self._repository.create_message_with_image(
                usage_mode=usage_mode,
                affected_user_info=dto.affected_user_info.strip(),
                message_body=dto.message_body.strip(),
                reply_email=str(dto.reply_email).strip().lower(),
                user_id=user_fields["user_id"],
                user_name=user_fields["user_name"],
                organization_id=user_fields["organization_id"],
                ip_address=ip_address,
                user_agent=user_agent,
                image=image_record,
            )
        except Exception as exc:
            _logger.exception("Error persistiendo mensaje de contacto: %s", exc)
            return {
                "success": False,
                "error": "No se pudo registrar el mensaje. Inténtelo más tarde.",
            }

        return {
            "success": True,
            "message_id": message_id,
            "image_id": image_id,
        }

    def _parse_screenshot(
        self, screenshot: dict[str, Any]
    ) -> tuple[LaimContactImageRecord | None, str | None]:
        """Decodifica y valida imagen en base64."""
        mime_type = str(screenshot.get("mime_type", "")).strip().lower()
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            return None, "Formato de imagen no permitido. Use PNG, JPG, WEBP o GIF."

        file_name = str(screenshot.get("file_name", "screenshot.png")).strip()
        if not file_name:
            file_name = "screenshot.png"

        raw_b64 = str(screenshot.get("data_base64", "")).strip()
        if "," in raw_b64 and raw_b64.startswith("data:"):
            raw_b64 = raw_b64.split(",", 1)[1]

        try:
            image_bytes = base64.b64decode(raw_b64, validate=True)
        except binascii.Error:
            return None, "La captura de pantalla no es válida."

        if len(image_bytes) > MAX_IMAGE_BYTES:
            return None, "La imagen supera el tamaño máximo permitido (5 MB)."

        if len(image_bytes) == 0:
            return None, "La captura de pantalla está vacía."

        return (
            LaimContactImageRecord(
                file_name=file_name[:255],
                mime_type=mime_type,
                file_size=len(image_bytes),
                image_data=image_bytes,
            ),
            None,
        )

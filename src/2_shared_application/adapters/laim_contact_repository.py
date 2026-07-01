"""Repositorio MariaDB para mensajes de contacto LAIM."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class LaimContactImageRecord:
    """Datos de imagen adjunta."""

    file_name: str
    mime_type: str
    file_size: int
    image_data: bytes


class LaimContactRepository:
    """Persistencia en laim_contact_messages y laim_contact_messages_images."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._logger = logging.getLogger("LaimContactRepository")

    def create_message_with_image(
        self,
        usage_mode: str,
        affected_user_info: str,
        message_body: str,
        reply_email: str,
        user_id: int | None,
        user_name: str | None,
        organization_id: int | None,
        ip_address: str,
        user_agent: str,
        image: LaimContactImageRecord | None = None,
    ) -> tuple[int, int | None]:
        """Inserta mensaje y opcionalmente imagen en una transacción."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_contact_messages (
                        usage_mode,
                        affected_user_info,
                        message_body,
                        reply_email,
                        user_id,
                        user_name,
                        organization_id,
                        ip_address,
                        user_agent
                    ) VALUES (
                        :usage_mode,
                        :affected_user_info,
                        :message_body,
                        :reply_email,
                        :user_id,
                        :user_name,
                        :organization_id,
                        :ip_address,
                        :user_agent
                    )
                    """
                ),
                {
                    "usage_mode": usage_mode,
                    "affected_user_info": affected_user_info or None,
                    "message_body": message_body,
                    "reply_email": reply_email,
                    "user_id": user_id,
                    "user_name": user_name,
                    "organization_id": organization_id,
                    "ip_address": ip_address or None,
                    "user_agent": user_agent or None,
                },
            )
            message_id = int(result.lastrowid)
            image_id: int | None = None

            if image is not None:
                img_result = conn.execute(
                    text(
                        """
                        INSERT INTO laim_contact_messages_images (
                            message_id,
                            file_name,
                            mime_type,
                            file_size,
                            image_data
                        ) VALUES (
                            :message_id,
                            :file_name,
                            :mime_type,
                            :file_size,
                            :image_data
                        )
                        """
                    ),
                    {
                        "message_id": message_id,
                        "file_name": image.file_name,
                        "mime_type": image.mime_type,
                        "file_size": image.file_size,
                        "image_data": image.image_data,
                    },
                )
                image_id = int(img_result.lastrowid)

            self._logger.info(
                "Mensaje de contacto creado id=%s image_id=%s email=%s",
                message_id,
                image_id,
                reply_email,
            )
            return message_id, image_id

    def get_message_by_id(self, message_id: int) -> dict[str, Any] | None:
        """Obtiene un mensaje por ID (consulta administrativa)."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, usage_mode, affected_user_info, message_body,
                           reply_email, user_id, user_name, organization_id,
                           status, created_at
                    FROM laim_contact_messages
                    WHERE id = :message_id
                    LIMIT 1
                    """
                ),
                {"message_id": message_id},
            ).mappings().fetchone()
        return dict(row) if row else None

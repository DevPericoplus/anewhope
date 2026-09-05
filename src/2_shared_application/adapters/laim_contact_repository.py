"""Repositorio MariaDB para casos de contacto LAIM."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

ESTADO_CASO_ABIERTO_ID = 1

CASOS_CONTACTO_TABLE = "casos_contacto"
CASOS_CONTACTO_IMAGENES_TABLE = "casos_contacto_imagenes"


@dataclass(frozen=True)
class LaimContactImageRecord:
    """Datos de imagen adjunta."""

    file_name: str
    mime_type: str
    file_size: int
    image_data: bytes


class LaimContactRepository:
    """Persistencia en casos_contacto y casos_contacto_imagenes."""

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
        id_estado: int = ESTADO_CASO_ABIERTO_ID,
    ) -> tuple[int, int | None]:
        """Inserta un caso (id = número de caso) y opcionalmente una imagen."""
        estado_id = id_estado if id_estado > 0 else ESTADO_CASO_ABIERTO_ID
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    INSERT INTO {CASOS_CONTACTO_TABLE} (
                        id_estado,
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
                        :id_estado,
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
                    "id_estado": estado_id,
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
            case_id = int(result.lastrowid)
            image_id: int | None = None

            if image is not None:
                img_result = conn.execute(
                    text(
                        f"""
                        INSERT INTO {CASOS_CONTACTO_IMAGENES_TABLE} (
                            id_caso,
                            file_name,
                            mime_type,
                            file_size,
                            image_data
                        ) VALUES (
                            :id_caso,
                            :file_name,
                            :mime_type,
                            :file_size,
                            :image_data
                        )
                        """
                    ),
                    {
                        "id_caso": case_id,
                        "file_name": image.file_name,
                        "mime_type": image.mime_type,
                        "file_size": image.file_size,
                        "image_data": image.image_data,
                    },
                )
                image_id = int(img_result.lastrowid)

            self._logger.info(
                "Caso de contacto creado numero_caso=%s id_estado=%s image_id=%s email=%s",
                case_id,
                estado_id,
                image_id,
                reply_email,
            )
            return case_id, image_id

    def get_message_by_id(self, message_id: int) -> dict[str, Any] | None:
        """Obtiene un caso por número (id)."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT c.id, c.id_estado, e.nombre AS estado_nombre,
                           c.usage_mode, c.affected_user_info, c.message_body,
                           c.reply_email, c.user_id, c.user_name, c.organization_id,
                           c.created_at
                    FROM {CASOS_CONTACTO_TABLE} c
                    INNER JOIN estados_casos_contacto e ON e.id = c.id_estado
                    WHERE c.id = :message_id
                    LIMIT 1
                    """
                ),
                {"message_id": message_id},
            ).mappings().fetchone()
        return dict(row) if row else None

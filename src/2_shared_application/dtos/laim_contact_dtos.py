"""DTOs para mensajes de contacto LAIM."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LaimContactScreenshotDto(BaseModel):
    """Captura de pantalla adjunta (base64)."""

    model_config = ConfigDict(extra="ignore")

    file_name: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=3, max_length=100)
    data_base64: str = Field(..., min_length=1)


class LaimContactMessageCreateDto(BaseModel):
    """Payload para crear un mensaje de contacto."""

    model_config = ConfigDict(extra="ignore")

    usage_mode: str = Field(..., min_length=1, max_length=50)
    affected_user_info: str = Field(default="", max_length=500)
    message_body: str = Field(..., min_length=10, max_length=10000)
    reply_email: str = Field(..., min_length=5, max_length=255)
    screenshot: LaimContactScreenshotDto | None = None


class LaimContactMessageResponseDto(BaseModel):
    """Respuesta tras crear un caso de contacto."""

    success: bool = True
    message_id: int = 0
    numero_caso: int = 0
    id_estado: int = 1
    image_id: int | None = None
    error: str = ""

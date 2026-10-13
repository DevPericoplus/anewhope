"""DTOs de tickets de soporte LAIM."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LaimTicketCreateDto(BaseModel):
    """Payload de alta de ticket (el servidor rellena user/edition)."""

    model_config = ConfigDict(extra="ignore")

    subject: str = Field(..., min_length=5, max_length=200)
    body: str = Field(..., min_length=10, max_length=10000)


class LaimTicketReplyDto(BaseModel):
    """Mensaje público en el hilo del ticket."""

    model_config = ConfigDict(extra="ignore")

    body: str = Field(..., min_length=1, max_length=10000)

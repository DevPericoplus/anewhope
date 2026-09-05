"""Contrato de persistencia para mensajes de contacto LAIM."""

from __future__ import annotations

from typing import Any, Protocol


class LaimContactRepository(Protocol):
    """Contrato para registrar mensajes del formulario de contacto LAIM."""

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
        image: Any | None = None,
        id_estado: int = 1,
    ) -> tuple[int, int | None]:
        """Inserta un caso de contacto (id = número de caso) e imagen opcional."""
        ...

    def get_message_by_id(self, message_id: int) -> dict[str, Any] | None:
        """Obtiene un caso por número (id)."""
        ...

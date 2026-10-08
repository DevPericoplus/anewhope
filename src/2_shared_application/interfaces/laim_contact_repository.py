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

    def list_messages(
        self,
        estado_clave: str | None = None,
        query: str | None = None,
        usage_mode: str | None = None,
        has_image: bool | None = None,
        has_user: bool | None = None,
        cursor_created_at: str | None = None,
        cursor_id: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Lista casos sin BLOB de captura, con paginación por cursor."""
        ...

    def get_with_image(self, message_id: int) -> dict[str, Any] | None:
        """Detalle de un caso incluyendo la captura si existe."""
        ...

    def update_estado(
        self, message_id: int, id_estado: int, actor: str
    ) -> dict[str, Any] | None:
        """Cambia el estado y registra auditoría. None si el caso no existe."""
        ...

    def replace_keywords(
        self, message_id: int, keywords: list[str], fuente: str = "ia"
    ) -> None:
        """Sustituye las etiquetas IA/manual de un caso."""
        ...

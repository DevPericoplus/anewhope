"""Formato de presentación compartido por los paneles de LAIM Web.

Un único sitio para las etiquetas de edición y las fechas, para que el mismo
dato no se vea de dos maneras (QA: «community edition» en el alta del ticket
y «community_edition» en el detalle; fechas ISO crudas en tickets y foro).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

EDITION_LABELS: dict[str, str] = {
    "community_edition": "Community Edition",
    "advance": "Advance",
}
DEFAULT_EDITION = "community_edition"
DISPLAY_DATETIME_FORMAT = "%d/%m/%Y %H:%M"


def edition_label(edition: Any) -> str:
    """Etiqueta legible de una edición (``community_edition`` → «Community Edition»)."""
    key = str(edition or "").strip() or DEFAULT_EDITION
    label = EDITION_LABELS.get(key.lower())
    if label is not None:
        return label
    return key.replace("_", " ").title()


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def format_display_datetime(value: Any) -> str:
    """Fecha para pantalla: ``dd/mm/aaaa HH:MM``.

    - Con zona (``Z`` u offset) se pasa a la hora local del servidor de LAIM
      Web (la de su TZ).
    - Sin zona (DATETIME de MariaDB) se muestra tal cual: ya es la hora del
      reloj de la base de datos, la misma que usa ``NOW()``.
    - Vacío o ``None`` → ``""``; un texto que no es fecha se devuelve sin
      tocar, para no ocultar el dato.
    """
    if value is None:
        return ""
    parsed = _parse_datetime(value)
    if parsed is None:
        return str(value).strip()
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone()
    return parsed.strftime(DISPLAY_DATETIME_FORMAT)

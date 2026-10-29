"""Los textos del foro conservan tildes, eñes y comillas «» (sin «?» de una mala codificación)."""

from __future__ import annotations

import re
from pathlib import Path

_SERVICE = Path(__file__).resolve().parents[1] / "laim_forum_service.py"

# Una letra pegada a «?» y seguida de otra letra: «subcategor?a», «sesi?n».
_BROKEN = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]\?[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]")


def test_forum_service_has_no_broken_accents() -> None:
    text = _SERVICE.read_text(encoding="utf-8")
    broken = [
        f"{n}: {line.strip()}"
        for n, line in enumerate(text.splitlines(), 1)
        if _BROKEN.search(line)
    ]
    assert broken == [], "\n".join(broken)


def test_user_facing_messages_keep_their_spelling() -> None:
    text = _SERVICE.read_text(encoding="utf-8")
    assert "Está baneado en esta subcategoría." in text
    assert "respondió en «{thread['titulo']}»" in text

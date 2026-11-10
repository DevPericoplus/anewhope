"""Reglas de contenido y moderación automática del foro LAIM.

Portado desde el dominio de referencia (Radikal) para reutilizar la misma
semántica de acciones, escalado de infracciones y detección de palabras.

Una regla puede llevar una excepción de contexto: la palabra sigue
prohibida, salvo cuando el mensaje tiene unas frases y no tiene otras.
`patron` es la expresión que decide el corte; si está vacía se usa la
palabra tal cual. El moderador puede editar las dos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

_MADRID = ZoneInfo("Europe/Madrid")
_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

RULE_ACTIONS = (
    "Agradecimientos",
    "Amonestaciones",
    "Sugerencias",
    "Ban",
    "Kick",
)

POSITIVE_ACTIONS = {"Agradecimientos", "Sugerencias"}
EscalationAction = Literal["none", "amonestacion", "ban", "kick"]

_URL_PATTERN = re.compile(r"https?://[^\s)\]>]+", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class WordRuleMatch:
    """Resultado de evaluar un mensaje contra una regla de palabra."""

    rule: dict
    block_message: bool
    escalation: EscalationAction
    notify_user: str
    announce_channel: str


def _phrases(value: object) -> list[str]:
    """Lista de frases en minúsculas, separadas por coma o por salto de línea."""
    if isinstance(value, (list, tuple)):
        raw = [str(item) for item in value]
    else:
        raw = str(value or "").replace("\n", ",").split(",")
    return [item.strip().lower() for item in raw if item.strip()]


def exception_allows(text: str, rule: dict) -> bool:
    """La palabra está en un contexto permitido.

    Hace falta al menos una condición. Si hay frases en `excepcion_tiene`,
    todas tienen que aparecer. Si hay frases en `excepcion_no_tiene`,
    ninguna puede aparecer. Sin condiciones no hay excepción.
    """
    tiene = _phrases(rule.get("excepcion_tiene"))
    no_tiene = _phrases(rule.get("excepcion_no_tiene"))
    if not tiene and not no_tiene:
        return False
    lower = (text or "").lower()
    if tiene and not all(phrase in lower for phrase in tiene):
        return False
    if any(phrase in lower for phrase in no_tiene):
        return False
    return True


def suggest_patron(palabra: str) -> str:
    """Expresión de partida, editable, que busca la palabra entera."""
    word = re.escape(str(palabra or "").strip())
    if not word:
        return ""
    return rf"(?i)\b{word}\b"


def exception_summary(rule: dict) -> str:
    """Frase corta para el backoffice."""
    tiene = _phrases(rule.get("excepcion_tiene"))
    no_tiene = _phrases(rule.get("excepcion_no_tiene"))
    parts: list[str] = []
    if tiene:
        quoted = ", ".join(f"«{item}»" for item in tiene)
        parts.append(f"si el mensaje tiene {quoted}")
    if no_tiene:
        quoted = ", ".join(f"«{item}»" for item in no_tiene)
        parts.append(f"si el mensaje no tiene {quoted}")
    if not parts:
        return ""
    return "Permitida " + " y ".join(parts) + "."


def rule_hit(text: str, rule: dict) -> tuple[int, int] | None:
    """Inicio y fin del corte, o None si la regla no aplica.

    Con `patron`, manda la expresión (una expresión inválida no corta).
    Sin ella, manda la palabra. Si el contexto cumple la excepción, no hay corte.
    """
    if not bool(rule.get("activo", True)):
        return None
    source = text or ""
    patron = str(rule.get("patron") or "").strip()
    span: tuple[int, int] | None = None
    if patron:
        try:
            found = re.search(patron, source, re.IGNORECASE)
        except re.error:
            return None
        if found:
            span = found.span()
    else:
        pattern = str(rule.get("palabra") or "").strip()
        if not pattern:
            return None
        lower = source.lower()
        needle = pattern.lower()
        idx = lower.find(needle)
        if idx >= 0:
            span = (idx, idx + len(needle))
        else:
            try:
                found = re.search(rf"\b{re.escape(needle)}\b", lower)
            except re.error:
                return None
            if found:
                span = found.span()
    if span is None:
        return None
    if exception_allows(source, rule):
        return None
    return span


def find_matching_rule(text: str, rules: list[dict]) -> dict | None:
    """Devuelve la primera regla activa que coincide y no está exceptuada."""
    for rule in rules:
        if rule_hit(text, rule) is not None:
            return rule
    return None


def excerpt_around(text: str, start: int, end: int, radius: int = 60) -> str:
    """Fragmento del mensaje alrededor del corte, para el backoffice."""
    source = text or ""
    left = max(0, start - radius)
    right = min(len(source), end + radius)
    chunk = " ".join(source[left:right].split())
    if left > 0:
        chunk = "…" + chunk
    if right < len(source):
        chunk = chunk + "…"
    return chunk


def format_return_at(expires_at: datetime | str | None) -> str:
    """Cuándo puede volver a publicar, en hora peninsular."""
    if expires_at is None or expires_at == "":
        return "No hay fecha de vuelta. Un administrador tiene que levantar el baneo."
    moment = expires_at
    if isinstance(moment, str):
        try:
            moment = datetime.fromisoformat(moment.replace("Z", "+00:00"))
        except ValueError:
            return f"Puede volver a publicar a partir de {expires_at}."
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    local = moment.astimezone(_MADRID)
    month = _MESES[local.month - 1]
    clock = local.strftime("%H:%M")
    return (
        f"Puede volver a publicar el {local.day} de {month} de {local.year} "
        f"a las {clock} (hora peninsular)."
    )


def ban_notice(
    *,
    motivo: str,
    expires_at: datetime | str | None,
    subcategory: str = "",
) -> dict[str, str]:
    """Texto del modal que ve quien ha sido baneado."""
    reason = (motivo or "").strip() or "La moderación automática ha bloqueado el mensaje."
    return {
        "titulo": "No puede publicar en el foro",
        "motivo": reason,
        "hasta": format_return_at(expires_at),
        "subcategoria": subcategory,
    }


def false_positive_apology(*, user_name: str, palabra: str, fragmento: str) -> dict[str, str]:
    """Disculpa cuando un administrador levanta un baneo que era un falso positivo."""
    name = (user_name or "").strip()
    greeting = f"Hola {name}," if name else "Hola,"
    word = (palabra or "").strip() or "una expresión"
    quote = (fragmento or "").strip()
    context = f"\n\nEl fragmento que vimos fue: «{quote}».\n" if quote else "\n"
    body = (
        f"{greeting}\n\n"
        f"Sentimos el baneo. La expresión «{word}» de su mensaje se interpretó "
        f"como no permitida y, revisado el contexto, era un falso positivo. "
        f"Ya puede volver a escribir en el foro."
        f"{context}\n"
        "Gracias por la paciencia y por ayudarnos a ajustar mejor el foro de LAIM.\n\n"
        "Departamento de soporte de LAIM"
    )
    return {
        "asunto": "Hemos levantado un baneo del foro de LAIM",
        "cuerpo": body,
    }


def evaluate_rule_match(rule: dict, *, strike_level: int) -> WordRuleMatch:
    """Determina cómo actuar según la regla y el nivel de infracción del día."""
    accion = str(rule.get("accion", "Amonestaciones"))
    mensaje = str(rule.get("mensaje", "")).strip() or (
        f"Regla activada: {rule.get('palabra', '')}"
    )

    if accion in POSITIVE_ACTIONS:
        return WordRuleMatch(
            rule=rule,
            block_message=False,
            escalation="none",
            notify_user="",
            announce_channel=mensaje,
        )

    if strike_level <= 1:
        return WordRuleMatch(
            rule=rule,
            block_message=True,
            escalation="amonestacion",
            notify_user=mensaje,
            announce_channel=(
                f"@Supervisor: amonestación por '{rule.get('palabra', '')}'."
            ),
        )
    if strike_level == 2:
        return WordRuleMatch(
            rule=rule,
            block_message=True,
            escalation="ban",
            notify_user=mensaje,
            announce_channel=(
                f"@Supervisor: ban automático por reincidencia con "
                f"'{rule.get('palabra', '')}'."
            ),
        )
    return WordRuleMatch(
        rule=rule,
        block_message=True,
        escalation="kick",
        notify_user=mensaje,
        announce_channel=(
            f"@Supervisor: kick automático por reincidencia con "
            f"'{rule.get('palabra', '')}'."
        ),
    )


def extract_urls(text: str) -> list[str]:
    """Extrae URLs http(s) del texto."""
    return _URL_PATTERN.findall(text or "")


def find_unauthorized_urls(text: str, allowed_domains: list[str]) -> list[str]:
    """Devuelve URLs cuyo dominio no está en la lista permitida."""
    allowed = {domain.strip().lower() for domain in allowed_domains if domain.strip()}
    if not allowed:
        return []
    unauthorized: list[str] = []
    for raw_url in extract_urls(text):
        url = raw_url.rstrip(".,;")
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host:
            continue
        if not any(host == domain or host.endswith(f".{domain}") for domain in allowed):
            unauthorized.append(url)
    return unauthorized

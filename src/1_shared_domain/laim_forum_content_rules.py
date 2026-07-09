"""Reglas de contenido y moderación automática del foro LAIM.

Portado desde el dominio de referencia (Radikal) para reutilizar la misma
semántica de acciones, escalado de infracciones y detección de palabras.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

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


def find_matching_rule(text: str, rules: list[dict]) -> dict | None:
    """Devuelve la primera regla activa que coincide con el texto."""
    lower = text.lower()
    for rule in rules:
        if not bool(rule.get("activo", True)):
            continue
        pattern = str(rule.get("palabra", "")).lower().strip()
        if not pattern:
            continue
        if pattern in lower:
            return rule
        try:
            if re.search(rf"\b{re.escape(pattern)}\b", lower):
                return rule
        except re.error:
            continue
    return None


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

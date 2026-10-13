"""Máquina de estados de tickets de soporte LAIM (v1)."""

from __future__ import annotations

ESTADO_ABIERTO = "abierto"
ESTADO_EN_CURSO = "en_curso"
ESTADO_ESPERANDO_USUARIO = "esperando_usuario"
ESTADO_CERRADO = "cerrado"

DEFAULT_EDITION = "community_edition"
ALLOWED_EDITIONS = frozenset({"community_edition", "advance"})

ESTADO_CLAVE_TO_ID = {
    ESTADO_ABIERTO: 1,
    ESTADO_EN_CURSO: 2,
    ESTADO_ESPERANDO_USUARIO: 3,
    ESTADO_CERRADO: 4,
}

ESTADO_ID_TO_CLAVE = {value: key for key, value in ESTADO_CLAVE_TO_ID.items()}

OPERATOR_TRANSITIONS: dict[str, frozenset[str]] = {
    ESTADO_ABIERTO: frozenset({ESTADO_EN_CURSO, ESTADO_ESPERANDO_USUARIO, ESTADO_CERRADO}),
    ESTADO_EN_CURSO: frozenset({ESTADO_ESPERANDO_USUARIO, ESTADO_CERRADO}),
    ESTADO_ESPERANDO_USUARIO: frozenset({ESTADO_EN_CURSO, ESTADO_CERRADO}),
    ESTADO_CERRADO: frozenset(),
}


class TicketStateError(ValueError):
    """Transición de ticket no permitida."""


def normalize_estado(clave: str) -> str:
    """Normaliza y valida una clave de estado."""
    normalized = (clave or "").strip().lower()
    if normalized not in ESTADO_CLAVE_TO_ID:
        raise TicketStateError(f"estado desconocido: {clave!r}")
    return normalized


def can_user_reply(estado: str) -> bool:
    """El usuario responde mientras el ticket no esté cerrado."""
    return normalize_estado(estado) != ESTADO_CERRADO


def next_state_after_user_reply(estado: str) -> str:
    """Respuesta del usuario: esperando_usuario pasa a en_curso."""
    current = normalize_estado(estado)
    if current == ESTADO_CERRADO:
        raise TicketStateError("El ticket está cerrado")
    if current == ESTADO_ESPERANDO_USUARIO:
        return ESTADO_EN_CURSO
    return current


def next_state_after_operator_reply(estado: str) -> str:
    """Respuesta del operador: un ticket abierto pasa a en_curso."""
    current = normalize_estado(estado)
    if current == ESTADO_CERRADO:
        raise TicketStateError("El ticket está cerrado")
    if current == ESTADO_ABIERTO:
        return ESTADO_EN_CURSO
    return current


def apply_operator_transition(current: str, target: str) -> str:
    """Cambio de estado explícito del operador (no incluye Reabrir)."""
    from_state = normalize_estado(current)
    to_state = normalize_estado(target)
    if to_state not in OPERATOR_TRANSITIONS[from_state]:
        raise TicketStateError(
            f"transición no permitida: {from_state} → {to_state}"
        )
    return to_state


def reopen(current: str) -> str:
    """Solo el operador reabre un ticket cerrado."""
    if normalize_estado(current) != ESTADO_CERRADO:
        raise TicketStateError("Solo se puede reabrir un ticket cerrado")
    return ESTADO_EN_CURSO

"""TDD: máquina de estados de tickets de soporte LAIM."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_STATES_PATH = (
    Path(__file__).resolve().parents[1] / "domain" / "laim_ticket_states.py"
)


def _load_states():
    name = "laim_ticket_states_test"
    spec = importlib.util.spec_from_file_location(name, _STATES_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # noqa: SLF001
    return module


def test_catalog_ids_and_claves() -> None:
    m = _load_states()
    assert m.ESTADO_CLAVE_TO_ID == {
        "abierto": 1,
        "en_curso": 2,
        "esperando_usuario": 3,
        "cerrado": 4,
    }
    assert m.ESTADO_ID_TO_CLAVE[1] == "abierto"
    assert m.DEFAULT_EDITION == "community_edition"


def test_user_cannot_reply_when_closed() -> None:
    m = _load_states()
    assert m.can_user_reply("abierto") is True
    assert m.can_user_reply("en_curso") is True
    assert m.can_user_reply("esperando_usuario") is True
    assert m.can_user_reply("cerrado") is False
    with pytest.raises(m.TicketStateError, match="cerrado"):
        m.next_state_after_user_reply("cerrado")


def test_user_reply_moves_waiting_to_in_progress() -> None:
    m = _load_states()
    assert m.next_state_after_user_reply("esperando_usuario") == "en_curso"
    assert m.next_state_after_user_reply("abierto") == "abierto"
    assert m.next_state_after_user_reply("en_curso") == "en_curso"


def test_operator_reply_opens_new_ticket() -> None:
    m = _load_states()
    assert m.next_state_after_operator_reply("abierto") == "en_curso"
    assert m.next_state_after_operator_reply("en_curso") == "en_curso"
    assert m.next_state_after_operator_reply("esperando_usuario") == "esperando_usuario"
    with pytest.raises(m.TicketStateError, match="cerrado"):
        m.next_state_after_operator_reply("cerrado")


def test_operator_allowed_transitions() -> None:
    m = _load_states()
    assert m.apply_operator_transition("abierto", "en_curso") == "en_curso"
    assert m.apply_operator_transition("abierto", "cerrado") == "cerrado"
    assert m.apply_operator_transition("en_curso", "esperando_usuario") == "esperando_usuario"
    assert m.apply_operator_transition("en_curso", "cerrado") == "cerrado"
    assert m.apply_operator_transition("esperando_usuario", "en_curso") == "en_curso"
    assert m.apply_operator_transition("esperando_usuario", "cerrado") == "cerrado"
    with pytest.raises(m.TicketStateError):
        m.apply_operator_transition("abierto", "esperando_usuario")
    with pytest.raises(m.TicketStateError):
        m.apply_operator_transition("cerrado", "en_curso")


def test_reopen_only_from_closed() -> None:
    m = _load_states()
    assert m.reopen("cerrado") == "en_curso"
    with pytest.raises(m.TicketStateError, match="cerrado"):
        m.reopen("abierto")
    with pytest.raises(m.TicketStateError, match="cerrado"):
        m.reopen("en_curso")

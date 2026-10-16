"""El deploy no inserta KeySerialSigning: el repo la siembra una vez."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

_REPO = Path(__file__).resolve().parents[1] / "adapters" / "laim_exchange_key.py"


def _load():
    spec = importlib.util.spec_from_file_location("laim_exch_ensure_test", _REPO)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["laim_exch_ensure_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE laim_exchange_keys (
                    key_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    major_version TEXT NOT NULL,
                    key_kind TEXT NOT NULL DEFAULT 'exchange',
                    key_value_cipher TEXT NOT NULL,
                    valid_from TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    valid_until TEXT
                )
                """
            )
        )
    return engine


def test_ensure_serial_signing_key_persists_once() -> None:
    mod = _load()
    repo = mod.LaimExchangeKeyRepository(_engine())
    assert repo.get_serial_signing_key() is None
    first = repo.ensure_serial_signing_key("first-key=")
    second = repo.ensure_serial_signing_key("other-key=")
    assert first.key_id == second.key_id
    assert second.key_value == "first-key="
    assert second.major_version == "2"

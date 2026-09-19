"""Clave de autenticidad compartida entre laim y laimweb (`laim_exchange_keys`,
migración 022) — ver anewhope/AGENTS.md § 37.2.

`KeyExchageLaimApp` (laim/internal/utils/version.go) viaja embebida en cada
binario laim distribuido, así que no puede tratarse como secreta frente a un
atacante con acceso al binario — no aporta confidencialidad. Se usa como
clave HMAC de autenticidad: firma las respuestas de /check_last_version para
que un cliente laim pueda comprobar que vinieron de verdad de laim.app y no
fueron manipuladas en tránsito ni en la caché de laimweb. La confidencialidad
del transporte ya la da HTTPS.

Cifrado en reposo de `key_value_cipher`: pendiente de diseño (ver el propio
comentario de la migración 022) — hasta que exista, el valor se guarda en
claro, protegido solo por permisos de base de datos. Es el estado interino
ya aceptado, no una improvisación de este módulo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True, slots=True)
class ExchangeKey:
    key_id: int
    major_version: str
    key_value: str


class LaimExchangeKeyRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_current_key(self, major_version: str) -> Optional[ExchangeKey]:
        """La clave vigente más reciente para major_version (valid_from <=
        NOW() y valid_until NULL o en el futuro) — soporta varias claves
        vigentes a la vez durante una rotación de versión mayor, ver
        AGENTS.md § 37.2. None si no hay ninguna vigente todavía."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT key_id, major_version, key_value_cipher
                    FROM laim_exchange_keys
                    WHERE major_version = :mv
                      AND valid_from <= CURRENT_TIMESTAMP
                      AND (valid_until IS NULL OR valid_until > CURRENT_TIMESTAMP)
                    ORDER BY valid_from DESC
                    LIMIT 1
                    """
                ),
                {"mv": major_version},
            ).mappings().fetchone()
        if row is None:
            return None
        return ExchangeKey(
            key_id=int(row["key_id"]),
            major_version=str(row["major_version"]),
            key_value=str(row["key_value_cipher"]),
        )

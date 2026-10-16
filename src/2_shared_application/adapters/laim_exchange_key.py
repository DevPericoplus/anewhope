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

    def get_current_key(self, major_version: str, key_kind: str = "exchange") -> Optional[ExchangeKey]:
        """La clave vigente más reciente para major_version (valid_from <=
        NOW() y valid_until NULL o en el futuro) — soporta varias claves
        vigentes a la vez durante una rotación de versión mayor, ver
        AGENTS.md § 37.2. None si no hay ninguna vigente todavía.
        key_kind: exchange = KeyExchageLaimApp; serial_signing = KeySerialSigning.
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT key_id, major_version, key_value_cipher
                    FROM laim_exchange_keys
                    WHERE major_version = :mv
                      AND key_kind = :kind
                      AND valid_from <= CURRENT_TIMESTAMP
                      AND (valid_until IS NULL OR valid_until > CURRENT_TIMESTAMP)
                    ORDER BY valid_from DESC
                    LIMIT 1
                    """
                ),
                {"mv": major_version, "kind": key_kind},
            ).mappings().fetchone()
        if row is None:
            return None
        return ExchangeKey(
            key_id=int(row["key_id"]),
            major_version=str(row["major_version"]),
            key_value=str(row["key_value_cipher"]),
        )

    def get_serial_signing_key(self) -> Optional[ExchangeKey]:
        """KeySerialSigning vigente (scheme 2, no rota por major como el HMAC
        de actualización). None si aún no hay fila: el servicio la siembra
        desde el valor de producto en el primer verify."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT key_id, major_version, key_value_cipher
                    FROM laim_exchange_keys
                    WHERE key_kind = 'serial_signing'
                      AND valid_from <= CURRENT_TIMESTAMP
                      AND (valid_until IS NULL OR valid_until > CURRENT_TIMESTAMP)
                    ORDER BY valid_from DESC
                    LIMIT 1
                    """
                ),
            ).mappings().fetchone()
        if row is None:
            return None
        return ExchangeKey(
            key_id=int(row["key_id"]),
            major_version=str(row["major_version"]),
            key_value=str(row["key_value_cipher"]),
        )

    def ensure_serial_signing_key(self, key_value: str, major_version: str = "2") -> ExchangeKey:
        """Idempotente: crea la fila serial_signing si no existe. El deploy
        no inserta secretos en SQL; backend_core siembra en el primer HMAC."""
        existing = self.get_serial_signing_key()
        if existing is not None:
            return existing
        value = (key_value or "").strip()
        if not value:
            raise ValueError("KeySerialSigning vacío")
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_exchange_keys (major_version, key_kind, key_value_cipher)
                    SELECT :mv, 'serial_signing', :val
                    WHERE NOT EXISTS (
                        SELECT 1 FROM laim_exchange_keys WHERE key_kind = 'serial_signing'
                    )
                    """
                ),
                {"mv": major_version, "val": value},
            )
        got = self.get_serial_signing_key()
        if got is None:
            raise RuntimeError("KeySerialSigning no quedó persistida")
        return got

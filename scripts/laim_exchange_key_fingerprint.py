#!/usr/bin/env python3
"""Huella de KeyExchageLaimApp sin revelar la clave (AGENTS.md § 37.2).

Imprime solo huellas (HMAC-SHA256 de una etiqueta pública fija, 16 hex):
- la de la constante de producto de laimweb (la que se siembra en
  laim_exchange_keys para el major de producto);
- con --laim-repo, la de KeyExchageLaimApp del version.go de ese checkout.
La clave vigente que firma en un entorno se comprueba sin entrar en él:
`key_fingerprint` de una respuesta con actualización de
GET /laim/check_last_version (p. ej. current_version=0.0.1).

Uso: scripts/laim_exchange_key_fingerprint.py [--laim-repo ../laim]
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

_SECURITY = Path(__file__).resolve().parents[1] / "src" / "2_shared_application" / "security"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fingerprints(laim_repo: Path | None) -> list[str]:
    signing = _load("laim_update_signing_fp", _SECURITY / "laim_update_signing.py")
    serial = _load("laim_serial_fp", _SECURITY / "laim_serial.py")
    lines = [
        f"laimweb producto (major {serial.PRODUCT_EXCHANGE_MAJOR}): "
        + signing.exchange_key_fingerprint(serial.product_exchange_key())
    ]
    if laim_repo is not None:
        version_go = laim_repo / "internal" / "utils" / "version.go"
        compiled = serial.key_exchange_from_laim_repo(version_go.read_text(encoding="utf-8"))
        lines.append(f"laim {laim_repo} (version.go): " + signing.exchange_key_fingerprint(compiled))
    return lines


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--laim-repo", type=Path, default=None)
    args = parser.parse_args(argv)
    lines = fingerprints(args.laim_repo)
    print("\n".join(lines))
    values = {line.rsplit(": ", 1)[1] for line in lines}
    return 0 if len(values) == 1 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

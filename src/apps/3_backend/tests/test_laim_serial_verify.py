"""VerifySerial Python = serial.go, contra el código y la clave reales de laim."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

_SERIAL_PATH = (
    Path(__file__).resolve().parents[3]
    / "2_shared_application"
    / "security"
    / "laim_serial.py"
)
_LAIM = Path("/Users/perico/develop/laim")
_SERIAL_GO = _LAIM / "internal" / "utils" / "serial.go"
_VERSION_GO = _LAIM / "internal" / "utils" / "version.go"


def _load():
    spec = importlib.util.spec_from_file_location("laim_serial_verify_test", _SERIAL_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["laim_serial_verify_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_constants_match_serial_go() -> None:
    src = _SERIAL_GO.read_text(encoding="utf-8")
    py = _SERIAL_PATH.read_text(encoding="utf-8")
    assert 'serialScheme = "2"' in src
    assert "serialPayloadBytes" in src
    assert "serialCheckBytes" in src
    assert 'SERIAL_SCHEME = "2"' in py
    assert "SERIAL_PAYLOAD_BYTES = 10" in py
    assert "SERIAL_CHECK_BYTES = 4" in py
    assert "hmac.Equal" in src or "hmac.compare_digest" in py


def test_roundtrip_and_reject_tamper_with_real_keyserialsigning() -> None:
    mod = _load()
    key = mod.key_serial_signing_from_laim_repo(_VERSION_GO.read_text(encoding="utf-8"))
    serial = mod.generate_serial(key)
    assert serial.startswith("2-")
    assert mod.verify_serial(serial, key) is True, serial
    parts = serial.split("-")
    group = parts[1]
    parts[1] = group[:-1] + ("B" if group[-1] != "B" else "C")
    tampered = "-".join(parts)
    assert mod.verify_serial(tampered, key) is False, tampered
    assert mod.verify_serial("2-AAAA-AAAA-AAAA-AAAAAAA-AAAAAAA", key) is False
    assert mod.verify_serial("1234A-5678B-9012C-3456D-7890E", key) is False
    assert "master_key" not in serial.lower()


def test_python_accepts_serial_generated_by_go() -> None:
    """Interop real: GenerateLaimSerial() de Go debe verificar aquí."""
    helper = r"""
package main
import (
    "fmt"
    "laim/internal/utils"
)
func main() { fmt.Print(utils.GenerateLaimSerial()) }
"""
    tmp = _LAIM / "internal" / "utils" / "cmd_serial_interop_main.go"
    # go run on a file in package utils fails; use `go test` print via -exec no.
    # Compile a tiny module-root program that imports the package.
    prog = _LAIM / "serial_interop_tmp.go"
    prog.write_text(
        """package main
import (
	"fmt"
	"laim/internal/utils"
)
func main() { fmt.Print(utils.GenerateLaimSerial()) }
""",
        encoding="utf-8",
    )
    try:
        proc = subprocess.run(
            ["go", "run", prog.name],
            cwd=_LAIM,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    finally:
        prog.unlink(missing_ok=True)
        tmp.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    serial = proc.stdout.strip()
    assert serial.startswith("2-"), serial
    mod = _load()
    key = mod.key_serial_signing_from_laim_repo(_VERSION_GO.read_text(encoding="utf-8"))
    assert mod.verify_serial(serial, key) is True, serial

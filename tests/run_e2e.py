#!/usr/bin/env python3
"""Lanza un script E2E con la raíz del repo en sys.path y el shim de requests."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.helpers import install_requests_shim  # noqa: E402
from tests.import_aliases import register_repo_helpers  # noqa: E402

install_requests_shim()
register_repo_helpers()

if len(sys.argv) < 2:
    raise SystemExit("Uso: run_e2e.py <script.py>")

script = Path(sys.argv[1]).resolve()
if not script.is_file():
    raise SystemExit(f"No existe el script E2E: {script}")

try:
    runpy.run_path(str(script), run_name="__main__")
except SystemExit as exc:
    code = exc.code
    if code in (None, 0):
        raise SystemExit(0) from None
    raise SystemExit(code) from None

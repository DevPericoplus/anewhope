"""Tests de normalización y comparación de OTP de login."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def _load_routermiddleware() -> Any:
    """Carga routermiddleware de forma aislada."""
    module_path = Path(__file__).resolve().parents[1] / "routermiddleware.py"
    spec = importlib.util.spec_from_file_location(
        "routermiddleware_otp_helpers", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar routermiddleware")
    module = importlib.util.module_from_spec(spec)
    sys.modules["routermiddleware_otp_helpers"] = module
    spec.loader.exec_module(module)
    return module


routermiddleware = _load_routermiddleware()


def test_normalize_otp_keeps_leading_zero() -> None:
    """Un OTP con cero inicial se conserva en 4 dígitos."""
    assert routermiddleware._normalize_otp_code("0415") == "0415"
    assert routermiddleware._normalize_otp_code(415) == "0415"
    assert routermiddleware._normalize_otp_code(" 415 ") == "0415"


def test_otp_codes_match_leading_zero_variants() -> None:
    """415 y 0415 se consideran el mismo código."""
    assert routermiddleware._otp_codes_match("0415", "415") is True
    assert routermiddleware._otp_codes_match("0415", "0415") is True
    assert routermiddleware._otp_codes_match("0415", "6969") is False
    assert routermiddleware._otp_codes_match("", "0415") is False

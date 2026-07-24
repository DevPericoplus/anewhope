"""Tema CRT ámbar fósforo — Backoffice."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_SRC_ROOT = Path(__file__).resolve().parents[2]
_CRT_DIR = _SRC_ROOT / "2_shared_application" / "reflex_shared" / "crt"


def _load_crt_module(name: str):
    path = _CRT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"portal_crt_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_crt_theme = _load_crt_module("crt_theme")
_crt_components = _load_crt_module("crt_components")

COLORS: dict[str, str] = _crt_theme.get_portal_colors("amber")
CRT_STYLESHEETS: list[str] = _crt_theme.CRTStylesheets["amber"]
CRT_SHELL_CLASS: str = _crt_theme.CRT_SHELL_CLASS["amber"]
SELECT_STYLE: dict[str, str] = _crt_theme.get_select_style("amber")
MARKDOWN_COMPONENT_MAP: dict[str, Any] = _crt_theme.get_markdown_component_map(
    "amber",
    body_font_size="1em",
    h1_size="7",
    h2_size="5",
    h3_size="4",
)
FONT_FAMILY: str = _crt_theme.FONT_FAMILY

crt_cross_portal_button = _crt_components.crt_cross_portal_button
crt_app_style = _crt_components.crt_app_style

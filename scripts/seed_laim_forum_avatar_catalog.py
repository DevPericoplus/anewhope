#!/usr/bin/env python3
"""Punto de entrada del seed del catálogo de avatares del foro LAIM."""

from __future__ import annotations

from pathlib import Path
import runpy

_SEED = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "2_shared_application"
    / "laim_forum_avatar_catalog_seed.py"
)
runpy.run_path(str(_SEED), run_name="__main__")

"""Contrato del home público: logo enmarcado y arranque de la animación."""

from __future__ import annotations

from pathlib import Path

laimweb_root = Path(__file__).resolve().parents[1]


def test_sidebar_logo_has_traveling_node_frame() -> None:
    logo = (laimweb_root / "laim_web" / "components" / "laim_logo.py").read_text(
        encoding="utf-8"
    )
    css = (laimweb_root / "assets" / "crt" / "crt_base.css").read_text(encoding="utf-8")
    assert "crt-logo-frame" in logo
    assert "crt-logo-node" in logo
    assert "offset-path" in css
    assert "crt-logo-orbit" in css


def test_home_polls_neural_scene_while_spinner_is_active() -> None:
    home = (laimweb_root / "laim_web" / "components" / "bento" / "home.py").read_text(
        encoding="utf-8"
    )
    js = (laimweb_root / "assets" / "crt" / "bento_neural.js").read_text(encoding="utf-8")
    assert "NEURAL_READY_WATCH_SCRIPT" in home
    assert "LAIMBentoNeural.ensure" in home
    assert "bento_neural.js?v=3d6" in home
    assert "ensure: ensure" in js
    assert "homeShowsSpinner()" in js
    assert "setInterval" in js
    assert "if (!worldEl() || !canvasEl())" in js

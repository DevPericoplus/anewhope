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
    assert "NEURAL_SCRIPT_SRC" in home
    assets = (laimweb_root / "laim_web" / "visual_assets.py").read_text(encoding="utf-8")
    assert 'NEURAL_SCRIPT_SRC = "/crt/bento_neural.js?v=4"' in assets
    assert "ensure: ensure" in js
    assert "homeShowsSpinner()" in js
    assert "setInterval" in js
    assert "if (!worldEl() || !canvasEl())" in js


def test_neural_binds_visible_home_not_stale_canvas_id() -> None:
    """Contacto → Inicio: Reflex remonta el DOM; getElementById queda
    en un canvas viejo (tamaño 0) y el spinner no se apaga nunca."""
    home = (laimweb_root / "laim_web" / "components" / "bento" / "home.py").read_text(
        encoding="utf-8"
    )
    js = (laimweb_root / "assets" / "crt" / "bento_neural.js").read_text(encoding="utf-8")
    css = (laimweb_root / "assets" / "crt" / "crt_base.css").read_text(encoding="utf-8")
    assert 'getElementById("crt-neural-canvas")' not in js
    assert ".crt-inicio-home .crt-neural-canvas" in js or 'home.querySelector(".crt-neural-canvas")' in js
    assert "isConnected" in js
    assert "laim-neural-ready" in js
    assert "html.laim-neural-ready" in css
    assert "attributeFilter" in js
    assert "n > 150" not in home
    assert "__LAIMNeuralWatch" in home

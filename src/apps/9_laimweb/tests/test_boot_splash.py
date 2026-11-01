"""La primera pintura de laimweb es la pantalla de preparación, no un negro."""

from __future__ import annotations

from pathlib import Path

APP = Path(__file__).resolve().parents[1]


def test_boot_splash_uses_the_laim_preparing_copy() -> None:
    splash = (APP / "laim_web" / "boot_splash.py").read_text(encoding="utf-8")
    app = (APP / "laim_web" / "laim_web.py").read_text(encoding="utf-8")
    assert "LAIM se está preparando" in splash
    assert "Preparando la interfaz…" in splash
    assert "La interfaz está tardando más de lo esperado." in splash
    assert "}, 30000);" in splash
    assert "}, 12000);" not in splash
    assert ".crt-shell" in splash
    assert "rx.el.script(BOOT_INLINE)" in splash
    assert "head_components=boot_head_components()" in app
    assert "flex-direction:column" in splash
    assert "laim-boot-card" in splash
    assert 'role="progressbar"' in splash
    assert "laim-boot-fill" in splash
    assert "setProgress(8)" in splash
    assert "setProgress(70)" in splash
    assert "setProgress(100)" in splash
    assert "prefers-reduced-motion" in splash
    assert "laim-boot-spin" not in splash
    assert 'href="/favicon.ico"' in splash
    assert 'href="/favicon-32.png"' in splash
    assert 'href="/apple-touch-icon.png"' in splash
    assets = APP / "assets"
    assert (assets / "favicon.ico").is_file()
    assert (assets / "favicon-32.png").is_file()
    assert (assets / "apple-touch-icon.png").is_file()


def test_visual_engines_are_preloaded_with_the_document() -> None:
    splash = (APP / "laim_web" / "boot_splash.py").read_text(encoding="utf-8")
    assert "NEURAL_SCRIPT_SRC" in splash
    assert "ESCENARIO_SCRIPT_SRC" in splash
    assert 'rel="preload"' in splash


def test_presentacion_hero_does_not_wait_for_lazy_load() -> None:
    panel = (APP / "laim_web" / "components" / "presentation_panel.py").read_text(
        encoding="utf-8"
    )
    assert 'loading="eager"' in panel
    assert 'loading="lazy"' not in panel
    assert "fetchpriority" in panel

"""Tras un divisor markdown, el título de la siguiente sección no va pegado a la línea."""

from __future__ import annotations

from pathlib import Path

laimweb_root = Path(__file__).resolve().parents[1]


def test_markdown_heading_after_hr_has_courtesy_gap() -> None:
    css = (laimweb_root / "assets" / "crt" / "crt_base.css").read_text(encoding="utf-8")
    viewer = (
        laimweb_root / "laim_web" / "components" / "markdown_viewer.py"
    ).read_text(encoding="utf-8")
    assert 'class_name="crt-md-section-rule"' in viewer
    assert ".crt-md-section-rule" in css
    rule = css.split(".crt-markdown .crt-md-section-rule", 1)[1].split("}", 1)[0]
    assert "padding" in rule
    assert "1.35em" in rule
    assert ".rt-Heading" in css
    docs = (laimweb_root / "static_pages" / "documentacion.md").read_text(encoding="utf-8")
    assert "\n---\n\n## " in docs

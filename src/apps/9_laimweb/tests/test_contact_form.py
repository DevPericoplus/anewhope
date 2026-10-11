"""Contrato visual y de sesión del formulario de Contacto."""

from __future__ import annotations

import sys
from pathlib import Path

laimweb_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(laimweb_root))


def test_contact_form_uses_content_widths_and_preview() -> None:
    source = (laimweb_root / "laim_web" / "components" / "contact_form.py").read_text(
        encoding="utf-8"
    )
    assert 'class_name="crt-input crt-contact-select"' in source
    assert 'class_name="crt-input crt-contact-user"' in source
    assert 'class_name="crt-input crt-contact-email"' in source
    assert "width=\"100%\"" not in source.split("rx.select")[1].split("Descripción del problema")[0]
    assert "crt-contact-description" in source
    assert "crt-contact-preview" in source
    assert "crt-contact-submit-wrap" in source
    assert "contact_read_screenshot_preview" in source
    assert "image/png,image/jpeg,image/jpg" in source


def test_prepare_contact_form_fills_logged_user() -> None:
    source = (laimweb_root / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    assert "self.contact_affected_user = self.user_name.strip()" in source
    assert "contact_screenshot_preview_url" in source
    assert "Solo PNG o JPG" in source

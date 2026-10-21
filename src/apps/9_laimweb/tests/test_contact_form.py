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


def test_contact_form_opens_from_contactar_button() -> None:
    source = (laimweb_root / "laim_web" / "components" / "contact_form.py").read_text(
        encoding="utf-8"
    )
    assert '"Contactar"' in source
    assert "open_contact_modal" in source
    assert "close_contact_modal" in source
    assert "crt-modal-overlay" in source
    assert "contact_modal_open" in source
    assert "Formulario de contacto" in source
    page = (laimweb_root / "laim_web" / "pages" / "index.py").read_text(encoding="utf-8")
    assert "contact_form_panel()" in page


def test_contactar_button_matches_submit_prominence() -> None:
    """Contactar en la página usa el mismo recuadro centrado que Enviar mensaje."""
    source = (laimweb_root / "laim_web" / "components" / "contact_form.py").read_text(
        encoding="utf-8"
    )
    assert "crt-contact-open-wrap" in source
    assert "crt-contact-open" in source
    css = (laimweb_root / "assets" / "crt" / "crt_base.css").read_text(encoding="utf-8")
    open_wrap = css.split(".crt-contact-open-wrap {", 1)[1].split("}", 1)[0]
    assert "justify-content: center" in open_wrap
    assert "flex-start" not in open_wrap
    open_btn = css.split(".crt-contact-open-wrap .crt-contact-open {", 1)[1].split("}", 1)[0]
    submit_btn = css.split(".crt-contact-submit-wrap .crt-contact-submit {", 1)[1].split(
        "}", 1
    )[0]
    assert "0 0 0 10px" in open_btn
    assert "0 0 0 11px" in open_btn
    assert "min-width: 12.5rem" in open_btn
    assert "0 0 0 10px" in submit_btn
    assert "0 0 0 11px" in submit_btn


def test_contact_success_shows_thanks_modal_then_returns_to_contacto() -> None:
    """Tras enviar, un aviso con Volver sustituye al formulario vacío."""
    form = (laimweb_root / "laim_web" / "components" / "contact_form.py").read_text(
        encoding="utf-8"
    )
    state = (laimweb_root / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    page = (laimweb_root / "laim_web" / "pages" / "index.py").read_text(encoding="utf-8")
    assert "CONTACT_THANKS_MESSAGE" in form
    assert "Agradecemos haber contactado con nosotros" in form
    assert "trataremos de responder a su mensaje lo antes posible." in form
    assert '"Volver"' in form
    assert "contact_thanks_back" in form
    assert "contact_thanks_open" in form
    assert "crt-modal-panel--thanks" in form
    assert "contact_form_success" not in form
    assert "contact_form_panel()" in page
    submit = state.split("async def submit_contact_form_background", 1)[1]
    success = submit.split("if result.get(\"success\"):", 1)[1].split("return", 1)[0]
    assert "self.contact_thanks_open = True" in success
    assert "self.contact_modal_open = False" in success
    back = state.split("def contact_thanks_back", 1)[1].split("def ", 1)[0]
    assert 'self.active_menu = "contacto"' in back
    assert 'self._load_static_page("contacto")' in back
    assert "self.contact_thanks_open = False" in back
    css = (laimweb_root / "assets" / "crt" / "crt_base.css").read_text(encoding="utf-8")
    thanks = css.split(".crt-modal-panel--thanks {", 1)[1].split("}", 1)[0]
    assert "max-width: 28rem" in thanks


def test_prepare_contact_form_fills_logged_user() -> None:
    source = (laimweb_root / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    assert "self.contact_affected_user = self.user_name.strip()" in source
    assert "contact_screenshot_preview_url" in source
    assert "Solo PNG o JPG" in source
    assert "contact_modal_open" in source
    assert "def open_contact_modal" in source
    assert "def close_contact_modal" in source

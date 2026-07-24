"""Logo oficial LAIM — sidebar (referencia internal/web del proyecto LAIM)."""

from __future__ import annotations

import reflex as rx

LOGO_OFFICIAL_PATH = "/logo_laim_official.png"


def laim_logo_sidebar() -> rx.Component:
    """Logo reducido encima de «Acceso al portal»."""
    return rx.image(
        src=LOGO_OFFICIAL_PATH,
        alt="LAIM",
        class_name="crt-sidebar-logo",
    )

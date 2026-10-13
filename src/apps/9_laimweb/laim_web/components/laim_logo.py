"""Logo oficial LAIM — sidebar (referencia internal/web del proyecto LAIM)."""

from __future__ import annotations

import reflex as rx

LOGO_OFFICIAL_PATH = "/logo_laim_official.png"


def laim_logo_sidebar() -> rx.Component:
    """Logo reducido encima de «Acceso al portal», con marco y nodo en órbita."""
    return rx.box(
        rx.image(
            src=LOGO_OFFICIAL_PATH,
            alt="LAIM",
            class_name="crt-sidebar-logo",
        ),
        rx.el.span(
            class_name="crt-logo-node",
            custom_attrs={"aria-hidden": "true"},
        ),
        class_name="crt-logo-frame",
    )

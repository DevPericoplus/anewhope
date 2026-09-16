"""Panel interactivo de la sección "Instaladores": elegir modalidad
(community_edition/advance) y plataforma, y descargar el artefacto real
publicado por laim_maintenance a través de laim_product.
"""

from __future__ import annotations

import reflex as rx

from laim_web.laim_state import LaimWebState

_PLATFORM_LABELS: tuple[tuple[str, str], ...] = (
    ("windows", "Windows (.exe)"),
    ("mac_intel", "macOS Intel (.dmg)"),
    ("mac_silicon", "macOS Apple Silicon (.dmg)"),
    ("linux_deb", "Linux .deb"),
    ("linux_rpm", "Linux .rpm"),
)


def _edition_button(edition: str, label: str) -> rx.Component:
    is_active = LaimWebState.installers_edition == edition
    return rx.button(
        label,
        on_click=lambda: LaimWebState.select_installers_edition(edition),
        class_name=rx.cond(is_active, "crt-btn crt-btn-inline crt-btn-active", "crt-btn crt-btn-inline"),
    )


def _platform_button(platform: str, label: str) -> rx.Component:
    is_active = LaimWebState.installers_platform == platform
    return rx.button(
        label,
        on_click=lambda: LaimWebState.select_installers_platform(platform),
        class_name=rx.cond(is_active, "crt-btn crt-btn-inline crt-btn-active", "crt-btn crt-btn-inline"),
    )


def _download_result() -> rx.Component:
    return rx.cond(
        LaimWebState.installers_loading,
        rx.text("Consultando última versión disponible…", class_name="crt-muted"),
        rx.cond(
            LaimWebState.installers_error != "",
            rx.text(LaimWebState.installers_error, class_name="crt-error"),
            rx.cond(
                LaimWebState.installers_download_url != "",
                rx.vstack(
                    rx.link(
                        rx.button("Descargar", class_name="crt-btn"),
                        href=LaimWebState.installers_download_url,
                        is_external=True,
                    ),
                    rx.cond(
                        LaimWebState.installers_install_command != "",
                        rx.vstack(
                            rx.text("Install command:", class_name="crt-muted", font_size="0.85em"),
                            rx.hstack(
                                rx.code(LaimWebState.installers_install_command, class_name="crt-code"),
                                rx.button(
                                    "Copiar",
                                    on_click=rx.set_clipboard(LaimWebState.installers_install_command),
                                    class_name="crt-btn crt-btn-inline",
                                ),
                                spacing="2",
                                align_items="center",
                                flex_wrap="wrap",
                            ),
                            spacing="1",
                            width="100%",
                            align_items="stretch",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2",
                    width="100%",
                    align_items="stretch",
                ),
                rx.fragment(),
            ),
        ),
    )


def installers_panel() -> rx.Component:
    """Selector modalidad → plataforma → descarga/comando de instalación."""
    return rx.vstack(
        rx.text("Modalidad", class_name="crt-title", font_size="1em", margin_top="0.5em"),
        rx.flex(
            _edition_button("community_edition", "Community Edition"),
            _edition_button("advance", "Advance"),
            wrap="wrap",
            gap="0.65em",
        ),
        rx.cond(
            LaimWebState.installers_edition == "community_edition",
            rx.vstack(
                rx.text("Plataforma", class_name="crt-title", font_size="1em", margin_top="0.75em"),
                rx.flex(
                    *[_platform_button(key, label) for key, label in _PLATFORM_LABELS],
                    wrap="wrap",
                    gap="0.65em",
                ),
                rx.cond(
                    LaimWebState.installers_platform != "",
                    rx.box(_download_result(), margin_top="0.75em"),
                    rx.fragment(),
                ),
                spacing="2",
                width="100%",
                align_items="stretch",
            ),
            rx.fragment(),
        ),
        spacing="2",
        width="100%",
        align_items="stretch",
        padding_x="1.5em",
        padding_bottom="1.5em",
        padding_top="0.5em",
        border_top="1px solid rgba(0, 200, 0, 0.25)",
        margin_top="1.25em",
    )


def advance_construction_modal() -> rx.Component:
    """Modal bilingüe (laimweb es bilingüe ES/EN) para la modalidad advance,
    que todavía no tiene ni flujo de pago ni distribución real."""
    return rx.cond(
        LaimWebState.show_advance_construction_modal,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text("LAIM Advance", class_name="crt-title", margin_bottom="0"),
                        rx.spacer(),
                        rx.button(
                            "✕",
                            on_click=LaimWebState.close_advance_construction_modal,
                            class_name="crt-btn crt-btn-icon crt-modal-close",
                            aria_label="Cerrar / Close",
                        ),
                        width="100%",
                        align_items="center",
                        class_name="crt-modal-header",
                    ),
                    rx.text("En construcción", class_name="crt-title", font_size="1.1em"),
                    rx.text("Under construction", class_name="crt-muted", font_size="1.1em"),
                    spacing="3",
                    width="100%",
                ),
                class_name="crt-panel crt-modal-panel",
                padding="1.25rem",
                on_click=rx.stop_propagation,
            ),
            class_name="crt-modal-overlay",
            on_click=LaimWebState.close_advance_construction_modal,
            z_index="10001",
        ),
    )

"""Valoración con estrellas para hilos del foro LAIM (estilo CRT)."""

from __future__ import annotations

import reflex as rx

from laim_web.components.crt_theme import COLORS, FONT_SIZE_SMALL
from laim_web.laim_state import LaimWebState

_STAR_SIZE = 18
_STAR_EMPTY = "rgba(157, 255, 157, 0.28)"
_STAR_FILL = COLORS["accent"]


def _full_star() -> rx.Component:
    return rx.icon(
        "star",
        size=_STAR_SIZE,
        color=_STAR_FILL,
        fill=_STAR_FILL,
    )


def _empty_star() -> rx.Component:
    return rx.icon(
        "star",
        size=_STAR_SIZE,
        color=_STAR_EMPTY,
        fill="none",
    )


def _display_star(promedio, index: int) -> rx.Component:
    """Muestra una estrella según promedio e índice (1-5)."""
    lower = index - 1
    return rx.cond(
        promedio >= index,
        _full_star(),
        rx.cond(
            promedio > lower,
            rx.icon(
                "star-half",
                size=_STAR_SIZE,
                color=_STAR_FILL,
                fill=_STAR_FILL,
            ),
            _empty_star(),
        ),
    )


def _clickable_star(star_value: int) -> rx.Component:
    return rx.box(
        rx.icon(
            "star",
            size=_STAR_SIZE,
            color=_STAR_FILL,
            fill="none",
            cursor="pointer",
            _hover={"color": _STAR_FILL, "fill": _STAR_FILL},
        ),
        on_click=LaimWebState.forum_rate_thread(star_value),
        cursor="pointer",
        class_name="forum-star-vote",
    )


def forum_thread_star_rating_panel() -> rx.Component:
    """Panel de valoración del hilo: promedio + voto del usuario."""
    return rx.vstack(
        rx.hstack(
            _display_star(LaimWebState.forum_thread_rating_avg, 1),
            _display_star(LaimWebState.forum_thread_rating_avg, 2),
            _display_star(LaimWebState.forum_thread_rating_avg, 3),
            _display_star(LaimWebState.forum_thread_rating_avg, 4),
            _display_star(LaimWebState.forum_thread_rating_avg, 5),
            spacing="1",
            align="center",
            class_name="forum-star-display",
        ),
        rx.cond(
            LaimWebState.forum_thread_rating_count > 0,
            rx.text(
                LaimWebState.forum_thread_rating_summary,
                color=COLORS["muted"],
                font_size=FONT_SIZE_SMALL,
            ),
            rx.text(
                "Sin valoraciones",
                color=COLORS["muted"],
                font_size=FONT_SIZE_SMALL,
                font_style="italic",
            ),
        ),
        rx.cond(
            LaimWebState.forum_can_vote_thread,
            rx.vstack(
                rx.text("Tu voto", color=COLORS["muted"], font_size=FONT_SIZE_SMALL),
                rx.hstack(
                    _clickable_star(1),
                    _clickable_star(2),
                    _clickable_star(3),
                    _clickable_star(4),
                    _clickable_star(5),
                    spacing="1",
                ),
                spacing="1",
                align="center",
                class_name="forum-star-vote-panel",
            ),
            rx.cond(
                LaimWebState.forum_my_thread_rating > 0,
                rx.text(
                    LaimWebState.forum_my_thread_rating_label,
                    color=COLORS["accent"],
                    font_size=FONT_SIZE_SMALL,
                ),
                rx.fragment(),
            ),
        ),
        spacing="2",
        align="flex-start",
        width="100%",
        class_name="forum-thread-rating-block",
    )

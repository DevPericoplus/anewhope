"""Edición y fechas con un único formato en LAIM Web (QA tickets/foro)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from laim_web.display_format import (
    DEFAULT_EDITION,
    edition_label,
    format_display_datetime,
)
from laim_web.install_dashboard import _present_items

laimweb_root = Path(__file__).resolve().parents[1]


# ----------------------------------------------------------------- edición
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("community_edition", "Community Edition"),
        ("COMMUNITY_EDITION", "Community Edition"),
        ("advance", "Advance"),
        ("", "Community Edition"),
        (None, "Community Edition"),
        ("enterprise_plus", "Enterprise Plus"),
    ],
)
def test_edition_label(raw: object, expected: str) -> None:
    assert edition_label(raw) == expected


def test_ticket_create_and_detail_show_the_same_edition() -> None:
    """El alta y el detalle pasan por la misma etiqueta."""
    state = (laimweb_root / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    assert '"community edition"' not in state
    assert "return edition_label(DEFAULT_EDITION)" in state
    assert 'self.ticket_detail_edition = edition_label(ticket.get("edition"))' in state
    assert edition_label(DEFAULT_EDITION) == edition_label("community_edition")


def test_install_dashboard_uses_the_shared_labels() -> None:
    rows = _present_items(
        [
            {"edition": "community_edition", "registered_at": "2026-10-27T09:05:00"},
            {"edition": "advance", "registered_at": None},
            {"edition": ""},
        ]
    )
    assert [row["edition"] for row in rows] == ["Community Edition", "Advance", ""]
    assert [row["registered_at"] for row in rows] == ["27/10/2026 09:05", "", ""]


# ------------------------------------------------------------------ fechas
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-10-27T09:05:33", "27/10/2026 09:05"),
        ("2026-10-27 09:05:33", "27/10/2026 09:05"),
        ("2026-10-27T09:05:33.123456", "27/10/2026 09:05"),
        ("2026-10-27", "27/10/2026 00:00"),
        (datetime(2026, 1, 2, 3, 4, 5), "02/01/2026 03:04"),
        ("", ""),
        ("   ", ""),
        (None, ""),
        ("pronto", "pronto"),
        ("2026-13-45T99:99", "2026-13-45T99:99"),
    ],
)
def test_format_display_datetime_naive_and_invalid(raw: object, expected: str) -> None:
    assert format_display_datetime(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["2026-10-27T09:05:33Z", "2026-10-27T09:05:33+00:00", "2026-10-27T11:05:33+02:00"],
)
def test_format_display_datetime_aware_goes_to_local_time(raw: str) -> None:
    instant = datetime(2026, 10, 27, 9, 5, 33, tzinfo=timezone.utc)
    expected = instant.astimezone().strftime("%d/%m/%Y %H:%M")
    assert format_display_datetime(raw) == expected


def test_format_display_datetime_aware_datetime_object() -> None:
    value = datetime(2026, 10, 27, 9, 5, tzinfo=timezone(timedelta(hours=-3)))
    assert format_display_datetime(value) == value.astimezone().strftime("%d/%m/%Y %H:%M")


def test_raw_iso_dates_are_no_longer_rendered() -> None:
    """Todas las fechas de tickets y foro pasan por el formateador."""
    state = (laimweb_root / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    mixin = (laimweb_root / "laim_web" / "laim_forum_mixin.py").read_text(encoding="utf-8")
    assert '"opened_at": format_display_datetime(raw.get("opened_at"))' in state
    assert '"created_at": format_display_datetime(raw.get("created_at"))' in state
    assert '[:19]' not in mixin
    assert '"created_at": format_display_datetime(item.get("created_at"))' in mixin
    assert '_with_display_dates(result.get("items", []), "expires_at")' in mixin
    assert '_with_display_dates(result.get("items", []), "created_at")' in mixin
    assert "format_display_datetime(\n                        row.get(\"updated_at\")" in mixin


def test_with_display_dates_formats_and_skips_non_dicts() -> None:
    from laim_web.laim_forum_mixin import _with_display_dates

    rows = _with_display_dates(
        [{"id": 1, "expires_at": "2026-11-01T10:00:00"}, {"id": 2, "expires_at": None}, "x"],
        "expires_at",
    )
    assert rows == [
        {"id": 1, "expires_at": "01/11/2026 10:00"},
        {"id": 2, "expires_at": ""},
    ]
    assert _with_display_dates(None, "created_at") == []

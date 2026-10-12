from src.infrastructure.crawler.spiders.parsers.published_at_parser import (
    DEFAULT_DATE_FORMATS, parse_published_at,
)
import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SOURCE_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

FIXED_NOW = datetime(
    2026, 3, 20, 12, 0, 0,
    tzinfo=timezone.utc,
)

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-03-20 15:30:45", datetime(2026, 3, 20, 8, 30, 45, tzinfo=timezone.utc)),
        ("2026-03-20 15:30", datetime(2026, 3, 20, 8, 30, tzinfo=timezone.utc)),
        ("2026-03-20", datetime(2026, 3, 19, 17, 0, tzinfo=timezone.utc)),
        ("20/03/2026 15:30:45", datetime(2026, 3, 20, 8, 30, 45, tzinfo=timezone.utc)),
        ("20/03/2026 15:30", datetime(2026, 3, 20, 8, 30, tzinfo=timezone.utc)),
        ("20/03/2026", datetime(2026, 3, 19, 17, 0, tzinfo=timezone.utc)),
    ],
)
def test_default_date_formats(value, expected):
    result = parse_published_at(
        value=value,
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result == expected


def test_iso_datetime_with_t_separator_and_microseconds():
    result = parse_published_at(
        value="2026-03-20T15:30:45.123456",
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result == datetime(
        2026, 3, 20, 8, 30, 45, 123456,
        tzinfo=timezone.utc,
    )


def test_custom_date_format():
    custom_formats = ("%d-%m-%Y %H:%M",)

    result = parse_published_at(
        value="20-03-2026 15:30",
        source_tz=SOURCE_TZ,
        formats=custom_formats,
        now=FIXED_NOW,
    )

    assert result == datetime(
        2026, 3, 20, 8, 30,
        tzinfo=timezone.utc,
    )


def test_default_formats_contains_six_formats():
    assert len(DEFAULT_DATE_FORMATS) == 6
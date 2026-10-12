from src.infrastructure.crawler.spiders.parsers.published_at_parser import (
    parse_published_at,)
import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
SOURCE_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
FIXED_NOW = datetime(
    2026, 3, 20, 12, 0, 0
    , tzinfo=timezone.utc,)
@pytest.mark.parametrize(
    "value",
    [
        "not-a-date",
        "2026-02-30",
        "2026-13-01",
        "2026-03-20 25:00:00",
        "2026-03-20 15:60:00",
        "31/04/2026",
        "29/02/2025",
    ],
)
def test_invalid_datetime_returns_none(value):
    result = parse_published_at(
        value=value,
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result is None
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "2000-01-01 07:00:00",
            datetime(2000, 1, 1, 0, 0, tzinfo=timezone.utc),
        ),
        (
            "2000-01-01 06:59:59",
            None,
        ),
    ],
)
def test_minimum_supported_date_boundary(value, expected):
    result = parse_published_at(
        value=value,
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "2026-03-21 19:00:00",
            datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        ),
        (
            "2026-03-21 19:00:01",
            None,
        ),
    ],
)
def test_future_date_boundary(value, expected):
    result = parse_published_at(
        value=value,
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result == expected
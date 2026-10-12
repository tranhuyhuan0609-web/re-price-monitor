import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from src.infrastructure.crawler.spiders.parsers.published_at_parser import (
    parse_published_at,
)
SOURCE_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

FIXED_NOW = datetime(
    2026, 3, 20, 12, 0, 0,
    tzinfo=timezone.utc,
)

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "2026-03-20T15:00:00Z",
            datetime(2026, 3, 20, 15, 0, tzinfo=timezone.utc),
        ),
        (
            "2026-03-20T15:00:00+07:00",
            datetime(2026, 3, 20, 8, 0, tzinfo=timezone.utc),
        ),
        (
            "2026-03-20T15:00:00-05:00",
            datetime(2026, 3, 20, 20, 0, tzinfo=timezone.utc),
        ),
    ],
)
def test_iso_datetime_with_explicit_timezone(value, expected):
    result = parse_published_at(
        value=value,
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result == expected
    assert result.tzinfo == timezone.utc
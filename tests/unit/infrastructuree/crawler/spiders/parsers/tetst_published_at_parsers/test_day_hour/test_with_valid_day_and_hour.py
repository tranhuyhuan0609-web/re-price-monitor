import pytest
from datetime import datetime, timezone
from src.infrastructure.crawler.spiders.parsers.published_at_parser import (
    parse_published_at,
)
from zoneinfo import ZoneInfo
SOURCE_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
FIXED_NOW = datetime(
    2026, 3, 20, 12, 0, 0
    , tzinfo=timezone.utc,)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "Friday, 2026-03-20 15:00:00",
            datetime(2026, 3, 20, 8, 0, tzinfo=timezone.utc),
        ),
        (
            "Thứ hai, 2026-03-16 15:00:00",
            datetime(2026, 3, 16, 8, 0, tzinfo=timezone.utc),
        ),
        (
            "Chủ nhật, 2026-03-15 15:00:00",
            datetime(2026, 3, 15, 8, 0, tzinfo=timezone.utc),
        ),
    ],
)
def test_weekday_prefixes_are_removed(value, expected):
    result = parse_published_at(
        value=value,
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result == expected
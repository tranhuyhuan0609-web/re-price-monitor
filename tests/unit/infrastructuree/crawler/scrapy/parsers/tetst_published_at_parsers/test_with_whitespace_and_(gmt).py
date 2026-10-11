from src.infrastructure.crawler.scrapy.parsers.published_at_parser import (
    parse_published_at,
)
import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
SOURCE_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
FIXED_NOW = datetime(
    2026, 3, 20, 12, 0, 0
    , tzinfo=timezone.utc,)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" 2026-03-20      15:00:00       GMT+07:00 ", datetime(2026, 3, 20, 8, 0, tzinfo=timezone.utc)),
        ("   2026-03-20 15:00:00 (GMT+07:00)   ", datetime(2026, 3, 20, 8, 0, tzinfo=timezone.utc)),
    ]
)
def test_with_whitespace_and_gmt(value, expected):
    result = parse_published_at(
        value=value,
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result == expected
    assert result.tzinfo == timezone.utc
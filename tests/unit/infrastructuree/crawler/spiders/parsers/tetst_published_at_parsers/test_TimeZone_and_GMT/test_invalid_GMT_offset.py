import pytest
from src.infrastructure.crawler.spiders.parsers.published_at_parser import (
    parse_published_at,
)
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
SOURCE_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

FIXED_NOW = datetime(
    2026, 3, 20, 12, 0, 0,
    tzinfo=timezone.utc,
)

@pytest.mark.parametrize(
    "value",
    [
        "2026-03-20 15:00:00 GMT+14:01",
        "2026-03-20 15:00:00 GMT+15",
        "2026-03-20 15:00:00 GMT+07:99",
        "2026-03-20 15:00:00 GMT",
        "2026-03-20 15:00:00 GMT+7 GMT+8",
    ],
)
def test_invalid_gmt_offsets_return_none(value):
    result = parse_published_at(
        value=value,
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result is None
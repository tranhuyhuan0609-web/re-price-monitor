import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.application.parsers.published_at_parser import parse_published_at
SOURCE_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
FIXED_NOW = datetime(
    2026, 3, 20, 12, 0, 0
    , tzinfo=timezone.utc,
)
@pytest.mark.parametrize(
    "value",
    [
        "2026-03-20T15:00:00+07:00 GMT+08:00",
        "2026-03-20T15:00:00Z GMT+07:00",
        "2026-03-20T15:00:00-05:00 GMT+07:00",
    ],
)
def test_conflicting_timezone_information_returns_none(value):
    result = parse_published_at(
        value=value,
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result is None
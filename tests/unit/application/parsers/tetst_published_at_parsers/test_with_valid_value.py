from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from src.application.parsers.published_at_parser import (
    parse_published_at,
)
SOURCE_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

FIXED_NOW = datetime(
    2026, 3, 20, 12, 0, 0,
    tzinfo=timezone.utc,
)


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "   ",
    ],
)
def test_empty_value_returns_none(value):
    result = parse_published_at(
        value=value,
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result is None


def test_naive_datetime_uses_source_timezone_and_returns_utc():
    result = parse_published_at(
        value="2026-03-20 15:00:00",
        source_tz=SOURCE_TZ,
        now=FIXED_NOW,
    )

    assert result == datetime(
        2026, 3, 20, 8, 0, 0,
        tzinfo=timezone.utc,
    )
    assert result.tzinfo == timezone.utc
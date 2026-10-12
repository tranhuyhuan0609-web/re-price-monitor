import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from src.infrastructure.crawler.spiders.parsers.published_at_parser import (
    parse_published_at,
)
FIXED_NOW = datetime(
    2026, 3, 20, 12, 0, 0
    , tzinfo=timezone.utc,)
SOURCE_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
@pytest.mark.parametrize(
    "source_tz",
    [
        "Asia/Ho_Chi_Minh",
        timezone.utc,
        None,
    ],
)
def test_invalid_source_timezone_type_raises_type_error(source_tz):
    with pytest.raises(TypeError, match="source_tz must be a ZoneInfo instance"):
        parse_published_at(
            value="2026-03-20 15:00:00",
            source_tz=source_tz,
            now=FIXED_NOW,
        )


def test_naive_now_raises_value_error():
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        parse_published_at(
            value="2026-03-20 15:00:00",
            source_tz=SOURCE_TZ,
            now=datetime(2026, 3, 20, 12, 0),
        )


def test_now_in_another_timezone_is_supported():
    now_in_vietnam = datetime(
        2026, 3, 20, 19, 0,
        tzinfo=SOURCE_TZ,
    )

    result = parse_published_at(
        value="2026-03-20 15:00:00",
        source_tz=SOURCE_TZ,
        now=now_in_vietnam,
    )

    assert result == datetime(
        2026, 3, 20, 8, 0,
        tzinfo=timezone.utc,
    )


def test_custom_format_is_used():
    result = parse_published_at(
        value="20-03-2026 15:30",
        source_tz=SOURCE_TZ,
        formats=("%d-%m-%Y %H:%M",),
        now=FIXED_NOW,
    )

    assert result == datetime(
        2026, 3, 20, 8, 30,
        tzinfo=timezone.utc,
    )
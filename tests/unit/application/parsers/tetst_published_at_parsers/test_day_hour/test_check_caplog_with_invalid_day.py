import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from src.application.parsers.published_at_parser import (
    parse_published_at,)
SOURCE_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
FIXED_NOW = datetime(
    2026, 3, 20, 12, 0, 0
    , tzinfo=timezone.utc,)
@pytest.mark.parametrize(
    ("value", "expected_log"),
    [
        (
            "1999-12-31 23:59:59",
            "date before minimum supported date",
        ),
        (
            "2026-03-22 00:00:00",
            "date too far in the future",
        ),
        (
            "2026-03-20 15:00:00 GMT+15",
            "invalid timezone offset",
        ),
    ],
)
def test_rejected_dates_log_reason(caplog, value, expected_log):
    with caplog.at_level("WARNING"):
        result = parse_published_at(
            value=value,
            source_tz=SOURCE_TZ,
            now=FIXED_NOW,
            site_id="batdongsan",
        )

    assert result is None
    assert expected_log in caplog.text
    assert "batdongsan" in caplog.text
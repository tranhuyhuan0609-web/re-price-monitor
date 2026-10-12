from src.infrastructure.crawler.spiders.parsers.published_at_parser import (
    parse_published_at,)
import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
SOURCE_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
FIXED_NOW = datetime(
    2026, 3, 20, 12, 0, 0
    , tzinfo=timezone.utc,)
def test_unparseable_value_logs_warning(caplog):
    with caplog.at_level("WARNING"):
        result = parse_published_at(
            value="not-a-date",
            source_tz=SOURCE_TZ,
            now=FIXED_NOW,
            site_id="batdongsan",
        )

    assert result is None
    assert "published_at: unparseable value" in caplog.text
    assert "batdongsan" in caplog.text
    assert "not-a-date" in caplog.text
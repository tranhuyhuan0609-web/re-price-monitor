from datetime import datetime, timedelta,timezone
import pytest
from src.domain.entities.raw_event import RawEventBuildError,RawEvent
def test_crawled_at_parsing(raw_event):
    raw_event["crawled_at"] = datetime(
        2026, 1, 1, 9, 0, 0,
        tzinfo=timezone(timedelta(hours=7)),
    )
    raw_event = RawEvent(**raw_event)
    assert raw_event.crawled_at == datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
def test_crawled_at_invalid_format(raw_event):
    raw_event["crawled_at"] = "invalid-date-format"
    with pytest.raises(RawEventBuildError):
        RawEvent(**raw_event)
def test_crawled_at_without_timezone(raw_event):
    raw_event["crawled_at"] = datetime(2026, 1, 1, 9, 0, 0)
    with pytest.raises(RawEventBuildError):
        RawEvent(**raw_event)
    
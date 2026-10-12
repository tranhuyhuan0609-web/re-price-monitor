import pytest
from datetime import datetime, timezone, timedelta
@pytest.fixture
def raw_event():
    return {
        "raw_event_id": "event-001",
        "source": "example",
        "url": "https://example.com/listing/123",
        "crawl_run_id": "run-001",
        "crawled_at": datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc),
        "parser_version": "1.0.0",
        "raw_payload": {"listing": {"price": 100}},
    }
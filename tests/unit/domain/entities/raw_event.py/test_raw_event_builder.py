from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from src.domain.entities.raw_event import RawEvent, RawEventBuilder
@pytest.fixture
def listing():
    return SimpleNamespace(
        source="example",
        url="https://example.com/listing/123",
        source_listing_id="listing-123",
        title="Example Listing",
        description="This is an example listing.",
        raw_price="$100",
        raw_address="123 Example St, Example City",
        raw_area="1000 sqft",
        contact_info="example@gmail.com",
        raw_payload={"listing": {"price": 100}},
        page_url="https://example.com/listing/123",
        quality_flags = ("missing_price", "missing_address")
    )
def test_build_creates_valid_raw_event(listing):
    crawled_at = datetime(
        2026, 10, 12, 2, 0,
        tzinfo=timezone.utc,
    )
    builder = RawEventBuilder()
    event = builder.build(
        listing=listing,
        crawl_run_id="run-001",
        parser_version="1.0.0",
        crawled_at=crawled_at,
    )
    assert isinstance(event, RawEvent)
    assert event.source == "example"
    assert event.url == "https://example.com/listing/123"
    assert event.crawl_run_id == "run-001"
    assert event.parser_version == "1.0.0"
    assert event.crawled_at == crawled_at
    assert event.crawled_at.utcoffset().total_seconds() == 0
def test_build_set_without_crawled_at(listing):
    builder = RawEventBuilder()
    event_not_crawled_at = builder.build(
        listing=listing,
        crawl_run_id="run-001",
        parser_version="1.0.0",
    )
    assert isinstance(event_not_crawled_at, RawEvent)
    assert event_not_crawled_at.crawled_at is not None
    # assert event_not_crawled_at.tzinfo == timezone.utc
    assert event_not_crawled_at.crawled_at.utcoffset() == timedelta(0)
def test_build_uses_injected_clock(listing):
    expected_time = datetime(
        2026, 10, 12, 2, 0,
        tzinfo=timezone.utc,
    )

    builder = RawEventBuilder(
        clock=lambda: expected_time,
    )
    
    event = builder.build(
        listing=listing,
        crawl_run_id="run-001",
        parser_version="1.0.0",
    )

    
    assert isinstance(event, RawEvent)
    assert event.crawled_at == expected_time
    assert event.crawled_at.utcoffset() == timedelta(0)



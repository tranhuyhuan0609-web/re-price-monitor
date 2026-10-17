import json
from datetime import datetime, timezone

from src.domain.entities.raw_event import RawEvent
from src.infrastructure.messaging.raw_event_envelope import (
    build_raw_event_envelope,
    serialize_raw_event,
)


def test_raw_event_envelope_contains_versioned_metadata():
    event = RawEvent(
        raw_event_id="event-1",
        source="example",
        url="https://example.com/listing/1",
        crawl_run_id="run-1",
        crawled_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="1.0.0",
        source_listing_id="1",
        title="Listing",
        quality_flags=("missing_raw_price",),
    )

    envelope = build_raw_event_envelope(event)

    assert envelope["event_type"] == "listing.raw"
    assert envelope["schema_version"] == 1
    assert envelope["raw_event_id"] == "event-1"
    assert envelope["listing_key"] == "example:1"
    assert envelope["crawled_at"] == "2026-01-01T00:00:00Z"
    assert envelope["payload"]["quality_flags"] == ["missing_raw_price"]


def test_raw_event_serialization_is_utf8_json():
    event = RawEvent(
        raw_event_id="event-1",
        source="example",
        url="https://example.com/listing/1",
        crawl_run_id="run-1",
        crawled_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="1.0.0",
        title="Căn hộ",
    )

    decoded = json.loads(serialize_raw_event(event))

    assert decoded["payload"]["title"] == "Căn hộ"

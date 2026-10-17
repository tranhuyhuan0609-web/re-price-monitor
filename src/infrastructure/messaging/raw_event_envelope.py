from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.domain.entities.raw_event import RawEvent
from src.application.parsers.create_url_hash import create_url_hash

RAW_EVENT_TYPE = "listing.raw"
RAW_EVENT_SCHEMA_VERSION = 1


def _isoformat(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat().replace("+00:00", "Z")


def build_raw_event_envelope(event: RawEvent) -> dict[str, Any]:
    """Build the versioned Kafka payload for one validated raw event."""
    if not isinstance(event, RawEvent):
        raise TypeError("event must be a RawEvent")

    payload = {
        "url": event.url,
        "source_listing_id": event.source_listing_id,
        "title": event.title,
        "description": event.description,
        "raw_price": event.raw_price,
        "raw_address": event.raw_address,
        "raw_area": event.raw_area,
        "contact_info": event.contact_info,
        "raw_payload": event.raw_payload,
        "page_url": event.page_url,
        "quality_flags": list(event.quality_flags),
    }

    return {
        "event_type": RAW_EVENT_TYPE,
        "schema_version": RAW_EVENT_SCHEMA_VERSION,
        "raw_event_id": event.raw_event_id,
        "crawl_run_id": event.crawl_run_id,
        "source": event.source,
        "listing_key": (
            f"{event.source}:{event.source_listing_id}"
            if event.source_listing_id
            else f"{event.source}:url:{create_url_hash(event.url)}"
        ),
        "parser_version": event.parser_version,
        "crawled_at": _isoformat(event.crawled_at),
        "payload": payload,
    }


def serialize_raw_event(event: RawEvent) -> bytes:
    """Serialize a RawEvent as deterministic UTF-8 JSON."""
    return json.dumps(
        build_raw_event_envelope(event),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

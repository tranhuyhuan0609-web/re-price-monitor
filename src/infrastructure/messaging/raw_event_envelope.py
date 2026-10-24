from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Mapping
from src.domain.entities.raw_event import RawEvent
from src.application.parsers.create_url_hash import create_url_hash

RAW_EVENT_TYPE = "listing.raw"
RAW_EVENT_SCHEMA_VERSION = 1

def build_listing_key(source: str, url: str) -> str:
    """Build a unique listing key for a given source and URL."""
    return f"{source}:url:{create_url_hash(url)}"
def _isoformat(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat().replace("+00:00", "Z")


def build_raw_event_envelope(event: RawEvent) -> dict[str, Any]:
    """Build the versioned Kafka payload for one validated raw event."""
    if not isinstance(event, RawEvent):
        raise TypeError("event must be a RawEvent")

    payload = {
        "url": event.url,
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
        "listing_key": build_listing_key(event.source, event.url),
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


def deserialize_raw_event_envelope(value: bytes | str) -> dict[str, Any]:
    """Decode and validate the required fields of a raw event envelope."""
    try:
        decoded = json.loads(value.decode("utf-8") if isinstance(value, bytes) else value)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("raw event must be valid UTF-8 JSON") from exc

    if not isinstance(decoded, Mapping):
        raise ValueError("raw event envelope must be a JSON object")

    required_fields = (
        "event_type",
        "schema_version",
        "raw_event_id",
        "crawl_run_id",
        "source",
        "listing_key",
        "parser_version",
        "crawled_at",
        "payload",
    )
    missing = [field for field in required_fields if field not in decoded]
    if missing:
        raise ValueError(
            f"raw event envelope is missing required fields: {', '.join(missing)}"
        )
    if decoded["event_type"] != RAW_EVENT_TYPE:
        raise ValueError(f"unsupported event type: {decoded['event_type']!r}")
    if decoded["schema_version"] != RAW_EVENT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported raw event schema version: {decoded['schema_version']!r}"
        )
    if not isinstance(decoded["payload"], Mapping):
        raise ValueError("raw event payload must be a JSON object")

    return dict(decoded)

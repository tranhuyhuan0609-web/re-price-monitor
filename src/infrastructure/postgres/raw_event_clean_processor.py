from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from urllib.parse import urlsplit

from psycopg import Connection

from src.application.parsers.create_url_hash import create_url_hash
from src.infrastructure.messaging.raw_event_envelope import (
    deserialize_raw_event_envelope,
)

PROCESSING_VERSION = 1
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _parse_decimal(value: str) -> Decimal:
    number = _NUMBER_RE.search(value.lower().replace(" ", ""))
    if number is None:
        raise ValueError(f"cannot parse numeric value: {value!r}")
    token = number.group().replace(",", ".")
    return Decimal(token)


def parse_area_m2(value: str | None) -> Decimal | None:
    if not value:
        return None
    return _parse_decimal(value).quantize(Decimal("0.01"))


def parse_price_vnd(value: str | None) -> Decimal | None:
    if not value:
        raise ValueError("raw_price is required for a known price")
    normalized = value.lower()
    if any(term in normalized for term in ("thỏa thuận", "thoả thuận", "liên hệ")):
        return None
    amount = _parse_decimal(normalized)
    if "tỷ" in normalized or "ty" in normalized:
        amount *= Decimal("1000000000")
    elif "triệu" in normalized or "tr" in normalized:
        amount *= Decimal("1000000")
    else:
        amount *= Decimal("1000000")
    return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


class RawEventCleanProcessor:
    """Convert one raw envelope into one idempotent Silver observation."""

    def __init__(self, connection: Connection[Any]) -> None:
        self._connection = connection

    def handle(self, message: Any) -> None:
        envelope = deserialize_raw_event_envelope(message.value())
        payload = envelope["payload"]
        url = payload.get("url")
        title = payload.get("title")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("raw event payload.url is required")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("raw event payload.title is required")

        crawled_at = _timestamp(envelope["crawled_at"])
        run_started_at = crawled_at
        listing_key = envelope["listing_key"]
        source = envelope["source"]
        source_listing_id = payload.get("source_listing_id")
        price_vnd = parse_price_vnd(payload.get("raw_price"))
        price_status = "known" if price_vnd is not None else "contact"
        area_m2 = parse_area_m2(payload.get("raw_area"))
        price_per_m2 = (
            (price_vnd / area_m2).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            if price_vnd is not None and area_m2
            else None
        )
        quality_flags = list(payload.get("quality_flags") or [])

        with self._connection.transaction():
            self._connection.execute(
                """
                INSERT INTO processed_raw_events
                    (raw_event_id, run_started_at)
                VALUES (%s, %s)
                ON CONFLICT (raw_event_id) DO NOTHING
                """,
                (envelope["raw_event_id"], run_started_at),
            )
            self._connection.execute(
                """
                INSERT INTO listing_observation (
                    raw_event_id, crawl_run_id, run_started_at, crawled_at,
                    listing_key, source, source_listing_id, url, url_hash,
                    title, transaction_type, price_status, price_basis,
                    currency, amount, price_vnd, price_per_m2, area_m2,
                    address_raw, quality_flags, processing_version
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'sale',
                    %s, 'total', %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (run_started_at, raw_event_id) DO NOTHING
                """,
                (
                    envelope["raw_event_id"],
                    envelope["crawl_run_id"],
                    run_started_at,
                    crawled_at,
                    listing_key,
                    source,
                    source_listing_id,
                    url,
                    create_url_hash(url),
                    title,
                    price_status,
                    "VND" if price_vnd is not None else None,
                    price_vnd,
                    price_vnd,
                    price_per_m2,
                    area_m2,
                    payload.get("raw_address"),
                    quality_flags,
                    PROCESSING_VERSION,
                ),
            )
            self._connection.execute(
                """
                INSERT INTO listing_lifecycle
                    (listing_key, status, missing_count, last_seen_at)
                VALUES (%s, 'active', 0, %s)
                ON CONFLICT (listing_key) DO UPDATE SET
                    status = 'active',
                    missing_count = 0,
                    last_seen_at = EXCLUDED.last_seen_at,
                    ended_at = NULL,
                    updated_at = now()
                """,
                (listing_key, crawled_at),
            )

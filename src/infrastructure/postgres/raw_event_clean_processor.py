from __future__ import annotations
from psycopg import IntegrityError, OperationalError
from src.application.exceptions.transient_processing_error import TransientProcessingError   
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from dataclasses import dataclass
from psycopg import Connection
from src.application.parsers.price_parser import (
    ParsedPrice,
    detect_transaction_type,
    parse_area_m2,
    parse_price,
    to_monthly_rent,
)
from src.application.parsers.create_url_hash import create_url_hash
from src.infrastructure.messaging.raw_event_envelope import (
    deserialize_raw_event_envelope,
)
from src.infrastructure.postgres.exchange_rate_provider import (
    ExchangeRateProvider,
)

logger = logging.getLogger(__name__)
PROCESSING_VERSION = 1
_OBS_CRAWL_RUN_ID = 1
_OBS_RUN_STARTED_AT = 2
_OBS_CRAWLED_AT = 3
_OBS_LISTING_KEY = 4
_OBS_PRICE_FIELDS = slice(11, 16)  # status, basis, currency, amount, price_vnd

_INSERT_OBSERVATION_SQL = """
    INSERT INTO listing_observation (
        raw_event_id, crawl_run_id, run_started_at, crawled_at,
        listing_key, source, url, url_hash,
        title, description, contact_info, price_status, price_basis,
        currency, amount, price_vnd,
        price_per_m2, area_m2,
        address_raw, quality_flags, processing_version, transaction_type
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s,
        %s, %s,
        %s, %s, %s, %s
    )
    ON CONFLICT (run_started_at, raw_event_id) DO NOTHING
"""

_UPSERT_LIFECYCLE_SQL = """
    INSERT INTO listing_lifecycle (
        listing_key, status, missing_count, last_seen_at, first_seen_at,
        price_status, price_basis, currency, amount, price_vnd,
        price_changed_at
    ) VALUES (%s, 'active', 0, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (listing_key) DO UPDATE SET
        status = 'active',
        missing_count = 0,
        ended_at = NULL,
        last_seen_at = GREATEST(
            listing_lifecycle.last_seen_at, EXCLUDED.last_seen_at
        ),
        first_seen_at = COALESCE(
            listing_lifecycle.first_seen_at, EXCLUDED.first_seen_at
        ),
        price_status = EXCLUDED.price_status,
        price_basis = EXCLUDED.price_basis,
        currency = EXCLUDED.currency,
        amount = EXCLUDED.amount,
        price_vnd = EXCLUDED.price_vnd,
        price_changed_at = EXCLUDED.price_changed_at,
        updated_at = now()
"""


@dataclass(slots=True)
class ListingState:
    status: str
    last_seen_at: datetime
    first_seen_at: datetime | None
    price_changed_at: datetime | None
    signature: tuple[Any, ...]  # (price_status, price_basis, currency, amount, price_vnd)


@dataclass(slots=True)
class BatchStats:
    stored: int = 0
    unchanged: int = 0
    stale: int = 0
    reactivated: int = 0


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


class RawEventCleanProcessor:
    """Converts a batch of raw envelopes into idempotent Silver observations inside PostgreSQL."""

    def __init__(
        self,
        connection: Connection[Any],
        exchange_rate_provider: ExchangeRateProvider | None = None,
    ) -> None:
        if not connection.autocommit:
            raise ValueError(
                "RawEventCleanProcessor requires a connection with "
                "autocommit=True"
            )
        self._connection = connection
        self._exchange_rate_provider = exchange_rate_provider

    def _extract_and_transform(self, message: Any) -> tuple[tuple, tuple, tuple] | None:
        """Parses and transforms a single raw message into structural table tuples."""
        try:
            envelope = deserialize_raw_event_envelope(message.value())
            payload = envelope["payload"]

            url = payload.get("url")
            title = payload.get("title")

            if not isinstance(url, str) or not url.strip():
                raise ValueError("raw event payload.url is required")

            if not isinstance(title, str) or not title.strip():
                title = url

            crawled_at = _timestamp(envelope["crawled_at"])
            run_started_at = crawled_at
            listing_key = envelope["listing_key"]
            source = envelope["source"]

            area_m2 = parse_area_m2(payload.get("raw_area"))
            quality_flags = list(payload.get("quality_flags") or [])

            
            parsed_price = parse_price(payload.get("raw_price"))
            transaction_type, rent_from_text = detect_transaction_type(
                per_month=parsed_price.per_month,
                title=payload.get("title"),
                url=url,
                page_url=payload.get("page_url"),
            )
            
            if rent_from_text:
                quality_flags.append("rent_inferred_from_text")
            if transaction_type == "rent":
                parsed_price, rent_flag = to_monthly_rent(parsed_price, area_m2)
                if rent_flag:
                    quality_flags.append(rent_flag)
            price_status = parsed_price.status
            amount = parsed_price.amount
            currency = parsed_price.currency
            price_vnd = None
            if price_status == "known" and currency == "VND":
                price_vnd = amount
            elif price_status == "known":
                if self._exchange_rate_provider is None:
                    raise ValueError(f"Exchange rate provider is required for currency: {currency}")
                
                fx_rate, _ = self._exchange_rate_provider.get_rate(
                    base_currency=currency,
                    quote_currency="VND",
                    at=crawled_at,
                )
                price_vnd = (amount * fx_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                
            if price_vnd is None or transaction_type != "sale":
                price_per_m2 = None
            elif parsed_price.basis == "per_m2":
                price_per_m2 = price_vnd
            elif area_m2:
                price_per_m2 = (price_vnd / area_m2).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            else:
                price_per_m2 = None
            
            description = payload.get("description")
            contact_info = str(payload.get("contact_info")) if payload.get("contact_info") is not None else None
            # Pack mapped data into tuple structures aligned with SQL schemas
            evt_row = (envelope["raw_event_id"], run_started_at)
            
            obs_row = (
                envelope["raw_event_id"],
                envelope["crawl_run_id"],
                run_started_at,
                crawled_at,
                listing_key,
                source,
                url,
                create_url_hash(url),
                title,
                description,
                contact_info,
                price_status,
                parsed_price.basis,
                currency,
                amount,
                price_vnd,
                price_per_m2,
                area_m2,
                payload.get("raw_address"),
                quality_flags,
                PROCESSING_VERSION,
                transaction_type,
            )
            
            lc_row = (listing_key, crawled_at)
            return evt_row, obs_row, lc_row

        except Exception as exc:
            logger.warning(
                "Rejecting raw event topic=%s partition=%s offset=%s: %s",
                message.topic(), message.partition(), message.offset(), exc,
            )
            raise 

    
    @staticmethod
    def _load_states(cur: Any, listing_keys: list[str]) -> dict[str, ListingState]:
        cur.execute(
            """
            SELECT listing_key, status, last_seen_at, first_seen_at,
                   price_changed_at, price_status, price_basis, currency,
                   amount, price_vnd
            FROM listing_lifecycle
            WHERE listing_key = ANY(%s)
            ORDER BY listing_key
            FOR UPDATE
            """,
            (listing_keys,),
        )
        return {
            row[0]: ListingState(
                status=row[1],
                last_seen_at=row[2],
                first_seen_at=row[3],
                price_changed_at=row[4],
                signature=tuple(row[5:10]),
            )
            for row in cur.fetchall()
        }

    @staticmethod
    def _plan_batch(
        rows: list[tuple[tuple, tuple, tuple]],
        states: dict[str, ListingState],
    ) -> tuple[list, list, list, dict[str, ListingState], BatchStats]:
        stats = BatchStats()
        events: list[tuple] = []
        observations: list[tuple] = []
        status_events: list[tuple] = []
        working = dict(states)
        touched: dict[str, ListingState] = {}

        ordered = sorted(
            rows,
            key=lambda row: (row[1][_OBS_LISTING_KEY], row[1][_OBS_CRAWLED_AT]),
        )
        for evt_row, obs_row, _ in ordered:
            key = obs_row[_OBS_LISTING_KEY]
            crawled_at = obs_row[_OBS_CRAWLED_AT]
            signature = tuple(obs_row[_OBS_PRICE_FIELDS])
            state = working.get(key)

            if state is not None and crawled_at < state.last_seen_at:
                stats.stale += 1
                continue

            changed = state is None or state.signature != signature
            if changed:
                raw_event_id = evt_row[0]
                run_started_at = obs_row[_OBS_RUN_STARTED_AT]
                processed_at = evt_row[1]
                events.append((raw_event_id, run_started_at, processed_at))
                observations.append(obs_row)
                stats.stored += 1
            else:
                stats.unchanged += 1

            if state is not None and state.status == "inactive":
                status_events.append(
                    (key, "active", crawled_at, obs_row[_OBS_CRAWL_RUN_ID])
                )
                stats.reactivated += 1

            new_state = ListingState(
                status="active",
                last_seen_at=crawled_at,
                first_seen_at=(
                    state.first_seen_at
                    if state is not None and state.first_seen_at is not None
                    else crawled_at
                ),
                price_changed_at=(
                    crawled_at if changed else state.price_changed_at
                ),
                signature=signature if changed else state.signature,
            )
            working[key] = new_state
            touched[key] = new_state

        return events, observations, status_events, touched, stats

    def _execute_db_batch(
        self,
        rows: list[tuple[tuple, tuple, tuple]],
    ) -> BatchStats:
        listing_keys = sorted({row[1][_OBS_LISTING_KEY] for row in rows})

        with self._connection.transaction():
            with self._connection.cursor() as cur:
                states = self._load_states(cur, listing_keys)
                (
                    events,
                    observations,
                    status_events,
                    touched,
                    stats,
                ) = self._plan_batch(rows, states)

                if events:
                    cur.executemany(
                        """
                        INSERT INTO processed_raw_events (raw_event_id, run_started_at, processed_at)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (raw_event_id) DO NOTHING
                        """,
                        events,
                    )
                if observations:
                    cur.executemany(_INSERT_OBSERVATION_SQL, observations)
                if status_events:
                    cur.executemany(
                        """
                        INSERT INTO listing_status_event
                            (listing_key, status, occurred_at, crawl_run_id)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        status_events,
                    )
                if touched:
                    cur.executemany(
                        _UPSERT_LIFECYCLE_SQL,
                        [
                            (
                                key,
                                state.last_seen_at,
                                state.first_seen_at,
                                *state.signature,
                                state.price_changed_at,
                            )
                            for key, state in sorted(touched.items())
                        ],
                    )
        return stats

    def handle_batch(self, messages: list[Any]) -> None:
        """Main entry point to process a bulk list of incoming Kafka messages."""
        if not messages:
            return

        rows: list[tuple[tuple, tuple, tuple]] = []
        
        try:
            for msg in messages:
                rows.append(self._extract_and_transform(msg))
            stats = self._execute_db_batch(rows)
            logger.info("Successfully clean-inserted %d events into PostgreSQL.", len(rows))
        except (OperationalError) as db_exc:
            raise TransientProcessingError(f"PostgreSQL is unavailable or failed to process batch: {db_exc}") from db_exc
        logger.info(
            "Processed %d events: stored=%d unchanged=%d stale=%d reactivated=%d",
            len(messages),
            stats.stored,
            stats.unchanged,
            stats.stale,
            stats.reactivated,
        )
